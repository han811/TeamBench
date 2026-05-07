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
    header = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"{header}.{body}."  # empty signature


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_none_alg_token_rejected(client):
    """Forged alg=none token must be rejected."""
    import datetime, time
    payload = {
        "user_id": "attacker",
        "role": "admin",
        "exp": int(time.time()) + 3600,
    }
    forged = _forge_none_token(payload)
    resp = client.get(
        "/profile",
        headers={"Authorization": f"Bearer {forged}"},
    )
    assert resp.status_code == 401, (
        f"alg=none token accepted — status={resp.status_code}"
    )


def test_valid_token_accepted(client):
    """Legitimately issued token must still work."""
    login_resp = client.post(
        "/login",
        json={"username": "testuser", "password": "any"},
        content_type="application/json",
    )
    assert login_resp.status_code == 200
    token = login_resp.get_json()["token"]

    resp = client.get(
        "/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


def test_tampered_token_rejected(client):
    """Token with modified payload (no re-signing) must be rejected."""
    login_resp = client.post(
        "/login",
        json={"username": "user", "password": "any"},
        content_type="application/json",
    )
    token = login_resp.get_json()["token"]
    parts = token.split(".")
    # Tamper with payload
    import base64, json as _json
    payload = _json.loads(base64.urlsafe_b64decode(parts[1] + "=="))
    payload["role"] = "admin"
    parts[1] = base64.urlsafe_b64encode(_json.dumps(payload).encode()).rstrip(b"=").decode()
    tampered = ".".join(parts)
    resp = client.get(
        "/profile",
        headers={"Authorization": f"Bearer {tampered}"},
    )
    assert resp.status_code == 401


def test_algorithms_none_not_in_decode_call():
    """Static check: decode_token() must not include 'none' in algorithms."""
    src = open("app.py").read()
    assert '"none"' not in src and "'none'" not in src, (
        "app.py still has 'none' in algorithms list"
    )
