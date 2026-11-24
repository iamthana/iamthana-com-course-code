import pytest
from mcp import Client

import receipt_fixed
from cafe_server import mcp as cafe

INJECTED_NAME = 'Malee"; touch pwned.txt; echo "'


@pytest.fixture(autouse=True)
def receipts_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(receipt_fixed, "RECEIPTS_DIR", tmp_path / "receipts")
    monkeypatch.chdir(tmp_path)
    return tmp_path / "receipts"


async def create_order(customer: str) -> int:
    items = [{"menu": "latte", "size": "M", "quantity": 1}]
    async with Client(cafe) as client:
        result = await client.call_tool("create_order", {"items": items, "customer_name": customer})
    return result.structured_content["id"]


async def print_receipt(order_id: int, filename: str):
    async with Client(receipt_fixed.mcp) as client:
        return await client.call_tool("print_receipt", {"order_id": order_id, "filename": filename})


async def test_injected_customer_name_is_printed_literally(tmp_path, receipts_folder):
    order_id = await create_order(INJECTED_NAME)
    result = await print_receipt(order_id, "receipt.txt")
    assert not result.is_error
    assert not (tmp_path / "pwned.txt").exists()
    assert (receipts_folder / "receipt.txt").read_text() == f"Receipt #{order_id} for {INJECTED_NAME}: 60 THB\n"


@pytest.mark.parametrize(
    "filename",
    ["../escaped.txt", "sub/receipt.txt", "/tmp/receipt.txt", "receipt.txt; touch pwned.txt", "-rf.txt", "receipt.sh", "", "a" * 41 + ".txt", "receipt.txt\n"],
    ids=["parent", "subfolder", "absolute", "semicolon", "leading-dash", "extension", "empty", "too-long", "trailing-newline"],
)
async def test_unsafe_filename_is_refused_before_anything_is_written(tmp_path, receipts_folder, filename):
    order_id = await create_order("Somchai")
    result = await print_receipt(order_id, filename)
    assert result.is_error
    assert [path.name for path in tmp_path.iterdir()] == ["cafe.db"]


async def test_unknown_order_is_refused(tmp_path):
    result = await print_receipt(999, "receipt.txt")
    assert result.is_error
    assert [path.name for path in tmp_path.iterdir()] == ["cafe.db"]
