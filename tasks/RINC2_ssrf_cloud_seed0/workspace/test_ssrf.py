"""
SSRF security tests for the URL fetcher service.

Tests verify that cloud metadata endpoints and private IP ranges
are blocked while legitimate public URLs are accepted.
"""
import pytest
import app as app_module
from unittest.mock import patch, MagicMock


@pytest.fixture
def client():
    app_module.app.config["TESTING"] = True
    with app_module.app.test_client() as c:
        yield c


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200


def test_metadata_endpoint_blocked(client):
    """Cloud metadata URL must be blocked."""
    resp = client.get(f"/fetch?target=http://169.254.169.254/latest/meta-data/iam/security-credentials/")
    assert resp.status_code in (400, 403), (
        f"Metadata URL not blocked: status={resp.status_code}"
    )
    data = resp.get_json()
    assert "error" in data


def test_link_local_ip_blocked(client):
    """169.254.x.x (link-local) must be blocked."""
    resp = client.get("/fetch?target=http://169.254.169.254/")
    assert resp.status_code in (400, 403), (
        f"169.254.169.254 not blocked: status={resp.status_code}"
    )


def test_private_10_range_blocked(client):
    """10.x.x.x private range must be blocked."""
    resp = client.get("/fetch?target=http://10.0.0.1/internal")
    assert resp.status_code in (400, 403), (
        f"10.0.0.1 not blocked: status={resp.status_code}"
    )


def test_private_192168_range_blocked(client):
    """192.168.x.x private range must be blocked."""
    resp = client.get("/fetch?target=http://192.168.1.1/admin")
    assert resp.status_code in (400, 403), (
        f"192.168.1.1 not blocked: status={resp.status_code}"
    )


def test_localhost_blocked(client):
    """localhost must be blocked."""
    resp = client.get("/fetch?target=http://localhost/etc/passwd")
    assert resp.status_code in (400, 403), (
        f"localhost not blocked: status={resp.status_code}"
    )


def test_public_url_allowed(client):
    """Public URLs should pass validation (mock the actual request)."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "Hello World"
    with patch("requests.get", return_value=mock_resp):
        resp = client.get("/fetch?target=https://example.com/")
    # Should not be blocked (400 from validation)
    assert resp.status_code != 400 or "allowed" not in resp.get_json().get("error", ""), (
        "Public URL https://example.com blocked — SSRF fix is too broad"
    )


def test_is_safe_url_rejects_metadata(client):
    """is_safe_url() must reject the metadata host directly."""
    safe, reason = app_module.is_safe_url("http://169.254.169.254/latest/meta-data/iam/security-credentials/")
    assert not safe, (
        f"is_safe_url accepted metadata URL — reason was: {reason}"
    )


def test_no_scheme_rejected(client):
    """Non-http/https schemes must be rejected."""
    resp = client.get("/fetch?target=file:///etc/passwd")
    assert resp.status_code in (400, 403)
