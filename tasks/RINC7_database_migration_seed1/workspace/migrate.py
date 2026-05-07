"""
Migration: Add index on events.event_type.

PROBLEM: CREATE INDEX without CONCURRENTLY (PostgreSQL) or during
high-traffic period holds a table read lock for the full build duration.

Incident: Caused write stalls at multiple companies during peak traffic.
"""
import sqlite3
import time


DB = "events.db"


def seed_data(conn, n_rows: int = 14325):
    """Create and populate the events table."""
    conn.execute("DROP TABLE IF EXISTS events")
    conn.execute("""
        CREATE TABLE events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            payload TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    event_types = ["click", "view", "purchase", "error", "login"]
    conn.executemany(
        "INSERT INTO events (event_type, payload) VALUES (?, ?)",
        [(event_types[i % len(event_types)], f"data_{i}") for i in range(n_rows)],
    )
    conn.commit()


def run_migration(conn):
    """Create index on event_type.

    PROBLEMATIC: In production PostgreSQL this should use CREATE INDEX CONCURRENTLY.
    SQLite always builds indexes synchronously; this simulates the blocking pattern.
    The fix is to add a lock_timeout and use CONCURRENT DDL where available.
    """
    start = time.time()
    # PROBLEMATIC: no CONCURRENT, no lock timeout — blocks writes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type)")
    conn.commit()
    elapsed = time.time() - start
    print(f"Index created in {elapsed:.3f}s")
    return elapsed


def get_migration_status(conn) -> dict:
    """Check if index was created."""
    indexes = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='events'"
    ).fetchall()
    index_names = [r[0] for r in indexes]
    return {
        "index_created": "idx_events_event_type" in index_names,
        "indexes": index_names,
    }


if __name__ == "__main__":
    conn = sqlite3.connect(DB)
    seed_data(conn)
    run_migration(conn)
    status = get_migration_status(conn)
    print(f"Status: {status}")
    conn.close()
