"""
Parameterized generator for GH15_gin_context_key.

Each seed produces a different Go HTTP server domain (auth/tracing/tenant)
where middleware sets a context value using a plain string key, and the
handler reads it using a different typed key type — silently getting nil
because Go's context.Context uses key identity (type + value), not just
string equality.

Bug: middleware.go sets ctx.WithValue(r.Context(), "userID", value).
     handler in main.go reads ctx.Value(contextKey("userID")) — a different
     type — so it always gets nil.
Fix: define one unexported key type (type contextKey string) and use it
     consistently in both middleware and handler.

Seeds vary: domain, key name, middleware/handler func names, route paths.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

DOMAIN_CONFIGS = [
    {
        "domain": "authentication",
        "module": "authserver",
        "key_name": "userID",
        "value_example": "alice",
        "middleware_name": "AuthMiddleware",
        "handler_name": "ProfileHandler",
        "route": "/profile",
        "value_desc": "authenticated user ID",
        "middleware_desc": "validates request and injects user identity",
        "handler_desc": "returns the current user profile",
    },
    {
        "domain": "distributed tracing",
        "module": "traceserver",
        "key_name": "traceID",
        "value_example": "abc-123-xyz",
        "middleware_name": "TraceMiddleware",
        "handler_name": "RequestHandler",
        "route": "/request",
        "value_desc": "distributed trace ID",
        "middleware_desc": "injects trace ID for request correlation",
        "handler_desc": "handles the request and echoes the trace ID",
    },
    {
        "domain": "multi-tenant service",
        "module": "tenantserver",
        "key_name": "tenantID",
        "value_example": "tenant-42",
        "middleware_name": "TenantMiddleware",
        "handler_name": "DataHandler",
        "route": "/data",
        "value_desc": "tenant identifier",
        "middleware_desc": "extracts and injects tenant ID from request header",
        "handler_desc": "returns tenant-specific data",
    },
]


class Generator(TaskGenerator):
    task_id = "GH15_gin_context_key"
    domain = "Real-World GitHub"
    difficulty = "easy"
    languages = ["go"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        cfg = DOMAIN_CONFIGS[seed % len(DOMAIN_CONFIGS)]
        port = rng.randint(8200, 8299)
        header_name = rng.choice(["X-User-ID", "X-Request-ID", "X-Tenant-ID"])

        workspace_files = self._make_workspace(cfg, port, header_name)
        spec_md = self._gen_spec(cfg, port, header_name)
        brief_md = self._gen_brief(cfg)

        return GeneratedTask(
            task_id="GH15_gin_context_key",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "seed": seed,
                "domain": cfg["domain"],
                "module": cfg["module"],
                "key_name": cfg["key_name"],
                "port": port,
                "header_name": header_name,
                "bug": "string_context_key_type_collision",
                "fix": "define unexported contextKey type used by both middleware and handler",
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "easy", "category": "Real-World GitHub"},
        )

    # ── workspace files ────────────────────────────────────────────────────

    def _make_workspace(self, cfg: dict, port: int, header_name: str) -> dict:
        return {
            "main.go": self._gen_main(cfg, port, header_name),
            "middleware.go": self._gen_middleware(cfg, header_name),
            "main_test.go": self._gen_tests(cfg, port, header_name),
            "go.mod": f"module {cfg['module']}\n\ngo 1.21\n",
        }

    def _gen_middleware(self, cfg: dict, header_name: str) -> str:
        mw_name = cfg["middleware_name"]
        key_name = cfg["key_name"]
        value_desc = cfg["value_desc"]
        mw_desc = cfg["middleware_desc"]
        domain = cfg["domain"]

        return f'''\
package main

import (
\t"context"
\t"net/http"
)

// {mw_name} {mw_desc}.
//
// BUG: this middleware uses a plain string literal "{key_name}" as the
// context key.  Go's context.WithValue requires keys to be comparable and
// recommends package-specific types to avoid collisions across packages.
// The handler in main.go reads the value using a contextKey("{key_name}")
// typed key, which is a DIFFERENT type — so context.Value() returns nil.
func {mw_name}(next http.Handler) http.Handler {{
\treturn http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {{
\t\t// BUG: using untyped string key — collides with nothing but also
\t\t// cannot be read by code that uses a typed key.
\t\tvalue := r.Header.Get("{header_name}")
\t\tif value == "" {{
\t\t\tvalue = "default-{key_name}"
\t\t}}
\t\tctx := context.WithValue(r.Context(), "{key_name}", value)
\t\tnext.ServeHTTP(w, r.WithContext(ctx))
\t}})
}}
'''

    def _gen_main(self, cfg: dict, port: int, header_name: str) -> str:
        module = cfg["module"]
        key_name = cfg["key_name"]
        handler_name = cfg["handler_name"]
        mw_name = cfg["middleware_name"]
        route = cfg["route"]
        value_desc = cfg["value_desc"]
        handler_desc = cfg["handler_desc"]
        domain = cfg["domain"]

        return f'''\
package main

import (
\t"encoding/json"
\t"fmt"
\t"net/http"
)

// contextKey is the package-local type for context keys in {module}.
// Using a typed key prevents collisions with keys from other packages.
type contextKey string

const {key_name}Key contextKey = "{key_name}"

// {handler_name} {handler_desc}.
//
// It reads the {value_desc} from the request context.
// BUG: the middleware sets the value using a plain string key "{key_name}",
// but this handler reads it using contextKey("{key_name}") — a different type.
// context.Value() compares keys by (type, value), so this always returns nil.
func {handler_name}(w http.ResponseWriter, r *http.Request) {{
\t// BUG: reads with typed key contextKey("{key_name}"), but middleware wrote
\t// with string("{key_name}") — these are different types, so value is nil.
\tvalue := r.Context().Value({key_name}Key)
\tif value == nil {{
\t\thttp.Error(w, "missing {key_name} in context", http.StatusInternalServerError)
\t\treturn
\t}}
\tw.Header().Set("Content-Type", "application/json")
\tjson.NewEncoder(w).Encode(map[string]string{{
\t\t"{key_name}": fmt.Sprintf("%v", value),
\t\t"status":    "ok",
\t}})
}}

func main() {{
\tmux := http.NewServeMux()
\tmux.Handle("{route}", {mw_name}(http.HandlerFunc({handler_name})))
\tfmt.Printf("{domain} server listening on :{port}\\n")
\thttp.ListenAndServe(":{port}", mux)
}}
'''

    def _gen_tests(self, cfg: dict, port: int, header_name: str) -> str:
        module = cfg["module"]
        key_name = cfg["key_name"]
        handler_name = cfg["handler_name"]
        mw_name = cfg["middleware_name"]
        route = cfg["route"]
        domain = cfg["domain"]
        value_example = cfg["value_example"]

        return f'''\
package main

import (
\t"encoding/json"
\t"net/http"
\t"net/http/httptest"
\t"testing"
)

// TestContextValuePropagated verifies that {mw_name} correctly injects the
// {key_name} into the request context so {handler_name} can read it.
// With the bug (string key vs contextKey type), the handler receives nil and
// returns 500.  After the fix, it must return 200 with the correct value.
func TestContextValuePropagated(t *testing.T) {{
\thandler := {mw_name}(http.HandlerFunc({handler_name}))

\treq := httptest.NewRequest(http.MethodGet, "{route}", nil)
\treq.Header.Set("{header_name}", "{value_example}")
\tw := httptest.NewRecorder()

\thandler.ServeHTTP(w, req)

\tif w.Code != http.StatusOK {{
\t\tt.Fatalf("expected 200, got %d — context value was nil (key type mismatch)", w.Code)
\t}}

\tvar body map[string]string
\tif err := json.NewDecoder(w.Body).Decode(&body); err != nil {{
\t\tt.Fatalf("failed to decode response body: %v", err)
\t}}

\tif body["{key_name}"] != "{value_example}" {{
\t\tt.Errorf("expected {key_name}=%q, got %q", "{value_example}", body["{key_name}"])
\t}}
\tif body["status"] != "ok" {{
\t\tt.Errorf("expected status=ok, got %q", body["status"])
\t}}
}}

// TestContextValueDefaultWhenHeaderAbsent verifies the fallback value is used
// when the {header_name} header is not set.
func TestContextValueDefaultWhenHeaderAbsent(t *testing.T) {{
\thandler := {mw_name}(http.HandlerFunc({handler_name}))

\treq := httptest.NewRequest(http.MethodGet, "{route}", nil)
\t// No {header_name} header
\tw := httptest.NewRecorder()

\thandler.ServeHTTP(w, req)

\tif w.Code != http.StatusOK {{
\t\tt.Fatalf("expected 200 with default value, got %d", w.Code)
\t}}
}}

// TestContextKeyTypeCollision documents the exact bug: writing with a string
// key and reading with a contextKey type must NOT match.
// After the fix, both middleware and handler must use the same key type.
func TestContextKeyTypeUnified(t *testing.T) {{
\t// This test verifies the fix indirectly: if TestContextValuePropagated
\t// passes, both sides must be using the same key type.
\thandler := {mw_name}(http.HandlerFunc({handler_name}))

\tfor _, headerVal := range []string{{"{value_example}", "another-value", "test-123"}} {{
\t\treq := httptest.NewRequest(http.MethodGet, "{route}", nil)
\t\treq.Header.Set("{header_name}", headerVal)
\t\tw := httptest.NewRecorder()
\t\thandler.ServeHTTP(w, req)

\t\tif w.Code != http.StatusOK {{
\t\t\tt.Errorf("headerVal=%q: expected 200, got %d", headerVal, w.Code)
\t\t\tcontinue
\t\t}}
\t\tvar body map[string]string
\t\tif err := json.NewDecoder(w.Body).Decode(&body); err != nil {{
\t\t\tt.Errorf("headerVal=%q: decode error: %v", headerVal, err)
\t\t\tcontinue
\t\t}}
\t\tif body["{key_name}"] != headerVal {{
\t\t\tt.Errorf("headerVal=%q: got {key_name}=%q", headerVal, body["{key_name}"])
\t\t}}
\t}}
}}
'''

    # ── spec / brief ───────────────────────────────────────────────────────

    def _gen_spec(self, cfg: dict, port: int, header_name: str) -> str:
        module = cfg["module"]
        key_name = cfg["key_name"]
        mw_name = cfg["middleware_name"]
        handler_name = cfg["handler_name"]
        route = cfg["route"]
        domain = cfg["domain"]

        return f"""\
# GH15: Go Context String Key Collision — Full Specification (Planner Only)

## Overview

The workspace implements a {domain} HTTP server. `{mw_name}` in `middleware.go`
sets a context value; `{handler_name}` in `main.go` reads it. There is
**one bug**: the middleware uses a plain `string` key while the handler uses a
typed `contextKey` — they never match.

## Program Structure

- `middleware.go` — `{mw_name}` with the buggy string key
- `main.go` — `{handler_name}` and `contextKey` type definition
- `main_test.go` — tests that detect the bug
- `go.mod` — module `{module}`

## The Bug

**Root cause:** Go's `context.WithValue` and `context.Value` compare keys by
both **type** and **value**.  Two keys with the same underlying string but
different types are not equal:

```go
context.WithValue(ctx, "userID", "alice")   // key type: string
ctx.Value(contextKey("userID"))             // key type: contextKey ≠ string → nil
```

The `context` package documentation explicitly warns: _"The provided key must
be comparable and should not be of type string or any other built-in type to
avoid collisions between packages using context."_

**Location:** `middleware.go` — `context.WithValue(r.Context(), "{key_name}", value)`
uses a bare string literal instead of `contextKey("{key_name}")`.

**Fix:** Change `middleware.go` to use `{key_name}Key` (the `contextKey` constant
already defined in `main.go`):
```go
ctx := context.WithValue(r.Context(), {key_name}Key, value)
```

## Acceptance Criteria

1. `{mw_name}` sets context value using `contextKey` type (not bare string)
2. `{handler_name}` reads non-nil value and returns 200
3. All tests pass: `go test -v ./...`
4. `go vet ./...` reports no issues

## Important Notes

- Fix is in `middleware.go` — one line change (the `context.WithValue` call)
- Do NOT modify `main.go` or `main_test.go`
- `contextKey` and `{key_name}Key` are already defined in `main.go`
"""

    def _gen_brief(self, cfg: dict) -> str:
        domain = cfg["domain"]
        mw_name = cfg["middleware_name"]
        handler_name = cfg["handler_name"]
        key_name = cfg["key_name"]

        return f"""\
# GH15: Context Key Type Mismatch (Brief)

Fix the {domain} server so `{mw_name}` correctly passes the `{key_name}`
value to `{handler_name}` via the request context.

Currently the handler always receives nil and returns 500 instead of the
expected value.

Verify with:
```
go test -v ./...
```

**Files to fix:** `middleware.go`
**Do NOT modify:** `main.go` or `main_test.go`

Follow the Planner's guidance precisely.
"""
