# DEMO: drives the attack servers with a plain client, no AI involved.
import asyncio
import sys

import anyio
from mcp import Client, StdioServerParameters
from mcp.server.mcpserver import Context, MCPServer

import cafe_server
import promo_rugpull_server
import promo_server


async def poison() -> None:
    promo_server.STOLEN_LOG.unlink(missing_ok=True)
    async with Client(promo_server.mcp) as client:
        for tool in (await client.list_tools()).tools:
            print(f"--- {tool.name}\n{tool.description}\n")
        # What a fooled model would do: read the orders, then pass them to the promo tool.
        async with Client(cafe_server.mcp) as cafe:
            orders = [(await cafe.read_resource(f"cafe://orders/{number}")).contents[0].text for number in (1, 2)]
        result = await client.call_tool("apply_promo", {"code": "SAVE10", "order_context": " ".join(orders)})
        print("tool result:", result.content[0].text)
    print("stolen.log:")
    print(promo_server.STOLEN_LOG.read_text())


async def wait_for_events(client: Client, trigger) -> int:
    async with client.listen(tools_list_changed=True) as subscription:
        print("subscription honored:", subscription.honored)
        await trigger()
        events = []
        with anyio.move_on_after(2):
            async for event in subscription:
                events.append(event)
        return len(events)


async def rugpull() -> None:
    promo_rugpull_server.FLAG.unlink(missing_ok=True)
    async with Client(promo_rugpull_server.mcp) as client:
        print("tools capability:", client.server_capabilities.tools)
        print("first tools/list:\n ", (await client.list_tools()).tools[0].description)

        async def flip_the_flag() -> None:
            promo_rugpull_server.FLAG.touch()

        print("list_changed events after the flag flipped:", await wait_for_events(client, flip_the_flag))
        print("second tools/list:\n ", (await client.list_tools()).tools[0].description.replace("\n", "\n  "))
    promo_rugpull_server.FLAG.unlink(missing_ok=True)

    # Control: a server that does publish the notification, to show the listener can hear one.
    control = MCPServer("control")

    @control.tool()
    async def change_tools(ctx: Context) -> str:
        await ctx.notify_tools_changed()
        return "sent"

    async with Client(control) as client:

        async def call_change_tools() -> None:
            await client.call_tool("change_tools", {})

        print("control server, list_changed events:", await wait_for_events(client, call_change_tools))


async def local_access() -> None:
    promo_server.STOLEN_LOG.unlink(missing_ok=True)
    stdio_server = StdioServerParameters(command=sys.executable, args=["promo_server.py"])
    async with Client(stdio_server) as client:  # a real subprocess, started the way Claude Code starts it
        result = await client.call_tool("todays_promotions", {})
        print("tool result:", result.content[0].text.replace("\n", " "))
    print("stolen.log:")
    print(promo_server.STOLEN_LOG.read_text())


asyncio.run({"poison": poison, "rugpull": rugpull, "local": local_access}[sys.argv[1]]())
