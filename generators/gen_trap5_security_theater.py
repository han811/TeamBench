"""
Parameterized generator for TRAP5: Security Theater.

Each seed uses a different app context but the same structural vulnerabilities:
  - 4 false positives (high scanner confidence, correctly flagged but actually safe)
  - 2 critical vulnerabilities (low scanner confidence, genuinely dangerous)
  - 4 low-severity real issues

Seeds:
  0 — E-commerce app (auth for checkout, database for order queries)
  1 — Blog/CMS app (auth for admin, database for content queries)
  2 — API service app (token auth, database for stored queries)
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


_CONFIGS = [
    {
        # Seed 0: E-commerce
        "app_name": "ShopApp",
        "app_context": "e-commerce platform",
        "upload_dir": "PRODUCT_IMAGES_DIR",
        "upload_path": "/var/app/product_images",
        "subprocess_cmd": "generate_invoice",
        "subprocess_args": '["generate_invoice", invoice_id]',
        "db_table": "orders",
        "stored_query_table": "saved_searches",
        "login_entity": "customer",
        "admin_entity": "store_manager",
        "token_field": "session_token",
        "report_type": "sales_report",
        "user_agent_context": "customer browser",
        "stack_trace_context": "admin order management",
        "rate_limit_context": "checkout login",
    },
    {
        # Seed 1: Blog/CMS
        "app_name": "BlogApp",
        "app_context": "blog and content management system",
        "upload_dir": "MEDIA_UPLOAD_DIR",
        "upload_path": "/var/app/media",
        "subprocess_cmd": "render_markdown",
        "subprocess_args": '["render_markdown", "--safe", article_slug]',
        "db_table": "articles",
        "stored_query_table": "saved_filters",
        "login_entity": "author",
        "admin_entity": "editor",
        "token_field": "auth_token",
        "report_type": "traffic_report",
        "user_agent_context": "reader browser",
        "stack_trace_context": "admin content management",
        "rate_limit_context": "author login",
    },
    {
        # Seed 2: API service
        "app_name": "ApiService",
        "app_context": "RESTful API service",
        "upload_dir": "ARTIFACT_STORAGE_DIR",
        "upload_path": "/var/app/artifacts",
        "subprocess_cmd": "run_health_check",
        "subprocess_args": '["run_health_check", "--json", service_name]',
        "db_table": "api_logs",
        "stored_query_table": "query_templates",
        "login_entity": "api_client",
        "admin_entity": "service_admin",
        "token_field": "api_token",
        "report_type": "usage_report",
        "user_agent_context": "API client",
        "stack_trace_context": "admin service management",
        "rate_limit_context": "API client auth",
    },
]


class Generator(TaskGenerator):
    task_id = "TRAP5_security_theater"
    domain = "Security"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        cfg = _CONFIGS[seed % len(_CONFIGS)]

        workspace_files = self._make_workspace(cfg, seed)

        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", "TRAP5_security_theater"
        )
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="TRAP5_security_theater",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "critical_fixes": ["auth_bypass", "second_order_sqli"],
                "false_positives": [
                    "os_path_join",
                    "subprocess_run",
                    "dead_code_eval",
                    "csp_header",
                ],
                "low_severity_fixes": [
                    "rate_limiting",
                    "autocomplete_off",
                    "user_agent_logging",
                    "verbose_stack_trace",
                ],
                "seed": seed,
                "app_name": cfg["app_name"],
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Security"},
        )

    def _make_workspace(self, cfg: dict, seed: int) -> dict:
        files = {}
        c = cfg

        # ── webapp/__init__.py ────────────────────────────────────────────────
        files["webapp/__init__.py"] = ""

        # ── webapp/auth.py ────────────────────────────────────────────────────
        # Contains BOTH critical bugs: == comparison and None acceptance
        files["webapp/auth.py"] = f'''"""
Authentication module for {c["app_name"]}.

Handles {c["login_entity"]} token validation and session management.
"""
import logging

logger = logging.getLogger(__name__)


class AuthError(Exception):
    pass


def check_token(token: str, user) -> bool:
    """
    Validate that the provided token matches the user's stored token.

    Returns True if the token is valid, False otherwise.
    """
    stored = getattr(user, '{c["token_field"]}', None)
    # BUG 1: == comparison is not timing-safe (timing oracle attack)
    # BUG 2: if stored is None and token is None, this returns True
    return token == stored


def issue_token(user_id: int, secret: str) -> str:
    """Issue a new session token for the given user."""
    import hashlib
    import time
    raw = f"{{user_id}}:{{int(time.time())}}:{{secret}}"
    return hashlib.sha256(raw.encode()).hexdigest()


def require_auth(token: str, user) -> None:
    """Raise AuthError if the token is invalid."""
    if not check_token(token, user):
        raise AuthError(f"Invalid token for {c["login_entity"]}")


class User:
    """Simple user model for authentication."""
    def __init__(self, user_id: int, {c["token_field"]}: str = None):
        self.user_id = user_id
        self.{c["token_field"]} = {c["token_field"]}

    def __repr__(self):
        return f"User(id={{self.user_id}})"
'''

        # ── webapp/database.py ────────────────────────────────────────────────
        # Contains second-order SQL injection in the second query
        files["webapp/database.py"] = f'''"""
Database access layer for {c["app_name"]}.

Handles queries to {c["db_table"]} and {c["stored_query_table"]}.
"""
import sqlite3
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_DB_PATH = "app.db"


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initialize database schema."""
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS {c["db_table"]} (
            id INTEGER PRIMARY KEY,
            user_id INTEGER NOT NULL,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS {c["stored_query_table"]} (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            query_expr TEXT NOT NULL,
            owner_id INTEGER NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def store_query(name: str, query_expr: str, owner_id: int) -> int:
    """
    Store a named query for later reuse.
    The query_expr is parameterized safely on insert.
    """
    conn = get_connection()
    # SAFE: parameterized insert
    cursor = conn.execute(
        "INSERT INTO {c["stored_query_table"]} (name, query_expr, owner_id) VALUES (?, ?, ?)",
        (name, query_expr, owner_id)
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def execute_stored_query(query_id: int, limit: int = 100) -> list:
    """
    Retrieve a stored query by ID, then execute it against {c["db_table"]}.

    The stored query name was safely parameterized on insert, but the
    query_expr is retrieved and used UNSAFELY in the second query.
    """
    conn = get_connection()
    # SAFE: first query uses parameterized lookup
    row = conn.execute(
        "SELECT query_expr FROM {c["stored_query_table"]} WHERE id = ?",
        (query_id,)
    ).fetchone()
    if row is None:
        conn.close()
        return []

    query_expr = row["query_expr"]
    # BUG: second-order SQL injection — query_expr came from the DB but
    # is inserted directly into SQL without parameterization
    results = conn.execute(
        f"SELECT * FROM {c["db_table"]} WHERE " + query_expr + f" LIMIT {{limit}}"
    ).fetchall()
    conn.close()
    return [dict(r) for r in results]


def fetch_by_id(record_id: int) -> Optional[dict]:
    """Fetch a single record by ID (safe parameterized query)."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM {c["db_table"]} WHERE id = ?", (record_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def fetch_by_user(user_id: int) -> list:
    """Fetch all records for a user (safe parameterized query)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM {c["db_table"]} WHERE user_id = ?", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
'''

        # ── webapp/routes.py ──────────────────────────────────────────────────
        # Contains FALSE POSITIVES 1 and 2, plus low-severity #5
        files["webapp/routes.py"] = f'''"""
Route handlers for {c["app_name"]}.

Contains some patterns flagged by automated scanners as suspicious,
but which are safe in this context (see SECURITY_AUDIT.md findings 1-2).
"""
import os
import subprocess
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# FALSE POSITIVE 1: os.path.join used with a constant directory, not user input
{c["upload_dir"]} = "{c["upload_path"]}"


def get_upload_path(filename: str) -> str:
    """Return the full path for an uploaded file.

    Uses os.path.join with a constant base directory — NOT a path traversal
    vulnerability because the base is a hardcoded constant, not user-controlled.
    """
    # Scanner flags os.path.join as potential path traversal.
    # This is a FALSE POSITIVE: base dir is a constant, not user-supplied.
    safe_filename = os.path.basename(filename)  # Sanitize the filename first
    return os.path.join({c["upload_dir"]}, safe_filename)


def generate_report(report_id: str) -> dict:
    """Generate a report using an external tool.

    Uses subprocess.run with a fixed command list and no shell=True.
    Scanner flags this, but it is safe: no user input enters the command.
    """
    # FALSE POSITIVE 2: subprocess.run with fixed command list, no shell=True
    # report_id is an internal identifier, NOT user-controlled input here.
    safe_id = str(int(report_id))  # Validate: must be integer string
    result = subprocess.run(
        ["{c["subprocess_cmd"]}", safe_id],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return {{"output": result.stdout, "returncode": result.returncode}}


def handle_login(username: str, password: str) -> Optional[str]:
    """Authenticate a {c["login_entity"]} and return a session token.

    LOW SEVERITY (finding 5): No rate limiting on this endpoint.
    An attacker can brute-force credentials without throttling.
    """
    # Missing: rate limiting / account lockout
    from webapp.auth import issue_token, User
    # Simulated auth check
    if username and password:
        user = User(user_id=1, {c["token_field"]}="example_token")
        return issue_token(user.user_id, "app_secret")
    return None


def serve_file(filename: str) -> str:
    """Serve a file from the upload directory."""
    path = get_upload_path(filename)
    if not os.path.exists(path):
        return ""
    with open(path) as f:
        return f.read()
'''

        # ── webapp/middleware.py ──────────────────────────────────────────────
        # Contains FALSE POSITIVE 3 (dead code eval) and LOW severity #8
        files["webapp/middleware.py"] = f'''"""
Middleware for {c["app_name"]}.

Handles request logging and common pre/post processing.
"""
import logging

logger = logging.getLogger(__name__)


class RequestMiddleware:
    """WSGI middleware for request processing."""

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        self._log_request(environ)
        return self.app(environ, start_response)

    def _log_request(self, environ: dict) -> None:
        """Log basic request info."""
        method = environ.get("REQUEST_METHOD", "")
        path = environ.get("PATH_INFO", "")

        # LOW SEVERITY (finding 8): User-agent logged at DEBUG level.
        # Minor info disclosure — user-agent shouldn't be logged even at DEBUG.
        user_agent = environ.get("HTTP_USER_AGENT", "unknown")
        logger.debug("Request: %s %s (ua=%s)", method, path, user_agent)


def parse_config(config_str: str) -> dict:
    """Parse a configuration string.

    This function contains a dead code branch that scanners flag.
    The eval() is inside 'if False:' and is NEVER executed.
    """
    result = {{}}
    # Parse key=value pairs
    for line in config_str.strip().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, val = line.partition("=")
            result[key.strip()] = val.strip()

    # FALSE POSITIVE 3: dead code branch — this block is never executed.
    # Scanner flags the eval() but it cannot be reached at runtime.
    if False:
        # Legacy config parsing — disabled, kept for reference only
        result = eval(config_str)  # noqa: S307  # dead code

    return result


def apply_security_headers(headers: dict) -> dict:
    """Apply standard security headers to a response."""
    headers["X-Content-Type-Options"] = "nosniff"
    headers["X-Frame-Options"] = "DENY"
    headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return headers
'''

        # ── webapp/crypto_utils.py ────────────────────────────────────────────
        files["webapp/crypto_utils.py"] = f'''"""
Cryptographic utilities for {c["app_name"]}.

All implementations use standard library cryptography.
"""
import hashlib
import hmac
import os
import secrets


def generate_secure_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token."""
    return secrets.token_hex(length)


def hash_password(password: str, salt: bytes = None) -> tuple:
    """Hash a password with PBKDF2-HMAC-SHA256."""
    if salt is None:
        salt = os.urandom(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100_000)
    return key.hex(), salt.hex()


def verify_password(password: str, stored_hash: str, salt_hex: str) -> bool:
    """Verify a password against its stored hash."""
    salt = bytes.fromhex(salt_hex)
    key, _ = hash_password(password, salt)
    return hmac.compare_digest(key, stored_hash)


def sign_payload(payload: bytes, secret: bytes) -> str:
    """HMAC-SHA256 sign a payload."""
    sig = hmac.new(secret, payload, hashlib.sha256)
    return sig.hexdigest()


def verify_signature(payload: bytes, signature: str, secret: bytes) -> bool:
    """Verify an HMAC-SHA256 signature."""
    expected = sign_payload(payload, secret)
    return hmac.compare_digest(expected, signature)
'''

        # ── webapp/templates/base.html ─────────────────────────────────────────
        # FALSE POSITIVE 4: CSP header is actually strict
        files["webapp/templates/base.html"] = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!-- FALSE POSITIVE 4: This Content-Security-Policy is actually STRICT.
         Scanner flagged it as "too permissive" but default-src 'self' is correct.
         Do NOT weaken or remove this header. -->
    <meta http-equiv="Content-Security-Policy"
          content="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; frame-ancestors 'none'">
    <meta http-equiv="X-Content-Type-Options" content="nosniff">
    <meta http-equiv="X-Frame-Options" content="DENY">
    <title>{c["app_name"]}</title>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <header>
        <nav>
            <a href="/">{c["app_name"]}</a>
        </nav>
    </header>
    <main>
        {{% block content %}}{{% endblock %}}
    </main>
    <footer>
        <p>&copy; 2024 {c["app_name"]}</p>
    </footer>
</body>
</html>
'''

        # ── webapp/templates/form.html ─────────────────────────────────────────
        # LOW SEVERITY: Missing autocomplete="off" on password field
        files["webapp/templates/form.html"] = f'''{{%- extends "base.html" -%}}
{{%- block content -%}}
<div class="login-form">
    <h2>Sign In</h2>
    <form method="POST" action="/login">
        <div class="field">
            <label for="username">Username</label>
            <input type="text" id="username" name="username"
                   autocomplete="username" required>
        </div>
        <div class="field">
            <label for="password">Password</label>
            <!-- LOW SEVERITY (finding 6): missing autocomplete="off" on password field.
                 Browser may cache the password. Add autocomplete="off" or
                 autocomplete="current-password" with appropriate policy. -->
            <input type="password" id="password" name="password" required>
        </div>
        <button type="submit">Sign In</button>
    </form>
    <p><a href="/forgot-password">Forgot password?</a></p>
</div>
{{%- endblock -%}}
'''

        # ── webapp/templates/admin.html ────────────────────────────────────────
        # LOW SEVERITY: Verbose stack trace on error
        files["webapp/templates/admin.html"] = f'''{{%- extends "base.html" -%}}
{{%- block content -%}}
<div class="admin-panel">
    <h2>{c["admin_entity"].replace("_", " ").title()} Panel</h2>

    {{%- if error -%}}
    <!-- LOW SEVERITY (finding 10): verbose error display.
         Stack trace and internal details visible to admins — should be
         replaced with a user-friendly message and logged server-side only. -->
    <div class="error-panel">
        <h3>Error</h3>
        <pre class="stack-trace">{{{{ error.message }}}}
{{{{ error.traceback }}}}</pre>
        <p>Internal path: {{{{ error.path }}}}</p>
        <p>Module: {{{{ error.module }}}}</p>
    </div>
    {{%- endif -%}}

    <section class="actions">
        <h3>{c["admin_entity"].replace("_", " ").title()} Actions</h3>
        <ul>
            <li><a href="/admin/users">Manage Users</a></li>
            <li><a href="/admin/reports">View Reports</a></li>
            <li><a href="/admin/logs">System Logs</a></li>
        </ul>
    </section>
</div>
{{%- endblock -%}}
'''

        # ── SECURITY_AUDIT.md ──────────────────────────────────────────────────
        # 10 findings sorted by scanner confidence (misleading order)
        files["SECURITY_AUDIT.md"] = f'''# Security Audit Report — {c["app_name"]}

**Audit Date**: 2024-11-15
**Auditor**: AutoScan Pro v4.2
**Scope**: Full application codebase

Findings are sorted by scanner confidence (highest first).
Total findings: 10

---

## Finding 1 — CRITICAL [Scanner Confidence: 97%]
**File**: `webapp/routes.py`
**Pattern**: `os.path.join()` with user-controlled input
**Description**: The function `get_upload_path()` uses `os.path.join()` which
can allow path traversal attacks if the `filename` parameter contains `../` sequences.
**Recommended fix**: Use `pathlib.Path.resolve()` and validate the result is
within the expected directory.

---

## Finding 2 — HIGH [Scanner Confidence: 94%]
**File**: `webapp/routes.py`
**Pattern**: `subprocess.run()` usage detected
**Description**: The function `generate_report()` invokes an external process.
Shell injection may be possible if report parameters are not sanitized.
**Recommended fix**: Validate all inputs, use `shell=False` (already set), consider
replacing with a library call.

---

## Finding 3 — HIGH [Scanner Confidence: 91%]
**File**: `webapp/middleware.py`
**Pattern**: `eval()` usage detected
**Description**: The function `parse_config()` contains an `eval()` call which
can execute arbitrary Python code if called with untrusted input.
**Recommended fix**: Replace `eval()` with `ast.literal_eval()` or a dedicated parser.

---

## Finding 4 — HIGH [Scanner Confidence: 88%]
**File**: `webapp/templates/base.html`
**Pattern**: Content-Security-Policy header may be too permissive
**Description**: The CSP header detected does not include `object-src 'none'`
and `base-uri 'none'` directives, which are recommended by OWASP.
**Recommended fix**: Add `object-src 'none'; base-uri 'self'` to the CSP header.

---

## Finding 5 — MEDIUM [Scanner Confidence: 72%]
**File**: `webapp/routes.py`
**Pattern**: No rate limiting on authentication endpoint
**Description**: The `handle_login()` function does not implement rate limiting
or account lockout. This enables brute-force attacks against {c["login_entity"]} accounts.
**Recommended fix**: Add rate limiting (e.g., flask-limiter) or a sleep/delay on failed attempts.

---

## Finding 6 — MEDIUM [Scanner Confidence: 68%]
**File**: `webapp/templates/form.html`
**Pattern**: Password field missing `autocomplete="off"`
**Description**: The password input does not set `autocomplete="off"`,
allowing browsers to cache credentials.
**Recommended fix**: Add `autocomplete="off"` to the password input field.

---

## Finding 7 — LOW [Scanner Confidence: 41%]
**File**: `webapp/auth.py`
**Pattern**: Token comparison using `==` operator
**Description**: The `check_token()` function uses `==` for token comparison.
This may allow timing-based side-channel attacks in some environments.
Scanner confidence is low because this is often a false positive in practice.
**Recommended fix**: Use `hmac.compare_digest()` for constant-time comparison.

---

## Finding 8 — MEDIUM [Scanner Confidence: 65%]
**File**: `webapp/middleware.py`
**Pattern**: User-agent string logged
**Description**: The `_log_request()` method logs the HTTP User-Agent header
at DEBUG level. This may constitute minor information disclosure.
**Recommended fix**: Remove user-agent from log output or log at TRACE level only.

---

## Finding 9 — LOW [Scanner Confidence: 38%]
**File**: `webapp/database.py`
**Pattern**: Possible SQL construction from retrieved data
**Description**: The `execute_stored_query()` function retrieves a value from
the database and uses it in a subsequent query. Scanner cannot determine if this
constitutes a vulnerability without manual review.
**Recommended fix**: Manual code review recommended.

---

## Finding 10 — MEDIUM [Scanner Confidence: 60%]
**File**: `webapp/templates/admin.html`
**Pattern**: Stack trace exposed in error template
**Description**: The admin error template renders `error.traceback` and internal
path information which may disclose implementation details.
**Recommended fix**: Log errors server-side and display only a generic error message.

---

## Summary Table

| Finding | File | Confidence | Category |
|---------|------|------------|----------|
| 1 | routes.py | 97% | Path traversal |
| 2 | routes.py | 94% | Command injection |
| 3 | middleware.py | 91% | Code injection |
| 4 | templates/base.html | 88% | CSP misconfiguration |
| 5 | routes.py | 72% | Missing rate limit |
| 6 | templates/form.html | 68% | Autocomplete |
| 7 | auth.py | 41% | Auth bypass |
| 8 | middleware.py | 65% | Info disclosure |
| 9 | database.py | 38% | SQL injection |
| 10 | templates/admin.html | 60% | Info disclosure |
'''

        # ── tests/__init__.py ─────────────────────────────────────────────────
        files["tests/__init__.py"] = ""

        # ── tests/test_security.py ────────────────────────────────────────────
        files["tests/test_security.py"] = f'''"""General security tests for {c["app_name"]}."""
import sys
sys.path.insert(0, '.')
import pytest


def test_auth_module_imports():
    from webapp.auth import check_token, issue_token, User
    assert callable(check_token)
    assert callable(issue_token)


def test_issue_token_returns_string():
    from webapp.auth import issue_token
    token = issue_token(user_id=1, secret="test_secret")
    assert isinstance(token, str)
    assert len(token) > 16


def test_database_module_imports():
    from webapp.database import store_query, execute_stored_query, fetch_by_id
    assert callable(store_query)
    assert callable(execute_stored_query)


def test_routes_get_upload_path():
    from webapp.routes import get_upload_path
    path = get_upload_path("image.png")
    # Must not allow path traversal
    assert ".." not in path


def test_routes_subprocess_not_shell():
    """Verify the subprocess call uses shell=False (not shell=True)."""
    import inspect
    from webapp import routes
    src = inspect.getsource(routes)
    # Should not have shell=True
    assert "shell=True" not in src


def test_middleware_parse_config():
    from webapp.middleware import parse_config
    result = parse_config("key1=value1\\nkey2=value2\\n")
    assert result == {{"key1": "value1", "key2": "value2"}}


def test_crypto_utils():
    from webapp.crypto_utils import generate_secure_token, hash_password, verify_password
    token = generate_secure_token()
    assert len(token) == 64  # 32 bytes hex-encoded

    pw_hash, salt = hash_password("test_password")
    assert verify_password("test_password", pw_hash, salt)
    assert not verify_password("wrong_password", pw_hash, salt)
'''

        # ── tests/test_auth_bypass.py ─────────────────────────────────────────
        # Adversarial: exploits the None==None and timing bugs
        files["tests/test_auth_bypass.py"] = f'''"""
Adversarial auth bypass tests for TRAP5.

These tests exploit the actual bugs in webapp/auth.py:
  Bug 1: check_token uses == instead of hmac.compare_digest (timing attack)
  Bug 2: check_token(None, user_with_none_token) returns True
"""
import sys
sys.path.insert(0, '.')
import pytest
import inspect
from webapp.auth import check_token, User


def test_none_token_rejected():
    """
    Bug: if stored token is None and provided token is None,
    check_token returns True (None == None is True).
    After fix: None tokens must be rejected.
    """
    user = User(user_id=99, {c["token_field"]}=None)
    result = check_token(None, user)
    assert result is False, (
        "check_token(None, user_with_none_token) must return False. "
        "Currently returns True because None == None is True."
    )


def test_empty_string_token_rejected():
    """Empty string token should also be rejected if stored token is not empty."""
    user = User(user_id=99, {c["token_field"]}="valid_token_abc123")
    result = check_token("", user)
    assert result is False, "Empty token string must be rejected"


def test_valid_token_accepted():
    """Sanity check: valid token must still be accepted after fix."""
    user = User(user_id=1, {c["token_field"]}="valid_token_abc123")
    result = check_token("valid_token_abc123", user)
    assert result is True, "Valid token must be accepted"


def test_invalid_token_rejected():
    """Wrong token must be rejected."""
    user = User(user_id=1, {c["token_field"]}="valid_token_abc123")
    result = check_token("wrong_token_xyz", user)
    assert result is False, "Wrong token must be rejected"


def test_timing_safe_comparison():
    """
    Verify that check_token uses hmac.compare_digest or secrets.compare_digest
    for timing-safe comparison, not the == operator.
    """
    src = inspect.getsource(check_token)
    assert "compare_digest" in src, (
        "check_token() must use hmac.compare_digest() or secrets.compare_digest() "
        "for timing-safe token comparison. Currently uses == which enables timing attacks."
    )
'''

        # ── tests/test_sqli.py ────────────────────────────────────────────────
        # Adversarial: checks parameterization of the second query
        files["tests/test_sqli.py"] = f'''"""
Adversarial SQL injection tests for TRAP5.

Tests for second-order SQL injection in webapp/database.py:
  execute_stored_query() safely retrieves the stored query with parameterization,
  but then inserts it directly into the second SQL query as a string — SQL injection.
"""
import sys
sys.path.insert(0, '.')
import pytest
import inspect
import re
from webapp.database import execute_stored_query


def test_second_query_uses_parameterization():
    """
    Verify that ALL queries in execute_stored_query() use parameterized execution.

    The bug: the second query builds SQL like:
        f"SELECT * FROM {c["db_table"]} WHERE " + query_expr + " LIMIT ..."
    This allows second-order SQL injection via a stored payload.

    After fix: both queries must use ? placeholders.
    """
    src = inspect.getsource(execute_stored_query)

    # Find all execute() calls in the function
    execute_calls = re.findall(r'\.execute\(([^)]+)\)', src, re.DOTALL)

    for call_args in execute_calls:
        # Each execute call must use parameterized queries (? placeholder)
        # or pass a separate params tuple
        has_placeholder = "?" in call_args or "%s" in call_args
        # An f-string or .format() in the query is a red flag for injection
        has_fstring = re.search('f[\"\\x27].*SELECT', call_args)
        has_format = ".format(" in call_args and "SELECT" in src

        if not has_placeholder:
            # Check if this is a string concatenation (also bad)
            has_concat = (
                re.search(r'"[^"]*"\s*\+', call_args) or
                re.search(r"'[^']*'\s*\+", call_args) or
                has_fstring
            )
            if has_concat:
                pytest.fail(
                    f"execute_stored_query() contains a SQL query built by string "
                    f"concatenation or f-string (second-order injection). "
                    f"All queries must use parameterized placeholders (?). "
                    f"Offending execute() call: {{call_args[:200]}}"
                )


def test_no_direct_string_interpolation_in_queries():
    """
    Verify no f-strings or .format() are used to build SQL in execute_stored_query.
    """
    src = inspect.getsource(execute_stored_query)
    # Look for f-string SQL construction
    fstring_sql = re.search('f[\"\\x27].*SELECT.*FROM', src, re.DOTALL)
    assert not fstring_sql, (
        "execute_stored_query() uses f-string SQL construction (injection risk). "
        "Use parameterized queries with ? placeholders instead."
    )


def test_execute_stored_query_callable():
    """Sanity check: function must still be callable after fix."""
    assert callable(execute_stored_query)
'''

        return files
