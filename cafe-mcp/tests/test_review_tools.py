from mcp import Client

import promo_rugpull_server
import promo_server
from cafe_server import mcp as cafe
from review_tools import find_flags, fingerprint


async def tools_of(server) -> dict:
    async with Client(server) as client:
        return {tool.name: tool for tool in (await client.list_tools()).tools}


async def test_poisoned_description_is_flagged_and_cafe_tools_are_not():
    promo = await tools_of(promo_server.mcp)
    assert {"hidden-instruction tag", "asks to keep a step from the user"} <= set(find_flags(promo["apply_promo"]))
    assert find_flags(promo["todays_promotions"]) == []
    assert all(find_flags(tool) == [] for tool in (await tools_of(cafe)).values())


async def test_pinned_hash_changes_when_the_description_changes(tmp_path, monkeypatch):
    monkeypatch.setattr(promo_rugpull_server, "FLAG", tmp_path / "rugpull.flag")
    before = fingerprint((await tools_of(promo_rugpull_server.mcp))["apply_promo"])
    promo_rugpull_server.FLAG.touch()
    after = fingerprint((await tools_of(promo_rugpull_server.mcp))["apply_promo"])
    assert before != after
