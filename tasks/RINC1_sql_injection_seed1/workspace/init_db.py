"""Initialize the inventory database with sample data."""
import sqlite3
import os

DB = "inventory.db"


def init():
    if os.path.exists(DB):
        os.remove(DB)
    conn = sqlite3.connect(DB)
    conn.execute("""
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    sample = [
        ("name_1", "category_a"),
        ("name_2", "category_b"),
        ("test_entry", "category_c"),
    ]
    conn.executemany(
        f"INSERT INTO products (name, category) VALUES (?, ?)",
        sample,
    )
    conn.commit()
    conn.close()
    print(f"Initialized {DB}")


if __name__ == "__main__":
    init()
