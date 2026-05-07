# RINC2: SSRF to Cloud Metadata Endpoint

## Incident Background
Inspired by the Capital One breach (July 2019). An attacker exploited a
misconfigured WAF to perform Server-Side Request Forgery (SSRF) against the
GCP instance metadata service. The metadata endpoint returned
IAM/service-account credentials that were used to exfiltrate 100M+ customer records.

## Service: WebhookProxy
File: `app.py`

## Vulnerability
The `is_safe_url()` function in `app.py` validates URL scheme but does NOT block:
1. Private IP ranges (10.x, 172.16-31.x, 192.168.x)
2. Link-local range (169.254.0.0/16) — used by GCP instance metadata (metadata.google.internal)
3. Localhost (127.0.0.1, ::1)
4. The metadata hostname `metadata.google.internal`

**Attack path:**
```
GET /fetch?endpoint=http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/
→ Server fetches cloud metadata API
→ Response contains access_token credentials
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

BLOCKED_HOSTNAMES = {"metadata.google.internal"}

def is_safe_url(url: str) -> tuple[bool, str]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in ("http", "https"):
        return False, "Only http/https allowed"
    host = parsed.hostname or ""
    if host in BLOCKED_HOSTNAMES:
        return False, f"Blocked host: {host}"
    try:
        ip = ipaddress.ip_address(socket.gethostbyname(host))
        for blocked in BLOCKED_RANGES:
            if ip in blocked:
                return False, f"Blocked IP range: {ip}"
    except (socket.gaierror, ValueError):
        pass
    return True, ""
```

## Acceptance Criteria
1. `http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/` → blocked (400/403)
2. `http://169.254.169.254/` → blocked
3. `http://10.0.0.1/` → blocked
4. `http://192.168.1.1/` → blocked
5. `http://localhost/` → blocked
6. `https://example.com/` → allowed (not blocked by validation)
7. All tests pass: `pytest test_ssrf.py -v`

## Files
- `app.py` — fix `is_safe_url()` function
- `test_ssrf.py` — do NOT modify
