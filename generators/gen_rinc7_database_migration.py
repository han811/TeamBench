"""
Parameterized generator for RINC7: Database Migration Table Lock.

Inspiration: GitHub's MySQL migration incident (2012) — a long-running
ALTER TABLE on a large table held a metadata lock, blocking all writes
to the table for hours. Also patterns from Shopify, Stack Overflow.

Workspace has a migration script that does a naive ALTER TABLE (or
equivalent) that locks the table, plus an app that tries to write to
it during migration. Fix: use online DDL, batched migration, or shadow
table approach.

Seeds vary: DB backend (SQLite/PostgreSQL pattern), table name, migration
type (add column / add index / change column type).

Grading: 7 checks — migration completes, writes not blocked, data
integrity preserved, index actually created, app reads still work.
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

MIGRATION_VARIANTS = [
    {
        "migration_type": "add_column",
        "table": "orders",
        "db_file": "app.db",
        "new_column": "fulfillment_status",
        "new_col_type": "TEXT DEFAULT 'pending'",
        "problem": "ALTER TABLE ... ADD COLUMN with DEFAULT acquires exclusive lock in old SQLite",
        "fix": "Use a multi-step migration: ADD COLUMN without DEFAULT, then UPDATE in batches, then set default via app",
        "app_operation": "INSERT INTO orders (customer_id, amount) VALUES (?, ?)",
        "service": "OrderService",
    },
    {
        "migration_type": "add_index",
        "table": "events",
        "db_file": "events.db",
        "new_column": "event_type",
        "new_col_type": "TEXT",
        "problem": "CREATE INDEX without CONCURRENT holds write lock for full index build duration",
        "fix": "Use CREATE INDEX CONCURRENTLY (PostgreSQL) or run index creation during low-traffic window with lock timeout",
        "app_operation": "INSERT INTO events (event_type, payload) VALUES (?, ?)",
        "service": "EventService",
    },
    {
        "migration_type": "rename_column",
        "table": "users",
        "db_file": "users.db",
        "new_column": "display_name",
        "new_col_type": "TEXT",
        "problem": "Direct column rename blocks all concurrent reads/writes in SQLite (requires table rebuild)",
        "fix": "Use expand-contract pattern: add new column, dual-write, backfill, cut over, drop old column",
        "app_operation": "INSERT INTO users (username, email) VALUES (?, ?)",
        "service": "UserService",
    },
]


class Generator(TaskGenerator):
    task_id = "RINC7_database_migration"
    domain = "incident"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        v = MIGRATION_VARIANTS[seed % len(MIGRATION_VARIANTS)]
        batch_size = rng.choice([100, 500, 1000])
        n_rows = rng.randint(5000, 15000)

        workspace_files = {
            "migrate.py": self._gen_migrate(v, n_rows),
            "app.py": self._gen_app(v),
            "test_migration.py": self._gen_tests(v, n_rows, batch_size),
            "requirements.txt": "pytest>=7.0\n",
        }

        expected = {
            "seed": seed,
            "migration_type": v["migration_type"],
            "table": v["table"],
            "fix": v["fix"],
            "batch_size": batch_size,
            "n_rows": n_rows,
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._gen_spec(v, n_rows, batch_size),
            brief_md=self._gen_brief(v),
            expected=expected,
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "incident", "incident": "GitHub-MySQL-2012"},
        )

    def _gen_migrate(self, v: dict, n_rows: int) -> str:
        if v["migration_type"] == "add_column":
            return self._gen_add_column_migrate(v, n_rows)
        elif v["migration_type"] == "add_index":
            return self._gen_add_index_migrate(v, n_rows)
        else:
            return self._gen_rename_column_migrate(v, n_rows)

    def _gen_add_column_migrate(self, v: dict, n_rows: int) -> str:
        return f'''\
"""
Migration: Add {v["new_column"]} column to {v["table"]}.

PROBLEM: This naive ALTER TABLE with DEFAULT acquires a write lock
for the entire table while SQLite rebuilds it. For large tables,
this blocks all writes for seconds to minutes.

Incident: GitHub MySQL migration (2012) — ALTER TABLE locked table for hours.
"""
import sqlite3
import time


DB = "{v["db_file"]}"


def seed_data(conn, n_rows: int = {n_rows}):
    """Create and populate the {v["table"]} table."""
    conn.execute("DROP TABLE IF EXISTS {v["table"]}")
    conn.execute("""
        CREATE TABLE {v["table"]} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.executemany(
        "INSERT INTO {v["table"]} (customer_id, amount) VALUES (?, ?)",
        [(i % 1000, round(10.0 + i * 0.01, 2)) for i in range(n_rows)],
    )
    conn.commit()


def run_migration(conn):
    """Run the migration to add {v["new_column"]} column.

    VULNERABLE: ALTER TABLE with DEFAULT in SQLite reconstructs the entire table,
    holding an exclusive lock throughout. Concurrent writes fail.

    This should be refactored to:
    1. ADD COLUMN without DEFAULT (fast, no lock)
    2. UPDATE in batches (releases lock between batches)
    3. Handle default at application level
    """
    start = time.time()
    # PROBLEMATIC: single ALTER TABLE with DEFAULT — full table lock
    conn.execute("ALTER TABLE {v["table"]} ADD COLUMN {v["new_column"]} {v["new_col_type"]}")
    conn.commit()
    elapsed = time.time() - start
    print(f"Migration completed in {{elapsed:.3f}}s")
    return elapsed


def get_migration_status(conn) -> dict:
    """Check migration completion status."""
    cols = [row[1] for row in conn.execute("PRAGMA table_info({v["table"]})").fetchall()]
    has_new_col = "{v["new_column"]}" in cols
    if has_new_col:
        null_count = conn.execute(
            "SELECT COUNT(*) FROM {v["table"]} WHERE {v["new_column"]} IS NULL"
        ).fetchone()[0]
    else:
        null_count = -1
    return {{
        "has_{v["new_column"]}": has_new_col,
        "null_count": null_count,
        "columns": cols,
    }}


if __name__ == "__main__":
    conn = sqlite3.connect(DB)
    seed_data(conn)
    run_migration(conn)
    status = get_migration_status(conn)
    print(f"Status: {{status}}")
    conn.close()
'''

    def _gen_add_index_migrate(self, v: dict, n_rows: int) -> str:
        return f'''\
"""
Migration: Add index on {v["table"]}.{v["new_column"]}.

PROBLEM: CREATE INDEX without CONCURRENTLY (PostgreSQL) or during
high-traffic period holds a table read lock for the full build duration.

Incident: Caused write stalls at multiple companies during peak traffic.
"""
import sqlite3
import time


DB = "{v["db_file"]}"


def seed_data(conn, n_rows: int = {n_rows}):
    """Create and populate the {v["table"]} table."""
    conn.execute("DROP TABLE IF EXISTS {v["table"]}")
    conn.execute("""
        CREATE TABLE {v["table"]} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            {v["new_column"]} TEXT NOT NULL,
            payload TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    event_types = ["click", "view", "purchase", "error", "login"]
    conn.executemany(
        "INSERT INTO {v["table"]} ({v["new_column"]}, payload) VALUES (?, ?)",
        [(event_types[i % len(event_types)], f"data_{{i}}") for i in range(n_rows)],
    )
    conn.commit()


def run_migration(conn):
    """Create index on {v["new_column"]}.

    PROBLEMATIC: In production PostgreSQL this should use CREATE INDEX CONCURRENTLY.
    SQLite always builds indexes synchronously; this simulates the blocking pattern.
    The fix is to add a lock_timeout and use CONCURRENT DDL where available.
    """
    start = time.time()
    # PROBLEMATIC: no CONCURRENT, no lock timeout — blocks writes
    conn.execute("CREATE INDEX IF NOT EXISTS idx_{v["table"]}_{v["new_column"]} ON {v["table"]}({v["new_column"]})")
    conn.commit()
    elapsed = time.time() - start
    print(f"Index created in {{elapsed:.3f}}s")
    return elapsed


def get_migration_status(conn) -> dict:
    """Check if index was created."""
    indexes = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='{v["table"]}'"
    ).fetchall()
    index_names = [r[0] for r in indexes]
    return {{
        "index_created": "idx_{v["table"]}_{v["new_column"]}" in index_names,
        "indexes": index_names,
    }}


if __name__ == "__main__":
    conn = sqlite3.connect(DB)
    seed_data(conn)
    run_migration(conn)
    status = get_migration_status(conn)
    print(f"Status: {{status}}")
    conn.close()
'''

    def _gen_rename_column_migrate(self, v: dict, n_rows: int) -> str:
        return f'''\
"""
Migration: Rename column in {v["table"]} using expand-contract pattern.

PROBLEM: SQLite doesn't support ALTER TABLE RENAME COLUMN in old versions.
The naive approach (CREATE new table, copy, drop old) holds an exclusive
lock for the full duration. PostgreSQL's RENAME COLUMN is faster but still
blocks concurrent writes.

Fix: expand-contract — add new column, dual-write, backfill, cut over.
"""
import sqlite3
import time


DB = "{v["db_file"]}"
OLD_COLUMN = "full_name"
NEW_COLUMN = "{v["new_column"]}"


def seed_data(conn, n_rows: int = {n_rows}):
    """Create and populate the {v["table"]} table."""
    conn.execute("DROP TABLE IF EXISTS {v["table"]}")
    conn.execute("""
        CREATE TABLE {v["table"]} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            full_name TEXT,
            email TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.executemany(
        "INSERT INTO {v["table"]} (username, full_name, email) VALUES (?, ?, ?)",
        [(f"user_{{i}}", f"User {{i}}", f"user{{i}}@example.com") for i in range(n_rows)],
    )
    conn.commit()


def run_migration(conn):
    """Rename full_name → {v["new_column"]} using naive table-rebuild approach.

    PROBLEMATIC: Rebuilds entire table with exclusive lock.
    Should use expand-contract pattern instead:
    1. ADD COLUMN {v["new_column"]} (fast)
    2. UPDATE in batches, copying full_name → {v["new_column"]}
    3. Verify backfill complete
    4. Update app to write both columns (dual-write)
    5. Cut over reads to new column
    6. DROP old column in separate migration
    """
    start = time.time()
    # PROBLEMATIC: full table reconstruction — exclusive lock
    conn.execute(f"""
        CREATE TABLE {v["table"]}_new AS
        SELECT id, username, full_name AS {v["new_column"]}, email, created_at
        FROM {v["table"]}
    """)
    conn.execute(f"DROP TABLE {v["table"]}")
    conn.execute(f"ALTER TABLE {v["table"]}_new RENAME TO {v["table"]}")
    conn.commit()
    elapsed = time.time() - start
    print(f"Migration completed in {{elapsed:.3f}}s")
    return elapsed


def get_migration_status(conn) -> dict:
    cols = [row[1] for row in conn.execute("PRAGMA table_info({v["table"]})").fetchall()]
    return {{
        "has_{v["new_column"]}": "{v["new_column"]}" in cols,
        "has_old_column": "full_name" in cols,
        "columns": cols,
        "row_count": conn.execute("SELECT COUNT(*) FROM {v["table"]}").fetchone()[0],
    }}


if __name__ == "__main__":
    conn = sqlite3.connect(DB)
    seed_data(conn)
    run_migration(conn)
    status = get_migration_status(conn)
    print(f"Status: {{status}}")
    conn.close()
'''

    def _gen_app(self, v: dict) -> str:
        return f'''\
"""
{v["service"]}: Application that writes to {v["table"]} during migration.

This module simulates concurrent application writes that should not be
blocked by the migration script.
"""
import sqlite3
import threading


DB = "{v["db_file"]}"


def write_record(conn, data: dict) -> int:
    """Write a record to {v["table"]}. Must succeed even during migration."""
    cursor = conn.execute(
        "{v["app_operation"]}",
        tuple(data.values()),
    )
    conn.commit()
    return cursor.lastrowid


def read_records(conn, limit: int = 10) -> list:
    """Read recent records from {v["table"]}."""
    rows = conn.execute(
        "SELECT * FROM {v["table"]} ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [dict(r) for r in rows]


def concurrent_write_test(db_path: str, n_writes: int = 20) -> dict:
    """Attempt concurrent writes, return success/failure counts."""
    results = {{"success": 0, "failed": 0, "errors": []}}
    lock = threading.Lock()

    def do_write(i):
        try:
            conn = sqlite3.connect(db_path, timeout=2.0)
            conn.row_factory = sqlite3.Row
            write_record(conn, {{"customer_id": i, "amount": float(i)}})
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
'''

    def _gen_tests(self, v: dict, n_rows: int, batch_size: int) -> str:
        return f'''\
"""
Database migration safety tests.

Tests verify that:
1. Migration completes without data loss
2. Application writes are not blocked
3. The new schema is correct after migration
"""
import sqlite3
import threading
import time
import os
import pytest
import migrate as mig_module
import app as app_module


DB = "{v["db_file"]}"


@pytest.fixture(autouse=True)
def fresh_db():
    if os.path.exists(DB):
        os.remove(DB)
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    mig_module.seed_data(conn, n_rows=100)  # small for tests
    conn.close()
    yield
    if os.path.exists(DB):
        os.remove(DB)


def test_migration_completes():
    """Migration must complete without raising an exception."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    mig_module.run_migration(conn)
    status = mig_module.get_migration_status(conn)
    conn.close()
    # Verify migration achieved its goal
    assert any(status.values()), f"Migration status shows no changes: {{status}}"


def test_data_preserved_after_migration():
    """Row count must not decrease after migration."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    before = conn.execute("SELECT COUNT(*) FROM {v["table"]}").fetchone()[0]
    mig_module.run_migration(conn)
    after = conn.execute("SELECT COUNT(*) FROM {v["table"]}").fetchone()[0]
    conn.close()
    assert after >= before, f"Data loss: {{before}} rows before, {{after}} after migration"


def test_concurrent_writes_not_blocked():
    """Application writes should succeed during or after migration."""
    errors = []
    migration_done = threading.Event()

    def run_migration():
        conn = sqlite3.connect(DB, timeout=5.0)
        conn.row_factory = sqlite3.Row
        try:
            mig_module.run_migration(conn)
        except Exception as e:
            errors.append(f"migration error: {{e}}")
        finally:
            conn.close()
            migration_done.set()

    mig_thread = threading.Thread(target=run_migration)
    mig_thread.start()

    # Attempt writes concurrently with migration
    write_results = app_module.concurrent_write_test(DB, n_writes=10)
    mig_thread.join()

    # Some writes may fail during migration, but not all of them
    assert write_results["success"] > 0 or len(errors) == 0, (
        f"All concurrent writes blocked: {{write_results}}, migration errors: {{errors}}"
    )


def test_schema_correct_after_migration():
    """After migration, the new schema must be queryable."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    mig_module.run_migration(conn)
    status = mig_module.get_migration_status(conn)

    # The migration should report success
    success_indicators = [v for v in status.values() if v is True]
    assert success_indicators, f"Migration did not achieve expected schema: {{status}}"
    conn.close()


def test_app_reads_work_after_migration():
    """Application reads must work correctly after migration completes."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    mig_module.run_migration(conn)
    conn.close()

    read_conn = sqlite3.connect(DB)
    read_conn.row_factory = sqlite3.Row
    rows = app_module.read_records(read_conn)
    read_conn.close()
    assert isinstance(rows, list)
    assert len(rows) > 0
'''

    def _gen_spec(self, v: dict, n_rows: int, batch_size: int) -> str:
        return f"""# RINC7: Database Migration Table Lock

## Incident Background
Inspired by GitHub's MySQL migration incident (2012) and similar events at
Shopify and Stack Overflow. A long-running ALTER TABLE acquired an exclusive
metadata lock, blocking all writes to the table for the entire migration
duration. For a {n_rows:,}-row table, this caused minutes of write downtime.

## System: {v["service"]}
Database: `{v["db_file"]}` | Table: `{v["table"]}` | Rows: {n_rows:,}
Migration type: `{v["migration_type"]}`

## Problem
`migrate.py` — `run_migration()` function
{v["problem"]}

The application (`app.py`) tries to write to `{v["table"]}` concurrently.
Without a non-blocking migration approach, writes are blocked for the full
duration of the migration.

## Required Fix
{v["fix"]}

Key principles:
1. Never hold an exclusive lock for longer than necessary
2. Use batched operations with `LIMIT {batch_size}` to yield locks between batches
3. Prefer additive changes (ADD COLUMN) over reconstructive ones (table rebuild)
4. Use `BEGIN`/`COMMIT` at batch boundaries, not around the full migration

## Acceptance Criteria
1. Migration completes without raising exceptions
2. Row count preserved after migration (no data loss)
3. Application writes succeed concurrently (not all blocked)
4. New schema is queryable after migration
5. Application reads return correct data post-migration
6. All tests pass: `pytest test_migration.py -v`

## Files
- `migrate.py` — refactor `run_migration()` to use non-blocking approach
- `app.py` — do NOT modify
- `test_migration.py` — do NOT modify
"""

    def _gen_brief(self, v: dict) -> str:
        return f"""# RINC7: Database Migration Lock Fix (Brief)

The {v["service"]} deployment is blocked. The `{v["migration_type"]}` migration
on `{v["table"]}` is blocking application writes for too long.

Refactor `migrate.py` to perform the migration without blocking concurrent writes.

Verify with:
```
pytest test_migration.py -v
```

**Files to fix:** `migrate.py`
**Do NOT modify:** `app.py`, `test_migration.py`
"""
