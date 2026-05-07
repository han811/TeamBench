"""
Migration: Rename column in users using expand-contract pattern.

PROBLEM: SQLite doesn't support ALTER TABLE RENAME COLUMN in old versions.
The naive approach (CREATE new table, copy, drop old) holds an exclusive
lock for the full duration. PostgreSQL's RENAME COLUMN is faster but still
blocks concurrent writes.

Fix: expand-contract — add new column, dual-write, backfill, cut over.
"""
import sqlite3
import time


DB = "users.db"
OLD_COLUMN = "full_name"
NEW_COLUMN = "display_name"


def seed_data(conn, n_rows: int = 6500):
    """Create and populate the users table."""
    conn.execute("DROP TABLE IF EXISTS users")
    conn.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            full_name TEXT,
            email TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.executemany(
        "INSERT INTO users (username, full_name, email) VALUES (?, ?, ?)",
        [(f"user_{i}", f"User {i}", f"user{i}@example.com") for i in range(n_rows)],
    )
    conn.commit()


def run_migration(conn):
    """Rename full_name → display_name using naive table-rebuild approach.

    PROBLEMATIC: Rebuilds entire table with exclusive lock.
    Should use expand-contract pattern instead:
    1. ADD COLUMN display_name (fast)
    2. UPDATE in batches, copying full_name → display_name
    3. Verify backfill complete
    4. Update app to write both columns (dual-write)
    5. Cut over reads to new column
    6. DROP old column in separate migration
    """
    start = time.time()
    # PROBLEMATIC: full table reconstruction — exclusive lock
    conn.execute(f"""
        CREATE TABLE users_new AS
        SELECT id, username, full_name AS display_name, email, created_at
        FROM users
    """)
    conn.execute(f"DROP TABLE users")
    conn.execute(f"ALTER TABLE users_new RENAME TO users")
    conn.commit()
    elapsed = time.time() - start
    print(f"Migration completed in {elapsed:.3f}s")
    return elapsed


def get_migration_status(conn) -> dict:
    cols = [row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()]
    return {
        "has_display_name": "display_name" in cols,
        "has_old_column": "full_name" in cols,
        "columns": cols,
        "row_count": conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
    }


if __name__ == "__main__":
    conn = sqlite3.connect(DB)
    seed_data(conn)
    run_migration(conn)
    status = get_migration_status(conn)
    print(f"Status: {status}")
    conn.close()
