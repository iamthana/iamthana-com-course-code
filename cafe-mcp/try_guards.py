import asyncio

from mcp import Client
from mcp.shared.exceptions import MCPError
from mcp_types import ElicitResult

import notify_server
import stock_server


def user_says(action: str):
    async def callback(context, params):
        print(f"  server asks: {params.message} -> {action}")
        return ElicitResult(action=action, content={"confirm": True} if action == "accept" else None)

    return callback


async def attempt(client, tool: str, arguments: dict) -> None:
    result = await client.call_tool(tool, arguments)
    shown = {key: (value[:30] + "..." if isinstance(value, str) and len(value) > 30 else value) for key, value in arguments.items()}
    text = result.content[0].text
    text = text.splitlines()[0] if result.is_error else " ".join(text.split())
    print(f"{tool} {shown}: is_error={result.is_error}", text)


async def main() -> None:
    print("## stock")
    async with Client(stock_server.mcp, elicitation_callback=user_says("accept")) as client:
        print("tools:", [tool.name for tool in (await client.list_tools()).tools])
        print("templates:", [item.uri_template for item in (await client.list_resource_templates()).resource_templates])
        for name in ("milk", "ice", "mocha", "' OR 1=1 --"):
            await attempt(client, "check_stock", {"ingredient": name})
        print("resource:", (await client.read_resource("stock://ingredients/milk")).contents[0].text.replace("\n", ""))
        for bad in (
            {"ingredient": "mocha", "amount": 5},
            {"ingredient": "milk", "amount": 0},
            {"ingredient": "milk", "amount": -3},
            {"ingredient": "milk", "amount": 1e9},
            {"ingredient": "milk", "amount": float("nan")},
        ):
            await attempt(client, "reorder", bad)
        await attempt(client, "reorder", {"ingredient": "milk", "amount": 5000})
        await attempt(client, "reorder", {"ingredient": "milk", "amount": 5000})
    for action in ("decline", "cancel"):
        async with Client(stock_server.mcp, elicitation_callback=user_says(action)) as client:
            await attempt(client, "reorder", {"ingredient": "ice", "amount": 3000})

    print("## notify")
    async with Client(notify_server.mcp, elicitation_callback=user_says("accept")) as client:
        print("tools:", [tool.name for tool in (await client.list_tools()).tools])
        print("channels:", (await client.read_resource("notify://channels")).contents[0].text.replace("\n", ""))
        for bad in (
            {"channel": "general", "text": "hi"},
            {"channel": "staff-group", "text": "   "},
            {"channel": "staff-group", "text": "x" * 501},
            {"channel": "' OR 1=1 --", "text": "hi"},
        ):
            await attempt(client, "send_message", bad)
        await attempt(client, "send_message", {"channel": "staff-group", "text": "'); DROP TABLE messages; --"})
    async with Client(notify_server.mcp, elicitation_callback=user_says("decline")) as client:
        await attempt(client, "send_message", {"channel": "owner", "text": "declined test"})
    async with Client(notify_server.mcp) as client:
        try:
            await attempt(client, "send_message", {"channel": "owner", "text": "no callback"})
        except MCPError as error:
            print(f"client without elicitation: error {error.code}: {error.message}")


asyncio.run(main())
