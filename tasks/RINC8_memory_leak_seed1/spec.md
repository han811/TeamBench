# RINC8: Memory Leak — Connection Pool Leak

## Incident Background
Common production memory leak pattern documented in post-mortems at Netflix,
Cloudflare, and others. A growing data structure (database connections) with no
eviction or cleanup causes gradual memory growth until OOM kills the process.

## Service: DatabasePoolService
File: `service.py`

## Problem
connection pool where connections are acquired but never released on error paths

The `active connections` grows without bound. Under load with 491+ unique
requests, memory usage grows proportionally with no upper bound.

**Monitoring signature:** gradual RSS/heap increase over hours/days, OOM
restarts at ~2-3x normal memory usage.

## Required Fix
use context manager (with conn_pool.get() as conn) to guarantee release on all exit paths

Key constraint: `max_size = 100` — the data structure must not hold
more than 100 database connections at any time.

## Acceptance Criteria
1. After 491 unique requests, `active connections` ≤ 100
2. Old entries evicted / resources released when limit reached
3. Normal functionality preserved (cache hits, queries, event delivery)
4. Concurrent usage does not cause pool exhaustion
5. Cleanup mechanism (eviction token / context manager) is implemented
6. All tests pass: `pytest test_memory.py -v`

## Files
- `service.py` — fix the memory leak
- `test_memory.py` — do NOT modify
