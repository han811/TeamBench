"""
Parameterized generator for RINC8: Memory Leak — Unbounded Cache/Pool.

Inspiration: Common production memory leak patterns documented in post-mortems
at Netflix, Cloudflare, and others. A growing data structure (cache, connection
pool, event listener list) with no eviction/cleanup causes gradual OOM.

Seeds vary: leak type (unbounded dict cache / connection pool not returned /
event listener accumulation), service name, resource counts.

Grading: 7 checks — leak fixed, eviction/cleanup present, memory stable
under load, functionality preserved.
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

LEAK_VARIANTS = [
    {
        "leak_type": "unbounded_cache",
        "service": "ProductCacheService",
        "description": "in-memory cache with no eviction policy — grows without bound",
        "fix": "add LRU eviction with maxsize limit using functools.lru_cache or manual dict with size cap",
        "resource": "cache entries",
        "metric": "cache size",
    },
    {
        "leak_type": "connection_pool_leak",
        "service": "DatabasePoolService",
        "description": "connection pool where connections are acquired but never released on error paths",
        "fix": "use context manager (with conn_pool.get() as conn) to guarantee release on all exit paths",
        "resource": "database connections",
        "metric": "active connections",
    },
    {
        "leak_type": "event_listener_leak",
        "service": "EventBusService",
        "description": "event listeners registered but never deregistered — listener list grows without bound",
        "fix": "return unsubscribe token from subscribe(); call unsubscribe in cleanup/teardown",
        "resource": "event listeners",
        "metric": "listener count",
    },
]


class Generator(TaskGenerator):
    task_id = "RINC8_memory_leak"
    domain = "incident"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        v = LEAK_VARIANTS[seed % len(LEAK_VARIANTS)]
        max_size = rng.choice([100, 500, 1000])
        n_requests = rng.randint(200, 500)

        workspace_files = {
            "service.py": self._gen_service(v, max_size),
            "test_memory.py": self._gen_tests(v, max_size, n_requests),
            "requirements.txt": "pytest>=7.0\n",
        }

        expected = {
            "seed": seed,
            "leak_type": v["leak_type"],
            "service": v["service"],
            "fix": v["fix"],
            "max_size": max_size,
            "n_requests": n_requests,
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._gen_spec(v, max_size, n_requests),
            brief_md=self._gen_brief(v),
            expected=expected,
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "incident", "pattern": "memory_leak"},
        )

    def _gen_service(self, v: dict, max_size: int) -> str:
        if v["leak_type"] == "unbounded_cache":
            return self._gen_cache_service(v, max_size)
        elif v["leak_type"] == "connection_pool_leak":
            return self._gen_pool_service(v, max_size)
        else:
            return self._gen_event_service(v, max_size)

    def _gen_cache_service(self, v: dict, max_size: int) -> str:
        return f'''\
"""
{v["service"]}: Caches product lookups in memory.

MEMORY LEAK: The cache dict is unbounded — every unique product_id
ever requested stays in memory forever. Under production load with
millions of unique keys, this causes OOM.

Incident pattern: Cloudflare/Netflix-style unbounded memoization caches.
"""
import time
from typing import Optional


# MEMORY LEAK: unbounded dict — no eviction policy
_cache: dict = {{}}
_cache_hits = 0
_cache_misses = 0


def _fetch_product_from_db(product_id: str) -> dict:
    """Simulate a DB fetch (slow)."""
    time.sleep(0.001)
    return {{
        "id": product_id,
        "name": f"Product {{product_id}}",
        "price": len(product_id) * 1.5,
        "cached_at": time.time(),
    }}


def get_product(product_id: str) -> dict:
    """Get product by ID, using in-memory cache.

    VULNERABLE: cache dict grows without bound.
    Every unique product_id is stored forever.
    Fix: implement LRU eviction with maxsize={max_size}.
    """
    global _cache_hits, _cache_misses
    if product_id in _cache:
        _cache_hits += 1
        return _cache[product_id]
    # LEAK: no eviction before inserting
    _cache_misses += 1
    product = _fetch_product_from_db(product_id)
    _cache[product_id] = product  # grows forever
    return product


def cache_stats() -> dict:
    return {{
        "size": len(_cache),
        "hits": _cache_hits,
        "misses": _cache_misses,
        "max_size": {max_size},
    }}


def clear_cache():
    """Clear entire cache (for testing only)."""
    global _cache_hits, _cache_misses
    _cache.clear()
    _cache_hits = 0
    _cache_misses = 0
'''

    def _gen_pool_service(self, v: dict, max_size: int) -> str:
        return f'''\
"""
{v["service"]}: Connection pool for database access.

MEMORY LEAK: Connections are acquired from the pool but not returned
on error paths. Pool exhausts; new requests block or fail.

Incident pattern: Common in pre-context-manager code where error handling
forgets to call conn.release() or conn.close().
"""
import threading
import time
from contextlib import contextmanager


class Connection:
    """Simulated database connection."""
    _id_counter = 0

    def __init__(self):
        Connection._id_counter += 1
        self.id = Connection._id_counter
        self.active = True

    def query(self, sql: str) -> list:
        if not self.active:
            raise RuntimeError("Connection already closed")
        time.sleep(0.001)
        return [{{"sql": sql, "conn_id": self.id}}]

    def close(self):
        self.active = False


class ConnectionPool:
    """Pool of database connections."""

    def __init__(self, max_connections: int = {max_size}):
        self.max_connections = max_connections
        self._pool: list[Connection] = [Connection() for _ in range(max_connections)]
        self._in_use: list[Connection] = []
        self._lock = threading.Lock()

    def acquire(self) -> Connection:
        with self._lock:
            if not self._pool:
                raise RuntimeError(f"Connection pool exhausted ({{len(self._in_use)}} in use)")
            conn = self._pool.pop()
            self._in_use.append(conn)
            return conn

    def release(self, conn: Connection):
        with self._lock:
            if conn in self._in_use:
                self._in_use.remove(conn)
                self._pool.append(conn)

    def stats(self) -> dict:
        with self._lock:
            return {{
                "available": len(self._pool),
                "in_use": len(self._in_use),
                "max": self.max_connections,
            }}


# Global pool
_pool = ConnectionPool(max_connections={max_size})


def execute_query(sql: str) -> list:
    """Execute a SQL query using a pooled connection.

    VULNERABLE: connection not released on exception path.
    After enough errors, pool exhausts and all queries fail.
    Fix: use a context manager or try/finally to guarantee release.
    """
    conn = _pool.acquire()
    # LEAK: if query raises, conn is never released back to pool
    results = conn.query(sql)
    _pool.release(conn)
    return results


def execute_query_with_error(sql: str) -> list:
    """Execute a query that always raises — demonstrates the leak."""
    conn = _pool.acquire()
    # LEAK: exception prevents release
    raise RuntimeError(f"Query failed: {{sql}}")
    _pool.release(conn)  # never reached
    return []


def pool_stats() -> dict:
    return _pool.stats()


def reset_pool():
    """Reset pool for testing."""
    global _pool
    _pool = ConnectionPool(max_connections={max_size})
'''

    def _gen_event_service(self, v: dict, max_size: int) -> str:
        return f'''\
"""
{v["service"]}: Pub/sub event bus.

MEMORY LEAK: Listeners are registered but never deregistered.
Each time a component subscribes (e.g., on every HTTP request),
a new listener is added. The listener list grows without bound.

Incident pattern: React/Node.js EventEmitter memory warnings,
Python asyncio uncleaned callbacks.
"""
import threading
from typing import Callable, Optional


class EventBus:
    """Simple synchronous event bus.

    VULNERABLE: subscribe() adds listeners but there is no
    unsubscribe mechanism. Listener list grows forever.
    """

    def __init__(self):
        self._listeners: dict[str, list[Callable]] = {{}}
        self._lock = threading.Lock()
        self._event_counts: dict[str, int] = {{}}

    def subscribe(self, event: str, handler: Callable) -> None:
        """Register a handler for an event.

        LEAK: no return value for unsubscription, no max_listeners limit.
        Each call permanently adds to the listener list.
        Fix: return an unsubscribe token; add max_listeners={max_size} guard.
        """
        with self._lock:
            if event not in self._listeners:
                self._listeners[event] = []
            # LEAK: no eviction, no duplicate check, no limit
            self._listeners[event].append(handler)

    def publish(self, event: str, data: dict) -> int:
        """Publish an event to all registered handlers."""
        with self._lock:
            handlers = list(self._listeners.get(event, []))
            self._event_counts[event] = self._event_counts.get(event, 0) + 1
        called = 0
        for handler in handlers:
            try:
                handler(data)
                called += 1
            except Exception:
                pass
        return called

    def listener_count(self, event: str) -> int:
        with self._lock:
            return len(self._listeners.get(event, []))

    def stats(self) -> dict:
        with self._lock:
            return {{
                "events": list(self._listeners.keys()),
                "listener_counts": {{e: len(ls) for e, ls in self._listeners.items()}},
                "total_listeners": sum(len(ls) for ls in self._listeners.values()),
                "max_size": {max_size},
            }}


_bus = EventBus()


def get_bus() -> EventBus:
    return _bus


def reset_bus():
    global _bus
    _bus = EventBus()
'''

    def _gen_tests(self, v: dict, max_size: int, n_requests: int) -> str:
        if v["leak_type"] == "unbounded_cache":
            return self._gen_cache_tests(v, max_size, n_requests)
        elif v["leak_type"] == "connection_pool_leak":
            return self._gen_pool_tests(v, max_size, n_requests)
        else:
            return self._gen_event_tests(v, max_size, n_requests)

    def _gen_cache_tests(self, v: dict, max_size: int, n_requests: int) -> str:
        return f'''\
"""Memory leak tests for {v["service"]} — unbounded cache."""
import pytest
import importlib
import service as svc


@pytest.fixture(autouse=True)
def reset():
    svc.clear_cache()
    yield
    svc.clear_cache()


def test_cache_returns_correct_data():
    product = svc.get_product("prod_001")
    assert product["id"] == "prod_001"
    assert "name" in product


def test_cache_hit_on_second_request():
    svc.get_product("prod_hit_test")
    before = svc.cache_stats()["hits"]
    svc.get_product("prod_hit_test")
    assert svc.cache_stats()["hits"] > before


def test_cache_bounded_under_load():
    """Cache size must not exceed max_size after many unique requests."""
    for i in range({n_requests}):
        svc.get_product(f"unique_product_{{i}}")
    stats = svc.cache_stats()
    assert stats["size"] <= {max_size}, (
        f"Cache size {{stats['size']}} exceeds max_size {max_size} — memory leak detected"
    )


def test_cache_evicts_old_entries():
    """When cache is full, old entries should be evicted (LRU)."""
    # Fill cache beyond max_size
    for i in range({max_size} + 50):
        svc.get_product(f"eviction_test_{{i}}")
    stats = svc.cache_stats()
    assert stats["size"] <= {max_size}, (
        f"No eviction: cache size {{stats['size']}} after filling to {max_size + 50}"
    )


def test_memory_stable_across_repeated_requests():
    """Repeatedly requesting the same keys must not grow the cache."""
    for _ in range(3):
        for i in range(20):
            svc.get_product(f"stable_{{i}}")
    stats = svc.cache_stats()
    assert stats["size"] <= 20, f"Cache grew for repeated keys: size={{stats['size']}}"
'''

    def _gen_pool_tests(self, v: dict, max_size: int, n_requests: int) -> str:
        return f'''\
"""Memory/resource leak tests for {v["service"]} — connection pool."""
import pytest
import service as svc


@pytest.fixture(autouse=True)
def reset():
    svc.reset_pool()
    yield
    svc.reset_pool()


def test_normal_query_works():
    result = svc.execute_query("SELECT 1")
    assert isinstance(result, list)


def test_connection_released_after_success():
    """After a successful query, connection must return to pool."""
    before = svc.pool_stats()["available"]
    svc.execute_query("SELECT 1")
    after = svc.pool_stats()["available"]
    assert after == before, (
        f"Connection not released: available went {{before}} → {{after}}"
    )


def test_connection_released_after_error():
    """Even if query raises, connection must return to pool."""
    before = svc.pool_stats()["available"]
    try:
        svc.execute_query_with_error("SELECT fail")
    except RuntimeError:
        pass
    after = svc.pool_stats()["available"]
    assert after == before, (
        f"Connection leaked on error: available went {{before}} → {{after}} — use try/finally"
    )


def test_pool_not_exhausted_after_repeated_errors():
    """Repeated failed queries must not exhaust the pool."""
    for _ in range({max_size} + 5):
        try:
            svc.execute_query_with_error("SELECT fail")
        except Exception:
            pass
    stats = svc.pool_stats()
    assert stats["available"] > 0, (
        f"Pool exhausted: {{stats['available']}} available — connection leak on error path"
    )


def test_concurrent_queries_succeed():
    """Concurrent queries must all get connections and release them."""
    import threading
    errors = []
    def do_query():
        try:
            svc.execute_query("SELECT 1")
        except Exception as e:
            errors.append(str(e))
    threads = [threading.Thread(target=do_query) for _ in range(min({max_size}//2, 10))]
    for t in threads: t.start()
    for t in threads: t.join()
    assert not errors, f"Concurrent queries failed: {{errors}}"
'''

    def _gen_event_tests(self, v: dict, max_size: int, n_requests: int) -> str:
        return f'''\
"""Memory leak tests for {v["service"]} — event listener accumulation."""
import pytest
import service as svc


@pytest.fixture(autouse=True)
def reset():
    svc.reset_bus()
    yield
    svc.reset_bus()


def test_publish_calls_listener():
    bus = svc.get_bus()
    received = []
    bus.subscribe("test_event", lambda d: received.append(d))
    bus.publish("test_event", {{"msg": "hello"}})
    assert received == [{{"msg": "hello"}}]


def test_listener_count_bounded():
    """Listener count must not grow beyond max_size."""
    bus = svc.get_bus()
    for i in range({n_requests}):
        bus.subscribe("load_event", lambda d: None)
    count = bus.listener_count("load_event")
    assert count <= {max_size}, (
        f"Listener count {{count}} exceeds max_size {max_size} — listener leak detected"
    )


def test_unsubscribe_removes_listener():
    """subscribe() must return a token; calling it removes the listener."""
    bus = svc.get_bus()
    received = []
    token = bus.subscribe("unsub_event", lambda d: received.append(d))
    assert token is not None, "subscribe() must return an unsubscribe token"
    # Unsubscribe
    token()  # call the token to unsubscribe
    bus.publish("unsub_event", {{"msg": "after unsub"}})
    assert received == [], "Listener still called after unsubscribe"


def test_publish_after_all_unsub():
    """After all listeners unsubscribed, publish returns 0 calls."""
    bus = svc.get_bus()
    tokens = []
    for _ in range(5):
        tokens.append(bus.subscribe("cleanup_event", lambda d: None))
    for t in tokens:
        t()
    called = bus.publish("cleanup_event", {{}})
    assert called == 0, f"Listeners still firing after unsubscribe: called={{called}}"


def test_stats_reflect_listener_count():
    bus = svc.get_bus()
    bus.subscribe("stat_event", lambda d: None)
    bus.subscribe("stat_event", lambda d: None)
    stats = bus.stats()
    assert stats["listener_counts"].get("stat_event", 0) <= {max_size}
'''

    def _gen_spec(self, v: dict, max_size: int, n_requests: int) -> str:
        return f"""# RINC8: Memory Leak — {v["leak_type"].replace("_", " ").title()}

## Incident Background
Common production memory leak pattern documented in post-mortems at Netflix,
Cloudflare, and others. A growing data structure ({v["resource"]}) with no
eviction or cleanup causes gradual memory growth until OOM kills the process.

## Service: {v["service"]}
File: `service.py`

## Problem
{v["description"]}

The `{v["metric"]}` grows without bound. Under load with {n_requests}+ unique
requests, memory usage grows proportionally with no upper bound.

**Monitoring signature:** gradual RSS/heap increase over hours/days, OOM
restarts at ~2-3x normal memory usage.

## Required Fix
{v["fix"]}

Key constraint: `max_size = {max_size}` — the data structure must not hold
more than {max_size} {v["resource"]} at any time.

## Acceptance Criteria
1. After {n_requests} unique requests, `{v["metric"]}` ≤ {max_size}
2. Old entries evicted / resources released when limit reached
3. Normal functionality preserved (cache hits, queries, event delivery)
4. Concurrent usage does not cause pool exhaustion
5. Cleanup mechanism (eviction token / context manager) is implemented
6. All tests pass: `pytest test_memory.py -v`

## Files
- `service.py` — fix the memory leak
- `test_memory.py` — do NOT modify
"""

    def _gen_brief(self, v: dict) -> str:
        return f"""# RINC8: Memory Leak Fix (Brief)

The {v["service"]} is leaking memory in production. Monitoring shows
{v["metric"]} growing without bound, causing periodic OOM restarts.

Fix the leak in `service.py`.

Verify with:
```
pytest test_memory.py -v
```

**Files to fix:** `service.py`
**Do NOT modify:** `test_memory.py`
"""
