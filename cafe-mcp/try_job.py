import asyncio
import json
from datetime import datetime, timezone

from mcp import Client
from mcp_types import ElicitResult

import notify_server
import stock_server
from cafe_server import mcp as cafe

TODAY = datetime.now(timezone.utc).date().isoformat()
INGREDIENTS = ("milk", "coffee beans", "ice", "thai tea")


async def accept(context, params):
    print(f"  server asks: {params.message} -> accept")
    return ElicitResult(action="accept", content={"confirm": True})


async def main() -> None:
    async with (
        Client(cafe) as cafe_client,
        Client(stock_server.mcp, elicitation_callback=accept) as stock_client,
        Client(notify_server.mcp, elicitation_callback=accept) as notify_client,
    ):
        sales = json.loads((await cafe_client.read_resource(f"cafe://sales/{TODAY}")).contents[0].text)
        total = sum(order["total_thb"] for order in sales)
        print(f"1. cafe: {len(sales)} orders today, {total} THB")

        for name in INGREDIENTS:
            found = (await stock_client.call_tool("check_stock", {"ingredient": name})).structured_content
            print("2. stock:", found)
            if not found["is_low"]:
                continue
            placed = await stock_client.call_tool("reorder", {"ingredient": name, "amount": 5000})
            print("3. reorder:", placed.content[0].text)
            if placed.is_error:
                continue
            text = f"{len(sales)} orders, {total} THB today. {name} is at {found['amount']:g} {found['unit']}. {placed.content[0].text}"
            sent = await notify_client.call_tool("send_message", {"channel": "staff-group", "text": text})
            print("4. notify:", sent.content[0].text)


asyncio.run(main())
