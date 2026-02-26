"""
Parameterized generator for INC6: Distributed Deadlock Diagnosis & Fix.

Each seed produces:
  - Different number of locks (2-4) and services involved (2-3)
  - Different lock pair causing the circular dependency
  - Different variable/class/function names for contamination resistance
  - Different red herring: a busy-wait loop or CPU-intensive computation
    that looks alarming in thread dumps but is NOT the deadlock

TNI driver (Pattern A,B):
  - The SPEC reveals the correct lock acquisition order across services,
    names the exact circular dependency (Service A acquires lock_X then
    lock_Y; Service B acquires lock_Y then lock_X), and identifies which
    thread in the dump is the deadlock victim vs. the red herring.
  - The BRIEF only says "Multiple services are intermittently hanging under
    load. Investigate and fix." Thread dumps are provided but include red
    herring threads (high CPU, NOT deadlocked).
  - Without the spec the Executor cannot distinguish the real deadlock from
    the busy-wait red herring.

Grader checks (10+):
  1. All service Python files are syntactically valid
  2. Lock ordering fixed (circular dependency eliminated)
  3. Red herring code NOT removed (busy-wait still present)
  4. Services still function (smoke test passes)
  5. No new deadlock possible (static analysis of acquire order)
  6. Simulation confirms no hang under concurrent load
  7. Fix is structural (not just adding timeouts to mask the problem)
  8. Service interop preserved (shared lock names unchanged)
  9. Original function signatures intact
  10. Attestation verdict=pass
  11. Lock hierarchy consistent across both services
  12. Thread dump analysis file updated correctly
"""
from __future__ import annotations

import json
import textwrap

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# ---------------------------------------------------------------------------
# Lock configuration definitions
# ---------------------------------------------------------------------------

# Each entry defines a scenario with 2-4 locks across 2-3 services.
# The "deadlock_pair" identifies which two services form the circular wait.
LOCK_SCENARIOS = [
    {
        "id": "inventory_payment",
        "locks": ["lock_inventory", "lock_payment"],
        "services": ["inventory_service", "payment_service"],
        "deadlock_pair": (0, 1),  # indices into services
        "domain": "e-commerce order processing",
        "lock_descriptions": {
            "lock_inventory": "protects the global inventory counter",
            "lock_payment": "protects the payment ledger",
        },
    },
    {
        "id": "user_session",
        "locks": ["lock_user", "lock_session"],
        "services": ["user_service", "session_service"],
        "deadlock_pair": (0, 1),
        "domain": "authentication pipeline",
        "lock_descriptions": {
            "lock_user": "protects the user profile store",
            "lock_session": "protects the active session registry",
        },
    },
    {
        "id": "cache_db",
        "locks": ["lock_cache", "lock_db", "lock_index"],
        "services": ["cache_service", "db_service", "index_service"],
        "deadlock_pair": (0, 1),
        "domain": "data access layer",
        "lock_descriptions": {
            "lock_cache": "protects the in-memory cache",
            "lock_db": "protects the database connection pool",
            "lock_index": "protects the search index",
        },
    },
    {
        "id": "order_fulfillment",
        "locks": ["lock_order", "lock_warehouse", "lock_shipping", "lock_billing"],
        "services": ["order_service", "fulfillment_service"],
        "deadlock_pair": (0, 1),
        "domain": "order fulfillment pipeline",
        "lock_descriptions": {
            "lock_order": "protects the order queue",
            "lock_warehouse": "protects the warehouse slot allocator",
            "lock_shipping": "protects the shipping manifest",
            "lock_billing": "protects the billing records",
        },
    },
    {
        "id": "auth_resource",
        "locks": ["lock_auth", "lock_resource"],
        "services": ["auth_service", "resource_service"],
        "deadlock_pair": (0, 1),
        "domain": "access control system",
        "lock_descriptions": {
            "lock_auth": "protects the auth token store",
            "lock_resource": "protects the resource permission table",
        },
    },
]

# ---------------------------------------------------------------------------
# Red herring definitions
# ---------------------------------------------------------------------------

RED_HERRINGS = [
    {
        "id": "busy_wait_cpu",
        "description": (
            "A busy-wait polling loop that consumes 100% CPU on one thread. "
            "It appears in thread dumps as a tight loop and looks alarming, "
            "but it is intentional back-pressure logic and NOT the deadlock."
        ),
        "thread_dump_label": "HIGH-CPU POLLER (not deadlocked)",
        "code_template": """\
def _poll_queue_{svc}(self) -> None:
    \"\"\"
    Back-pressure poller: busy-waits until the work queue drains below
    the high-water mark.  Appears as 100%% CPU in thread dumps — this is
    intentional and is NOT the cause of the service hang.
    \"\"\"
    high_water = {high_water}
    while len(self._work_queue) > high_water:
        pass  # Intentional busy-wait (red herring — NOT the deadlock)
    # Queue has drained; normal processing resumes
""",
        "params": {"high_water": [50, 100, 200, 500]},
    },
    {
        "id": "spin_hash",
        "description": (
            "A CPU-intensive hash computation loop that runs in a background thread. "
            "It shows up as a spinning thread in profiling and looks like a hang, "
            "but it always terminates and is not part of any locking path."
        ),
        "thread_dump_label": "HASH-WORKER (cpu-bound, not deadlocked)",
        "code_template": """\
def _background_hash_worker_{svc}(self, data: bytes) -> int:
    \"\"\"
    CPU-intensive background checksum worker.  Spins for up to {iterations}
    iterations; appears as a 'stuck' thread in basic profilers.
    This is NOT the deadlock — it holds no locks.
    \"\"\"
    acc = 0
    chunk = data if data else b"default-payload"
    for _ in range({iterations}):
        acc = (acc * 31 + sum(chunk)) & 0xFFFFFFFF
    return acc
""",
        "params": {"iterations": [500_000, 1_000_000, 2_000_000, 5_000_000]},
    },
    {
        "id": "retry_backoff",
        "description": (
            "A retry loop with exponential backoff that sleeps between attempts. "
            "It causes long pauses in logs that resemble a hang, but it eventually "
            "succeeds and does NOT hold any locks during the sleep."
        ),
        "thread_dump_label": "RETRY-LOOP (sleeping, not deadlocked)",
        "code_template": """\
def _retry_with_backoff_{svc}(self, fn, max_attempts: int = {max_attempts}) -> object:
    \"\"\"
    Retry wrapper with exponential back-off.  Pauses up to {max_sleep}s between
    attempts; log lines look like hangs but NO locks are held during sleep.
    This is NOT the deadlock.
    \"\"\"
    import time as _time
    delay = 0.1
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception:
            if attempt == max_attempts - 1:
                raise
            _time.sleep(delay)
            delay = min(delay * 2, {max_sleep})
    return None
""",
        "params": {
            "max_attempts": [3, 5, 7, 10],
            "max_sleep": [2, 4, 8, 16],
        },
    },
]

# ---------------------------------------------------------------------------
# Code generator
# ---------------------------------------------------------------------------

def _pick_deadlock_locks(scenario: dict, rng: SeededRandom) -> tuple[str, str]:
    """Pick the two locks that form the circular dependency."""
    locks = scenario["locks"]
    if len(locks) == 2:
        return locks[0], locks[1]
    # For 3-4 lock scenarios, pick a pair from the first two
    shuffled = list(locks)
    rng.shuffle(shuffled)
    return shuffled[0], shuffled[1]


def _build_service_file(
    svc_name: str,
    svc_index: int,
    scenario: dict,
    lock_a: str,
    lock_b: str,
    is_buggy_service: bool,  # True => acquires in wrong order
    red_herring: dict,
    rng: SeededRandom,
    seed: int,
    all_locks: list[str],
) -> str:
    """
    Build one service Python file.

    Correct order (canonical / fixed):  lock_a THEN lock_b
    Buggy order (one service):          lock_b THEN lock_a  (causes deadlock)
    """
    svc_id = svc_name  # e.g. "inventory_service"

    # Pick red herring param values
    rh_params = {}
    for k, v_list in red_herring["params"].items():
        rh_params[k] = rng.choice(v_list)

    rh_code = red_herring["code_template"].format(svc=svc_id, **rh_params)

    # Build declarations for all locks (shared threading.Lock objects imported
    # from shared_locks module — in workspace they are module-level globals)
    lock_decls = "\n".join(
        f"{lk} = threading.Lock()  # {scenario['lock_descriptions'].get(lk, 'shared resource lock')}"
        for lk in all_locks
    )

    # Determine acquisition order for THIS service
    if is_buggy_service:
        # WRONG order — creates circular wait
        first_lock, second_lock = lock_b, lock_a
        order_comment = (
            f"# BUG: Acquires {lock_b} before {lock_a} — circular with the other service.\n"
            f"    # Correct order should be: {lock_a} THEN {lock_b}.\n"
            f"    # DEADLOCK: if the other service holds {lock_a} and waits for {lock_b},\n"
            f"    # and this service holds {lock_b} and waits for {lock_a}, both hang."
        )
    else:
        # CORRECT order — other service must also use this order after fix
        first_lock, second_lock = lock_a, lock_b
        order_comment = (
            f"# Correct acquisition order: {lock_a} THEN {lock_b}.\n"
            f"    # All services must acquire in this order to prevent deadlock."
        )

    port = rng.randint(8100, 9900)
    worker_threads = rng.randint(2, 8)

    code = f'''\
"""
{svc_name}.py — {scenario["domain"]} service component

Part of a distributed system processing {scenario["domain"]} requests.
This service coordinates with peer services using shared threading locks.

Seed: {seed}
"""
import threading
import time
import logging
import hashlib
import itertools
from typing import Any, Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s %(threadName)s: %(message)s",
)
logger = logging.getLogger("{svc_name}")

# ── Shared locks (must be imported/shared across services in production) ──────
# In this simulation each file declares its own instances for standalone testing.
# In the real system these are shared via a lock registry.
{lock_decls}

# ── Configuration ─────────────────────────────────────────────────────────────
PORT = {port}
WORKER_THREADS = {worker_threads}
MAX_QUEUE_SIZE = 256

# ── Work queue (simulated) ────────────────────────────────────────────────────
_work_queue: List[Dict] = []
_work_queue_lock = threading.Lock()

# ── Red herring: looks suspicious in thread dumps but is NOT the deadlock ─────
{rh_code}

# ── Core service class ────────────────────────────────────────────────────────

class {svc_name.title().replace("_", "")}:
    """Main service class for {svc_name.replace("_", " ")}."""

    def __init__(self) -> None:
        self._work_queue: List[Dict] = []
        self._running = False
        self._request_counter = itertools.count(1)

    def _generate_request_id(self) -> str:
        n = next(self._request_counter)
        return hashlib.md5(f"req-{{n}}-{svc_name}-seed-{seed}".encode()).hexdigest()[:12]

    def process_request(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an incoming request, acquiring shared locks as required.

        Lock acquisition order determines deadlock safety.
        {order_comment}
        """
        request_id = self._generate_request_id()
        logger.debug("Processing request_id=%s payload_keys=%s", request_id, list(payload.keys()))

        with {first_lock}:
            # Critical section: operating on {first_lock}
            logger.debug("Acquired {first_lock} for request_id=%s", request_id)
            time.sleep(0.001)  # Simulate work under first lock

            with {second_lock}:
                # Critical section: operating on both {first_lock} and {second_lock}
                logger.debug("Acquired {second_lock} for request_id=%s", request_id)
                result = self._do_work(payload, request_id)

        return result

    def _do_work(self, payload: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Perform the actual work while both locks are held."""
        return {{
            "request_id": request_id,
            "service": "{svc_name}",
            "status": "ok",
            "payload_keys": list(payload.keys()),
            "processed_by": "{svc_name}",
        }}

    def health_check(self) -> Dict[str, Any]:
        """Return service health status."""
        return {{
            "service": "{svc_name}",
            "status": "healthy",
            "port": PORT,
            "worker_threads": WORKER_THREADS,
        }}

    def run_smoke_test(self) -> bool:
        """Minimal smoke test: process one request and verify output."""
        try:
            result = self.process_request({{"test": "smoke", "seed": {seed}}})
            assert result.get("status") == "ok", f"Unexpected status: {{result.get('status')}}"
            assert result.get("service") == "{svc_name}", "Wrong service name in result"
            h = self.health_check()
            assert h.get("status") == "healthy"
            return True
        except Exception as exc:
            logger.error("Smoke test failed: %s", exc)
            return False


# ── Module-level smoke test (called by grader) ───────────────────────────────

def run_smoke_test() -> bool:
    svc = {svc_name.title().replace("_", "")}()
    return svc.run_smoke_test()


if __name__ == "__main__":
    logger.info("Starting {svc_name} on port %d", PORT)
    ok = run_smoke_test()
    logger.info("Smoke test: %s", "PASS" if ok else "FAIL")
    import sys; sys.exit(0 if ok else 1)
'''
    return code


def _build_thread_dump(
    scenario: dict,
    lock_a: str,
    lock_b: str,
    buggy_svc: str,
    good_svc: str,
    red_herring: dict,
    rng: SeededRandom,
    seed: int,
) -> str:
    """Generate a realistic thread dump showing the deadlock + red herring."""
    ts = f"2024-0{rng.randint(1,9)}-{rng.randint(10,28)}T{rng.randint(10,23)}:{rng.randint(10,59)}:{rng.randint(10,59)}Z"
    pid = rng.randint(10000, 65000)
    tid_a = rng.randint(100, 999)
    tid_b = rng.randint(100, 999)
    tid_rh = rng.randint(100, 999)

    rh_label = red_herring["thread_dump_label"]

    return f"""\
Thread Dump — {scenario["domain"]}
Timestamp: {ts}
PID: {pid}

============================================================
THREAD: worker-{tid_a} ({buggy_svc})
STATE: BLOCKED (waiting to acquire lock)
  - Holding:   {lock_b}
  - Waiting for: {lock_a}
  Stack:
    {buggy_svc}.process_request (line ~42)
    threading.Lock.acquire (blocking)

THREAD: worker-{tid_b} ({good_svc})
STATE: BLOCKED (waiting to acquire lock)
  - Holding:   {lock_a}
  - Waiting for: {lock_b}
  Stack:
    {good_svc}.process_request (line ~42)
    threading.Lock.acquire (blocking)

THREAD: poller-{tid_rh} [{rh_label}]
STATE: RUNNABLE (100% CPU or tight-loop)
  - Holding:   <none>
  - Waiting for: <nothing>
  Stack:
    {buggy_svc}._poll_queue / _background_hash_worker / _retry_with_backoff (red herring)
    [This thread is CPU-bound or sleeping; it holds NO locks and is NOT deadlocked]

============================================================
DEADLOCK DETECTED:
  worker-{tid_a} ({buggy_svc}) holds {lock_b}, waits for {lock_a}
  worker-{tid_b} ({good_svc}) holds {lock_a}, waits for {lock_b}
  => Circular wait. Neither thread can proceed.

NOTE: The poller-{tid_rh} thread (high CPU) is a RED HERRING.
      It does not participate in the deadlock and should NOT be modified.
============================================================
"""


def _build_deadlock_sim(
    scenario: dict,
    lock_a: str,
    lock_b: str,
    svc_names: list[str],
    buggy_svc_name: str,
    good_svc_name: str,
    seed: int,
) -> str:
    """Generate a concurrent simulation script that demonstrates the deadlock."""
    return f'''\
"""
deadlock_sim.py — Deadlock demonstration and fix verifier.

Simulates concurrent access by the two services.

Usage:
    python3 deadlock_sim.py            # Run with buggy lock order (will deadlock)
    python3 deadlock_sim.py --fixed    # Run with fixed lock order (should not deadlock)

Exit codes:
    0 — No deadlock (correct lock ordering)
    1 — Deadlock detected (incorrect lock ordering)
    2 — Timeout (presumed deadlock)
"""
import argparse
import sys
import threading
import time

# Shared locks (simulated)
{lock_a} = threading.Lock()
{lock_b} = threading.Lock()

TIMEOUT = 3.0  # seconds to wait before declaring deadlock
result_a = None
result_b = None
error_a = None
error_b = None


def service_a_buggy():
    \"\"\"Buggy: acquires {lock_b} then {lock_a} — opposite to service_b.\"\"\"
    global result_a, error_a
    try:
        with {lock_b}:
            time.sleep(0.05)
            with {lock_a}:
                result_a = "done"
    except Exception as e:
        error_a = str(e)


def service_b_correct():
    \"\"\"Correct order: acquires {lock_a} then {lock_b}.\"\"\"
    global result_b, error_b
    try:
        with {lock_a}:
            time.sleep(0.05)
            with {lock_b}:
                result_b = "done"
    except Exception as e:
        error_b = str(e)


def service_a_fixed():
    \"\"\"Fixed: acquires {lock_a} then {lock_b} — same as service_b.\"\"\"
    global result_a, error_a
    try:
        with {lock_a}:
            time.sleep(0.05)
            with {lock_b}:
                result_a = "done"
    except Exception as e:
        error_a = str(e)


def main():
    global result_a, result_b
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixed", action="store_true", help="Use fixed lock ordering")
    args = parser.parse_args()

    fn_a = service_a_fixed if args.fixed else service_a_buggy
    fn_b = service_b_correct

    t_a = threading.Thread(target=fn_a, name="service-a", daemon=True)
    t_b = threading.Thread(target=fn_b, name="service-b", daemon=True)

    t_a.start()
    t_b.start()

    t_a.join(timeout=TIMEOUT)
    t_b.join(timeout=TIMEOUT)

    if t_a.is_alive() or t_b.is_alive():
        print("RESULT: DEADLOCK DETECTED — threads still blocked after timeout")
        print(f"  service-a alive: {{t_a.is_alive()}}")
        print(f"  service-b alive: {{t_b.is_alive()}}")
        sys.exit(2)
    elif error_a or error_b:
        print(f"RESULT: ERROR — service_a error={{error_a}}, service_b error={{error_b}}")
        sys.exit(1)
    else:
        print(f"RESULT: OK — No deadlock. result_a={{result_a}}, result_b={{result_b}}")
        sys.exit(0)


if __name__ == "__main__":
    main()
'''


def _build_check_fix(
    scenario: dict,
    lock_a: str,
    lock_b: str,
    buggy_svc_name: str,
    good_svc_name: str,
    red_herring: dict,
    seed: int,
) -> str:
    """Generate a fix-checker script that validates the deadlock was resolved."""
    rh_id = red_herring["id"]
    # Pick a characteristic identifier unique to this red herring type
    rh_markers = {
        "busy_wait_cpu": "_poll_queue",
        "spin_hash": "_background_hash_worker",
        "retry_backoff": "_retry_with_backoff",
    }
    rh_marker = rh_markers.get(rh_id, "_poll_queue")

    return f'''\
"""
check_fix.py — Automated fix validator for INC6: Distributed Deadlock.

Checks:
  1. Both service files parse without syntax errors
  2. Smoke tests pass for both services
  3. Lock ordering is fixed (no circular dependency)
  4. Red herring code still present
  5. deadlock_sim.py --fixed exits 0

Usage:
    python3 check_fix.py

Exit codes:
    0 — all checks pass
    1 — one or more checks failed
"""
import ast
import subprocess
import sys

CHECKS_PASSED = 0
CHECKS_TOTAL = 0
FAILURES = []


def check(name: str, fn) -> bool:
    global CHECKS_PASSED, CHECKS_TOTAL
    CHECKS_TOTAL += 1
    try:
        ok = fn()
        if ok:
            CHECKS_PASSED += 1
            return True
        else:
            FAILURES.append(name)
            return False
    except Exception as exc:
        print(f"  ERROR in check {{name}}: {{exc}}")
        FAILURES.append(name)
        return False


def check_syntax_both() -> bool:
    """Both service files must parse without syntax errors."""
    for fname in ["{buggy_svc_name}.py", "{good_svc_name}.py"]:
        try:
            with open(fname, "r") as f:
                src = f.read()
            ast.parse(src)
            print(f"PASS: {{fname}} parses OK")
        except (FileNotFoundError, SyntaxError) as e:
            print(f"FAIL: {{fname}}: {{e}}")
            return False
    return True


def check_smoke_both() -> bool:
    """Both services must pass their smoke tests."""
    for fname in ["{buggy_svc_name}.py", "{good_svc_name}.py"]:
        result = subprocess.run(
            [sys.executable, fname],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode != 0:
            print(f"FAIL: {{fname}} smoke test failed (exit {{result.returncode}})")
            print(f"  stderr: {{result.stderr[:200]}}")
            return False
        print(f"PASS: {{fname}} smoke test passed")
    return True


def check_lock_ordering_fixed() -> bool:
    \"\"\"
    Verify that {buggy_svc_name}.py now acquires {lock_a} before {lock_b}
    (same order as {good_svc_name}.py).

    We check that in process_request(), the first `with {lock_a}` appears
    before the first `with {lock_b}`.
    \"\"\"
    with open("{buggy_svc_name}.py", "r") as f:
        src = f.read()

    lines = src.splitlines()
    first_a = None
    first_b = None
    in_process = False
    for i, line in enumerate(lines):
        if "def process_request" in line:
            in_process = True
        if in_process:
            if first_a is None and "with {lock_a}" in line:
                first_a = i
            if first_b is None and "with {lock_b}" in line:
                first_b = i
        # Stop at next top-level def
        if in_process and i > 0 and line.startswith("    def ") and "process_request" not in line:
            break

    if first_a is None or first_b is None:
        print(f"FAIL: Could not locate both lock acquires in process_request()")
        return False
    if first_a < first_b:
        print(f"PASS: Lock ordering correct — {lock_a} (line {{first_a+1}}) before {lock_b} (line {{first_b+1}})")
        return True
    else:
        print(f"FAIL: Lock ordering still wrong — {lock_b} (line {{first_b+1}}) before {lock_a} (line {{first_a+1}})")
        return False


def check_red_herring_present() -> bool:
    \"\"\"Red herring code must still be present in {buggy_svc_name}.py.\"\"\"
    with open("{buggy_svc_name}.py", "r") as f:
        src = f.read()
    marker = "{rh_marker}"
    if marker in src:
        print(f"PASS: Red herring marker '{{marker}}' present")
        return True
    print(f"FAIL: Red herring code removed (marker '{{marker}}' missing)")
    return False


def check_sim_fixed() -> bool:
    \"\"\"deadlock_sim.py --fixed must exit 0 (no deadlock).\"\"\"
    result = subprocess.run(
        [sys.executable, "deadlock_sim.py", "--fixed"],
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode == 0:
        print("PASS: deadlock_sim.py --fixed exits 0")
        return True
    print(f"FAIL: deadlock_sim.py --fixed exited {{result.returncode}}: {{result.stdout[:200]}}")
    return False


def main():
    print("=" * 60)
    print("INC6 Fix Checker — Distributed Deadlock Validation")
    print(f"Scenario: {scenario['id']} (seed={seed})")
    print("=" * 60)
    print()

    check("syntax_both",          check_syntax_both)
    check("smoke_both",           check_smoke_both)
    check("lock_ordering_fixed",  check_lock_ordering_fixed)
    check("red_herring_present",  check_red_herring_present)
    check("sim_fixed",            check_sim_fixed)

    print()
    print(f"Results: {{CHECKS_PASSED}}/{{CHECKS_TOTAL}} checks passed")
    if FAILURES:
        print(f"Failed: {{', '.join(FAILURES)}}")
        sys.exit(1)
    else:
        print("All checks passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
'''


# ---------------------------------------------------------------------------
# Spec and Brief generators
# ---------------------------------------------------------------------------

def _generate_spec(
    scenario: dict,
    lock_a: str,
    lock_b: str,
    buggy_svc: str,
    good_svc: str,
    red_herring: dict,
    seed: int,
    rng: SeededRandom,
) -> str:
    rh_id = red_herring["id"]
    rh_desc = red_herring["description"]
    rh_label = red_herring["thread_dump_label"]
    lock_a_desc = scenario["lock_descriptions"].get(lock_a, lock_a)
    lock_b_desc = scenario["lock_descriptions"].get(lock_b, lock_b)

    all_locks_desc = "\n".join(
        f"- `{lk}`: {scenario['lock_descriptions'].get(lk, lk)}"
        for lk in scenario["locks"]
    )

    return f"""# INC6: Distributed Deadlock — Planner Specification

## Incident Summary

**Incident ID**: INC-DL-{seed:04d}
**Severity**: P1 (services intermittently hang, requiring manual restart)
**Domain**: {scenario["domain"]}
**Status**: Active — deadlock reproducible under concurrent load

Multiple services in the {scenario["domain"]} are intermittently hanging.
Restarting one service temporarily resolves the hang, but it recurs.
Thread dump analysis has identified the root cause.

---

## Lock Inventory

All shared locks in the system:

{all_locks_desc}

**Canonical lock acquisition order** (must be respected system-wide):

> **{lock_a}** MUST always be acquired before **{lock_b}**

This ordering is the agreed protocol. Any service that deviates creates
a potential circular wait.

---

## Root Cause: Circular Lock Dependency

**Deadlock pair**:
- `{buggy_svc}` acquires **{lock_b}** then **{lock_a}** (WRONG ORDER)
- `{good_svc}` acquires **{lock_a}** then **{lock_b}** (correct order)

**Circular wait**:

```
{buggy_svc}:  holds {lock_b}, waits for {lock_a}
{good_svc}:   holds {lock_a}, waits for {lock_b}
              ^^^^^^^^ DEADLOCK ^^^^^^^^
```

**Fix**: Change `{buggy_svc}.process_request()` to acquire `{lock_a}` first,
then `{lock_b}`. Do NOT change `{good_svc}` — it already uses the correct order.

---

## Thread Dump Analysis

The provided `thread_dump.txt` contains three threads:

| Thread | Service | State | Holds | Waiting |
|--------|---------|-------|-------|---------|
| worker-A | `{buggy_svc}` | BLOCKED | `{lock_b}` | `{lock_a}` |
| worker-B | `{good_svc}` | BLOCKED | `{lock_a}` | `{lock_b}` |
| poller (red herring) | `{buggy_svc}` | {rh_label} | *none* | *nothing* |

**Critical distinction**: The third thread (`{rh_label}`) is a **red herring**.
It is CPU-bound or sleeping and holds NO locks. It is NOT part of the deadlock.
Do not remove or modify the red herring code — it is intentional production logic.

### Red Herring Details

`{rh_id}`: {rh_desc}

---

## Fix Requirements

1. **Open** `{buggy_svc}.py` and locate `process_request()`.
2. **Swap** the lock acquisition order: acquire `{lock_a}` first, then `{lock_b}`.
3. **Do NOT touch** `{good_svc}.py` — it is already correct.
4. **Preserve** the red herring code in `{buggy_svc}.py` exactly as-is.
5. **Verify** with `python3 deadlock_sim.py --fixed` (must exit 0).
6. **Verify** with `python3 check_fix.py` (all checks must pass).
7. **Verify** both `python3 {buggy_svc}.py` and `python3 {good_svc}.py` exit 0.

---

## Constraints

- Both service files must remain syntactically valid Python.
- Both smoke tests must pass (exit 0).
- The red herring code must remain present in `{buggy_svc}.py`.
- No new deadlock may be introduced.
- Fix must address root cause; adding lock timeouts alone is insufficient.
- Do not rename locks or change their scope.

---

## Verification Checklist (for Verifier)

- [ ] `{buggy_svc}.py` parses without syntax errors
- [ ] `{good_svc}.py` parses without syntax errors
- [ ] `python3 {buggy_svc}.py` exits 0 (smoke test)
- [ ] `python3 {good_svc}.py` exits 0 (smoke test)
- [ ] `{buggy_svc}.process_request()` acquires `{lock_a}` before `{lock_b}`
- [ ] Red herring code present in `{buggy_svc}.py`
- [ ] `python3 deadlock_sim.py --fixed` exits 0
- [ ] `python3 check_fix.py` reports all checks passed
- [ ] `attestation.json` has `verdict = "pass"`
"""


def _generate_brief(
    scenario: dict,
    svc_names: list[str],
    seed: int,
) -> str:
    svc_list = ", ".join(f"`{s}.py`" for s in svc_names)
    return f"""# INC6: Distributed Deadlock Investigation (Brief)

Multiple services in the **{scenario["domain"]}** are intermittently hanging
under concurrent load. On-call has confirmed that both `{svc_names[0]}` and
`{svc_names[1]}` stop responding periodically. Restarting one service temporarily
unblocks things, but the hang recurs within minutes.

**Situation**: Thread dumps show multiple threads blocked on lock acquisition.
Several threads appear suspicious — at least one is burning CPU or sleeping —
but it is unclear which thread(s) are actually deadlocked and which are red
herrings. The system uses shared threading locks to protect critical resources.

**Goal**: Identify the deadlock root cause, fix the lock ordering, and verify
that services still function correctly.

**Workspace files**:
- {svc_list} — Python service files (one has a lock-ordering bug)
- `thread_dump.txt` — Thread dump from a live deadlock event
- `deadlock_sim.py` — Simulation script; run with `--fixed` to verify the fix
- `check_fix.py` — Automated fix checker

**What to do**:
1. Inspect `thread_dump.txt` to identify which services are deadlocked.
2. Inspect the service `.py` files to find the mismatched lock acquisition order.
3. Fix the lock ordering in the offending service (do not modify the other service).
4. Be careful: one thread in the dump looks alarming but is NOT the deadlock.
5. Run `python3 deadlock_sim.py --fixed` to confirm no deadlock after fix.
6. Run `python3 check_fix.py` and ensure all checks pass.
7. Run both service files directly to confirm smoke tests pass.

The Planner has thread dump analysis identifying the exact deadlock cycle,
the correct lock acquisition order, and which thread is a red herring.
Coordinate with the Planner before implementing.

**Constraint**: The fix must correct the lock ordering. Simply adding timeouts
to lock acquisition is not sufficient to pass grading.
"""


# ---------------------------------------------------------------------------
# Main Generator class
# ---------------------------------------------------------------------------

class Generator(TaskGenerator):
    task_id = "INC6_deadlock"
    domain = "incident_response"
    difficulty = "expert"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # Select scenario
        scenario = LOCK_SCENARIOS[seed % len(LOCK_SCENARIOS)]

        # Select the two locks that form the deadlock cycle
        lock_a, lock_b = _pick_deadlock_locks(scenario, rng)

        # Select which service is buggy (has wrong lock order)
        # The buggy service index is seed-derived but always within range
        svc_names = scenario["services"]
        buggy_idx = (seed // len(LOCK_SCENARIOS)) % len(svc_names)
        good_idx = 1 - buggy_idx  # works for 2-service scenarios
        if len(svc_names) > 2:
            good_idx = (buggy_idx + 1) % len(svc_names)

        buggy_svc = svc_names[buggy_idx]
        good_svc = svc_names[good_idx]

        # Select red herring
        rh = RED_HERRINGS[seed % len(RED_HERRINGS)]

        # All locks in this scenario
        all_locks = scenario["locks"]

        # Generate service files
        buggy_code = _build_service_file(
            svc_name=buggy_svc,
            svc_index=buggy_idx,
            scenario=scenario,
            lock_a=lock_a,
            lock_b=lock_b,
            is_buggy_service=True,
            red_herring=rh,
            rng=rng,
            seed=seed,
            all_locks=all_locks,
        )
        good_code = _build_service_file(
            svc_name=good_svc,
            svc_index=good_idx,
            scenario=scenario,
            lock_a=lock_a,
            lock_b=lock_b,
            is_buggy_service=False,
            red_herring=rh,
            rng=rng,
            seed=seed,
            all_locks=all_locks,
        )

        # Generate auxiliary files
        thread_dump = _build_thread_dump(
            scenario=scenario,
            lock_a=lock_a,
            lock_b=lock_b,
            buggy_svc=buggy_svc,
            good_svc=good_svc,
            red_herring=rh,
            rng=rng,
            seed=seed,
        )
        deadlock_sim = _build_deadlock_sim(
            scenario=scenario,
            lock_a=lock_a,
            lock_b=lock_b,
            svc_names=svc_names,
            buggy_svc_name=buggy_svc,
            good_svc_name=good_svc,
            seed=seed,
        )
        check_fix = _build_check_fix(
            scenario=scenario,
            lock_a=lock_a,
            lock_b=lock_b,
            buggy_svc_name=buggy_svc,
            good_svc_name=good_svc,
            red_herring=rh,
            seed=seed,
        )

        # Generate spec and brief
        spec_md = _generate_spec(
            scenario=scenario,
            lock_a=lock_a,
            lock_b=lock_b,
            buggy_svc=buggy_svc,
            good_svc=good_svc,
            red_herring=rh,
            seed=seed,
            rng=rng,
        )
        brief_md = _generate_brief(
            scenario=scenario,
            svc_names=svc_names,
            seed=seed,
        )

        expected = {
            "scenario_id": scenario["id"],
            "lock_a": lock_a,
            "lock_b": lock_b,
            "buggy_service": buggy_svc,
            "good_service": good_svc,
            "correct_order": [lock_a, lock_b],
            "red_herring_id": rh["id"],
            "red_herring_marker": {
                "busy_wait_cpu": "_poll_queue",
                "spin_hash": "_background_hash_worker",
                "retry_backoff": "_retry_with_backoff",
            }[rh["id"]],
            "deadlock_type": "circular_lock_dependency",
            "fix_location": f"{buggy_svc}.py:process_request",
            "seed": seed,
        }

        workspace_files = {
            f"{buggy_svc}.py": buggy_code,
            f"{good_svc}.py": good_code,
            "thread_dump.txt": thread_dump,
            "deadlock_sim.py": deadlock_sim,
            "check_fix.py": check_fix,
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )
