import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "cafe.db"

SCHEMA = """
CREATE TABLE menu (name TEXT PRIMARY KEY, price_thb INTEGER NOT NULL, available INTEGER NOT NULL);
CREATE TABLE recipes (menu TEXT NOT NULL, size TEXT NOT NULL, instructions TEXT NOT NULL, PRIMARY KEY (menu, size));
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT, customer TEXT NOT NULL, status TEXT NOT NULL,
    total_thb INTEGER NOT NULL, order_date TEXT NOT NULL
);
CREATE TABLE order_items (order_id INTEGER NOT NULL, menu TEXT NOT NULL, size TEXT NOT NULL, quantity INTEGER NOT NULL);

INSERT INTO menu VALUES ('latte', 60, 1), ('iced latte', 65, 1), ('americano', 50, 1), ('thai tea', 45, 0);
INSERT INTO recipes VALUES
    ('latte', 'S', 'Espresso 1 shot, milk 120 ml'),
    ('latte', 'M', 'Espresso 2 shots, milk 180 ml'),
    ('latte', 'L', 'Espresso 2 shots, milk 260 ml'),
    ('iced latte', 'M', 'Espresso 2 shots, milk 150 ml, ice 150 g'),
    ('iced latte', 'L', 'Espresso 2 shots, milk 200 ml, ice 200 g'),
    ('americano', 'M', 'Espresso 2 shots, water 200 ml'),
    ('americano', 'L', 'Espresso 3 shots, water 280 ml'),
    ('thai tea', 'M', 'Thai tea 40 g, milk 60 ml, ice 150 g');
INSERT INTO orders VALUES (1, 'Malee', 'completed', 125, date('now')), (2, 'Preecha', 'completed', 100, date('now'));
INSERT INTO order_items VALUES (1, 'latte', 'M', 1), (1, 'iced latte', 'M', 1), (2, 'americano', 'L', 2);
"""


def connect() -> sqlite3.Connection:
    is_new = not DB_PATH.exists()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    if is_new:
        connection.executescript(SCHEMA)
    return connection
