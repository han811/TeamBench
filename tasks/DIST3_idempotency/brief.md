# DIST3: Payment Idempotency (Brief)

Add idempotency to 4 payment operations to prevent double-charges on retry.
The Planner has identified which operations need idempotency and how to implement
the deduplication store.

Do NOT modify `payments/balance.py` — it is already idempotent.

Implement `payments/idempotency.py` and update the 4 non-idempotent modules.

Run `pytest tests/` to verify.
