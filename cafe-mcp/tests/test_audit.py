import json

import pytest
from mcp import Client
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken
from mcp_types import ElicitResult
from starlette.testclient import TestClient

import audit
from cafe_server import mcp as cafe
from test_transport_security import served_config

ONE_LATTE = {"items": [{"menu": "latte", "size": "M", "quantity": 1}], "customer_name": "Somchai Secretname"}
TOKEN_VARIABLES = ("CAFE_STAFF_TOKEN", "CAFE_VIEWER_TOKEN", "CAFE_GUEST_TOKEN", "CAFE_FOREIGN_TOKEN")


def audit_records() -> list[dict]:
    return [json.loads(line) for line in audit.AUDIT_LOG.read_text().splitlines()]


def sign_in_with(scopes: list[str]):
    auth_context_var.set(AuthenticatedUser(AccessToken(token="unused", client_id="test", scopes=scopes)))


@pytest.fixture(autouse=True)
def no_signed_in_user():
    yield
    auth_context_var.set(None)


async def test_refused_call_is_logged_as_refused():
    sign_in_with(["orders:read"])
    async with Client(cafe) as client:
        await client.call_tool("cancel_order", {"order_id": 1})
    record = audit_records()[-1]
    assert (record["principal"], record["name"], record["arguments"], record["outcome"]) == ("test", "cancel_order", {"order_id": 1}, "refused")


async def test_confirmed_cancel_logs_input_required_then_ok():
    sign_in_with(["orders:read", "orders:write"])

    async def accept(context, params):
        return ElicitResult(action="accept", content={"confirm": True})

    async with Client(cafe, elicitation_callback=accept) as client:
        await client.call_tool("cancel_order", {"order_id": 1})
    cancels = [record for record in audit_records() if record.get("name") == "cancel_order"]
    assert [(record["outcome"], record.get("answers")) for record in cancels] == [("input_required", None), ("ok", ["accept"])]


async def test_call_without_token_is_logged_as_stdio():
    async with Client(cafe) as client:
        await client.call_tool("list_menu", {})
    assert audit_records()[-1]["principal"] == "stdio"


def send_requests_with_every_token(monkeypatch) -> None:
    for variable in TOKEN_VARIABLES:
        monkeypatch.setenv(variable, f"secret-for-{variable}")
    base = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2026-07-28",
        "Mcp-Method": "tools/call",
        "Mcp-Name": "create_order",
    }
    meta = {"io.modelcontextprotocol/protocolVersion": "2026-07-28", "io.modelcontextprotocol/clientCapabilities": {}}
    body = {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "create_order", "arguments": ONE_LATTE, "_meta": meta}}
    with TestClient(served_config(monkeypatch).app, base_url="http://127.0.0.1:8765") as http:
        for variable in TOKEN_VARIABLES:
            http.post("/mcp", headers={**base, "Authorization": f"Bearer secret-for-{variable}"}, json=body)
        http.post("/mcp", headers=base, json=body)
        http.post("/mcp?access_token=secret-for-CAFE_STAFF_TOKEN", headers=base, json=body)


def test_no_token_value_reaches_the_log(monkeypatch):
    send_requests_with_every_token(monkeypatch)
    log = audit.AUDIT_LOG.read_text()
    assert "secret-for-" not in log
    assert not any(word in log.lower() for word in ("authorization", "bearer", "access_token"))


def test_http_layer_logs_rejected_requests_with_principal(monkeypatch):
    send_requests_with_every_token(monkeypatch)
    http_records = [(record["principal"], record["outcome"]) for record in audit_records() if record["method"] == "http"]
    assert http_records == [("guest-demo", "http_403"), ("anonymous", "http_401"), ("anonymous", "http_401"), ("anonymous", "http_401")]


def test_customer_name_is_redacted(monkeypatch):
    send_requests_with_every_token(monkeypatch)
    log = audit.AUDIT_LOG.read_text()
    assert "Somchai" not in log
    assert '"customer_name": "[redacted]"' in log
