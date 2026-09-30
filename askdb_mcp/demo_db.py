"""Sample customers/products/orders database used for demos and hosted deployments."""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path
from uuid import uuid4


SCHEMA = """
CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT, city TEXT);
CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT NOT NULL, price REAL NOT NULL);
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    ordered_at TEXT NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
"""

CUSTOMERS = [
    (1, "Olivia Bennett", "olivia.bennett@example.com", "London"),
    (2, "James Carter", "james.carter@example.com", "Manchester"),
    (3, "Emma Wilson", "emma.wilson@example.com", "Birmingham"),
    (4, "Noah Brooks", "noah.brooks@example.com", "Leeds"),
    (5, "Sophia Turner", "sophia.turner@example.com", "Bristol"),
    (6, "Liam Parker", "liam.parker@example.com", "York"),
]
PRODUCTS = [
    (1, "Notebook", 4.5),
    (2, "Keyboard", 39.99),
    (3, "Monitor", 159.0),
    (4, "Wireless Mouse", 24.75),
    (5, "Desk Lamp", 32.4),
    (6, "USB-C Hub", 44.9),
]
ORDERS = [
    (1, 1, 1, 3, "2026-08-01"),
    (2, 2, 2, 1, "2026-08-02"),
    (3, 3, 3, 2, "2026-08-03"),
    (4, 4, 4, 1, "2026-08-04"),
    (5, 5, 5, 2, "2026-08-05"),
    (6, 6, 6, 1, "2026-08-06"),
]


def create_demo_database(path: Path) -> None:
    """Create the sample database at ``path`` if it does not exist yet."""

    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    # Build under a temp name so concurrent cold starts never see a half-written file.
    tmp_path = path.with_name(f"{path.name}.{uuid4().hex}.tmp")
    with sqlite3.connect(tmp_path) as connection:
        connection.executescript(SCHEMA)
        connection.executemany("INSERT INTO customers VALUES (?, ?, ?, ?)", CUSTOMERS)
        connection.executemany("INSERT INTO products VALUES (?, ?, ?)", PRODUCTS)
        connection.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", ORDERS)
    connection.close()
    tmp_path.replace(path)


def main() -> None:
    target = Path(sys.argv[1] if len(sys.argv) > 1 else "example.sqlite")
    if target.exists():
        print(f"{target} already exists; leaving it unchanged.")
        return
    create_demo_database(target)
    print(f"Created demo database at {target.resolve()}")


if __name__ == "__main__":
    main()
