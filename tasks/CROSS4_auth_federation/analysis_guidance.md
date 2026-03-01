# Analysis Guidance — CROSS4_auth_federation

## Tools to run
- `cat gateway/auth.py` — main bug locations
- `cat gateway/rbac.py` — role mapping bug
- `cat service_a/keys/public.pem` — RS256 public key (note the algorithm)
- `cat service_b/secrets.py` — HMAC secret
- `cat tests/attack_vectors.py` — see documented attacks

## Bug Locations and Fixes

### Bug 1: JWT Algorithm Confusion (gateway/auth.py)
Look for `algorithms=` parameter in JWT decode call.
**Current**: `algorithms=["HS256", "RS256"]` (accepts both)
**Fix**: `algorithms=["RS256"]` only
**Risk**: Attacker uses public key as HMAC secret to forge tokens

### Bug 2: Timing Attack on API Keys (gateway/auth.py)
Look for API key comparison in `validate_api_key()`.
**Current**: `expected == stored_key` using `==` operator
**Fix**: `hmac.compare_digest(expected, stored_key)`
**Risk**: Timing oracle allows extracting API key byte-by-byte

### Bug 3: Incomplete Role Mapping (gateway/rbac.py)
Look for the role translation dict.
**Current**: Missing `"admin": "superuser"` entry
**Fix**: Add `"admin": "superuser"` to the mapping
**Risk**: Admin users from Service A lose their privileges in Service B

### Bug 4: Session Token Never Expires (gateway/auth.py)
Look for `exp` claim generation in `create_session_token()`.
**Current**: `"exp": 0` (never expires)
**Fix**: `"exp": int(time.time()) + 3600`
**Risk**: Compromised tokens are valid indefinitely

### Bug 5: Missing Audience Validation (gateway/auth.py)
Look for `audience=` parameter in JWT decode call inside `validate_jwt()`.
**Current**: `audience=None` or missing parameter
**Fix**: Add `audience=GATEWAY_AUDIENCE` (value from `gateway/config.py`)
**Risk**: Tokens issued for one service accepted by another

## Tell Executor
Fix all 5 in gateway/auth.py and gateway/rbac.py.
Do not change gateway/config.py or any files under service_a/keys/.
