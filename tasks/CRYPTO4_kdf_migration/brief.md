# CRYPTO4: Password Migration (Brief)

Migrate password hashing to Argon2id with backward compatibility.
The Planner has identified 2 bugs in the migration path and the hex-salt edge case.

Follow the Planner's analysis precisely — the format marker bug causes ALL users
to fail login after their first post-migration login.

Run `pytest tests/` to verify all formats work.
