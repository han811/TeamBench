# RINC6: Cascading Failure Fix (Brief)

The e-commerce service stack is experiencing availability issues.
When the `pricing` service goes down, the entire
product catalog → inventory → pricing service chain stops responding.

Implement the circuit breaker in `circuit_breaker.py` to stop the cascade.

Verify with:
```
pytest test_cascade.py -v
```

**Files to fix:** `circuit_breaker.py`
**Do NOT modify:** `services.py`, `test_cascade.py`
