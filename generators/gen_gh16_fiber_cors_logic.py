"""
Parameterized generator for GH16_fiber_cors_logic.

Each seed produces a different Go HTTP server with a CORS middleware that has
a logic error: the guard uses || (OR) instead of && (AND) to decide when to
skip adding CORS headers.

Bug: cors.go skips CORS headers when (origin == "" || method == ""), but the
     correct check is (origin == "" && method == "") — i.e., only skip when
     BOTH headers are absent (non-CORS request).  With OR, any request missing
     just one of the two headers gets no CORS headers.
Fix: change || to && in the guard condition.

Seeds vary: domain, allowed origins, route paths, service name, allowed methods.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

DOMAIN_CONFIGS = [
    {
        "domain": "API gateway",
        "module": "apigateway",
        "service_name": "APIGateway",
        "cors_middleware_name": "CORSMiddleware",
        "route_api": "/api/data",
        "route_health": "/health",
        "allowed_origins": ["https://app.example.com", "https://dashboard.example.com"],
        "allowed_methods": ["GET", "POST", "PUT", "DELETE"],
        "handler_name": "DataHandler",
        "health_handler_name": "HealthHandler",
    },
    {
        "domain": "web service",
        "module": "webservice",
        "service_name": "WebService",
        "cors_middleware_name": "CORSMiddleware",
        "route_api": "/api/items",
        "route_health": "/ping",
        "allowed_origins": ["https://frontend.myapp.io", "https://admin.myapp.io"],
        "allowed_methods": ["GET", "POST", "PATCH", "DELETE"],
        "handler_name": "ItemsHandler",
        "health_handler_name": "PingHandler",
    },
    {
        "domain": "REST backend",
        "module": "restbackend",
        "service_name": "RESTBackend",
        "cors_middleware_name": "CORSMiddleware",
        "route_api": "/v1/resources",
        "route_health": "/status",
        "allowed_origins": ["https://client.service.net", "https://portal.service.net"],
        "allowed_methods": ["GET", "POST", "PUT"],
        "handler_name": "ResourceHandler",
        "health_handler_name": "StatusHandler",
    },
]


class Generator(TaskGenerator):
    task_id = "GH16_fiber_cors_logic"
    domain = "Real-World GitHub"
    difficulty = "easy"
    languages = ["go"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        cfg = DOMAIN_CONFIGS[seed % len(DOMAIN_CONFIGS)]
        port = rng.randint(8300, 8399)
        origin = rng.choice(cfg["allowed_origins"])

        workspace_files = self._make_workspace(cfg, port, origin)
        spec_md = self._gen_spec(cfg, port, origin)
        brief_md = self._gen_brief(cfg)

        return GeneratedTask(
            task_id="GH16_fiber_cors_logic",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "domain": cfg["domain"],
                "module": cfg["module"],
                "port": port,
                "origin": origin,
                "bug": "cors_guard_uses_OR_instead_of_AND",
                "fix": "change || to && in cors.go guard condition",
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "easy", "category": "Real-World GitHub"},
        )

    # ── workspace files ────────────────────────────────────────────────────

    def _make_workspace(self, cfg: dict, port: int, origin: str) -> dict:
        return {
            "main.go": self._gen_main(cfg, port),
            "cors.go": self._gen_cors(cfg),
            "main_test.go": self._gen_tests(cfg, origin),
            "go.mod": f"module {cfg['module']}\n\ngo 1.21\n",
        }

    def _gen_cors(self, cfg: dict) -> str:
        mw_name = cfg["cors_middleware_name"]
        origins = cfg["allowed_origins"]
        methods = cfg["allowed_methods"]
        domain = cfg["domain"]
        origins_str = ", ".join(f'"{o}"' for o in origins)
        methods_str = ", ".join(f'"{m}"' for m in methods)

        return f'''\
package main

import (
\t"net/http"
\t"strings"
)

var allowedOrigins = []string{{{origins_str}}}
var allowedMethods = []string{{{methods_str}}}

// {mw_name} adds CORS headers to responses for cross-origin requests.
//
// A request is considered a CORS request when it carries an Origin header.
// A preflight request additionally carries Access-Control-Request-Method.
//
// BUG: the guard below uses || (OR) instead of && (AND).
// With OR, ANY request that lacks EITHER header is skipped — this means
// real cross-origin GET/POST requests (which have Origin but no
// Access-Control-Request-Method) never receive CORS headers.
func {mw_name}(next http.Handler) http.Handler {{
\treturn http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {{
\t\torigin := r.Header.Get("Origin")
\t\trequestMethod := r.Header.Get("Access-Control-Request-Method")

\t\t// BUG: should be && (skip only when BOTH are absent = non-CORS request)
\t\t// With ||, we skip when EITHER is absent — breaks real (non-preflight) requests
\t\tif origin == "" || requestMethod == "" {{
\t\t\tnext.ServeHTTP(w, r)
\t\t\treturn
\t\t}}

\t\t// Check if origin is allowed
\t\tallowed := false
\t\tfor _, o := range allowedOrigins {{
\t\t\tif o == origin {{
\t\t\t\tallowed = true
\t\t\t\tbreak
\t\t\t}}
\t\t}}

\t\tif allowed {{
\t\t\tw.Header().Set("Access-Control-Allow-Origin", origin)
\t\t\tw.Header().Set("Access-Control-Allow-Methods", strings.Join(allowedMethods, ", "))
\t\t\tw.Header().Set("Access-Control-Allow-Headers", "Content-Type, Authorization")
\t\t\tw.Header().Set("Access-Control-Max-Age", "86400")
\t\t}}

\t\t// Handle preflight
\t\tif r.Method == http.MethodOptions {{
\t\t\tw.WriteHeader(http.StatusNoContent)
\t\t\treturn
\t\t}}

\t\tnext.ServeHTTP(w, r)
\t}})
}}
'''

    def _gen_main(self, cfg: dict, port: int) -> str:
        module = cfg["module"]
        service_name = cfg["service_name"]
        mw_name = cfg["cors_middleware_name"]
        route_api = cfg["route_api"]
        route_health = cfg["route_health"]
        handler_name = cfg["handler_name"]
        health_handler_name = cfg["health_handler_name"]
        domain = cfg["domain"]

        return f'''\
package main

import (
\t"encoding/json"
\t"fmt"
\t"net/http"
)

// {handler_name} serves the main API endpoint.
func {handler_name}(w http.ResponseWriter, r *http.Request) {{
\tw.Header().Set("Content-Type", "application/json")
\tjson.NewEncoder(w).Encode(map[string]string{{"status": "ok", "service": "{service_name}"}})
}}

// {health_handler_name} serves the health check endpoint.
func {health_handler_name}(w http.ResponseWriter, r *http.Request) {{
\tw.Header().Set("Content-Type", "application/json")
\tjson.NewEncoder(w).Encode(map[string]string{{"status": "healthy"}})
}}

func main() {{
\tmux := http.NewServeMux()
\tmux.Handle("{route_api}", {mw_name}(http.HandlerFunc({handler_name})))
\tmux.Handle("{route_health}", http.HandlerFunc({health_handler_name}))
\tfmt.Printf("{domain} server listening on :{port}\\n")
\thttp.ListenAndServe(":{port}", mux)
}}
'''

    def _gen_tests(self, cfg: dict, origin: str) -> str:
        module = cfg["module"]
        mw_name = cfg["cors_middleware_name"]
        handler_name = cfg["handler_name"]
        route_api = cfg["route_api"]
        domain = cfg["domain"]
        allowed_origins = cfg["allowed_origins"]

        return f'''\
package main

import (
\t"net/http"
\t"net/http/httptest"
\t"testing"
)

func makeHandler() http.Handler {{
\treturn {mw_name}(http.HandlerFunc({handler_name}))
}}

// TestRealCORSRequestGetsHeaders verifies that a real (non-preflight) cross-origin
// request — which has Origin but NOT Access-Control-Request-Method — receives
// CORS headers.  With the bug (||), such requests are skipped.
func TestRealCORSRequestGetsHeaders(t *testing.T) {{
\thandler := makeHandler()

\treq := httptest.NewRequest(http.MethodGet, "{route_api}", nil)
\treq.Header.Set("Origin", "{origin}")
\t// Real CORS request: has Origin but NO Access-Control-Request-Method
\tw := httptest.NewRecorder()
\thandler.ServeHTTP(w, req)

\tif w.Code != http.StatusOK {{
\t\tt.Fatalf("expected 200, got %d", w.Code)
\t}}

\tgot := w.Header().Get("Access-Control-Allow-Origin")
\tif got != "{origin}" {{
\t\tt.Errorf(
\t\t\t"real CORS GET: expected Access-Control-Allow-Origin=%q, got %q\\n"+
\t\t\t"(bug: || in guard skips CORS headers when Access-Control-Request-Method is absent)",
\t\t\t"{origin}", got,
\t\t)
\t}}
}}

// TestPreflightRequestGetsHeaders verifies that a preflight (OPTIONS) request
// — which has BOTH Origin AND Access-Control-Request-Method — receives CORS
// headers.  This works even with the bug; it verifies the positive case.
func TestPreflightRequestGetsHeaders(t *testing.T) {{
\thandler := makeHandler()

\treq := httptest.NewRequest(http.MethodOptions, "{route_api}", nil)
\treq.Header.Set("Origin", "{origin}")
\treq.Header.Set("Access-Control-Request-Method", "GET")
\tw := httptest.NewRecorder()
\thandler.ServeHTTP(w, req)

\tif w.Code != http.StatusNoContent {{
\t\tt.Fatalf("expected 204 for preflight, got %d", w.Code)
\t}}

\tgot := w.Header().Get("Access-Control-Allow-Origin")
\tif got != "{origin}" {{
\t\tt.Errorf("preflight: expected Access-Control-Allow-Origin=%q, got %q", "{origin}", got)
\t}}
}}

// TestNonCORSRequestNoHeaders verifies that requests without Origin get no
// CORS headers (not a cross-origin request).
func TestNonCORSRequestNoHeaders(t *testing.T) {{
\thandler := makeHandler()

\treq := httptest.NewRequest(http.MethodGet, "{route_api}", nil)
\t// No Origin header — same-origin or non-browser request
\tw := httptest.NewRecorder()
\thandler.ServeHTTP(w, req)

\tif w.Code != http.StatusOK {{
\t\tt.Fatalf("expected 200, got %d", w.Code)
\t}}

\tgot := w.Header().Get("Access-Control-Allow-Origin")
\tif got != "" {{
\t\tt.Errorf("non-CORS request: expected no CORS headers, got Access-Control-Allow-Origin=%q", got)
\t}}
}}

// TestDisallowedOriginGetsNoHeaders verifies that an unknown origin is rejected.
func TestDisallowedOriginGetsNoHeaders(t *testing.T) {{
\thandler := makeHandler()

\treq := httptest.NewRequest(http.MethodGet, "{route_api}", nil)
\treq.Header.Set("Origin", "https://evil.example.com")
\tw := httptest.NewRecorder()
\thandler.ServeHTTP(w, req)

\tgot := w.Header().Get("Access-Control-Allow-Origin")
\tif got != "" {{
\t\tt.Errorf("disallowed origin: expected no CORS headers, got %q", got)
\t}}
}}
'''

    # ── spec / brief ───────────────────────────────────────────────────────

    def _gen_spec(self, cfg: dict, port: int, origin: str) -> str:
        module = cfg["module"]
        mw_name = cfg["cors_middleware_name"]
        route_api = cfg["route_api"]
        domain = cfg["domain"]
        allowed_origins = cfg["allowed_origins"]

        return f"""\
# GH16: CORS Middleware OR vs AND Logic Bug — Full Specification (Planner Only)

## Overview

The workspace implements a {domain} HTTP server with a `{mw_name}` in
`cors.go`. There is **one bug** — a `||` that should be `&&` in the guard
condition.

## Program Structure

- `cors.go` — `{mw_name}` with the OR vs AND bug
- `main.go` — server entry point and handlers (correct, do not modify)
- `main_test.go` — tests that detect the bug
- `go.mod` — module `{module}`

## The Bug

**Location:** `cors.go` — the guard `if origin == "" || requestMethod == ""`

**Root cause:** The guard is supposed to skip CORS processing only for
non-CORS requests (requests that have no `Origin` header at all).  But with
`||`, the condition is true whenever EITHER header is absent:

- Non-CORS request: `origin=""`, `requestMethod=""` → `"" || ""` = `true` ✓ skip
- Real CORS GET:    `origin="https://..."`, `requestMethod=""` → `false || true` = `true` ✗ skip (BUG)
- Preflight:        `origin="https://..."`, `requestMethod="GET"` → `false || false` = `false` ✓ process

So real (non-preflight) cross-origin GET/POST requests never receive CORS
headers, causing browsers to block them.

**Fix:** Change `||` to `&&`:
```go
if origin == "" && requestMethod == "" {{
    next.ServeHTTP(w, r)
    return
}}
```

With `&&`, CORS processing is skipped only when BOTH headers are absent
(guaranteed non-CORS request).

## Request Classification

| Request type | Origin | Req-Method header | Expected |
|---|---|---|---|
| Same-origin / non-browser | (empty) | (empty) | No CORS headers |
| Real CORS GET/POST | present | (empty) | CORS headers added |
| Preflight OPTIONS | present | present | CORS headers + 204 |

## Acceptance Criteria

1. Real CORS GET (Origin present, no Access-Control-Request-Method) → `Access-Control-Allow-Origin` header set
2. Preflight OPTIONS (both headers present) → 204 + CORS headers
3. Non-CORS request (no Origin) → no CORS headers
4. Disallowed origin → no CORS headers
5. All tests pass: `go test -v ./...`

## Important Notes

- Fix is in `cors.go` — one character change (`||` → `&&`)
- Do NOT modify `main.go` or `main_test.go`
"""

    def _gen_brief(self, cfg: dict) -> str:
        domain = cfg["domain"]
        mw_name = cfg["cors_middleware_name"]

        return f"""\
# GH16: CORS Middleware Logic Bug (Brief)

Fix the {domain} CORS middleware (`{mw_name}`) so browsers can make
cross-origin requests.

Currently, real cross-origin requests (GET/POST with an Origin header) do not
receive CORS headers — only preflight OPTIONS requests work correctly.

Verify with:
```
go test -v ./...
```

**Files to fix:** `cors.go`
**Do NOT modify:** `main.go` or `main_test.go`

Follow the Planner's guidance precisely.
"""
