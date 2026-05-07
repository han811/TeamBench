# RINC1: SQL Injection Fix (Brief)

The InventoryAPI has been flagged by a security scan. Users are reporting
unexpected data exposure through the /search endpoint.

Fix the security vulnerabilities in `app.py` so the service handles
user input safely.

Verify with:
```
python init_db.py
pytest test_security.py -v
```

**Files to fix:** `app.py`
**Do NOT modify:** `init_db.py`, `test_security.py`
