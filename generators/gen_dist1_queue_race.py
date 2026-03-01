"""
Parameterized generator for DIST1: Message Queue Race Conditions.

Each seed produces a different domain context (task/event/job queue) but the
same 3 structural race conditions. The bug structure is identical across seeds;
only variable/class names and domain terminology vary.
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# Domain variants per seed
DOMAINS = ["task", "event", "job"]
QUEUE_CLASSES = ["TaskQueue", "EventQueue", "JobQueue"]
MESSAGE_CLASSES = ["Task", "Event", "Job"]
PRIORITY_CLASSES = ["PriorityTask", "PriorityEvent", "PriorityJob"]
PRODUCER_NAMES = ["worker_producer", "event_emitter", "job_submitter"]
CONSUMER_NAMES = ["worker_consumer", "event_handler", "job_executor"]
PRIORITY_LABELS = ["urgency", "severity", "sla_tier"]
PRIORITY_DESCS = [
    "Lower urgency number = higher priority (0=critical, 9=low)",
    "Lower severity number = higher priority (0=critical, 9=info)",
    "Lower SLA tier number = higher priority (0=platinum, 9=best-effort)",
]
CAPACITY_VALS = [500, 1000, 750]
MODULE_NAMES = ["tqueue", "equeue", "jqueue"]


class Generator(TaskGenerator):
    task_id = "DIST1_queue_race"
    domain = "Distributed"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        idx = seed % len(DOMAINS)

        domain = DOMAINS[idx]
        queue_cls = QUEUE_CLASSES[idx]
        msg_cls = MESSAGE_CLASSES[idx]
        prio_cls = PRIORITY_CLASSES[idx]
        producer_fn = PRODUCER_NAMES[idx]
        consumer_fn = CONSUMER_NAMES[idx]
        prio_field = PRIORITY_LABELS[idx]
        prio_desc = PRIORITY_DESCS[idx]
        capacity = CAPACITY_VALS[idx]
        mod = MODULE_NAMES[idx]

        workspace_files = self._make_workspace(
            domain=domain,
            queue_cls=queue_cls,
            msg_cls=msg_cls,
            prio_cls=prio_cls,
            producer_fn=producer_fn,
            consumer_fn=consumer_fn,
            prio_field=prio_field,
            prio_desc=prio_desc,
            capacity=capacity,
            mod=mod,
        )

        tasks_dir = os.path.join(
            os.path.dirname(__file__), "..", "tasks", "DIST1_queue_race"
        )
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="DIST1_queue_race",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "bugs_fixed": ["TOCTOU_capacity", "missing_ack_pattern", "type_unsafe_comparator"],
                "seed": seed,
                "domain": domain,
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Distributed"},
        )

    def _make_workspace(
        self,
        domain: str,
        queue_cls: str,
        msg_cls: str,
        prio_cls: str,
        producer_fn: str,
        consumer_fn: str,
        prio_field: str,
        prio_desc: str,
        capacity: int,
        mod: str,
    ) -> dict:
        files = {}

        files["mqueue/__init__.py"] = ""
        files["tests/__init__.py"] = ""

        # --- mqueue/config.py ---
        files["mqueue/config.py"] = f'''"""Queue configuration constants."""

CAPACITY = {capacity}
TIMEOUT = 5.0          # seconds to wait for a slot/message
N_PRODUCERS = 10
N_CONSUMERS = 10
MESSAGES_PER_PRODUCER = 100
'''

        # --- mqueue/queue.py  (contains Bug 1 and Bug 2) ---
        files["mqueue/queue.py"] = f'''"""
{domain.capitalize()} message queue with acknowledgment support.

WARNING: This implementation contains known race conditions for testing purposes.
"""
import threading
import uuid
from collections import deque
from typing import Any, Optional, Tuple


class QueueFull(Exception):
    """Raised when the queue has reached its capacity."""


class QueueEmpty(Exception):
    """Raised when the queue is empty."""


class {queue_cls}:
    """Thread-safe {domain} queue with configurable capacity."""

    def __init__(self, capacity: int = {capacity}):
        self._capacity = capacity
        self._queue: deque = deque()
        self._lock = threading.Lock()

    def put(self, message: Any) -> None:
        """
        Enqueue a {domain} message.

        Raises QueueFull if the queue is at capacity.
        """
        # BUG 1: TOCTOU — the capacity check and the append are two separate
        # operations with no lock holding both. Two producers can both pass
        # the check before either appends, causing capacity to be exceeded.
        if len(self._queue) >= self._capacity:  # Step 1: check (no lock held)
            raise QueueFull(
                f"{queue_cls} at capacity ({{self._capacity}})"
            )
        self._queue.append(message)  # Step 2: append (another thread may have
                                     # also passed the check between these two lines)

    def get(self) -> Optional[Any]:
        """
        Dequeue and return the next {domain} message, or None if empty.

        BUG 2: The message is removed from the queue immediately. If the
        consumer crashes after get() but before finishing processing, the
        message is permanently lost — there is no way to re-deliver it.
        """
        with self._lock:
            if not self._queue:
                return None
            return self._queue.popleft()  # message gone forever after this line

    def size(self) -> int:
        """Return the current number of {domain}s in the queue."""
        return len(self._queue)

    def is_empty(self) -> bool:
        """Return True if the queue has no {domain}s waiting."""
        return len(self._queue) == 0

    def is_full(self) -> bool:
        """Return True if the queue is at capacity."""
        return len(self._queue) >= self._capacity
'''

        # --- mqueue/priority.py  (contains Bug 3) ---
        files["mqueue/priority.py"] = f'''"""
Priority-ordered {domain} message wrapper.

Uses a dataclass with ordering so that {domain}s can be placed in a heap.
"""
from dataclasses import dataclass
from typing import Any


@dataclass(order=True)
class {prio_cls}:
    """{prio_desc}

    BUG 3: When two {domain}s have equal {prio_field}, Python\'s dataclass
    ordering falls through to comparing the `message` field. If the payload
    is a dict, list, or other non-comparable type, this raises TypeError at
    runtime — crashes the priority heap under concurrent load.
    """
    {prio_field}: int   # Primary sort key
    message: Any        # BUG: used as secondary sort key by dataclass ordering
                        # — crashes with TypeError if payload is a dict or list
'''

        # --- mqueue/producer.py ---
        files["mqueue/producer.py"] = f'''"""Producer helper for the {domain} queue."""
import threading
import time
from typing import Any

from mqueue.queue import {queue_cls}, QueueFull


class {msg_cls}Producer:
    """Sends {domain}s to a {queue_cls}."""

    def __init__(self, queue: {queue_cls}, producer_id: int):
        self._queue = queue
        self._producer_id = producer_id
        self._sent: list = []
        self._lock = threading.Lock()

    def send(self, payload: Any, retries: int = 3) -> bool:
        """
        Send a {domain} to the queue.

        Returns True on success, False if the queue remained full after retries.
        """
        for attempt in range(retries):
            try:
                self._queue.put(payload)
                with self._lock:
                    self._sent.append(payload)
                return True
            except QueueFull:
                if attempt < retries - 1:
                    time.sleep(0.001 * (attempt + 1))
        return False

    @property
    def sent_count(self) -> int:
        return len(self._sent)

    @property
    def sent_messages(self) -> list:
        with self._lock:
            return list(self._sent)
'''

        # --- mqueue/consumer.py ---
        files["mqueue/consumer.py"] = f'''"""Consumer interface for the {domain} queue.

This consumer does NOT use an acknowledgment pattern — it calls get() and
immediately proceeds with processing. If the consumer crashes mid-processing,
the {domain} is permanently lost.

The consumer needs to be updated to use ack/nack once the queue supports it.
"""
import threading
import time
from typing import Any, Callable, Optional

from mqueue.queue import {queue_cls}


class {msg_cls}Consumer:
    """
    Consumes {domain}s from a {queue_cls}.

    Current implementation: fire-and-forget (no ack/nack).
    After fixing Bug 2, this should use the ack/nack pattern.
    """

    def __init__(
        self,
        queue: {queue_cls},
        handler: Callable[[Any], None],
        consumer_id: int = 0,
    ):
        self._queue = queue
        self._handler = handler
        self._consumer_id = consumer_id
        self._processed: list = []
        self._lock = threading.Lock()
        self._running = False

    def run_once(self) -> bool:
        """
        Process one {domain} from the queue.

        Returns True if a {domain} was processed, False if the queue was empty.
        """
        # No ack pattern: message removed from queue before handler called.
        # If self._handler raises, the {domain} is permanently lost.
        message = self._queue.get()
        if message is None:
            return False
        self._handler(message)
        with self._lock:
            self._processed.append(message)
        return True

    def run_until_empty(self, max_idle_cycles: int = 10) -> None:
        """Drain the queue, stopping after max_idle_cycles consecutive empty polls."""
        idle = 0
        while idle < max_idle_cycles:
            if self.run_once():
                idle = 0
            else:
                idle += 1
                time.sleep(0.001)

    @property
    def processed_count(self) -> int:
        return len(self._processed)

    @property
    def processed_messages(self) -> list:
        with self._lock:
            return list(self._processed)
'''

        # --- tests/test_single_thread.py  (pass even with bugs) ---
        files["tests/test_single_thread.py"] = f'''"""
Single-threaded tests for the {domain} queue.

These tests pass even with the race condition bugs because they never
exercise concurrent access paths.
"""
import pytest
from mqueue.queue import {queue_cls}, QueueFull


def test_put_and_get_basic():
    """Basic enqueue/dequeue round-trip."""
    q = {queue_cls}(capacity=10)
    q.put("{domain}_1")
    q.put("{domain}_2")
    result = q.get()
    # After fix, get() returns (msg, receipt) — handle both
    msg = result[0] if isinstance(result, tuple) else result
    assert msg == "{domain}_1"


def test_queue_empty_returns_none():
    """get() on empty queue returns None (or (None, None) after fix)."""
    q = {queue_cls}(capacity=10)
    result = q.get()
    if isinstance(result, tuple):
        assert result[0] is None
    else:
        assert result is None


def test_queue_full_raises():
    """put() on a full queue raises QueueFull."""
    q = {queue_cls}(capacity=3)
    q.put("a")
    q.put("b")
    q.put("c")
    with pytest.raises(QueueFull):
        q.put("d")


def test_size_tracking():
    """size() reflects current queue depth."""
    q = {queue_cls}(capacity=10)
    assert q.size() == 0
    q.put("x")
    assert q.size() == 1
    q.put("y")
    assert q.size() == 2


def test_is_empty_and_is_full():
    """is_empty() and is_full() return correct values."""
    q = {queue_cls}(capacity=2)
    assert q.is_empty()
    assert not q.is_full()
    q.put("a")
    assert not q.is_empty()
    assert not q.is_full()
    q.put("b")
    assert q.is_full()


def test_fifo_order():
    """Messages are retrieved in FIFO order (single thread)."""
    q = {queue_cls}(capacity=10)
    for i in range(5):
        q.put(f"{domain}_{{i}}")
    for i in range(5):
        result = q.get()
        msg = result[0] if isinstance(result, tuple) else result
        assert msg == f"{domain}_{{i}}"
'''

        # --- tests/test_concurrent.py  (expose the race conditions) ---
        files["tests/test_concurrent.py"] = f'''"""
Concurrent correctness tests for the {domain} queue.

These tests FAIL with the buggy implementation because they exercise
race conditions that single-threaded tests cannot expose.
"""
import threading
import time
import pytest

from mqueue.queue import {queue_cls}, QueueFull
from mqueue.config import N_PRODUCERS, N_CONSUMERS, MESSAGES_PER_PRODUCER


def test_concurrent_no_message_loss():
    """
    Multiple producers and consumers, all messages must arrive with zero loss.

    Exposes Bug 2 (no ack): if a consumer gets a message but crashes before
    processing, the message is gone. We simulate this by tracking all sent
    and received messages.
    """
    total_messages = N_PRODUCERS * MESSAGES_PER_PRODUCER
    q = {queue_cls}(capacity=total_messages)

    sent = []
    received = []
    sent_lock = threading.Lock()
    recv_lock = threading.Lock()
    done_event = threading.Event()

    def producer(pid: int):
        for i in range(MESSAGES_PER_PRODUCER):
            msg = f"p{{pid}}-{domain}{{i}}"
            with sent_lock:
                sent.append(msg)
            q.put(msg)
            time.sleep(0.00005)

    def consumer():
        while not done_event.is_set() or not q.is_empty():
            result = q.get()
            if isinstance(result, tuple):
                msg, receipt = result
                if msg is None:
                    time.sleep(0.001)
                    continue
                # ack if the queue supports it
                if hasattr(q, 'ack') and receipt is not None:
                    q.ack(receipt)
            else:
                msg = result
                if msg is None:
                    time.sleep(0.001)
                    continue
            with recv_lock:
                received.append(msg)

    threads = []
    for i in range(N_PRODUCERS):
        threads.append(threading.Thread(target=producer, args=(i,), daemon=False))
    consumer_threads = [
        threading.Thread(target=consumer, daemon=True)
        for _ in range(N_CONSUMERS)
    ]

    for t in consumer_threads:
        t.start()
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    done_event.set()
    time.sleep(0.5)  # Let consumers drain

    assert len(received) == total_messages, (
        f"Message loss: sent {{total_messages}}, received {{len(received)}}"
    )


def test_capacity_never_exceeded():
    """
    Concurrent puts must not push the queue past capacity.

    Exposes Bug 1 (TOCTOU): two producers both check capacity, both see room,
    both append — queue exceeds declared capacity.
    """
    capacity = 20
    q = {queue_cls}(capacity=capacity)
    errors = []

    def aggressive_producer():
        for _ in range(50):
            try:
                q.put(f"{domain}_item")
            except QueueFull:
                pass
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=aggressive_producer) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not errors, f"Unexpected errors during concurrent puts: {{errors}}"
    assert q.size() <= capacity, (
        f"Capacity violated: queue size {{q.size()}} exceeds capacity {{capacity}}"
    )
'''

        # --- tests/test_message_loss.py ---
        files["tests/test_message_loss.py"] = f'''"""
Zero-loss guarantee test for the {domain} queue.

Sends 10,000 {domain}s across 20 threads and verifies every one is received.
"""
import threading
import time

from mqueue.queue import {queue_cls}, QueueFull


def test_zero_message_loss_10k():
    """10K {domain}s across 20 threads must arrive with zero loss."""
    N = 10_000
    n_producers = 10
    n_consumers = 10
    per_producer = N // n_producers

    q = {queue_cls}(capacity=N)
    sent = []
    received = []
    s_lock = threading.Lock()
    r_lock = threading.Lock()
    stop = threading.Event()

    def producer(pid: int):
        for i in range(per_producer):
            msg = f"{domain}-{{pid}}-{{i}}"
            retry = 0
            while retry < 10:
                try:
                    q.put(msg)
                    with s_lock:
                        sent.append(msg)
                    break
                except QueueFull:
                    time.sleep(0.001)
                    retry += 1

    def consumer():
        while not stop.is_set() or not q.is_empty():
            result = q.get()
            if isinstance(result, tuple):
                msg, receipt = result
                if msg is None:
                    time.sleep(0.0005)
                    continue
                if hasattr(q, 'ack') and receipt is not None:
                    q.ack(receipt)
            else:
                msg = result
                if msg is None:
                    time.sleep(0.0005)
                    continue
            with r_lock:
                received.append(msg)

    producer_threads = [
        threading.Thread(target=producer, args=(i,)) for i in range(n_producers)
    ]
    consumer_threads = [
        threading.Thread(target=consumer, daemon=True) for _ in range(n_consumers)
    ]

    for t in consumer_threads:
        t.start()
    for t in producer_threads:
        t.start()
    for t in producer_threads:
        t.join(timeout=120)

    stop.set()
    time.sleep(1.0)

    assert len(sent) == N, f"Not all {domain}s were sent: {{len(sent)}}/{{N}}"
    assert len(received) == len(sent), (
        f"Message loss: sent {{len(sent)}}, received {{len(received)}}"
    )
'''

        # --- tests/test_ordering.py ---
        files["tests/test_ordering.py"] = f'''"""
Priority ordering tests for the {domain} priority queue.

Verifies that {prio_field} ordering is correct and that equal-{prio_field}
messages do not cause TypeError (Bug 3).
"""
import heapq
import pytest

# Import the priority class — name varies by seed
try:
    from mqueue.priority import {prio_cls}
    _PRIO_CLS = {prio_cls}
except ImportError:
    _PRIO_CLS = None


def _make_item(prio, seq, msg):
    """Construct a priority item, handling both buggy (2-field) and fixed (3-field) class."""
    try:
        return _PRIO_CLS({prio_field}=prio, seq=seq, message=msg)
    except TypeError:
        # Buggy version has only two fields: {prio_field} and message
        return _PRIO_CLS({prio_field}=prio, message=msg)


@pytest.mark.skipif(_PRIO_CLS is None, reason="Priority class not found")
def test_higher_priority_comes_first():
    """Lower {prio_field} number must be dequeued first (string payloads — comparable in both versions)."""
    heap = []
    for prio in [5, 1, 3, 0, 4]:
        item = _make_item(prio, prio, f"{domain}-prio{{prio}}")
        heapq.heappush(heap, item)

    priorities = []
    while heap:
        item = heapq.heappop(heap)
        priorities.append(item.{prio_field})

    assert priorities == sorted(priorities), (
        f"Priority ordering wrong: {{priorities}}"
    )


@pytest.mark.skipif(_PRIO_CLS is None, reason="Priority class not found")
def test_equal_priority_no_type_error_with_dict_payload():
    """Equal-{prio_field} {domain}s with dict payloads must not raise TypeError."""
    heap = []
    for i in range(5):
        item = _make_item(1, i, {{"{domain}_id": i, "data": [i, i + 1]}})
        heapq.heappush(heap, item)  # Buggy version raises TypeError here

    results = []
    while heap:
        results.append(heapq.heappop(heap))

    assert len(results) == 5


@pytest.mark.skipif(_PRIO_CLS is None, reason="Priority class not found")
def test_equal_priority_no_type_error_with_list_payload():
    """Equal-{prio_field} {domain}s with list payloads must not raise TypeError."""
    heap = []
    for i in range(3):
        item = _make_item(2, i, [i, "data", {{}}])
        heapq.heappush(heap, item)

    while heap:
        heapq.heappop(heap)  # Must not raise
'''

        # --- tests/test_capacity.py ---
        files["tests/test_capacity.py"] = f'''"""
Capacity enforcement tests for the {domain} queue under concurrent load.

Verifies Bug 1 (TOCTOU) is fixed: concurrent puts must never push the queue
past its declared capacity.
"""
import threading
import pytest

from mqueue.queue import {queue_cls}, QueueFull


def test_capacity_not_exceeded_under_concurrent_puts():
    """
    5 threads each try 40 puts into a capacity-10 queue.
    After all threads finish, queue size must be <= 10.
    """
    capacity = 10
    q = {queue_cls}(capacity=capacity)
    errors = []

    def stuffer():
        for _ in range(40):
            try:
                q.put("{domain}_item")
            except QueueFull:
                pass
            except Exception as e:
                errors.append(e)

    threads = [threading.Thread(target=stuffer) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not errors, f"Unexpected errors: {{errors}}"
    assert q.size() <= capacity, (
        f"Capacity violated: size={{q.size()}}, capacity={{capacity}}"
    )


def test_capacity_not_exceeded_high_contention():
    """20 threads hammering a capacity-5 queue must never exceed 5 items."""
    capacity = 5
    q = {queue_cls}(capacity=capacity)
    peak_sizes = []
    lock = threading.Lock()

    def worker():
        for _ in range(100):
            try:
                q.put("{domain}")
            except QueueFull:
                pass
            with lock:
                peak_sizes.append(q.size())

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    max_seen = max(peak_sizes) if peak_sizes else 0
    assert max_seen <= capacity, (
        f"Capacity {{capacity}} violated: peak size was {{max_seen}}"
    )
'''

        # --- tests/test_crash_recovery.py ---
        files["tests/test_crash_recovery.py"] = f'''"""
Consumer crash recovery tests.

Verifies Bug 2 is fixed: if a consumer gets a {domain} but calls nack()
(simulating a crash), the {domain} must be re-queued and eventually delivered.
"""
import pytest

from mqueue.queue import {queue_cls}


def test_nack_requeues_message():
    """
    A nack()'d {domain} must be re-delivered to the next consumer.
    """
    q = {queue_cls}(capacity=10)
    if not hasattr(q, 'ack') or not hasattr(q, 'nack'):
        pytest.skip("Queue does not support ack/nack — fix Bug 2 first")

    q.put("{domain}_important")

    # First get — simulated crash
    msg1, receipt1 = q.get()
    assert msg1 == "{domain}_important"
    q.nack(receipt1)  # Consumer crashed — put it back

    # Second get — must re-deliver the same message
    msg2, receipt2 = q.get()
    assert msg2 == "{domain}_important", (
        f"Message not re-delivered after nack: got {{msg2!r}}"
    )
    q.ack(receipt2)  # Successful processing


def test_acked_message_not_redelivered():
    """
    An ack()'d {domain} must NOT be re-delivered.
    """
    q = {queue_cls}(capacity=10)
    if not hasattr(q, 'ack'):
        pytest.skip("Queue does not support ack — fix Bug 2 first")

    q.put("{domain}_done")
    msg, receipt = q.get()
    assert msg == "{domain}_done"
    q.ack(receipt)

    # Queue must now be empty — no re-delivery
    result = q.get()
    if isinstance(result, tuple):
        assert result[0] is None, "Acked message was re-delivered"
    else:
        assert result is None, "Acked message was re-delivered"


def test_multiple_in_flight_nack_all():
    """
    Multiple in-flight {domain}s that all get nack()'d must all be re-queued.
    """
    q = {queue_cls}(capacity=10)
    if not hasattr(q, 'ack') or not hasattr(q, 'nack'):
        pytest.skip("Queue does not support ack/nack — fix Bug 2 first")

    msgs = [f"{domain}_{{i}}" for i in range(3)]
    for m in msgs:
        q.put(m)

    receipts = []
    for _ in range(3):
        msg, receipt = q.get()
        receipts.append((msg, receipt))

    # Nack all of them (simulate 3 simultaneous crashes)
    for _, receipt in receipts:
        q.nack(receipt)

    # All 3 must be retrievable again
    recovered = []
    for _ in range(3):
        result = q.get()
        if isinstance(result, tuple):
            msg, receipt = result
            if msg is not None:
                q.ack(receipt)
                recovered.append(msg)

    assert len(recovered) == 3, (
        f"Expected 3 recovered {domain}s after nack, got {{len(recovered)}}"
    )
'''

        return files
