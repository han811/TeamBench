# RINC3: Unsafe Deserialization Fix (Brief)

The ExpressionEvalService is processing user-provided expression data in a way
that could allow attackers to run arbitrary code on the server.

Fix the deserialization vulnerability in `app.py`.

Verify with:
```
pytest test_deser.py -v
```

**Files to fix:** `app.py`
**Do NOT modify:** `test_deser.py`
