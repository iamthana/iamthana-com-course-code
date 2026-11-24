import httpx2
import pytest
from mcp.server.auth.middleware.auth_context import auth_context_var
from mcp.server.auth.middleware.bearer_auth import AuthenticatedUser
from mcp.server.auth.provider import AccessToken
from mcp.server.mcpserver.exceptions import ToolError

from pos import fetch_sales


def mock_pos_api(requests: list[httpx2.Request]) -> httpx2.AsyncClient:
    def respond(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return httpx2.Response(200, text='{"total_thb": 225}')

    return httpx2.AsyncClient(transport=httpx2.MockTransport(respond))


@pytest.fixture(autouse=True)
def pos_credential(monkeypatch):
    monkeypatch.setenv("POS_API_TOKEN", "token-issued-to-this-server")
    yield
    auth_context_var.set(None)


async def test_downstream_call_carries_the_servers_credential_not_the_callers():
    auth_context_var.set(AuthenticatedUser(AccessToken(token="token-of-the-caller", client_id="viewer", scopes=["orders:read"])))
    requests: list[httpx2.Request] = []
    async with mock_pos_api(requests) as http:
        await fetch_sales("2026-11-24", http)
    assert requests[0].headers["Authorization"] == "Bearer token-issued-to-this-server"
    assert "token-of-the-caller" not in str(requests[0].headers)


async def test_caller_without_scope_never_reaches_the_downstream_api():
    auth_context_var.set(AuthenticatedUser(AccessToken(token="token-of-the-caller", client_id="guest", scopes=[])))
    requests: list[httpx2.Request] = []
    async with mock_pos_api(requests) as http:
        with pytest.raises(ToolError):
            await fetch_sales("2026-11-24", http)
    assert requests == []


async def test_day_must_be_a_date_before_it_reaches_the_url():
    requests: list[httpx2.Request] = []
    async with mock_pos_api(requests) as http:
        with pytest.raises(ValueError):
            await fetch_sales("../admin", http)
    assert requests == []
