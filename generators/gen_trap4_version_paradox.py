"""
Parameterized generator for TRAP4: Version Paradox.

Each seed uses a different library domain (database, HTTP client, message queue).
The structural challenge is identical: 6 v2 patterns to address, but 2 of them
are imported by a pinned vendor dependency and must be kept as compat shims.

Seeds:
  0 — database connection library (dblib)
  1 — HTTP client library (httpclient)
  2 — message queue library (mqclient)
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# Per-seed configuration
_CONFIGS = [
    {
        # Seed 0: database connection library
        "lib_name": "mylib",
        "domain": "database",
        "description": "database connection and query library",
        # v3 API names (the goal state)
        "run_fn": "run",
        "results_fn": "results",
        "configure_fn": "configure",
        "query_cls": "Query",
        "builder_cls": "Builder",
        "connect_fn": "connect",
        # v2 names (to be migrated or shimmed)
        "execute_fn": "execute",
        "fetch_all_fn": "fetch_all",
        "set_config_fn": "set_config",
        "raw_query_cls": "RawQuery",
        # The two v2 names imported by the vendor (must stay as shims)
        "compat_factory": "connect_v2",
        "compat_builder": "QueryBuilder",
        # Domain-specific details
        "host_param": "host",
        "default_host": "localhost",
        "port_param": "port",
        "default_port": 5432,
        "example_query": "SELECT * FROM users WHERE id = ?",
        "vendor_pkg": "legacy_adapter",
        "vendor_desc": "Legacy database adapter for on-premise deployments",
    },
    {
        # Seed 1: HTTP client library
        "lib_name": "mylib",
        "domain": "http",
        "description": "HTTP client and request builder library",
        "run_fn": "send",
        "results_fn": "responses",
        "configure_fn": "configure",
        "query_cls": "Request",
        "builder_cls": "RequestBuilder",
        "connect_fn": "connect",
        # v2 names
        "execute_fn": "execute",
        "fetch_all_fn": "fetch_all",
        "set_config_fn": "set_config",
        "raw_query_cls": "RawRequest",
        # The two v2 names imported by the vendor (must stay as shims)
        "compat_factory": "connect_v2",
        "compat_builder": "QueryBuilder",
        # Domain-specific
        "host_param": "base_url",
        "default_host": "https://api.example.com",
        "port_param": "timeout",
        "default_port": 30,
        "example_query": "GET /users/42",
        "vendor_pkg": "legacy_adapter",
        "vendor_desc": "Legacy HTTP adapter for internal service mesh",
    },
    {
        # Seed 2: message queue library
        "lib_name": "mylib",
        "domain": "mq",
        "description": "message queue publish/subscribe library",
        "run_fn": "publish",
        "results_fn": "consume",
        "configure_fn": "configure",
        "query_cls": "Message",
        "builder_cls": "MessageBuilder",
        "connect_fn": "connect",
        # v2 names
        "execute_fn": "execute",
        "fetch_all_fn": "fetch_all",
        "set_config_fn": "set_config",
        "raw_query_cls": "RawMessage",
        # The two v2 names imported by the vendor (must stay as shims)
        "compat_factory": "connect_v2",
        "compat_builder": "QueryBuilder",
        # Domain-specific
        "host_param": "broker",
        "default_host": "amqp://localhost",
        "port_param": "prefetch",
        "default_port": 10,
        "example_query": "PUBLISH orders.created {id: 42}",
        "vendor_pkg": "legacy_adapter",
        "vendor_desc": "Legacy MQ adapter for on-premise message brokers",
    },
]


class Generator(TaskGenerator):
    task_id = "TRAP4_version_paradox"
    domain = "SWE"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        cfg = _CONFIGS[seed % len(_CONFIGS)]

        workspace_files = self._make_workspace(cfg, seed)

        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", "TRAP4_version_paradox"
        )
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="TRAP4_version_paradox",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "fully_migrated": [
                    cfg["execute_fn"],
                    cfg["fetch_all_fn"],
                    cfg["set_config_fn"],
                    cfg["raw_query_cls"],
                ],
                "kept_as_shims": [cfg["compat_factory"], cfg["compat_builder"]],
                "v3_api": [
                    cfg["run_fn"],
                    cfg["results_fn"],
                    cfg["configure_fn"],
                    cfg["query_cls"],
                ],
                "seed": seed,
                "domain": cfg["domain"],
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "SWE", "domain": cfg["domain"]},
        )

    def _make_workspace(self, cfg: dict, seed: int) -> dict:
        files = {}
        c = cfg  # short alias

        # ── mylib/__init__.py ─────────────────────────────────────────────────
        files["mylib/__init__.py"] = f'''"""
{c["lib_name"]}: {c["description"]}.

v2 API (being migrated — see MIGRATION_GUIDE.md):
  {c["execute_fn"]}(), {c["fetch_all_fn"]}(), {c["set_config_fn"]}(),
  {c["raw_query_cls"]}, {c["compat_factory"]}(), {c["compat_builder"]}

v3 API (migration target):
  {c["run_fn"]}(), {c["results_fn"]}(), {c["configure_fn"]}(),
  {c["query_cls"]}, {c["connect_fn"]}(), {c["builder_cls"]}
"""
from mylib.core import (
    {c["connect_fn"]},
    {c["run_fn"]},
    {c["results_fn"]},
    {c["configure_fn"]},
    {c["query_cls"]},
    {c["builder_cls"]},
    # v2 aliases kept for backward compat — migrate these per MIGRATION_GUIDE.md
    {c["execute_fn"]},
    {c["fetch_all_fn"]},
    {c["set_config_fn"]},
    {c["raw_query_cls"]},
    {c["compat_factory"]},
    {c["compat_builder"]},
)

__version__ = "2.9.1"
__all__ = [
    "{c["connect_fn"]}",
    "{c["run_fn"]}",
    "{c["results_fn"]}",
    "{c["configure_fn"]}",
    "{c["query_cls"]}",
    "{c["builder_cls"]}",
    # v2 (deprecated)
    "{c["execute_fn"]}",
    "{c["fetch_all_fn"]}",
    "{c["set_config_fn"]}",
    "{c["raw_query_cls"]}",
    "{c["compat_factory"]}",
    "{c["compat_builder"]}",
]
'''

        # ── mylib/core.py ─────────────────────────────────────────────────────
        # Contains all v2 AND v3 APIs (executor must refactor this)
        files["mylib/core.py"] = f'''"""
Core implementation for {c["lib_name"]}.

This module currently contains both v2 and v3 APIs mixed together.
Per MIGRATION_GUIDE.md, v2 APIs should be removed or shimmed.
"""
import warnings
from typing import Any, Optional


# ── Internal connection state ─────────────────────────────────────────────────

_CONFIG: dict = {{
    "{c["host_param"]}": "{c["default_host"]}",
    "{c["port_param"]}": {c["default_port"]},
    "timeout": 30,
    "pool_size": 5,
}}


# ── v3 API ────────────────────────────────────────────────────────────────────

class {c["query_cls"]}:
    """v3: Structured query/request object."""

    def __init__(self, expression: str, params: Optional[tuple] = None):
        self.expression = expression
        self.params = params or ()

    def __repr__(self) -> str:
        return f"{c["query_cls"]}({{self.expression!r}})"


class {c["builder_cls"]}:
    """v3: Fluent builder for constructing {c["query_cls"]} objects."""

    def __init__(self):
        self._parts: list[str] = []
        self._params: list[Any] = []

    def add(self, part: str, *params: Any) -> "{c["builder_cls"]}":
        self._parts.append(part)
        self._params.extend(params)
        return self

    def build(self) -> {c["query_cls"]}:
        return {c["query_cls"]}(" ".join(self._parts), tuple(self._params))


class Connection:
    """Internal connection object (both v2 and v3)."""

    def __init__(self, {c["host_param"]}: str, **kwargs):
        self.{c["host_param"]} = {c["host_param"]}
        self._kwargs = kwargs
        self._connected = True

    def close(self) -> None:
        self._connected = False


def {c["connect_fn"]}({c["host_param"]}: str = "{c["default_host"]}", **kwargs) -> Connection:
    """v3: Create a new connection."""
    return Connection({c["host_param"]}, **kwargs)


def {c["configure_fn"]}(*, {c["host_param"]}: Optional[str] = None, {c["port_param"]}: Optional[int] = None, **kwargs) -> None:
    """v3: Configure library defaults (keyword-only arguments)."""
    if {c["host_param"]} is not None:
        _CONFIG["{c["host_param"]}"] = {c["host_param"]}
    if {c["port_param"]} is not None:
        _CONFIG["{c["port_param"]}"] = {c["port_param"]}
    _CONFIG.update(kwargs)


def {c["run_fn"]}(query: {c["query_cls"]}, conn: Optional[Connection] = None) -> list:
    """v3: Execute a query/request and return results."""
    # Simulate execution
    return [dict(expression=query.expression, params=query.params)]


def {c["results_fn"]}(query: {c["query_cls"]}, conn: Optional[Connection] = None) -> list:
    """v3: Alias for {c["run_fn"]}() — returns all results."""
    return {c["run_fn"]}(query, conn)


# ── v2 API (to be migrated per MIGRATION_GUIDE.md) ───────────────────────────

class {c["raw_query_cls"]}:
    """v2: Raw query string wrapper. Migrate to {c["query_cls"]}."""

    def __init__(self, raw: str):
        self.raw = raw

    def __repr__(self) -> str:
        return f"{c["raw_query_cls"]}({{self.raw!r}})"


def {c["execute_fn"]}(raw: str, conn: Optional[Connection] = None) -> list:
    """v2: Execute a raw query string. Migrate to {c["run_fn"]}({c["query_cls"]}(...))."""
    return [{{"raw": raw, "result": "ok"}}]


def {c["fetch_all_fn"]}(raw: str, conn: Optional[Connection] = None) -> list:
    """v2: Fetch all results from raw query. Migrate to {c["results_fn"]}({c["query_cls"]}(...))."""
    return {c["execute_fn"]}(raw, conn)


def {c["set_config_fn"]}({c["host_param"]}: Optional[str] = None, {c["port_param"]}: Optional[int] = None) -> None:
    """v2: Set configuration. Migrate to {c["configure_fn"]}() with keyword-only args."""
    if {c["host_param"]} is not None:
        _CONFIG["{c["host_param"]}"] = {c["host_param"]}
    if {c["port_param"]} is not None:
        _CONFIG["{c["port_param"]}"] = {c["port_param"]}


def {c["compat_factory"]}({c["host_param"]}: str = "{c["default_host"]}", **kwargs) -> Connection:
    """v2: Legacy connection factory. Migrate callers to {c["connect_fn"]}()."""
    # NOTE: This function is imported by vendor/legacy_adapter.
    # Keep as a compatibility shim per MIGRATION_GUIDE.md section 5.
    return Connection({c["host_param"]}, **kwargs)


class {c["compat_builder"]}:
    """v2: Legacy query builder. Migrate callers to {c["builder_cls"]}."""

    # NOTE: This class is imported by vendor/legacy_adapter.
    # Keep as a compatibility shim per MIGRATION_GUIDE.md section 6.

    def __init__(self):
        self._raw_parts: list[str] = []

    def append(self, part: str) -> "{c["compat_builder"]}":
        self._raw_parts.append(part)
        return self

    def to_raw(self) -> {c["raw_query_cls"]}:
        return {c["raw_query_cls"]}(" ".join(self._raw_parts))
'''

        # ── mylib/compat.py ───────────────────────────────────────────────────
        # Empty file — executor must move shims here
        files["mylib/compat.py"] = f'''"""
Compatibility shims for {c["lib_name"]} v2 → v3 migration.

Place deprecated v2 API shims here so they can be re-exported from
mylib/__init__.py without polluting mylib/core.py.

Each shim must:
  1. Emit warnings.warn(..., DeprecationWarning, stacklevel=2)
  2. Delegate to the v3 equivalent
"""
# TODO: Move connect_v2 and QueryBuilder shims here from core.py
'''

        # ── mylib/utils.py ────────────────────────────────────────────────────
        files["mylib/utils.py"] = f'''"""Utility helpers for {c["lib_name"]}."""
import hashlib
import time
from typing import Any


def make_cache_key(*parts: Any) -> str:
    """Generate a deterministic cache key from parts."""
    raw = "|".join(str(p) for p in parts)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def retry(fn, attempts: int = 3, delay: float = 0.1):
    """Retry fn up to `attempts` times with exponential backoff."""
    last_exc = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:
            last_exc = exc
            time.sleep(delay * (2 ** i))
    raise last_exc


def chunk(lst: list, size: int) -> list:
    """Split a list into chunks of at most `size`."""
    return [lst[i:i + size] for i in range(0, len(lst), size)]
'''

        # ── vendor/legacy_adapter/__init__.py ─────────────────────────────────
        files["vendor/legacy_adapter/__init__.py"] = f'''"""
{c["vendor_desc"]}.

This package is pinned at version 1.4.2 in requirements.txt.
It imports v2 patterns from mylib that MUST remain available.
"""
# These imports MUST continue to work after migration.
# Do NOT remove connect_v2 or QueryBuilder from mylib.
from mylib import {c["compat_factory"]}, {c["compat_builder"]}

from legacy_adapter.adapter import LegacyAdapter


def create_legacy_adapter({c["host_param"]}: str = "{c["default_host"]}") -> LegacyAdapter:
    """Create a legacy adapter using the v2 connection factory."""
    conn = {c["compat_factory"]}({c["host_param"]})
    builder = {c["compat_builder"]}()
    return LegacyAdapter(conn=conn, builder=builder)


__version__ = "1.4.2"
__all__ = ["LegacyAdapter", "create_legacy_adapter"]
'''

        # ── vendor/legacy_adapter/adapter.py ──────────────────────────────────
        files["vendor/legacy_adapter/adapter.py"] = f'''"""
LegacyAdapter: wraps v2 mylib connection for on-premise integrations.
"""
from typing import Any, Optional


class LegacyAdapter:
    """Adapter that wraps v2 mylib APIs for backward-compatible integrations."""

    def __init__(self, conn, builder):
        self._conn = conn
        self._builder = builder

    def query(self, expression: str) -> list:
        """Execute a query using the v2 builder pattern."""
        self._builder.append(expression)
        raw = self._builder.to_raw()
        # Simulate result
        return [{{"expression": raw.raw, "status": "ok"}}]

    def close(self) -> None:
        """Close the underlying connection."""
        self._conn.close()

    def __repr__(self) -> str:
        return f"LegacyAdapter(conn={{self._conn!r}})"
'''

        # ── MIGRATION_GUIDE.md ────────────────────────────────────────────────
        files["MIGRATION_GUIDE.md"] = f'''# {c["lib_name"]} Migration Guide: v2 → v3

This guide documents all breaking changes between {c["lib_name"]} v2 and v3.

## Overview

Version 3 introduces a cleaner, more consistent API. All v2 patterns must be
addressed — either fully migrated or kept as compatibility shims if required by
downstream dependencies.

---

## Change 1: `{c["execute_fn"]}()` → `{c["run_fn"]}()`

**v2:**
```python
result = {c["execute_fn"]}("{c["example_query"]}")
```

**v3:**
```python
q = {c["query_cls"]}("{c["example_query"]}")
result = {c["run_fn"]}(q)
```

Action: Rename all calls. Remove `{c["execute_fn"]}` from `mylib/core.py` public API.

---

## Change 2: `{c["fetch_all_fn"]}()` → `{c["results_fn"]}()`

**v2:**
```python
rows = {c["fetch_all_fn"]}("{c["example_query"]}")
```

**v3:**
```python
q = {c["query_cls"]}("{c["example_query"]}")
rows = {c["results_fn"]}(q)
```

Action: Rename all calls. Remove `{c["fetch_all_fn"]}` from public API.

---

## Change 3: `{c["set_config_fn"]}()` → `{c["configure_fn"]}()` (new signature)

**v2:**
```python
{c["set_config_fn"]}("{c["default_host"]}", {c["default_port"]})
```

**v3 (keyword-only):**
```python
{c["configure_fn"]}({c["host_param"]}="{c["default_host"]}", {c["port_param"]}={c["default_port"]})
```

Action: Update all call sites to use keyword arguments.

---

## Change 4: `{c["raw_query_cls"]}` → `{c["query_cls"]}`

**v2:**
```python
q = {c["raw_query_cls"]}("{c["example_query"]}")
```

**v3:**
```python
q = {c["query_cls"]}("{c["example_query"]}")
```

Action: Replace class name everywhere. Remove `{c["raw_query_cls"]}` from public API.

---

## Change 5: `{c["compat_factory"]}()` — COMPATIBILITY SHIM REQUIRED

**v2:**
```python
conn = {c["compat_factory"]}("{c["default_host"]}")
```

**v3:**
```python
conn = {c["connect_fn"]}("{c["default_host"]}")
```

Action: Check `vendor/` directory. If any vendored package imports `{c["compat_factory"]}`,
keep it as a shim in `mylib/compat.py` that delegates to `{c["connect_fn"]}()` and emits
`DeprecationWarning`. Re-export from `mylib/__init__.py`.

---

## Change 6: `{c["compat_builder"]}` — COMPATIBILITY SHIM REQUIRED

**v2:**
```python
b = {c["compat_builder"]}()
b.append("SELECT 1")
raw = b.to_raw()
```

**v3:**
```python
b = {c["builder_cls"]}()
b.add("SELECT 1")
q = b.build()
```

Action: Check `vendor/` directory. If any vendored package imports `{c["compat_builder"]}`,
keep it as a shim in `mylib/compat.py` that subclasses `{c["builder_cls"]}` and emits
`DeprecationWarning` in `__init__`. Re-export from `mylib/__init__.py`.

---

## Summary Table

| v2 Pattern | v3 Replacement | Action |
|------------|----------------|--------|
| `{c["execute_fn"]}()` | `{c["run_fn"]}()` | Remove v2 |
| `{c["fetch_all_fn"]}()` | `{c["results_fn"]}()` | Remove v2 |
| `{c["set_config_fn"]}()` | `{c["configure_fn"]}()` | Remove v2 |
| `{c["raw_query_cls"]}` | `{c["query_cls"]}` | Remove v2 |
| `{c["compat_factory"]}()` | `{c["connect_fn"]}()` | **Shim** (vendor dep) |
| `{c["compat_builder"]}` | `{c["builder_cls"]}` | **Shim** (vendor dep) |
'''

        # ── requirements.txt ──────────────────────────────────────────────────
        files["requirements.txt"] = f'''# Production dependencies
legacy-adapter==1.4.2
pytest>=7.0
'''

        # ── tests/__init__.py ─────────────────────────────────────────────────
        files["tests/__init__.py"] = ""

        # ── tests/test_v3_api.py ──────────────────────────────────────────────
        files["tests/test_v3_api.py"] = f'''"""Tests for the v3 API. These must pass after migration."""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'vendor')
import pytest
import mylib


def test_query_cls_exists():
    q = mylib.{c["query_cls"]}("{c["example_query"]}")
    assert q.expression == "{c["example_query"]}"


def test_run_fn():
    q = mylib.{c["query_cls"]}("{c["example_query"]}")
    result = mylib.{c["run_fn"]}(q)
    assert isinstance(result, list)


def test_results_fn():
    q = mylib.{c["query_cls"]}("{c["example_query"]}")
    result = mylib.{c["results_fn"]}(q)
    assert isinstance(result, list)


def test_configure_fn_keyword_args():
    # v3 configure() uses keyword-only args
    mylib.{c["configure_fn"]}({c["host_param"]}="{c["default_host"]}")
    mylib.{c["configure_fn"]}({c["port_param"]}={c["default_port"]})


def test_builder_cls():
    b = mylib.{c["builder_cls"]}()
    b.add("part1")
    b.add("part2")
    q = b.build()
    assert isinstance(q, mylib.{c["query_cls"]})


def test_connect_fn():
    conn = mylib.{c["connect_fn"]}("{c["default_host"]}")
    assert conn is not None
    conn.close()


def test_v2_execute_removed():
    """After migration, execute() should not be a top-level public function."""
    # It is acceptable if execute is removed from the module entirely
    # OR if it is only accessible via compat and emits a warning
    import warnings
    if hasattr(mylib, '{c["execute_fn"]}'):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            mylib.{c["execute_fn"]}("{c["example_query"]}")
            # If still present, must emit DeprecationWarning
            assert any(issubclass(x.category, DeprecationWarning) for x in w), \\
                "{c["execute_fn"]}() must emit DeprecationWarning if still exported"


def test_v2_raw_query_removed():
    """After migration, {c["raw_query_cls"]} should not be the primary query class."""
    # {c["raw_query_cls"]} may still exist for compat, but {c["query_cls"]} must be the primary
    assert hasattr(mylib, '{c["query_cls"]}'), "v3 {c["query_cls"]} must exist"
'''

        # ── tests/test_adapter.py ─────────────────────────────────────────────
        files["tests/test_adapter.py"] = f'''"""Tests that the vendor legacy_adapter continues to work after migration."""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'vendor')
import pytest


def test_legacy_adapter_import():
    """vendor/legacy_adapter must import without errors."""
    import legacy_adapter
    assert hasattr(legacy_adapter, 'LegacyAdapter')
    assert hasattr(legacy_adapter, 'create_legacy_adapter')


def test_create_legacy_adapter():
    """create_legacy_adapter() must return a working LegacyAdapter."""
    import legacy_adapter
    adapter = legacy_adapter.create_legacy_adapter("{c["default_host"]}")
    assert adapter is not None


def test_legacy_adapter_query():
    """LegacyAdapter.query() must still work."""
    import legacy_adapter
    adapter = legacy_adapter.create_legacy_adapter("{c["default_host"]}")
    result = adapter.query("{c["example_query"]}")
    assert isinstance(result, list)
    adapter.close()


def test_compat_factory_still_importable():
    """connect_v2 must still be importable from mylib (used by vendor)."""
    import mylib
    assert hasattr(mylib, '{c["compat_factory"]}'), \\
        "{c["compat_factory"]} must remain importable (required by legacy_adapter)"


def test_compat_builder_still_importable():
    """QueryBuilder must still be importable from mylib (used by vendor)."""
    import mylib
    assert hasattr(mylib, '{c["compat_builder"]}'), \\
        "{c["compat_builder"]} must remain importable (required by legacy_adapter)"
'''

        # ── tests/test_deprecation.py ─────────────────────────────────────────
        files["tests/test_deprecation.py"] = f'''"""Tests that deprecated v2 shims emit DeprecationWarning."""
import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'vendor')
import warnings
import pytest
import mylib


def test_connect_v2_emits_deprecation():
    """connect_v2() must emit DeprecationWarning (it is a shim, not the real API)."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        conn = mylib.{c["compat_factory"]}("{c["default_host"]}")
        assert any(issubclass(x.category, DeprecationWarning) for x in w), \\
            "{c["compat_factory"]}() must emit DeprecationWarning"
        conn.close()


def test_query_builder_emits_deprecation():
    """QueryBuilder() must emit DeprecationWarning (it is a shim)."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        b = mylib.{c["compat_builder"]}()
        assert any(issubclass(x.category, DeprecationWarning) for x in w), \\
            "{c["compat_builder"]}() must emit DeprecationWarning"


def test_v3_api_has_no_deprecation_warnings():
    """v3 APIs must NOT emit DeprecationWarning."""
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        conn = mylib.{c["connect_fn"]}("{c["default_host"]}")
        q = mylib.{c["query_cls"]}("{c["example_query"]}")
        mylib.{c["run_fn"]}(q)
        mylib.{c["results_fn"]}(q)
        b = mylib.{c["builder_cls"]}()
        b.add("test")
        b.build()
        dep_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(dep_warnings) == 0, \\
            f"v3 API must not emit DeprecationWarning, got: {{dep_warnings}}"
        conn.close()
'''

        return files
