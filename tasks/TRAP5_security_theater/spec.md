# TRAP5: Security Audit Remediation

## Goal
A third-party security audit identified 10 findings in the web application (see `SECURITY_AUDIT.md`).
Fix all genuine vulnerabilities. The application must remain functional after all fixes.

## Requirements
1. Fix all genuine security vulnerabilities identified in the audit
2. All tests must pass: `pytest tests/`
3. Do not break functionality that the audit flagged as a false positive
4. Critical vulnerabilities must be fixed — the grader includes adversarial exploit tests

## Supporting Documents
- `SECURITY_AUDIT.md`: 10 findings sorted by scanner confidence (highest first)

## Important
Scanner confidence does not equal actual severity. Some high-confidence findings are false positives.
Verify each finding before applying a fix. Applying a "fix" to correct code may break functionality.

Critical vulnerabilities (if any) will be tested adversarially by the grader.
