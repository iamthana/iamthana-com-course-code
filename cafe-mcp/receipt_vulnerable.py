# DEMO VULNERABLE SERVER: builds a shell command from order data. Do not copy this pattern.
import subprocess
from pathlib import Path

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from cafe_server import load_order

RECEIPTS_DIR = Path(__file__).parent / "receipts"

mcp = MCPServer("receipts-vulnerable")


@mcp.tool()
def print_receipt(order_id: int, filename: str) -> str:
    """Print the receipt of an order to a text file in the receipts folder."""
    order = load_order(order_id)
    if order is None:
        raise ToolError(f"Order {order_id} not found.")
    RECEIPTS_DIR.mkdir(exist_ok=True)
    command = f'echo "Receipt #{order["id"]} for {order["customer"]}: {order["total_thb"]} THB" | tee receipts/{filename}'
    subprocess.run(command, shell=True, cwd=RECEIPTS_DIR.parent, capture_output=True, check=True)
    return f"Receipt saved to receipts/{filename}"


if __name__ == "__main__":
    mcp.run()
