# Analysis Guidance — CRYPTO2_timing_safe

## Tools to run
- `cat SECURITY_REQUIREMENTS.md` — read which comparisons need timing safety
- `grep -n "==" auth/api_keys.py auth/signatures.py auth/passwords.py auth/sessions.py auth/users.py`
- `python -m pytest tests/ --co -q` — list all tests

## The 4 Comparisons to Fix

### 1. auth/api_keys.py — validate_api_key()
**Current**: `return computed == stored_hash`
**Fix**: `return hmac.compare_digest(computed, stored_hash)`
**Why secret**: API keys are secrets; timing oracle allows key extraction

### 2. auth/signatures.py — verify_signature()
**Current**: `return computed == provided_signature`
**Fix**: `return hmac.compare_digest(computed, provided_signature)`
**Why secret**: HMAC signatures are MACs; timing oracle breaks MAC security

### 3. auth/passwords.py — check_password()
**Current**: `return stored_hash == compute_hash(password)`
**Fix**: `return hmac.compare_digest(stored_hash, compute_hash(password))`
**Why secret**: Password hashes are secret; timing leaks info about hash length match

### 4. auth/sessions.py — validate_session()
**Current**: `return stored_token == provided_token`
**Fix**: `return hmac.compare_digest(stored_token.encode(), provided_token.encode())`
**Why secret**: Session tokens are bearer credentials; timing allows forgery

## The 1 Comparison NOT to Change

### auth/users.py — find_user()
**Current**: `return user if user['username'] == query_username else None`
**DO NOT CHANGE**: Usernames are public identifiers. Timing differences in username lookup
do not leak secrets — an attacker already knows whether a username exists (registration
would tell them). Using hmac.compare_digest here is security theater.

## Tell Executor
Fix ONLY the 4 comparisons in api_keys.py, signatures.py, passwords.py, sessions.py.
Do NOT touch auth/users.py.
