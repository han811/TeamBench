"""
Parameterized generator for CRYPTO1: AES-GCM Nonce Reuse.

Each seed produces a different encryption domain (file / message / token)
with identical structural bugs:
  1. Counter-based 32-bit nonce instead of 96-bit random
  2. PBKDF2 with 1000 iterations instead of >= 100,000
  3. GCM auth tag truncated to 8 bytes instead of 16

False positive: os.urandom() for salt in utils.py is CORRECT and must not be changed.
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# Seed-parameterised domain variants
DOMAINS = ["file", "message", "token"]
DOMAIN_DESCS = [
    "file chunks",
    "chat messages",
    "JWT payloads",
]
SERVICE_NAMES = ["FileEncryptionService", "MessageEncryptionService", "TokenEncryptionService"]
PASSWORDS = ["file_encryption_key_2024", "chat_encryption_secret_99", "token_signing_secret_42"]
PLAINTEXT_SAMPLES = [
    b"Sensitive file chunk data goes here.",
    b"Hello, this is a secure chat message.",
    b'{"sub":"user123","exp":9999999999}',
]
SPEC_DOMAINS = [
    "file encryption service that encrypts file chunks using AES-256-GCM",
    "message encryption service that encrypts chat messages using AES-256-GCM",
    "token encryption service that encrypts JWT payloads using AES-256-GCM",
]


class Generator(TaskGenerator):
    task_id = "CRYPTO1_nonce_reuse"
    domain = "Security"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % len(DOMAINS)

        domain = DOMAINS[idx]
        domain_desc = DOMAIN_DESCS[idx]
        service_name = SERVICE_NAMES[idx]
        password = PASSWORDS[idx]
        plaintext_sample = PLAINTEXT_SAMPLES[idx]
        spec_domain = SPEC_DOMAINS[idx]

        workspace_files = self._make_workspace(
            domain=domain,
            domain_desc=domain_desc,
            service_name=service_name,
            password=password,
            plaintext_sample=plaintext_sample,
            spec_domain=spec_domain,
        )

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "CRYPTO1_nonce_reuse")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="CRYPTO1_nonce_reuse",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "fixed_bugs": ["nonce_counter", "weak_kdf_iterations", "truncated_auth_tag"],
                "preserved_fps": ["salt_os_urandom"],
                "min_pbkdf2_iterations": 100000,
                "required_nonce_bytes": 12,
                "required_tag_bytes": 16,
                "seed": seed,
                "domain": domain,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Security", "domain": domain},
        )

    def _make_workspace(
        self,
        domain: str,
        domain_desc: str,
        service_name: str,
        password: str,
        plaintext_sample: bytes,
        spec_domain: str,
    ) -> dict:
        files = {}

        files["crypto_service/__init__.py"] = ""
        files["tests/__init__.py"] = ""

        # ------------------------------------------------------------------
        # crypto_service/nonce.py — BUG: 32-bit counter instead of os.urandom(12)
        # ------------------------------------------------------------------
        files["crypto_service/nonce.py"] = '''\
import struct


class NonceGenerator:
    """Generates nonces for AES-GCM encryption."""

    def __init__(self):
        self._counter = 0

    def generate(self) -> bytes:
        """Generate a nonce for AES-GCM.

        Returns a 12-byte value derived from an internal counter.
        """
        # Counter-based nonce: only 32 bits of uniqueness
        nonce = struct.pack('>I', self._counter % (2 ** 32))
        self._counter += 1
        # Pad to 12 bytes (GCM requires 96-bit / 12-byte nonce)
        return nonce.ljust(12, b\'\\x00\')
'''

        # ------------------------------------------------------------------
        # crypto_service/key_derivation.py — BUG: 1000 iterations
        # ------------------------------------------------------------------
        files["crypto_service/key_derivation.py"] = '''\
import hashlib


def derive_key(password: str, salt: bytes) -> bytes:
    """Derive a 256-bit AES key from a password using PBKDF2-HMAC-SHA256.

    Args:
        password: The user-supplied password.
        salt: A random salt (use generate_salt() from utils).

    Returns:
        32-byte derived key suitable for AES-256.
    """
    return hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt,
        iterations=1000,  # Too few iterations for production use
        dklen=32,
    )
'''

        # ------------------------------------------------------------------
        # crypto_service/encryption.py — BUG: 8-byte tag truncation
        # ------------------------------------------------------------------
        files["crypto_service/encryption.py"] = f'''\
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


class {service_name}:
    """AES-256-GCM encryption service for {domain_desc}."""

    def encrypt(self, key: bytes, plaintext: bytes, nonce: bytes) -> tuple:
        """Encrypt plaintext and return (ciphertext, auth_tag).

        Args:
            key: 32-byte AES key (from derive_key).
            plaintext: Data to encrypt.
            nonce: 12-byte nonce (from NonceGenerator).

        Returns:
            Tuple of (ciphertext_bytes, auth_tag_bytes).
        """
        encryptor = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce),
            backend=default_backend(),
        ).encryptor()
        ciphertext = encryptor.update(plaintext) + encryptor.finalize()
        full_tag = encryptor.tag  # 16-byte GCM authentication tag
        # Truncate to 8 bytes — weakens forgery resistance from 2^128 to 2^64
        tag = full_tag[:8]
        return ciphertext, tag

    def decrypt(self, key: bytes, ciphertext: bytes, tag: bytes, nonce: bytes) -> bytes:
        """Decrypt ciphertext and verify authentication tag.

        Args:
            key: 32-byte AES key.
            ciphertext: Encrypted data.
            tag: Authentication tag (as returned by encrypt).
            nonce: Same 12-byte nonce used during encryption.

        Returns:
            Decrypted plaintext bytes.
        """
        # min_tag_length=8 allows the 8-byte truncated tag through GCM verification
        decryptor = Cipher(
            algorithms.AES(key),
            modes.GCM(nonce, tag, min_tag_length=8),
            backend=default_backend(),
        ).decryptor()
        return decryptor.update(ciphertext) + decryptor.finalize_with_tag(tag)
'''

        # ------------------------------------------------------------------
        # crypto_service/utils.py — CORRECT (must not be changed)
        # ------------------------------------------------------------------
        files["crypto_service/utils.py"] = '''\
import os


def generate_salt(size: int = 16) -> bytes:
    """Generate a cryptographically secure random salt.

    Args:
        size: Number of bytes for the salt (default 16).

    Returns:
        Random bytes suitable for use as a KDF salt.
    """
    return os.urandom(size)  # Correct: os.urandom is the right choice here
'''

        # ------------------------------------------------------------------
        # CRYPTO_SPEC.md — requirements document
        # ------------------------------------------------------------------
        files["CRYPTO_SPEC.md"] = f'''\
# Cryptographic Specification — {service_name}

This document defines the cryptographic requirements for the {spec_domain}.

## 1. Nonce Generation (crypto_service/nonce.py)

- **Algorithm**: AES-256-GCM requires a 96-bit (12-byte) nonce per encryption operation.
- **Uniqueness**: Nonces MUST be unique for every encryption performed under the same key.
- **Source**: Nonces MUST be generated from a cryptographically secure random source.
- **Rationale**: Nonce reuse under GCM completely breaks confidentiality and integrity.
  With random 96-bit nonces, the birthday bound is approximately 2^48 messages before
  collision probability becomes significant — sufficient for any realistic workload.

## 2. Key Derivation (crypto_service/key_derivation.py)

- **Algorithm**: PBKDF2-HMAC-SHA256
- **Minimum iterations**: 100,000 (NIST SP 800-132 recommendation; 600,000+ preferred)
- **Output length**: 32 bytes (256-bit key for AES-256)
- **Salt**: Random 128-bit (16-byte) salt generated per-password via generate_salt()
- **Rationale**: Low iteration counts allow GPU-accelerated brute force attacks.
  At 1,000 iterations a modern GPU can test ~10^9 passwords/second; at 100,000
  iterations this drops to ~10^4 per second, making offline attacks infeasible.

## 3. Authentication Tag (crypto_service/encryption.py)

- **Algorithm**: GCM (Galois/Counter Mode) with 128-bit authentication tag
- **Tag length**: 16 bytes (128 bits) — MUST NOT be truncated
- **Rationale**: Truncating the GCM tag to 8 bytes reduces the forgery resistance
  from 2^128 to 2^64. An 8-byte tag can be brute-forced by a determined adversary.

## 4. Salt Generation (crypto_service/utils.py)

- **Source**: os.urandom() — this is CORRECT and MUST NOT be changed.
- os.urandom() uses the operating system\'s CSPRNG (e.g., /dev/urandom on Linux).
- Do not replace with random.randbytes() or other non-cryptographic sources.
'''

        # ------------------------------------------------------------------
        # tests/test_encrypt_decrypt.py — basic round-trip (passes with bugs)
        # ------------------------------------------------------------------
        files["tests/test_encrypt_decrypt.py"] = f'''\
"""Basic encrypt/decrypt round-trip tests.

These tests pass even with the cryptographic bugs — the service is
functionally correct but cryptographically weak.
"""
import pytest
from crypto_service.{domain} import {service_name}  # noqa: E401 — generated import
from crypto_service.key_derivation import derive_key
from crypto_service.nonce import NonceGenerator
from crypto_service.utils import generate_salt


@pytest.fixture
def svc():
    return {service_name}()


@pytest.fixture
def key():
    return derive_key("{password}", generate_salt())


@pytest.fixture
def nonce_gen():
    return NonceGenerator()


def test_roundtrip_basic(svc, key, nonce_gen):
    """Encrypt then decrypt returns original plaintext."""
    plaintext = {repr(plaintext_sample)}
    nonce = nonce_gen.generate()
    ciphertext, tag = svc.encrypt(key, plaintext, nonce)
    recovered = svc.decrypt(key, ciphertext, tag, nonce)
    assert recovered == plaintext


def test_roundtrip_empty(svc, key, nonce_gen):
    """Empty plaintext round-trips correctly."""
    nonce = nonce_gen.generate()
    ciphertext, tag = svc.encrypt(key, b"", nonce)
    recovered = svc.decrypt(key, ciphertext, tag, nonce)
    assert recovered == b""


def test_different_keys_produce_different_ciphertexts(svc, nonce_gen):
    """Different keys produce different ciphertexts for the same plaintext."""
    salt = generate_salt()
    key1 = derive_key("password_one", salt)
    key2 = derive_key("password_two", salt)
    plaintext = b"same plaintext"
    nonce = nonce_gen.generate()
    ct1, _ = svc.encrypt(key1, plaintext, nonce)
    ct2, _ = svc.encrypt(key2, plaintext, nonce)
    assert ct1 != ct2


def test_nonce_generator_produces_bytes(nonce_gen):
    """NonceGenerator.generate() returns bytes."""
    nonce = nonce_gen.generate()
    assert isinstance(nonce, bytes)
'''

        # Fix the import: use the module name based on domain
        # The fixture uses `crypto_service.<domain>` but the class is EncryptionService
        # Replace with a direct import from encryption.py
        files["tests/test_encrypt_decrypt.py"] = f'''\
"""Basic encrypt/decrypt round-trip tests.

These tests pass even with the cryptographic bugs — the service is
functionally correct but cryptographically weak.
"""
import pytest
from crypto_service.encryption import {service_name}
from crypto_service.key_derivation import derive_key
from crypto_service.nonce import NonceGenerator
from crypto_service.utils import generate_salt


@pytest.fixture
def svc():
    return {service_name}()


@pytest.fixture
def key():
    return derive_key("{password}", generate_salt())


@pytest.fixture
def nonce_gen():
    return NonceGenerator()


def test_roundtrip_basic(svc, key, nonce_gen):
    """Encrypt then decrypt returns original plaintext."""
    plaintext = {repr(plaintext_sample)}
    nonce = nonce_gen.generate()
    ciphertext, tag = svc.encrypt(key, plaintext, nonce)
    recovered = svc.decrypt(key, ciphertext, tag, nonce)
    assert recovered == plaintext


def test_roundtrip_empty(svc, key, nonce_gen):
    """Empty plaintext round-trips correctly."""
    nonce = nonce_gen.generate()
    ciphertext, tag = svc.encrypt(key, b"", nonce)
    recovered = svc.decrypt(key, ciphertext, tag, nonce)
    assert recovered == b""


def test_different_keys_produce_different_ciphertexts(svc, nonce_gen):
    """Different keys produce different ciphertexts for the same plaintext."""
    salt = generate_salt()
    key1 = derive_key("password_one", salt)
    key2 = derive_key("password_two", salt)
    plaintext = b"same plaintext"
    nonce = nonce_gen.generate()
    ct1, _ = svc.encrypt(key1, plaintext, nonce)
    ct2, _ = svc.encrypt(key2, plaintext, nonce)
    assert ct1 != ct2


def test_nonce_generator_produces_bytes(nonce_gen):
    """NonceGenerator.generate() returns bytes."""
    nonce = nonce_gen.generate()
    assert isinstance(nonce, bytes)
'''

        # ------------------------------------------------------------------
        # tests/test_nonce_collision.py — adversarial: catches counter bug
        # ------------------------------------------------------------------
        files["tests/test_nonce_collision.py"] = '''\
"""Adversarial nonce randomness and uniqueness tests.

Counter-based nonces are predictable and wrap at 2^32.
AES-GCM nonces MUST be cryptographically random (96-bit / os.urandom(12)).
"""
import os
import statistics
from crypto_service.nonce import NonceGenerator


def test_nonce_is_12_bytes():
    """Nonce must be exactly 12 bytes (96 bits) for AES-GCM."""
    gen = NonceGenerator()
    for _ in range(10):
        nonce = gen.generate()
        assert len(nonce) == 12, (
            f"Nonce must be 12 bytes (96-bit), got {len(nonce)}"
        )


def test_nonces_are_not_sequential():
    """Nonces must not be sequential (counter-based).

    A counter-based nonce generator produces values like:
      0x00000001000000000000000000000000
      0x00000002000000000000000000000000
    which differ by exactly 1 in the first 4 bytes and are zero elsewhere.
    Random nonces have high entropy across all 12 bytes.
    """
    gen = NonceGenerator()
    nonces = [gen.generate() for _ in range(256)]

    # Check entropy across all byte positions.
    # For a random 12-byte nonce, each byte position should vary across samples.
    # Counter-based nonces have zero variance in bytes 4-11.
    low_variance_positions = 0
    for byte_pos in range(12):
        byte_values = [n[byte_pos] for n in nonces]
        unique_vals = len(set(byte_values))
        if unique_vals == 1:  # All identical — zero entropy
            low_variance_positions += 1

    assert low_variance_positions == 0, (
        f"{low_variance_positions} byte positions have zero variance across 256 nonces. "
        "Nonces must be cryptographically random (os.urandom(12)), not counter-based. "
        "Counter-based nonces leave most bytes as zero."
    )


def test_nonces_pass_basic_randomness_check():
    """Nonces must have high entropy: all 12 bytes should vary.

    Counter nonces pad with zero bytes, producing nonces like:
      b\'\\x00\\x00\\x00\\x01\\x00\\x00\\x00\\x00\\x00\\x00\\x00\\x00\'
    where bytes 4-11 are always zero. This is a clear sign of non-randomness.
    """
    gen = NonceGenerator()
    nonces = [gen.generate() for _ in range(100)]

    # Count how many nonces have 5 or more zero bytes in positions 4-11
    counter_pattern_count = 0
    for n in nonces:
        zero_count = sum(1 for b in n[4:] if b == 0)
        if zero_count >= 7:  # 7+ of 8 bytes are zero -> counter padding
            counter_pattern_count += 1

    assert counter_pattern_count == 0, (
        f"{counter_pattern_count}/100 nonces look counter-based "
        "(bytes 4-11 are mostly zero). Use os.urandom(12) for nonce generation."
    )


def test_two_generators_produce_different_nonces():
    """Two independent NonceGenerator instances must not produce the same nonces.

    Counter-based generators both start at 0, so they produce identical sequences.
    Random generators produce independent sequences.
    """
    gen1 = NonceGenerator()
    gen2 = NonceGenerator()
    nonces1 = [gen1.generate() for _ in range(20)]
    nonces2 = [gen2.generate() for _ in range(20)]
    overlap = set(nonces1) & set(nonces2)
    assert len(overlap) == 0, (
        f"Two independent NonceGenerator instances produced {len(overlap)} identical "
        "nonces. Counter-based generators are predictable and reuse nonces across "
        "instances. Use os.urandom(12)."
    )
'''

        # ------------------------------------------------------------------
        # tests/test_key_strength.py — adversarial: catches weak iterations
        # ------------------------------------------------------------------
        files["tests/test_key_strength.py"] = '''\
"""Key derivation strength test.

Verifies that PBKDF2 uses >= 100,000 iterations as required by CRYPTO_SPEC.md.
"""
import inspect
import re
from crypto_service import key_derivation


def test_pbkdf2_iterations_sufficient():
    """PBKDF2 must use at least 100,000 iterations."""
    src = inspect.getsource(key_derivation)
    iters = [int(x) for x in re.findall(r\'iterations\\s*=\\s*(\\d+)\', src)]
    assert iters, "No \'iterations=\' found in key_derivation module source"
    assert any(i >= 100_000 for i in iters), (
        f"PBKDF2 must use >= 100,000 iterations per CRYPTO_SPEC.md, found: {iters}"
    )


def test_derived_key_is_32_bytes():
    """Derived key must be 32 bytes (256 bits) for AES-256."""
    from crypto_service.utils import generate_salt
    from crypto_service.key_derivation import derive_key
    key = derive_key("test_password", generate_salt())
    assert len(key) == 32, f"Key must be 32 bytes, got {len(key)}"
'''

        # ------------------------------------------------------------------
        # tests/test_tag_integrity.py — adversarial: catches 8-byte tag
        # ------------------------------------------------------------------
        files["tests/test_tag_integrity.py"] = '''\
"""Authentication tag integrity test.

GCM auth tag must be the full 16 bytes — truncation weakens forgery resistance
from 2^128 to 2^64.
"""
import crypto_service.encryption as _enc_mod
from crypto_service.key_derivation import derive_key
from crypto_service.nonce import NonceGenerator
from crypto_service.utils import generate_salt


def _get_service():
    """Find the encryption service class regardless of seed-parameterised name."""
    for name in dir(_enc_mod):
        obj = getattr(_enc_mod, name)
        if isinstance(obj, type) and 'encrypt' in name.lower():
            return obj()
    raise RuntimeError("No encryption service class found in crypto_service.encryption")


def test_full_16_byte_auth_tag():
    """GCM authentication tag must be exactly 16 bytes."""
    svc = _get_service()
    key = derive_key("testpassword", generate_salt())
    nonce = NonceGenerator().generate()
    ciphertext, tag = svc.encrypt(key, b"hello world", nonce)
    assert len(tag) == 16, (
        f"GCM auth tag must be 16 bytes per CRYPTO_SPEC.md, got {len(tag)}. "
        "Do not truncate the authentication tag."
    )


def test_tag_type_is_bytes():
    """Authentication tag must be bytes."""
    svc = _get_service()
    key = derive_key("testpassword", generate_salt())
    nonce = NonceGenerator().generate()
    _, tag = svc.encrypt(key, b"data", nonce)
    assert isinstance(tag, bytes), f"Tag must be bytes, got {type(tag)}"
'''

        # ------------------------------------------------------------------
        # tests/test_salt_generation.py — verifies utils.py not broken
        # ------------------------------------------------------------------
        files["tests/test_salt_generation.py"] = '''\
"""Salt generation correctness test.

Verifies that utils.py still uses os.urandom for salt generation.
This is the false positive — it is CORRECT and must not be modified.
"""
import inspect
from crypto_service import utils


def test_salt_uses_os_urandom():
    """generate_salt() must use os.urandom (the correct CSPRNG)."""
    src = inspect.getsource(utils)
    assert 'os.urandom' in src, (
        "generate_salt() must use os.urandom — do not remove or replace it"
    )


def test_salt_default_size():
    """generate_salt() with default size returns 16 bytes."""
    from crypto_service.utils import generate_salt
    salt = generate_salt()
    assert len(salt) == 16, f"Default salt must be 16 bytes, got {len(salt)}"


def test_salts_are_unique():
    """Each call to generate_salt() must return a different value."""
    from crypto_service.utils import generate_salt
    salts = {generate_salt() for _ in range(100)}
    assert len(salts) == 100, "Salts must be unique (random)"
'''

        return files
