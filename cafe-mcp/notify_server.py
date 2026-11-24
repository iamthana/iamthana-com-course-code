import sqlite3
from pathlib import Path
from typing import Annotated

from mcp.server.mcpserver import AcceptedElicitation, Elicit, ElicitationResult, MCPServer, Resolve
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import BaseModel

DB_PATH = Path(__file__).parent / "notify.db"
MAX_TEXT_LENGTH = 500

SCHEMA = """
CREATE TABLE channels (id TEXT PRIMARY KEY, description TEXT NOT NULL);
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT, channel TEXT NOT NULL, text TEXT NOT NULL, sent_at TEXT NOT NULL
);
INSERT INTO channels VALUES ('staff-group', 'Barista group chat'), ('owner', 'Owner daily digest');
"""


def connect() -> sqlite3.Connection:
    is_new = not DB_PATH.exists()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    if is_new:
        connection.executescript(SCHEMA)
    return connection


mcp = MCPServer("notify")


class Confirmation(BaseModel):
    confirm: bool


@mcp.resource("notify://channels", mime_type="application/json")
def channels_resource() -> list[dict]:
    """Channels that send_message can reach."""
    with connect() as db:
        return [dict(row) for row in db.execute("SELECT id, description FROM channels ORDER BY id")]


def ask_send_confirmation(channel: str, text: str) -> Elicit[Confirmation]:
    with connect() as db:
        known = db.execute("SELECT 1 FROM channels WHERE id = ?", (channel,)).fetchone()
    if known is None:
        raise ToolError(f"Unknown channel '{channel}'. Read notify://channels first.")
    if not text.strip() or len(text) > MAX_TEXT_LENGTH:
        raise ToolError(f"A message needs 1 to {MAX_TEXT_LENGTH} characters.")
    return Elicit(f"Send to {channel}: {text}", Confirmation)


@mcp.tool()
def send_message(
    channel: str,
    text: str,
    answer: Annotated[ElicitationResult[Confirmation], Resolve(ask_send_confirmation)],
) -> str:
    """Send a message to a channel after the user confirms. Stand-in: stores the message in notify.db."""
    if not isinstance(answer, AcceptedElicitation) or not answer.data.confirm:
        return f"Message to {channel} was not sent."
    with connect() as db:
        cursor = db.execute(
            "INSERT INTO messages (channel, text, sent_at) VALUES (?, ?, datetime('now'))", (channel, text)
        )
    return f"Sent message #{cursor.lastrowid} to {channel}."


if __name__ == "__main__":
    mcp.run()
