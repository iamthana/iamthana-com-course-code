import asyncio
from datetime import datetime, timezone

from mcp import Client

from cafe_server import mcp

TODAY = datetime.now(timezone.utc).date().isoformat()
URIS = [
    "cafe://menu",
    "cafe://orders/1",
    "cafe://orders/99",
    "cafe://orders/abc",
    "cafe://orders/99999999999999999999",
    f"cafe://sales/{TODAY}",
    "cafe://sales/2026-02-30",
    "cafe://sales/yesterday",
    "cafe://recipes/latte/M",
    "cafe://recipes/latte/XL",
    "cafe://recipes/' OR 1=1 --/M",
]


async def main() -> None:
    async with Client(mcp) as client:
        print("resources:", [(item.name, item.uri) for item in (await client.list_resources()).resources])
        templates = (await client.list_resource_templates()).resource_templates
        print("templates:", [(item.name, item.uri_template) for item in templates])
        for uri in URIS:
            try:
                result = await client.read_resource(uri)
                print(f"{uri} ->", result.contents[0].mime_type, result.contents[0].text)
            except Exception as error:
                print(f"{uri} -> {type(error).__name__}: {error}")


asyncio.run(main())
