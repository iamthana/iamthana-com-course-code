import hmac
import os

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken
from mcp.server.auth.settings import AuthSettings
from mcp.server.mcpserver.exceptions import ToolError

RESOURCE_URL = "http://127.0.0.1:8765/mcp"

# environment variable -> (client id, scopes, resource the token was issued for)
DEMO_TOKENS = {
    "CAFE_STAFF_TOKEN": ("staff-demo", ["orders:read", "orders:write"], RESOURCE_URL),
    "CAFE_VIEWER_TOKEN": ("viewer-demo", ["orders:read"], RESOURCE_URL),
    "CAFE_GUEST_TOKEN": ("guest-demo", [], RESOURCE_URL),
    "CAFE_FOREIGN_TOKEN": ("foreign-demo", ["orders:read", "orders:write"], "http://127.0.0.1:9999/other"),
}

AUTH_SETTINGS = AuthSettings(
    issuer_url="https://auth.example.com",
    resource_server_url=RESOURCE_URL,
    required_scopes=["orders:read"],
    validate_token_resource=True,
)


class DemoTokenVerifier:
    """Stands in for JWT or introspection checks against a real authorization server."""

    async def verify_token(self, token: str) -> AccessToken | None:
        for variable, (client_id, scopes, resource) in DEMO_TOKENS.items():
            expected = os.environ.get(variable, "")
            if expected and hmac.compare_digest(token.encode(), expected.encode()):
                return AccessToken(token=token, client_id=client_id, scopes=scopes, resource=resource)
        return None


def require_scope(scope: str) -> None:
    # No access token means stdio or an in-process client; over HTTP the endpoint rejects requests without one.
    access_token = get_access_token()
    if access_token is not None and scope not in access_token.scopes:
        raise ToolError(f"This token cannot change orders: missing scope {scope}.")
