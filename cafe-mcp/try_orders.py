import asyncio

from mcp import Client
from mcp_types import ElicitResult

from cafe_server import mcp


def answer(action: str):
    async def callback(context, params):
        print(f"server asks: {params.message} -> user says {action}")
        return ElicitResult(action=action, content={"confirm": True} if action == "accept" else None)

    return callback


async def main() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()
        print("tools:", [tool.name for tool in tools.tools])

        order = {"items": [{"menu": "iced latte", "size": "M", "quantity": 2}], "customer_name": "Somchai"}
        result = await client.call_tool("create_order", order)
        print("created:", result.structured_content)

        for menu in ("mocha", "thai tea"):
            bad = {"items": [{"menu": menu, "size": "M", "quantity": 1}], "customer_name": "Somchai"}
            result = await client.call_tool("create_order", bad)
            print(f"{menu}: is_error={result.is_error}", result.content[0].text)

    for action in ("accept", "decline"):
        async with Client(mcp, elicitation_callback=answer(action)) as client:
            result = await client.call_tool("cancel_order", {"order_id": 1})
            print(f"{action}:", result.content[0].text)


asyncio.run(main())
