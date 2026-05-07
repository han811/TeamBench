"""
APIGateway: API gateway with JWT authentication.

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
JWT_SECRET = os.environ.get("JWT_SECRET", "secret")


def create_token(sub: str, scope: str) -> str:
    payload = {
        "sub": sub,
        "scope": scope,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_token(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])


@app.route("/auth/token", methods=["POST"])
def get_token():
    data = request.get_json() or {}
    user = data.get("username", "guest")
    token = create_token(user, "read")
    return jsonify({"token": token, "type": "Bearer"})


@app.route("/api/data")
def protected_data():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return jsonify({"error": "missing token"}), 401
    try:
        payload = verify_token(auth[7:])
        return jsonify({"data": "sensitive", "user": payload.get("sub")})
    except jwt.InvalidTokenError as e:
        return jsonify({"error": str(e)}), 401


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    app.run(port=5317, debug=False)
