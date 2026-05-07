# RINC4: JWT Authentication Bypass — WEAK_SECRET

## Incident Background
Inspired by CVE-2015-9235 and related JWT algorithm confusion vulnerabilities.
JWT libraries that do not strictly enforce algorithm choice allow attackers to
forge tokens without knowledge of the signing secret.

## Service: APIGateway
File: `app.py`

## Vulnerability
**Attack type:** weak_secret
**Description:** uses a short, guessable HMAC secret ('secret', 'key', etc.)

## Required Fix
replace weak secret with a 256-bit random secret loaded from environment

## Acceptance Criteria
1. Forged/manipulated tokens are rejected with 401
2. Legitimately issued tokens continue to work
3. The specific weak_secret vector is neutralized
4. No weak or hardcoded secrets remain (for weak_secret variant)
5. kid validation uses strict allowlist (for kid_injection variant)
6. All tests pass: `pytest test_jwt.py -v`

## Files
- `app.py` — fix the JWT vulnerability
- `test_jwt.py` — do NOT modify
