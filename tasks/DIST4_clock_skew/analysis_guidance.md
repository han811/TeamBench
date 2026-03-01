# Analysis Guidance — DIST4_clock_skew

## Tools to run
- `cat eventlog/lamport.py` — find all 3 bugs in LamportClock class
- `cat eventlog/ordering.py` — find tie-breaking bug in EventOrderer
- `cat eventlog/vector_clock.py` — verify it's correct (do NOT change)
- `python -m pytest tests/test_lamport.py tests/test_ordering.py -v`

## The 3 Bugs

### Bug 1: Increment After Send (eventlog/lamport.py)
```python
# BUGGY: clock incremented AFTER creating message (sent message has old timestamp)
def send_event(self, event_type, payload):
    timestamp = self.clock  # BUG: use current value (pre-increment)
    self.clock += 1         # BUG: increment happens AFTER
    return Event(timestamp=timestamp, node=self.node_id, ...)
```
**Fix**: Increment FIRST, then attach:
```python
def send_event(self, event_type, payload):
    self.clock += 1  # increment first (Lamport rule: increment before send)
    return Event(timestamp=self.clock, node=self.node_id, ...)
```

### Bug 2: Missing +1 on Receive (eventlog/lamport.py)
```python
# BUGGY: max without +1 violates Lamport receive rule
def receive_event(self, event):
    self.clock = max(self.clock, event.timestamp)  # BUG: should be max(...) + 1
```
**Fix**: Add the +1:
```python
def receive_event(self, event):
    self.clock = max(self.clock, event.timestamp) + 1  # correct Lamport rule
```

### Bug 3: No Tie-Breaking in Ordering (eventlog/ordering.py)
```python
# BUGGY: only compares timestamp, no tie-breaker for concurrent events
def compare(self, a, b):
    return a.timestamp - b.timestamp  # BUG: 0 when timestamps equal (indeterminate)
```
**Fix**: Use node_id as tie-breaker:
```python
def compare(self, a, b):
    if a.timestamp != b.timestamp:
        return a.timestamp - b.timestamp
    return (a.node_id > b.node_id) - (a.node_id < b.node_id)  # lexicographic node_id
```

## The Correct Implementation (do NOT touch)
`eventlog/vector_clock.py` — VectorClock class with:
- `increment(node_id)`: increments own component
- `update(other)`: takes component-wise max of two vectors
- `happens_before(a, b)`: true if a causally precedes b
These are all correct and must not be modified.

## Tell Executor
Fix bugs in `eventlog/lamport.py` and `eventlog/ordering.py`.
Do NOT touch `eventlog/vector_clock.py`, `eventlog/network.py`, or scenario files.
