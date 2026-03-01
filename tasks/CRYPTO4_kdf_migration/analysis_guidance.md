# Analysis Guidance — CRYPTO4_kdf_migration

## Tools to run
- `cat auth_system/migrator.py` — find format marker bug
- `cat auth_system/formats.py` — understand all 4 formats
- `cat auth_system/verifier.py` — find hex-salt handling
- `python -m pytest tests/test_format_detect.py -v` — verify format detection

## The 4 Hash Formats

### Format 0: Plain MD5
`md5:<32-char hex>` — e.g., `md5:5f4dcc3b5aa765d61d8327deb882cf99`
Verify: `hashlib.md5(password.encode()).hexdigest() == stored_hash`

### Format 1: Salted MD5
`md5s:<hex_salt>:<hex_hash>` — e.g., `md5s:deadbeef:5f4dcc3...`
**IMPORTANT**: Salt is HEX-encoded, not base64. Common mistake is to base64-decode it.
Verify: `hashlib.md5((bytes.fromhex(salt) + password.encode())).hexdigest() == hash`

### Format 2: SHA256-HMAC
`sha256h:<b64_salt>:<b64_hash>` — e.g., `sha256h:dGVzdA==:abc123==`
Salt is BASE64-encoded. HMAC-SHA256 with the salt as the key.
Verify: `hmac.new(base64.b64decode(salt), password.encode(), sha256).digest() == base64.b64decode(hash)`

### Format 3: Argon2id
`argon2:$argon2id$v=19$...` — Standard argon2 encoded format
Verify: `argon2.PasswordHasher().verify(stored_hash.removeprefix("argon2:"), password)`

## Bug 1: Format Marker Not Updated After Upgrade (auth_system/migrator.py)

```python
# BUGGY: writes new Argon2id hash to DB but doesn't update format field
def upgrade_hash(user_id: int, password: str, db) -> bool:
    ph = argon2.PasswordHasher()
    new_hash = "argon2:" + ph.hash(password)
    # BUG: updates hash_value column but NOT hash_format column
    db.execute("UPDATE users SET hash_value=? WHERE id=?", (new_hash, user_id))
    db.commit()
    return True
    # FIX: also update hash_format to 3 (Argon2id)
```

**Effect of bug**: After upgrade, user tries to log in again. Verifier reads `hash_format=1`
(still MD5), tries MD5 verification on an Argon2id hash → fails. User locked out.

## Bug 2: Hex Salt for Format 1 (auth_system/verifier.py)

```python
# BUGGY: base64-decodes the salt, but format 1 uses hex encoding
def verify_format1(password: str, stored: str) -> bool:
    _, salt_enc, hash_enc = stored.split(":")
    salt = base64.b64decode(salt_enc)  # BUG: should be bytes.fromhex(salt_enc)
    ...
```

Fix: `salt = bytes.fromhex(salt_enc)` for format 1.

## Tell Executor
1. Fix `auth_system/migrator.py`: update BOTH `hash_value` AND `hash_format` on upgrade
2. Fix `auth_system/verifier.py`: use `bytes.fromhex()` for format 1 salt (not base64)
3. Implement new user registration in `auth_system/hasher.py` to use Argon2id
