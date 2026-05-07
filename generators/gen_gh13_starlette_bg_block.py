"""
Parameterized generator for GH13_starlette_bg_block.

Each seed produces a different async web-app domain (notification/analytics/audit)
with a middleware that wraps call_next() using BaseHTTPMiddleware.  The bug is
that a slow background task appended to the response blocks all subsequent
requests because BaseHTTPMiddleware keeps the request/response lifecycle open
until all background tasks complete.

Bug: middleware.py uses BaseHTTPMiddleware (dispatch / call_next pattern).
     Background tasks added to response.background run BEFORE the middleware
     yields control back, so concurrent requests queue behind the slow task.
Fix: replace BaseHTTPMiddleware with a pure ASGI middleware that does NOT
     wait for response.background tasks, OR move the slow work to a
     non-blocking background mechanism (e.g. asyncio.create_task after
     response is sent), OR restructure so dispatch returns immediately.

Seeds vary: app domain, route paths, background task duration, service names.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

DOMAIN_CONFIGS = [
    {
        "domain": "notification service",
        "app_name": "notify_app",
        "middleware_name": "NotificationMiddleware",
        "bg_task_name": "send_notification",
        "route_main": "/notify",
        "route_health": "/health",
        "bg_sleep": 3,
        "bg_desc": "send an async notification",
        "request_desc": "notification request",
    },
    {
        "domain": "analytics service",
        "app_name": "analytics_app",
        "middleware_name": "AnalyticsMiddleware",
        "bg_task_name": "record_event",
        "route_main": "/track",
        "route_health": "/ping",
        "bg_sleep": 3,
        "bg_desc": "record an analytics event",
        "request_desc": "tracking request",
    },
    {
        "domain": "audit logging service",
        "app_name": "audit_app",
        "middleware_name": "AuditMiddleware",
        "bg_task_name": "write_audit_log",
        "route_main": "/action",
        "route_health": "/status",
        "bg_sleep": 3,
        "bg_desc": "write an audit log entry",
        "request_desc": "action request",
    },
]


class Generator(TaskGenerator):
    task_id = "GH13_starlette_bg_block"
    domain = "Real-World GitHub"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        cfg = DOMAIN_CONFIGS[seed % len(DOMAIN_CONFIGS)]
        port = rng.randint(8100, 8199)

        workspace_files = self._make_workspace(cfg, port)
        spec_md = self._gen_spec(cfg, port)
        brief_md = self._gen_brief(cfg)

        return GeneratedTask(
            task_id="GH13_starlette_bg_block",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "domain": cfg["domain"],
                "app_name": cfg["app_name"],
                "middleware_name": cfg["middleware_name"],
                "bg_task_name": cfg["bg_task_name"],
                "port": port,
                "bug": "BaseHTTPMiddleware_blocks_on_background_tasks",
                "fix": "replace with raw ASGI middleware or schedule work after response",
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "medium", "category": "Real-World GitHub"},
        )

    # ── workspace files ────────────────────────────────────────────────────

    def _make_workspace(self, cfg: dict, port: int) -> dict:
        return {
            "app.py": self._gen_app(cfg),
            "middleware.py": self._gen_middleware(cfg),
            "test_app.py": self._gen_tests(cfg),
        }

    def _gen_middleware(self, cfg: dict) -> str:
        name = cfg["middleware_name"]
        bg_task = cfg["bg_task_name"]
        bg_sleep = cfg["bg_sleep"]
        bg_desc = cfg["bg_desc"]

        return f'''\
"""
Middleware for {cfg["domain"]}.

BUG: This middleware inherits from BaseHTTPMiddleware.
Starlette's BaseHTTPMiddleware keeps the ASGI send/receive lifecycle open
until ALL background tasks attached to the response have completed.
This means a slow background task blocks the connection, preventing other
concurrent requests from being processed until it finishes.
"""
import asyncio
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.background import BackgroundTask


async def {bg_task}(request_id: str) -> None:
    """Simulate a slow background operation: {bg_desc}.

    This takes {bg_sleep} seconds to complete.
    """
    await asyncio.sleep({bg_sleep})
    # In production this would write to a DB, call an external API, etc.


class {name}(BaseHTTPMiddleware):
    """Middleware that attaches a background task to every response.

    BUG: Because this inherits BaseHTTPMiddleware, the call_next() lifecycle
    does not return until the background task completes.  Concurrent requests
    are therefore serialized behind each slow background task.
    """

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        # Attach background task — triggers BEFORE middleware releases connection
        response.background = BackgroundTask(
            {bg_task}, request_id=str(id(request))
        )
        return response
'''

    def _gen_app(self, cfg: dict) -> str:
        app_name = cfg["app_name"]
        mw_name = cfg["middleware_name"]
        route_main = cfg["route_main"]
        route_health = cfg["route_health"]
        domain = cfg["domain"]
        request_desc = cfg["request_desc"]

        return f'''\
"""
{domain} application.

This app registers {mw_name} and exposes two routes:
  {route_main}   — the primary endpoint that triggers background work
  {route_health} — a lightweight health check
"""
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from middleware import {mw_name}


async def handle_main(request: Request) -> JSONResponse:
    """Handle a {request_desc}."""
    return JSONResponse({{"status": "ok", "route": "{route_main}"}})


async def handle_health(request: Request) -> JSONResponse:
    """Lightweight health-check endpoint — must respond immediately."""
    return JSONResponse({{"status": "healthy"}})


{app_name} = Starlette(
    routes=[
        Route("{route_main}", handle_main, methods=["GET", "POST"]),
        Route("{route_health}", handle_health, methods=["GET"]),
    ]
)

{app_name}.add_middleware({mw_name})
'''

    def _gen_tests(self, cfg: dict) -> str:
        app_name = cfg["app_name"]
        route_main = cfg["route_main"]
        route_health = cfg["route_health"]
        domain = cfg["domain"]
        bg_sleep = cfg["bg_sleep"]
        # Test expects second request returns well before background task finishes
        fast_threshold = 2  # seconds — well under bg_sleep

        return f'''\
"""
Tests for {domain} concurrency behaviour.

The key requirement: a slow background task attached to a response must NOT
block subsequent requests.  A health-check sent concurrently with a main
request must respond in < {fast_threshold}s even though the background task
sleeps for {bg_sleep}s.
"""
import asyncio
import time
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.mark.asyncio
async def test_background_task_does_not_block_concurrent_request():
    """Second request must complete in < {fast_threshold}s while background task runs."""
    from app import {app_name}

    transport = ASGITransport(app={app_name})
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:

        async def first_request():
            return await client.get("{route_main}")

        async def second_request():
            # Small delay so first request starts first, then we fire immediately
            await asyncio.sleep(0.1)
            start = time.monotonic()
            resp = await client.get("{route_health}")
            elapsed = time.monotonic() - start
            return resp, elapsed

        first, (second_resp, elapsed) = await asyncio.gather(
            first_request(),
            second_request(),
        )

    assert second_resp.status_code == 200, (
        f"Health check returned {{second_resp.status_code}}"
    )
    assert elapsed < {fast_threshold}, (
        f"Health check took {{elapsed:.2f}}s — background task is blocking "
        f"concurrent requests (expected < {fast_threshold}s)"
    )


@pytest.mark.asyncio
async def test_main_route_returns_200():
    """Main route must return 200 with status ok."""
    from app import {app_name}

    transport = ASGITransport(app={app_name})
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("{route_main}")

    assert resp.status_code == 200
    assert resp.json().get("status") == "ok"


@pytest.mark.asyncio
async def test_health_route_returns_healthy():
    """Health endpoint must return 200 with status healthy."""
    from app import {app_name}

    transport = ASGITransport(app={app_name})
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("{route_health}")

    assert resp.status_code == 200
    assert resp.json().get("status") == "healthy"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
'''

    # ── spec / brief ───────────────────────────────────────────────────────

    def _gen_spec(self, cfg: dict, port: int) -> str:
        domain = cfg["domain"]
        app_name = cfg["app_name"]
        mw_name = cfg["middleware_name"]
        bg_task = cfg["bg_task_name"]
        route_main = cfg["route_main"]
        route_health = cfg["route_health"]
        bg_sleep = cfg["bg_sleep"]

        return f"""\
# GH13: BaseHTTPMiddleware Blocks on Background Tasks — Full Specification (Planner Only)

## Overview

The workspace implements a {domain} using Starlette. A middleware class
`{mw_name}` attaches a slow background task (`{bg_task}`, {bg_sleep}s) to
every response. There is **one structural bug** in `middleware.py`.

## Program Structure

- `middleware.py` — {mw_name} with the bug (BaseHTTPMiddleware)
- `app.py` — Starlette application (correct, do not modify)
- `test_app.py` — pytest-asyncio tests that detect the bug

## The Bug

**Location:** `middleware.py` — the class inherits `BaseHTTPMiddleware`.

**Root cause:** Starlette's `BaseHTTPMiddleware` uses an internal streaming
adapter that keeps the ASGI `send` callable open until all `BackgroundTask`
objects attached to the response have completed.  Concretely:

1. Request A arrives, `dispatch()` calls `call_next(request)`.
2. `dispatch()` attaches `BackgroundTask({bg_task}, ...)` to the response.
3. `BaseHTTPMiddleware` does NOT return from `dispatch()` until `{bg_task}`
   finishes ({bg_sleep}s later).
4. During those {bg_sleep}s no other request can be processed.

This is a known Starlette issue: https://github.com/encode/starlette/issues/919

**Fix options (any one is acceptable):**

**Option A — Raw ASGI middleware (recommended):**
```python
class {mw_name}:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        await self.app(scope, receive, send)
        # Schedule background work AFTER response is sent
        if scope["type"] == "http":
            import asyncio
            asyncio.create_task({bg_task}(request_id=str(id(scope))))
```

**Option B — asyncio.create_task inside dispatch:**
Keep BaseHTTPMiddleware but use `asyncio.create_task()` instead of
`BackgroundTask` so the work runs independently of the response lifecycle.

## Acceptance Criteria

1. A concurrent health-check request completes in < 2s while `{bg_task}` runs
2. `{route_main}` still returns 200 `{{"status": "ok"}}`
3. `{route_health}` still returns 200 `{{"status": "healthy"}}`
4. All tests pass: `pytest test_app.py -v`

## Important Notes

- Fix is in `middleware.py` only
- Do NOT modify `app.py` or `test_app.py`
- The fix must not remove the background task entirely — it still needs to run
"""

    def _gen_brief(self, cfg: dict) -> str:
        domain = cfg["domain"]
        mw_name = cfg["middleware_name"]
        route_health = cfg["route_health"]
        bg_sleep = cfg["bg_sleep"]

        return f"""\
# GH13: Background Task Blocks Requests (Brief)

Fix the {domain} so background tasks don't block other concurrent requests.

Currently, a slow background task causes the `{route_health}` health-check
to wait {bg_sleep}s instead of responding immediately.

Verify with:
```
pytest test_app.py -v
```

**Files to fix:** `middleware.py`
**Do NOT modify:** `app.py` or `test_app.py`

Follow the Planner's guidance precisely.
"""
