# RINC2: SSRF Vulnerability Fix (Brief)

The WebhookProxy's `/fetch` endpoint is accepting requests it shouldn't.
Security team reports the service can be used to probe internal infrastructure.

Fix the URL validation in `app.py` so internal/cloud addresses are rejected.

Verify with:
```
pytest test_ssrf.py -v
```

**Files to fix:** `app.py`
**Do NOT modify:** `test_ssrf.py`
