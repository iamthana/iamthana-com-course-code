# DEMO: three requests against the receipts server given as the first argument (vulnerable or fixed).
import asyncio
import importlib
import sys

from mcp import Client

from cafe_server import mcp as cafe

SERVERS = {"vulnerable": "receipt_vulnerable", "fixed": "receipt_fixed"}
LATTE = [{"menu": "latte", "size": "M", "quantity": 1}]
REQUESTS = [
    ("normal name", "Somchai", "receipt-{id}.txt"),
    ("injected name", 'Malee"; touch pwned.txt; echo "', "receipt-{id}.txt"),
    ("traversal filename", "Preecha", "../escaped.txt"),
]


async def main(which: str) -> None:
    receipts_server = importlib.import_module(SERVERS[which]).mcp
    async with Client(cafe) as orders, Client(receipts_server) as receipts:
        for label, customer, filename in REQUESTS:
            created = await orders.call_tool("create_order", {"items": LATTE, "customer_name": customer})
            order_id = created.structured_content["id"]
            result = await receipts.call_tool("print_receipt", {"order_id": order_id, "filename": filename.format(id=order_id)})
            print(f"{label}: order {order_id}, is_error={result.is_error}, {result.content[0].text}")


asyncio.run(main(sys.argv[1]))
