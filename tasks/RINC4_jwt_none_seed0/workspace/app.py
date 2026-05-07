"""
AuthService: JWT authentication service.

WARNING: This code contains a JWT algorithm confusion vulnerability.
Inspiration: CVE-2015-9235 — alg=none bypass.
"""
import jwt
import datetime
from flask import Flask, request, jsonify

app = Flask(__name__)
SECRET_KEY = "super-secret-key-change-in-production"


def create_token(user_id: str, role: str) -> str:
    payload = {
        "user_id": user_id,
        "role": role,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        "iat": datetime.datetime.utcnow(),
    }
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
        raise ValueError(f"Invalid token: {e}")


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json() or {}
    username = data.get("username", "")
    password = data.get("password", "")
    # Simplified auth — in real app would check DB
    if username == "admin" and password == "correct_password":
        token = create_token(username, "admin")
        return jsonify({"token": token})
    elif username and password:
        token = create_token(username, "user")
        return jsonify({"token": token})
    return jsonify({"error": "invalid credentials"}), 401


@app.route("/profile")
def protected():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "missing token"}), 401
    token = auth[7:]
    try:
        payload = decode_token(token)
        return jsonify({"user": payload.get("user_id"), "role": payload.get("role"), "data": "sensitive_data"})
    except ValueError as e:
        return jsonify({"error": str(e)}), 401


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "AuthService"})


if __name__ == "__main__":
    app.run(port=5349, debug=False)
