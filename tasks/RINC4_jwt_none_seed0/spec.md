# RINC4: JWT Authentication Bypass — NONE_ALGORITHM

## Incident Background
Inspired by CVE-2015-9235 and related JWT algorithm confusion vulnerabilities.
JWT libraries that do not strictly enforce algorithm choice allow attackers to
forge tokens without knowledge of the signing secret.

## Service: AuthService
File: `app.py`

## Vulnerability
**Attack type:** none_algorithm
**Description:** accepts tokens with alg=none (no signature required)

## Required Fix
explicitly reject alg=none and enforce alg=HS256 or RS256

## Acceptance Criteria
1. Forged/manipulated tokens are rejected with 401
2. Legitimately issued tokens continue to work
3. The specific none_algorithm vector is neutralized
4. No weak or hardcoded secrets remain (for weak_secret variant)
5. kid validation uses strict allowlist (for kid_injection variant)
6. All tests pass: `pytest test_jwt.py -v`

## Files
- `app.py` — fix the JWT vulnerability
- `test_jwt.py` — do NOT modify
