import asyncio

from mcp import Client
from mcp_types import PromptReference, ResourceTemplateReference

from cafe_server import mcp

RECIPE = ResourceTemplateReference(type="ref/resource", uri="cafe://recipes/{menu}/{size}")
SALES = ResourceTemplateReference(type="ref/resource", uri="cafe://sales/{day}")
SUMMARY = PromptReference(type="ref/prompt", name="daily_summary")
CASES = [
    ("menu, prefix 'la'", RECIPE, "menu", "la", None),
    ("menu, prefix 'i'", RECIPE, "menu", "i", None),
    ("menu, uppercase prefix 'AM'", RECIPE, "menu", "AM", None),
    ("menu, empty prefix", RECIPE, "menu", "", None),
    ("menu, no match", RECIPE, "menu", "mocha", None),
    ("menu, SQL wildcard '%'", RECIPE, "menu", "%", None),
    ("size, menu=latte", RECIPE, "size", "", {"menu": "latte"}),
    ("size, menu=americano", RECIPE, "size", "", {"menu": "americano"}),
    ("size, menu=latte, prefix 'm'", RECIPE, "size", "m", {"menu": "latte"}),
    ("size, unknown menu", RECIPE, "size", "", {"menu": "mocha"}),
    ("size, no menu chosen", RECIPE, "size", "", None),
    ("day, resource, empty prefix", SALES, "day", "", None),
    ("day, prompt, prefix '2026-11-2'", SUMMARY, "day", "2026-11-2", None),
    ("day, prompt, no match", SUMMARY, "day", "1999", None),
    ("focus, prompt", SUMMARY, "focus", "can", None),
]


async def main() -> None:
    async with Client(mcp) as client:
        for label, ref, name, value, chosen in CASES:
            result = await client.complete(ref, {"name": name, "value": value}, context_arguments=chosen)
            print(f"{label}: {result.completion.values} has_more={result.completion.has_more}")


asyncio.run(main())
