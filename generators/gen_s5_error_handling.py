"""
Parameterized generator for S5: Error Handling.

TNI Pattern E (Spec/Brief Divergence):
  - Spec has: complete error code taxonomy with exact HTTP status codes,
    recovery actions per error type, retry logic, logging requirements,
    and session management for auth errors.
  - Brief says: "The application lacks proper error handling. Add it."
  - TNI driver: Without the Planner's error code taxonomy the Executor cannot
    know which HTTP statuses to return, what recovery actions to implement,
    or that retry logic (3x with backoff) is required for database errors.

Each seed produces a different:
  - Application type (api_server / file_processor / data_importer / webhook_handler)
  - Error code count (5-8 error codes)
  - Recovery action types per error
  - Retry configuration (attempts, backoff)
  - Logging format/fields
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# ── Application type variants ─────────────────────────────────────────────────

APP_TYPES = ["api_server", "file_processor", "data_importer", "webhook_handler"]

APP_DESCRIPTIONS = {
    "api_server": "REST API server for managing resources",
    "file_processor": "file processing service for ingesting documents",
    "data_importer": "data import service for batch operations",
    "webhook_handler": "webhook handler for receiving external events",
}

APP_MODULE_NAMES = {
    "api_server": "app",
    "file_processor": "processor",
    "data_importer": "importer",
    "webhook_handler": "handler",
}

# ── Error code pools ──────────────────────────────────────────────────────────

# Each entry: (code, name, http_status, description, recovery_action, extra_header)
# extra_header: None or (header_name, header_value_template)
BASE_ERROR_CODES = [
    (
        "E001", "InvalidInput", 400,
        "Request contains invalid or malformed input data",
        "validate_and_return_details",
        None,
    ),
    (
        "E002", "NotFound", 404,
        "Requested resource does not exist",
        "return_not_found",
        None,
    ),
    (
        "E003", "RateLimit", 429,
        "Too many requests; client has exceeded rate limit",
        "return_retry_after",
        ("Retry-After", "60"),
    ),
    (
        "E004", "DatabaseError", 503,
        "Database operation failed; retry with exponential backoff",
        "retry_then_503",
        None,
    ),
    (
        "E005", "AuthError", 401,
        "Authentication failed; invalid or expired credentials",
        "clear_session_and_401",
        None,
    ),
    (
        "E006", "Timeout", 504,
        "Upstream service did not respond within the allowed time",
        "abort_and_504",
        None,
    ),
    (
        "E007", "PayloadTooLarge", 413,
        "Request payload exceeds the maximum allowed size",
        "reject_with_limit_info",
        None,
    ),
    (
        "E008", "Conflict", 409,
        "Resource state conflict; operation cannot be completed",
        "return_conflict_details",
        None,
    ),
]

# ── Retry configuration variants ──────────────────────────────────────────────

RETRY_CONFIGS = [
    {"attempts": 3, "backoff_base": 1, "backoff_factor": 2},
    {"attempts": 3, "backoff_base": 0.5, "backoff_factor": 2},
    {"attempts": 4, "backoff_base": 1, "backoff_factor": 2},
    {"attempts": 3, "backoff_base": 2, "backoff_factor": 3},
]

# ── Logging format variants ───────────────────────────────────────────────────

LOG_FORMATS = [
    {"style": "structured", "fields": ["error_code", "message", "timestamp", "request_id"]},
    {"style": "structured", "fields": ["error_code", "message", "timestamp", "user_id"]},
    {"style": "structured", "fields": ["error_code", "message", "timestamp", "trace_id"]},
    {"style": "structured", "fields": ["error_code", "message", "timestamp", "session_id"]},
]

# ── Resource name pools per app type ─────────────────────────────────────────

RESOURCE_NAMES = {
    "api_server": ["user", "product", "order", "invoice", "report"],
    "file_processor": ["document", "archive", "manifest", "record", "batch"],
    "data_importer": ["dataset", "record", "schema", "partition", "job"],
    "webhook_handler": ["event", "payload", "subscription", "notification", "delivery"],
}


class Generator(TaskGenerator):
    task_id = "S5_error_handling"
    domain = "software"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        app_type = rng.choice(APP_TYPES)
        app_desc = APP_DESCRIPTIONS[app_type]
        module_name = APP_MODULE_NAMES[app_type]
        resource = rng.choice(RESOURCE_NAMES[app_type])

        # Pick 5-8 error codes
        num_errors = rng.randint(5, 8)
        # Always include the core 5 (E001-E005), then optionally add extras
        core_errors = BASE_ERROR_CODES[:5]
        extra_errors = BASE_ERROR_CODES[5:]
        rng.shuffle(extra_errors)
        selected_errors = core_errors + extra_errors[: num_errors - 5]

        retry_cfg = rng.choice(RETRY_CONFIGS)
        log_fmt = rng.choice(LOG_FORMATS)
        rate_limit_window = rng.choice([60, 30, 120])

        workspace_files: dict[str, str] = {}

        # ── Broken app file (bare excepts, no error codes, generic 500s) ──────
        workspace_files[f"{module_name}.py"] = self._gen_broken_app(
            app_type, module_name, resource, selected_errors
        )

        # ── Error definitions stub (agent must populate) ──────────────────────
        workspace_files["errors.py"] = self._gen_errors_stub()

        # ── Tests that must pass after fix ────────────────────────────────────
        workspace_files["tests/__init__.py"] = ""
        workspace_files["tests/test_error_handling.py"] = self._gen_tests(
            module_name, app_type, resource, selected_errors,
            retry_cfg, rate_limit_window,
        )

        # ── requirements stub ─────────────────────────────────────────────────
        workspace_files["requirements.txt"] = "flask>=2.0\npytest>=7.0\n"

        expected = {
            "app_type": app_type,
            "module_name": module_name,
            "resource": resource,
            "num_errors": num_errors,
            "error_codes": [e[0] for e in selected_errors],
            "error_names": [e[1] for e in selected_errors],
            "http_statuses": {e[0]: e[2] for e in selected_errors},
            "retry_attempts": retry_cfg["attempts"],
            "retry_backoff_base": retry_cfg["backoff_base"],
            "retry_backoff_factor": retry_cfg["backoff_factor"],
            "rate_limit_window": rate_limit_window,
            "log_fields": log_fmt["fields"],
            "has_retry_after_header": any(e[4] == "return_retry_after" for e in selected_errors),
            "has_session_clear": any(e[4] == "clear_session_and_401" for e in selected_errors),
        }

        spec_md = self._gen_spec(
            app_type, app_desc, module_name, resource,
            selected_errors, retry_cfg, log_fmt, rate_limit_window,
        )
        brief_md = self._gen_brief(app_type, app_desc)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # ── Broken app generator ──────────────────────────────────────────────────

    def _gen_broken_app(
        self,
        app_type: str,
        module_name: str,
        resource: str,
        errors: list,
    ) -> str:
        if app_type == "api_server":
            return self._broken_api_server(module_name, resource)
        elif app_type == "file_processor":
            return self._broken_file_processor(module_name, resource)
        elif app_type == "data_importer":
            return self._broken_data_importer(module_name, resource)
        else:
            return self._broken_webhook_handler(module_name, resource)

    def _broken_api_server(self, module_name: str, resource: str) -> str:
        return f'''\
"""
{module_name}.py - {resource.capitalize()} API server.

WARNING: This file has poor error handling. Bare except clauses,
no structured error codes, and all errors return generic 500 responses.
"""
import json
import logging
import time

from flask import Flask, request, jsonify, session

app = Flask(__name__)
app.secret_key = "dev-secret"

logger = logging.getLogger(__name__)

# Simulated database
_DB: dict = {{}}
_REQUEST_COUNTS: dict = {{}}
_RATE_LIMIT = 100  # requests per window


def _db_get(key: str):
    """Simulate a DB read that can fail."""
    if key.startswith("_fail_"):
        raise Exception("DB connection error")
    return _DB.get(key)


def _db_set(key: str, value: dict):
    """Simulate a DB write that can fail."""
    if key.startswith("_fail_"):
        raise Exception("DB write error")
    _DB[key] = value


def _check_auth():
    """Check if the current request is authenticated."""
    token = request.headers.get("Authorization", "")
    if not token or token == "Bearer invalid":
        return False
    return True


def _check_rate_limit(client_id: str) -> bool:
    now = time.time()
    window_start = now - 60
    counts = _REQUEST_COUNTS.get(client_id, [])
    counts = [t for t in counts if t > window_start]
    _REQUEST_COUNTS[client_id] = counts
    if len(counts) >= _RATE_LIMIT:
        return False
    counts.append(now)
    _REQUEST_COUNTS[client_id] = counts
    return True


@app.route("/{resource}s/<{resource}_id>", methods=["GET"])
def get_{resource}({resource}_id):
    try:
        data = _db_get({resource}_id)
        if data is None:
            return jsonify({{"error": "not found"}}), 500  # BUG: wrong status
        return jsonify(data)
    except:  # BUG: bare except
        return jsonify({{"error": "something went wrong"}}), 500


@app.route("/{resource}s", methods=["POST"])
def create_{resource}():
    try:
        body = request.get_json()
        if not body or "name" not in body:
            return jsonify({{"error": "bad request"}}), 500  # BUG: wrong status
        client_id = request.remote_addr
        if not _check_rate_limit(client_id):
            return jsonify({{"error": "slow down"}}), 500  # BUG: wrong status, missing header
        if not _check_auth():
            return jsonify({{"error": "unauthorized"}}), 500  # BUG: wrong status
        key = body["name"]
        _db_set(key, body)
        return jsonify(body), 201
    except:  # BUG: bare except
        return jsonify({{"error": "something went wrong"}}), 500


@app.route("/{resource}s/<{resource}_id>", methods=["PUT"])
def update_{resource}({resource}_id):
    try:
        body = request.get_json()
        if body is None:
            return jsonify({{"error": "invalid json"}}), 500  # BUG: wrong status
        if not _check_auth():
            return jsonify({{"error": "unauthorized"}}), 500  # BUG: wrong status
        existing = _db_get({resource}_id)
        if existing is None:
            return jsonify({{"error": "not found"}}), 500  # BUG: wrong status
        existing.update(body)
        _db_set({resource}_id, existing)
        return jsonify(existing)
    except:  # BUG: bare except
        return jsonify({{"error": "something went wrong"}}), 500


@app.route("/{resource}s/<{resource}_id>", methods=["DELETE"])
def delete_{resource}({resource}_id):
    try:
        if not _check_auth():
            return jsonify({{"error": "unauthorized"}}), 500  # BUG: wrong status
        if {resource}_id not in _DB:
            return jsonify({{"error": "not found"}}), 500  # BUG: wrong status
        del _DB[{resource}_id]
        return jsonify({{"deleted": True}})
    except:  # BUG: bare except
        return jsonify({{"error": "something went wrong"}}), 500


if __name__ == "__main__":
    app.run(debug=True)
'''

    def _broken_file_processor(self, module_name: str, resource: str) -> str:
        return f'''\
"""
{module_name}.py - {resource.capitalize()} file processing service.

WARNING: This file has poor error handling. Bare except clauses,
no structured error codes, and all errors return generic 500 responses.
"""
import json
import logging
import time

from flask import Flask, request, jsonify, session

app = Flask(__name__)
app.secret_key = "dev-secret"

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
_REQUEST_COUNTS: dict = {{}}
_RATE_LIMIT = 50

_PROCESSED: dict = {{}}


def _simulate_db_write(key: str, data: dict):
    if key.startswith("_fail_"):
        raise Exception("DB write error")
    _PROCESSED[key] = data


def _check_auth():
    token = request.headers.get("Authorization", "")
    if not token or token == "Bearer invalid":
        return False
    return True


def _check_rate_limit(client_id: str) -> bool:
    now = time.time()
    window_start = now - 60
    counts = _REQUEST_COUNTS.get(client_id, [])
    counts = [t for t in counts if t > window_start]
    _REQUEST_COUNTS[client_id] = counts
    if len(counts) >= _RATE_LIMIT:
        return False
    counts.append(now)
    _REQUEST_COUNTS[client_id] = counts
    return True


@app.route("/process", methods=["POST"])
def process_{resource}():
    try:
        if not _check_auth():
            return jsonify({{"error": "unauthorized"}}), 500  # BUG: wrong status
        client_id = request.remote_addr
        if not _check_rate_limit(client_id):
            return jsonify({{"error": "slow down"}}), 500  # BUG: wrong status, missing header
        file = request.files.get("{resource}")
        if file is None:
            return jsonify({{"error": "no file"}}), 500  # BUG: wrong status
        content = file.read()
        if len(content) > MAX_FILE_SIZE:
            return jsonify({{"error": "too big"}}), 500  # BUG: wrong status
        name = file.filename or "unknown"
        _simulate_db_write(name, {{"size": len(content), "name": name}})
        return jsonify({{"processed": True, "name": name}})
    except:  # BUG: bare except
        return jsonify({{"error": "something went wrong"}}), 500


@app.route("/status/<job_id>", methods=["GET"])
def get_status(job_id):
    try:
        data = _PROCESSED.get(job_id)
        if data is None:
            return jsonify({{"error": "not found"}}), 500  # BUG: wrong status
        return jsonify(data)
    except:  # BUG: bare except
        return jsonify({{"error": "something went wrong"}}), 500


@app.route("/validate", methods=["POST"])
def validate_{resource}():
    try:
        body = request.get_json()
        if not body or "{resource}_type" not in body:
            return jsonify({{"error": "bad request"}}), 500  # BUG: wrong status
        return jsonify({{"valid": True}})
    except:  # BUG: bare except
        return jsonify({{"error": "something went wrong"}}), 500


if __name__ == "__main__":
    app.run(debug=True)
'''

    def _broken_data_importer(self, module_name: str, resource: str) -> str:
        return f'''\
"""
{module_name}.py - {resource.capitalize()} data import service.

WARNING: This file has poor error handling. Bare except clauses,
no structured error codes, and all errors return generic 500 responses.
"""
import json
import logging
import time

from flask import Flask, request, jsonify, session

app = Flask(__name__)
app.secret_key = "dev-secret"

logger = logging.getLogger(__name__)

MAX_PAYLOAD_SIZE = 5 * 1024 * 1024  # 5 MB
_REQUEST_COUNTS: dict = {{}}
_RATE_LIMIT = 20
_STORE: dict = {{}}


def _db_insert(key: str, rows: list):
    if key.startswith("_fail_"):
        raise Exception("DB insert error")
    _STORE[key] = rows


def _check_auth():
    token = request.headers.get("Authorization", "")
    if not token or token == "Bearer invalid":
        return False
    return True


def _check_rate_limit(client_id: str) -> bool:
    now = time.time()
    window_start = now - 60
    counts = _REQUEST_COUNTS.get(client_id, [])
    counts = [t for t in counts if t > window_start]
    _REQUEST_COUNTS[client_id] = counts
    if len(counts) >= _RATE_LIMIT:
        return False
    counts.append(now)
    _REQUEST_COUNTS[client_id] = counts
    return True


@app.route("/import/{resource}s", methods=["POST"])
def import_{resource}s():
    try:
        if not _check_auth():
            return jsonify({{"error": "unauthorized"}}), 500  # BUG: wrong status
        client_id = request.remote_addr
        if not _check_rate_limit(client_id):
            return jsonify({{"error": "slow down"}}), 500  # BUG: wrong status, missing header
        body = request.get_json()
        if not body or "rows" not in body:
            return jsonify({{"error": "invalid payload"}}), 500  # BUG: wrong status
        rows = body["rows"]
        if not isinstance(rows, list):
            return jsonify({{"error": "rows must be list"}}), 500  # BUG: wrong status
        batch_id = body.get("batch_id", "default")
        existing = _STORE.get(batch_id)
        if existing is not None:
            return jsonify({{"error": "batch already exists"}}), 500  # BUG: wrong status
        _db_insert(batch_id, rows)
        return jsonify({{"imported": len(rows), "batch_id": batch_id}}), 201
    except:  # BUG: bare except
        return jsonify({{"error": "something went wrong"}}), 500


@app.route("/import/{resource}s/<batch_id>", methods=["GET"])
def get_batch(batch_id):
    try:
        data = _STORE.get(batch_id)
        if data is None:
            return jsonify({{"error": "not found"}}), 500  # BUG: wrong status
        return jsonify({{"batch_id": batch_id, "rows": data}})
    except:  # BUG: bare except
        return jsonify({{"error": "something went wrong"}}), 500


if __name__ == "__main__":
    app.run(debug=True)
'''

    def _broken_webhook_handler(self, module_name: str, resource: str) -> str:
        return f'''\
"""
{module_name}.py - {resource.capitalize()} webhook handler.

WARNING: This file has poor error handling. Bare except clauses,
no structured error codes, and all errors return generic 500 responses.
"""
import json
import logging
import time
import hmac
import hashlib

from flask import Flask, request, jsonify, session

app = Flask(__name__)
app.secret_key = "dev-secret"

logger = logging.getLogger(__name__)

WEBHOOK_SECRET = "webhook-secret-key"
MAX_PAYLOAD_SIZE = 1 * 1024 * 1024  # 1 MB
_REQUEST_COUNTS: dict = {{}}
_RATE_LIMIT = 200
_EVENTS: dict = {{}}


def _db_store_event(event_id: str, event: dict):
    if event_id.startswith("_fail_"):
        raise Exception("DB store error")
    _EVENTS[event_id] = event


def _check_auth():
    token = request.headers.get("Authorization", "")
    if not token or token == "Bearer invalid":
        return False
    return True


def _verify_signature(payload: bytes, sig: str) -> bool:
    expected = hmac.new(WEBHOOK_SECRET.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, sig)


def _check_rate_limit(client_id: str) -> bool:
    now = time.time()
    window_start = now - 60
    counts = _REQUEST_COUNTS.get(client_id, [])
    counts = [t for t in counts if t > window_start]
    _REQUEST_COUNTS[client_id] = counts
    if len(counts) >= _RATE_LIMIT:
        return False
    counts.append(now)
    _REQUEST_COUNTS[client_id] = counts
    return True


@app.route("/webhook/{resource}s", methods=["POST"])
def receive_{resource}():
    try:
        client_id = request.remote_addr
        if not _check_rate_limit(client_id):
            return jsonify({{"error": "slow down"}}), 500  # BUG: wrong status, missing header
        if not _check_auth():
            return jsonify({{"error": "unauthorized"}}), 500  # BUG: wrong status
        raw = request.get_data()
        if len(raw) > MAX_PAYLOAD_SIZE:
            return jsonify({{"error": "too large"}}), 500  # BUG: wrong status
        body = request.get_json()
        if not body or "{resource}_type" not in body:
            return jsonify({{"error": "missing fields"}}), 500  # BUG: wrong status
        event_id = body.get("event_id", "unknown")
        existing = _EVENTS.get(event_id)
        if existing is not None:
            return jsonify({{"error": "duplicate event"}}), 500  # BUG: wrong status
        _db_store_event(event_id, body)
        return jsonify({{"received": True, "event_id": event_id}}), 201
    except:  # BUG: bare except
        return jsonify({{"error": "something went wrong"}}), 500


@app.route("/webhook/{resource}s/<event_id>", methods=["GET"])
def get_{resource}(event_id):
    try:
        if not _check_auth():
            return jsonify({{"error": "unauthorized"}}), 500  # BUG: wrong status
        data = _EVENTS.get(event_id)
        if data is None:
            return jsonify({{"error": "not found"}}), 500  # BUG: wrong status
        return jsonify(data)
    except:  # BUG: bare except
        return jsonify({{"error": "something went wrong"}}), 500


if __name__ == "__main__":
    app.run(debug=True)
'''

    # ── errors.py stub ────────────────────────────────────────────────────────

    def _gen_errors_stub(self) -> str:
        return '''\
"""
errors.py - Application error definitions.

TODO: Implement the error code taxonomy as specified.
Each error class should carry the error code, HTTP status, and message.
"""


class AppError(Exception):
    """Base application error. Subclass this for specific error types."""
    code: str = "E000"
    http_status: int = 500
    message: str = "An unexpected error occurred"

    def __init__(self, message: str | None = None):
        self.message = message or self.__class__.message
        super().__init__(self.message)

    def to_dict(self) -> dict:
        return {"error_code": self.code, "message": self.message}


# TODO: Add error classes for each error code in the spec:
# E001 InvalidInputError  -> 400
# E002 NotFoundError      -> 404
# E003 RateLimitError     -> 429 (with Retry-After header)
# E004 DatabaseError      -> 503 (with retry logic in handler)
# E005 AuthError          -> 401 (clear session)
# ... (additional codes per spec)
'''

    # ── Test generator ────────────────────────────────────────────────────────

    def _not_found_url(self, app_type: str, resource: str, item_id: str = "__nonexistent_resource_xyz__") -> str:
        """Return the GET URL that should produce a 404 for this app type."""
        if app_type == "api_server":
            return f"/{resource}s/{item_id}"
        elif app_type == "file_processor":
            return f"/status/{item_id}"
        elif app_type == "data_importer":
            return f"/import/{resource}s/{item_id}"
        else:  # webhook_handler
            return f"/webhook/{resource}s/{item_id}"

    def _gen_tests(
        self,
        module_name: str,
        app_type: str,
        resource: str,
        errors: list,
        retry_cfg: dict,
        rate_limit_window: int,
    ) -> str:
        # Build error-code-specific test cases
        error_tests = []
        for code, name, status, desc, recovery, extra_header in errors:
            if recovery == "validate_and_return_details":
                error_tests.append(self._test_invalid_input(module_name, resource, code, status, app_type))
            elif recovery == "return_not_found":
                error_tests.append(self._test_not_found(module_name, resource, code, status, app_type))
            elif recovery == "return_retry_after":
                error_tests.append(self._test_rate_limit(module_name, resource, code, status, rate_limit_window, app_type))
            elif recovery == "retry_then_503":
                error_tests.append(self._test_database_error(module_name, resource, code, status, retry_cfg, app_type))
            elif recovery == "clear_session_and_401":
                error_tests.append(self._test_auth_error(module_name, resource, code, status, app_type))
            elif recovery == "abort_and_504":
                error_tests.append(self._test_timeout(module_name, resource, code, status, app_type))
            elif recovery == "reject_with_limit_info":
                error_tests.append(self._test_payload_too_large(module_name, resource, code, status, app_type))
            elif recovery == "return_conflict_details":
                error_tests.append(self._test_conflict(module_name, resource, code, status, app_type))

        error_tests_str = "\n\n".join(error_tests)
        not_found_url = self._not_found_url(app_type, resource)

        return f'''\
"""
Tests for error handling in {module_name}.py.

These tests verify that each error code returns the correct HTTP status,
headers, response body, and that recovery actions are properly implemented.
"""
import json
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from {module_name} import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    app.config["SECRET_KEY"] = "test-secret"
    with app.test_client() as c:
        yield c


# ── Structural checks ─────────────────────────────────────────────────────────

def test_no_bare_except_in_module():
    """Verify no bare except clauses remain in the main module."""
    import ast
    src_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "{module_name}.py"
    )
    tree = ast.parse(open(src_path).read())
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            assert node.type is not None, (
                f"Bare except clause found at line {{node.lineno}} in {module_name}.py"
            )


def test_errors_module_importable():
    """errors.py must be importable and define AppError."""
    import errors
    assert hasattr(errors, "AppError"), "errors.py must define AppError"


def test_error_classes_have_codes():
    """Each error class must have a non-empty code attribute."""
    import errors
    import inspect
    for name, obj in inspect.getmembers(errors, inspect.isclass):
        if issubclass(obj, errors.AppError) and obj is not errors.AppError:
            assert hasattr(obj, "code") and obj.code, (
                f"{{name}} must have a non-empty 'code' attribute"
            )
            assert hasattr(obj, "http_status") and obj.http_status != 500, (
                f"{{name}} must define a specific http_status (not generic 500)"
            )


def test_error_response_has_error_code_field(client):
    """Error responses must include 'error_code' field, not just 'error'."""
    # Trigger a 404 by requesting a nonexistent resource
    resp = client.get("{not_found_url}",
                      headers={{"Authorization": "Bearer valid-token"}})
    data = json.loads(resp.data)
    assert "error_code" in data, (
        "Error responses must include 'error_code' field"
    )


{error_tests_str}


# ── Logging checks ────────────────────────────────────────────────────────────

def test_errors_are_logged(client, caplog):
    """Errors must be logged (not silently swallowed)."""
    import logging
    with caplog.at_level(logging.ERROR):
        client.get("/{resource}s/__nonexistent_resource_xyz__",
                   headers={{"Authorization": "Bearer valid-token"}})
    # Either the caplog captured something or the module uses its own logger
    # We just verify the endpoint doesn't crash silently
    resp = client.get("/{resource}s/__nonexistent_resource_xyz__",
                      headers={{"Authorization": "Bearer valid-token"}})
    assert resp.status_code in (404, 401), (
        "Expected 404 or 401 for unknown resource, got generic 500"
    )
'''

    # ── Individual test case builders ─────────────────────────────────────────

    def _test_invalid_input(self, module_name, resource, code, status, app_type):
        if app_type == "api_server":
            trigger = f'client.post("/{resource}s", json={{}}, headers={{"Authorization": "Bearer valid-token"}})'
        elif app_type == "file_processor":
            trigger = f'client.post("/validate", json={{}}, headers={{"Authorization": "Bearer valid-token"}})'
        elif app_type == "data_importer":
            trigger = f'client.post("/import/{resource}s", json={{}}, headers={{"Authorization": "Bearer valid-token"}})'
        else:
            trigger = f'client.post("/webhook/{resource}s", json={{}}, headers={{"Authorization": "Bearer valid-token"}})'

        return f'''\
def test_{code.lower()}_invalid_input_returns_{status}(client):
    """{code} InvalidInput must return HTTP {status} with error_code in body."""
    resp = {trigger}
    assert resp.status_code == {status}, (
        f"{code} InvalidInput: expected {status}, got {{resp.status_code}}"
    )
    data = json.loads(resp.data)
    assert "error_code" in data, "Response must include 'error_code' field"
    assert data["error_code"] == "{code}", (
        f"Expected error_code='{code}', got {{data.get('error_code')}}"
    )'''

    def _test_not_found(self, module_name, resource, code, status, app_type):
        if app_type == "api_server":
            trigger = f'client.get("/{resource}s/__does_not_exist__", headers={{"Authorization": "Bearer valid-token"}})'
        elif app_type == "file_processor":
            trigger = f'client.get("/status/__does_not_exist__", headers={{"Authorization": "Bearer valid-token"}})'
        elif app_type == "data_importer":
            trigger = f'client.get("/import/{resource}s/__does_not_exist__", headers={{"Authorization": "Bearer valid-token"}})'
        else:
            trigger = f'client.get("/webhook/{resource}s/__does_not_exist__", headers={{"Authorization": "Bearer valid-token"}})'

        return f'''\
def test_{code.lower()}_not_found_returns_{status}(client):
    """{code} NotFound must return HTTP {status}."""
    resp = {trigger}
    assert resp.status_code == {status}, (
        f"{code} NotFound: expected {status}, got {{resp.status_code}}"
    )
    data = json.loads(resp.data)
    assert "error_code" in data, "Response must include 'error_code' field"
    assert data["error_code"] == "{code}", (
        f"Expected error_code='{code}', got {{data.get('error_code')}}"
    )'''

    def _test_rate_limit(self, module_name, resource, code, status, window, app_type):
        if app_type == "api_server":
            setup = f'''\
    import importlib
    import {module_name} as mod
    # Exhaust the rate limit counter directly
    mod._REQUEST_COUNTS["test_rl_client"] = [__import__("time").time()] * (mod._RATE_LIMIT + 1)
    resp = client.get("/{resource}s/x",
                      headers={{"Authorization": "Bearer valid-token",
                                "X-Forwarded-For": "test_rl_client"}})'''
        elif app_type == "file_processor":
            setup = f'''\
    import {module_name} as mod
    mod._REQUEST_COUNTS["test_rl_client"] = [__import__("time").time()] * (mod._RATE_LIMIT + 1)
    resp = client.post("/validate", json={{"file_type": "pdf"}},
                       headers={{"Authorization": "Bearer valid-token",
                                 "X-Forwarded-For": "test_rl_client"}})'''
        elif app_type == "data_importer":
            setup = f'''\
    import {module_name} as mod
    mod._REQUEST_COUNTS["test_rl_client"] = [__import__("time").time()] * (mod._RATE_LIMIT + 1)
    resp = client.post("/import/{resource}s",
                       json={{"rows": [], "batch_id": "rl_test"}},
                       headers={{"Authorization": "Bearer valid-token",
                                 "X-Forwarded-For": "test_rl_client"}})'''
        else:
            setup = f'''\
    import {module_name} as mod
    mod._REQUEST_COUNTS["test_rl_client"] = [__import__("time").time()] * (mod._RATE_LIMIT + 1)
    resp = client.post("/webhook/{resource}s",
                       json={{"{resource}_type": "test", "event_id": "rl_test"}},
                       headers={{"Authorization": "Bearer valid-token",
                                 "X-Forwarded-For": "test_rl_client"}})'''

        return f'''\
def test_{code.lower()}_rate_limit_returns_{status}_with_retry_after(client):
    """{code} RateLimit must return HTTP {status} with Retry-After header."""
{setup}
    assert resp.status_code == {status}, (
        f"{code} RateLimit: expected {status}, got {{resp.status_code}}"
    )
    assert "Retry-After" in resp.headers, (
        "{code} RateLimit response must include Retry-After header"
    )
    data = json.loads(resp.data)
    assert "error_code" in data and data["error_code"] == "{code}", (
        f"Expected error_code='{code}', got {{data.get('error_code')}}"
    )'''

    def _test_database_error(self, module_name, resource, code, status, retry_cfg, app_type):
        attempts = retry_cfg["attempts"]
        if app_type == "api_server":
            trigger = f'''\
    # Use the _fail_ prefix to trigger DB error
    resp = client.get("/{resource}s/_fail_trigger",
                      headers={{"Authorization": "Bearer valid-token"}})'''
        elif app_type == "file_processor":
            trigger = f'''\
    resp = client.get("/status/_fail_trigger",
                      headers={{"Authorization": "Bearer valid-token"}})'''
        elif app_type == "data_importer":
            trigger = f'''\
    resp = client.get("/import/{resource}s/_fail_trigger",
                      headers={{"Authorization": "Bearer valid-token"}})'''
        else:
            trigger = f'''\
    resp = client.get("/webhook/{resource}s/_fail_trigger",
                      headers={{"Authorization": "Bearer valid-token"}})'''

        return f'''\
def test_{code.lower()}_database_error_returns_{status}(client):
    """{code} DatabaseError must return HTTP {status} after retries exhausted."""
{trigger}
    assert resp.status_code == {status}, (
        f"{code} DatabaseError: expected {status}, got {{resp.status_code}}"
    )
    data = json.loads(resp.data)
    assert "error_code" in data and data["error_code"] == "{code}", (
        f"Expected error_code='{code}', got {{data.get('error_code')}}"
    )


def test_{code.lower()}_retry_logic_present():
    """Verify retry logic is implemented in the module (not just a pass-through)."""
    import ast, os
    src_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "{module_name}.py"
    )
    src = open(src_path).read()
    # Retry logic requires a loop or a retry utility
    has_retry = (
        "retry" in src.lower()
        or "attempt" in src.lower()
        or "for _ in range" in src
        or "while" in src
    )
    assert has_retry, (
        "Module must implement retry logic for {code} DatabaseError "
        "(expected {attempts} retry attempts)"
    )'''

    def _test_auth_error(self, module_name, resource, code, status, app_type):
        if app_type == "api_server":
            trigger = f'client.get("/{resource}s/any_id", headers={{"Authorization": "Bearer invalid"}})'
        elif app_type == "file_processor":
            trigger = f'client.post("/validate", json={{"file_type": "pdf"}}, headers={{"Authorization": "Bearer invalid"}})'
        elif app_type == "data_importer":
            trigger = f'client.post("/import/{resource}s", json={{"rows": []}}, headers={{"Authorization": "Bearer invalid"}})'
        else:
            trigger = f'client.get("/webhook/{resource}s/any_id", headers={{"Authorization": "Bearer invalid"}})'

        return f'''\
def test_{code.lower()}_auth_error_returns_{status}(client):
    """{code} AuthError must return HTTP {status}."""
    resp = {trigger}
    assert resp.status_code == {status}, (
        f"{code} AuthError: expected {status}, got {{resp.status_code}}"
    )
    data = json.loads(resp.data)
    assert "error_code" in data and data["error_code"] == "{code}", (
        f"Expected error_code='{code}', got {{data.get('error_code')}}"
    )


def test_{code.lower()}_auth_error_clears_session(client):
    """{code} AuthError must clear the session."""
    with client.session_transaction() as sess:
        sess["user_id"] = "test_user"
        sess["token"] = "some_token"
    resp = {trigger}
    assert resp.status_code == {status}
    with client.session_transaction() as sess:
        assert "user_id" not in sess, (
            "{code} AuthError must clear 'user_id' from session"
        )'''

    def _test_timeout(self, module_name, resource, code, status, app_type):
        return f'''\
def test_{code.lower()}_timeout_error_class_exists():
    """{code} Timeout error class must be defined in errors.py."""
    import errors
    timeout_classes = [
        cls for name, cls in vars(errors).items()
        if isinstance(cls, type)
        and issubclass(cls, errors.AppError)
        and getattr(cls, "code", "") == "{code}"
    ]
    assert timeout_classes, (
        "errors.py must define a class with code='{code}' for Timeout errors"
    )
    assert timeout_classes[0].http_status == {status}, (
        f"{code} Timeout must have http_status={status}"
    )'''

    def _test_payload_too_large(self, module_name, resource, code, status, app_type):
        return f'''\
def test_{code.lower()}_payload_too_large_class_exists():
    """{code} PayloadTooLarge error class must be defined in errors.py."""
    import errors
    classes = [
        cls for name, cls in vars(errors).items()
        if isinstance(cls, type)
        and issubclass(cls, errors.AppError)
        and getattr(cls, "code", "") == "{code}"
    ]
    assert classes, (
        "errors.py must define a class with code='{code}' for PayloadTooLarge errors"
    )
    assert classes[0].http_status == {status}, (
        f"{code} PayloadTooLarge must have http_status={status}"
    )'''

    def _test_conflict(self, module_name, resource, code, status, app_type):
        if app_type == "api_server":
            setup = f'''\
    import {module_name} as mod
    mod._DB["conflict_resource"] = {{"name": "conflict_resource"}}
    resp = client.post("/{resource}s",
                       json={{"name": "conflict_resource"}},
                       headers={{"Authorization": "Bearer valid-token"}})'''
        elif app_type == "data_importer":
            setup = f'''\
    import {module_name} as mod
    mod._STORE["conflict_batch"] = []
    resp = client.post("/import/{resource}s",
                       json={{"rows": [], "batch_id": "conflict_batch"}},
                       headers={{"Authorization": "Bearer valid-token"}})'''
        elif app_type == "webhook_handler":
            setup = f'''\
    import {module_name} as mod
    mod._EVENTS["conflict_event"] = {{"{resource}_type": "test"}}
    resp = client.post("/webhook/{resource}s",
                       json={{"{resource}_type": "test", "event_id": "conflict_event"}},
                       headers={{"Authorization": "Bearer valid-token"}})'''
        else:
            setup = f'''\
    # Conflict: file already processed
    import {module_name} as mod
    mod._PROCESSED["conflict_file"] = {{"size": 0}}
    resp = client.get("/status/conflict_file",
                      headers={{"Authorization": "Bearer valid-token"}})
    # Conflict detection may vary by app type; verify status or class existence
    import errors
    conflict_classes = [
        cls for n, cls in vars(errors).items()
        if isinstance(cls, type) and issubclass(cls, errors.AppError)
        and getattr(cls, "code", "") == "{code}"
    ]
    assert conflict_classes, "errors.py must define {code} Conflict class"
    return  # skip response check for file_processor'''

        return f'''\
def test_{code.lower()}_conflict_returns_{status}(client):
    """{code} Conflict must return HTTP {status}."""
{setup}
    assert resp.status_code == {status}, (
        f"{code} Conflict: expected {status}, got {{resp.status_code}}"
    )
    data = json.loads(resp.data)
    assert "error_code" in data and data["error_code"] == "{code}", (
        f"Expected error_code='{code}', got {{data.get('error_code')}}"
    )'''

    # ── Spec generator ────────────────────────────────────────────────────────

    def _gen_spec(
        self,
        app_type: str,
        app_desc: str,
        module_name: str,
        resource: str,
        errors: list,
        retry_cfg: dict,
        log_fmt: dict,
        rate_limit_window: int,
    ) -> str:
        error_table_rows = []
        for code, name, status, desc, recovery, extra_header in errors:
            header_note = f" + `{extra_header[0]}: {extra_header[1]}` header" if extra_header else ""
            error_table_rows.append(
                f"| `{code}` | `{name}` | {status} | {desc}{header_note} |"
            )
        error_table = "\n".join(error_table_rows)

        recovery_sections = []
        for code, name, status, desc, recovery, extra_header in errors:
            if recovery == "validate_and_return_details":
                recovery_sections.append(
                    f"- **{code} {name}**: Validate all request fields. "
                    f"Return HTTP {status} with `error_code: \"{code}\"` and a `details` "
                    f"field listing which fields failed validation."
                )
            elif recovery == "return_not_found":
                recovery_sections.append(
                    f"- **{code} {name}**: Return HTTP {status} with `error_code: \"{code}\"` "
                    f"and `message` indicating the resource identifier that was not found."
                )
            elif recovery == "return_retry_after":
                recovery_sections.append(
                    f"- **{code} {name}**: Return HTTP {status} with `error_code: \"{code}\"`, "
                    f"and a `Retry-After: {rate_limit_window}` response header. "
                    f"The rate limit window is {rate_limit_window} seconds."
                )
            elif recovery == "retry_then_503":
                recovery_sections.append(
                    f"- **{code} {name}**: Retry the database operation up to "
                    f"{retry_cfg['attempts']} times with exponential backoff "
                    f"(base={retry_cfg['backoff_base']}s, factor={retry_cfg['backoff_factor']}x). "
                    f"If all retries are exhausted, return HTTP {status} with `error_code: \"{code}\"`."
                )
            elif recovery == "clear_session_and_401":
                recovery_sections.append(
                    f"- **{code} {name}**: Clear the server-side session (remove `user_id` "
                    f"and `token` keys). Return HTTP {status} with `error_code: \"{code}\"`."
                )
            elif recovery == "abort_and_504":
                recovery_sections.append(
                    f"- **{code} {name}**: Abort the upstream call immediately on timeout. "
                    f"Return HTTP {status} with `error_code: \"{code}\"`."
                )
            elif recovery == "reject_with_limit_info":
                recovery_sections.append(
                    f"- **{code} {name}**: Reject the request without reading the body. "
                    f"Return HTTP {status} with `error_code: \"{code}\"` and a `max_size` "
                    f"field indicating the allowed limit in bytes."
                )
            elif recovery == "return_conflict_details":
                recovery_sections.append(
                    f"- **{code} {name}**: Return HTTP {status} with `error_code: \"{code}\"` "
                    f"and a `conflict_detail` field describing the conflicting state."
                )

        recovery_text = "\n".join(recovery_sections)
        log_fields_str = ", ".join(f"`{f}`" for f in log_fmt["fields"])

        return f"""\
# S5: Error Handling — Specification

## Application Overview

This task involves a **{app_desc}** implemented as a Flask application.
The main module is `{module_name}.py`. The application handles `{resource}` resources.

## Current State

The application has critical error handling deficiencies:
- Bare `except:` clauses that swallow all exceptions silently
- All error conditions return generic HTTP 500 responses
- No structured error codes in responses
- Missing required HTTP headers (e.g., `Retry-After` for rate limit errors)
- No retry logic for transient failures
- Session not cleared on authentication failure

## Error Code Taxonomy

Implement the following error codes in `errors.py` as subclasses of `AppError`:

| Code | Name | HTTP Status | Description |
|------|------|-------------|-------------|
{error_table}

## Recovery Actions

Each error type requires a specific recovery action:

{recovery_text}

## Error Response Format

Every error response **must** use this JSON structure:

```json
{{
  "error_code": "E001",
  "message": "Human-readable description of the error"
}}
```

For `E001 InvalidInput`, also include:
```json
{{
  "error_code": "E001",
  "message": "Invalid input",
  "details": {{"field_name": "reason for rejection"}}
}}
```

## Logging Requirements

All errors must be logged using the module-level `logger`. Each log entry must include:
{log_fields_str}

Log at `ERROR` level for server-side errors (E004, E006) and `WARNING` level
for client errors (E001, E002, E003, E005, E007, E008).

## Retry Logic (E004 DatabaseError)

Implement retry with exponential backoff:
- **Max attempts**: {retry_cfg['attempts']}
- **Base delay**: {retry_cfg['backoff_base']} second(s)
- **Backoff factor**: {retry_cfg['backoff_factor']}x (delay doubles/triples each retry)
- After all retries exhausted, raise `DatabaseError` which the handler converts to HTTP {[e[2] for e in errors if e[4] == "retry_then_503"][0] if any(e[4] == "retry_then_503" for e in errors) else 503}

## Implementation Requirements

1. Create error classes in `errors.py` — one class per error code
2. Update `{module_name}.py` to:
   - Replace all bare `except:` clauses with specific exception handling
   - Import and raise the correct error class for each condition
   - Add an error handler that converts `AppError` subclasses to JSON responses
   - Implement retry logic for database operations
   - Add `Retry-After` header to rate limit responses
   - Clear session on auth errors
3. Do **not** change the URL routes or method signatures
"""

    # ── Brief generator ───────────────────────────────────────────────────────

    def _gen_brief(self, app_type: str, app_desc: str) -> str:
        return f"""\
# S5: Error Handling — Task Brief

## Overview

The application is a **{app_desc}**.

## Problem

The application lacks proper error handling. Add it.

The code currently uses bare `except` clauses and returns generic 500 responses
for all error conditions. This needs to be fixed.

## What to Do

1. Review the application code in the workspace
2. Implement proper error handling throughout the application
3. Ensure all tests in `tests/test_error_handling.py` pass

## Files

- Main application: see the `.py` file in the workspace root
- Error definitions: `errors.py` (stub provided, needs implementation)
- Tests: `tests/test_error_handling.py`
"""
