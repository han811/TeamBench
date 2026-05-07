"""Security tests for TaskQueueService — pickle deserialization."""
import base64
import json
import pickle
import pytest
import app as app_module


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def _encode(obj) -> str:
    return base64.b64encode(pickle.dumps(obj)).decode()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_rce_payload_rejected(client):
    """A malicious pickle payload must be rejected (not executed)."""
    import os

    class RCEPayload:
        def __reduce__(self):
            # Would execute: touch /tmp/pwned
            return (os.system, ("touch /tmp/pwned_rinc3",))

    payload = base64.b64encode(pickle.dumps(RCEPayload())).decode()
    resp = client.post(
        "/submit",
        json={"payload": payload},
        content_type="application/json",
    )
    # Should be rejected — either 400 or the endpoint no longer uses pickle
    import os as _os
    assert not _os.path.exists("/tmp/pwned_rinc3"), (
        "RCE payload executed — /tmp/pwned_rinc3 was created"
    )


def test_safe_deserialization_works(client):
    """Normal JSON task data should be accepted after the fix."""
    import json, base64
    # After fix, endpoint should accept JSON-encoded data
    payload = base64.b64encode(json.dumps({"type": "compute", "value": 42}).encode()).decode()
    resp = client.post(
        "/submit",
        json={"payload": payload},
        content_type="application/json",
    )
    # Should not crash (200 or 400 with meaningful error, not 500)
    assert resp.status_code in (200, 400)


def test_no_pickle_loads_in_app(tmp_path):
    """Static check: app.py must not call pickle.loads() on request data."""
    import re, ast
    src = open("app.py").read()
    # Check for pickle.loads in the route handler
    assert "pickle.loads" not in src, (
        "app.py still contains pickle.loads() — replace with safe deserialization"
    )


def test_missing_payload_returns_400(client):
    resp = client.post("/submit", json={}, content_type="application/json")
    assert resp.status_code == 400
