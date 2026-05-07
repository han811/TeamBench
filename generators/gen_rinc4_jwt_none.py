"""
Parameterized generator for RINC4: JWT Algorithm Confusion Attacks.

Inspiration: CVE-2015-9235 — JWT libraries that accept alg=none allow
attackers to forge tokens without a secret. Also covers weak HMAC key
and kid (key injection) variants.

Seeds vary: JWT vulnerability type (none algo / weak key / kid injection),
service name, token claims structure.

Grading: 7 checks — none algorithm rejected, forged token blocked,
valid tokens still accepted, algorithm validation in place.
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

VARIANTS = [
    {
        "attack": "none_algorithm",
        "service": "AuthService",
        "vuln_desc": "accepts tokens with alg=none (no signature required)",
        "fix_desc": "explicitly reject alg=none and enforce alg=HS256 or RS256",
        "endpoint_login": "/login",
        "endpoint_protected": "/profile",
        "claim_user": "user_id",
        "claim_role": "role",
    },
    {
        "attack": "weak_secret",
        "service": "APIGateway",
        "vuln_desc": "uses a short, guessable HMAC secret ('secret', 'key', etc.)",
        "fix_desc": "replace weak secret with a 256-bit random secret loaded from environment",
        "endpoint_login": "/auth/token",
        "endpoint_protected": "/api/data",
        "claim_user": "sub",
        "claim_role": "scope",
    },
    {
        "attack": "kid_injection",
        "service": "TokenValidator",
        "vuln_desc": "uses kid header to look up key without sanitization — path traversal or SQL injection in kid",
        "fix_desc": "validate kid against a strict allowlist of known key IDs",
        "endpoint_login": "/token",
        "endpoint_protected": "/secure/data",
        "claim_user": "uid",
        "claim_role": "perms",
    },
]


class Generator(TaskGenerator):
    task_id = "RINC4_jwt_none"
    domain = "security"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        v = VARIANTS[seed % len(VARIANTS)]
        port = rng.randint(5300, 5399)
        weak_secret = rng.choice(["secret", "key", "password", "jwt_secret"])

        workspace_files = {
            "app.py": self._gen_app(v, port, weak_secret),
            "test_jwt.py": self._gen_tests(v),
            "requirements.txt": "flask>=2.3\npyjwt>=2.8\npytest>=7.0\n",
        }

        expected = {
            "seed": seed,
            "attack": v["attack"],
            "service": v["service"],
            "fix": v["fix_desc"],
            "endpoint_protected": v["endpoint_protected"],
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._gen_spec(v, weak_secret),
            brief_md=self._gen_brief(v),
            expected=expected,
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "security", "cve": "CVE-2015-9235"},
        )

    def _gen_app(self, v: dict, port: int, weak_secret: str) -> str:
        if v["attack"] == "none_algorithm":
            return self._gen_none_app(v, port)
        elif v["attack"] == "weak_secret":
            return self._gen_weak_secret_app(v, port, weak_secret)
        else:
            return self._gen_kid_app(v, port)

    def _gen_none_app(self, v: dict, port: int) -> str:
        return f'''\
"""
{v["service"]}: JWT authentication service.

WARNING: This code contains a JWT algorithm confusion vulnerability.
Inspiration: CVE-2015-9235 — alg=none bypass.
"""
import jwt
import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)
SECRET_KEY = "super-secret-key-change-in-production"


def create_token(user_id: str, role: str) -> str:
    payload = {{
        "{v["claim_user"]}": user_id,
        "{v["claim_role"]}": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        "iat": datetime.datetime.utcnow(),
    }}
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token.

    VULNERABLE: does not specify algorithms= parameter.
    PyJWT < 2.x would accept alg=none. Even in newer versions,
    omitting algorithms= is a security misconfiguration.
    """
    try:
        # VULNERABILITY: no algorithms= restriction — accepts whatever alg the token claims
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256", "none"])
        return payload
    except jwt.ExpiredSignatureError:
        raise ValueError("Token expired")
    except jwt.InvalidTokenError as e:
        raise ValueError(f"Invalid token: {{e}}")


@app.route("{v["endpoint_login"]}", methods=["POST"])
def login():
    data = request.get_json() or {{}}
    username = data.get("username", "")
    password = data.get("password", "")
    # Simplified auth — in real app would check DB
    if username == "admin" and password == "correct_password":
        token = create_token(username, "admin")
        return jsonify({{"token": token}})
    elif username and password:
        token = create_token(username, "user")
        return jsonify({{"token": token}})
    return jsonify({{"error": "invalid credentials"}}), 401


@app.route("{v["endpoint_protected"]}")
def protected():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({{"error": "missing token"}}), 401
    token = auth[7:]
    try:
        payload = decode_token(token)
        return jsonify({{"user": payload.get("{v["claim_user"]}"), "role": payload.get("{v["claim_role"]}"), "data": "sensitive_data"}})
    except ValueError as e:
        return jsonify({{"error": str(e)}}), 401


@app.route("/health")
def health():
    return jsonify({{"status": "ok", "service": "{v["service"]}"}})


if __name__ == "__main__":
    app.run(port={port}, debug=False)
'''

    def _gen_weak_secret_app(self, v: dict, port: int, weak_secret: str) -> str:
        return f'''\
"""
{v["service"]}: API gateway with JWT authentication.

WARNING: Uses a weak HMAC secret that can be brute-forced offline.
Inspiration: JWT weak secret attacks — common in misconfigured services.
"""
import jwt
import datetime
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# VULNERABILITY: hardcoded weak secret — trivially brute-forced offline
# Attacker obtains any valid token, cracks the secret, forges admin tokens
JWT_SECRET = os.environ.get("JWT_SECRET", "{weak_secret}")


def create_token(sub: str, scope: str) -> str:
    payload = {{
        "{v["claim_user"]}": sub,
        "{v["claim_role"]}": scope,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    }}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])


@app.route("{v["endpoint_login"]}", methods=["POST"])
def get_token():
    data = request.get_json() or {{}}
    user = data.get("username", "guest")
    token = create_token(user, "read")
    return jsonify({{"token": token, "type": "Bearer"}})


@app.route("{v["endpoint_protected"]}")
def protected_data():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({{"error": "missing token"}}), 401
    try:
        payload = verify_token(auth[7:])
        return jsonify({{"data": "sensitive", "user": payload.get("{v["claim_user"]}")}})
    except jwt.InvalidTokenError as e:
        return jsonify({{"error": str(e)}}), 401


@app.route("/health")
def health():
    return jsonify({{"status": "ok"}})


if __name__ == "__main__":
    app.run(port={port}, debug=False)
'''

    def _gen_kid_app(self, v: dict, port: int) -> str:
        return f'''\
"""
{v["service"]}: Token validator with kid (Key ID) header support.

WARNING: kid header used without sanitization — path traversal possible.
Inspiration: JWT kid header injection attacks.
"""
import jwt
import datetime
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# Key store — kid maps to secret
KEY_STORE = {{
    "key-2024-01": "production-secret-key-alpha",
    "key-2024-02": "production-secret-key-beta",
}}


def get_key_for_kid(kid: str) -> str:
    """Look up signing key by kid header.

    VULNERABLE: no validation of kid format — allows path traversal
    or injection to use an attacker-controlled key.
    """
    # VULNERABILITY: no allowlist check — kid could be '../../../etc/passwd'
    # or SQL injection if keys were stored in a DB
    key = KEY_STORE.get(kid)
    if key is None:
        # Fallback: try to read from keys/ directory (path traversal risk)
        key_path = os.path.join("keys", kid)
        if os.path.exists(key_path):
            with open(key_path) as f:
                key = f.read().strip()
        else:
            raise ValueError(f"Unknown kid: {{kid}}")
    return key


def verify_token(token: str) -> dict:
    header = jwt.get_unverified_header(token)
    kid = header.get("kid", "key-2024-01")
    secret = get_key_for_kid(kid)
    return jwt.decode(token, secret, algorithms=["HS256"])


@app.route("{v["endpoint_login"]}", methods=["POST"])
def issue_token():
    data = request.get_json() or {{}}
    user = data.get("user", "anonymous")
    payload = {{
        "{v["claim_user"]}": user,
        "{v["claim_role"]}": "read",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    }}
    token = jwt.encode(payload, KEY_STORE["key-2024-01"], algorithm="HS256",
                       headers={{"kid": "key-2024-01"}})
    return jsonify({{"token": token}})


@app.route("{v["endpoint_protected"]}")
def secure_data():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({{"error": "missing token"}}), 401
    try:
        payload = verify_token(auth[7:])
        return jsonify({{"secure": True, "user": payload.get("{v["claim_user"]}")}})
    except (jwt.InvalidTokenError, ValueError) as e:
        return jsonify({{"error": str(e)}}), 401


@app.route("/health")
def health():
    return jsonify({{"status": "ok"}})


if __name__ == "__main__":
    app.run(port={port}, debug=False)
'''

    def _gen_tests(self, v: dict) -> str:
        if v["attack"] == "none_algorithm":
            return self._gen_none_tests(v)
        elif v["attack"] == "weak_secret":
            return self._gen_weak_secret_tests(v)
        else:
            return self._gen_kid_tests(v)

    def _gen_none_tests(self, v: dict) -> str:
        return f'''\
"""JWT none-algorithm bypass tests."""
import base64
import json
import pytest
import app as app_module


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def _forge_none_token(payload: dict) -> str:
    """Forge a JWT with alg=none (no signature)."""
    header = base64.urlsafe_b64encode(json.dumps({{"alg": "none", "typ": "JWT"}}).encode()).rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"{{header}}.{{body}}."  # empty signature


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_none_alg_token_rejected(client):
    """Forged alg=none token must be rejected."""
    import datetime, time
    payload = {{
        "{v["claim_user"]}": "attacker",
        "{v["claim_role"]}": "admin",
        "exp": int(time.time()) + 3600,
    }}
    forged = _forge_none_token(payload)
    resp = client.get(
        "{v["endpoint_protected"]}",
        headers={{"Authorization": f"Bearer {{forged}}"}},
    )
    assert resp.status_code == 401, (
        f"alg=none token accepted — status={{resp.status_code}}"
    )


def test_valid_token_accepted(client):
    """Legitimately issued token must still work."""
    login_resp = client.post(
        "{v["endpoint_login"]}",
        json={{"username": "testuser", "password": "any"}},
        content_type="application/json",
    )
    assert login_resp.status_code == 200
    token = login_resp.get_json()["token"]

    resp = client.get(
        "{v["endpoint_protected"]}",
        headers={{"Authorization": f"Bearer {{token}}"}},
    )
    assert resp.status_code == 200


def test_tampered_token_rejected(client):
    """Token with modified payload (no re-signing) must be rejected."""
    login_resp = client.post(
        "{v["endpoint_login"]}",
        json={{"username": "user", "password": "any"}},
        content_type="application/json",
    )
    token = login_resp.get_json()["token"]
    parts = token.split(".")
    # Tamper with payload
    import base64, json as _json
    payload = _json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
    payload["{v["claim_role"]}"] = "admin"
    parts[1] = base64.urlsafe_b64encode(_json.dumps(payload).encode()).rstrip(b"=").decode()
    tampered = ".".join(parts)
    resp = client.get(
        "{v["endpoint_protected"]}",
        headers={{"Authorization": f"Bearer {{tampered}}"}},
    )
    assert resp.status_code == 401


def test_algorithms_none_not_in_decode_call():
    """Static check: decode_token() must not include 'none' in algorithms."""
    src = open("app.py").read()
    assert '"none"' not in src and "'none'" not in src, (
        "app.py still has 'none' in algorithms list"
    )
'''

    def _gen_weak_secret_tests(self, v: dict) -> str:
        return f'''\
"""JWT weak secret tests."""
import pytest
import app as app_module


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_secret_not_weak(client):
    """JWT_SECRET must not be a well-known weak value."""
    weak_secrets = ["secret", "key", "password", "jwt_secret", "changeme", "test", "1234"]
    secret = app_module.JWT_SECRET
    assert secret not in weak_secrets, (
        f"JWT_SECRET is still a weak value: '{{secret}}'"
    )
    assert len(secret) >= 32, (
        f"JWT_SECRET is too short: {{len(secret)}} chars (need >= 32)"
    )


def test_valid_token_flow(client):
    """Full login + protected endpoint flow must work."""
    resp = client.post("{v["endpoint_login"]}", json={{"username": "testuser"}})
    assert resp.status_code == 200
    token = resp.get_json()["token"]

    resp2 = client.get(
        "{v["endpoint_protected"]}",
        headers={{"Authorization": f"Bearer {{token}}"}},
    )
    assert resp2.status_code == 200


def test_forged_token_rejected(client):
    """Token signed with known weak secret must be rejected."""
    import jwt, datetime
    forged = jwt.encode(
        {{"{v["claim_user"]}": "hacker", "{v["claim_role"]}": "admin",
          "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)}},
        "secret",  # known weak secret
        algorithm="HS256",
    )
    resp = client.get(
        "{v["endpoint_protected"]}",
        headers={{"Authorization": f"Bearer {{forged}}"}},
    )
    assert resp.status_code == 401, (
        "Token signed with known weak secret 'secret' was accepted"
    )


def test_no_hardcoded_weak_secret():
    """Static check: app.py must not default to a weak secret."""
    import re
    src = open("app.py").read()
    weak = ["secret", "key", "password", "changeme", "jwt_secret"]
    for weak_val in weak:
        pattern = rf'get\("JWT_SECRET",\s*"' + weak_val + r'"\)'
        if re.search(pattern, src):
            assert False, f"Hardcoded weak default secret '{{weak_val}}' found in app.py"
'''

    def _gen_kid_tests(self, v: dict) -> str:
        return f'''\
"""JWT kid injection tests."""
import pytest
import os
import app as app_module


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_valid_token_works(client):
    resp = client.post("{v["endpoint_login"]}", json={{"user": "alice"}})
    assert resp.status_code == 200
    token = resp.get_json()["token"]
    resp2 = client.get("{v["endpoint_protected"]}",
                       headers={{"Authorization": f"Bearer {{token}}"}})
    assert resp2.status_code == 200


def test_path_traversal_kid_rejected(client):
    """kid with path traversal must be rejected."""
    import jwt, datetime
    # Craft a token with kid='../app.py'
    payload = {{"{v["claim_user"]}": "attacker", "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)}}
    # Sign with a known key that the file would contain
    token = jwt.encode(payload, "dummy", algorithm="HS256",
                       headers={{"kid": "../app.py"}})
    resp = client.get("{v["endpoint_protected"]}",
                      headers={{"Authorization": f"Bearer {{token}}"}})
    assert resp.status_code == 401, (
        f"Path traversal kid not rejected: status={{resp.status_code}}"
    )


def test_unknown_kid_rejected(client):
    """Token with unknown kid must be rejected."""
    import jwt, datetime
    payload = {{"{v["claim_user"]}": "user", "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)}}
    token = jwt.encode(payload, "somekey", algorithm="HS256",
                       headers={{"kid": "nonexistent-key"}})
    resp = client.get("{v["endpoint_protected"]}",
                      headers={{"Authorization": f"Bearer {{token}}"}})
    assert resp.status_code == 401


def test_kid_allowlist_enforced():
    """Static/functional check: get_key_for_kid must validate against allowlist."""
    import pytest
    with pytest.raises((ValueError, KeyError, Exception)):
        app_module.get_key_for_kid("../etc/passwd")
'''

    def _gen_spec(self, v: dict, weak_secret: str) -> str:
        return f"""# RINC4: JWT Authentication Bypass — {v["attack"].upper()}

## Incident Background
Inspired by CVE-2015-9235 and related JWT algorithm confusion vulnerabilities.
JWT libraries that do not strictly enforce algorithm choice allow attackers to
forge tokens without knowledge of the signing secret.

## Service: {v["service"]}
File: `app.py`

## Vulnerability
**Attack type:** {v["attack"]}
**Description:** {v["vuln_desc"]}

## Required Fix
{v["fix_desc"]}

## Acceptance Criteria
1. Forged/manipulated tokens are rejected with 401
2. Legitimately issued tokens continue to work
3. The specific {v["attack"]} vector is neutralized
4. No weak or hardcoded secrets remain (for weak_secret variant)
5. kid validation uses strict allowlist (for kid_injection variant)
6. All tests pass: `pytest test_jwt.py -v`

## Files
- `app.py` — fix the JWT vulnerability
- `test_jwt.py` — do NOT modify
"""

    def _gen_brief(self, v: dict) -> str:
        return f"""# RINC4: JWT Vulnerability Fix (Brief)

The {v["service"]} has a JWT authentication issue that allows attackers
to access protected endpoints without valid credentials.

Fix the authentication logic in `app.py`.

Verify with:
```
pytest test_jwt.py -v
```

**Files to fix:** `app.py`
**Do NOT modify:** `test_jwt.py`
"""
