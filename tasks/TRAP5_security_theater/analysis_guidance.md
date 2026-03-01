# Analysis Guidance — TRAP5_security_theater

## Tools to run
- `cat SECURITY_AUDIT.md` — read all 10 findings
- `cat webapp/auth.py` — check finding 7 (auth bypass)
- `cat webapp/database.py` — check finding 9 (SQL injection)
- `cat webapp/routes.py` — check findings 1-2 (likely false positives)
- `python -m pytest tests/ --co -q` — discover all tests

## Key Finding: Audit order is misleading

**Findings 1-4 (HIGH scanner confidence) — FALSE POSITIVES**:
1. routes.py: `os.path.join()` flagged as path traversal — it's used with `UPLOAD_DIR` constant, not user input
2. routes.py: `subprocess.run()` flagged — it uses a fixed command list, no shell=True, no user input
3. middleware.py: `eval()` flagged — it's inside a dead code branch (never reached, wrapped in `if False:`)
4. templates/base.html: CSP header flagged as "too permissive" — header is actually strict (default-src 'self')

**Findings 5, 6, 8, 10 (MEDIUM scanner confidence) — REAL, LOW SEVERITY**:
5. routes.py: Missing rate limiting on login endpoint
6. templates/form.html: Missing `autocomplete="off"` on password field
8. middleware.py: User-agent logged at DEBUG level (minor info disclosure)
10. templates/admin.html: Verbose stack trace displayed on errors (minor info disclosure)

**Findings 7, 9 (LOW scanner confidence) — GENUINELY CRITICAL**:
7. webapp/auth.py: Authentication bypass — the `check_token()` function compares tokens with `==`
   instead of `hmac.compare_digest()`. More critically, it also accepts `token=None` as valid
   when the user record has `token=None` (None == None evaluates True).
9. webapp/database.py: Second-order SQL injection — user input is stored (sanitized), then retrieved
   and inserted into a second query WITHOUT parameterization. The first query is safe; the second is not.

## Tell Executor

**Must fix (critical)**:
- `webapp/auth.py`: Fix check_token() to use hmac.compare_digest() and reject None tokens explicitly
- `webapp/database.py`: Fix the second query in execute_stored_query() to use parameterized queries

**Should fix (low severity)**:
- Add rate limiting or sleep to login endpoint
- Add autocomplete="off" to password field in form.html
- Change log level from DEBUG to not log user-agents
- Remove verbose stack trace from admin.html error display

**Do NOT touch (false positives)**:
- The os.path.join() usage in routes.py
- The subprocess.run() call in routes.py
- The eval() in the dead code branch in middleware.py
- The CSP header in base.html
