# DIST4: Lamport Clock Bugs (Brief)

Fix 3 Lamport clock bugs per the Planner's analysis: send-before-increment,
max-plus-one on receive, and deterministic tie-breaking.

Do NOT modify `eventlog/vector_clock.py` — it is correct.

Run `pytest tests/` to verify.
