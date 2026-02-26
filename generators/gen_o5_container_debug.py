"""
Parameterized generator for O5: Container Debug.

TNI Pattern A,B:
  - spec.md has the full intended container setup: base image, required packages,
    env vars, port mapping, health check, CMD/ENTRYPOINT.
  - brief.md only says "The containerized service fails to start or crashes
    immediately after starting."
  - The workspace has a broken Dockerfile and config with misleading error
    messages embedded in comments.

Each seed produces:
  - Different app type: python-flask, python-fastapi, node-express, go-http
  - Different subset of bug types injected into the Dockerfile:
      wrong_base_image, missing_dependency_install, wrong_port_expose,
      missing_env_var, wrong_cmd
  - Different port, service name, and environment variable values
  - server.py (or index.js / main.go) — runnable if Dockerfile is correct
  - app_config.json — app config that must match env vars

Grade checks (10+):
  1.  Dockerfile exists
  2.  Correct base image present
  3.  Required packages installed (RUN ... install ...)
  4.  Correct EXPOSE port
  5.  Required ENV vars declared
  6.  Correct CMD or ENTRYPOINT
  7.  WORKDIR set
  8.  App files copied (COPY instruction)
  9.  HEALTHCHECK defined
  10. app_config.json references correct port
  11. app_config.json references correct host binding
  12. submission/fix_notes.txt exists and mentions each bug type fixed
"""
from __future__ import annotations

import json
import textwrap
from typing import Any

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# ── Parameterisation pools ─────────────────────────────────────────────────────

APP_TYPES = [
    "python-flask",
    "python-fastapi",
    "node-express",
    "go-http",
]

# All possible bug types that can be injected
BUG_TYPE_POOL = [
    "wrong_base_image",
    "missing_dependency_install",
    "wrong_port_expose",
    "missing_env_var",
    "wrong_cmd",
]

PORT_POOL = [3000, 4000, 5000, 6000, 7000, 8000, 8080, 8888, 9000, 9090]

SERVICE_NAME_POOL = [
    "api-gateway", "auth-service", "payment-service", "user-service",
    "catalog-service", "notification-service", "order-service", "search-service",
    "report-service", "billing-service",
]

ENV_KEY_POOL = [
    "APP_SECRET", "DATABASE_URL", "API_KEY", "JWT_SECRET", "SERVICE_TOKEN",
    "AUTH_TOKEN", "CACHE_URL", "QUEUE_URL",
]

# ── App-type definitions ──────────────────────────────────────────────────────

# correct_base: the right base image for each app type
# wrong_base:   a plausible-but-wrong alternative base image
APP_DEFINITIONS = {
    "python-flask": {
        "correct_base":    "python:3.11-slim",
        "wrong_base":      "node:18-alpine",
        "packages":        ["flask", "gunicorn"],
        "install_cmd":     "pip install --no-cache-dir flask gunicorn",
        "correct_cmd":     '["gunicorn", "--bind", "0.0.0.0:{port}", "server:app"]',
        "wrong_cmd":       '["python", "server.py"]',
        "app_file":        "server.py",
        "copy_glob":       ".",
        "entrypoint_key":  "CMD",
        "run_instruction": "pip install --no-cache-dir flask gunicorn",
        "wrong_run":       "apt-get install -y python3-flask",
    },
    "python-fastapi": {
        "correct_base":    "python:3.11-slim",
        "wrong_base":      "golang:1.21-alpine",
        "packages":        ["fastapi", "uvicorn"],
        "install_cmd":     "pip install --no-cache-dir fastapi uvicorn",
        "correct_cmd":     '["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "{port}"]',
        "wrong_cmd":       '["python", "-m", "uvicorn", "main:app"]',
        "app_file":        "server.py",
        "copy_glob":       ".",
        "entrypoint_key":  "CMD",
        "run_instruction": "pip install --no-cache-dir fastapi uvicorn",
        "wrong_run":       "npm install fastapi",
    },
    "node-express": {
        "correct_base":    "node:18-alpine",
        "wrong_base":      "python:3.11-slim",
        "packages":        ["express"],
        "install_cmd":     "npm install",
        "correct_cmd":     '["node", "server.js"]',
        "wrong_cmd":       '["python3", "server.js"]',
        "app_file":        "server.js",
        "copy_glob":       ".",
        "entrypoint_key":  "CMD",
        "run_instruction": "npm install",
        "wrong_run":       "pip install express",
    },
    "go-http": {
        "correct_base":    "golang:1.21-alpine",
        "wrong_base":      "python:3.11-slim",
        "packages":        [],
        "install_cmd":     "go build -o server .",
        "correct_cmd":     '["./server"]',
        "wrong_cmd":       '["go", "run", "main.go"]',
        "app_file":        "main.go",
        "copy_glob":       ".",
        "entrypoint_key":  "CMD",
        "run_instruction": "go build -o server .",
        "wrong_run":       "pip install go",
    },
}

# ── Bug injection helpers ─────────────────────────────────────────────────────

def _inject_bugs(
    rng: SeededRandom,
    app_type: str,
    port: int,
    env_key: str,
    env_value: str,
    bug_types: list[str],
) -> str:
    """Build a broken Dockerfile by injecting the selected bug types."""
    app = APP_DEFINITIONS[app_type]

    # Start with correct values, then selectively corrupt
    base_image = app["correct_base"]
    run_install = app["run_instruction"]
    expose_port = port
    env_line = f"{env_key}={env_value}"
    cmd_line = app["correct_cmd"].format(port=port)
    include_healthcheck = True  # healthcheck always correct — bug is elsewhere

    if "wrong_base_image" in bug_types:
        base_image = app["wrong_base"]

    if "missing_dependency_install" in bug_types:
        run_install = app["wrong_run"]

    if "wrong_port_expose" in bug_types:
        # Use a different, wrong port
        wrong_ports = [p for p in PORT_POOL if p != port]
        expose_port = rng.choice(wrong_ports)

    if "missing_env_var" in bug_types:
        env_line = ""  # omit the seed-specific ENV declaration

    if "wrong_cmd" in bug_types:
        cmd_line = app["wrong_cmd"]

    # Build Dockerfile text
    lines = [
        f"FROM {base_image}",
        "",
        "WORKDIR /app",
        "",
        f"COPY {app['copy_glob']} .",
        "",
        f"RUN {run_install}",
    ]

    # APP_PORT is always present (it is never itself a bug type)
    lines += ["", f"ENV APP_PORT={port}"]

    if env_line:
        lines += [f"ENV {env_line}"]

    lines += [
        "",
        f"EXPOSE {expose_port}",
    ]

    if include_healthcheck:
        lines += [
            "",
            f'HEALTHCHECK --interval=30s --timeout=5s --retries=3 \\',
            f'  CMD wget -qO- http://localhost:{port}/health || exit 1',
        ]

    lines += [
        "",
        f"{app['entrypoint_key']} {cmd_line}",
    ]

    # Inject misleading comments to confuse naive agents
    misleading = _misleading_comment(app_type, bug_types, port)
    lines = [misleading, ""] + lines

    return "\n".join(lines) + "\n"


def _misleading_comment(app_type: str, bug_types: list[str], port: int) -> str:
    """Generate a misleading header comment that points to the wrong problem."""
    if "wrong_base_image" in bug_types:
        return (
            f"# Service container — base image updated to latest stable release\n"
            f"# Port {port} is correct per infrastructure spec"
        )
    if "missing_dependency_install" in bug_types:
        return (
            f"# Dependencies pre-installed in base image — no pip/npm install needed\n"
            f"# See requirements.txt for the package list"
        )
    if "wrong_port_expose" in bug_types:
        return (
            f"# EXPOSE declares the container's listening port\n"
            f"# Note: internal port differs from external mapping in docker-compose"
        )
    if "missing_env_var" in bug_types:
        return (
            f"# Environment variables are injected at runtime via docker run --env-file\n"
            f"# No ENV declarations needed in Dockerfile"
        )
    # wrong_cmd
    return (
        f"# Start command uses the standard Python entry point\n"
        f"# The server binds automatically to 0.0.0.0:{port}"
    )


# ── Server file generators ────────────────────────────────────────────────────

def _server_flask(port: int, env_key: str) -> str:
    return f'''\
"""
Flask HTTP server.
Reads APP_PORT from environment (default {port}).
Requires ENV {env_key} to be set.
"""
import os
from flask import Flask, jsonify

app = Flask(__name__)

# Will raise KeyError at startup if env var is missing
SECRET = os.environ["{env_key}"]
PORT = int(os.environ.get("APP_PORT", {port}))


@app.route("/health")
def health():
    return jsonify({{"status": "ok"}})


@app.route("/api/info")
def info():
    return jsonify({{"service": "flask-app", "port": PORT}})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
'''


def _server_fastapi(port: int, env_key: str) -> str:
    return f'''\
"""
FastAPI HTTP server.
Reads APP_PORT from environment (default {port}).
Requires ENV {env_key} to be set.
"""
import os
from fastapi import FastAPI

app = FastAPI()

SECRET = os.environ["{env_key}"]
PORT = int(os.environ.get("APP_PORT", {port}))


@app.get("/health")
def health():
    return {{"status": "ok"}}


@app.get("/api/info")
def info():
    return {{"service": "fastapi-app", "port": PORT}}
'''


def _server_node(port: int, env_key: str) -> str:
    return f"""\
'use strict';
// Express HTTP server
// Requires {env_key} environment variable
const express = require('express');
const app = express();
const PORT = process.env.APP_PORT || {port};
const SECRET = process.env.{env_key};
if (!SECRET) {{ process.exit(1); }}

app.get('/health', (req, res) => res.json({{ status: 'ok' }}));
app.get('/api/info', (req, res) => res.json({{ service: 'node-app', port: PORT }}));

app.listen(PORT, '0.0.0.0', () => {{
  console.log(`Server listening on 0.0.0.0:${{PORT}}`);
}});
"""


def _server_go(port: int, env_key: str) -> str:
    return f"""\
package main

import (
\t"encoding/json"
\t"fmt"
\t"net/http"
\t"os"
)

func main() {{
\tsecret := os.Getenv("{env_key}")
\tif secret == "" {{
\t\tfmt.Fprintln(os.Stderr, "ERROR: {env_key} not set")
\t\tos.Exit(1)
\t}}
\tport := os.Getenv("APP_PORT")
\tif port == "" {{
\t\tport = "{port}"
\t}}
\thttp.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {{
\t\tw.Header().Set("Content-Type", "application/json")
\t\tjson.NewEncoder(w).Encode(map[string]string{{"status": "ok"}})
\t}})
\thttp.HandleFunc("/api/info", func(w http.ResponseWriter, r *http.Request) {{
\t\tw.Header().Set("Content-Type", "application/json")
\t\tjson.NewEncoder(w).Encode(map[string]interface{{{{"service": "go-app", "port": port}}}})
\t}})
\tfmt.Printf("Server listening on 0.0.0.0:%s\\n", port)
\tif err := http.ListenAndServe("0.0.0.0:"+port, nil); err != nil {{
\t\tfmt.Fprintln(os.Stderr, err)
\t\tos.Exit(1)
\t}}
}}
"""


def _app_config(port: int, service_name: str, env_key: str) -> str:
    return json.dumps({
        "service": service_name,
        "host": "0.0.0.0",
        "port": port,
        "health_endpoint": "/health",
        "required_env": [env_key, "APP_PORT"],
    }, indent=2)


# ── Package.json for node-express ────────────────────────────────────────────

def _package_json(service_name: str) -> str:
    return json.dumps({
        "name": service_name,
        "version": "1.0.0",
        "main": "server.js",
        "dependencies": {
            "express": "^4.18.2"
        },
        "scripts": {
            "start": "node server.js"
        }
    }, indent=2)


# ── Generator ─────────────────────────────────────────────────────────────────

class Generator(TaskGenerator):
    task_id = "O5_container_debug"
    domain = "operations"
    difficulty = "hard"
    languages = ["python", "javascript", "go", "dockerfile"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        app_type    = rng.choice(APP_TYPES)
        port        = rng.choice(PORT_POOL)
        svc_name    = rng.choice(SERVICE_NAME_POOL)
        env_key     = rng.choice(ENV_KEY_POOL)
        env_value   = f"secret-{rng.randint(1000, 9999)}"

        # Each seed gets 2-4 bugs from the pool (always at least 2 for hard difficulty)
        n_bugs = rng.randint(2, 4)
        # Shuffle bug pool and take first n_bugs — deterministic via SeededRandom
        bug_pool_copy = list(BUG_TYPE_POOL)
        rng.shuffle(bug_pool_copy)
        bug_types = bug_pool_copy[:n_bugs]

        app = APP_DEFINITIONS[app_type]

        # Build workspace files
        broken_dockerfile = _inject_bugs(rng, app_type, port, env_key, env_value, bug_types)
        app_config = _app_config(port, svc_name, env_key)

        workspace_files: dict[str, str] = {
            "Dockerfile":        broken_dockerfile,
            "app_config.json":   app_config,
        }

        # Add app server file
        if app_type == "python-flask":
            workspace_files["server.py"] = _server_flask(port, env_key)
        elif app_type == "python-fastapi":
            workspace_files["server.py"] = _server_fastapi(port, env_key)
        elif app_type == "node-express":
            workspace_files["server.js"] = _server_node(port, env_key)
            workspace_files["package.json"] = _package_json(svc_name)
        elif app_type == "go-http":
            workspace_files["main.go"] = _server_go(port, env_key)

        expected: dict[str, Any] = {
            "app_type":           app_type,
            "service_name":       svc_name,
            "port":               port,
            "env_key":            env_key,
            "env_value":          env_value,
            "bug_types":          sorted(bug_types),
            "correct_base_image": app["correct_base"],
            "correct_cmd":        app["correct_cmd"].format(port=port),
            "correct_run":        app["run_instruction"],
            "app_file":           app["app_file"],
            "packages":           app["packages"],
        }

        spec_md  = self._generate_spec(app_type, app, port, svc_name, env_key, env_value, bug_types)
        brief_md = self._generate_brief(svc_name, app_type)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # ── Spec / Brief ──────────────────────────────────────────────────────────

    def _generate_spec(
        self,
        app_type: str,
        app: dict,
        port: int,
        svc_name: str,
        env_key: str,
        env_value: str,
        bug_types: list[str],
    ) -> str:
        packages_str = ", ".join(f"`{p}`" for p in app["packages"]) if app["packages"] else "built-in (no external packages)"
        cmd_str = app["correct_cmd"].format(port=port)

        bug_descriptions = {
            "wrong_base_image": (
                f"**Wrong base image**: The Dockerfile uses an incorrect base image. "
                f"The correct base image is `{app['correct_base']}`."
            ),
            "missing_dependency_install": (
                f"**Missing/wrong dependency install**: The RUN instruction for installing "
                f"dependencies is incorrect. The correct RUN command is:\n"
                f"  `RUN {app['run_instruction']}`"
            ),
            "wrong_port_expose": (
                f"**Wrong EXPOSE port**: The EXPOSE directive uses the wrong port. "
                f"The correct port is `{port}`."
            ),
            "missing_env_var": (
                f"**Missing ENV declaration**: The required environment variable `{env_key}` "
                f"is not declared in the Dockerfile. Add:\n"
                f"  `ENV {env_key}={env_value}`"
            ),
            "wrong_cmd": (
                f"**Wrong CMD/ENTRYPOINT**: The CMD is incorrect for this application type. "
                f"The correct CMD is:\n"
                f"  `CMD {cmd_str}`"
            ),
        }

        bug_section_lines = []
        for bt in sorted(bug_types):
            bug_section_lines.append(f"- {bug_descriptions[bt]}")
        bug_section = "\n".join(bug_section_lines)

        return f"""\
# O5: Container Debug

## Goal

Fix the broken `Dockerfile` so the containerized `{svc_name}` service starts
correctly and passes all health checks.

The service currently fails to start due to multiple Dockerfile bugs. The
`app_config.json` and application server file are correct — only the
`Dockerfile` needs to be fixed.

## Service Specification

| Property | Value |
|----------|-------|
| Application type | `{app_type}` |
| Service name | `{svc_name}` |
| Listen port | `{port}` |
| Health endpoint | `GET /health` → `{{"status": "ok"}}` |

## Correct Dockerfile Requirements

### Base Image

```
FROM {app["correct_base"]}
```

### Working Directory

```
WORKDIR /app
```

### Copy Application Files

```
COPY . .
```

### Install Dependencies

```
RUN {app["run_instruction"]}
```

Packages required: {packages_str}

### Environment Variables

The following ENV vars must be declared in the Dockerfile:

```
ENV {env_key}={env_value}
ENV APP_PORT={port}
```

### Expose Port

```
EXPOSE {port}
```

### Health Check

```
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \\
  CMD wget -qO- http://localhost:{port}/health || exit 1
```

### Start Command

```
CMD {cmd_str}
```

## Known Bugs in Dockerfile

The current Dockerfile has the following bugs (all must be fixed):

{bug_section}

## Hard Requirements

1. `FROM` must use exactly `{app["correct_base"]}`.
2. `RUN` must correctly install all required packages.
3. `EXPOSE` must declare port `{port}`.
4. `ENV {env_key}` must be declared.
5. `ENV APP_PORT` must be declared with value `{port}`.
6. `CMD` must match the correct start command above exactly.
7. `WORKDIR /app` must be set.
8. `COPY` must include the application files.
9. `HEALTHCHECK` must be defined.
10. `app_config.json` must not be modified (it is correct as-is).
11. Write a `submission/fix_notes.txt` describing each bug you fixed.

## Trap Design (TNI Pattern A+B)

The brief only says the container fails to start. The Dockerfile contains
misleading comments suggesting the current configuration is correct.
The spec (this document) has the full container requirements.

A naive fix might:
- Fix only the base image but miss the CMD or ENV bugs.
- Fix the EXPOSE port but leave the wrong base image.
- Modify `app_config.json` instead of the Dockerfile.
- Use an approximate CMD that does not match the exact required form.

The Planner must read this full spec. The Verifier must check all Dockerfile
elements against these requirements.
"""

    def _generate_brief(self, svc_name: str, app_type: str) -> str:
        return f"""\
# O5: Container Debug (Brief)

The containerized `{svc_name}` ({app_type}) service fails to start or crashes
immediately after starting.

The `Dockerfile` in the workspace is broken. Fix it so the container starts
correctly and the `/health` endpoint responds with HTTP 200.

The Planner has the full container specification with correct base image,
dependencies, environment variables, port, and start command.

Write your findings to `submission/fix_notes.txt`.
"""
