import pytest
from mcp import Client
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken
from mcp.shared.exceptions import MCPError
from mcp_types import ElicitResult
from starlette.testclient import TestClient

from cafe_server import mcp as cafe

VIEWER_SCOPES = ["orders:read"]
STAFF_SCOPES = ["orders:read", "orders:write"]
ONE_LATTE = {"items": [{"menu": "latte", "size": "M", "quantity": 1}], "customer_name": "Somchai"}


def sign_in_with(scopes: list[str]):
    token = AccessToken(token="unused", client_id="test", scopes=scopes)
    return auth_context_var.set(AuthenticatedUser(token))


@pytest.fixture(autouse=True)
def no_signed_in_user():
    yield
    auth_context_var.set(None)


async def test_viewer_cannot_create_order():
    sign_in_with(VIEWER_SCOPES)
    async with Client(cafe) as client:
        result = await client.call_tool("create_order", ONE_LATTE)
        assert result.is_error
        assert "missing scope orders:write" in result.content[0].text
        with pytest.raises(MCPError):
            await client.read_resource("cafe://orders/3")


async def test_viewer_cancel_is_refused_before_the_question():
    sign_in_with(VIEWER_SCOPES)
    questions = []

    async def record_question(context, params):
        questions.append(params.message)
        return ElicitResult(action="accept", content={"confirm": True})

    async with Client(cafe, elicitation_callback=record_question) as client:
        result = await client.call_tool("cancel_order", {"order_id": 1})
    assert result.is_error
    assert questions == []


async def test_staff_is_asked_before_cancelling():
    sign_in_with(STAFF_SCOPES)
    questions = []

    async def decline(context, params):
        questions.append(params.message)
        return ElicitResult(action="decline")

    async with Client(cafe, elicitation_callback=decline) as client:
        result = await client.call_tool("cancel_order", {"order_id": 1})
    assert len(questions) == 1
    assert result.content[0].text == "Order 1 was not cancelled."


@pytest.mark.parametrize(
    "token_variable, expected_status",
    [(None, 401), ("CAFE_NO_SUCH_TOKEN", 401), ("CAFE_FOREIGN_TOKEN", 401), ("CAFE_GUEST_TOKEN", 403), ("CAFE_VIEWER_TOKEN", 200)],
)
def test_endpoint_status_by_token(monkeypatch, token_variable, expected_status):
    for variable in ("CAFE_STAFF_TOKEN", "CAFE_VIEWER_TOKEN", "CAFE_GUEST_TOKEN", "CAFE_FOREIGN_TOKEN"):
        monkeypatch.setenv(variable, f"secret-for-{variable}")
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2026-07-28",
        "Mcp-Method": "tools/list",
    }
    if token_variable:
        headers["Authorization"] = f"Bearer secret-for-{token_variable}"
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {"_meta": {"io.modelcontextprotocol/protocolVersion": "2026-07-28", "io.modelcontextprotocol/clientCapabilities": {}}},
    }
    with TestClient(cafe.streamable_http_app(), base_url="http://127.0.0.1:8765") as http:
        response = http.post("/mcp", headers=headers, json=body)
    assert response.status_code == expected_status
