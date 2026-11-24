import sqlite3
from pathlib import Path
from typing import Annotated, TypedDict

from mcp.server.mcpserver import AcceptedElicitation, Elicit, ElicitationResult, MCPServer, Resolve
from mcp.server.mcpserver.exceptions import ResourceNotFoundError, ToolError
from pydantic import BaseModel

DB_PATH = Path(__file__).parent / "stock.db"
MAX_REORDER = 100_000

SCHEMA = """
CREATE TABLE stock (
    ingredient TEXT PRIMARY KEY, amount REAL NOT NULL, unit TEXT NOT NULL, reorder_level REAL NOT NULL
);
CREATE TABLE reorders (
    id INTEGER PRIMARY KEY AUTOINCREMENT, ingredient TEXT NOT NULL, amount REAL NOT NULL,
    status TEXT NOT NULL, created_at TEXT NOT NULL
);
INSERT INTO stock VALUES
    ('milk', 800, 'ml', 1000),
    ('coffee beans', 3000, 'g', 1000),
    ('ice', 4000, 'g', 2000),
    ('thai tea', 600, 'g', 200);
"""


def connect() -> sqlite3.Connection:
    is_new = not DB_PATH.exists()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    if is_new:
        connection.executescript(SCHEMA)
    return connection


mcp = MCPServer("stock")


class Ingredient(TypedDict):
    ingredient: str
    amount: float
    unit: str
    reorder_level: float
    is_low: bool


class Confirmation(BaseModel):
    confirm: bool


def load_ingredient(name: str) -> Ingredient | None:
    with connect() as db:
        row = db.execute("SELECT * FROM stock WHERE ingredient = ?", (name,)).fetchone()
    return None if row is None else {**dict(row), "is_low": row["amount"] <= row["reorder_level"]}


@mcp.tool()
def check_stock(ingredient: str) -> Ingredient:
    """Current stock of an ingredient, with is_low true when it is at or below its reorder level."""
    found = load_ingredient(ingredient)
    if found is None:
        raise ToolError(f"Unknown ingredient '{ingredient}'.")
    return found


def ask_reorder_confirmation(ingredient: str, amount: float) -> Elicit[Confirmation]:
    found = load_ingredient(ingredient)
    if found is None or not 0 < amount <= MAX_REORDER:
        raise ToolError(f"Cannot reorder {amount} of '{ingredient}': amount must be between 0 and {MAX_REORDER}.")
    with connect() as db:
        pending = db.execute("SELECT 1 FROM reorders WHERE ingredient = ? AND status = 'open'", (ingredient,)).fetchone()
    if pending:
        raise ToolError(f"'{ingredient}' already has an open reorder.")
    return Elicit(f"Order {amount:g} {found['unit']} of {ingredient} from the supplier?", Confirmation)


@mcp.tool()
def reorder(
    ingredient: str,
    amount: float,
    answer: Annotated[ElicitationResult[Confirmation], Resolve(ask_reorder_confirmation)],
) -> str:
    """Place a supplier reorder for an ingredient after the user confirms. Records an open reorder; stock does not change until delivery."""
    if not isinstance(answer, AcceptedElicitation) or not answer.data.confirm:
        return f"Reorder of {ingredient} was not placed."
    with connect() as db:
        cursor = db.execute(
            "INSERT INTO reorders (ingredient, amount, status, created_at) VALUES (?, ?, 'open', datetime('now'))",
            (ingredient, amount),
        )
    return f"Reorder #{cursor.lastrowid}: {amount:g} of {ingredient}."


@mcp.resource("stock://ingredients/{name}", mime_type="application/json")
def ingredient_resource(name: str) -> Ingredient:
    """Stock level of one ingredient."""
    found = load_ingredient(name)
    if found is None:
        raise ResourceNotFoundError(f"Unknown ingredient '{name}'")
    return found


if __name__ == "__main__":
    mcp.run()
