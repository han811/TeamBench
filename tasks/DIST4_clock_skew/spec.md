# DIST4: Lamport Clock — Event Ordering

## Goal
Fix 3 bugs in the Lamport clock implementation that cause incorrect event ordering
across distributed nodes.

## Requirements
Per Lamport (1978) "Time, Clocks, and the Ordering of Events in a Distributed System":
1. On send: increment clock BEFORE attaching timestamp to message
   (current bug: increments after sending)
2. On receive: set clock to max(local, received) + 1
   (current bug: sets to max(local, received) without the +1)
3. Event ordering must break timestamp ties by node_id deterministically
   (current bug: no tie-breaking, causing inconsistent orderings across replicas)
4. The vector clock in `eventlog/vector_clock.py` is correct — do NOT modify it

## Supporting Documents
- `eventlog/lamport.py` — Lamport clock (all 3 bugs)
- `eventlog/ordering.py` — Event comparator (tie-breaking bug)
- `eventlog/vector_clock.py` — Vector clock (CORRECT — do not touch)
- `tests/test_vector.py` — Vector clock tests (must still pass)

## Important
The vector clock and the Lamport clock serve different purposes. The Lamport clock
provides total ordering; the vector clock provides causal dependency tracking. They
are independent — fixing Lamport bugs must not affect the vector clock.
