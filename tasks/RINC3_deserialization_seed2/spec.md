# RINC3: Unsafe Deserialization — EVAL

## Incident Background
Inspired by multiple CVEs involving unsafe deserialization in Python applications.
The `eval` vector allows attackers to execute arbitrary code on the server
by sending a crafted payload to the `/evaluate` endpoint.

## Service: ExpressionEvalService
File: `app.py`

## Vulnerability
**Location:** `/evaluate` route handler in `app.py`
**Unsafe operation:** `eval(expression)`
**Attack:** eval() executes arbitrary Python — attacker can read files, run subprocesses, etc.

**Concrete attack payload:**
```
POST /evaluate
expr=<malicious_expression_payload>
```
A crafted payload causes the server to execute arbitrary OS commands.

## Required Fix
replace eval() with ast.literal_eval() for untrusted expressions

Replace:
```python
eval(expression)
```
With the safe alternative that only handles data types, not code execution.

## Acceptance Criteria
1. A malicious `eval` payload does NOT execute code (no /tmp/pwned file)
2. Normal `expression` data continues to be processed correctly
3. The unsafe call `eval(expression)` no longer appears in `app.py`
4. Missing/malformed input returns 400
5. All tests pass: `pytest test_deser.py -v`

## Files
- `app.py` — fix the unsafe deserialization call
- `test_deser.py` — do NOT modify
