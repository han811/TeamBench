"""
Parameterized generator for CRYPTO2: Timing-Safe Secret Comparisons.

Each seed produces a different auth domain context (SaaS, IoT, Payment) but
the same structural challenge: 4 timing-unsafe == comparisons to fix, and 1
non-secret == comparison in users.py that must NOT be changed.

The core TNI challenge: the Planner must distinguish secret-bearing comparisons
(API keys, HMAC signatures, password hashes, session tokens) from non-secret
public-identifier comparisons (username lookup), and instruct the Executor
accordingly. Blind replacement of all == fails C6/C8.
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# Per-seed domain context
DOMAINS = ["SaaS application", "IoT device management", "Payment service"]
KEY_LABELS = ["API key", "device key", "merchant key"]
SIG_LABELS = ["webhook signature", "device signature", "payment signature"]
SERVICE_NAMES = ["AuthService", "DeviceAuth", "PaymentAuth"]
USER_FIELDS = ["username", "device_id", "merchant_id"]
USER_FIELD_DESCS = [
    "Username is a public identifier — timing differences do not leak secrets",
    "Device ID is a public identifier — timing differences do not leak secrets",
    "Merchant ID is a public identifier — timing differences do not leak secrets",
]
EXAMPLE_KEYS = [
    "saas_api_key_example_abc123",
    "iot_device_key_example_xyz789",
    "payment_merchant_key_example_def456",
]
HMAC_CONTEXTS = [
    "webhook payload",
    "device telemetry message",
    "payment request",
]


class Generator(TaskGenerator):
    task_id = "CRYPTO2_timing_safe"
    domain = "Security"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % len(DOMAINS)

        domain = DOMAINS[idx]
        key_label = KEY_LABELS[idx]
        sig_label = SIG_LABELS[idx]
        service_name = SERVICE_NAMES[idx]
        user_field = USER_FIELDS[idx]
        user_field_desc = USER_FIELD_DESCS[idx]
        example_key = EXAMPLE_KEYS[idx]
        hmac_ctx = HMAC_CONTEXTS[idx]

        workspace_files = self._make_workspace(
            domain, key_label, sig_label, service_name,
            user_field, user_field_desc, example_key, hmac_ctx,
        )

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "CRYPTO2_timing_safe")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="CRYPTO2_timing_safe",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "files_to_fix": ["auth/api_keys.py", "auth/signatures.py",
                                  "auth/passwords.py", "auth/sessions.py"],
                "file_to_preserve": "auth/users.py",
                "fix_method": "hmac.compare_digest",
                "user_field": user_field,
                "seed": seed,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Security", "domain": domain},
        )

    def _make_workspace(
        self,
        domain: str,
        key_label: str,
        sig_label: str,
        service_name: str,
        user_field: str,
        user_field_desc: str,
        example_key: str,
        hmac_ctx: str,
    ) -> dict:
        files = {}

        files["auth/__init__.py"] = ""
        files["tests/__init__.py"] = ""

        # ------------------------------------------------------------------
        # SECURITY_REQUIREMENTS.md — documents which comparisons need fixing
        # ------------------------------------------------------------------
        files["SECURITY_REQUIREMENTS.md"] = f"""\
# Security Requirements — Timing-Safe Comparisons

## Context
This {domain} performs authentication using {key_label}s, HMAC signatures,
password hashes, and session tokens.

## Timing Side-Channel Risk
String comparison with == short-circuits on the first mismatched byte.
An attacker can measure response times to determine how many leading bytes
of a secret they have correct, enabling byte-by-byte extraction.

## Comparisons Requiring Constant-Time Replacement

| File | Function | Secret Type | Action Required |
|------|----------|-------------|-----------------|
| auth/api_keys.py | validate_api_key() | {key_label} hash | Replace == with hmac.compare_digest |
| auth/signatures.py | verify_signature() | HMAC-SHA256 {sig_label} | Replace == with hmac.compare_digest |
| auth/passwords.py | check_password() | bcrypt/SHA256 password hash | Replace == with hmac.compare_digest |
| auth/sessions.py | validate_session() | Session bearer token | Replace == with hmac.compare_digest |

## Comparisons That Must NOT Be Changed

| File | Function | Field | Reason |
|------|----------|-------|--------|
| auth/users.py | find_user() | {user_field} | {user_field_desc}. This is a public data lookup, not a secret comparison. Changing it to compare_digest is security theater. |

## Summary
Fix exactly 4 comparisons. Do NOT change auth/users.py.
"""

        # ------------------------------------------------------------------
        # auth/api_keys.py — BUGGY: uses == for key hash comparison
        # ------------------------------------------------------------------
        files["auth/api_keys.py"] = f"""\
import hmac
import hashlib
import os


def generate_api_key() -> str:
    \"\"\"Generate a new random {key_label}.\"\"\"
    return os.urandom(32).hex()


def hash_api_key(key: str) -> str:
    \"\"\"Hash a {key_label} for storage.\"\"\"
    return hashlib.sha256(key.encode()).hexdigest()


def validate_api_key(provided_key: str, stored_hash: str) -> bool:
    \"\"\"Validate a provided {key_label} against its stored hash.\"\"\"
    computed = hash_api_key(provided_key)
    return computed == stored_hash  # BUG: timing-unsafe, use hmac.compare_digest
"""

        # ------------------------------------------------------------------
        # auth/signatures.py — BUGGY: uses == for HMAC comparison
        # ------------------------------------------------------------------
        files["auth/signatures.py"] = f"""\
import hmac
import hashlib


def compute_signature(payload: bytes, secret: str) -> str:
    \"\"\"Compute HMAC-SHA256 {sig_label} for a {hmac_ctx}.\"\"\"
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def verify_signature(payload: bytes, provided_signature: str, secret: str) -> bool:
    \"\"\"Verify the {sig_label} on a {hmac_ctx}.\"\"\"
    computed = compute_signature(payload, secret)
    return computed == provided_signature  # BUG: timing-unsafe, use hmac.compare_digest
"""

        # ------------------------------------------------------------------
        # auth/passwords.py — BUGGY: uses == for password hash comparison
        # ------------------------------------------------------------------
        files["auth/passwords.py"] = f"""\
import hashlib
import os


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, bytes]:
    \"\"\"Hash a password with a random salt using SHA-256.\"\"\"
    if salt is None:
        salt = os.urandom(16)
    digest = hashlib.sha256(salt + password.encode()).hexdigest()
    return digest, salt


def check_password(password: str, stored_hash: str, salt: bytes) -> bool:
    \"\"\"Check a password against its stored hash.\"\"\"
    computed, _ = hash_password(password, salt)
    return stored_hash == computed  # BUG: timing-unsafe, use hmac.compare_digest
"""

        # ------------------------------------------------------------------
        # auth/sessions.py — BUGGY: uses == for session token comparison
        # ------------------------------------------------------------------
        files["auth/sessions.py"] = f"""\
import os
import time


def generate_session_token() -> str:
    \"\"\"Generate a cryptographically random session token.\"\"\"
    return os.urandom(32).hex()


def validate_session(provided_token: str, stored_token: str) -> bool:
    \"\"\"Validate a session token for the {domain}.\"\"\"
    return stored_token == provided_token  # BUG: timing-unsafe, use hmac.compare_digest
"""

        # ------------------------------------------------------------------
        # auth/users.py — CORRECT: uses dict.get() for username lookup
        # This is a public identifier lookup — must NOT be changed.
        # ------------------------------------------------------------------
        files["auth/users.py"] = f"""\
from typing import Optional


def find_user(users_db: dict, {user_field}: str) -> Optional[dict]:
    \"\"\"Look up a user record by {user_field}.

    {user_field_desc}.
    This is a public data lookup using a plain dict get — correct as-is.
    \"\"\"
    return users_db.get({user_field})
"""

        # ------------------------------------------------------------------
        # tests/test_api_keys.py
        # ------------------------------------------------------------------
        files["tests/test_api_keys.py"] = f"""\
from auth.api_keys import generate_api_key, hash_api_key, validate_api_key


def test_valid_key_accepted():
    key = generate_api_key()
    stored = hash_api_key(key)
    assert validate_api_key(key, stored) is True


def test_wrong_key_rejected():
    key = generate_api_key()
    stored = hash_api_key(key)
    wrong_key = generate_api_key()
    assert validate_api_key(wrong_key, stored) is False


def test_empty_key_rejected():
    key = generate_api_key()
    stored = hash_api_key(key)
    assert validate_api_key("", stored) is False


def test_hash_is_deterministic():
    key = "test_{key_label.replace(' ', '_')}_abc"
    assert hash_api_key(key) == hash_api_key(key)
"""

        # ------------------------------------------------------------------
        # tests/test_signatures.py
        # ------------------------------------------------------------------
        files["tests/test_signatures.py"] = f"""\
from auth.signatures import compute_signature, verify_signature


def test_valid_signature_accepted():
    payload = b"test {hmac_ctx} data"
    secret = "shared_secret_key"
    sig = compute_signature(payload, secret)
    assert verify_signature(payload, sig, secret) is True


def test_wrong_signature_rejected():
    payload = b"test {hmac_ctx} data"
    secret = "shared_secret_key"
    assert verify_signature(payload, "deadbeef" * 8, secret) is False


def test_wrong_secret_rejected():
    payload = b"test {hmac_ctx} data"
    sig = compute_signature(payload, "correct_secret")
    assert verify_signature(payload, sig, "wrong_secret") is False


def test_tampered_payload_rejected():
    payload = b"original {hmac_ctx}"
    secret = "shared_secret_key"
    sig = compute_signature(payload, secret)
    assert verify_signature(b"tampered {hmac_ctx}", sig, secret) is False
"""

        # ------------------------------------------------------------------
        # tests/test_passwords.py
        # ------------------------------------------------------------------
        files["tests/test_passwords.py"] = """\
from auth.passwords import hash_password, check_password


def test_correct_password_accepted():
    password = "correct_horse_battery_staple"
    stored, salt = hash_password(password)
    assert check_password(password, stored, salt) is True


def test_wrong_password_rejected():
    password = "correct_horse_battery_staple"
    stored, salt = hash_password(password)
    assert check_password("wrong_password", stored, salt) is False


def test_different_salts_produce_different_hashes():
    password = "same_password"
    h1, s1 = hash_password(password)
    h2, s2 = hash_password(password)
    # Different salts → different hashes
    assert s1 != s2
    assert h1 != h2


def test_hash_with_explicit_salt():
    import os
    salt = os.urandom(16)
    password = "test_password"
    h1, _ = hash_password(password, salt)
    h2, _ = hash_password(password, salt)
    assert h1 == h2
"""

        # ------------------------------------------------------------------
        # tests/test_sessions.py
        # ------------------------------------------------------------------
        files["tests/test_sessions.py"] = """\
from auth.sessions import generate_session_token, validate_session


def test_valid_token_accepted():
    token = generate_session_token()
    assert validate_session(token, token) is True


def test_wrong_token_rejected():
    stored = generate_session_token()
    provided = generate_session_token()
    assert validate_session(provided, stored) is False


def test_tokens_are_random():
    t1 = generate_session_token()
    t2 = generate_session_token()
    assert t1 != t2


def test_token_length():
    token = generate_session_token()
    # 32 random bytes → 64 hex chars
    assert len(token) == 64
"""

        # ------------------------------------------------------------------
        # tests/test_timing.py — statistical timing variance test
        # ------------------------------------------------------------------
        files["tests/test_timing.py"] = """\
import time
import statistics
from auth.api_keys import validate_api_key, hash_api_key


def measure_validation_time(key: str, stored_hash: str, n: int = 500) -> list:
    times = []
    for _ in range(n):
        start = time.perf_counter_ns()
        validate_api_key(key, stored_hash)
        times.append(time.perf_counter_ns() - start)
    return times


def test_timing_variance_not_key_dependent():
    \"\"\"Timing should not vary significantly based on where comparison fails.\"\"\"
    key = "a" * 32
    stored = hash_api_key(key)

    # Early-mismatch key (differs at first byte of hash)
    wrong_early = "b" + "a" * 31
    times_early = measure_validation_time(wrong_early, stored)

    # Late-mismatch key (correct until last byte of hash)
    wrong_late = "a" * 31 + "b"
    times_late = measure_validation_time(wrong_late, stored)

    mean_early = statistics.mean(times_early)
    mean_late = statistics.mean(times_late)

    # If timing differs by >2x, likely has timing vulnerability
    ratio = max(mean_early, mean_late) / max(min(mean_early, mean_late), 1)
    assert ratio < 2.0, (
        f"Timing varies too much ({ratio:.2f}x): "
        f"early={mean_early:.0f}ns late={mean_late:.0f}ns — likely timing-unsafe"
    )
"""

        # ------------------------------------------------------------------
        # tests/test_no_overfix.py — verifies users.py still uses simple ==
        # ------------------------------------------------------------------
        files["tests/test_no_overfix.py"] = f"""\
import inspect
from auth import users


def test_username_lookup_uses_simple_comparison():
    \"\"\"Username lookup must NOT use hmac.compare_digest — it's security theater.\"\"\"
    src = inspect.getsource(users)
    assert 'compare_digest' not in src, (
        "auth/users.py must NOT use compare_digest — "
        "{user_field} is a public identifier, not a secret"
    )


def test_find_user_functional():
    \"\"\"find_user() must work correctly for existing and missing users.\"\"\"
    db = {{"alice": {{"{user_field}": "alice", "email": "alice@example.com"}}}}
    result = users.find_user(db, "alice")
    assert result is not None
    assert result["{user_field}"] == "alice"
    result2 = users.find_user(db, "nonexistent")
    assert result2 is None
"""

        return files
