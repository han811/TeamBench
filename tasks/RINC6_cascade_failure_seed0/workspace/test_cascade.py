"""
Cascade failure and circuit breaker tests.

Tests verify that circuit breaker opens after repeated failures,
returns fallback values, and stops the cascade.
"""
import time
import pytest
import importlib
import services as svc_module
import circuit_breaker as cb_module
from circuit_breaker import CircuitBreaker, CircuitState


def reload_modules():
    """Reset all service state between tests."""
    importlib.reload(cb_module)
    importlib.reload(svc_module)
    # Reset failing service call counter
    svc_module.PricingService.reset()


@pytest.fixture(autouse=True)
def reset_state():
    reload_modules()
    yield
    reload_modules()


def test_circuit_breaker_opens_after_failures():
    """Circuit breaker must open after failure_threshold consecutive failures."""
    breaker = CircuitBreaker(failure_threshold=4, recovery_timeout=60)

    def failing_func():
        raise ConnectionError("upstream down")

    for i in range(4):
        try:
            breaker.call(failing_func, fallback=None)
        except (ConnectionError, Exception):
            pass

    assert breaker.state == CircuitState.OPEN, (
        f"Circuit breaker did not open after 4 failures — state={breaker.state}"
    )


def test_open_circuit_returns_fallback():
    """When circuit is OPEN, call() must return fallback without calling func."""
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
    call_count = [0]

    def func():
        call_count[0] += 1
        raise ConnectionError("down")

    # Trip the breaker
    try:
        breaker.call(func, fallback={"status": "fallback"})
    except Exception:
        pass

    assert breaker.state == CircuitState.OPEN

    # Now call again — should use fallback, not call func
    before = call_count[0]
    result = breaker.call(func, fallback={"status": "fallback"})
    assert result == {"status": "fallback"}, (
        f"Fallback not returned when circuit OPEN: {result}"
    )
    assert call_count[0] == before, "func was called even though circuit is OPEN"


def test_cascade_stopped_by_circuit_breaker():
    """After failures, catalog must return a fallback instead of raising."""
    svc_module.PricingService.reset()
    # Trip the failing service several times
    entry_svc = svc_module.CatalogService()
    results = []
    for _ in range(4 + 3):
        try:
            result = entry_svc.handle_request()
            results.append(result)
        except Exception as e:
            results.append({"error": str(e)})

    # After the breaker opens, later calls should NOT raise — they return fallback
    later_results = results[4:]
    for r in later_results:
        assert "error" not in r, (
            f"Cascade not stopped — still getting errors after breaker should be open: {r}"
        )


def test_closed_circuit_passes_through():
    """A healthy circuit should pass calls through normally."""
    breaker = CircuitBreaker(failure_threshold=4)
    result = breaker.call(lambda: {"ok": True}, fallback=None)
    assert result == {"ok": True}
    assert breaker.state == CircuitState.CLOSED


def test_circuit_recovers_after_timeout():
    """Circuit should transition to HALF_OPEN after recovery_timeout."""
    breaker = CircuitBreaker(failure_threshold=1, recovery_timeout=0.1)

    def failing():
        raise ConnectionError("down")

    try:
        breaker.call(failing, fallback=None)
    except Exception:
        pass

    assert breaker.state == CircuitState.OPEN
    time.sleep(0.2)

    # After timeout, a call should probe (HALF_OPEN) or succeed
    result = breaker.call(lambda: {"recovered": True}, fallback={"status": "fallback"})
    # Either the probe succeeded (circuit closed) or it's in half-open
    assert breaker.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)
