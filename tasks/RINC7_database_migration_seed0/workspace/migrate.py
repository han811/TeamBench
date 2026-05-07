"""
Migration: Add fulfillment_status column to orders.

PROBLEM: This naive ALTER TABLE with DEFAULT acquires a write lock
for the entire table while SQLite rebuilds it. For large tables,
this blocks all writes for seconds to minutes.

Incident: GitHub MySQL migration (2012) — ALTER TABLE locked table for hours.
"""
import sqlite3
import time


DB = "app.db"


def seed_data(conn, n_rows: int = 11890):
    """Create and populate the orders table."""
    conn.execute("DROP TABLE IF EXISTS orders")
    conn.execute("""
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.executemany(
        "INSERT INTO orders (customer_id, amount) VALUES (?, ?)",
        [(i % 1000, round(10.0 + i * 0.01, 2)) for i in range(n_rows)],
    )
    conn.commit()


def run_migration(conn):
    """Run the migration to add fulfillment_status column.

    VULNERABLE: ALTER TABLE with DEFAULT in SQLite reconstructs the entire table,
    holding an exclusive lock throughout. Concurrent writes fail.

    This should be refactored to:
    1. ADD COLUMN without DEFAULT (fast, no lock)
    2. UPDATE in batches (releases lock between batches)
    3. Handle default at application level
    """
    start = time.time()
    # PROBLEMATIC: single ALTER TABLE with DEFAULT — full table lock
    conn.execute("ALTER TABLE orders ADD COLUMN fulfillment_status TEXT DEFAULT 'pending'")
    conn.commit()
    elapsed = time.time() - start
    print(f"Migration completed in {elapsed:.3f}s")
    return elapsed


def get_migration_status(conn) -> dict:
    """Check migration completion status."""
    cols = [row[1] for row in conn.execute("PRAGMA table_info(orders)").fetchall()]
    has_new_col = "fulfillment_status" in cols
    if has_new_col:
        null_count = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE fulfillment_status IS NULL"
        ).fetchone()[0]
    else:
        null_count = -1
    return {
        "has_fulfillment_status": has_new_col,
        "null_count": null_count,
        "columns": cols,
    }


if __name__ == "__main__":
    conn = sqlite3.connect(DB)
    seed_data(conn)
    run_migration(conn)
    status = get_migration_status(conn)
    print(f"Status: {status}")
    conn.close()
