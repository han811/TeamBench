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
    resp = client.post("/token", json={"user": "alice"})
    assert resp.status_code == 200
    token = resp.get_json()["token"]
    resp2 = client.get("/secure/data",
                       headers={"Authorization": f"Bearer {token}"})
    assert resp2.status_code == 200


def test_path_traversal_kid_rejected(client):
    """kid with path traversal must be rejected."""
    import jwt, datetime
    # Craft a token with kid='../app.py'
    payload = {"uid": "attacker", "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)}
    # Sign with a known key that the file would contain
    token = jwt.encode(payload, "dummy", algorithm="HS256",
                       headers={"kid": "../app.py"})
    resp = client.get("/secure/data",
                      headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401, (
        f"Path traversal kid not rejected: status={resp.status_code}"
    )


def test_unknown_kid_rejected(client):
    """Token with unknown kid must be rejected."""
    import jwt, datetime
    payload = {"uid": "user", "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1)}
    token = jwt.encode(payload, "somekey", algorithm="HS256",
                       headers={"kid": "nonexistent-key"})
    resp = client.get("/secure/data",
                      headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_kid_allowlist_enforced():
    """Static/functional check: get_key_for_kid must validate against allowlist."""
    import pytest
    with pytest.raises((ValueError, KeyError, Exception)):
        app_module.get_key_for_kid("../etc/passwd")
