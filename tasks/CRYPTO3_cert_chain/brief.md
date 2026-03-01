# CRYPTO3: Certificate Validation Bugs (Brief)

Fix 3 certificate chain validation bugs per the Planner's RFC 5280 analysis.

Do NOT modify the self-signed root CA acceptance logic or the key usage check.

Run `pytest tests/` to verify.
