"""
EventService: Application that writes to events during migration.

This module simulates concurrent application writes that should not be
blocked by the migration script.
"""
import sqlite3
import threading


DB = "events.db"


def write_record(conn, data: dict) -> int:
    """Write a record to events. Must succeed even during migration."""
    cursor = conn.execute(
        "INSERT INTO events (event_type, payload) VALUES (?, ?)",
        tuple(data.values()),
    )
    conn.commit()
    return cursor.lastrowid


def read_records(conn, limit: int = 10) -> list:
    """Read recent records from events."""
    rows = conn.execute(
        "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def concurrent_write_test(db_path: str, n_writes: int = 20) -> dict:
    """Attempt concurrent writes, return success/failure counts."""
    results = {"success": 0, "failed": 0, "errors": []}
    lock = threading.Lock()

    def do_write(i):
        try:
            conn = sqlite3.connect(db_path, timeout=2.0)
            conn.row_factory = sqlite3.Row
            write_record(conn, {"customer_id": i, "amount": float(i)})
            conn.close()
            with lock:
                results["success"] += 1
        except Exception as e:
            with lock:
                results["failed"] += 1
                results["errors"].append(str(e))

    threads = [threading.Thread(target=do_write, args=(i,)) for i in range(n_writes)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results
