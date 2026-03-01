# DIST3: Payment Service Idempotency

## Goal
Make 4 payment operations safe to retry by implementing idempotency key deduplication.

## Requirements
1. Charge creation must be idempotent: same `idempotency_key` returns same charge result
2. Refund processing must be idempotent: same key returns same refund result
3. Webhook delivery must be idempotent: same key sends webhook exactly once
4. Ledger entry creation must be idempotent: same key creates entry exactly once
5. The balance query endpoint must NOT be modified (it is already safe to retry)
6. Implement the idempotency store in `payments/idempotency.py`
7. All tests must pass: `pytest tests/`

## Supporting Documents
- `payments/charges.py` — Charge creation (not idempotent)
- `payments/refunds.py` — Refund processing (not idempotent)
- `payments/webhooks.py` — Webhook delivery (not idempotent)
- `payments/ledger.py` — Ledger entries (not idempotent)
- `payments/balance.py` — Balance query (ALREADY IDEMPOTENT — do not change)
- `payments/idempotency.py` — Empty stub — implement this

## Idempotency Key Pattern
Each operation receives an `idempotency_key: str` parameter. Before executing:
1. Check if `idempotency_key` exists in the dedup table
2. If yes: return the cached result from the first execution
3. If no: execute the operation, store the result with the key, return result

The idempotency key is set by the caller. Operations must never execute twice for the same key.
