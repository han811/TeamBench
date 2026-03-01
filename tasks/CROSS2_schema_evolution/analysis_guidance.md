# Analysis Guidance — CROSS2_schema_evolution

## Tools to run
- `cat service_a/migrations/002_add_columns.py` — CRITICAL: shows all schema changes
- `cat service_a/config.py` — read default values for backfill
- `cat shared/schema.sql` — expected final schema
- `cat service_b/models.py` — compare with migration to find staleness
- `grep -n "SELECT \*" service_b/queries.py` — find unsafe queries

## Key Findings

### Schema changes (from migration 002):
1. Column RENAMED: `user_name` → `username` (breaking change)
2. Column ADDED: `email_verified` (boolean, default: False)
3. Column ADDED: `last_login_at` (datetime, default: None)
4. Column ADDED: `account_tier` (string, default: from config DEFAULT_TIER)

### Service B staleness:
- `service_b/models.py` `User` class still has `user_name` attribute (wrong)
- `service_b/models.py` missing `email_verified`, `last_login_at`, `account_tier` fields
- `service_b/queries.py` has 2 queries using `SELECT *` — will break with new columns

### Backfill defaults (from service_a/config.py):
- `email_verified`: False
- `last_login_at`: None
- `account_tier`: `DEFAULT_TIER` constant (read its value from config.py)

## Tell Executor
1. In `service_b/models.py`: rename `user_name` → `username`, add 3 new fields
2. In `service_b/queries.py`: replace both `SELECT *` with explicit column lists
3. In `scripts/backfill.py`: UPDATE all existing rows setting the 3 new columns to defaults
