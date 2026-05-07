"""
E-Commerce microservices — product catalog → inventory → pricing service chain.

WARNING: No circuit breakers — a failure in pricing cascades to all dependents.
Inspiration: AWS S3 outage (2017) — cascading failures from missing circuit breakers.
"""
import time
import threading
from circuit_breaker import CircuitBreaker, CircuitState

TIMEOUT = 2
FAILURE_THRESHOLD = 4



class CatalogService:
    """Depends on inventoryService — vulnerable to cascade if no circuit breaker."""
    port = 6000

    def __init__(self):
        self._upstream = InventoryService()
        # VULNERABILITY: circuit breaker exists but is not properly implemented
        self._breaker = CircuitBreaker(failure_threshold=FAILURE_THRESHOLD)

    def handle_request(self):
        # VULNERABLE: call() does not implement circuit breaking — always passes through
        try:
            upstream_data = self._breaker.call(
                self._upstream.handle_request,
                fallback={"service": "inventory", "status": "fallback", "data": None},
            )
            return {"service": "catalog", "status": "ok", "upstream": upstream_data}
        except (ConnectionError, TimeoutError) as e:
            # Without circuit breaker, this exception propagates every time
            raise ConnectionError(f"catalog failed because inventory is down: {e}")


class InventoryService:
    """Depends on pricingService — vulnerable to cascade if no circuit breaker."""
    port = 6001

    def __init__(self):
        self._upstream = PricingService()
        # VULNERABILITY: circuit breaker exists but is not properly implemented
        self._breaker = CircuitBreaker(failure_threshold=FAILURE_THRESHOLD)

    def handle_request(self):
        # VULNERABLE: call() does not implement circuit breaking — always passes through
        try:
            upstream_data = self._breaker.call(
                self._upstream.handle_request,
                fallback={"service": "pricing", "status": "fallback", "data": None},
            )
            return {"service": "inventory", "status": "ok", "upstream": upstream_data}
        except (ConnectionError, TimeoutError) as e:
            # Without circuit breaker, this exception propagates every time
            raise ConnectionError(f"inventory failed because pricing is down: {e}")


class PricingService:
    """Simulates a degraded/failing upstream service."""
    port = 6002
    _call_count = 0

    def handle_request(self):
        PricingService._call_count += 1
        # Simulate slow failure after startup
        if PricingService._call_count > 2:
            time.sleep(0.1)  # slow response
            raise ConnectionError(f"pricing service unavailable (call #{PricingService._call_count})")
        return {"service": "pricing", "status": "ok", "data": "initial_data"}

    @classmethod
    def reset(cls):
        cls._call_count = 0


def run_request_chain():
    """Simulate a request through the full service chain.

    Without circuit breakers, a failure in pricing causes the entire
    chain to hang for TIMEOUT seconds per retry, cascading upward.
    """
    catalog_svc = CatalogService()
    return catalog_svc.handle_request()


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
