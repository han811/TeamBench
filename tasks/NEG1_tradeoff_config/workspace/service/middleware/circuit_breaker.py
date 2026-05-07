"""Circuit breaker for external service calls — with retry and backoff."""
import time
import random


# Simulated external service
def _external_service(data):
    """Simulate an external service call."""
    # Force failure when trigger_fail is set
    if data.get("trigger_fail"):
        raise ConnectionError("External service unavailable")
    # Randomly fail ~10% of the time
    if random.random() < 0.1:
        raise ConnectionError("External service unavailable")
    time.sleep(0.01)  # 10ms latency
    return {"processed": True, "input_hash": hash(str(data))}


class CircuitBreaker:
    """Circuit breaker implementation.

    States:
      - closed: normal operation, requests pass through
      - open: failing, requests rejected immediately
      - half-open: testing recovery, one probe request allowed
    """

    def __init__(self, failure_threshold=3, recovery_timeout=10):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"

    def call(self, func, *args, **kwargs):
        if self.state == "open":
            elapsed = time.time() - self.last_failure_time
            if elapsed >= self.recovery_timeout:
                self.state = "half-open"
            else:
                raise Exception("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)
            # Success: reset
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
            else:
                self.failure_count = 0
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = "open"
            raise


# Module-level circuit breaker instance (shared across all calls)
_circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=10)


def _call_with_retry(func, data, max_retries=3, base_delay=0.1):
    """Call func with exponential backoff retry."""
    for attempt in range(max_retries + 1):
        try:
            return _circuit_breaker.call(func, data)
        except Exception as e:
            if "Circuit breaker is open" in str(e):
                raise
            if attempt == max_retries:
                raise
            delay = base_delay * (2 ** attempt)  # 100ms, 200ms, 400ms
            time.sleep(delay)


def call_external_service(data):
    """Call external service with circuit breaker and retry logic.
    
    Raises exceptions on failure so callers can detect circuit breaker state.
    Returns a dict on success.
    """
    return _call_with_retry(_external_service, data)
