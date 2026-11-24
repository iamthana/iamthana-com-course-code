import json
from datetime import date
from typing import Annotated, TypedDict

from mcp.server.mcpserver import AcceptedElicitation, Elicit, ElicitationResult, MCPServer, Resolve
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError
from mcp.server.mcpserver.prompts.base import UserMessage
from mcp.shared.exceptions import MCPError
from mcp_types import (
    INVALID_PARAMS,
    Completion,
    CompletionArgument,
    CompletionContext,
    EmbeddedResource,
    PromptReference,
    ResourceTemplateReference,
    TextResourceContents,
)
from pydantic import BaseModel

from audit import audit_middleware
from auth import AUTH_SETTINGS, DemoTokenVerifier, require_scope
from database import connect

mcp = MCPServer("cafe", auth=AUTH_SETTINGS, token_verifier=DemoTokenVerifier(), middleware=[audit_middleware])


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
    require_scope("orders:write")
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
    require_scope("orders:write")  # resolvers run before the tool body, so this refuses before any question
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


@mcp.resource("cafe://menu", mime_type="application/json")
def menu_resource() -> list[MenuItem]:
    """The full menu as JSON."""
    return list_menu()


@mcp.resource("cafe://orders/{order_id}", mime_type="application/json")
def order_resource(order_id: str) -> str:
    """One order with its items."""
    try:
        order = load_order(int(order_id))
    except (ValueError, OverflowError):
        raise ResourceNotFoundError(f"'{order_id}' is not an order number") from None
    if order is None:
        raise ResourceNotFoundError(f"Order {order_id} not found")
    return json.dumps(order, default=lambda item: item.model_dump(), ensure_ascii=False)


@mcp.resource("cafe://sales/{day}", mime_type="application/json")
def sales_resource(day: str) -> list[dict]:
    """Orders placed on a day (YYYY-MM-DD), without customer names."""
    try:
        date.fromisoformat(day)
    except ValueError:
        raise ResourceNotFoundError(f"'{day}' is not a date, use YYYY-MM-DD") from None
    with connect() as db:
        rows = db.execute("SELECT id, status, total_thb FROM orders WHERE order_date = ?", (day,))
        return [dict(row) for row in rows]


@mcp.resource("cafe://recipes/{menu}/{size}", mime_type="text/plain")
def recipe_resource(menu: str, size: str) -> str:
    """How to make a drink in a given size."""
    with connect() as db:
        row = db.execute("SELECT instructions FROM recipes WHERE menu = ? AND size = ?", (menu, size)).fetchone()
    if row is None:
        raise ResourceNotFoundError(f"No recipe for {menu} size {size}")
    return row["instructions"]


@mcp.prompt()
def daily_summary(day: str, focus: str = "") -> list[UserMessage]:
    """Summarise the cafe's sales for a day (YYYY-MM-DD). Optional focus narrows the summary."""
    try:
        sales = sales_resource(day)
    except ResourceNotFoundError as error:
        raise MCPError(INVALID_PARAMS, str(error)) from None
    instruction = f"Summarise the cafe's sales for {day}: total in baht, number of orders, and how many are not completed."
    if focus:
        instruction += f" Focus on: {focus}"
    return [
        UserMessage(instruction),
        UserMessage(
            EmbeddedResource(
                type="resource",
                resource=TextResourceContents(
                    uri=f"cafe://sales/{day}", mime_type="application/json", text=json.dumps(sales, indent=2)
                ),
            )
        ),
    ]


MAX_SUGGESTIONS = 10


@mcp.completion()
async def complete_arguments(
    ref: PromptReference | ResourceTemplateReference,
    argument: CompletionArgument,
    context: CompletionContext | None,
) -> Completion | None:
    chosen = context.arguments if context and context.arguments else {}
    if argument.name == "menu":
        query, parameters = "SELECT name FROM menu WHERE instr(lower(name), lower(?)) = 1 ORDER BY name", [argument.value]
    elif argument.name == "size":
        query = "SELECT size FROM recipes WHERE menu = ? AND instr(lower(size), lower(?)) = 1 ORDER BY size"
        parameters = [chosen.get("menu", ""), argument.value]
    elif argument.name == "day":
        query = "SELECT DISTINCT order_date FROM orders WHERE instr(order_date, ?) = 1 ORDER BY order_date DESC"
        parameters = [argument.value]
    else:
        return None
    with connect() as db:
        rows = db.execute(f"{query} LIMIT ?", [*parameters, MAX_SUGGESTIONS + 1]).fetchall()
    return Completion(values=[row[0] for row in rows[:MAX_SUGGESTIONS]], has_more=len(rows) > MAX_SUGGESTIONS)


if __name__ == "__main__":
    mcp.run()
