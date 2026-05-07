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
        f"JWT_SECRET is still a weak value: '{secret}'"
    )
    assert len(secret) >= 32, (
        f"JWT_SECRET is too short: {len(secret)} chars (need >= 32)"
    )


def test_valid_token_flow(client):
    """Full login + protected endpoint flow must work."""
    resp = client.post("/auth/token", json={"username": "testuser"})
    assert resp.status_code == 200
    token = resp.get_json()["token"]

    resp2 = client.get(
        "/api/data",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp2.status_code == 200


def test_forged_token_rejected(client):
    """Token signed with known weak secret must be rejected."""
    import jwt, datetime
    forged = jwt.encode(
        {"sub": "hacker", "scope": "admin",
          "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)},
        "secret",  # known weak secret
        algorithm="HS256",
    )
    resp = client.get(
        "/api/data",
        headers={"Authorization": f"Bearer {forged}"},
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
            assert False, f"Hardcoded weak default secret '{weak_val}' found in app.py"
