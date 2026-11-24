# DEMO of a vulnerable setup: no token and no Host/Origin check, on 127.0.0.1:8766 only.
from mcp.server.mcpserver import MCPServer
from mcp.server.transport_security import TransportSecuritySettings

mcp = MCPServer("open-cafe")


@mcp.tool()
def list_menu() -> list[str]:
    """List the cafe menu."""
    return ["latte", "americano"]


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8766,
        transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    )
