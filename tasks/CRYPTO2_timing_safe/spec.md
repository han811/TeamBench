# CRYPTO2: Timing-Safe Secret Comparisons

## Goal
Fix timing side-channel vulnerabilities in the authentication system's secret comparisons.

## Requirements
1. All secret comparisons must use constant-time comparison functions
2. Non-secret comparisons (public data lookups) must NOT be changed
3. All functional tests must pass after changes: `pytest tests/`
4. See `SECURITY_REQUIREMENTS.md` for which comparisons are secret-bearing

## Supporting Documents
- `auth/api_keys.py`: API key validation (secret comparison)
- `auth/signatures.py`: HMAC signature verification (secret comparison)
- `auth/passwords.py`: Password hash comparison (secret comparison)
- `auth/sessions.py`: Session token validation (secret comparison)
- `auth/users.py`: Username lookup (NOT secret — plain == is correct here)
- `SECURITY_REQUIREMENTS.md`: Documents which comparisons need timing safety

## Important
NOT all string comparisons need to be constant-time. A username is a public identifier;
timing differences in username lookup do not leak secret information. Changing the username
lookup to use `hmac.compare_digest` is security theater and will cause issues.
Only comparisons involving secrets (keys, signatures, hashes, tokens) need fixing.
