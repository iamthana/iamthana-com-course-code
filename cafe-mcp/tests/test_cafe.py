import json

from mcp import Client
from mcp.shared.exceptions import MCPError
from mcp_types import ElicitResult, ResourceTemplateReference

from cafe_server import mcp as cafe

ONE_LATTE = {"items": [{"menu": "latte", "size": "M", "quantity": 1}], "customer_name": "Somchai"}


def user_says(action: str):
    async def callback(context, params):
        content = {"confirm": True} if action == "accept" else None
        return ElicitResult(action=action, content=content)

    return callback


async def order_status(client: Client, order_id: int) -> str:
    result = await client.read_resource(f"cafe://orders/{order_id}")
    return json.loads(result.contents[0].text)["status"]


async def test_list_menu_filters_by_price():
    async with Client(cafe) as client:
        result = await client.call_tool("list_menu", {"max_price_thb": 55})
    names = [item["name"] for item in result.structured_content["result"]]
    assert names == ["thai tea", "americano"]


async def test_create_order_calculates_total_from_menu():
    order = {"items": [{"menu": "iced latte", "size": "M", "quantity": 2}], "customer_name": "Somchai"}
    async with Client(cafe) as client:
        result = await client.call_tool("create_order", order)
    assert result.structured_content["id"] == 3
    assert result.structured_content["total_thb"] == 130


async def test_create_order_rejects_empty_items():
    async with Client(cafe) as client:
        result = await client.call_tool("create_order", {"items": [], "customer_name": "Somchai"})
    assert result.is_error
    assert "at least one item" in result.content[0].text


async def test_create_order_rejects_blank_customer():
    async with Client(cafe) as client:
        result = await client.call_tool("create_order", {**ONE_LATTE, "customer_name": "   "})
    assert result.is_error


async def test_create_order_rejects_unavailable_unknown_size_and_zero_quantity():
    bad_items = [
        {"menu": "thai tea", "size": "M", "quantity": 1},
        {"menu": "latte", "size": "XL", "quantity": 1},
        {"menu": "latte", "size": "M", "quantity": 0},
    ]
    async with Client(cafe) as client:
        for item in bad_items:
            result = await client.call_tool("create_order", {"items": [item], "customer_name": "Somchai"})
            assert result.is_error, item


async def test_cancel_order_after_user_accepts():
    async with Client(cafe, elicitation_callback=user_says("accept")) as client:
        result = await client.call_tool("cancel_order", {"order_id": 1})
        assert result.content[0].text == "Order 1 cancelled."
        assert await order_status(client, 1) == "cancelled"


async def test_cancel_order_does_nothing_after_user_declines():
    async with Client(cafe, elicitation_callback=user_says("decline")) as client:
        result = await client.call_tool("cancel_order", {"order_id": 1})
        assert result.content[0].text == "Order 1 was not cancelled."
        assert await order_status(client, 1) == "completed"


async def test_cancel_order_without_elicitation_support_is_refused():
    async with Client(cafe) as client:
        try:
            await client.call_tool("cancel_order", {"order_id": 1})
        except MCPError as error:
            assert error.code == -32021
        else:
            raise AssertionError("expected error -32021")


async def test_order_resource_returns_items_and_unknown_order_fails():
    async with Client(cafe) as client:
        order = json.loads((await client.read_resource("cafe://orders/2")).contents[0].text)
        assert order["customer"] == "Preecha"
        assert order["items"] == [{"menu": "americano", "size": "L", "quantity": 2}]
        try:
            await client.read_resource("cafe://orders/999")
        except MCPError as error:
            assert "Order 999 not found" in error.message
        else:
            raise AssertionError("expected not found")


async def test_daily_summary_embeds_sales_and_rejects_bad_date():
    async with Client(cafe) as client:
        rendered = await client.get_prompt("daily_summary", {"day": "2027-06-15"})
        assert rendered.messages[1].content.resource.uri == "cafe://sales/2027-06-15"
        try:
            await client.get_prompt("daily_summary", {"day": "yesterday"})
        except MCPError as error:
            assert "not a date" in error.message
        else:
            raise AssertionError("expected invalid params")


async def test_completion_suggests_by_prefix():
    template = ResourceTemplateReference(uri="cafe://recipes/{menu}/{size}")
    async with Client(cafe) as client:
        menus = await client.complete(template, {"name": "menu", "value": "i"})
        sizes = await client.complete(template, {"name": "size", "value": ""}, {"menu": "americano"})
    assert menus.completion.values == ["iced latte"]
    assert sizes.completion.values == ["L", "M"]
