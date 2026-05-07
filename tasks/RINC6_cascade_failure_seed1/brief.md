# RINC6: Cascading Failure Fix (Brief)

The analytics service stack is experiencing availability issues.
When the `collector` service goes down, the entire
dashboard → metrics → collector chain stops responding.

Implement the circuit breaker in `circuit_breaker.py` to stop the cascade.

Verify with:
```
pytest test_cascade.py -v
```

**Files to fix:** `circuit_breaker.py`
**Do NOT modify:** `services.py`, `test_cascade.py`
