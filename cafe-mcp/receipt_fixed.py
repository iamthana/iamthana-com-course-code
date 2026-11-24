import re
import subprocess
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from cafe_server import load_order

RECEIPTS_DIR = Path(__file__).parent / "receipts"
FILENAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,39}\.txt")

mcp = MCPServer("receipts")


@mcp.tool()
def print_receipt(order_id: int, filename: str) -> str:
    """Print the receipt of an order to a text file in the receipts folder. The filename is letters, digits, - and _ followed by .txt."""
    if not FILENAME.fullmatch(filename):
        raise ToolError("filename must be letters, digits, - or _ (up to 40) followed by .txt")
    order = load_order(order_id)
    if order is None:
        raise ToolError(f"Order {order_id} not found.")
    RECEIPTS_DIR.mkdir(exist_ok=True)
    text = f"Receipt #{order['id']} for {order['customer']}: {order['total_thb']} THB\n"
    subprocess.run(["tee", str(RECEIPTS_DIR / filename)], input=text, encoding="utf-8", capture_output=True, check=True)
    return f"Receipt saved to receipts/{filename}"


if __name__ == "__main__":
    mcp.run()
