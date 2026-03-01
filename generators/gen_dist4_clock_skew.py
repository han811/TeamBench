"""
Parameterized generator for DIST4: Lamport Clock — Event Ordering.

Each seed produces a different distributed event log domain but the same
3 structural bugs in the Lamport clock implementation:
  Bug 1: send_event increments clock AFTER attaching timestamp (should be before)
  Bug 2: receive_event uses max(local, received) without +1
  Bug 3: EventOrderer.compare() has no node_id tie-breaking

The vector clock (VectorClock) is always correct and must not be modified.

Seeds:
  0 — Distributed audit log    (nodes: auth, api, database)
  1 — Distributed trace log    (nodes: frontend, backend, cache)
  2 — Distributed transaction  (nodes: leader, follower1, follower2)
"""
from __future__ import annotations
import json
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# Per-seed domain configuration
DOMAINS = [
    {
        "name": "audit_log",
        "description": "Distributed audit log",
        "nodes": ["auth", "api", "database"],
        "event_types": ["login", "request", "query"],
        "log_class": "AuditLog",
        "node_class": "AuditNode",
    },
    {
        "name": "trace_log",
        "description": "Distributed trace log",
        "nodes": ["frontend", "backend", "cache"],
        "event_types": ["span_start", "rpc_call", "cache_hit"],
        "log_class": "TraceLog",
        "node_class": "TraceNode",
    },
    {
        "name": "transaction_log",
        "description": "Distributed transaction log",
        "nodes": ["leader", "follower1", "follower2"],
        "event_types": ["propose", "accept", "commit"],
        "log_class": "TransactionLog",
        "node_class": "TransactionNode",
    },
]


class Generator(TaskGenerator):
    task_id = "DIST4_clock_skew"
    domain = "Distributed"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % len(DOMAINS)
        domain = DOMAINS[idx]

        workspace_files = self._make_workspace(domain, seed)

        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", "DIST4_clock_skew"
        )
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="DIST4_clock_skew",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "bugs_fixed": ["send_increment_before", "receive_max_plus_one", "ordering_tie_break"],
                "files_not_to_modify": ["eventlog/vector_clock.py"],
                "seed": seed,
                "domain": domain["name"],
                "nodes": domain["nodes"],
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Distributed"},
        )

    def _make_workspace(self, domain: dict, seed: int) -> dict:
        files = {}
        nodes = domain["nodes"]
        event_types = domain["event_types"]
        log_class = domain["log_class"]
        node_class = domain["node_class"]
        n0, n1, n2 = nodes

        files["eventlog/__init__.py"] = ""
        files["tests/__init__.py"] = ""
        files["tests/scenarios/__init__.py"] = ""

        # -----------------------------------------------------------------
        # eventlog/event.py
        # -----------------------------------------------------------------
        files["eventlog/event.py"] = '''\
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Event:
    """An event in the distributed event log."""
    timestamp: int
    node_id: str
    event_type: str
    payload: Dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"Event(ts={self.timestamp}, node={self.node_id!r}, type={self.event_type!r})"
'''

        # -----------------------------------------------------------------
        # eventlog/lamport.py — with all 3 bugs
        # -----------------------------------------------------------------
        files["eventlog/lamport.py"] = f'''\
"""
Lamport logical clock implementation.

Implements the algorithm from:
  Lamport, L. (1978). Time, clocks, and the ordering of events in a
  distributed system. Communications of the ACM, 21(7), 558-565.
"""
from eventlog.event import Event


class LamportClock:
    """Logical clock for a single node in a distributed system."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.clock = 0

    def send_event(self, event_type: str, payload: dict) -> Event:
        """
        Create a new event to send to other nodes.

        Lamport rule: increment clock, then attach new value as timestamp.
        """
        timestamp = self.clock     # BUG 1: saves value BEFORE increment
        self.clock += 1            # BUG 1: increment happens AFTER saving timestamp
        return Event(
            timestamp=timestamp,
            node_id=self.node_id,
            event_type=event_type,
            payload=payload,
        )

    def receive_event(self, event: Event) -> None:
        """
        Update clock upon receiving an event from another node.

        Lamport rule: clock = max(local_clock, received_timestamp) + 1
        """
        self.clock = max(self.clock, event.timestamp)  # BUG 2: missing + 1

    def current_time(self) -> int:
        """Return the current logical clock value."""
        return self.clock
'''

        # -----------------------------------------------------------------
        # eventlog/vector_clock.py — CORRECT, must not be changed
        # -----------------------------------------------------------------
        files["eventlog/vector_clock.py"] = '''\
"""
Vector clock for causal dependency tracking.

This implementation is correct — do NOT modify it.
"""
from collections import defaultdict
from typing import Dict


class VectorClock:
    """Vector clock for causal dependency tracking. This implementation is correct."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.clock: Dict[str, int] = defaultdict(int)

    def increment(self) -> Dict[str, int]:
        """Increment this node\'s own component and return a snapshot."""
        self.clock[self.node_id] += 1
        return dict(self.clock)

    def update(self, other_clock: Dict[str, int]) -> None:
        """Merge another node\'s vector clock (component-wise max, then increment own)."""
        for node, time in other_clock.items():
            self.clock[node] = max(self.clock[node], time)
        self.clock[self.node_id] += 1

    def happens_before(self, a: Dict[str, int], b: Dict[str, int]) -> bool:
        """Returns True if event with clock a causally precedes event with clock b."""
        all_nodes = set(a) | set(b)
        return (
            all(a.get(n, 0) <= b.get(n, 0) for n in all_nodes)
            and any(a.get(n, 0) < b.get(n, 0) for n in all_nodes)
        )

    def concurrent(self, a: Dict[str, int], b: Dict[str, int]) -> bool:
        """Returns True if neither event causally precedes the other."""
        return not self.happens_before(a, b) and not self.happens_before(b, a)
'''

        # -----------------------------------------------------------------
        # eventlog/ordering.py — with tie-breaking bug
        # -----------------------------------------------------------------
        files["eventlog/ordering.py"] = '''\
"""
Event ordering for the distributed event log.

Provides total ordering of events using Lamport timestamps.
"""
from eventlog.event import Event


class EventOrderer:
    """Orders events by Lamport timestamp."""

    def compare(self, a: Event, b: Event) -> int:
        """
        Compare two events for ordering.

        Returns negative if a < b, 0 if equal, positive if a > b.

        Lamport total ordering: timestamps define order; ties must be broken
        deterministically (e.g. by node_id) so all replicas agree.
        """
        return a.timestamp - b.timestamp  # BUG 3: no tie-breaking when timestamps equal

    def sort(self, events: list) -> list:
        """Return events sorted in Lamport total order."""
        from functools import cmp_to_key
        return sorted(events, key=cmp_to_key(self.compare))
'''

        # -----------------------------------------------------------------
        # eventlog/node.py
        # -----------------------------------------------------------------
        files["eventlog/node.py"] = f'''\
"""
A node in the distributed {domain["description"].lower()}.
Uses LamportClock for event timestamping.
"""
from typing import List
from eventlog.lamport import LamportClock
from eventlog.event import Event


class {node_class}:
    """Represents a node that participates in the distributed event log."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.clock = LamportClock(node_id)
        self.log: List[Event] = []

    def emit(self, event_type: str, payload: dict) -> Event:
        """Emit a new event and record it locally."""
        event = self.clock.send_event(event_type, payload)
        self.log.append(event)
        return event

    def receive(self, event: Event) -> None:
        """Receive an event from another node and record it."""
        self.clock.receive_event(event)
        self.log.append(event)

    def get_log(self) -> List[Event]:
        """Return all events this node has seen."""
        return list(self.log)
'''

        # -----------------------------------------------------------------
        # eventlog/network.py
        # -----------------------------------------------------------------
        files["eventlog/network.py"] = f'''\
"""
Simulated network for the distributed {domain["description"].lower()}.
Delivers events between nodes (in-process, no actual networking).
"""
from typing import Dict, List, Optional
from eventlog.node import {node_class}
from eventlog.event import Event


class SimulatedNetwork:
    """Routes events between nodes in simulation."""

    def __init__(self):
        self.nodes: Dict[str, {node_class}] = {{}}
        self.message_log: List[tuple] = []

    def add_node(self, node: {node_class}) -> None:
        self.nodes[node.node_id] = node

    def send(self, sender_id: str, receiver_id: str, event_type: str, payload: dict) -> Event:
        """Node sender_id sends an event; receiver_id receives it."""
        sender = self.nodes[sender_id]
        receiver = self.nodes[receiver_id]
        event = sender.emit(event_type, payload)
        receiver.receive(event)
        self.message_log.append((sender_id, receiver_id, event))
        return event

    def broadcast(self, sender_id: str, event_type: str, payload: dict) -> Event:
        """Sender broadcasts to all other nodes."""
        sender = self.nodes[sender_id]
        event = sender.emit(event_type, payload)
        for nid, node in self.nodes.items():
            if nid != sender_id:
                node.receive(event)
        return event

    def collect_all_events(self) -> List[Event]:
        """Collect all events seen by any node (union, deduplicated by identity)."""
        seen_ids = set()
        events = []
        for node in self.nodes.values():
            for e in node.get_log():
                eid = id(e)
                if eid not in seen_ids:
                    seen_ids.add(eid)
                    events.append(e)
        return events
'''

        # -----------------------------------------------------------------
        # tests/test_lamport.py
        # -----------------------------------------------------------------
        files["tests/test_lamport.py"] = '''\
"""Tests for LamportClock — verifies send and receive rules."""
import pytest
from eventlog.lamport import LamportClock
from eventlog.event import Event


def test_send_increments_before_use():
    """Lamport rule: increment before sending, so sent message has incremented value."""
    clock = LamportClock("node1")
    assert clock.current_time() == 0
    event = clock.send_event("test", {})
    # After send: clock should be 1, and event.timestamp should be 1 (not 0)
    assert event.timestamp == 1, (
        f"Expected timestamp=1 (incremented before use), got {event.timestamp}"
    )
    assert clock.current_time() == 1


def test_send_second_event_has_higher_timestamp():
    """Each successive send must produce a strictly higher timestamp."""
    clock = LamportClock("node1")
    e1 = clock.send_event("first", {})
    e2 = clock.send_event("second", {})
    assert e2.timestamp > e1.timestamp, (
        f"Second event timestamp {e2.timestamp} must be > first {e1.timestamp}"
    )


def test_receive_increments_to_max_plus_one():
    """Lamport receive rule: clock = max(local, received) + 1."""
    clock = LamportClock("node2")
    clock.clock = 3  # local is 3

    # Receive event with timestamp=7
    incoming = Event(timestamp=7, node_id="node1", event_type="test", payload={})
    clock.receive_event(incoming)

    # Should be max(3, 7) + 1 = 8
    assert clock.current_time() == 8, (
        f"Expected 8 (max(3,7)+1), got {clock.current_time()}"
    )


def test_receive_when_local_is_larger():
    """Even when local > received, still add 1."""
    clock = LamportClock("node2")
    clock.clock = 10  # local is 10

    incoming = Event(timestamp=3, node_id="node1", event_type="test", payload={})
    clock.receive_event(incoming)

    # Should be max(10, 3) + 1 = 11
    assert clock.current_time() == 11, (
        f"Expected 11 (max(10,3)+1), got {clock.current_time()}"
    )


def test_receive_equal_clocks():
    """When local == received, result must be max+1 = local+1."""
    clock = LamportClock("node2")
    clock.clock = 5

    incoming = Event(timestamp=5, node_id="node1", event_type="test", payload={})
    clock.receive_event(incoming)

    assert clock.current_time() == 6, (
        f"Expected 6 (max(5,5)+1), got {clock.current_time()}"
    )


def test_send_after_receive_advances_clock():
    """After receiving a high-timestamp event, next send must be even higher."""
    clock = LamportClock("node2")
    incoming = Event(timestamp=100, node_id="node1", event_type="test", payload={})
    clock.receive_event(incoming)  # clock should become 101
    event = clock.send_event("response", {})
    assert event.timestamp >= 101, (
        f"Send after receive must produce timestamp >= 101, got {event.timestamp}"
    )
'''

        # -----------------------------------------------------------------
        # tests/test_ordering.py
        # -----------------------------------------------------------------
        files["tests/test_ordering.py"] = f'''\
"""Tests for EventOrderer — verifies tie-breaking and consistent ordering."""
import pytest
from functools import cmp_to_key
from eventlog.event import Event
from eventlog.ordering import EventOrderer


def test_different_timestamps_ordered_correctly():
    """Events with different timestamps are ordered by timestamp."""
    orderer = EventOrderer()
    a = Event(timestamp=3, node_id="{n1}", event_type="x", payload={{}})
    b = Event(timestamp=7, node_id="{n0}", event_type="x", payload={{}})
    assert orderer.compare(a, b) < 0, "Lower timestamp must come first"
    assert orderer.compare(b, a) > 0, "Higher timestamp must come second"


def test_equal_timestamps_broken_by_node_id():
    """Concurrent events with same timestamp must be ordered by node_id."""
    orderer = EventOrderer()
    a = Event(timestamp=5, node_id="node_a", event_type="x", payload={{}})
    b = Event(timestamp=5, node_id="node_b", event_type="x", payload={{}})

    order_1 = orderer.compare(a, b)
    order_2 = orderer.compare(b, a)

    assert order_1 != 0, "Tie must be broken (not 0)"
    assert order_2 != 0, "Reverse comparison must also be non-zero"
    assert (order_1 > 0) != (order_2 > 0), "Orderings must be opposite (antisymmetric)"


def test_ordering_consistent_across_replicas():
    """All replicas must produce same ordering for same set of events."""
    orderer = EventOrderer()

    events = [
        Event(timestamp=3, node_id="node_c", event_type="e", payload={{}}),
        Event(timestamp=3, node_id="node_a", event_type="e", payload={{}}),
        Event(timestamp=5, node_id="node_b", event_type="e", payload={{}}),
        Event(timestamp=3, node_id="node_b", event_type="e", payload={{}}),
    ]

    # Sort twice (simulating two replicas receiving events in different orders)
    sorted1 = sorted(events, key=cmp_to_key(orderer.compare))
    sorted2 = sorted(list(reversed(events)), key=cmp_to_key(orderer.compare))

    assert [e.node_id for e in sorted1] == [e.node_id for e in sorted2], (
        "Ordering must be consistent regardless of initial input order"
    )


def test_sort_method_returns_sorted_list():
    """EventOrderer.sort() returns events in total order."""
    orderer = EventOrderer()
    events = [
        Event(timestamp=10, node_id="z", event_type="e", payload={{}}),
        Event(timestamp=2, node_id="a", event_type="e", payload={{}}),
        Event(timestamp=5, node_id="m", event_type="e", payload={{}}),
    ]
    result = orderer.sort(events)
    timestamps = [e.timestamp for e in result]
    assert timestamps == sorted(timestamps), "sort() must produce ascending timestamp order"
'''

        # -----------------------------------------------------------------
        # tests/test_causal.py
        # -----------------------------------------------------------------
        files["tests/test_causal.py"] = f'''\
"""Tests verifying causal ordering — events that causally precede must have lower timestamps."""
import pytest
from eventlog.lamport import LamportClock
from eventlog.event import Event
from eventlog.ordering import EventOrderer
from functools import cmp_to_key


def test_send_before_receive_in_causal_order():
    """
    If node A sends event e1, and node B receives it then sends e2,
    then e1 must have a lower timestamp than e2.
    """
    clock_a = LamportClock("{n0}")
    clock_b = LamportClock("{n1}")

    e1 = clock_a.send_event("{event_types[0]}", {{"data": 1}})
    clock_b.receive_event(e1)
    e2 = clock_b.send_event("{event_types[1]}", {{"data": 2}})

    assert e1.timestamp < e2.timestamp, (
        f"Causal predecessor e1.ts={{e1.timestamp}} must be < e2.ts={{e2.timestamp}}"
    )


def test_causal_chain_across_three_nodes():
    """
    A -> B -> C causal chain: each event must have strictly higher timestamp.
    """
    clock_a = LamportClock("{n0}")
    clock_b = LamportClock("{n1}")
    clock_c = LamportClock("{n2}")

    ea = clock_a.send_event("{event_types[0]}", {{}})
    clock_b.receive_event(ea)
    eb = clock_b.send_event("{event_types[1]}", {{}})
    clock_c.receive_event(eb)
    ec = clock_c.send_event("{event_types[2]}", {{}})

    assert ea.timestamp < eb.timestamp < ec.timestamp, (
        f"Causal chain violated: {{ea.timestamp}} < {{eb.timestamp}} < {{ec.timestamp}}"
    )


def test_orderer_respects_causal_order():
    """EventOrderer must place causally prior events before causally later ones."""
    clock_a = LamportClock("{n0}")
    clock_b = LamportClock("{n1}")

    e1 = clock_a.send_event("{event_types[0]}", {{}})
    clock_b.receive_event(e1)
    e2 = clock_b.send_event("{event_types[1]}", {{}})

    orderer = EventOrderer()
    result = orderer.sort([e2, e1])  # pass in reverse causal order

    assert result[0].node_id == "{n0}", (
        f"Causally first event (from {n0}) must come first in sorted order"
    )
    assert result[1].node_id == "{n1}", (
        f"Causally second event (from {n1}) must come second in sorted order"
    )
'''

        # -----------------------------------------------------------------
        # tests/test_vector.py
        # -----------------------------------------------------------------
        files["tests/test_vector.py"] = '''\
"""Tests for VectorClock — must pass unchanged (vector clock is correct)."""
import pytest
from eventlog.vector_clock import VectorClock


def test_increment_advances_own_component():
    vc = VectorClock("node1")
    snap = vc.increment()
    assert snap["node1"] == 1
    assert vc.clock["node1"] == 1


def test_increment_does_not_affect_other_nodes():
    vc = VectorClock("node1")
    vc.increment()
    assert vc.clock.get("node2", 0) == 0


def test_update_takes_component_wise_max():
    vc = VectorClock("node2")
    vc.clock["node1"] = 3
    vc.clock["node2"] = 1
    vc.update({"node1": 2, "node2": 5, "node3": 4})
    # After update: max(3,2)=3 for node1, max(1,5)=5 for node2 then +1=6, max(0,4)=4 for node3
    assert vc.clock["node1"] == 3
    assert vc.clock["node2"] == 6   # own component gets +1 after max
    assert vc.clock["node3"] == 4


def test_happens_before_causal_predecessor():
    vc = VectorClock("x")
    a = {"node1": 1, "node2": 0}
    b = {"node1": 2, "node2": 1}
    assert vc.happens_before(a, b) is True
    assert vc.happens_before(b, a) is False


def test_happens_before_equal_clocks():
    vc = VectorClock("x")
    a = {"node1": 1, "node2": 1}
    assert vc.happens_before(a, a) is False


def test_concurrent_events():
    vc = VectorClock("x")
    a = {"node1": 2, "node2": 0}
    b = {"node1": 0, "node2": 2}
    assert vc.concurrent(a, b) is True
    assert vc.happens_before(a, b) is False
    assert vc.happens_before(b, a) is False


def test_not_concurrent_when_one_precedes():
    vc = VectorClock("x")
    a = {"node1": 1, "node2": 0}
    b = {"node1": 1, "node2": 1}
    assert vc.concurrent(a, b) is False
'''

        # -----------------------------------------------------------------
        # tests/test_consistency.py
        # -----------------------------------------------------------------
        files["tests/test_consistency.py"] = f'''\
"""Tests verifying all replicas produce identical final ordering."""
import pytest
from functools import cmp_to_key
from eventlog.lamport import LamportClock
from eventlog.event import Event
from eventlog.ordering import EventOrderer


def _simulate_distributed_scenario(nodes_ids):
    """
    Simulate a small distributed scenario: each node emits events and
    some events are propagated to other nodes.
    Returns list of all events seen across the system.
    """
    clocks = {{nid: LamportClock(nid) for nid in nodes_ids}}
    events = []

    n0, n1, n2 = nodes_ids

    # n0 emits
    e1 = clocks[n0].send_event("evt_a", {{"seq": 1}})
    events.append(e1)

    # n2 emits independently
    e2 = clocks[n2].send_event("evt_b", {{"seq": 2}})
    events.append(e2)

    # n1 receives e1 then emits
    clocks[n1].receive_event(e1)
    e3 = clocks[n1].send_event("evt_c", {{"seq": 3}})
    events.append(e3)

    # n0 emits again
    e4 = clocks[n0].send_event("evt_d", {{"seq": 4}})
    events.append(e4)

    # n2 receives e3 then emits
    clocks[n2].receive_event(e3)
    e5 = clocks[n2].send_event("evt_e", {{"seq": 5}})
    events.append(e5)

    return events


def test_all_replicas_agree_on_ordering():
    """
    Given the same set of events, all replicas must produce identical total ordering
    regardless of the order in which they received events.
    """
    nodes_ids = ["{n0}", "{n1}", "{n2}"]
    events = _simulate_distributed_scenario(nodes_ids)

    orderer = EventOrderer()

    # Simulate 3 replicas sorting in different initial orders
    replica1 = sorted(events, key=cmp_to_key(orderer.compare))
    replica2 = sorted(list(reversed(events)), key=cmp_to_key(orderer.compare))
    shuffled = events[2:] + events[:2]
    replica3 = sorted(shuffled, key=cmp_to_key(orderer.compare))

    ids1 = [(e.timestamp, e.node_id) for e in replica1]
    ids2 = [(e.timestamp, e.node_id) for e in replica2]
    ids3 = [(e.timestamp, e.node_id) for e in replica3]

    assert ids1 == ids2, f"Replica 1 and 2 disagree: {{ids1}} vs {{ids2}}"
    assert ids1 == ids3, f"Replica 1 and 3 disagree: {{ids1}} vs {{ids3}}"


def test_ordering_is_total():
    """Every pair of events must have a strict order (no ties allowed)."""
    nodes_ids = ["{n0}", "{n1}", "{n2}"]
    events = _simulate_distributed_scenario(nodes_ids)

    orderer = EventOrderer()
    for i, a in enumerate(events):
        for j, b in enumerate(events):
            if i == j:
                continue
            cmp = orderer.compare(a, b)
            assert cmp != 0 or a is b, (
                f"Events must have strict order: "
                f"{{a}} vs {{b}} returned 0"
            )
'''

        # -----------------------------------------------------------------
        # tests/scenarios/concurrent.json
        # -----------------------------------------------------------------
        concurrent_scenario = [
            {"timestamp": 1, "node_id": n0, "event_type": event_types[0], "payload": {"seq": 1}},
            {"timestamp": 1, "node_id": n1, "event_type": event_types[1], "payload": {"seq": 2}},
            {"timestamp": 1, "node_id": n2, "event_type": event_types[2], "payload": {"seq": 3}},
            {"timestamp": 3, "node_id": n0, "event_type": event_types[0], "payload": {"seq": 4}},
        ]
        files["tests/scenarios/concurrent.json"] = json.dumps(concurrent_scenario, indent=2)

        # -----------------------------------------------------------------
        # tests/scenarios/causal_chain.json
        # -----------------------------------------------------------------
        causal_chain_scenario = [
            {"timestamp": 1, "node_id": n0, "event_type": event_types[0], "payload": {"seq": 1}, "causes": []},
            {"timestamp": 2, "node_id": n1, "event_type": event_types[1], "payload": {"seq": 2}, "causes": [0]},
            {"timestamp": 3, "node_id": n2, "event_type": event_types[2], "payload": {"seq": 3}, "causes": [1]},
        ]
        files["tests/scenarios/causal_chain.json"] = json.dumps(causal_chain_scenario, indent=2)

        return files
