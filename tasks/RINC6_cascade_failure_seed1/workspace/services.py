"""
Analytics microservices — dashboard → metrics → collector chain.

WARNING: No circuit breakers — a failure in collector cascades to all dependents.
Inspiration: AWS S3 outage (2017) — cascading failures from missing circuit breakers.
"""
import time
import threading
from circuit_breaker import CircuitBreaker, CircuitState

TIMEOUT = 3
FAILURE_THRESHOLD = 3



class DashboardService:
    """Depends on metricsService — vulnerable to cascade if no circuit breaker."""
    port = 6010

    def __init__(self):
        self._upstream = MetricsService()
        # VULNERABILITY: circuit breaker exists but is not properly implemented
        self._breaker = CircuitBreaker(failure_threshold=FAILURE_THRESHOLD)

    def handle_request(self):
        # VULNERABLE: call() does not implement circuit breaking — always passes through
        try:
            upstream_data = self._breaker.call(
                self._upstream.handle_request,
                fallback={"service": "metrics", "status": "fallback", "data": None},
            )
            return {"service": "dashboard", "status": "ok", "upstream": upstream_data}
        except (ConnectionError, TimeoutError) as e:
            # Without circuit breaker, this exception propagates every time
            raise ConnectionError(f"dashboard failed because metrics is down: {e}")


class MetricsService:
    """Depends on collectorService — vulnerable to cascade if no circuit breaker."""
    port = 6011

    def __init__(self):
        self._upstream = CollectorService()
        # VULNERABILITY: circuit breaker exists but is not properly implemented
        self._breaker = CircuitBreaker(failure_threshold=FAILURE_THRESHOLD)

    def handle_request(self):
        # VULNERABLE: call() does not implement circuit breaking — always passes through
        try:
            upstream_data = self._breaker.call(
                self._upstream.handle_request,
                fallback={"service": "collector", "status": "fallback", "data": None},
            )
            return {"service": "metrics", "status": "ok", "upstream": upstream_data}
        except (ConnectionError, TimeoutError) as e:
            # Without circuit breaker, this exception propagates every time
            raise ConnectionError(f"metrics failed because collector is down: {e}")


class CollectorService:
    """Simulates a degraded/failing upstream service."""
    port = 6012
    _call_count = 0

    def handle_request(self):
        CollectorService._call_count += 1
        # Simulate slow failure after startup
        if CollectorService._call_count > 2:
            time.sleep(0.1)  # slow response
            raise ConnectionError(f"collector service unavailable (call #{CollectorService._call_count})")
        return {"service": "collector", "status": "ok", "data": "initial_data"}

    @classmethod
    def reset(cls):
        cls._call_count = 0


def run_request_chain():
    """Simulate a request through the full service chain.

    Without circuit breakers, a failure in collector causes the entire
    chain to hang for TIMEOUT seconds per retry, cascading upward.
    """
    dashboard_svc = DashboardService()
    return dashboard_svc.handle_request()


class ServiceHealth:
    """Track service health across multiple calls."""

    def __init__(self):
        self.results = []

    def check(self, service_class, n_calls: int = 5):
        svc = service_class()
        for _ in range(n_calls):
            result = svc.handle_request()
            self.results.append(result)
        return self.results
