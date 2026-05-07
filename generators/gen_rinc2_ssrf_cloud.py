"""
Parameterized generator for RINC2: SSRF to Cloud Metadata.

Inspiration: Capital One breach (2019) — attacker exploited SSRF to reach
AWS EC2 instance metadata endpoint (169.254.169.254), obtaining IAM credentials.
Workspace has a web app with a URL-fetching endpoint. The spec reveals the
exact metadata paths that are reachable and the fix (URL allowlist / block
private ranges).

Seeds vary: cloud provider (AWS/GCP/Azure), service name, URL parameter name,
metadata path structure.

Grading: 7 checks — metadata endpoint blocked, private IP ranges blocked,
public URLs still fetchable, SSRF fix in place.
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

CLOUD_VARIANTS = [
    {
        "provider": "AWS",
        "metadata_url": "http://169.254.169.254/latest/meta-data/iam/security-credentials/",
        "metadata_host": "169.254.169.254",
        "metadata_path": "/latest/meta-data/",
        "sensitive_path": "/latest/meta-data/iam/security-credentials/ec2-role",
        "block_desc": "AWS EC2 instance metadata (169.254.169.254)",
        "cred_field": "AccessKeyId",
    },
    {
        "provider": "GCP",
        "metadata_url": "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/",
        "metadata_host": "metadata.google.internal",
        "metadata_path": "/computeMetadata/v1/",
        "sensitive_path": "/computeMetadata/v1/instance/service-accounts/default/token",
        "block_desc": "GCP instance metadata (metadata.google.internal)",
        "cred_field": "access_token",
    },
    {
        "provider": "Azure",
        "metadata_url": "http://169.254.169.254/metadata/instance?api-version=2021-02-01",
        "metadata_host": "169.254.169.254",
        "metadata_path": "/metadata/",
        "sensitive_path": "/metadata/identity/oauth2/token?api-version=2018-02-01&resource=https://management.azure.com/",
        "block_desc": "Azure IMDS (169.254.169.254/metadata)",
        "cred_field": "access_token",
    },
]

SERVICE_NAMES = ["LinkPreviewService", "WebhookProxy", "URLFetcherAPI"]


class Generator(TaskGenerator):
    task_id = "RINC2_ssrf_cloud"
    domain = "security"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        cloud = CLOUD_VARIANTS[seed % len(CLOUD_VARIANTS)]
        service_name = SERVICE_NAMES[seed % len(SERVICE_NAMES)]
        port = rng.randint(5100, 5199)
        url_param = rng.choice(["url", "target", "endpoint"])

        workspace_files = {
            "app.py": self._gen_app(cloud, service_name, port, url_param),
            "test_ssrf.py": self._gen_tests(cloud, url_param),
            "requirements.txt": "flask>=2.3\npytest>=7.0\nrequests>=2.28\nurllib3>=2.0\n",
        }

        expected = {
            "seed": seed,
            "provider": cloud["provider"],
            "metadata_host": cloud["metadata_host"],
            "url_param": url_param,
            "fix": "block_private_ip_ranges_and_metadata_endpoints",
            "blocked_ranges": ["169.254.0.0/16", "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"],
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._gen_spec(cloud, service_name, url_param),
            brief_md=self._gen_brief(service_name, url_param),
            expected=expected,
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "security", "cve_class": "SSRF"},
        )

    def _gen_app(self, cloud: dict, service_name: str, port: int, url_param: str) -> str:
        return f'''\
"""
{service_name}: Fetches remote URLs and returns their content.

WARNING: This code contains an SSRF vulnerability for training purposes.
Inspiration: Capital One breach (2019) — SSRF to {cloud["provider"]} instance metadata.
"""
import ipaddress
import socket
import urllib.parse
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)
TIMEOUT = 5


def is_safe_url(url: str) -> tuple[bool, str]:
    """Validate that a URL is safe to fetch.

    VULNERABLE: This function is incomplete — it does not block private IP
    ranges or cloud metadata endpoints. An attacker can reach internal
    services and cloud metadata APIs.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False, "Only http/https allowed"
        # BUG: no check for private/link-local IP ranges
        # BUG: no check for metadata hostnames (e.g. {cloud["metadata_host"]})
        return True, ""
    except Exception as e:
        return False, str(e)


@app.route("/fetch")
def fetch_url():
    """Fetch a remote URL and return the response body.

    VULNERABLE: accepts any URL including internal/metadata endpoints.
    """
    url = request.args.get("{url_param}", "")
    if not url:
        return jsonify({{"error": "missing {url_param} parameter"}}), 400

    safe, reason = is_safe_url(url)
    if not safe:
        return jsonify({{"error": reason}}), 400

    try:
        resp = requests.get(url, timeout=TIMEOUT, allow_redirects=False)
        return jsonify({{
            "status_code": resp.status_code,
            "content_length": len(resp.text),
            "content": resp.text[:500],
        }})
    except requests.RequestException as e:
        return jsonify({{"error": str(e)}}), 502


@app.route("/health")
def health():
    return jsonify({{"status": "ok", "service": "{service_name}"}})


if __name__ == "__main__":
    app.run(port={port}, debug=False)
'''

    def _gen_tests(self, cloud: dict, url_param: str) -> str:
        metadata_url = cloud["metadata_url"]
        return f'''\
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
    resp = client.get(f"/fetch?{url_param}={metadata_url}")
    assert resp.status_code in (400, 403), (
        f"Metadata URL not blocked: status={{resp.status_code}}"
    )
    data = resp.get_json()
    assert "error" in data


def test_link_local_ip_blocked(client):
    """169.254.x.x (link-local) must be blocked."""
    resp = client.get("/fetch?{url_param}=http://169.254.169.254/")
    assert resp.status_code in (400, 403), (
        f"169.254.169.254 not blocked: status={{resp.status_code}}"
    )


def test_private_10_range_blocked(client):
    """10.x.x.x private range must be blocked."""
    resp = client.get("/fetch?{url_param}=http://10.0.0.1/internal")
    assert resp.status_code in (400, 403), (
        f"10.0.0.1 not blocked: status={{resp.status_code}}"
    )


def test_private_192168_range_blocked(client):
    """192.168.x.x private range must be blocked."""
    resp = client.get("/fetch?{url_param}=http://192.168.1.1/admin")
    assert resp.status_code in (400, 403), (
        f"192.168.1.1 not blocked: status={{resp.status_code}}"
    )


def test_localhost_blocked(client):
    """localhost must be blocked."""
    resp = client.get("/fetch?{url_param}=http://localhost/etc/passwd")
    assert resp.status_code in (400, 403), (
        f"localhost not blocked: status={{resp.status_code}}"
    )


def test_public_url_allowed(client):
    """Public URLs should pass validation (mock the actual request)."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "Hello World"
    with patch("requests.get", return_value=mock_resp):
        resp = client.get("/fetch?{url_param}=https://example.com/")
    # Should not be blocked (400 from validation)
    assert resp.status_code != 400 or "allowed" not in resp.get_json().get("error", ""), (
        "Public URL https://example.com blocked — SSRF fix is too broad"
    )


def test_is_safe_url_rejects_metadata(client):
    """is_safe_url() must reject the metadata host directly."""
    safe, reason = app_module.is_safe_url("{metadata_url}")
    assert not safe, (
        f"is_safe_url accepted metadata URL — reason was: {{reason}}"
    )


def test_no_scheme_rejected(client):
    """Non-http/https schemes must be rejected."""
    resp = client.get("/fetch?{url_param}=file:///etc/passwd")
    assert resp.status_code in (400, 403)
'''

    def _gen_spec(self, cloud: dict, service_name: str, url_param: str) -> str:
        provider = cloud["provider"]
        block_desc = cloud["block_desc"]
        metadata_host = cloud["metadata_host"]
        metadata_url = cloud["metadata_url"]
        cred_field = cloud["cred_field"]
        return f"""# RINC2: SSRF to Cloud Metadata Endpoint

## Incident Background
Inspired by the Capital One breach (July 2019). An attacker exploited a
misconfigured WAF to perform Server-Side Request Forgery (SSRF) against the
{provider} instance metadata service. The metadata endpoint returned
IAM/service-account credentials that were used to exfiltrate 100M+ customer records.

## Service: {service_name}
File: `app.py`

## Vulnerability
The `is_safe_url()` function in `app.py` validates URL scheme but does NOT block:
1. Private IP ranges (10.x, 172.16-31.x, 192.168.x)
2. Link-local range (169.254.0.0/16) — used by {block_desc}
3. Localhost (127.0.0.1, ::1)
4. The metadata hostname `{metadata_host}`

**Attack path:**
```
GET /fetch?{url_param}={metadata_url}
→ Server fetches cloud metadata API
→ Response contains {cred_field} credentials
→ Attacker uses credentials to access cloud resources
```

## Required Fix

Extend `is_safe_url()` to block:

```python
import ipaddress
import socket

BLOCKED_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),   # link-local / cloud metadata
    ipaddress.ip_network("127.0.0.0/8"),       # loopback
    ipaddress.ip_network("::1/128"),            # IPv6 loopback
]

BLOCKED_HOSTNAMES = {{"{metadata_host}"}}

def is_safe_url(url: str) -> tuple[bool, str]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False, "Only http/https allowed"
    host = parsed.hostname or ""
    if host in BLOCKED_HOSTNAMES:
        return False, f"Blocked host: {{host}}"
    try:
        ip = ipaddress.ip_address(socket.gethostbyname(host))
        for blocked in BLOCKED_RANGES:
            if ip in blocked:
                return False, f"Blocked IP range: {{ip}}"
    except (socket.gaierror, ValueError):
        pass
    return True, ""
```

## Acceptance Criteria
1. `{metadata_url}` → blocked (400/403)
2. `http://169.254.169.254/` → blocked
3. `http://10.0.0.1/` → blocked
4. `http://192.168.1.1/` → blocked
5. `http://localhost/` → blocked
6. `https://example.com/` → allowed (not blocked by validation)
7. All tests pass: `pytest test_ssrf.py -v`

## Files
- `app.py` — fix `is_safe_url()` function
- `test_ssrf.py` — do NOT modify
"""

    def _gen_brief(self, service_name: str, url_param: str) -> str:
        return f"""# RINC2: SSRF Vulnerability Fix (Brief)

The {service_name}'s `/fetch` endpoint is accepting requests it shouldn't.
Security team reports the service can be used to probe internal infrastructure.

Fix the URL validation in `app.py` so internal/cloud addresses are rejected.

Verify with:
```
pytest test_ssrf.py -v
```

**Files to fix:** `app.py`
**Do NOT modify:** `test_ssrf.py`
"""
