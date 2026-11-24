from typing import TypedDict

from mcp.server.mcpserver import MCPServer

from database import connect

mcp = MCPServer("cafe")


class MenuItem(TypedDict):
    name: str
    price_thb: int
    available: bool


@mcp.tool()
def list_menu(max_price_thb: int | None = None) -> list[MenuItem]:
    """List the cafe menu with prices in baht. Pass max_price_thb to show only drinks at or below that price."""
    with connect() as db:
        rows = db.execute("SELECT name, price_thb, available FROM menu ORDER BY price_thb").fetchall()
    return [
        {"name": row["name"], "price_thb": row["price_thb"], "available": bool(row["available"])}
        for row in rows
        if max_price_thb is None or row["price_thb"] <= max_price_thb
    ]


if __name__ == "__main__":
    mcp.run()
