# RINC7: Database Migration Table Lock

## Incident Background
Inspired by GitHub's MySQL migration incident (2012) and similar events at
Shopify and Stack Overflow. A long-running ALTER TABLE acquired an exclusive
metadata lock, blocking all writes to the table for the entire migration
duration. For a 14,325-row table, this caused minutes of write downtime.

## System: EventService
Database: `events.db` | Table: `events` | Rows: 14,325
Migration type: `add_index`

## Problem
`migrate.py` — `run_migration()` function
CREATE INDEX without CONCURRENT holds write lock for full index build duration

The application (`app.py`) tries to write to `events` concurrently.
Without a non-blocking migration approach, writes are blocked for the full
duration of the migration.

## Required Fix
Use CREATE INDEX CONCURRENTLY (PostgreSQL) or run index creation during low-traffic window with lock timeout

Key principles:
1. Never hold an exclusive lock for longer than necessary
2. Use batched operations with `LIMIT 100` to yield locks between batches
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
