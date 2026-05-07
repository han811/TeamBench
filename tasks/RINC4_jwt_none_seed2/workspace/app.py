"""
TokenValidator: Token validator with kid (Key ID) header support.

WARNING: kid header used without sanitization — path traversal possible.
Inspiration: JWT kid header injection attacks.
"""
import jwt
import datetime
import os
from flask import Flask, request, jsonify

app = Flask(__name__)

# Key store — kid maps to secret
KEY_STORE = {
    "key-2024-01": "production-secret-key-alpha",
    "key-2024-02": "production-secret-key-beta",
}


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
            raise ValueError(f"Unknown kid: {kid}")
    return key


def verify_token(token: str) -> dict:
    header = jwt.get_unverified_header(token)
    kid = header.get("kid", "key-2024-01")
    secret = get_key_for_kid(kid)
    return jwt.decode(token, secret, algorithms=["HS256"])


@app.route("/token", methods=["POST"])
def issue_token():
    data = request.get_json() or {}
    user = data.get("user", "anonymous")
    payload = {
        "uid": user,
        "perms": "read",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    }
    token = jwt.encode(payload, KEY_STORE["key-2024-01"], algorithm="HS256",
                       headers={"kid": "key-2024-01"})
    return jsonify({"token": token})


@app.route("/secure/data")
def secure_data():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "missing token"}), 401
    try:
        payload = verify_token(auth[7:])
        return jsonify({"secure": True, "user": payload.get("uid")})
    except (jwt.InvalidTokenError, ValueError) as e:
        return jsonify({"error": str(e)}), 401


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(port=5307, debug=False)
