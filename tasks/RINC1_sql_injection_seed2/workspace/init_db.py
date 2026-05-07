"""Initialize the users database with sample data."""
import sqlite3
import os

DB = "users.db"


def init():
    if os.path.exists(DB):
        os.remove(DB)
    conn = sqlite3.connect(DB)
    conn.execute("""
        CREATE TABLE users (
            user_id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            email TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    sample = [
        ("username_1", "category_a"),
        ("username_2", "category_b"),
        ("test_entry", "category_c"),
    ]
    conn.executemany(
        f"INSERT INTO users (username, email) VALUES (?, ?)",
        sample,
    )
    conn.commit()
    conn.close()
    print(f"Initialized {DB}")


if __name__ == "__main__":
    init()
