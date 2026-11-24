# DEMO: a server bound to 0.0.0.0 with and without explicit transport_security. No network needed.
from mcp.server.mcpserver import MCPServer
from starlette.testclient import TestClient

from auth import TRANSPORT_SECURITY

BODY = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {"_meta": {"io.modelcontextprotocol/protocolVersion": "2026-07-28", "io.modelcontextprotocol/clientCapabilities": {}}},
}
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
    "MCP-Protocol-Version": "2026-07-28",
    "Mcp-Method": "tools/list",
}
FOREIGN = "http://evil.example.com:8765"
CASES = [
    ("0.0.0.0, no settings, foreign Host and Origin", None, FOREIGN, {"Origin": FOREIGN}),
    ("0.0.0.0, explicit settings, foreign Host and Origin", TRANSPORT_SECURITY, FOREIGN, {"Origin": FOREIGN}),
    ("0.0.0.0, explicit settings, Host 127.0.0.1:8765", TRANSPORT_SECURITY, "http://127.0.0.1:8765", {}),
]

for label, settings, base_url, extra_headers in CASES:
    app = MCPServer("probe").streamable_http_app(host="0.0.0.0", transport_security=settings)
    with TestClient(app, base_url=base_url) as http:
        print(f"{label} ->", http.post("/mcp", headers=HEADERS | extra_headers, json=BODY).status_code)
