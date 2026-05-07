# RINC9: Race Condition Fix (Brief)

The WalletService has a concurrency bug — wallet balance is being
corrupted under concurrent load.

Fix the race condition in `service.py`.

Verify with:
```
pytest test_race.py -v
```

**Files to fix:** `service.py`
**Do NOT modify:** `test_race.py`
