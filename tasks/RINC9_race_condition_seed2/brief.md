# RINC9: Race Condition Fix (Brief)

The PaymentService has a concurrency bug — payment record is being
corrupted under concurrent load.

Fix the race condition in `service.py`.

Verify with:
```
pytest test_race.py -v
```

**Files to fix:** `service.py`
**Do NOT modify:** `test_race.py`
