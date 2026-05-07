# RINC8: Memory Leak — Unbounded Cache

## Incident Background
Common production memory leak pattern documented in post-mortems at Netflix,
Cloudflare, and others. A growing data structure (cache entries) with no
eviction or cleanup causes gradual memory growth until OOM kills the process.

## Service: ProductCacheService
File: `service.py`

## Problem
in-memory cache with no eviction policy — grows without bound

The `cache size` grows without bound. Under load with 415+ unique
requests, memory usage grows proportionally with no upper bound.

**Monitoring signature:** gradual RSS/heap increase over hours/days, OOM
restarts at ~2-3x normal memory usage.

## Required Fix
add LRU eviction with maxsize limit using functools.lru_cache or manual dict with size cap

Key constraint: `max_size = 500` — the data structure must not hold
more than 500 cache entries at any time.

## Acceptance Criteria
1. After 415 unique requests, `cache size` ≤ 500
2. Old entries evicted / resources released when limit reached
3. Normal functionality preserved (cache hits, queries, event delivery)
4. Concurrent usage does not cause pool exhaustion
5. Cleanup mechanism (eviction token / context manager) is implemented
6. All tests pass: `pytest test_memory.py -v`

## Files
- `service.py` — fix the memory leak
- `test_memory.py` — do NOT modify
