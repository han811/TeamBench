# RINC6: Cascading Failure — Circuit Breaker Missing

## Incident Background
Inspired by the AWS S3 us-east-1 outage (February 28, 2017). A small
operational error cascaded because dependent services had no isolation
mechanisms. Services kept retrying failed upstream calls, exhausting
connection pools and thread pools, amplifying the outage.

## System: Payments (checkout → payment processor → fraud check chain)
Service chain: `checkout → payment_processor → fraud_check`

## Problem
The `fraud_check` service starts failing after 2 successful calls.
Because there are no circuit breakers, `checkout` keeps retrying
through the full chain, hanging for 1s per call and propagating exceptions.

**Files:**
- `circuit_breaker.py` — stub with unimplemented `call()` method
- `services.py` — microservice chain that uses the circuit breaker

## Required Fix: Implement `CircuitBreaker.call()`

The `call()` method must:
1. If circuit is **OPEN** → return `fallback` immediately (no upstream call)
2. If circuit is **CLOSED** or **HALF_OPEN** → call `func(*args, **kwargs)`
3. On success → `_on_success()` (reset failure count, close circuit)
4. On exception → `_on_failure()` (increment count, open if threshold reached)
5. After `recovery_timeout` seconds in OPEN state → transition to HALF_OPEN

```python
def call(self, func, *args, fallback=None, **kwargs):
    with self._lock:
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                return fallback
    try:
        result = func(*args, **kwargs)
        self._on_success()
        return result
    except Exception:
        self._on_failure()
        return fallback
```

## Acceptance Criteria
1. Circuit opens after `failure_threshold=3` consecutive failures
2. Open circuit returns fallback without calling upstream
3. `checkout` returns fallback data instead of raising after circuit opens
4. Closed circuit still passes calls through (no regression)
5. Circuit recovers after `recovery_timeout` seconds
6. All tests pass: `pytest test_cascade.py -v`

## Files
- `circuit_breaker.py` — implement `CircuitBreaker.call()`
- `services.py` — do NOT modify
- `test_cascade.py` — do NOT modify
