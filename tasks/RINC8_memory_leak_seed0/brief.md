# RINC8: Memory Leak Fix (Brief)

The ProductCacheService is leaking memory in production. Monitoring shows
cache size growing without bound, causing periodic OOM restarts.

Fix the leak in `service.py`.

Verify with:
```
pytest test_memory.py -v
```

**Files to fix:** `service.py`
**Do NOT modify:** `test_memory.py`
