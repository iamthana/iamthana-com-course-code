import pytest

import audit
import database
import notify_server
import stock_server


@pytest.fixture(autouse=True)
def fresh_databases(tmp_path, tmp_path_factory, monkeypatch):
    monkeypatch.setattr(database, "DB_PATH", tmp_path / "cafe.db")
    monkeypatch.setattr(stock_server, "DB_PATH", tmp_path / "stock.db")
    monkeypatch.setattr(notify_server, "DB_PATH", tmp_path / "notify.db")
    monkeypatch.setattr(audit, "AUDIT_LOG", tmp_path_factory.mktemp("audit") / "audit.log")
