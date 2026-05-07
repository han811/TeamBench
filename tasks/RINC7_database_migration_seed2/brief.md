# RINC7: Database Migration Lock Fix (Brief)

The UserService deployment is blocked. The `rename_column` migration
on `users` is blocking application writes for too long.

Refactor `migrate.py` to perform the migration without blocking concurrent writes.

Verify with:
```
pytest test_migration.py -v
```

**Files to fix:** `migrate.py`
**Do NOT modify:** `app.py`, `test_migration.py`
