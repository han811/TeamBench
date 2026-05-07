"""Initialize the bookstore database with sample data."""
import sqlite3
import os

DB = "bookstore.db"


def init():
    if os.path.exists(DB):
        os.remove(DB)
    conn = sqlite3.connect(DB)
    conn.execute("""
        CREATE TABLE books (
            book_id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            author TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    sample = [
        ("title_1", "category_a"),
        ("title_2", "category_b"),
        ("test_entry", "category_c"),
    ]
    conn.executemany(
        f"INSERT INTO books (title, author) VALUES (?, ?)",
        sample,
    )
    conn.commit()
    conn.close()
    print(f"Initialized {DB}")


if __name__ == "__main__":
    init()
