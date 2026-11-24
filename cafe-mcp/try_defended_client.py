# DEMO: an MCP client over HTTP, with the token header, against the hardened http_server.py.
import asyncio
import os

import httpx2
from mcp import Client
from mcp.client.streamable_http import streamable_http_client


async def main() -> None:
    headers = {"Authorization": f"Bearer {os.environ['CAFE_STAFF_TOKEN']}"}
    async with httpx2.AsyncClient(headers=headers) as http:
        async with Client(streamable_http_client("http://127.0.0.1:8765/mcp", http_client=http)) as client:
            print("tools:", [tool.name for tool in (await client.list_tools()).tools])
            menu = await client.call_tool("list_menu", {"max_price_thb": 50})
            print("list_menu is_error:", menu.is_error)


asyncio.run(main())
