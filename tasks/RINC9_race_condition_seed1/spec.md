# RINC9: Race Condition — File Toctou

## Incident Background
Race condition bugs have caused catastrophic failures ranging from the Therac-25
radiation overdose incidents (1985-1987) to modern payment double-charge bugs.
The common pattern: read state, make decision, act — without atomic guarantees.

## Service: FileProcessorService
File: `service.py`

## Problem
TOCTOU: check file existence then open — another process can delete between check and open

**Timing window:** Under concurrent load with 5 threads,
the race window (read-check-write gap) is exploited reliably.

## Required Fix
use atomic open-with-exclusive-lock (fcntl.flock) or rely on exception handling instead of existence check

The fix must ensure atomicity — the check and the action must happen
as a single atomic unit that no other thread can interleave.

## Acceptance Criteria
1. Concurrent process_file calls do not produce inconsistent state
2. Single process_file still works correctly
3. Invalid operations are still rejected
4. No deadlocks under concurrent load
5. Final state is consistent with the number of successful operations
6. All tests pass: `pytest test_race.py -v`

## Files
- `service.py` — fix the race condition
- `test_race.py` — do NOT modify
