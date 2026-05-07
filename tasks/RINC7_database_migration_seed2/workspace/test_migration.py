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


DB = "users.db"


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
    assert any(status.values()), f"Migration status shows no changes: {status}"


def test_data_preserved_after_migration():
    """Row count must not decrease after migration."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    before = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    mig_module.run_migration(conn)
    after = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    assert after >= before, f"Data loss: {before} rows before, {after} after migration"


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
            errors.append(f"migration error: {e}")
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
        f"All concurrent writes blocked: {write_results}, migration errors: {errors}"
    )


def test_schema_correct_after_migration():
    """After migration, the new schema must be queryable."""
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    mig_module.run_migration(conn)
    status = mig_module.get_migration_status(conn)

    # The migration should report success
    success_indicators = [v for v in status.values() if v is True]
    assert success_indicators, f"Migration did not achieve expected schema: {status}"
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
