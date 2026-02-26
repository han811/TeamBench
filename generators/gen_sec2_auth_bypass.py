"""
Parameterized generator for SEC2: Authentication Bypass.

Each seed produces:
- Different endpoint names (users/accounts/members/staff/clients)
- Different role names (admin/superuser/root/manager/owner)
- Different JWT secret key env var names
- Different admin endpoint paths
- Different password reset token storage approach label
- Same 3 auth vulnerabilities but in varied surface area

TNI Design:
  - brief.md: vague — "fix the auth issues, Planner has threat model"
  - spec.md: full threat model with 3 specific CVE-style findings
  - workspace: looks plausible; vulns NOT obvious from code review alone
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# ── Variation pools ───────────────────────────────────────────────────────────

ENDPOINT_GROUPS = [
    {
        "resource": "users",
        "admin_path": "/api/users/admin",
        "admin_func": "admin_users",
        "list_path": "/api/users",
        "detail_path": "/api/users/<int:user_id>",
        "list_func": "list_users",
        "detail_func": "get_user",
    },
    {
        "resource": "accounts",
        "admin_path": "/api/accounts/admin",
        "admin_func": "admin_accounts",
        "list_path": "/api/accounts",
        "detail_path": "/api/accounts/<int:account_id>",
        "list_func": "list_accounts",
        "detail_func": "get_account",
    },
    {
        "resource": "members",
        "admin_path": "/api/members/admin",
        "admin_func": "admin_members",
        "list_path": "/api/members",
        "detail_path": "/api/members/<int:member_id>",
        "list_func": "list_members",
        "detail_func": "get_member",
    },
    {
        "resource": "staff",
        "admin_path": "/api/staff/admin",
        "admin_func": "admin_staff",
        "list_path": "/api/staff",
        "detail_path": "/api/staff/<int:staff_id>",
        "list_func": "list_staff",
        "detail_func": "get_staff",
    },
    {
        "resource": "clients",
        "admin_path": "/api/clients/admin",
        "admin_func": "admin_clients",
        "list_path": "/api/clients",
        "detail_path": "/api/clients/<int:client_id>",
        "list_func": "list_clients",
        "detail_func": "get_client",
    },
]

ROLE_VARIANTS = [
    {"role": "admin",     "role_field": "role",       "role_check": "user_data['role'] == 'admin'"},
    {"role": "superuser", "role_field": "role",       "role_check": "user_data['role'] == 'superuser'"},
    {"role": "root",      "role_field": "access_level", "role_check": "user_data['access_level'] == 'root'"},
    {"role": "manager",   "role_field": "role",       "role_check": "user_data['role'] == 'manager'"},
    {"role": "owner",     "role_field": "tier",       "role_check": "user_data['tier'] == 'owner'"},
]

JWT_SECRET_NAMES = [
    "JWT_SECRET_KEY",
    "JWT_SIGNING_SECRET",
    "TOKEN_SECRET",
    "AUTH_SECRET_KEY",
    "APP_JWT_SECRET",
]

RESET_STORE_VARIANTS = [
    {
        "label": "in-memory dict",
        "store_name": "reset_tokens",
        "store_init": "reset_tokens = {}  # Maps token -> user_id",
        "store_set": "    reset_tokens[token] = user_id",
        "store_get": "    user_id = reset_tokens.get(token)",
        "store_del": "    del reset_tokens[token]",
        "store_check": "    if token not in reset_tokens:",
    },
    {
        "label": "SQLite db",
        "store_name": "reset_tokens",
        "store_init": "reset_tokens = {}  # Backed by SQLite at runtime; dict used for tests",
        "store_set": "    reset_tokens[token] = user_id",
        "store_get": "    user_id = reset_tokens.get(token)",
        "store_del": "    del reset_tokens[token]",
        "store_check": "    if token not in reset_tokens:",
    },
    {
        "label": "Redis cache",
        "store_name": "token_cache",
        "store_init": "token_cache = {}  # Redis-backed in prod; dict for local dev",
        "store_set": "    token_cache[token] = user_id",
        "store_get": "    user_id = token_cache.get(token)",
        "store_del": "    del token_cache[token]",
        "store_check": "    if token not in token_cache:",
    },
]


class Generator(TaskGenerator):
    task_id = "SEC2_auth_bypass"
    domain = "security"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        ep = ENDPOINT_GROUPS[rng.randint(0, len(ENDPOINT_GROUPS) - 1)]
        rv = ROLE_VARIANTS[rng.randint(0, len(ROLE_VARIANTS) - 1)]
        jwt_secret_name = JWT_SECRET_NAMES[rng.randint(0, len(JWT_SECRET_NAMES) - 1)]
        rs = RESET_STORE_VARIANTS[rng.randint(0, len(RESET_STORE_VARIANTS) - 1)]

        expected = {
            "resource": ep["resource"],
            "role": rv["role"],
            "jwt_secret_env": jwt_secret_name,
            "reset_store": rs["label"],
            "vulnerabilities": [
                "jwt_expiry_not_validated",
                "admin_missing_role_check",
                "reset_token_not_invalidated",
            ],
            "fixes": {
                "jwt_expiry": "jwt.decode must use options={'verify_exp': True} or not pass verify_exp=False",
                "role_check": f"admin endpoint must verify {rv['role_field']}=={rv['role']} before responding",
                "token_invalidation": "reset token must be deleted from store after single use",
            },
        }

        workspace_files = {
            "auth.py":         self._gen_auth(jwt_secret_name),
            "routes.py":       self._gen_routes(ep, rv, rs, jwt_secret_name),
            "models.py":       self._gen_models(ep, rv, rs),
            "requirements.txt": self._gen_requirements(),
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._gen_spec(ep, rv, rs, jwt_secret_name),
            brief_md=self._gen_brief(ep),
            expected=expected,
            workspace_files=workspace_files,
        )

    # ── workspace file generators ─────────────────────────────────────────────

    def _gen_auth(self, jwt_secret_name: str) -> str:
        return f'''\
"""JWT authentication helpers."""
import os
import jwt
import datetime

# Load secret from environment
{jwt_secret_name} = os.environ.get("{jwt_secret_name}", "changeme-dev-secret")


def create_token(user_id: int, role: str) -> str:
    """Issue a signed JWT with a 1-hour expiry."""
    payload = {{
        "sub": user_id,
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        "iat": datetime.datetime.utcnow(),
    }}
    return jwt.encode(payload, {jwt_secret_name}, algorithm="HS256")


def decode_token(token: str) -> dict:
    """Decode and validate a JWT.

    NOTE: Returns the payload for downstream use.
    """
    # Decode the token — options dict controls what to verify
    payload = jwt.decode(
        token,
        {jwt_secret_name},
        algorithms=["HS256"],
        options={{"verify_exp": False}},  # expiry checked separately if needed
    )
    return payload


def require_auth(f):
    """Decorator: ensure request carries a valid JWT."""
    from functools import wraps
    from flask import request, jsonify

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({{"error": "Missing token"}}), 401
        token = auth_header[7:]
        try:
            user_data = decode_token(token)
        except jwt.InvalidTokenError as exc:
            return jsonify({{"error": str(exc)}}), 401
        return f(user_data, *args, **kwargs)

    return decorated
'''

    def _gen_routes(self, ep: dict, rv: dict, rs: dict, jwt_secret_name: str) -> str:
        resource = ep["resource"]
        admin_path = ep["admin_path"]
        admin_func = ep["admin_func"]
        list_path = ep["list_path"]
        detail_path = ep["detail_path"]
        list_func = ep["list_func"]
        detail_func = ep["detail_func"]
        # extract path param name e.g. user_id from "<int:user_id>"
        import re as _re
        m = _re.search(r"<int:(\w+)>", detail_path)
        id_param = m.group(1) if m else "item_id"

        store_name = rs["store_name"]
        store_check = rs["store_check"]
        store_get = rs["store_get"]
        # build invalidation line WITHOUT the del (vulnerable)
        store_del_commented = f"    # TODO: clean up used tokens"

        role_field = rv["role_field"]
        role = rv["role"]

        return f'''\
"""API routes for {resource} management."""
import secrets
from flask import Blueprint, jsonify, request
from auth import require_auth
from models import get_{resource}, {rs["store_name"]}, invalidate_reset_token

bp = Blueprint("api", __name__)


@bp.route("{list_path}", methods=["GET"])
@require_auth
def {list_func}(user_data):
    """Return all {resource}. Any authenticated user may list."""
    items = get_{resource}()
    return jsonify({{"data": items, "count": len(items)}})


@bp.route("{detail_path}", methods=["GET"])
@require_auth
def {detail_func}(user_data, {id_param}):
    """Return a single {resource[:-1] if resource.endswith("s") else resource} by id."""
    items = get_{resource}()
    item = next((i for i in items if i["id"] == {id_param}), None)
    if item is None:
        return jsonify({{"error": "not found"}}), 404
    return jsonify(item)


@bp.route("{admin_path}", methods=["GET"])
@require_auth
def {admin_func}(user_data):
    """Admin-only view: returns sensitive operational data."""
    # Access control: caller must be authenticated (decorator handles that).
    # Privileged data follows.
    return jsonify({{
        "status": "ok",
        "admin_data": {{
            "total_{resource}": 42,
            "flagged": 3,
            "system_health": "green",
        }},
    }})


@bp.route("/api/auth/reset-request", methods=["POST"])
def request_password_reset():
    """Send a password-reset token to the user."""
    body = request.get_json(force=True) or {{}}
    user_id = body.get("user_id")
    if not user_id:
        return jsonify({{"error": "user_id required"}}), 400
    token = secrets.token_urlsafe(32)
    {rs["store_name"]}[token] = user_id  # store for later validation
    # In prod, email the token to the user
    return jsonify({{"message": "Reset token issued", "token": token}})


@bp.route("/api/auth/reset-confirm", methods=["POST"])
def confirm_password_reset():
    """Consume a reset token and update the password."""
    body = request.get_json(force=True) or {{}}
    token = body.get("token")
    new_password = body.get("new_password")
    if not token or not new_password:
        return jsonify({{"error": "token and new_password required"}}), 400
{store_check}
        return jsonify({{"error": "Invalid or expired token"}}), 400
{store_get}
    if user_id is None:
        return jsonify({{"error": "Invalid token"}}), 400
    # Password updated — but token kept in store (will be cleaned up on next cycle)
    {store_del_commented}
    return jsonify({{"message": "Password updated successfully", "user_id": user_id}})
'''

    def _gen_models(self, ep: dict, rv: dict, rs: dict) -> str:
        resource = ep["resource"]
        role_field = rv["role_field"]
        role = rv["role"]
        store_init = rs["store_init"]
        store_name = rs["store_name"]

        return f'''\
"""Data models and in-process stores."""
from typing import Optional

# ── Password-reset token store ───────────────────────────────────────────────
{store_init}


def invalidate_reset_token(token: str) -> None:
    """Remove a used reset token so it cannot be replayed."""
    {store_name}.pop(token, None)


# ── Fake user store (replace with DB in prod) ────────────────────────────────
_USERS = [
    {{"id": 1, "name": "Alice", "{role_field}": "{role}", "email": "alice@example.com"}},
    {{"id": 2, "name": "Bob",   "{role_field}": "user",   "email": "bob@example.com"}},
    {{"id": 3, "name": "Carol", "{role_field}": "user",   "email": "carol@example.com"}},
]


def get_{resource}() -> list:
    """Return all {resource} records (non-sensitive fields only)."""
    return [{{"id": u["id"], "name": u["name"], "{role_field}": u["{role_field}"]}} for u in _USERS]
'''

    def _gen_requirements(self) -> str:
        return """\
Flask>=2.3.0
PyJWT>=2.8.0
"""

    # ── doc generators ────────────────────────────────────────────────────────

    def _gen_spec(self, ep: dict, rv: dict, rs: dict, jwt_secret_name: str) -> str:
        resource = ep["resource"]
        admin_path = ep["admin_path"]
        role = rv["role"]
        role_field = rv["role_field"]
        role_check = rv["role_check"]

        return f"""\
# SEC2: Authentication Bypass — Threat Model (Planner/Verifier Only)

## Overview

A security review of the `{resource}` REST API identified three authentication bypass
vulnerabilities. Each finding below includes the attack vector and the required fix.

---

## Finding 1: JWT Expiry Not Validated (HIGH)

**Location**: `auth.py` → `decode_token()`

**Attack Vector**:
An attacker who captured a JWT issued in the past (e.g., from a leaked log or
intercepted session) can re-use it indefinitely because `decode_token()` passes
`options={{"verify_exp": False}}` to `jwt.decode()`. PyJWT therefore skips the
expiry check entirely, and the token remains valid forever.

**Reproduction**:
1. Obtain any previously-issued JWT (expired or not).
2. Send it as `Authorization: Bearer <token>` to any `@require_auth` endpoint.
3. Observe that the request succeeds even after token expiry.

**Required Fix**:
Remove the `options={{"verify_exp": False}}` override (or change it to
`{{"verify_exp": True}}`). PyJWT validates `exp` by default when no override is
supplied — the default behaviour is correct and must be restored.

---

## Finding 2: Admin Endpoint Missing Role Check (CRITICAL)

**Location**: `routes.py` → `{ep["admin_func"]}()` (`{admin_path}`)

**Attack Vector**:
The `{admin_path}` endpoint is decorated with `@require_auth`, which only
verifies that the caller holds *any* valid JWT. It does not verify that the
caller's token carries the `{role_field}={role!r}` claim. Any authenticated
user (including ordinary `user`-role accounts) can access all admin data.

**Reproduction**:
1. Authenticate as an ordinary user and obtain a JWT with `{role_field}="user"`.
2. `GET {admin_path}` with that token.
3. Observe that full admin data is returned with HTTP 200.

**Required Fix**:
Inside `{ep["admin_func"]}()`, check that `{role_check}` before returning
admin data. Return HTTP 403 if the check fails.

---

## Finding 3: Password-Reset Token Not Invalidated After Use (HIGH)

**Location**: `routes.py` → `confirm_password_reset()`

**Attack Vector**:
After a user successfully resets their password via `/api/auth/reset-confirm`,
the one-time token is left in the `{rs["store_name"]}` store because the
deletion call is replaced by a comment (`# TODO: clean up used tokens`).
An attacker who intercepts the reset token (e.g., via shoulder-surfing, phishing,
or a shared device) can re-use it to set a new password even after the legitimate
user has already consumed it.

**Reproduction**:
1. POST `/api/auth/reset-request` to obtain a reset token.
2. POST `/api/auth/reset-confirm` with that token and a new password → succeeds.
3. POST `/api/auth/reset-confirm` again with the same token → should fail but
   currently succeeds again (token still in store).

**Required Fix**:
After a successful password update, remove the token from `{rs["store_name"]}`
(e.g., call `invalidate_reset_token(token)` or `del {rs["store_name"]}[token]`).

---

## Fix Requirements Summary

| # | Vulnerability                  | File        | Required Change                                      |
|---|-------------------------------|-------------|------------------------------------------------------|
| 1 | JWT expiry bypass              | `auth.py`   | Remove / correct `verify_exp: False`                 |
| 2 | Admin endpoint no role check   | `routes.py` | Add `{role_field}=={role!r}` guard before admin data |
| 3 | Reset token reuse              | `routes.py` | Delete token from store after successful reset       |

## Deliverables

The Executor must patch the three vulnerabilities. The Verifier must confirm:
- `jwt.decode` no longer bypasses expiry validation
- `{admin_path}` returns 403 for non-`{role}` tokens
- A consumed reset token cannot be used a second time
"""

    def _gen_brief(self, ep: dict) -> str:
        resource = ep["resource"]
        return f"""\
# SEC2: Authentication Bypass (Executor Brief)

The `{resource}` API has been flagged in a security review.
Fix the authentication issues. The Planner has the full threat model.

**Your workspace contains**:
- `auth.py` — JWT helpers and `@require_auth` decorator
- `routes.py` — API endpoints for `{resource}`
- `models.py` — data models and token store
- `requirements.txt` — Python dependencies

Do not change the public API surface (URL paths, request/response shapes).
"""
