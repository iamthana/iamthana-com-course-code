from typing import Annotated, TypedDict

from mcp.server.mcpserver import AcceptedElicitation, Elicit, ElicitationResult, MCPServer, Resolve
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel

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


class OrderItem(BaseModel):
    menu: str
    size: str
    quantity: int


class Order(TypedDict):
    id: int
    customer: str
    status: str
    total_thb: int
    items: list[OrderItem]


class Confirmation(BaseModel):
    confirm: bool


def load_order(order_id: int) -> Order | None:
    with connect() as db:
        row = db.execute("SELECT id, customer, status, total_thb FROM orders WHERE id = ?", (order_id,)).fetchone()
        if row is None:
            return None
        items = db.execute("SELECT menu, size, quantity FROM order_items WHERE order_id = ?", (order_id,)).fetchall()
    return {**dict(row), "items": [OrderItem(**dict(item)) for item in items]}


@mcp.tool()
def create_order(items: list[OrderItem], customer_name: str) -> Order:
    """Create an order for a customer. Each item needs a menu name, a size (S, M or L) and a quantity."""
    if not items or not customer_name.strip():
        raise ToolError("An order needs a customer name and at least one item.")
    total = 0
    with connect() as db:
        for item in items:
            menu = db.execute("SELECT price_thb, available FROM menu WHERE name = ?", (item.menu,)).fetchone()
            size = db.execute("SELECT 1 FROM recipes WHERE menu = ? AND size = ?", (item.menu, item.size)).fetchone()
            if menu is None or not menu["available"] or size is None or item.quantity < 1:
                raise ToolError(f"Cannot order {item.quantity} x {item.menu} size {item.size}: check list_menu first.")
            total += menu["price_thb"] * item.quantity
        cursor = db.execute(
            "INSERT INTO orders (customer, status, total_thb, order_date) VALUES (?, 'open', ?, date('now'))",
            (customer_name, total),
        )
        db.executemany(
            "INSERT INTO order_items VALUES (?, ?, ?, ?)",
            [(cursor.lastrowid, item.menu, item.size, item.quantity) for item in items],
        )
    return load_order(cursor.lastrowid)


def ask_cancel_confirmation(order_id: int) -> Elicit[Confirmation]:
    order = load_order(order_id)
    if order is None:
        raise ToolError(f"Order {order_id} not found.")
    return Elicit(f"Cancel order {order_id} for {order['customer']} ({order['total_thb']} THB)?", Confirmation)


@mcp.tool()
def cancel_order(
    order_id: int,
    answer: Annotated[ElicitationResult[Confirmation], Resolve(ask_cancel_confirmation)],
) -> str:
    """Cancel an order after the user confirms."""
    if not isinstance(answer, AcceptedElicitation) or not answer.data.confirm:
        return f"Order {order_id} was not cancelled."
    with connect() as db:
        db.execute("UPDATE orders SET status = 'cancelled' WHERE id = ?", (order_id,))
    return f"Order {order_id} cancelled."


if __name__ == "__main__":
    mcp.run()
