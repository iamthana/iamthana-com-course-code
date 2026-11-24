import pytest

import database
import notify_server
import stock_server


@pytest.fixture(autouse=True)
def fresh_databases(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "cafe.db")
    monkeypatch.setattr(stock_server, "DB_PATH", tmp_path / "stock.db")
    monkeypatch.setattr(notify_server, "DB_PATH", tmp_path / "notify.db")
