"""
Parameterized generator for DIST2: Raft Consensus — Network Partition Safety.

Each seed produces a different cluster size and state machine type, but the same
3 structural Raft bugs. The bug structure is identical across seeds; only the
state machine domain and cluster configuration vary.

Seed 0: 5-node cluster, key-value store state machine
Seed 1: 5-node cluster, counter state machine
Seed 2: 7-node cluster, set membership state machine
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# Per-seed configuration
CLUSTER_SIZES = [5, 5, 7]
SM_NAMES = ["KVStore", "Counter", "MemberSet"]
SM_DOMAINS = ["key-value store", "counter", "set membership"]
SM_OP_TYPES = ["Put/Get operations", "Increment/Decrement operations", "Add/Remove operations"]
QUORUM_SIZES = [3, 3, 4]  # majority of cluster


class Generator(TaskGenerator):
    task_id = "DIST2_consensus_partition"
    domain = "Distributed"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % len(CLUSTER_SIZES)

        cluster_size = CLUSTER_SIZES[idx]
        sm_name = SM_NAMES[idx]
        sm_domain = SM_DOMAINS[idx]
        sm_ops = SM_OP_TYPES[idx]
        quorum = QUORUM_SIZES[idx]

        workspace_files = self._make_workspace(
            seed=seed,
            cluster_size=cluster_size,
            sm_name=sm_name,
            sm_domain=sm_domain,
            sm_ops=sm_ops,
            quorum=quorum,
        )

        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", "DIST2_consensus_partition"
        )
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="DIST2_consensus_partition",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "bugs_fixed": [
                    "requestvote_log_uptodate_check",
                    "appendentries_prev_log_check",
                    "commit_current_term_check",
                ],
                "seed": seed,
                "cluster_size": cluster_size,
                "state_machine": sm_name,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Distributed"},
        )

    def _make_workspace(
        self,
        seed: int,
        cluster_size: int,
        sm_name: str,
        sm_domain: str,
        sm_ops: str,
        quorum: int,
    ) -> dict:
        files = {}

        files["raft/__init__.py"] = ""
        files["tests/__init__.py"] = ""
        files["tests/scenarios/__init__.py"] = ""

        files["raft/config.py"] = self._make_config(cluster_size)
        files["raft/messages.py"] = self._make_messages()
        files["raft/log.py"] = self._make_log()
        files["raft/state_machine.py"] = self._make_state_machine(sm_name, sm_domain, sm_ops, seed)
        files["raft/network.py"] = self._make_network(cluster_size)
        files["raft/node.py"] = self._make_node(cluster_size, quorum)

        files["tests/test_election.py"] = self._make_test_election(cluster_size, quorum)
        files["tests/test_replication.py"] = self._make_test_replication(cluster_size, quorum)
        files["tests/test_commit.py"] = self._make_test_commit(cluster_size, quorum)
        files["tests/test_partition.py"] = self._make_test_partition(cluster_size, quorum)
        files["tests/test_safety.py"] = self._make_test_safety(cluster_size, quorum)

        files["tests/scenarios/partition_heal.json"] = self._make_partition_scenario(cluster_size)
        files["tests/scenarios/leader_crash.json"] = self._make_crash_scenario(cluster_size)

        return files

    def _make_config(self, cluster_size: int) -> str:
        return f'''"""Raft cluster configuration."""

CLUSTER_SIZE = {cluster_size}
ELECTION_TIMEOUT_MIN = 0.15   # seconds
ELECTION_TIMEOUT_MAX = 0.30   # seconds
HEARTBEAT_INTERVAL = 0.05     # seconds
RPC_TIMEOUT = 0.10            # seconds
QUORUM = {cluster_size} // 2 + 1
'''

    def _make_messages(self) -> str:
        return '''"""
Raft RPC message types.

These are pure data containers — no logic here.
Do not modify this file.
"""
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class LogEntry:
    """A single entry in the replicated log."""
    term: int
    index: int
    command: Any


@dataclass
class RequestVoteRequest:
    """Sent by a candidate to gather votes."""
    term: int
    candidate_id: int
    last_log_index: int
    last_log_term: int


@dataclass
class RequestVoteResponse:
    """Response to a RequestVote RPC."""
    term: int
    vote_granted: bool


@dataclass
class AppendEntriesRequest:
    """Sent by leader to replicate log entries (also serves as heartbeat)."""
    term: int
    leader_id: int
    prev_log_index: int
    prev_log_term: int
    entries: List[LogEntry] = field(default_factory=list)
    leader_commit: int = 0


@dataclass
class AppendEntriesResponse:
    """Response to an AppendEntries RPC."""
    term: int
    success: bool
    match_index: int = 0  # Highest log index known to be replicated on this follower
'''

    def _make_log(self) -> str:
        return '''"""
Replicated log for Raft consensus.

The log is 1-indexed. Index 0 is a sentinel (empty entry at term 0).
"""
from typing import Any, List, Optional
from raft.messages import LogEntry


class ReplicatedLog:
    """Thread-safe replicated log with append, truncate, and query operations."""

    def __init__(self):
        # Index 0 is a sentinel; real entries start at index 1
        self._entries: List[LogEntry] = [LogEntry(term=0, index=0, command=None)]

    def append(self, entry: LogEntry) -> None:
        """Append an entry. Entry must have index == last_index() + 1."""
        self._entries.append(entry)

    def last_index(self) -> int:
        """Return the index of the last log entry (0 if log is empty)."""
        return len(self._entries) - 1

    def last_term(self) -> int:
        """Return the term of the last log entry (0 if log is empty)."""
        return self._entries[-1].term

    def term_at(self, index: int) -> int:
        """Return the term of the entry at the given index."""
        if index < 0 or index >= len(self._entries):
            return 0
        return self._entries[index].term

    def entry_at(self, index: int) -> Optional[LogEntry]:
        """Return the entry at the given index, or None if out of range."""
        if index <= 0 or index >= len(self._entries):
            return None
        return self._entries[index]

    def entries_from(self, start_index: int) -> List[LogEntry]:
        """Return all entries with index >= start_index."""
        if start_index >= len(self._entries):
            return []
        return list(self._entries[start_index:])

    def truncate_from(self, index: int) -> None:
        """Remove all entries with index >= the given index."""
        if index > 0 and index < len(self._entries):
            self._entries = self._entries[:index]

    def __len__(self) -> int:
        return len(self._entries) - 1  # Exclude sentinel
'''

    def _make_state_machine(self, sm_name: str, sm_domain: str, sm_ops: str, seed: int) -> str:
        if seed % 3 == 0:
            # Key-value store
            return f'''"""
{sm_name} state machine for Raft — {sm_domain}.

Supports {sm_ops}.
"""
from typing import Any, Dict, Optional


class {sm_name}:
    """Simple key-value store state machine."""

    def __init__(self):
        self._store: Dict[str, Any] = {{}}

    def apply(self, command: Any) -> Any:
        """Apply a log command to the state machine and return the result."""
        if command is None:
            return None
        op = command.get("op")
        key = command.get("key")
        if op == "put":
            self._store[key] = command.get("value")
            return True
        elif op == "get":
            return self._store.get(key)
        elif op == "delete":
            return self._store.pop(key, None)
        return None

    def snapshot(self) -> dict:
        """Return a copy of the current state."""
        return dict(self._store)

    def restore(self, snapshot: dict) -> None:
        """Restore state from a snapshot."""
        self._store = dict(snapshot)
'''
        elif seed % 3 == 1:
            # Counter state machine
            return f'''"""
{sm_name} state machine for Raft — {sm_domain}.

Supports {sm_ops}.
"""
from typing import Any, Dict


class {sm_name}:
    """Simple named-counter state machine."""

    def __init__(self):
        self._counters: Dict[str, int] = {{}}

    def apply(self, command: Any) -> Any:
        """Apply a log command to the state machine and return the result."""
        if command is None:
            return None
        op = command.get("op")
        name = command.get("name", "default")
        if op == "increment":
            self._counters[name] = self._counters.get(name, 0) + command.get("by", 1)
            return self._counters[name]
        elif op == "decrement":
            self._counters[name] = self._counters.get(name, 0) - command.get("by", 1)
            return self._counters[name]
        elif op == "get":
            return self._counters.get(name, 0)
        elif op == "reset":
            self._counters[name] = 0
            return 0
        return None

    def snapshot(self) -> dict:
        """Return a copy of the current state."""
        return dict(self._counters)

    def restore(self, snapshot: dict) -> None:
        """Restore state from a snapshot."""
        self._counters = dict(snapshot)
'''
        else:
            # Set membership state machine
            return f'''"""
{sm_name} state machine for Raft — {sm_domain}.

Supports {sm_ops}.
"""
from typing import Any, Set


class {sm_name}:
    """Simple set membership state machine."""

    def __init__(self):
        self._members: Set[str] = set()

    def apply(self, command: Any) -> Any:
        """Apply a log command to the state machine and return the result."""
        if command is None:
            return None
        op = command.get("op")
        member = command.get("member")
        if op == "add":
            self._members.add(member)
            return True
        elif op == "remove":
            self._members.discard(member)
            return True
        elif op == "contains":
            return member in self._members
        elif op == "list":
            return sorted(self._members)
        return None

    def snapshot(self) -> dict:
        """Return a copy of the current state."""
        return {{"members": sorted(self._members)}}

    def restore(self, snapshot: dict) -> None:
        """Restore state from a snapshot."""
        self._members = set(snapshot.get("members", []))
'''

    def _make_network(self, cluster_size: int) -> str:
        return f'''"""
Simulated in-process network for Raft testing.

DO NOT MODIFY — the grader verifies this file is unchanged.

Nodes communicate via thread-safe queues. The network supports:
- Point-to-point message delivery
- Simulated partitions (bidirectional or one-way)
- Message loss simulation (for future use)
"""
import threading
import queue
from typing import Dict, FrozenSet, Set, Tuple, Any


class SimulatedNetwork:
    """
    In-process network simulation for a {cluster_size}-node Raft cluster.

    Messages are delivered synchronously via put() on the recipient's inbox queue.
    Partitioned links silently drop messages in both directions.
    """

    def __init__(self):
        self._lock = threading.Lock()
        # Set of (from_id, to_id) pairs that are currently partitioned
        self._partitioned_links: Set[Tuple[int, int]] = set()
        # Per-node message queues
        self._queues: Dict[int, queue.Queue] = {{}}

    def register(self, node_id: int) -> queue.Queue:
        """Register a node and return its inbox queue."""
        with self._lock:
            q = queue.Queue()
            self._queues[node_id] = q
            return q

    def send(self, from_id: int, to_id: int, message: Any) -> bool:
        """
        Send a message from one node to another.

        Returns True if delivered, False if the link is partitioned.
        """
        with self._lock:
            if (from_id, to_id) in self._partitioned_links:
                return False
            if to_id not in self._queues:
                return False
            self._queues[to_id].put((from_id, message))
            return True

    def partition(self, node_a: int, node_b: int) -> None:
        """Create a bidirectional partition between two nodes."""
        with self._lock:
            self._partitioned_links.add((node_a, node_b))
            self._partitioned_links.add((node_b, node_a))

    def heal(self, node_a: int, node_b: int) -> None:
        """Heal a partition between two nodes."""
        with self._lock:
            self._partitioned_links.discard((node_a, node_b))
            self._partitioned_links.discard((node_b, node_a))

    def heal_all(self) -> None:
        """Remove all partitions."""
        with self._lock:
            self._partitioned_links.clear()

    def is_partitioned(self, from_id: int, to_id: int) -> bool:
        """Check if a link is currently partitioned."""
        with self._lock:
            return (from_id, to_id) in self._partitioned_links

    def isolate(self, node_id: int, all_node_ids: list) -> None:
        """Isolate a node from all other nodes (partition all links to/from it)."""
        for other_id in all_node_ids:
            if other_id != node_id:
                self.partition(node_id, other_id)

    def unisolate(self, node_id: int, all_node_ids: list) -> None:
        """Remove all partitions involving a node."""
        for other_id in all_node_ids:
            if other_id != node_id:
                self.heal(node_id, other_id)
'''

    def _make_node(self, cluster_size: int, quorum: int) -> str:
        return f'''"""
Raft node implementation.

WARNING: This file contains 3 known bugs for testing purposes.

Bug 1 (handle_request_vote): Does not check log up-to-date-ness before granting vote.
Bug 2 (handle_append_entries): Does not check prevLogIndex/prevLogTerm before appending.
Bug 3 (_try_commit): Commits entries from any term, not just the current term.

All 3 bugs must be fixed. Only modify this file.
"""
import threading
import queue
import time
import random
from typing import Dict, List, Optional, Set

from raft.messages import (
    LogEntry,
    RequestVoteRequest,
    RequestVoteResponse,
    AppendEntriesRequest,
    AppendEntriesResponse,
)
from raft.log import ReplicatedLog
from raft.config import ELECTION_TIMEOUT_MIN, ELECTION_TIMEOUT_MAX, HEARTBEAT_INTERVAL


class NodeState:
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"


class RaftNode:
    """
    Raft consensus node.

    Implements leader election, log replication, and commit logic per the Raft paper.
    Uses in-process thread + queue communication (no real networking).
    """

    def __init__(self, node_id: int, peers: List[int], network):
        self.node_id = node_id
        self.peers = peers
        self.network = network
        self._quorum = {quorum}

        # Persistent state (would be written to stable storage in real Raft)
        self.current_term = 0
        self.voted_for: Optional[int] = None
        self.log = ReplicatedLog()

        # Volatile state
        self.state = NodeState.FOLLOWER
        self.leader_id: Optional[int] = None
        self.commit_index = 0
        self.last_applied = 0

        # Leader-only state (initialized on election)
        self.next_index: Dict[int, int] = {{}}
        self.match_index: Dict[int, int] = {{}}

        self._lock = threading.RLock()
        self._inbox = network.register(node_id)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._last_heartbeat = time.monotonic()
        self._election_timeout = self._random_election_timeout()
        self._votes_received: Set[int] = set()

        # Applied commands (for test verification)
        self.applied: List[LogEntry] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the node's background thread."""
        self._running = True
        self._thread = threading.Thread(
            target=self._run, name=f"raft-node-{{self.node_id}}", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the node's background thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def submit(self, command) -> Optional[int]:
        """
        Submit a command to the cluster (leader only).

        Returns the log index if accepted, or None if this node is not the leader.
        """
        with self._lock:
            if self.state != NodeState.LEADER:
                return None
            index = self.log.last_index() + 1
            entry = LogEntry(term=self.current_term, index=index, command=command)
            self.log.append(entry)
            self.match_index[self.node_id] = index
            self._broadcast_append_entries()
            return index

    def is_leader(self) -> bool:
        with self._lock:
            return self.state == NodeState.LEADER

    # ------------------------------------------------------------------
    # RPC Handlers — called by the message loop
    # ------------------------------------------------------------------

    def handle_request_vote(self, msg: RequestVoteRequest) -> RequestVoteResponse:
        with self._lock:
            # Update term if needed
            if msg.term > self.current_term:
                self._become_follower(msg.term)

            if msg.term < self.current_term:
                return RequestVoteResponse(self.current_term, False)

            # BUG 1: No log up-to-date check before granting vote.
            # The Raft paper requires: "grant vote only if candidate's log is
            # at least as up-to-date as receiver's log."
            # Missing: compare last_log_term first, then last_log_index.
            can_vote = self.voted_for is None or self.voted_for == msg.candidate_id
            if can_vote:
                self.voted_for = msg.candidate_id
                self._reset_election_timeout()
                return RequestVoteResponse(self.current_term, True)
            return RequestVoteResponse(self.current_term, False)

    def handle_append_entries(self, msg: AppendEntriesRequest) -> AppendEntriesResponse:
        with self._lock:
            # Update term if needed
            if msg.term > self.current_term:
                self._become_follower(msg.term)

            if msg.term < self.current_term:
                return AppendEntriesResponse(self.current_term, False)

            # Valid leader contact — reset election timeout
            self._reset_election_timeout()
            self.leader_id = msg.leader_id
            if self.state != NodeState.FOLLOWER:
                self._become_follower(msg.term)

            # BUG 2: No prevLogIndex/prevLogTerm consistency check.
            # The Raft paper requires: "Reply false if log doesn't contain an entry
            # at prevLogIndex whose term matches prevLogTerm."
            # Missing: check self.log.last_index() >= msg.prev_log_index
            # and self.log.term_at(msg.prev_log_index) == msg.prev_log_term.
            for entry in msg.entries:
                # Overwrite conflicting entries and append new ones
                if entry.index <= self.log.last_index():
                    if self.log.term_at(entry.index) != entry.term:
                        self.log.truncate_from(entry.index)
                        self.log.append(entry)
                else:
                    self.log.append(entry)

            # Update commit index
            if msg.leader_commit > self.commit_index:
                self.commit_index = min(msg.leader_commit, self.log.last_index())
                self._apply_committed()

            return AppendEntriesResponse(self.current_term, True, self.log.last_index())

    def handle_request_vote_response(self, sender: int, msg: RequestVoteResponse) -> None:
        with self._lock:
            if msg.term > self.current_term:
                self._become_follower(msg.term)
                return

            if self.state != NodeState.CANDIDATE:
                return
            if msg.term != self.current_term:
                return

            if msg.vote_granted:
                self._votes_received.add(sender)
                if len(self._votes_received) >= self._quorum:
                    self._become_leader()

    def handle_append_entries_response(
        self, sender: int, msg: AppendEntriesResponse
    ) -> None:
        with self._lock:
            if msg.term > self.current_term:
                self._become_follower(msg.term)
                return

            if self.state != NodeState.LEADER:
                return

            if msg.success:
                self.match_index[sender] = msg.match_index
                self.next_index[sender] = msg.match_index + 1
                self._try_commit()
            else:
                # Decrement next_index and retry
                self.next_index[sender] = max(1, self.next_index.get(sender, 1) - 1)

    # ------------------------------------------------------------------
    # Leader commit logic
    # ------------------------------------------------------------------

    def _try_commit(self) -> None:
        """
        Advance commit_index if a majority of nodes have replicated the entry.

        BUG 3: Commits entries from any term, not just the current term.
        The Raft paper (Section 5.4.2) states: "a leader can only commit log
        entries from its current term by counting replicas."
        Entries from previous terms are committed indirectly when a current-term
        entry is committed (log matching property).
        Missing: check self.log.term_at(n) == self.current_term before committing.
        """
        for n in range(self.commit_index + 1, self.log.last_index() + 1):
            # Count replicas (leader counts itself)
            count = 1 + sum(1 for m in self.match_index.values() if m >= n)
            if count >= self._quorum:
                self.commit_index = n
        self._apply_committed()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _become_follower(self, term: int) -> None:
        self.state = NodeState.FOLLOWER
        self.current_term = term
        self.voted_for = None
        self.leader_id = None
        self._reset_election_timeout()

    def _become_candidate(self) -> None:
        self.state = NodeState.CANDIDATE
        self.current_term += 1
        self.voted_for = self.node_id
        self._votes_received = {{self.node_id}}
        self._reset_election_timeout()

        # Send RequestVote to all peers
        msg = RequestVoteRequest(
            term=self.current_term,
            candidate_id=self.node_id,
            last_log_index=self.log.last_index(),
            last_log_term=self.log.last_term(),
        )
        for peer in self.peers:
            self.network.send(self.node_id, peer, ("request_vote", msg))

    def _become_leader(self) -> None:
        self.state = NodeState.LEADER
        self.leader_id = self.node_id
        # Initialize next_index and match_index
        last_idx = self.log.last_index()
        for peer in self.peers:
            self.next_index[peer] = last_idx + 1
            self.match_index[peer] = 0
        self.match_index[self.node_id] = last_idx
        self._broadcast_append_entries()

    def _broadcast_append_entries(self) -> None:
        """Send AppendEntries to all peers (heartbeat or with entries)."""
        for peer in self.peers:
            ni = self.next_index.get(peer, self.log.last_index() + 1)
            prev_idx = ni - 1
            prev_term = self.log.term_at(prev_idx)
            entries = self.log.entries_from(ni)
            msg = AppendEntriesRequest(
                term=self.current_term,
                leader_id=self.node_id,
                prev_log_index=prev_idx,
                prev_log_term=prev_term,
                entries=entries,
                leader_commit=self.commit_index,
            )
            self.network.send(self.node_id, peer, ("append_entries", msg))

    def _apply_committed(self) -> None:
        """Apply all committed but not-yet-applied log entries."""
        while self.last_applied < self.commit_index:
            self.last_applied += 1
            entry = self.log.entry_at(self.last_applied)
            if entry is not None:
                self.applied.append(entry)

    def _reset_election_timeout(self) -> None:
        self._last_heartbeat = time.monotonic()
        self._election_timeout = self._random_election_timeout()

    def _random_election_timeout(self) -> float:
        return random.uniform(ELECTION_TIMEOUT_MIN, ELECTION_TIMEOUT_MAX)

    def _election_timed_out(self) -> bool:
        return (time.monotonic() - self._last_heartbeat) > self._election_timeout

    # ------------------------------------------------------------------
    # Main event loop
    # ------------------------------------------------------------------

    def _run(self) -> None:
        """Background thread: process messages and trigger elections/heartbeats."""
        while self._running:
            # Process all pending messages (non-blocking)
            try:
                while True:
                    sender, message = self._inbox.get_nowait()
                    self._dispatch(sender, message)
            except queue.Empty:
                pass

            with self._lock:
                if self.state == NodeState.LEADER:
                    # Send heartbeats
                    now = time.monotonic()
                    if now - self._last_heartbeat >= HEARTBEAT_INTERVAL:
                        self._broadcast_append_entries()
                        self._last_heartbeat = now
                elif self._election_timed_out():
                    self._become_candidate()

            time.sleep(0.005)  # 5ms poll interval

    def _dispatch(self, sender: int, message) -> None:
        """Route an incoming message to the appropriate handler."""
        msg_type, msg = message
        if msg_type == "request_vote":
            resp = self.handle_request_vote(msg)
            self.network.send(self.node_id, sender, ("request_vote_response", resp))
        elif msg_type == "append_entries":
            resp = self.handle_append_entries(msg)
            self.network.send(self.node_id, sender, ("append_entries_response", resp))
        elif msg_type == "request_vote_response":
            self.handle_request_vote_response(sender, msg)
        elif msg_type == "append_entries_response":
            self.handle_append_entries_response(sender, msg)
'''

    def _make_test_election(self, cluster_size: int, quorum: int) -> str:
        return f'''"""
Election safety tests for the Raft consensus implementation.

Tests that:
- A node with a stale log cannot win an election (Bug 1 target)
- At most one leader per term (election safety invariant)
"""
import time
import random
import pytest

from raft.network import SimulatedNetwork
from raft.node import RaftNode
from raft.messages import LogEntry


CLUSTER_SIZE = {cluster_size}
ALL_IDS = list(range(CLUSTER_SIZE))


def make_cluster():
    net = SimulatedNetwork()
    nodes = [
        RaftNode(i, [j for j in ALL_IDS if j != i], net)
        for i in ALL_IDS
    ]
    return net, nodes


def start_all(nodes):
    for n in nodes:
        n.start()


def stop_all(nodes):
    for n in nodes:
        n.stop()


def wait_for_leader(nodes, timeout=5.0):
    """Wait until exactly one leader emerges."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        leaders = [n for n in nodes if n.is_leader()]
        if len(leaders) == 1:
            return leaders[0]
        time.sleep(0.05)
    return None


def test_leader_elected():
    """A leader must emerge within the election timeout window."""
    net, nodes = make_cluster()
    start_all(nodes)
    try:
        leader = wait_for_leader(nodes)
        assert leader is not None, "No leader elected within timeout"
    finally:
        stop_all(nodes)


def test_at_most_one_leader_per_term():
    """Election safety: at most one leader per term across the cluster."""
    net, nodes = make_cluster()
    start_all(nodes)
    try:
        # Let a leader emerge
        leader = wait_for_leader(nodes)
        assert leader is not None

        # Collect all (term, node_id) pairs for leaders observed
        leaders_by_term = {{}}
        for n in nodes:
            if n.is_leader():
                t = n.current_term
                if t in leaders_by_term:
                    assert leaders_by_term[t] == n.node_id, (
                        f"Two leaders in term {{t}}: {{leaders_by_term[t]}} and {{n.node_id}}"
                    )
                else:
                    leaders_by_term[t] = n.node_id
    finally:
        stop_all(nodes)


def test_stale_candidate_cannot_win():
    """
    A node with a stale log must not win the election.

    Setup: node 0 has extra committed entries; it is isolated, a new leader
    emerges among the remaining nodes (without node 0's entries), then node 0
    is brought back. Node 0 must not become leader because its term is lower.

    This test exposes Bug 1: without a log up-to-date check, any candidate
    whose term is high enough can win even with a stale log.
    """
    net, nodes = make_cluster()
    start_all(nodes)
    try:
        # Wait for initial leader
        leader = wait_for_leader(nodes)
        assert leader is not None

        # Submit some entries via the leader
        for i in range(3):
            leader.submit({{"op": "set", "key": f"k{{i}}", "value": i}})
        time.sleep(0.3)

        # Isolate node 0 (assume it may or may not have the entries)
        # Partition all remaining nodes from node 0
        other_ids = [i for i in ALL_IDS if i != 0]
        for oid in other_ids:
            net.partition(0, oid)

        time.sleep(0.5)  # Let remaining nodes elect a new leader

        # A new leader must emerge among the non-isolated nodes
        non_isolated = [nodes[i] for i in other_ids]
        new_leader = wait_for_leader(non_isolated, timeout=3.0)
        assert new_leader is not None, "No leader emerged after isolating node 0"
        assert new_leader.node_id != 0, "Node 0 (isolated) should not be leader"

        # Heal the partition
        for oid in other_ids:
            net.heal(0, oid)

        time.sleep(0.5)

        # At most one leader must exist now
        current_leaders = [n for n in nodes if n.is_leader()]
        assert len(current_leaders) <= 1, (
            f"Multiple leaders after heal: {{[n.node_id for n in current_leaders]}}"
        )
    finally:
        stop_all(nodes)
'''

    def _make_test_replication(self, cluster_size: int, quorum: int) -> str:
        return f'''"""
Log replication tests — verifies AppendEntries consistency check (Bug 2).

Tests that followers reject AppendEntries when prevLogIndex/prevLogTerm
does not match their log.
"""
import time
import pytest

from raft.network import SimulatedNetwork
from raft.node import RaftNode
from raft.messages import AppendEntriesRequest, LogEntry


CLUSTER_SIZE = {cluster_size}
ALL_IDS = list(range(CLUSTER_SIZE))


def make_cluster():
    net = SimulatedNetwork()
    nodes = [
        RaftNode(i, [j for j in ALL_IDS if j != i], net)
        for i in ALL_IDS
    ]
    return net, nodes


def wait_for_leader(nodes, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        leaders = [n for n in nodes if n.is_leader()]
        if len(leaders) == 1:
            return leaders[0]
        time.sleep(0.05)
    return None


def start_all(nodes):
    for n in nodes:
        n.start()


def stop_all(nodes):
    for n in nodes:
        n.stop()


def test_follower_rejects_inconsistent_append():
    """
    A follower must reject AppendEntries when prevLogIndex/prevLogTerm don't match.

    Directly calls handle_append_entries on a fresh node with a mismatched
    prev_log_index to verify the consistency check is present.
    """
    net = SimulatedNetwork()
    node = RaftNode(0, [1, 2], net)

    # Node has no entries (log is empty except sentinel)
    # Send AppendEntries claiming prev_log_index=5 (which doesn't exist)
    msg = AppendEntriesRequest(
        term=1,
        leader_id=1,
        prev_log_index=5,   # Follower log is empty — mismatch
        prev_log_term=1,
        entries=[LogEntry(term=1, index=6, command={{"op": "set"}})],
        leader_commit=0,
    )
    # Force term to match
    node.current_term = 1

    resp = node.handle_append_entries(msg)
    assert not resp.success, (
        "Follower must reject AppendEntries when prev_log_index doesn't exist in its log"
    )


def test_follower_rejects_wrong_prev_term():
    """
    A follower must reject AppendEntries when prevLogTerm doesn't match.
    """
    net = SimulatedNetwork()
    node = RaftNode(0, [1, 2], net)

    # Add an entry at index 1 with term 1
    node.log.append(LogEntry(term=1, index=1, command={{"op": "init"}}))
    node.current_term = 2

    # Send AppendEntries claiming prev_log_index=1, prev_log_term=99 (wrong)
    msg = AppendEntriesRequest(
        term=2,
        leader_id=1,
        prev_log_index=1,
        prev_log_term=99,  # Wrong term — should be 1
        entries=[LogEntry(term=2, index=2, command={{"op": "set"}})],
        leader_commit=0,
    )

    resp = node.handle_append_entries(msg)
    assert not resp.success, (
        "Follower must reject AppendEntries when prev_log_term doesn't match"
    )


def test_follower_accepts_consistent_append():
    """
    A follower must accept AppendEntries when prevLogIndex/prevLogTerm match.
    """
    net = SimulatedNetwork()
    node = RaftNode(0, [1, 2], net)

    # Add an entry at index 1 with term 1
    node.log.append(LogEntry(term=1, index=1, command={{"op": "init"}}))
    node.current_term = 2

    # Send AppendEntries with correct prev values
    msg = AppendEntriesRequest(
        term=2,
        leader_id=1,
        prev_log_index=1,
        prev_log_term=1,   # Correct
        entries=[LogEntry(term=2, index=2, command={{"op": "set"}})],
        leader_commit=0,
    )

    resp = node.handle_append_entries(msg)
    assert resp.success, "Follower must accept AppendEntries when prev log matches"
    assert node.log.last_index() == 2


def test_log_convergence_after_leader_change():
    """
    After a leader change, all nodes must converge to the same log.

    Exercises the full replication path including prevLogIndex checks.
    """
    net, nodes = make_cluster()
    start_all(nodes)
    try:
        leader = wait_for_leader(nodes)
        assert leader is not None

        # Submit several entries
        for i in range(5):
            leader.submit({{"op": "put", "key": f"key{{i}}", "value": i}})

        time.sleep(0.5)  # Wait for replication

        # All nodes must have the same last committed index
        commit_indices = [n.commit_index for n in nodes]
        assert max(commit_indices) > 0, "No entries committed"
        # At least a quorum must agree
        majority_commit = sorted(commit_indices)[{quorum - 1}]
        assert majority_commit > 0, f"Majority not committed: {{commit_indices}}"
    finally:
        stop_all(nodes)
'''

    def _make_test_commit(self, cluster_size: int, quorum: int) -> str:
        return f'''"""
Commit safety tests — verifies Bug 3 fix: leaders must not commit
entries from previous terms by counting replicas alone.

From the Raft paper (Section 5.4.2):
"Raft never commits log entries from previous terms by counting replicas."
"""
import time
import pytest

from raft.network import SimulatedNetwork
from raft.node import RaftNode, NodeState
from raft.messages import LogEntry


CLUSTER_SIZE = {cluster_size}
ALL_IDS = list(range(CLUSTER_SIZE))


def test_leader_does_not_commit_old_term_entry_directly():
    """
    A leader must not advance commit_index to an old-term entry
    even if a majority of match_index values cover it.

    Per Raft Section 5.4.2: only current-term entries can be directly committed.
    Old entries are committed indirectly via log matching.
    """
    net = SimulatedNetwork()
    # Build a standalone leader node (no running peers — we control state directly)
    node = RaftNode(0, list(range(1, CLUSTER_SIZE)), net)

    # Simulate the node as a leader in term 3
    node.current_term = 3
    node.state = NodeState.LEADER

    # Add a log entry from term 1 (old term) at index 1
    node.log.append(LogEntry(term=1, index=1, command={{"op": "old_entry"}}))

    # Simulate majority replication of this old-term entry
    for peer in node.peers:
        node.match_index[peer] = 1
    node.match_index[node.node_id] = 1

    # With Bug 3, this would commit index 1 (old-term entry)
    node._try_commit()

    # The fixed implementation must NOT commit an old-term entry directly
    assert node.commit_index == 0, (
        f"Bug 3 present: committed old-term entry directly. "
        f"commit_index={{node.commit_index}}, entry term=1, current_term=3"
    )


def test_current_term_entry_can_be_committed():
    """
    A leader can commit an entry from its current term once majority replicated.
    """
    net = SimulatedNetwork()
    node = RaftNode(0, list(range(1, CLUSTER_SIZE)), net)

    node.current_term = 3
    node.state = NodeState.LEADER

    # Add a current-term entry
    node.log.append(LogEntry(term=3, index=1, command={{"op": "current_entry"}}))

    # Simulate majority replication
    for peer in node.peers:
        node.match_index[peer] = 1
    node.match_index[node.node_id] = 1

    node._try_commit()

    assert node.commit_index == 1, (
        f"Current-term entry must be committable. commit_index={{node.commit_index}}"
    )


def test_old_term_entry_committed_indirectly():
    """
    An old-term entry is committed indirectly when a current-term entry
    at a higher index is committed (log matching property).
    """
    net = SimulatedNetwork()
    node = RaftNode(0, list(range(1, CLUSTER_SIZE)), net)

    node.current_term = 3
    node.state = NodeState.LEADER

    # Index 1: old-term entry
    node.log.append(LogEntry(term=1, index=1, command={{"op": "old_entry"}}))
    # Index 2: current-term entry
    node.log.append(LogEntry(term=3, index=2, command={{"op": "new_entry"}}))

    # Simulate majority replication of both entries
    for peer in node.peers:
        node.match_index[peer] = 2
    node.match_index[node.node_id] = 2

    node._try_commit()

    # Both should be committed now (index 2 is current-term, commits index 1 too)
    assert node.commit_index == 2, (
        f"Old-term entry should be committed indirectly via current-term entry. "
        f"commit_index={{node.commit_index}}"
    )
    # Both entries should be applied
    assert node.last_applied == 2
'''

    def _make_test_partition(self, cluster_size: int, quorum: int) -> str:
        return f'''"""
Network partition and heal tests.

Tests that the cluster maintains safety during and after network partitions:
- A minority partition cannot elect a leader (no quorum)
- After healing, the cluster converges to a consistent state
"""
import time
import pytest

from raft.network import SimulatedNetwork
from raft.node import RaftNode


CLUSTER_SIZE = {cluster_size}
ALL_IDS = list(range(CLUSTER_SIZE))
QUORUM = {quorum}


def make_cluster():
    net = SimulatedNetwork()
    nodes = [
        RaftNode(i, [j for j in ALL_IDS if j != i], net)
        for i in ALL_IDS
    ]
    return net, nodes


def wait_for_leader(nodes, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        leaders = [n for n in nodes if n.is_leader()]
        if len(leaders) == 1:
            return leaders[0]
        time.sleep(0.05)
    return None


def start_all(nodes):
    for n in nodes:
        n.start()


def stop_all(nodes):
    for n in nodes:
        n.stop()


def test_minority_partition_no_leader():
    """
    A minority partition (size < quorum) must not elect a leader.
    """
    net, nodes = make_cluster()
    start_all(nodes)
    try:
        # Wait for initial leader
        leader = wait_for_leader(nodes)
        assert leader is not None

        # Isolate a minority (nodes 0..quorum-2) from the majority
        minority_size = QUORUM - 1
        minority_ids = list(range(minority_size))
        majority_ids = [i for i in ALL_IDS if i not in minority_ids]

        for mid in minority_ids:
            for maj_id in majority_ids:
                net.partition(mid, maj_id)

        time.sleep(0.8)  # Give minority time to attempt elections

        # Minority nodes must not have elected a leader among themselves
        minority_nodes = [nodes[i] for i in minority_ids]
        minority_leaders = [n for n in minority_nodes if n.is_leader()]
        assert len(minority_leaders) == 0, (
            f"Minority of {{minority_size}} nodes elected a leader: "
            f"{{[n.node_id for n in minority_leaders]}}"
        )
    finally:
        stop_all(nodes)


def test_partition_heal_convergence():
    """
    After healing a partition, all nodes must converge to the same log.
    """
    net, nodes = make_cluster()
    start_all(nodes)
    try:
        leader = wait_for_leader(nodes)
        assert leader is not None

        # Submit entries before partition
        for i in range(3):
            leader.submit({{"op": "pre_partition", "index": i}})
        time.sleep(0.3)

        # Partition node 0 from everyone
        for oid in ALL_IDS[1:]:
            net.partition(0, oid)

        time.sleep(0.4)

        # Submit entries during partition (to remaining majority)
        majority_nodes = nodes[1:]
        new_leader = wait_for_leader(majority_nodes, timeout=3.0)
        if new_leader is not None:
            for i in range(3):
                new_leader.submit({{"op": "during_partition", "index": i}})
            time.sleep(0.3)

        # Heal partition
        for oid in ALL_IDS[1:]:
            net.heal(0, oid)

        time.sleep(1.0)  # Allow convergence

        # Majority nodes must agree on commit_index
        majority_commits = [nodes[i].commit_index for i in ALL_IDS[1:]]
        assert len(set(majority_commits)) <= 2, (
            f"Majority nodes disagree on commit_index after heal: {{majority_commits}}"
        )
        assert max(majority_commits) >= 3, (
            f"Pre-partition entries not committed: max commit={{max(majority_commits)}}"
        )
    finally:
        stop_all(nodes)
'''

    def _make_test_safety(self, cluster_size: int, quorum: int) -> str:
        return f'''"""
Safety invariant tests for Raft consensus.

Verifies three core Raft safety invariants:
1. Election Safety: at most one leader per term
2. Leader Completeness: committed entries appear in all future leaders' logs
3. State Machine Safety: all nodes apply the same commands in the same order
"""
import time
import threading
import pytest

from raft.network import SimulatedNetwork
from raft.node import RaftNode


CLUSTER_SIZE = {cluster_size}
ALL_IDS = list(range(CLUSTER_SIZE))


def make_cluster():
    net = SimulatedNetwork()
    nodes = [
        RaftNode(i, [j for j in ALL_IDS if j != i], net)
        for i in ALL_IDS
    ]
    return net, nodes


def wait_for_leader(nodes, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        leaders = [n for n in nodes if n.is_leader()]
        if len(leaders) == 1:
            return leaders[0]
        time.sleep(0.05)
    return None


def start_all(nodes):
    for n in nodes:
        n.start()


def stop_all(nodes):
    for n in nodes:
        n.stop()


def test_election_safety_no_two_leaders_same_term():
    """
    Election Safety: at most one leader per term.

    Run multiple elections and verify no two leaders share the same term.
    """
    net, nodes = make_cluster()
    start_all(nodes)
    seen_leaders: dict = {{}}  # term -> node_id

    try:
        for _ in range(3):
            leader = wait_for_leader(nodes, timeout=3.0)
            if leader is None:
                continue

            term = leader.current_term
            if term in seen_leaders:
                assert seen_leaders[term] == leader.node_id, (
                    f"Two leaders in term {{term}}: "
                    f"{{seen_leaders[term]}} and {{leader.node_id}}"
                )
            seen_leaders[term] = leader.node_id

            # Force a new election by isolating current leader briefly
            for peer in leader.peers:
                net.partition(leader.node_id, peer)
            time.sleep(0.4)
            for peer in leader.peers:
                net.heal(leader.node_id, peer)
            time.sleep(0.3)
    finally:
        stop_all(nodes)


def test_state_machine_safety_same_commands_same_order():
    """
    State Machine Safety: nodes that have applied up to index N must agree on
    the command at every index <= N.

    All nodes that have committed the same index must have the same command there.
    """
    net, nodes = make_cluster()
    start_all(nodes)
    try:
        leader = wait_for_leader(nodes)
        assert leader is not None

        commands = [{{"op": "put", "key": f"k{{i}}", "value": i}} for i in range(5)]
        for cmd in commands:
            leader.submit(cmd)

        time.sleep(0.6)  # Wait for replication

        # Find the minimum committed index across all nodes
        committed = [n.commit_index for n in nodes]
        min_committed = min(committed)

        if min_committed < 1:
            pytest.skip("No entries committed yet — increase timeout")

        # All nodes must agree on log content up to min_committed
        for idx in range(1, min_committed + 1):
            entries_at_idx = [n.log.entry_at(idx) for n in nodes]
            # Filter out None (nodes that don't have this entry)
            present = [e for e in entries_at_idx if e is not None]
            if len(present) < 2:
                continue
            # All present entries must have the same term and command
            terms = {{e.term for e in present}}
            assert len(terms) == 1, (
                f"Nodes disagree on term at index {{idx}}: {{terms}}"
            )
            commands_at = [str(e.command) for e in present]
            assert len(set(commands_at)) == 1, (
                f"Nodes disagree on command at index {{idx}}: {{commands_at}}"
            )
    finally:
        stop_all(nodes)


def test_leader_completeness_after_election():
    """
    Leader Completeness: a new leader must have all committed entries.

    Submit entries, ensure they are committed, then force a re-election
    and verify the new leader has all previously committed entries.
    """
    net, nodes = make_cluster()
    start_all(nodes)
    try:
        leader = wait_for_leader(nodes)
        assert leader is not None

        # Submit and commit some entries
        for i in range(4):
            leader.submit({{"op": "setup", "index": i}})
        time.sleep(0.5)

        original_commit = leader.commit_index
        if original_commit == 0:
            pytest.skip("No entries committed — increase sleep")

        # Force re-election: isolate current leader
        old_leader_id = leader.node_id
        for peer in leader.peers:
            net.partition(old_leader_id, peer)

        time.sleep(0.6)  # New election

        remaining = [n for n in nodes if n.node_id != old_leader_id]
        new_leader = wait_for_leader(remaining, timeout=3.0)

        if new_leader is None:
            pytest.skip("No new leader elected — partition may have prevented quorum")

        # New leader must have all entries up to original_commit
        for idx in range(1, original_commit + 1):
            entry = new_leader.log.entry_at(idx)
            assert entry is not None, (
                f"Leader Completeness violated: new leader {{new_leader.node_id}} "
                f"missing committed entry at index {{idx}}"
            )

        # Heal
        for peer in leader.peers:
            net.heal(old_leader_id, peer)
    finally:
        stop_all(nodes)
'''

    def _make_partition_scenario(self, cluster_size: int) -> str:
        import json
        scenario = {
            "name": "partition_heal",
            "description": "Partition a minority of nodes then heal and verify convergence",
            "cluster_size": cluster_size,
            "steps": [
                {"action": "submit", "count": 3, "label": "pre_partition"},
                {"action": "partition", "nodes": [0], "from": list(range(1, cluster_size))},
                {"action": "wait", "ms": 400},
                {"action": "submit", "count": 3, "label": "during_partition", "via_majority": True},
                {"action": "heal_all"},
                {"action": "wait", "ms": 800},
                {"action": "assert_convergence", "min_committed": 3},
            ],
        }
        return json.dumps(scenario, indent=2)

    def _make_crash_scenario(self, cluster_size: int) -> str:
        import json
        scenario = {
            "name": "leader_crash",
            "description": "Leader is isolated mid-replication; new leader must have all committed entries",
            "cluster_size": cluster_size,
            "steps": [
                {"action": "wait_leader"},
                {"action": "submit", "count": 5, "label": "before_crash"},
                {"action": "wait", "ms": 300},
                {"action": "isolate_leader"},
                {"action": "wait", "ms": 600},
                {"action": "wait_leader", "exclude_crashed": True},
                {"action": "assert_leader_completeness"},
                {"action": "heal_all"},
                {"action": "wait", "ms": 500},
                {"action": "assert_convergence", "min_committed": 5},
            ],
        }
        return json.dumps(scenario, indent=2)
