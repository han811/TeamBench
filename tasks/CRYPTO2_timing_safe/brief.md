# CRYPTO2: Timing-Safe Comparisons (Brief)

Replace timing-unsafe `==` comparisons with constant-time equivalents in the auth system.
The Planner has identified exactly which 4 comparisons need fixing and which 1 must
NOT be changed.

Run `pytest tests/` to verify all tests pass.
