import runpy

import pytest
import uvicorn
from starlette.testclient import TestClient

BODY = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {"_meta": {"io.modelcontextprotocol/protocolVersion": "2026-07-28", "io.modelcontextprotocol/clientCapabilities": {}}},
}


def served_config(monkeypatch) -> uvicorn.Config:
    """Runs http_server.py with uvicorn stubbed out and returns the config it would have served."""
    served = []

    async def capture(server, *args, **kwargs):
        served.append(server.config)

    monkeypatch.setattr(uvicorn.Server, "serve", capture)
    runpy.run_module("http_server")
    return served[0]


@pytest.mark.parametrize(
    "extra_headers, expected_status",
    [
        ({}, 200),
        ({"Host": "evil.example.com:8765"}, 421),
        ({"Origin": "https://evil.example.com"}, 403),
        ({"Host": "evil.example.com:8765", "Origin": "http://evil.example.com:8765"}, 421),
        ({"Origin": "http://localhost:3000"}, 403),
        ({"Host": "localhost:8765"}, 421),
    ],
    ids=["normal", "foreign-host", "foreign-origin", "foreign-host-and-origin", "localhost-origin", "localhost-host"],
)
def test_http_server_refuses_foreign_host_and_origin(monkeypatch, extra_headers, expected_status):
    monkeypatch.setenv("CAFE_VIEWER_TOKEN", "secret-for-viewer")
    headers = {
        "Authorization": "Bearer secret-for-viewer",
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
        "MCP-Protocol-Version": "2026-07-28",
        "Mcp-Method": "tools/list",
        **extra_headers,
    }
    config = served_config(monkeypatch)
    assert (config.host, config.port) == ("127.0.0.1", 8765)
    with TestClient(config.app, base_url="http://127.0.0.1:8765") as http:
        assert http.post("/mcp", headers=headers, json=BODY).status_code == expected_status
