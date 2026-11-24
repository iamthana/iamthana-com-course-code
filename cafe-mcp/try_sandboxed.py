# DEMO: starts promo_server.py the way .mcp.json would, wrapped in a macOS sandbox profile.
import asyncio
from pathlib import Path

from mcp import Client, StdioServerParameters

HERE = Path(__file__).parent
STOLEN_LOG = HERE / "stolen.log"


async def main() -> None:
    STOLEN_LOG.unlink(missing_ok=True)
    sandboxed = StdioServerParameters(
        command="sandbox-exec",
        args=["-f", str(HERE / "promo.sb"), "-D", f"PROJECT={HERE}", "uv", "run", "--directory", str(HERE), "python", "promo_server.py"],
    )
    async with Client(sandboxed) as client:
        denied = await client.call_tool("todays_promotions", {})
        print("todays_promotions is_error:", denied.is_error)
        print("todays_promotions:", denied.content[0].text)
        allowed = await client.call_tool("apply_promo", {"code": "SAVE10"})
        print("apply_promo:", allowed.content[0].text)
    print("stolen.log:")
    print(STOLEN_LOG.read_text())


asyncio.run(main())
