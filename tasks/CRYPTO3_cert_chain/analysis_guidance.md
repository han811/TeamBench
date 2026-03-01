# Analysis Guidance — CRYPTO3_cert_chain

## Tools to run
- `cat certlib/validator.py` — find chain continuity and pathLen bugs
- `cat certlib/time_utils.py` — find timezone bug
- `python -m pytest tests/test_valid_chain.py tests/test_self_signed.py -v`

## Bug 1: Local time in expiry check (certlib/time_utils.py)
```python
# BUGGY: datetime.now() returns local time, but cert times are UTC
def is_valid_time(cert):
    now = datetime.now()  # BUG: local time, not UTC
    return cert.not_valid_before <= now <= cert.not_valid_after
```
Fix: Use `datetime.utcnow()` to get current UTC time:
```python
def is_valid_time(cert):
    now = datetime.utcnow()  # FIXED: UTC time matches cert validity timestamps
    return cert.not_valid_before <= now <= cert.not_valid_after
```

## Bug 2: Missing Subject/Issuer chain check (certlib/validator.py)
```python
# BUGGY: verifies signature but not that Issuer == Subject of next cert
def validate_chain(chain):
    for i in range(len(chain) - 1):
        cert = chain[i]
        issuer_cert = chain[i + 1]
        # BUG: only verifies signature, not subject/issuer name match
        verify_signature(cert, issuer_cert.public_key())
```
Fix: Add subject/issuer check:
```python
if cert.issuer != issuer_cert.subject:  # Check name chain
    raise CertChainError(f"Issuer mismatch at position {i}")
```

## Bug 3: Missing pathLenConstraint (certlib/validator.py)
```python
# BUGGY: checks CA:true but not pathLenConstraint
def check_basic_constraints(cert, depth):
    bc = cert.extensions.get_extension_for_class(BasicConstraints)
    if not bc.value.ca:
        raise CertChainError("Not a CA cert")
    # BUG: doesn't check bc.value.path_length
```
Fix:
```python
if bc.value.path_length is not None and depth > bc.value.path_length:
    raise CertChainError(f"pathLenConstraint violated: depth {depth} > {bc.value.path_length}")
```

## False Positives — DO NOT CHANGE

### Self-signed root acceptance
```python
# This is CORRECT: RFC 5280 requires trusting self-signed root CAs
def is_self_signed(cert):
    return cert.issuer == cert.subject
```
The validator correctly accepts self-signed roots. Don't change this.

### Leaf key usage check
```python
# This is CORRECT: leaf certs must have digitalSignature key usage
def check_key_usage(cert, is_leaf):
    if is_leaf:
        ku = cert.extensions.get_extension_for_class(KeyUsage)
        if not ku.value.digital_signature:
            raise CertChainError("Leaf cert missing digitalSignature key usage")
```
This is correct per RFC 5280. Don't change it.

## Tell Executor
Fix only: certlib/time_utils.py (bug 1), certlib/validator.py (bugs 2 and 3).
