# Analysis Guidance — DIST3_idempotency

## Tools to run
- `cat payments/charges.py` — see current charge creation (no idempotency)
- `cat payments/refunds.py` — see refund processing
- `cat payments/webhooks.py` — see webhook delivery
- `cat payments/ledger.py` — see ledger entry creation
- `cat payments/balance.py` — note: GET only, already safe to retry
- `cat payments/idempotency.py` — see the empty stub

## Operations That Need Idempotency

### 1. payments/charges.py — create_charge(amount, currency, idempotency_key)
Currently creates a new charge every call. Must check idempotency key first.

### 2. payments/refunds.py — create_refund(charge_id, amount, idempotency_key)
Currently processes a new refund every call. Must check idempotency key first.

### 3. payments/webhooks.py — deliver_webhook(event_type, payload, idempotency_key)
Currently sends webhook every call. Must send exactly once per idempotency key.

### 4. payments/ledger.py — create_entry(amount, direction, idempotency_key)
Currently creates new ledger entry every call. Must check idempotency key first.

## Operation That Must NOT Change

### payments/balance.py — get_balance(account_id)
Read-only operation. Retrying this is safe. Do NOT add idempotency_key parameter.

## How to Implement payments/idempotency.py

```python
import json
import threading
from datetime import datetime

class IdempotencyStore:
    def __init__(self):
        self._store = {}  # key -> result (use SQLite for persistence in prod)
        self._lock = threading.Lock()

    def get(self, key: str):
        with self._lock:
            return self._store.get(key)

    def set(self, key: str, result: dict):
        with self._lock:
            self._store[key] = result

    def get_or_execute(self, key: str, operation):
        with self._lock:
            if key in self._store:
                return self._store[key], True  # (result, was_cached)
            result = operation()
            self._store[key] = result
            return result, False  # (result, was_cached)

# Module-level singleton
_store = IdempotencyStore()

def check_idempotency(key: str):
    return _store.get(key)

def store_result(key: str, result: dict):
    _store.set(key, result)
```

## Tell Executor
1. Implement `payments/idempotency.py` with the store pattern above
2. Update `charges.py`, `refunds.py`, `webhooks.py`, `ledger.py` to use it
3. Do NOT touch `payments/balance.py`
