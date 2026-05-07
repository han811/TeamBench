"""Security tests for ConfigLoaderService — yaml.load() deserialization."""
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


def test_rce_yaml_payload_rejected(client):
    """A !!python/object YAML payload must not execute code."""
    import os
    malicious_yaml = "!!python/object/apply:os.system ['touch /tmp/pwned_rinc3']"
    resp = client.post(
        "/load-config",
        json={"config": malicious_yaml},
        content_type="application/json",
    )
    import os as _os
    assert not _os.path.exists("/tmp/pwned_rinc3"), (
        "RCE payload executed — /tmp/pwned_rinc3 was created"
    )


def test_safe_yaml_works(client):
    """Normal YAML config should load correctly."""
    safe_yaml = "name: myapp\nversion: 1\ntimeout: 30"
    resp = client.post(
        "/load-config",
        json={"config": safe_yaml},
        content_type="application/json",
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert "loaded" in data
    assert data["loaded"].get("name") == "myapp"


def test_no_yaml_loader_in_app():
    """Static check: app.py must not use yaml.Loader (full loader)."""
    src = open("app.py").read()
    assert "yaml.Loader" not in src, (
        "app.py still uses yaml.Loader — replace with yaml.safe_load()"
    )


def test_yaml_object_tag_rejected(client):
    """YAML !!python/object tag must be rejected."""
    evil = "!!python/object:os.path.join []"
    resp = client.post(
        "/load-config",
        json={"config": evil},
        content_type="application/json",
    )
    assert resp.status_code in (400, 500), (
        f"YAML object tag not rejected: status={resp.status_code}"
    )
