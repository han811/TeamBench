"""
Parameterized generator for CRYPTO4: KDF Migration.

Each seed produces a different application context (auth system, employee portal,
customer account) with the same 2 structural bugs:
  Bug 1 (migrator.py): upgrade_hash() updates hash_value but NOT hash_format column
  Bug 2 (verifier.py): format 1 salt decoded with base64 instead of hex

The Planner's static analysis (reading migrator.py and verifier.py) will find both
bugs; without that cross-format analysis the Executor will break backward compat
or leave the format marker bug causing cascading login failures.
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# Seed-specific application contexts
APP_CONTEXTS = [
    {
        "name": "User Authentication System",
        "module_comment": "User authentication system password storage",
        "db_table": "users",
        "test_user_prefix": "user",
        "app_title": "User Auth",
    },
    {
        "name": "Employee Portal Authentication",
        "module_comment": "Employee portal password storage",
        "db_table": "employees",
        "test_user_prefix": "emp",
        "app_title": "Employee Portal",
    },
    {
        "name": "Customer Account Authentication",
        "module_comment": "Customer account password storage",
        "db_table": "customers",
        "test_user_prefix": "cust",
        "app_title": "Customer Accounts",
    },
]

# Seed-specific hex salts (different per seed for contamination resistance)
HEX_SALTS = [
    "deadbeefcafe0123",
    "feedface12345678",
    "cafebabe87654321",
]

# Seed-specific HMAC salts
HMAC_SALTS = [
    b"testingsalt",
    b"employeesalt",
    b"customersalt",
]

# Seed-specific test passwords
TEST_PASSWORDS = [
    "testpassword123",
    "employeepass456",
    "customerpass789",
]


class Generator(TaskGenerator):
    task_id = "CRYPTO4_kdf_migration"
    domain = "Security"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % len(APP_CONTEXTS)

        ctx = APP_CONTEXTS[idx]
        hex_salt = HEX_SALTS[idx]
        hmac_salt = HMAC_SALTS[idx]
        test_password = TEST_PASSWORDS[idx]

        workspace_files = self._make_workspace(ctx, hex_salt, hmac_salt, test_password)

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "CRYPTO4_kdf_migration")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="CRYPTO4_kdf_migration",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "bugs_fixed": ["format_marker", "hex_salt"],
                "new_hash_format": "argon2id",
                "legacy_formats_supported": [0, 1, 2],
                "seed": seed,
                "context": ctx["name"],
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Security"},
        )

    def _make_workspace(self, ctx: dict, hex_salt: str, hmac_salt: bytes, test_password: str) -> dict:
        import hashlib, hmac as hmac_mod, base64

        files: dict[str, str] = {}

        table = ctx["db_table"]
        user_prefix = ctx["test_user_prefix"]
        comment = ctx["module_comment"]

        # --- auth_system/__init__.py ---
        files["auth_system/__init__.py"] = ""

        # --- auth_system/formats.py ---
        files["auth_system/formats.py"] = f'''"""Hash format constants and detection for {comment}."""

PLAIN_MD5 = 0
SALTED_MD5 = 1
SHA256_HMAC = 2
ARGON2ID = 3


def detect_format(stored_hash: str) -> int:
    """Detect the format of a stored password hash."""
    if stored_hash.startswith("argon2:"):
        return ARGON2ID
    elif stored_hash.startswith("md5s:"):
        return SALTED_MD5
    elif stored_hash.startswith("sha256h:"):
        return SHA256_HMAC
    elif stored_hash.startswith("md5:"):
        return PLAIN_MD5
    raise ValueError(f"Unknown hash format: {{stored_hash[:20]}}")
'''

        # --- auth_system/hasher.py (BUG: uses MD5 for new users) ---
        files["auth_system/hasher.py"] = f'''"""Password hasher for {comment}."""
import hashlib
import os


def hash_password(password: str) -> tuple[str, int]:
    """Hash a new password. Currently uses MD5 (insecure — should use Argon2id).

    Returns:
        (stored_hash, format_id) tuple
    """
    # TODO: migrate to Argon2id
    hashed = "md5:" + hashlib.md5(password.encode()).hexdigest()
    return hashed, 0  # format 0 = plain MD5
'''

        # --- auth_system/verifier.py (BUG: base64 decodes hex salt in format 1) ---
        files["auth_system/verifier.py"] = f'''"""Multi-format password verifier for {comment}."""
import hashlib
import hmac
import base64

from auth_system.formats import PLAIN_MD5, SALTED_MD5, SHA256_HMAC, ARGON2ID


def verify_password(password: str, stored_hash: str, hash_format: int) -> bool:
    """Verify a password against its stored hash.

    Supports all 4 legacy and current formats.
    """
    if hash_format == PLAIN_MD5:
        # Format 0: md5:<hex_hash>
        expected = stored_hash.removeprefix("md5:")
        return hashlib.md5(password.encode()).hexdigest() == expected

    elif hash_format == SALTED_MD5:
        # Format 1: md5s:<hex_salt>:<hex_hash>
        _, salt_enc, hash_enc = stored_hash.split(":")
        # BUG: salt is hex-encoded, not base64 — this will raise or produce wrong bytes
        salt = base64.b64decode(salt_enc)  # BUG: should be bytes.fromhex(salt_enc)
        computed = hashlib.md5(salt + password.encode()).hexdigest()
        return computed == hash_enc

    elif hash_format == SHA256_HMAC:
        # Format 2: sha256h:<b64_salt>:<b64_hash>
        _, salt_enc, hash_enc = stored_hash.split(":")
        salt = base64.b64decode(salt_enc)  # CORRECT: format 2 uses base64
        computed = hmac.new(salt, password.encode(), hashlib.sha256).digest()
        return base64.b64encode(computed).decode() == hash_enc

    elif hash_format == ARGON2ID:
        # Format 3: argon2:$argon2id$...
        import argon2
        ph = argon2.PasswordHasher()
        try:
            return ph.verify(stored_hash.removeprefix("argon2:"), password)
        except Exception:
            return False

    return False
'''

        # --- auth_system/migrator.py (BUG: does not update hash_format column) ---
        files["auth_system/migrator.py"] = f'''"""Hash upgrade logic for {comment}."""
import argon2


def upgrade_hash(user_id: int, password: str, db) -> bool:
    """Upgrade a legacy password hash to Argon2id after successful verification.

    Should update both hash_value and hash_format in the database.
    """
    ph = argon2.PasswordHasher(time_cost=2, memory_cost=65536, parallelism=1)
    new_hash = "argon2:" + ph.hash(password)
    # BUG: only updates hash_value, does NOT update hash_format to 3 (ARGON2ID)
    # After this, the next login will try to verify an Argon2id hash as MD5 → failure
    db.execute(
        "UPDATE {table} SET hash_value=? WHERE id=?",
        (new_hash, user_id),
    )
    db.commit()
    return True
    # FIX: should be:
    # db.execute(
    #     "UPDATE {table} SET hash_value=?, hash_format=3 WHERE id=?",
    #     (new_hash, user_id),
    # )
'''

        # --- auth_system/user_store.py ---
        files["auth_system/user_store.py"] = f'''"""User database operations for {comment}."""
import sqlite3
from typing import Optional

from auth_system.formats import detect_format


def get_user(db, username: str) -> Optional[dict]:
    """Fetch a user row by username."""
    row = db.execute(
        "SELECT id, username, hash_value, hash_format FROM {table} WHERE username=?",
        (username,),
    ).fetchone()
    if row is None:
        return None
    return {{"id": row[0], "username": row[1], "hash_value": row[2], "hash_format": row[3]}}


def create_user(db, username: str, hash_value: str, hash_format: int) -> int:
    """Insert a new user and return their id."""
    cur = db.execute(
        "INSERT INTO {table} (username, hash_value, hash_format) VALUES (?, ?, ?)",
        (username, hash_value, hash_format),
    )
    db.commit()
    return cur.lastrowid
'''

        # Pre-compute legacy hashes for conftest
        # Format 0: plain MD5
        md5_hash = "md5:" + hashlib.md5(test_password.encode()).hexdigest()

        # Format 1: salted MD5 with hex-encoded salt
        salt_bytes = bytes.fromhex(hex_salt)
        salted_hash_hex = hashlib.md5(salt_bytes + test_password.encode()).hexdigest()
        md5s_hash = f"md5s:{hex_salt}:{salted_hash_hex}"

        # Format 2: SHA256-HMAC with base64-encoded salt
        mac = hmac_mod.new(hmac_salt, test_password.encode(), hashlib.sha256).digest()
        b64_salt = base64.b64encode(hmac_salt).decode()
        b64_mac = base64.b64encode(mac).decode()
        sha256h_hash = f"sha256h:{b64_salt}:{b64_mac}"

        # --- tests/__init__.py ---
        files["tests/__init__.py"] = ""

        # --- tests/conftest.py ---
        files["tests/conftest.py"] = f'''"""Test fixtures for CRYPTO4 — pre-populated users in all 3 legacy formats."""
import pytest
import hashlib
import hmac
import base64
import sqlite3


PASSWORD = "{test_password}"


@pytest.fixture
def db():
    conn = sqlite3.connect(":memory:")
    conn.execute("""
        CREATE TABLE {table} (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            hash_value TEXT,
            hash_format INTEGER
        )
    """)

    # Format 0: Plain MD5
    md5_hash = "md5:" + hashlib.md5(PASSWORD.encode()).hexdigest()
    conn.execute(
        "INSERT INTO {table} VALUES (1, '{user_prefix}_md5', ?, 0)",
        (md5_hash,),
    )

    # Format 1: Salted MD5 (HEX-encoded salt — NOT base64)
    salt_hex = "{hex_salt}"
    salt_bytes = bytes.fromhex(salt_hex)
    salted_hash = hashlib.md5(salt_bytes + PASSWORD.encode()).hexdigest()
    md5s_hash = f"md5s:{{salt_hex}}:{{salted_hash}}"
    conn.execute(
        "INSERT INTO {table} VALUES (2, '{user_prefix}_salted', ?, 1)",
        (md5s_hash,),
    )

    # Format 2: SHA256-HMAC (BASE64-encoded salt)
    hmac_salt = {hmac_salt!r}
    mac = hmac.new(hmac_salt, PASSWORD.encode(), hashlib.sha256).digest()
    sha_hash = f"sha256h:{{base64.b64encode(hmac_salt).decode()}}:{{base64.b64encode(mac).decode()}}"
    conn.execute(
        "INSERT INTO {table} VALUES (3, '{user_prefix}_sha256', ?, 2)",
        (sha_hash,),
    )

    conn.commit()
    yield conn
    conn.close()
'''

        # --- tests/test_new_users.py ---
        files["tests/test_new_users.py"] = f'''"""Test that new registrations produce Argon2id hashes."""
import sys
sys.path.insert(0, '.')

from auth_system.hasher import hash_password
from auth_system.formats import ARGON2ID


def test_new_user_hash_is_argon2id():
    h, fmt = hash_password("somenewpassword")
    assert fmt == ARGON2ID, f"Expected format 3 (Argon2id), got {{fmt}}"
    assert h.startswith("argon2:"), f"Expected argon2: prefix, got {{h[:30]}}"


def test_new_user_hash_not_md5():
    h, fmt = hash_password("anotherpassword")
    assert not h.startswith("md5:"), "New hashes must not use plain MD5"
    assert not h.startswith("md5s:"), "New hashes must not use salted MD5"


def test_new_user_argon2id_verifiable():
    import argon2
    password = "verifiablepassword"
    h, fmt = hash_password(password)
    ph = argon2.PasswordHasher()
    assert ph.verify(h.removeprefix("argon2:"), password), "New Argon2id hash must be self-verifiable"
'''

        # --- tests/test_legacy_md5.py ---
        files["tests/test_legacy_md5.py"] = f'''"""Test Format 0 (plain MD5) backward compatibility."""
import sys
sys.path.insert(0, '.')

from auth_system.verifier import verify_password
from auth_system.formats import PLAIN_MD5

PASSWORD = "{test_password}"


def test_format0_correct_password(db):
    row = db.execute(
        "SELECT hash_value, hash_format FROM {table} WHERE username='{user_prefix}_md5'"
    ).fetchone()
    stored_hash, fmt = row
    assert verify_password(PASSWORD, stored_hash, fmt), "Format 0 correct password must pass"


def test_format0_wrong_password(db):
    row = db.execute(
        "SELECT hash_value, hash_format FROM {table} WHERE username='{user_prefix}_md5'"
    ).fetchone()
    stored_hash, fmt = row
    assert not verify_password("wrongpassword", stored_hash, fmt), "Format 0 wrong password must fail"
'''

        # --- tests/test_legacy_salted.py ---
        files["tests/test_legacy_salted.py"] = f'''"""Test Format 1 (salted MD5, HEX salt) backward compatibility."""
import sys
sys.path.insert(0, '.')

from auth_system.verifier import verify_password
from auth_system.formats import SALTED_MD5

PASSWORD = "{test_password}"


def test_format1_correct_password(db):
    """Format 1 uses hex-encoded salt — verifier must use bytes.fromhex(), not base64."""
    row = db.execute(
        "SELECT hash_value, hash_format FROM {table} WHERE username='{user_prefix}_salted'"
    ).fetchone()
    stored_hash, fmt = row
    assert verify_password(PASSWORD, stored_hash, fmt), (
        "Format 1 (hex-salt) correct password must pass. "
        "Check that verifier uses bytes.fromhex() not base64.b64decode() for format 1 salt."
    )


def test_format1_wrong_password(db):
    row = db.execute(
        "SELECT hash_value, hash_format FROM {table} WHERE username='{user_prefix}_salted'"
    ).fetchone()
    stored_hash, fmt = row
    assert not verify_password("wrongpassword", stored_hash, fmt), "Format 1 wrong password must fail"
'''

        # --- tests/test_legacy_sha256.py ---
        files["tests/test_legacy_sha256.py"] = f'''"""Test Format 2 (SHA256-HMAC, base64 salt) backward compatibility."""
import sys
sys.path.insert(0, '.')

from auth_system.verifier import verify_password
from auth_system.formats import SHA256_HMAC

PASSWORD = "{test_password}"


def test_format2_correct_password(db):
    row = db.execute(
        "SELECT hash_value, hash_format FROM {table} WHERE username='{user_prefix}_sha256'"
    ).fetchone()
    stored_hash, fmt = row
    assert verify_password(PASSWORD, stored_hash, fmt), "Format 2 (SHA256-HMAC) correct password must pass"


def test_format2_wrong_password(db):
    row = db.execute(
        "SELECT hash_value, hash_format FROM {table} WHERE username='{user_prefix}_sha256'"
    ).fetchone()
    stored_hash, fmt = row
    assert not verify_password("wrongpassword", stored_hash, fmt), "Format 2 wrong password must fail"
'''

        # --- tests/test_upgrade.py ---
        files["tests/test_upgrade.py"] = f'''"""Test transparent hash upgrade on login."""
import sys
sys.path.insert(0, '.')

from auth_system.verifier import verify_password
from auth_system.migrator import upgrade_hash
from auth_system.formats import ARGON2ID

PASSWORD = "{test_password}"


def test_format_marker_updated_after_upgrade(db):
    """Bug: upgrade writes new hash but doesn\'t update format marker column."""
    row = db.execute(
        "SELECT id, hash_value, hash_format FROM {table} WHERE username=\'{user_prefix}_md5\'"
    ).fetchone()
    user_id, stored_hash, fmt = row
    assert verify_password(PASSWORD, stored_hash, fmt), "Pre-condition: format 0 login must work"

    upgrade_hash(user_id, PASSWORD, db)

    row_after = db.execute(
        "SELECT hash_value, hash_format FROM {table} WHERE id=?", (user_id,)
    ).fetchone()
    new_hash, new_fmt = row_after
    assert new_hash.startswith("argon2:"), f"Upgraded hash must be argon2: prefix, got {{new_hash[:30]}}"
    assert new_fmt == ARGON2ID, (
        f"hash_format must be updated to {{ARGON2ID}} (Argon2id) after upgrade, got {{new_fmt}}. "
        "Fix: UPDATE both hash_value AND hash_format in migrator.py."
    )


def test_second_login_after_upgrade(db):
    """After upgrade, second login must succeed using Argon2id verification."""
    row = db.execute(
        "SELECT id, hash_value, hash_format FROM {table} WHERE username=\'{user_prefix}_md5\'"
    ).fetchone()
    user_id, stored_hash, fmt = row

    upgrade_hash(user_id, PASSWORD, db)

    row_after = db.execute(
        "SELECT hash_value, hash_format FROM {table} WHERE id=?", (user_id,)
    ).fetchone()
    new_hash, new_fmt = row_after
    assert verify_password(PASSWORD, new_hash, new_fmt), (
        f"Second login must succeed after upgrade. "
        f"Got fmt={{new_fmt}}, hash={{new_hash[:30]}}"
    )


def test_salted_md5_upgrade(db):
    """Format 1 users can also be upgraded."""
    row = db.execute(
        "SELECT id, hash_value, hash_format FROM {table} WHERE username=\'{user_prefix}_salted\'"
    ).fetchone()
    user_id, stored_hash, fmt = row
    assert verify_password(PASSWORD, stored_hash, fmt), "Pre-condition: format 1 login must work"

    upgrade_hash(user_id, PASSWORD, db)

    row_after = db.execute(
        "SELECT hash_value, hash_format FROM {table} WHERE id=?", (user_id,)
    ).fetchone()
    new_hash, new_fmt = row_after
    assert new_fmt == ARGON2ID, f"Format 1 user hash_format must be Argon2id after upgrade, got {{new_fmt}}"
    assert verify_password(PASSWORD, new_hash, new_fmt), "Second login after format 1 upgrade must succeed"
'''

        # --- tests/test_format_detect.py ---
        files["tests/test_format_detect.py"] = f'''"""Test hash format detection for all 4 formats."""
import sys
sys.path.insert(0, '.')

import pytest
from auth_system.formats import detect_format, PLAIN_MD5, SALTED_MD5, SHA256_HMAC, ARGON2ID


def test_detect_plain_md5():
    assert detect_format("md5:5f4dcc3b5aa765d61d8327deb882cf99") == PLAIN_MD5


def test_detect_salted_md5():
    assert detect_format("md5s:deadbeef:5f4dcc3b5aa765d61d8327deb882cf99") == SALTED_MD5


def test_detect_sha256_hmac():
    assert detect_format("sha256h:dGVzdA==:abc123==") == SHA256_HMAC


def test_detect_argon2id():
    assert detect_format("argon2:$argon2id$v=19$m=65536,t=2,p=1$abc$def") == ARGON2ID


def test_unknown_format_raises():
    with pytest.raises(ValueError):
        detect_format("bcrypt:$2b$12$...")


def test_all_formats_from_db(db):
    """Detect formats from actual database entries."""
    rows = db.execute(
        "SELECT hash_value, hash_format FROM {table}"
    ).fetchall()
    for stored_hash, stored_fmt in rows:
        detected = detect_format(stored_hash)
        assert detected == stored_fmt, (
            f"detect_format({{stored_hash[:30]}}) returned {{detected}}, expected {{stored_fmt}}"
        )
'''

        return files
