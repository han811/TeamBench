"""
Circuit breaker implementation.

A circuit breaker has 3 states:
  CLOSED   — normal operation, requests pass through
  OPEN     — too many failures, requests fail fast (fallback returned)
  HALF_OPEN — testing if upstream recovered

TODO: Implement the CircuitBreaker class to prevent cascading failures.
"""
import time
import threading
from enum import Enum


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    STUB: Circuit breaker pattern implementation.

    This class needs to be implemented. The breaker should:
    1. Count consecutive failures
    2. Open the circuit after `failure_threshold` failures
    3. Return a fallback value when circuit is OPEN
    4. Attempt recovery after `recovery_timeout` seconds (HALF_OPEN state)
    5. Close the circuit on a successful probe
    """

    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 5.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = 0.0
        self._lock = threading.Lock()

    def call(self, func, *args, fallback=None, **kwargs):
        """
        Execute func(*args, **kwargs) with circuit breaker protection.

        If circuit is OPEN, return fallback immediately without calling func.
        If func raises an exception, increment failure count.
        If failure_threshold reached, open the circuit.
        """
        # TODO: implement circuit breaker logic
        # For now, just calls through with no protection (VULNERABLE)
        return func(*args, **kwargs)

    @property
    def is_open(self) -> bool:
        return self.state == CircuitState.OPEN

    def _on_success(self):
        with self._lock:
            self.failure_count = 0
            self.state = CircuitState.CLOSED

    def _on_failure(self):
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitState.OPEN
