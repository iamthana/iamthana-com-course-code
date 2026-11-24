from mcp import Client
from mcp_types import ElicitResult

import notify_server
import stock_server


async def accept(context, params):
    return ElicitResult(action="accept", content={"confirm": True})


async def test_reorder_allows_one_open_order_per_ingredient():
    async with Client(stock_server.mcp, elicitation_callback=accept) as client:
        first = await client.call_tool("reorder", {"ingredient": "milk", "amount": 5000})
        second = await client.call_tool("reorder", {"ingredient": "milk", "amount": 5000})
    assert first.content[0].text == "Reorder #1: 5000 of milk."
    assert second.is_error
    assert "already has an open reorder" in second.content[0].text


async def test_reorder_rejects_amount_out_of_range():
    async with Client(stock_server.mcp, elicitation_callback=accept) as client:
        for amount in (0, -3, 1e9):
            result = await client.call_tool("reorder", {"ingredient": "milk", "amount": amount})
            assert result.is_error, amount


async def test_send_message_rejects_unknown_channel_and_stores_sql_text_as_data():
    sql_text = "'); DROP TABLE messages; --"
    async with Client(notify_server.mcp, elicitation_callback=accept) as client:
        unknown = await client.call_tool("send_message", {"channel": "general", "text": "hi"})
        sent = await client.call_tool("send_message", {"channel": "staff-group", "text": sql_text})
    assert unknown.is_error
    assert sent.content[0].text == "Sent message #1 to staff-group."
    with notify_server.connect() as db:
        assert db.execute("SELECT text FROM messages").fetchone()["text"] == sql_text
