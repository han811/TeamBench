# RINC6: Cascading Failure Fix (Brief)

The payments service stack is experiencing availability issues.
When the `fraud_check` service goes down, the entire
checkout → payment processor → fraud check chain stops responding.

Implement the circuit breaker in `circuit_breaker.py` to stop the cascade.

Verify with:
```
pytest test_cascade.py -v
```

**Files to fix:** `circuit_breaker.py`
**Do NOT modify:** `services.py`, `test_cascade.py`
