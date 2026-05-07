# RINC4: JWT Vulnerability Fix (Brief)

The TokenValidator has a JWT authentication issue that allows attackers
to access protected endpoints without valid credentials.

Fix the authentication logic in `app.py`.

Verify with:
```
pytest test_jwt.py -v
```

**Files to fix:** `app.py`
**Do NOT modify:** `test_jwt.py`
