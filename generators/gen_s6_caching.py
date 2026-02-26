"""
Parameterized generator for S6: Caching.

TNI Pattern A,C,D (Multi-pattern):
  - Spec has: per-endpoint caching rules (GET /users: cache 5 min, GET /products:
    cache 1 hr, GET /search: no cache, POST endpoints: invalidate related cache),
    exact cache key format, and invalidation triggers (write to users table
    invalidates GET /users cache).
  - Brief says: "The application is slow. Add caching to improve performance."
  - TNI drivers:
    A) Spec has precise TTL values; brief has no numbers.
    C) Spec lists which endpoints must NOT be cached (GET /search); brief omits.
    D) Spec defines cache key format and invalidation table-to-endpoint mapping;
       brief gives no cross-system contract detail.

Each seed produces a different:
  - Resource domain (users/products/orders | articles/comments/tags | employees/departments/projects)
  - TTL values for each GET endpoint (drawn from constrained pools)
  - Cache key format (prefix:resource:param | resource_v2:param | app:resource:param)
  - Which GET endpoint is explicitly uncacheable
  - Invalidation rules (which POST/PUT triggers which GET cache clear)
  - App name and port
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# ── Domain pools ──────────────────────────────────────────────────────────────

# Each tuple: (resource_a, resource_b, resource_c, app_name, db_prefix)
RESOURCE_DOMAINS = [
    ("users",     "products",    "orders",      "shop_api",    "shop"),
    ("articles",  "comments",    "tags",        "blog_api",    "blog"),
    ("employees", "departments", "projects",    "hr_api",      "hr"),
    ("customers", "invoices",    "payments",    "billing_api", "billing"),
    ("posts",     "categories",  "media",       "cms_api",     "cms"),
    ("events",    "attendees",   "venues",      "events_api",  "events"),
]

# TTL pools for GET /resource_a (seconds): short-lived data
TTL_A_OPTIONS = [300, 180, 120, 600]   # 5 min, 3 min, 2 min, 10 min

# TTL pools for GET /resource_b (seconds): longer-lived data
TTL_B_OPTIONS = [3600, 1800, 7200, 900]  # 1 hr, 30 min, 2 hr, 15 min

# TTL pools for GET /resource_c (seconds): medium
TTL_C_OPTIONS = [600, 300, 1200, 3600]

# Cache key format templates — {prefix} and {resource} are filled at gen time
CACHE_KEY_FORMATS = [
    "{prefix}:{resource}:{param}",
    "{resource}_v2:{param}",
    "{app}:{resource}:{param}",
    "cache:{prefix}:{resource}:{param}",
]

# Which resource index (0=a, 1=b, 2=c) is the "search-like" uncacheable endpoint
UNCACHEABLE_RESOURCE_IDX = [2, 0, 1]  # cycles across seeds

# Port pool
PORTS = [8000, 8080, 5000, 5050, 9000]


def _ttl_label(seconds: int) -> str:
    """Human-readable TTL string."""
    if seconds >= 3600:
        h = seconds // 3600
        return f"{h} hour{'s' if h > 1 else ''}"
    m = seconds // 60
    return f"{m} minute{'s' if m > 1 else ''}"


class Generator(TaskGenerator):
    task_id = "S6_caching"
    domain = "software"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # ── Pick domain
        domain = RESOURCE_DOMAINS[seed % len(RESOURCE_DOMAINS)]
        res_a, res_b, res_c, app_name, db_prefix = domain

        # ── Pick TTLs
        ttl_a = rng.choice(TTL_A_OPTIONS)
        ttl_b = rng.choice(TTL_B_OPTIONS)
        ttl_c = rng.choice(TTL_C_OPTIONS)

        # ── Pick cache key format
        key_fmt = rng.choice(CACHE_KEY_FORMATS)
        # prefix used inside key_fmt where {prefix} appears
        cache_prefix = db_prefix

        # ── Pick which resource is uncacheable (search-like)
        uncacheable_idx = UNCACHEABLE_RESOURCE_IDX[seed % len(UNCACHEABLE_RESOURCE_IDX)]
        resources_ordered = [res_a, res_b, res_c]
        ttls_ordered = [ttl_a, ttl_b, ttl_c]
        uncacheable_res = resources_ordered[uncacheable_idx]

        # Cacheable resources and their TTLs
        cacheable = [
            (r, t) for i, (r, t) in enumerate(zip(resources_ordered, ttls_ordered))
            if i != uncacheable_idx
        ]

        # ── Pick port
        port = rng.choice(PORTS)

        # ── Build cache key helper (resolves format string for a given resource+param)
        def make_cache_key(resource: str, param: str = "all") -> str:
            return (key_fmt
                    .replace("{prefix}", cache_prefix)
                    .replace("{resource}", resource)
                    .replace("{param}", param)
                    .replace("{app}", app_name))

        # ── Invalidation rules: POST /resource_a -> clear resource_a GET cache
        #    POST /resource_b -> clear resource_b GET cache
        #    (uncacheable resource has no cache to invalidate)
        invalidation_rules: list[dict] = []
        for res, ttl in cacheable:
            invalidation_rules.append({
                "trigger_method": "POST",
                "trigger_endpoint": f"/{res}",
                "invalidates_key_pattern": make_cache_key(res, "*"),
                "invalidates_resource": res,
            })
        # Also PUT triggers invalidation for res_a
        invalidation_rules.append({
            "trigger_method": "PUT",
            "trigger_endpoint": f"/{cacheable[0][0]}/{{id}}",
            "invalidates_key_pattern": make_cache_key(cacheable[0][0], "*"),
            "invalidates_resource": cacheable[0][0],
        })

        # ── Build workspace files
        app_py = self._build_app_py(
            app_name, port, res_a, res_b, res_c,
            ttl_a, ttl_b, ttl_c, uncacheable_res,
            key_fmt, cache_prefix, cacheable, invalidation_rules,
        )
        cache_py = self._build_cache_py()

        # ── Spec and brief
        spec_md = self._build_spec(
            app_name, port, res_a, res_b, res_c,
            ttl_a, ttl_b, ttl_c, uncacheable_res,
            key_fmt, cache_prefix, cacheable, invalidation_rules,
        )
        brief_md = self._build_brief(app_name)

        # ── Expected (ground truth for grader)
        expected = {
            "app_name": app_name,
            "port": port,
            "resources": [res_a, res_b, res_c],
            "ttl_a": ttl_a,
            "ttl_b": ttl_b,
            "ttl_c": ttl_c,
            "ttl_map": {
                res_a: ttl_a,
                res_b: ttl_b,
                res_c: ttl_c,
            },
            "uncacheable_resource": uncacheable_res,
            "cacheable_resources": [r for r, _ in cacheable],
            "cache_key_format": key_fmt,
            "cache_prefix": cache_prefix,
            "cache_keys": {
                r: make_cache_key(r, "all")
                for r, _ in cacheable
            },
            "cache_key_single": {
                r: make_cache_key(r, "{id}")
                for r in resources_ordered
            },
            "invalidation_rules": invalidation_rules,
        }

        return GeneratedTask(
            task_id="S6_caching",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files={
                "app.py": app_py,
                "cache.py": cache_py,
            },
            metadata={"difficulty": "hard", "tni_patterns": ["A", "C", "D"]},
        )

    # ── Workspace file builders ───────────────────────────────────────────────

    def _build_app_py(
        self,
        app_name: str,
        port: int,
        res_a: str,
        res_b: str,
        res_c: str,
        ttl_a: int,
        ttl_b: int,
        ttl_c: int,
        uncacheable_res: str,
        key_fmt: str,
        cache_prefix: str,
        cacheable: list,
        invalidation_rules: list,
    ) -> str:
        """Generate app.py — a Flask API with simulated slow DB calls but NO caching yet."""
        singular_a = res_a.rstrip("s")
        singular_b = res_b.rstrip("s")
        singular_c = res_c.rstrip("s")

        return f'''"""
{app_name} - Python REST API
This API has simulated slow database calls.  Caching has NOT been implemented yet.
"""
import time
import json
from flask import Flask, request, jsonify

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Simulated database (in-memory store)
# ---------------------------------------------------------------------------

_DB = {{
    "{res_a}": [
        {{"id": 1, "name": "Alpha", "value": 100}},
        {{"id": 2, "name": "Beta",  "value": 200}},
    ],
    "{res_b}": [
        {{"id": 1, "name": "Widget",  "price": 9.99}},
        {{"id": 2, "name": "Gadget",  "price": 49.99}},
    ],
    "{res_c}": [
        {{"id": 1, "name": "Foo", "category": "misc"}},
        {{"id": 2, "name": "Bar", "category": "misc"}},
    ],
}}


def _slow_db_query(table: str, record_id=None):
    """Simulate a slow database query (100 ms latency)."""
    time.sleep(0.1)
    rows = _DB.get(table, [])
    if record_id is not None:
        rows = [r for r in rows if r["id"] == record_id]
    return rows


def _slow_db_write(table: str, record: dict):
    """Simulate a slow database write."""
    time.sleep(0.05)
    _DB.setdefault(table, []).append(record)


# ---------------------------------------------------------------------------
# GET endpoints (no caching — this is what needs to be added)
# ---------------------------------------------------------------------------

@app.route("/{res_a}", methods=["GET"])
def get_{res_a}():
    data = _slow_db_query("{res_a}")
    return jsonify({{"data": data, "source": "db"}})


@app.route("/{res_a}/<int:item_id>", methods=["GET"])
def get_{singular_a}(item_id):
    data = _slow_db_query("{res_a}", item_id)
    if not data:
        return jsonify({{"error": "not found"}}), 404
    return jsonify({{"data": data[0], "source": "db"}})


@app.route("/{res_b}", methods=["GET"])
def get_{res_b}():
    data = _slow_db_query("{res_b}")
    return jsonify({{"data": data, "source": "db"}})


@app.route("/{res_b}/<int:item_id>", methods=["GET"])
def get_{singular_b}(item_id):
    data = _slow_db_query("{res_b}", item_id)
    if not data:
        return jsonify({{"error": "not found"}}), 404
    return jsonify({{"data": data[0], "source": "db"}})


@app.route("/{res_c}", methods=["GET"])
def get_{res_c}():
    # NOTE: this endpoint must NOT be cached (results change too frequently)
    data = _slow_db_query("{res_c}")
    return jsonify({{"data": data, "source": "db"}})


@app.route("/{res_c}/<int:item_id>", methods=["GET"])
def get_{singular_c}(item_id):
    data = _slow_db_query("{res_c}", item_id)
    if not data:
        return jsonify({{"error": "not found"}}), 404
    return jsonify({{"data": data[0], "source": "db"}})


# ---------------------------------------------------------------------------
# POST / PUT endpoints (writes — must invalidate related cache on write)
# ---------------------------------------------------------------------------

@app.route("/{res_a}", methods=["POST"])
def create_{singular_a}():
    body = request.get_json(force=True) or {{}}
    new_id = max((r["id"] for r in _DB["{res_a}"]), default=0) + 1
    record = {{"id": new_id, **body}}
    _slow_db_write("{res_a}", record)
    return jsonify({{"created": record}}), 201


@app.route("/{res_a}/<int:item_id>", methods=["PUT"])
def update_{singular_a}(item_id):
    body = request.get_json(force=True) or {{}}
    rows = _DB.get("{res_a}", [])
    for row in rows:
        if row["id"] == item_id:
            row.update(body)
            return jsonify({{"updated": row}})
    return jsonify({{"error": "not found"}}), 404


@app.route("/{res_b}", methods=["POST"])
def create_{singular_b}():
    body = request.get_json(force=True) or {{}}
    new_id = max((r["id"] for r in _DB["{res_b}"]), default=0) + 1
    record = {{"id": new_id, **body}}
    _slow_db_write("{res_b}", record)
    return jsonify({{"created": record}}), 201


@app.route("/{res_c}", methods=["POST"])
def create_{singular_c}():
    body = request.get_json(force=True) or {{}}
    new_id = max((r["id"] for r in _DB.get("{res_c}", [])), default=0) + 1
    record = {{"id": new_id, **body}}
    _slow_db_write("{res_c}", record)
    return jsonify({{"created": record}}), 201


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.route("/health", methods=["GET"])
def health():
    return jsonify({{"status": "ok", "service": "{app_name}"}})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port={port}, debug=False)
'''

    def _build_cache_py(self) -> str:
        """Generate cache.py — empty module stub the agent must implement."""
        return '''"""
Cache module — implement caching logic here.

You must implement an in-process cache that supports:
  - set(key, value, ttl_seconds): store value with expiry
  - get(key): return value if present and not expired, else None
  - delete(key): remove a specific key
  - delete_pattern(pattern): remove all keys matching a glob pattern (e.g. "users:*")
  - clear(): remove all keys

The cache must respect TTLs (time-to-live). Expired entries must return None from get().
"""


class Cache:
    """In-process TTL cache.  Implement the methods below."""

    def __init__(self):
        # TODO: initialize your storage here
        pass

    def set(self, key: str, value, ttl_seconds: int) -> None:
        """Store value under key, expiring after ttl_seconds."""
        # TODO: implement
        raise NotImplementedError("Cache.set() not implemented")

    def get(self, key: str):
        """Return cached value, or None if missing/expired."""
        # TODO: implement
        raise NotImplementedError("Cache.get() not implemented")

    def delete(self, key: str) -> None:
        """Delete a specific key (no-op if absent)."""
        # TODO: implement
        raise NotImplementedError("Cache.delete() not implemented")

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a glob pattern.
        Returns the number of deleted keys.
        Supports '*' as wildcard (e.g. 'users:*' matches 'users:all', 'users:42').
        """
        # TODO: implement
        raise NotImplementedError("Cache.delete_pattern() not implemented")

    def clear(self) -> None:
        """Remove all keys from the cache."""
        # TODO: implement
        raise NotImplementedError("Cache.clear() not implemented")


# Module-level singleton used by app.py
cache = Cache()
'''

    # ── Spec and brief builders ───────────────────────────────────────────────

    def _build_spec(
        self,
        app_name: str,
        port: int,
        res_a: str,
        res_b: str,
        res_c: str,
        ttl_a: int,
        ttl_b: int,
        ttl_c: int,
        uncacheable_res: str,
        key_fmt: str,
        cache_prefix: str,
        cacheable: list,
        invalidation_rules: list,
    ) -> str:
        singular_a = res_a.rstrip("s")
        singular_b = res_b.rstrip("s")

        # Build cache key examples
        def ex_key(res, param="all"):
            return (key_fmt
                    .replace("{prefix}", cache_prefix)
                    .replace("{resource}", res)
                    .replace("{param}", param)
                    .replace("{app}", app_name))

        cacheable_res = [r for r, _ in cacheable]
        ttl_map = {res_a: ttl_a, res_b: ttl_b, res_c: ttl_c}

        inv_section = ""
        for rule in invalidation_rules:
            inv_section += (
                f"- `{rule['trigger_method']} {rule['trigger_endpoint']}` → "
                f"invalidate all cache keys matching `{rule['invalidates_key_pattern']}`\n"
            )

        return f"""# S6 Caching — Full Specification

## Overview

`{app_name}` is a REST API running on port `{port}`.  Database queries are
slow (simulated 100 ms latency per call).  You must add caching so that
repeated GET requests are served from an in-process cache instead of hitting
the database every time.

## File Layout

```
app.py      ← Flask application (modify to add caching)
cache.py    ← Cache module stub (implement Cache class here)
```

## Per-Endpoint Caching Rules

| Endpoint | Method | Cache? | TTL |
|---|---|---|---|
| `/{res_a}` | GET | YES | {ttl_a} seconds ({_ttl_label(ttl_a)}) |
| `/{res_a}/{{id}}` | GET | YES | {ttl_a} seconds ({_ttl_label(ttl_a)}) |
| `/{res_b}` | GET | YES | {ttl_b} seconds ({_ttl_label(ttl_b)}) |
| `/{res_b}/{{id}}` | GET | YES | {ttl_b} seconds ({_ttl_label(ttl_b)}) |
| `/{res_c}` | GET | **NO** | — (do not cache; results change too frequently) |
| `/{res_c}/{{id}}` | GET | **NO** | — |
| `/{res_a}` | POST | — | (write — see invalidation) |
| `/{res_a}/{{id}}` | PUT | — | (write — see invalidation) |
| `/{res_b}` | POST | — | (write — see invalidation) |

## Cache Key Format

Cache keys must follow this exact format:

```
{key_fmt}
```

Where:
- `{{prefix}}` = `{cache_prefix}`
- `{{resource}}` = the resource name (e.g. `{res_a}`, `{res_b}`)
- `{{param}}` = `all` for list endpoints, the numeric `id` for single-item endpoints
- `{{app}}` = `{app_name}`

### Example Cache Keys

| Endpoint | Cache Key |
|---|---|
| `GET /{res_a}` | `{ex_key(res_a, 'all')}` |
| `GET /{res_a}/42` | `{ex_key(res_a, '42')}` |
| `GET /{res_b}` | `{ex_key(res_b, 'all')}` |
| `GET /{res_b}/7` | `{ex_key(res_b, '7')}` |

## Cache Invalidation Rules

When a write operation succeeds, the related GET cache entries MUST be
invalidated immediately (before the response is returned to the caller):

{inv_section}
Use `cache.delete_pattern(pattern)` to remove all matching keys at once.

## Cache Implementation Requirements

Implement `Cache` in `cache.py`:

- `set(key, value, ttl_seconds)` — store with TTL
- `get(key)` — return value if present and not expired, else `None`
- `delete(key)` — remove a specific key
- `delete_pattern(pattern)` — remove all keys matching a glob pattern (`*` wildcard)
- `clear()` — remove all keys

A module-level singleton `cache = Cache()` is already defined in `cache.py`;
`app.py` must import and use it.

## Response Format

Cached responses MUST include `"source": "cache"` in the JSON body.
Database responses MUST include `"source": "db"` in the JSON body.
This allows the grader to verify cache hits vs. misses.

## What Must NOT Change

- All existing endpoints must continue to function correctly.
- The `/{res_c}` endpoint must **never** serve from cache.
- POST/PUT responses are not cached.
- The `GET /health` endpoint is not cached.

## Acceptance Criteria

1. `GET /{res_a}` and `GET /{res_b}` (and their `/{{id}}` variants) are cached
   with correct TTLs.
2. `GET /{res_c}` is never cached.
3. A second identical GET request returns `"source": "cache"` and completes
   significantly faster than the first.
4. `POST /{res_a}` clears the `{res_a}` cache entries before responding.
5. `PUT /{res_a}/{{id}}` clears the `{res_a}` cache entries before responding.
6. `POST /{res_b}` clears the `{res_b}` cache entries before responding.
7. After a POST write to `{res_a}`, the next GET returns fresh data (no stale
   cache).
8. Expired entries (TTL elapsed) are not returned by `cache.get()`.
9. `cache.delete_pattern()` supports `*` wildcard matching.
10. All existing API tests pass without modification.
"""

    def _build_brief(self, app_name: str) -> str:
        return f"""# Task Brief

The `{app_name}` application is slow. Database queries are taking too long
and users are experiencing high latency.

**Add caching to improve performance.**

The workspace contains:
- `app.py` — the Flask API
- `cache.py` — an empty cache module stub

Implement caching so the application responds faster on repeated requests.
"""


# ── Standalone test (python -m generators.gen_s6_caching) ────────────────────

if __name__ == "__main__":
    import json
    gen = Generator()
    for seed in (0, 1, 2):
        task = gen.generate(seed)
        print(f"\n=== Seed {seed} ===")
        print(f"app_name={task.expected['app_name']}  port={task.expected['port']}")
        print(f"uncacheable={task.expected['uncacheable_resource']}")
        print(f"ttl_map={task.expected['ttl_map']}")
        print(f"cache_key_format={task.expected['cache_key_format']}")
        print(f"cache_keys={json.dumps(task.expected['cache_keys'], indent=2)}")
        print(f"invalidation_rules count={len(task.expected['invalidation_rules'])}")
    print("\nCross-seed validation:", gen.validate_cross_seed(0, 1), gen.validate_cross_seed(1, 2))
