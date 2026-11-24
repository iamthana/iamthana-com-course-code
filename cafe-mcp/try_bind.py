# DEMO: does the SDK check Host and Origin when the server is bound to 127.0.0.1 versus 0.0.0.0? No network needed.
from mcp.server.mcpserver import MCPServer
from starlette.testclient import TestClient

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
    "Origin": "http://evil.example.com:8765",
}

for bind_host in ("127.0.0.1", "0.0.0.0"):
    app = MCPServer("probe").streamable_http_app(host=bind_host)
    with TestClient(app, base_url="http://evil.example.com:8765") as http:
        print(f"bound to {bind_host}: foreign Host and Origin ->", http.post("/mcp", headers=HEADERS, json=BODY).status_code)
