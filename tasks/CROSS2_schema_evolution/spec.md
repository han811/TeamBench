# CROSS2: Schema Evolution — Cross-Service Compatibility

## Goal
Service A has been updated with a database migration that modifies the shared schema.
Update Service B to work with the new schema without breaking either service.

## Requirements
1. Update `service_b/models.py` to match the new schema (see `service_a/migrations/002_add_columns.py`)
2. Fix `service_b/queries.py` to use explicit column names (no `SELECT *`)
3. Implement `scripts/backfill.py` to populate new columns for existing records
4. Use default values from `service_a/config.py` for the backfill
5. All tests must pass: `pytest tests/`

## Supporting Documents
- `service_a/migrations/002_add_columns.py` — The migration that changed the schema
- `service_a/config.py` — Default values for new columns
- `shared/schema.sql` — Expected final schema (source of truth)
- `service_b/models.py` — Stale ORM models (need updating)
- `service_b/queries.py` — Contains SELECT * (needs fixing)

## Important
The migration renames one column and adds three new columns. Service B must be updated
to use the new column names. The backfill script must use exact default values from
Service A's config — do not invent values.
