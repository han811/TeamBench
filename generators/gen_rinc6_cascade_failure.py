"""
Parameterized generator for RINC6: Cascading Failure / No Circuit Breakers.

Inspiration: AWS S3 us-east-1 outage (February 2017). A single component
(S3) failing caused cascading failures across dependent services because
no circuit breakers or fallback mechanisms existed. Services kept retrying
until they exhausted threads/connections.

Workspace has 3 microservices with dependency graph. One upstream service
becomes slow/unavailable; downstream services have no circuit breakers and
cascade-fail. Fix: add circuit breaker pattern + timeout + fallback.

Seeds vary: service names, dependency graph topology, failure point.

Grading: 7 checks — circuit breaker opens on failures, fallback returns,
cascade stops, healthy services still respond, timeout enforced.
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

TOPOLOGIES = [
    {
        "name": "e-commerce",
        "services": {
            "catalog": {"depends_on": ["inventory"], "port_offset": 0},
            "inventory": {"depends_on": ["pricing"], "port_offset": 1},
            "pricing": {"depends_on": [], "port_offset": 2},  # fails
        },
        "failing_service": "pricing",
        "entry_service": "catalog",
        "description": "product catalog → inventory → pricing service chain",
    },
    {
        "name": "analytics",
        "services": {
            "dashboard": {"depends_on": ["metrics"], "port_offset": 0},
            "metrics": {"depends_on": ["collector"], "port_offset": 1},
            "collector": {"depends_on": [], "port_offset": 2},  # fails
        },
        "failing_service": "collector",
        "entry_service": "dashboard",
        "description": "dashboard → metrics → collector chain",
    },
    {
        "name": "payments",
        "services": {
            "checkout": {"depends_on": ["payment_processor"], "port_offset": 0},
            "payment_processor": {"depends_on": ["fraud_check"], "port_offset": 1},
            "fraud_check": {"depends_on": [], "port_offset": 2},  # fails
        },
        "failing_service": "fraud_check",
        "entry_service": "checkout",
        "description": "checkout → payment processor → fraud check chain",
    },
]


class Generator(TaskGenerator):
    task_id = "RINC6_cascade_failure"
    domain = "incident"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        topo = TOPOLOGIES[seed % len(TOPOLOGIES)]
        base_port = 6000 + seed * 10
        failure_threshold = rng.randint(3, 5)
        timeout_sec = rng.choice([1, 2, 3])

        workspace_files = {
            "services.py": self._gen_services(topo, base_port, failure_threshold, timeout_sec),
            "circuit_breaker.py": self._gen_circuit_breaker_stub(),
            "test_cascade.py": self._gen_tests(topo, failure_threshold, timeout_sec),
            "requirements.txt": "pytest>=7.0\nrequests>=2.28\n",
        }

        expected = {
            "seed": seed,
            "topology": topo["name"],
            "failing_service": topo["failing_service"],
            "fix": "circuit_breaker_with_fallback",
            "failure_threshold": failure_threshold,
            "timeout_sec": timeout_sec,
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._gen_spec(topo, failure_threshold, timeout_sec),
            brief_md=self._gen_brief(topo),
            expected=expected,
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "incident", "incident": "AWS-S3-2017"},
        )

    def _gen_circuit_breaker_stub(self) -> str:
        return '''\
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
'''

    def _gen_services(self, topo: dict, base_port: int, failure_threshold: int, timeout_sec: int) -> str:
        svc_names = list(topo["services"].keys())
        failing = topo["failing_service"]
        entry = topo["entry_service"]

        # Build the service call chain
        service_classes = []
        for svc_name, svc_cfg in topo["services"].items():
            deps = svc_cfg["depends_on"]
            port = base_port + svc_cfg["port_offset"]
            if svc_name == failing:
                service_classes.append(self._gen_failing_service_class(svc_name, port))
            elif deps:
                dep = deps[0]
                service_classes.append(self._gen_dependent_service_class(svc_name, dep, port, timeout_sec))
            else:
                service_classes.append(self._gen_leaf_service_class(svc_name, port))

        return f'''\
"""
{topo["name"].title()} microservices — {topo["description"]}.

WARNING: No circuit breakers — a failure in {failing} cascades to all dependents.
Inspiration: AWS S3 outage (2017) — cascading failures from missing circuit breakers.
"""
import time
import threading
from circuit_breaker import CircuitBreaker, CircuitState

TIMEOUT = {timeout_sec}
FAILURE_THRESHOLD = {failure_threshold}

{"".join(service_classes)}

def run_request_chain():
    """Simulate a request through the full service chain.

    Without circuit breakers, a failure in {failing} causes the entire
    chain to hang for TIMEOUT seconds per retry, cascading upward.
    """
    {entry}_svc = {entry.replace("_","").title()}Service()
    return {entry}_svc.handle_request()


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
'''

    def _gen_failing_service_class(self, name: str, port: int) -> str:
        class_name = name.replace("_", "").title() + "Service"
        return f'''

class {class_name}:
    """Simulates a degraded/failing upstream service."""
    port = {port}
    _call_count = 0

    def handle_request(self):
        {class_name}._call_count += 1
        # Simulate slow failure after startup
        if {class_name}._call_count > 2:
            time.sleep(0.1)  # slow response
            raise ConnectionError(f"{name} service unavailable (call #{{{class_name}._call_count}})")
        return {{"service": "{name}", "status": "ok", "data": "initial_data"}}

    @classmethod
    def reset(cls):
        cls._call_count = 0
'''

    def _gen_dependent_service_class(self, name: str, dep: str, port: int, timeout: int) -> str:
        class_name = name.replace("_", "").title() + "Service"
        dep_class = dep.replace("_", "").title() + "Service"
        return f'''

class {class_name}:
    """Depends on {dep}Service — vulnerable to cascade if no circuit breaker."""
    port = {port}

    def __init__(self):
        self._upstream = {dep_class}()
        # VULNERABILITY: circuit breaker exists but is not properly implemented
        self._breaker = CircuitBreaker(failure_threshold=FAILURE_THRESHOLD)

    def handle_request(self):
        # VULNERABLE: call() does not implement circuit breaking — always passes through
        try:
            upstream_data = self._breaker.call(
                self._upstream.handle_request,
                fallback={{"service": "{dep}", "status": "fallback", "data": None}},
            )
            return {{"service": "{name}", "status": "ok", "upstream": upstream_data}}
        except (ConnectionError, TimeoutError) as e:
            # Without circuit breaker, this exception propagates every time
            raise ConnectionError(f"{name} failed because {dep} is down: {{e}}")
'''

    def _gen_leaf_service_class(self, name: str, port: int) -> str:
        class_name = name.replace("_", "").title() + "Service"
        return f'''

class {class_name}:
    """Leaf service with no upstream dependencies."""
    port = {port}

    def handle_request(self):
        return {{"service": "{name}", "status": "ok", "data": "leaf_data"}}
'''

    def _gen_tests(self, topo: dict, failure_threshold: int, timeout_sec: int) -> str:
        entry = topo["entry_service"]
        entry_class = entry.replace("_", "").title() + "Service"
        failing = topo["failing_service"]
        failing_class = failing.replace("_", "").title() + "Service"

        return f'''\
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
    svc_module.{failing_class}.reset()


@pytest.fixture(autouse=True)
def reset_state():
    reload_modules()
    yield
    reload_modules()


def test_circuit_breaker_opens_after_failures():
    """Circuit breaker must open after failure_threshold consecutive failures."""
    breaker = CircuitBreaker(failure_threshold={failure_threshold}, recovery_timeout=60)

    def failing_func():
        raise ConnectionError("upstream down")

    for i in range({failure_threshold}):
        try:
            breaker.call(failing_func, fallback=None)
        except (ConnectionError, Exception):
            pass

    assert breaker.state == CircuitState.OPEN, (
        f"Circuit breaker did not open after {failure_threshold} failures — state={{breaker.state}}"
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
        breaker.call(func, fallback={{"status": "fallback"}})
    except Exception:
        pass

    assert breaker.state == CircuitState.OPEN

    # Now call again — should use fallback, not call func
    before = call_count[0]
    result = breaker.call(func, fallback={{"status": "fallback"}})
    assert result == {{"status": "fallback"}}, (
        f"Fallback not returned when circuit OPEN: {{result}}"
    )
    assert call_count[0] == before, "func was called even though circuit is OPEN"


def test_cascade_stopped_by_circuit_breaker():
    """After failures, {entry} must return a fallback instead of raising."""
    svc_module.{failing_class}.reset()
    # Trip the failing service several times
    entry_svc = svc_module.{entry_class}()
    results = []
    for _ in range({failure_threshold} + 3):
        try:
            result = entry_svc.handle_request()
            results.append(result)
        except Exception as e:
            results.append({{"error": str(e)}})

    # After the breaker opens, later calls should NOT raise — they return fallback
    later_results = results[{failure_threshold}:]
    for r in later_results:
        assert "error" not in r, (
            f"Cascade not stopped — still getting errors after breaker should be open: {{r}}"
        )


def test_closed_circuit_passes_through():
    """A healthy circuit should pass calls through normally."""
    breaker = CircuitBreaker(failure_threshold={failure_threshold})
    result = breaker.call(lambda: {{"ok": True}}, fallback=None)
    assert result == {{"ok": True}}
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
    result = breaker.call(lambda: {{"recovered": True}}, fallback={{"status": "fallback"}})
    # Either the probe succeeded (circuit closed) or it's in half-open
    assert breaker.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)
'''

    def _gen_spec(self, topo: dict, failure_threshold: int, timeout_sec: int) -> str:
        svc_chain = " → ".join(list(topo["services"].keys()))
        return f"""# RINC6: Cascading Failure — Circuit Breaker Missing

## Incident Background
Inspired by the AWS S3 us-east-1 outage (February 28, 2017). A small
operational error cascaded because dependent services had no isolation
mechanisms. Services kept retrying failed upstream calls, exhausting
connection pools and thread pools, amplifying the outage.

## System: {topo["name"].title()} ({topo["description"]})
Service chain: `{svc_chain}`

## Problem
The `{topo["failing_service"]}` service starts failing after 2 successful calls.
Because there are no circuit breakers, `{topo["entry_service"]}` keeps retrying
through the full chain, hanging for {timeout_sec}s per call and propagating exceptions.

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
1. Circuit opens after `failure_threshold={failure_threshold}` consecutive failures
2. Open circuit returns fallback without calling upstream
3. `{topo["entry_service"]}` returns fallback data instead of raising after circuit opens
4. Closed circuit still passes calls through (no regression)
5. Circuit recovers after `recovery_timeout` seconds
6. All tests pass: `pytest test_cascade.py -v`

## Files
- `circuit_breaker.py` — implement `CircuitBreaker.call()`
- `services.py` — do NOT modify
- `test_cascade.py` — do NOT modify
"""

    def _gen_brief(self, topo: dict) -> str:
        return f"""# RINC6: Cascading Failure Fix (Brief)

The {topo["name"]} service stack is experiencing availability issues.
When the `{topo["failing_service"]}` service goes down, the entire
{topo["description"]} stops responding.

Implement the circuit breaker in `circuit_breaker.py` to stop the cascade.

Verify with:
```
pytest test_cascade.py -v
```

**Files to fix:** `circuit_breaker.py`
**Do NOT modify:** `services.py`, `test_cascade.py`
"""
