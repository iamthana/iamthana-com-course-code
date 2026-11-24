from mcp.server.mcpserver import MCPServer

mcp = MCPServer("currency")


@mcp.tool()
def convert_thb(amount: float, to: str) -> str:
    """Convert an amount in baht to USD or EUR."""
    rates = {"USD": 0.028, "EUR": 0.026}
    return f"{amount * rates[to.upper()]:.2f} {to.upper()}"


if __name__ == "__main__":
    mcp.run()
