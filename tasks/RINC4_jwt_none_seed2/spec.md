# RINC4: JWT Authentication Bypass — KID_INJECTION

## Incident Background
Inspired by CVE-2015-9235 and related JWT algorithm confusion vulnerabilities.
JWT libraries that do not strictly enforce algorithm choice allow attackers to
forge tokens without knowledge of the signing secret.

## Service: TokenValidator
File: `app.py`

## Vulnerability
**Attack type:** kid_injection
**Description:** uses kid header to look up key without sanitization — path traversal or SQL injection in kid

## Required Fix
validate kid against a strict allowlist of known key IDs

## Acceptance Criteria
1. Forged/manipulated tokens are rejected with 401
2. Legitimately issued tokens continue to work
3. The specific kid_injection vector is neutralized
4. No weak or hardcoded secrets remain (for weak_secret variant)
5. kid validation uses strict allowlist (for kid_injection variant)
6. All tests pass: `pytest test_jwt.py -v`

## Files
- `app.py` — fix the JWT vulnerability
- `test_jwt.py` — do NOT modify
