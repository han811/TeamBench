# RINC8: Memory Leak — Event Listener Leak

## Incident Background
Common production memory leak pattern documented in post-mortems at Netflix,
Cloudflare, and others. A growing data structure (event listeners) with no
eviction or cleanup causes gradual memory growth until OOM kills the process.

## Service: EventBusService
File: `service.py`

## Problem
event listeners registered but never deregistered — listener list grows without bound

The `listener count` grows without bound. Under load with 246+ unique
requests, memory usage grows proportionally with no upper bound.

**Monitoring signature:** gradual RSS/heap increase over hours/days, OOM
restarts at ~2-3x normal memory usage.

## Required Fix
return unsubscribe token from subscribe(); call unsubscribe in cleanup/teardown

Key constraint: `max_size = 100` — the data structure must not hold
more than 100 event listeners at any time.

## Acceptance Criteria
1. After 246 unique requests, `listener count` ≤ 100
2. Old entries evicted / resources released when limit reached
3. Normal functionality preserved (cache hits, queries, event delivery)
4. Concurrent usage does not cause pool exhaustion
5. Cleanup mechanism (eviction token / context manager) is implemented
6. All tests pass: `pytest test_memory.py -v`

## Files
- `service.py` — fix the memory leak
- `test_memory.py` — do NOT modify
