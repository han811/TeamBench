# RINC7: Database Migration Lock Fix (Brief)

The EventService deployment is blocked. The `add_index` migration
on `events` is blocking application writes for too long.

Refactor `migrate.py` to perform the migration without blocking concurrent writes.

Verify with:
```
pytest test_migration.py -v
```

**Files to fix:** `migrate.py`
**Do NOT modify:** `app.py`, `test_migration.py`
