import asyncio

from mcp import Client

from cafe_server import mcp


async def main() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()
        for tool in tools.tools:
            print(tool.name, "->", tool.input_schema)

        result = await client.call_tool("list_menu", {"max_price_thb": 55})
        print("content:", [block.text for block in result.content])
        print("structuredContent:", result.structured_content)


asyncio.run(main())
