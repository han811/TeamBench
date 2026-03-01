"""
Parameterized generator for TRAP1: Spec Conflict.

Each seed produces a REST API with 7 endpoints (4 strict + 3 relaxed).
The structural contradiction between api_spec.yaml and CHANGELOG.md is the same
across all seeds; only variable/field names and report type lists change.
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── Seed-parameterized name pools ─────────────────────────────────────────────

# User model field names (first = "name", second = "email")
USER_NAME_FIELDS = ["name", "full_name", "username", "display_name"]
USER_EMAIL_FIELDS = ["email", "email_address", "contact_email", "user_email"]

# Item model field names
ITEM_NAME_FIELDS = ["name", "title", "product_name", "item_name"]
ITEM_PRICE_FIELDS = ["price", "cost", "unit_price", "amount"]

# Order model field names
ORDER_USER_ID_FIELDS = ["user_id", "buyer_id", "customer_id", "owner_id"]
ORDER_ITEM_ID_FIELDS = ["item_id", "product_id", "sku_id", "listing_id"]
ORDER_QTY_FIELDS = ["quantity", "qty", "count", "num_units"]

# Report type lists (4 allowed values each, varies by seed)
REPORT_TYPE_SETS = [
    ["summary", "detailed", "audit", "export"],
    ["daily", "weekly", "monthly", "annual"],
    ["sales", "inventory", "revenue", "compliance"],
    ["full", "partial", "delta", "snapshot"],
    ["html", "pdf", "csv", "json"],
    ["internal", "external", "regulatory", "executive"],
    ["usage", "billing", "performance", "security"],
    ["alpha", "beta", "gamma", "delta"],
    ["standard", "extended", "minimal", "verbose"],
    ["ops", "finance", "engineering", "legal"],
]

# API version strings
API_VERSIONS = ["v1", "v2", "v3", "v1.0", "v2.0"]

# App module names
APP_NAMES = [
    "marketplace_api", "catalog_api", "commerce_api", "platform_api",
    "storefront_api", "exchange_api", "portal_api", "hub_api",
    "gateway_api", "nexus_api",
]

# Batch import field descriptions (seed variation for CHANGELOG)
BATCH_IMPORT_USECASES = [
    "bulk migration workflows",
    "legacy data imports",
    "mass onboarding pipelines",
    "historical data ingestion",
    "partner data sync",
]

SEARCH_USECASES = [
    "integration partner queries",
    "federated search adapters",
    "external system queries",
    "partner API integrations",
    "third-party search connectors",
]

WEBHOOK_USECASES = [
    "registered partner webhooks",
    "third-party event callbacks",
    "external notification handlers",
    "partner event streams",
    "integration event receivers",
]


class Generator(TaskGenerator):
    task_id = "TRAP1_spec_conflict"
    domain = "Security"
    difficulty = "expert"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % 10

        # Pick field names for this seed
        user_name_f = USER_NAME_FIELDS[seed % len(USER_NAME_FIELDS)]
        user_email_f = USER_EMAIL_FIELDS[seed % len(USER_EMAIL_FIELDS)]
        item_name_f = ITEM_NAME_FIELDS[seed % len(ITEM_NAME_FIELDS)]
        item_price_f = ITEM_PRICE_FIELDS[seed % len(ITEM_PRICE_FIELDS)]
        order_uid_f = ORDER_USER_ID_FIELDS[seed % len(ORDER_USER_ID_FIELDS)]
        order_iid_f = ORDER_ITEM_ID_FIELDS[seed % len(ORDER_ITEM_ID_FIELDS)]
        order_qty_f = ORDER_QTY_FIELDS[seed % len(ORDER_QTY_FIELDS)]

        report_types = REPORT_TYPE_SETS[seed % len(REPORT_TYPE_SETS)]
        api_version = API_VERSIONS[seed % len(API_VERSIONS)]
        app_name = APP_NAMES[seed % len(APP_NAMES)]

        batch_usecase = BATCH_IMPORT_USECASES[seed % len(BATCH_IMPORT_USECASES)]
        search_usecase = SEARCH_USECASES[seed % len(SEARCH_USECASES)]
        webhook_usecase = WEBHOOK_USECASES[seed % len(WEBHOOK_USECASES)]

        params = dict(
            user_name_f=user_name_f,
            user_email_f=user_email_f,
            item_name_f=item_name_f,
            item_price_f=item_price_f,
            order_uid_f=order_uid_f,
            order_iid_f=order_iid_f,
            order_qty_f=order_qty_f,
            report_types=report_types,
            api_version=api_version,
            app_name=app_name,
            batch_usecase=batch_usecase,
            search_usecase=search_usecase,
            webhook_usecase=webhook_usecase,
        )

        workspace_files = self._make_workspace(**params)

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "TRAP1_spec_conflict")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="TRAP1_spec_conflict",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "strict_endpoints": ["users", "items", "orders", "reports"],
                "relaxed_endpoints": ["batch-import", "search", "webhooks"],
                "report_types": report_types,
                "user_name_field": user_name_f,
                "user_email_field": user_email_f,
                "item_name_field": item_name_f,
                "item_price_field": item_price_f,
                "order_user_id_field": order_uid_f,
                "order_item_id_field": order_iid_f,
                "order_quantity_field": order_qty_f,
                "seed": seed,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "expert", "category": "Security"},
        )

    def _make_workspace(
        self,
        user_name_f: str,
        user_email_f: str,
        item_name_f: str,
        item_price_f: str,
        order_uid_f: str,
        order_iid_f: str,
        order_qty_f: str,
        report_types: list,
        api_version: str,
        app_name: str,
        batch_usecase: str,
        search_usecase: str,
        webhook_usecase: str,
    ) -> dict:
        files = {}

        report_types_py = repr(report_types)
        report_types_yaml = "\n".join(f"          - {rt}" for rt in report_types)
        report_types_str = ", ".join(report_types)

        # ── app/__init__.py ───────────────────────────────────────────────────
        files["app/__init__.py"] = f'''\
"""
{app_name} — Flask application factory.
"""
from flask import Flask


def create_app():
    app = Flask(__name__)
    app.config["TESTING"] = False

    from app.routes import register_routes
    register_routes(app)

    return app
'''

        # ── app/config.py ─────────────────────────────────────────────────────
        files["app/config.py"] = f'''\
import os

API_VERSION = "{api_version}"
STRICT_MODE = False
ALLOWED_REPORT_TYPES = {report_types_py}
'''

        # ── app/models.py ─────────────────────────────────────────────────────
        files["app/models.py"] = f'''\
"""Data models for {app_name}."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    {user_name_f}: str
    {user_email_f}: str
    id: Optional[int] = None


@dataclass
class Item:
    {item_name_f}: str
    {item_price_f}: float
    id: Optional[int] = None


@dataclass
class Order:
    {order_uid_f}: int
    {order_iid_f}: int
    {order_qty_f}: int
    id: Optional[int] = None


@dataclass
class Report:
    report_type: str
    id: Optional[int] = None
'''

        # ── app/validators.py ─────────────────────────────────────────────────
        files["app/validators.py"] = f'''\
"""
Input validation helpers for {app_name}.

These validators enforce strict rules. They should only be applied to
endpoints where strict validation is appropriate.
"""
import re
from typing import Optional


def validate_email(value: str) -> bool:
    """Return True if value looks like a valid email address."""
    return bool(re.match(r"^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$", value))


def validate_user(data: dict) -> Optional[str]:
    """Validate user payload. Returns error string or None."""
    if not data.get("{user_name_f}"):
        return "'{user_name_f}' is required and must be non-empty"
    if not data.get("{user_email_f}"):
        return "'{user_email_f}' is required"
    if not validate_email(data["{user_email_f}"]):
        return "'{user_email_f}' must be a valid email address"
    return None


def validate_item(data: dict) -> Optional[str]:
    """Validate item payload. Returns error string or None."""
    if not data.get("{item_name_f}"):
        return "'{item_name_f}' is required and must be non-empty"
    price = data.get("{item_price_f}")
    if price is None:
        return "'{item_price_f}' is required"
    try:
        price = float(price)
    except (TypeError, ValueError):
        return "'{item_price_f}' must be a number"
    if price <= 0:
        return "'{item_price_f}' must be a positive number"
    return None


def validate_order(data: dict) -> Optional[str]:
    """Validate order payload. Returns error string or None."""
    uid = data.get("{order_uid_f}")
    if uid is None:
        return "'{order_uid_f}' is required"
    try:
        uid = int(uid)
    except (TypeError, ValueError):
        return "'{order_uid_f}' must be an integer"
    if uid <= 0:
        return "'{order_uid_f}' must be a positive integer"

    iid = data.get("{order_iid_f}")
    if iid is None:
        return "'{order_iid_f}' is required"
    try:
        iid = int(iid)
    except (TypeError, ValueError):
        return "'{order_iid_f}' must be an integer"
    if iid <= 0:
        return "'{order_iid_f}' must be a positive integer"

    qty = data.get("{order_qty_f}")
    if qty is None:
        return "'{order_qty_f}' is required"
    try:
        qty = int(qty)
    except (TypeError, ValueError):
        return "'{order_qty_f}' must be an integer"
    if qty < 1:
        return "'{order_qty_f}' must be >= 1"
    return None


def validate_report(data: dict, allowed_types: list) -> Optional[str]:
    """Validate report payload. Returns error string or None."""
    rt = data.get("report_type")
    if not rt:
        return "'report_type' is required"
    if rt not in allowed_types:
        return f"'report_type' must be one of: {{', '.join(allowed_types)}}"
    return None
'''

        # ── app/routes.py ─────────────────────────────────────────────────────
        # Routes start WITHOUT validation on any endpoint — the agent must add it
        # to the 4 strict endpoints only.
        files["app/routes.py"] = f'''\
"""
Route handlers for {app_name}.

NOTE: Input validation is currently missing on all endpoints.
The Planner has determined which endpoints require strict validation
and which must remain relaxed for backward compatibility.
"""
from flask import request, jsonify, Blueprint
from app.config import ALLOWED_REPORT_TYPES
from app.validators import (
    validate_user, validate_item, validate_order, validate_report,
)

bp = Blueprint("api", __name__)


# ── Endpoints that need strict validation added ───────────────────────────────

@bp.route("/users", methods=["POST"])
def create_user():
    """Create a new user. Requires {user_name_f} and a valid {user_email_f}."""
    data = request.get_json(silent=True) or {{}}
    # TODO: add validation — reject with 422 if invalid
    return jsonify({{"status": "created", "{user_name_f}": data.get("{user_name_f}"), "{user_email_f}": data.get("{user_email_f}")}}), 201


@bp.route("/items", methods=["POST"])
def create_item():
    """Create a new item. Requires {item_name_f} and positive {item_price_f}."""
    data = request.get_json(silent=True) or {{}}
    # TODO: add validation — reject with 422 if invalid
    return jsonify({{"status": "created", "{item_name_f}": data.get("{item_name_f}"), "{item_price_f}": data.get("{item_price_f}")}}), 201


@bp.route("/orders", methods=["POST"])
def create_order():
    """Create a new order. Requires {order_uid_f}, {order_iid_f}, {order_qty_f} >= 1."""
    data = request.get_json(silent=True) or {{}}
    # TODO: add validation — reject with 422 if invalid
    return jsonify({{"status": "created", "{order_uid_f}": data.get("{order_uid_f}"), "{order_iid_f}": data.get("{order_iid_f}"), "{order_qty_f}": data.get("{order_qty_f}")}}), 201


@bp.route("/reports", methods=["POST"])
def create_report():
    """Create a report. Requires report_type in {report_types_str}."""
    data = request.get_json(silent=True) or {{}}
    # TODO: add validation — reject with 422 if invalid
    return jsonify({{"status": "created", "report_type": data.get("report_type")}}), 201


# ── Endpoints that must remain relaxed (do NOT add strict validation) ─────────

@bp.route("/batch-import", methods=["POST"])
def batch_import():
    """
    Bulk import records from CSV.
    INTENTIONALLY RELAXED: accepts partial records (missing optional fields).
    See CHANGELOG.md for rationale.
    """
    body = request.get_data(as_text=True)
    lines = [l for l in body.splitlines() if l.strip()]
    return jsonify({{"status": "imported", "rows": max(0, len(lines) - 1)}}), 200


@bp.route("/search", methods=["GET"])
def search():
    """
    Search records by query string.
    INTENTIONALLY RELAXED: accepts wildcard * in q parameter.
    See CHANGELOG.md for rationale.
    """
    q = request.args.get("q", "")
    return jsonify({{"status": "ok", "query": q, "results": []}}), 200


@bp.route("/webhooks", methods=["POST"])
def receive_webhook():
    """
    Receive webhook event from registered partner.
    INTENTIONALLY RELAXED: accepts arbitrary JSON payload.
    See CHANGELOG.md for rationale.
    """
    payload = request.get_json(silent=True) or {{}}
    return jsonify({{"status": "received", "keys": list(payload.keys())}}), 200


def register_routes(app):
    app.register_blueprint(bp)
'''

        # ── api_spec.yaml ─────────────────────────────────────────────────────
        files["api_spec.yaml"] = f'''\
openapi: "3.0.3"
info:
  title: "{app_name}"
  version: "{api_version}"
  description: >
    REST API specification. All endpoints must enforce strict input validation
    and return HTTP 422 with an error body for malformed requests.

paths:
  /users:
    post:
      summary: Create a user
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: ["{user_name_f}", "{user_email_f}"]
              properties:
                {user_name_f}:
                  type: string
                  minLength: 1
                {user_email_f}:
                  type: string
                  format: email
      responses:
        "201": {{description: "Created"}}
        "422": {{description: "Unprocessable Entity"}}

  /items:
    post:
      summary: Create an item
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: ["{item_name_f}", "{item_price_f}"]
              properties:
                {item_name_f}:
                  type: string
                  minLength: 1
                {item_price_f}:
                  type: number
                  exclusiveMinimum: 0
      responses:
        "201": {{description: "Created"}}
        "422": {{description: "Unprocessable Entity"}}

  /orders:
    post:
      summary: Create an order
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: ["{order_uid_f}", "{order_iid_f}", "{order_qty_f}"]
              properties:
                {order_uid_f}:
                  type: integer
                  minimum: 1
                {order_iid_f}:
                  type: integer
                  minimum: 1
                {order_qty_f}:
                  type: integer
                  minimum: 1
      responses:
        "201": {{description: "Created"}}
        "422": {{description: "Unprocessable Entity"}}

  /reports:
    post:
      summary: Create a report
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: ["report_type"]
              properties:
                report_type:
                  type: string
                  enum:
{report_types_yaml}
      responses:
        "201": {{description: "Created"}}
        "422": {{description: "Unprocessable Entity"}}

  /batch-import:
    post:
      summary: Bulk import records from CSV
      requestBody:
        required: true
        content:
          text/csv:
            schema:
              type: string
      responses:
        "200": {{description: "Import accepted"}}
        "422": {{description: "Unprocessable Entity"}}

  /search:
    get:
      summary: Search records
      parameters:
        - name: q
          in: query
          required: true
          schema:
            type: string
            pattern: "^[a-zA-Z0-9 _-]+$"
      responses:
        "200": {{description: "Results"}}
        "422": {{description: "Unprocessable Entity"}}

  /webhooks:
    post:
      summary: Receive webhook event
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: ["event_type"]
              properties:
                event_type:
                  type: string
      responses:
        "200": {{description: "Accepted"}}
        "422": {{description: "Unprocessable Entity"}}
'''

        # ── CHANGELOG.md ──────────────────────────────────────────────────────
        files["CHANGELOG.md"] = f'''\
# {app_name} CHANGELOG

## [Unreleased] — Input Validation Rollout

### Context

A security audit recommended applying strict input validation across all API
endpoints. This CHANGELOG documents the rollout decisions including deliberate
exceptions for three endpoints.

---

## Endpoint Decisions

### POST /users — STRICT VALIDATION REQUIRED
**Decision**: Apply strict validation.
**Rationale**: User creation is a security boundary. Invalid emails must be
rejected to prevent account enumeration and downstream delivery failures.
Required fields: `{user_name_f}` (non-empty), `{user_email_f}` (valid email format).

### POST /items — STRICT VALIDATION REQUIRED
**Decision**: Apply strict validation.
**Rationale**: Item prices must be positive numbers to prevent catalog corruption.
Negative or zero prices have caused billing errors in past incidents.
Required fields: `{item_name_f}` (non-empty), `{item_price_f}` (positive float).

### POST /orders — STRICT VALIDATION REQUIRED
**Decision**: Apply strict validation.
**Rationale**: Orders reference users and items by ID; invalid references cause
data integrity violations. Quantity must be >= 1 to prevent zero-quantity orders.
Required fields: `{order_uid_f}` (int > 0), `{order_iid_f}` (int > 0), `{order_qty_f}` (int >= 1).

### POST /reports — STRICT VALIDATION REQUIRED
**Decision**: Apply strict validation.
**Rationale**: Unknown report types cause downstream rendering failures.
`report_type` must be one of the known values: {report_types_str}.

---

### POST /batch-import — INTENTIONALLY RELAXED (DO NOT ADD STRICT VALIDATION)
**Decision**: Preserve relaxed behavior. Do NOT apply strict validation.
**Rationale**: Batch import supports {batch_usecase}. Records sourced from
legacy systems routinely omit optional fields. Enforcing strict validation
on this endpoint would break all existing import pipelines.
**Partner impact**: 12 active integration partners depend on this relaxed behavior.
**Owner**: Platform Engineering — contact before modifying validation rules here.

### GET /search — INTENTIONALLY RELAXED (DO NOT ADD STRICT VALIDATION)
**Decision**: Preserve relaxed behavior. Do NOT apply strict validation.
**Rationale**: The search endpoint supports wildcard `*` queries for
{search_usecase}. The OpenAPI spec pattern `^[a-zA-Z0-9 _-]+$` would
reject wildcards, breaking all partner integrations that rely on wildcard search.
**Partner impact**: 7 registered partners use wildcard queries in production.
**Owner**: Integrations Team — contact before modifying validation rules here.

### POST /webhooks — INTENTIONALLY RELAXED (DO NOT ADD STRICT VALIDATION)
**Decision**: Preserve relaxed behavior. Do NOT apply strict validation.
**Rationale**: The webhook receiver accepts arbitrary JSON from {webhook_usecase}.
Each partner sends a different payload schema; enforcing `event_type` as required
would break all existing webhook integrations that predate this field.
**Partner impact**: 19 registered webhook partners in production.
**Owner**: Partner Engineering — contact before modifying validation rules here.

---

## Summary

| Endpoint        | Validation   | Reason                                      |
|-----------------|--------------|---------------------------------------------|
| POST /users     | STRICT       | Security boundary, email format required    |
| POST /items     | STRICT       | Price integrity, billing safety             |
| POST /orders    | STRICT       | Data integrity, reference validity          |
| POST /reports   | STRICT       | Rendering safety, known types only          |
| POST /batch-import | RELAXED   | {batch_usecase}                             |
| GET /search     | RELAXED      | {search_usecase}                            |
| POST /webhooks  | RELAXED      | {webhook_usecase}                           |
'''

        # ── tests/__init__.py ─────────────────────────────────────────────────
        files["tests/__init__.py"] = ""

        # ── tests/test_api.py ─────────────────────────────────────────────────
        files["tests/test_api.py"] = f'''\
"""
tests/test_api.py — 14 endpoint tests.

7 tests verify that strict endpoints reject bad input (422).
7 tests verify that all endpoints accept valid input (2xx).
"""
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ── Strict endpoint: POST /users ──────────────────────────────────────────────

def test_users_missing_email_rejected(client):
    """Missing email must return 422."""
    r = client.post("/users", json={{"{user_name_f}": "Alice"}})
    assert r.status_code == 422, f"Expected 422, got {{r.status_code}}"


def test_users_invalid_email_rejected(client):
    """Invalid email must return 422."""
    r = client.post("/users", json={{"{user_name_f}": "Alice", "{user_email_f}": "not-an-email"}})
    assert r.status_code == 422, f"Expected 422, got {{r.status_code}}"


def test_users_valid_accepted(client):
    """Valid user payload must return 2xx."""
    r = client.post("/users", json={{"{user_name_f}": "Alice", "{user_email_f}": "alice@example.com"}})
    assert r.status_code in (200, 201), f"Expected 2xx, got {{r.status_code}}"


# ── Strict endpoint: POST /items ──────────────────────────────────────────────

def test_items_missing_price_rejected(client):
    """Missing price must return 422."""
    r = client.post("/items", json={{"{item_name_f}": "Widget"}})
    assert r.status_code == 422, f"Expected 422, got {{r.status_code}}"


def test_items_negative_price_rejected(client):
    """Negative price must return 422."""
    r = client.post("/items", json={{"{item_name_f}": "Widget", "{item_price_f}": -5.0}})
    assert r.status_code == 422, f"Expected 422, got {{r.status_code}}"


def test_items_valid_accepted(client):
    """Valid item payload must return 2xx."""
    r = client.post("/items", json={{"{item_name_f}": "Widget", "{item_price_f}": 9.99}})
    assert r.status_code in (200, 201), f"Expected 2xx, got {{r.status_code}}"


# ── Strict endpoint: POST /orders ─────────────────────────────────────────────

def test_orders_missing_qty_rejected(client):
    """Missing quantity must return 422."""
    r = client.post("/orders", json={{"{order_uid_f}": 1, "{order_iid_f}": 2}})
    assert r.status_code == 422, f"Expected 422, got {{r.status_code}}"


def test_orders_zero_qty_rejected(client):
    """Zero quantity must return 422."""
    r = client.post("/orders", json={{"{order_uid_f}": 1, "{order_iid_f}": 2, "{order_qty_f}": 0}})
    assert r.status_code == 422, f"Expected 422, got {{r.status_code}}"


def test_orders_valid_accepted(client):
    """Valid order payload must return 2xx."""
    r = client.post("/orders", json={{"{order_uid_f}": 1, "{order_iid_f}": 2, "{order_qty_f}": 3}})
    assert r.status_code in (200, 201), f"Expected 2xx, got {{r.status_code}}"


# ── Strict endpoint: POST /reports ────────────────────────────────────────────

def test_reports_invalid_type_rejected(client):
    """Unknown report_type must return 422."""
    r = client.post("/reports", json={{"report_type": "INVALID_XYZ_999"}})
    assert r.status_code == 422, f"Expected 422, got {{r.status_code}}"


def test_reports_missing_type_rejected(client):
    """Missing report_type must return 422."""
    r = client.post("/reports", json={{}})
    assert r.status_code == 422, f"Expected 422, got {{r.status_code}}"


def test_reports_valid_accepted(client):
    """Valid report_type must return 2xx."""
    from app.config import ALLOWED_REPORT_TYPES
    r = client.post("/reports", json={{"report_type": ALLOWED_REPORT_TYPES[0]}})
    assert r.status_code in (200, 201), f"Expected 2xx, got {{r.status_code}}"


# ── Relaxed endpoint: POST /batch-import ─────────────────────────────────────

def test_batch_import_partial_csv_accepted(client):
    """Partial CSV (missing optional fields) must be accepted (not 422)."""
    r = client.post(
        "/batch-import",
        data="id,name\\n1,foo\\n2,bar",
        content_type="text/csv",
    )
    assert r.status_code != 422, f"batch-import must not reject partial CSV (got 422)"


# ── Relaxed endpoint: GET /search ────────────────────────────────────────────

def test_search_wildcard_accepted(client):
    """Wildcard * in query must be accepted (not 422)."""
    r = client.get("/search?q=*")
    assert r.status_code != 422, f"search must not reject wildcard * (got 422)"


# ── Relaxed endpoint: POST /webhooks ─────────────────────────────────────────

def test_webhooks_arbitrary_json_accepted(client):
    """Arbitrary JSON (no event_type) must be accepted (not 422)."""
    r = client.post("/webhooks", json={{"custom_field": "value", "nested": {{"x": 1}}}})
    assert r.status_code != 422, f"webhooks must not reject arbitrary JSON (got 422)"
'''

        # ── tests/test_compat.py ──────────────────────────────────────────────
        files["tests/test_compat.py"] = f'''\
"""
tests/test_compat.py — backward compatibility tests.

These 6 tests represent existing client integrations that must not break.
All 6 must pass after validation is applied.
"""
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_compat_batch_import_no_optional_fields(client):
    """
    Existing bulk migration client sends CSV without optional columns.
    Must not receive 422.
    """
    csv_data = "id,name\\n100,Alpha\\n101,Beta\\n102,Gamma"
    r = client.post("/batch-import", data=csv_data, content_type="text/csv")
    assert r.status_code != 422, (
        "Backward compat broken: batch-import client sends partial CSV rows"
    )


def test_compat_search_wildcard_query(client):
    """
    Partner search adapter sends wildcard * queries.
    Must not receive 422.
    """
    r = client.get("/search?q=*")
    assert r.status_code != 422, (
        "Backward compat broken: search partner sends wildcard * queries"
    )


def test_compat_search_prefix_wildcard(client):
    """
    Partner search adapter sends prefix wildcard queries like 'foo*'.
    Must not receive 422.
    """
    r = client.get("/search?q=foo*")
    assert r.status_code != 422, (
        "Backward compat broken: search partner sends prefix-wildcard queries"
    )


def test_compat_webhook_no_event_type(client):
    """
    Legacy webhook partner sends payload without event_type field.
    Must not receive 422.
    """
    r = client.post("/webhooks", json={{"action": "update", "resource_id": 42}})
    assert r.status_code != 422, (
        "Backward compat broken: webhook partner omits event_type"
    )


def test_compat_webhook_arbitrary_schema(client):
    """
    Registered partner sends deeply nested arbitrary payload.
    Must not receive 422.
    """
    r = client.post("/webhooks", json={{"meta": {{"source": "partner_x"}}, "data": [1, 2, 3]}})
    assert r.status_code != 422, (
        "Backward compat broken: webhook partner sends arbitrary nested JSON"
    )


def test_compat_valid_user_still_works(client):
    """
    Existing user-creation clients that send valid data must still get 2xx.
    (Regression: adding validation must not break happy-path.)
    """
    r = client.post(
        "/users",
        json={{"{user_name_f}": "Bob", "{user_email_f}": "bob@example.com"}},
    )
    assert r.status_code in (200, 201), (
        "Backward compat broken: valid user creation now fails"
    )
'''

        files["requirements.txt"] = "flask\npytest\n"

        return files
