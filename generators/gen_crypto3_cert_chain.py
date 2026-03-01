"""
Parameterized generator for CRYPTO3: X.509 Certificate Chain Validation.

Each seed produces a different PKI context (Web PKI / Code Signing / Client Auth)
with identical structural bugs:
  1. Naive datetime in expiry check (certlib/time_utils.py)
  2. Missing Subject/Issuer name chain check (certlib/validator.py)
  3. Missing pathLenConstraint enforcement (certlib/validator.py)

False positives (must NOT be changed):
  - Self-signed root CA acceptance (correct per RFC 5280)
  - Leaf certificate key usage check (correct per RFC 5280)
"""
from __future__ import annotations

import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# Seed-parameterised PKI context variants
PKI_CONTEXTS = ["Web PKI", "Code Signing PKI", "Client Auth PKI"]
ROOT_CA_NAMES = ["Web Root CA", "Code Signing Root CA", "Enterprise Root CA"]
INTERMEDIATE_CA_NAMES = ["Web Intermediate CA", "Code Signing CA", "Department CA"]
LEAF_NAMES = ["server.example.com", "code-signing-cert", "client@corp.example.com"]
LEAF_DESCRIPTIONS = [
    "TLS server certificate for example.com",
    "Code signing certificate for software releases",
    "Client authentication certificate for corporate users",
]
PATH_LENGTH_LABELS = [
    "Web PKI chain (Root → Intermediate → Server)",
    "Code Signing chain (Root → Signing CA → Signing Cert)",
    "Client Auth chain (Enterprise → Department → Client)",
]


class Generator(TaskGenerator):
    task_id = "CRYPTO3_cert_chain"
    domain = "Security"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % len(PKI_CONTEXTS)

        pki_context = PKI_CONTEXTS[idx]
        root_ca_name = ROOT_CA_NAMES[idx]
        intermediate_ca_name = INTERMEDIATE_CA_NAMES[idx]
        leaf_name = LEAF_NAMES[idx]
        leaf_desc = LEAF_DESCRIPTIONS[idx]
        path_label = PATH_LENGTH_LABELS[idx]

        workspace_files = self._make_workspace(
            pki_context=pki_context,
            root_ca_name=root_ca_name,
            intermediate_ca_name=intermediate_ca_name,
            leaf_name=leaf_name,
            leaf_desc=leaf_desc,
            path_label=path_label,
        )

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "CRYPTO3_cert_chain")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="CRYPTO3_cert_chain",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "fixed_bugs": ["naive_datetime_expiry", "missing_issuer_subject_check", "missing_path_len_constraint"],
                "preserved_fps": ["self_signed_root_acceptance", "leaf_key_usage_check"],
                "seed": seed,
                "pki_context": pki_context,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Security", "pki_context": pki_context},
        )

    def _make_workspace(
        self,
        pki_context: str,
        root_ca_name: str,
        intermediate_ca_name: str,
        leaf_name: str,
        leaf_desc: str,
        path_label: str,
    ) -> dict:
        files = {}

        files["certlib/__init__.py"] = ""
        files["tests/__init__.py"] = ""

        # ------------------------------------------------------------------
        # certlib/exceptions.py
        # ------------------------------------------------------------------
        files["certlib/exceptions.py"] = '''\
"""Custom exceptions for certificate chain validation."""


class CertChainError(Exception):
    """Raised when certificate chain validation fails."""
    pass


class CertExpiredError(CertChainError):
    """Raised when a certificate has expired or is not yet valid."""
    pass


class CertSignatureError(CertChainError):
    """Raised when a certificate signature cannot be verified."""
    pass
'''

        # ------------------------------------------------------------------
        # certlib/constants.py
        # ------------------------------------------------------------------
        files["certlib/constants.py"] = '''\
"""OID constants for certificate extension parsing."""
from cryptography.x509.oid import ExtensionOID, NameOID

# Well-known extension OIDs
BASIC_CONSTRAINTS_OID = ExtensionOID.BASIC_CONSTRAINTS
KEY_USAGE_OID = ExtensionOID.KEY_USAGE
SUBJECT_ALT_NAME_OID = ExtensionOID.SUBJECT_ALTERNATIVE_NAME

# Name attribute OIDs
COMMON_NAME_OID = NameOID.COMMON_NAME
ORG_NAME_OID = NameOID.ORGANIZATION_NAME
'''

        # ------------------------------------------------------------------
        # certlib/crypto_ops.py — signature verification helpers
        # ------------------------------------------------------------------
        files["certlib/crypto_ops.py"] = '''\
"""Cryptographic operations for certificate chain validation."""
from cryptography.hazmat.primitives.asymmetric import padding
from certlib.exceptions import CertSignatureError


def verify_signature(cert, issuer_public_key) -> None:
    """Verify that cert was signed by the given issuer public key.

    Args:
        cert: The certificate whose signature to verify.
        issuer_public_key: The public key of the claimed issuer.

    Raises:
        CertSignatureError: If the signature is invalid.
    """
    try:
        issuer_public_key.verify(
            cert.signature,
            cert.tbs_certificate_bytes,
            padding.PKCS1v15(),
            cert.signature_hash_algorithm,
        )
    except Exception as e:
        raise CertSignatureError(f"Signature verification failed: {e}") from e
'''

        # ------------------------------------------------------------------
        # certlib/parser.py — certificate parsing helpers
        # ------------------------------------------------------------------
        files["certlib/parser.py"] = f'''\
"""Certificate parsing helpers for {pki_context}."""
from cryptography import x509
from cryptography.hazmat.primitives.serialization import Encoding


def get_subject_cn(cert) -> str:
    """Extract the Common Name from a certificate subject."""
    attrs = cert.subject.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
    if attrs:
        return attrs[0].value
    return "<no CN>"


def get_issuer_cn(cert) -> str:
    """Extract the Common Name from a certificate issuer."""
    attrs = cert.issuer.get_attributes_for_oid(x509.NameOID.COMMON_NAME)
    if attrs:
        return attrs[0].value
    return "<no CN>"


def is_ca_cert(cert) -> bool:
    """Return True if the certificate has BasicConstraints CA:True."""
    from cryptography.x509.extensions import BasicConstraints
    try:
        bc = cert.extensions.get_extension_for_class(BasicConstraints)
        return bc.value.ca
    except x509.ExtensionNotFound:
        return False


def cert_to_pem(cert) -> bytes:
    """Serialize a certificate to PEM format."""
    return cert.public_bytes(Encoding.PEM)
'''

        # ------------------------------------------------------------------
        # certlib/time_utils.py — BUG 1: local time instead of UTC
        # ------------------------------------------------------------------
        files["certlib/time_utils.py"] = '''\
"""Time utilities for certificate validity checking."""
from datetime import datetime


def is_valid_time(cert) -> bool:
    """Check if certificate is currently time-valid.

    Compares the certificate validity period against the current time.

    Args:
        cert: A cryptography.x509.Certificate object.

    Returns:
        True if the certificate is currently valid, False otherwise.
    """
    # BUG: datetime.now() returns LOCAL time, but cert.not_valid_before and
    # cert.not_valid_after store UTC (as naive datetimes in the cryptography lib).
    # In UTC-negative timezones (e.g. UTC-5), datetime.now() can be up to 12 hours
    # behind UTC, so a cert that expired an hour ago in UTC still appears valid.
    # Fix: use datetime.utcnow() to get the current time in UTC.
    now = datetime.now()
    return cert.not_valid_before <= now <= cert.not_valid_after
'''

        # ------------------------------------------------------------------
        # certlib/validator.py — BUG 2 (missing issuer check) and BUG 3 (missing pathLen)
        # ------------------------------------------------------------------
        files["certlib/validator.py"] = f'''\
"""X.509 certificate chain validator for {pki_context}.

Validates certificate chains per RFC 5280 rules.
"""
from cryptography import x509
from cryptography.x509.extensions import BasicConstraints, KeyUsage
from certlib.time_utils import is_valid_time
from certlib.crypto_ops import verify_signature
from certlib.exceptions import CertChainError, CertExpiredError


def validate_chain(chain: list) -> bool:
    """Validate a certificate chain from leaf to root.

    The chain must be ordered from leaf (index 0) to root (last index).
    Each certificate must be signed by the next certificate in the chain.

    Args:
        chain: List of certificates, leaf first, root last.

    Returns:
        True if the chain is valid.

    Raises:
        CertChainError: If any validation check fails.
    """
    if not chain:
        raise CertChainError("Empty chain")

    for i, cert in enumerate(chain):
        is_leaf = (i == 0)
        is_root = (i == len(chain) - 1)

        # Check time validity
        if not is_valid_time(cert):
            raise CertChainError(f"Certificate at position {{i}} is not time-valid")

        # Check basic constraints for non-leaf certs
        if not is_leaf:
            _check_basic_constraints(cert, depth=i - 1)

        # Check key usage for leaf cert
        if is_leaf:
            _check_leaf_key_usage(cert)

        # Verify signature chain (skip self-signed root)
        if not is_root:
            issuer_cert = chain[i + 1]
            # BUG 2: Missing Subject/Issuer name continuity check.
            # RFC 5280 requires that cert.issuer == issuer_cert.subject.
            # Without this check, a cert chain with mismatched names but valid
            # signatures (e.g., from a compromised sub-CA) would pass validation.
            # Fix: add -> if cert.issuer != issuer_cert.subject: raise CertChainError(...)
            verify_signature(cert, issuer_cert.public_key())

    return True


def _check_basic_constraints(cert, depth: int) -> None:
    """Check BasicConstraints extension for intermediate CA certificates.

    Args:
        cert: The certificate to check.
        depth: The chain depth position (0 = direct issuer of leaf).

    Raises:
        CertChainError: If BasicConstraints are invalid.
    """
    try:
        bc = cert.extensions.get_extension_for_class(BasicConstraints)
        if not bc.value.ca:
            raise CertChainError(f"Intermediate cert at depth {{depth}} is not a CA")
        # BUG 3: Missing pathLenConstraint check.
        # RFC 5280 s4.2.1.9: if pathLenConstraint is present, it limits the number
        # of intermediate CA certificates that may follow this cert in the chain.
        # A cert with pathLen=0 may only issue end-entity (leaf) certs, not other CAs.
        # Fix: add -> if bc.value.path_length is not None and depth > bc.value.path_length:
        #                 raise CertChainError(f"pathLenConstraint violated: ...")
    except x509.ExtensionNotFound:
        raise CertChainError("Missing BasicConstraints extension on CA certificate")


def _check_leaf_key_usage(cert) -> None:
    """Check leaf certificate key usage — THIS IS CORRECT per RFC 5280.

    Leaf certificates must have the digitalSignature key usage bit set.
    This function is intentionally correct — do not modify it.

    Args:
        cert: The leaf certificate to check.

    Raises:
        CertChainError: If the required key usage is absent.
    """
    try:
        ku = cert.extensions.get_extension_for_class(KeyUsage)
        if not ku.value.digital_signature:
            raise CertChainError("Leaf cert missing required digitalSignature key usage")
    except x509.ExtensionNotFound:
        raise CertChainError("Leaf cert missing required KeyUsage extension")


def is_self_signed(cert) -> bool:
    """Return True if the certificate is self-signed (issuer == subject).

    This is CORRECT per RFC 5280 — root CA certificates are self-signed
    by definition. Do not modify this function.

    Args:
        cert: The certificate to check.

    Returns:
        True if subject == issuer.
    """
    return cert.issuer == cert.subject
'''

        # ------------------------------------------------------------------
        # tests/conftest.py — generates real test certs using cryptography lib
        # ------------------------------------------------------------------
        files["tests/conftest.py"] = f'''\
"""
Test fixtures for CRYPTO3 certificate chain validation tests.

Generates real X.509 certificates dynamically using the cryptography library.
PKI context: {pki_context}
Chain: {path_label}
"""
import datetime
import pytest
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_key():
    """Generate a 2048-bit RSA key pair."""
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def make_cert(
    subject_name,
    issuer_name,
    issuer_key,
    subject_key,
    is_ca=False,
    path_length=None,
    days_valid=365,
    expired=False,
):
    """Build and sign an X.509 certificate.

    Args:
        subject_name: x509.Name for the certificate subject.
        issuer_name: x509.Name for the certificate issuer.
        issuer_key: Private key of the issuer (used for signing).
        subject_key: Private key of the subject (public key embedded).
        is_ca: Whether this is a CA certificate (BasicConstraints CA:True).
        path_length: pathLenConstraint value (None = unconstrained).
        days_valid: Validity period in days.
        expired: If True, generate an already-expired certificate.

    Returns:
        A signed cryptography.x509.Certificate object.
    """
    # Use naive UTC datetimes — cryptography lib stores validity as naive UTC.
    now = datetime.datetime.utcnow()
    if expired:
        not_before = now - datetime.timedelta(days=30)
        not_after = now - datetime.timedelta(days=1)
    else:
        not_before = now - datetime.timedelta(hours=1)
        not_after = now + datetime.timedelta(days=days_valid)

    builder = (
        x509.CertificateBuilder()
        .subject_name(subject_name)
        .issuer_name(issuer_name)
        .public_key(subject_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(not_before)
        .not_valid_after(not_after)
    )

    if is_ca:
        builder = builder.add_extension(
            x509.BasicConstraints(ca=True, path_length=path_length),
            critical=True,
        )
        builder = builder.add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
    else:
        builder = builder.add_extension(
            x509.BasicConstraints(ca=False, path_length=None),
            critical=True,
        )
        builder = builder.add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=False,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )

    return builder.sign(issuer_key, hashes.SHA256())


# ---------------------------------------------------------------------------
# Key fixtures (session-scoped for speed)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def root_key():
    return generate_key()


@pytest.fixture(scope="session")
def intermediate_key():
    return generate_key()


@pytest.fixture(scope="session")
def leaf_key():
    return generate_key()


# ---------------------------------------------------------------------------
# Name fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def root_name():
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "{root_ca_name}")])


@pytest.fixture(scope="session")
def intermediate_name():
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "{intermediate_ca_name}")])


@pytest.fixture(scope="session")
def leaf_name():
    return x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "{leaf_name}")])


# ---------------------------------------------------------------------------
# Certificate fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def root_cert(root_name, root_key):
    """Self-signed root CA with pathLen=1 (can issue one level of intermediates)."""
    return make_cert(
        root_name, root_name, root_key, root_key, is_ca=True, path_length=1
    )


@pytest.fixture(scope="session")
def intermediate_cert(intermediate_name, root_name, root_key, intermediate_key):
    """Intermediate CA cert signed by root, pathLen=0 (may only issue leaf certs)."""
    return make_cert(
        intermediate_name, root_name, root_key, intermediate_key,
        is_ca=True, path_length=0
    )


@pytest.fixture(scope="session")
def leaf_cert(leaf_name, intermediate_name, intermediate_key, leaf_key):
    """Leaf end-entity cert signed by intermediate."""
    return make_cert(
        leaf_name, intermediate_name, intermediate_key, leaf_key, is_ca=False
    )


@pytest.fixture(scope="session")
def valid_chain(leaf_cert, intermediate_cert, root_cert):
    """A complete valid certificate chain: leaf -> intermediate -> root."""
    return [leaf_cert, intermediate_cert, root_cert]


@pytest.fixture(scope="session")
def expired_leaf_cert(leaf_name, intermediate_name, intermediate_key, leaf_key):
    """A leaf cert that has already expired."""
    return make_cert(
        leaf_name, intermediate_name, intermediate_key, leaf_key,
        is_ca=False, expired=True
    )


@pytest.fixture(scope="session")
def wrong_issuer_leaf_cert(leaf_name, root_name, intermediate_key, leaf_key):
    """A leaf cert whose Issuer field claims to be the root (not intermediate),
    but is signed by intermediate_key so the signature is valid.

    The issuer name (root_name) does not match intermediate_cert.subject
    (intermediate_name), so the Subject/Issuer chain continuity check must fail.
    Without bug 2 fix, this cert passes because only the signature is verified.
    """
    # Signed by intermediate_key so signature verifies against intermediate_cert —
    # only the name continuity check (bug 2) distinguishes this as invalid.
    return make_cert(
        leaf_name, root_name, intermediate_key, leaf_key, is_ca=False
    )
'''

        # ------------------------------------------------------------------
        # tests/test_valid_chain.py
        # ------------------------------------------------------------------
        files["tests/test_valid_chain.py"] = '''\
"""Test that a valid certificate chain passes validation."""
import pytest
from certlib.validator import validate_chain


def test_valid_chain_passes(valid_chain):
    """A properly constructed chain must validate successfully."""
    result = validate_chain(valid_chain)
    assert result is True


def test_single_self_signed_cert(root_cert):
    """A chain containing only a self-signed root must pass."""
    from certlib.validator import validate_chain
    result = validate_chain([root_cert])
    assert result is True


def test_empty_chain_raises():
    """An empty chain must raise CertChainError."""
    from certlib.exceptions import CertChainError
    with pytest.raises(CertChainError):
        validate_chain([])
'''

        # ------------------------------------------------------------------
        # tests/test_expired.py
        # ------------------------------------------------------------------
        files["tests/test_expired.py"] = '''\
"""Test that expired certificates are correctly rejected.

Bug: datetime.now() uses local time instead of datetime.utcnow() (UTC).
In UTC-negative timezones, a cert that expired recently in UTC still
appears valid because local time lags behind.

The fix is to use datetime.utcnow() in certlib/time_utils.py.
"""
import datetime
import pytest
from certlib.time_utils import is_valid_time
from certlib.exceptions import CertChainError


def test_expired_cert_rejected_by_is_valid_time(expired_leaf_cert):
    """is_valid_time() must return False for a clearly expired certificate.

    The cert expired 1 day ago in UTC. Both datetime.now() and datetime.utcnow()
    should reject it, so this test passes with both buggy and fixed code.
    It confirms the basic expiry logic works.
    """
    assert is_valid_time(expired_leaf_cert) is False


def test_valid_cert_accepted_by_is_valid_time(leaf_cert):
    """is_valid_time() must return True for a currently valid certificate."""
    assert is_valid_time(leaf_cert) is True


def test_utcnow_used_not_local_time():
    """certlib/time_utils.py must use datetime.utcnow(), not datetime.now().

    datetime.now() returns local time. Certificate validity periods are stored
    in UTC. Using local time means certs that expired recently may still pass
    validation in UTC-negative timezones (e.g. a cert expiring at 01:00 UTC
    is still "valid" at 00:00 US/Eastern = 05:00 UTC-minus-5).
    """
    import inspect
    from certlib import time_utils
    src = inspect.getsource(time_utils)
    assert "utcnow" in src, (
        "certlib/time_utils.py must use datetime.utcnow() for UTC comparison. "
        "datetime.now() returns local time which differs from the UTC timestamps "
        "stored in X.509 certificates."
    )
    assert "datetime.now()" not in src.replace("datetime.utcnow()", ""), (
        "certlib/time_utils.py must not use datetime.now() (local time). "
        "Use datetime.utcnow() to compare against UTC certificate validity times."
    )


def test_expired_chain_rejected(expired_leaf_cert, intermediate_cert, root_cert):
    """A chain with an expired leaf must be rejected end-to-end (after all bugs fixed)."""
    # This test requires bugs 2 and 3 to also be fixed to reach the expiry check
    # on a chain that has correct issuer/subject names. It is informational.
    # The primary expiry test is test_expired_cert_rejected_by_is_valid_time.
    pass
'''

        # ------------------------------------------------------------------
        # tests/test_issuer_match.py
        # ------------------------------------------------------------------
        files["tests/test_issuer_match.py"] = '''\
"""Test that Subject/Issuer name chain continuity is enforced."""
import pytest
from certlib.validator import validate_chain
from certlib.exceptions import CertChainError


def test_issuer_mismatch_rejected(wrong_issuer_leaf_cert, intermediate_cert, root_cert):
    """A cert whose Issuer name does not match the next cert's Subject must be rejected.

    wrong_issuer_leaf_cert has Issuer=root_name, but intermediate_cert.subject
    is intermediate_name. The name chain is broken so validation must fail.
    """
    chain = [wrong_issuer_leaf_cert, intermediate_cert, root_cert]
    with pytest.raises(CertChainError):
        validate_chain(chain)


def test_correct_issuer_chain_passes(valid_chain):
    """A chain with correct Subject/Issuer continuity must pass."""
    result = validate_chain(valid_chain)
    assert result is True
'''

        # ------------------------------------------------------------------
        # tests/test_path_length.py
        # ------------------------------------------------------------------
        files["tests/test_path_length.py"] = f'''\
"""Test that pathLenConstraint is enforced for intermediate CA certs."""
import datetime
import pytest
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from certlib.validator import validate_chain
from certlib.exceptions import CertChainError
from tests.conftest import make_cert, generate_key


def test_path_len_violation_rejected(root_key, root_name, intermediate_key, intermediate_name):
    """intermediate_cert has pathLen=0, meaning it cannot issue CA certs.

    If we try to use it as the issuer of another CA certificate, the chain depth
    violates pathLenConstraint and must be rejected.
    """
    # intermediate has pathLen=0: may only issue leaf certs, not other CAs
    second_int_key = generate_key()
    second_int_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Second Intermediate CA")])
    leaf_key2 = generate_key()
    leaf_name2 = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "{leaf_name}-2")])

    # Build: root (pathLen=1) -> intermediate (pathLen=0) -> second_int (CA) -> leaf
    root_cert = make_cert(root_name, root_name, root_key, root_key, is_ca=True, path_length=2)
    intermediate_cert = make_cert(
        intermediate_name, root_name, root_key, intermediate_key,
        is_ca=True, path_length=0  # pathLen=0: may NOT issue CA certs
    )
    # second_int is a CA cert issued by intermediate — this violates pathLen=0
    second_int_cert = make_cert(
        second_int_name, intermediate_name, intermediate_key, second_int_key,
        is_ca=True, path_length=None
    )
    leaf_cert2 = make_cert(
        leaf_name2, second_int_name, second_int_key, leaf_key2, is_ca=False
    )

    # Chain: leaf -> second_int (CA) -> intermediate (pathLen=0 VIOLATED) -> root
    chain = [leaf_cert2, second_int_cert, intermediate_cert, root_cert]
    with pytest.raises(CertChainError):
        validate_chain(chain)


def test_path_len_within_limit_passes(root_key, root_name, intermediate_key, intermediate_name, leaf_cert, leaf_key):
    """A chain that respects pathLenConstraint must pass."""
    # intermediate has pathLen=0, and the chain only goes one level deeper (leaf)
    root_cert = make_cert(root_name, root_name, root_key, root_key, is_ca=True, path_length=1)
    intermediate_cert = make_cert(
        intermediate_name, root_name, root_key, intermediate_key,
        is_ca=True, path_length=0
    )
    # leaf_cert is not a CA, so depth=0 for intermediate — within pathLen=0 limit
    chain = [leaf_cert, intermediate_cert, root_cert]
    result = validate_chain(chain)
    assert result is True
'''

        # ------------------------------------------------------------------
        # tests/test_self_signed.py — false positive: self-signed root accepted
        # ------------------------------------------------------------------
        files["tests/test_self_signed.py"] = '''\
"""Test that self-signed root CAs are correctly accepted (false positive check).

Per RFC 5280, root CA certificates are self-signed by definition.
The validator must accept self-signed certs at the root position.
This is correct behaviour — do not change it.
"""
import pytest
from certlib.validator import validate_chain, is_self_signed
from certlib.exceptions import CertChainError


def test_self_signed_root_is_detected(root_cert):
    """is_self_signed() must return True for the root cert."""
    assert is_self_signed(root_cert) is True


def test_self_signed_root_accepted_in_chain(valid_chain):
    """A chain ending with a self-signed root must pass validation."""
    result = validate_chain(valid_chain)
    assert result is True


def test_leaf_is_not_self_signed(leaf_cert):
    """is_self_signed() must return False for a leaf cert."""
    assert is_self_signed(leaf_cert) is False


def test_intermediate_is_not_self_signed(intermediate_cert):
    """is_self_signed() must return False for an intermediate cert."""
    assert is_self_signed(intermediate_cert) is False
'''

        # ------------------------------------------------------------------
        # tests/test_key_usage.py — false positive: leaf key usage preserved
        # ------------------------------------------------------------------
        files["tests/test_key_usage.py"] = '''\
"""Test that leaf certificate key usage check is preserved (false positive check).

RFC 5280 requires leaf certs to have the digitalSignature key usage bit.
The validator correctly enforces this — do not remove or weaken it.
"""
import datetime
import pytest
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from certlib.validator import validate_chain
from certlib.exceptions import CertChainError
from tests.conftest import generate_key, make_cert


def test_leaf_without_digital_signature_rejected(
    root_key, root_name, intermediate_key, intermediate_name
):
    """A leaf cert without digitalSignature key usage must be rejected."""
    leaf_key = generate_key()
    leaf_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "no-key-usage.example.com")])

    root_cert = make_cert(root_name, root_name, root_key, root_key, is_ca=True, path_length=1)
    int_cert = make_cert(
        intermediate_name, root_name, root_key, intermediate_key, is_ca=True, path_length=0
    )

    # Build a leaf cert with no KeyUsage extension — use raw builder
    now = datetime.datetime.utcnow()
    bad_leaf = (
        x509.CertificateBuilder()
        .subject_name(leaf_name)
        .issuer_name(intermediate_name)
        .public_key(leaf_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - datetime.timedelta(hours=1))
        .not_valid_after(now + datetime.timedelta(days=365))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        # Intentionally omitting KeyUsage extension
        .sign(intermediate_key, hashes.SHA256())
    )

    chain = [bad_leaf, int_cert, root_cert]
    with pytest.raises(CertChainError, match="KeyUsage"):
        validate_chain(chain)


def test_leaf_with_digital_signature_passes(valid_chain):
    """A leaf cert with correct key usage must pass validation."""
    result = validate_chain(valid_chain)
    assert result is True
'''

        return files
