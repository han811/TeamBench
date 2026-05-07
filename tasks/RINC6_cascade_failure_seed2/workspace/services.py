"""
Payments microservices — checkout → payment processor → fraud check chain.

WARNING: No circuit breakers — a failure in fraud_check cascades to all dependents.
Inspiration: AWS S3 outage (2017) — cascading failures from missing circuit breakers.
"""
import time
import threading
from circuit_breaker import CircuitBreaker, CircuitState

TIMEOUT = 1
FAILURE_THRESHOLD = 3



class CheckoutService:
    """Depends on payment_processorService — vulnerable to cascade if no circuit breaker."""
    port = 6020

    def __init__(self):
        self._upstream = PaymentprocessorService()
        # VULNERABILITY: circuit breaker exists but is not properly implemented
        self._breaker = CircuitBreaker(failure_threshold=FAILURE_THRESHOLD)

    def handle_request(self):
        # VULNERABLE: call() does not implement circuit breaking — always passes through
        try:
            upstream_data = self._breaker.call(
                self._upstream.handle_request,
                fallback={"service": "payment_processor", "status": "fallback", "data": None},
            )
            return {"service": "checkout", "status": "ok", "upstream": upstream_data}
        except (ConnectionError, TimeoutError) as e:
            # Without circuit breaker, this exception propagates every time
            raise ConnectionError(f"checkout failed because payment_processor is down: {e}")


class PaymentprocessorService:
    """Depends on fraud_checkService — vulnerable to cascade if no circuit breaker."""
    port = 6021

    def __init__(self):
        self._upstream = FraudcheckService()
        # VULNERABILITY: circuit breaker exists but is not properly implemented
        self._breaker = CircuitBreaker(failure_threshold=FAILURE_THRESHOLD)

    def handle_request(self):
        # VULNERABLE: call() does not implement circuit breaking — always passes through
        try:
            upstream_data = self._breaker.call(
                self._upstream.handle_request,
                fallback={"service": "fraud_check", "status": "fallback", "data": None},
            )
            return {"service": "payment_processor", "status": "ok", "upstream": upstream_data}
        except (ConnectionError, TimeoutError) as e:
            # Without circuit breaker, this exception propagates every time
            raise ConnectionError(f"payment_processor failed because fraud_check is down: {e}")


class FraudcheckService:
    """Simulates a degraded/failing upstream service."""
    port = 6022
    _call_count = 0

    def handle_request(self):
        FraudcheckService._call_count += 1
        # Simulate slow failure after startup
        if FraudcheckService._call_count > 2:
            time.sleep(0.1)  # slow response
            raise ConnectionError(f"fraud_check service unavailable (call #{FraudcheckService._call_count})")
        return {"service": "fraud_check", "status": "ok", "data": "initial_data"}

    @classmethod
    def reset(cls):
        cls._call_count = 0


def run_request_chain():
    """Simulate a request through the full service chain.

    Without circuit breakers, a failure in fraud_check causes the entire
    chain to hang for TIMEOUT seconds per retry, cascading upward.
    """
    checkout_svc = CheckoutService()
    return checkout_svc.handle_request()


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
