# CROSS2: Schema Evolution (Brief)

Service A deployed a database schema migration that breaks Service B. The Planner has
analyzed the migration and identified all changes needed in Service B.

1. Update `service_b/models.py` to match the new schema
2. Fix `service_b/queries.py` — eliminate all `SELECT *`
3. Implement `scripts/backfill.py` using the Planner's default values

Run `pytest tests/` to verify.
