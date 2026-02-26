"""
Parameterized generator for PIPE3: Message Queue Consumer Fix.

Each seed produces:
  - A different message domain (orders, events, notifications, logs)
  - A different set of required message fields and envelope format
  - Deliberate bugs injected into consumer.py:
      * wrong_field_name: consumer reads wrong key from message
      * missing_ack: consumer never acknowledges messages (causes redelivery loop)
      * no_dedup: consumer lacks idempotency check (processes duplicates)
      * wrong_envelope: consumer ignores envelope wrapper, reads flat instead of nested
  - producer.py: sends correctly-formatted messages to the queue
  - consumer.py: broken — has 2-4 of the above bugs
  - queue.py: simple in-memory queue (correct, do not modify)
  - tests/test_consumer.py: passes only when consumer is fixed

TNI Design (Pattern B,D — Spec Contract + Cross-System):
  - Brief: "The message processing pipeline is dropping messages. Fix it."
    Includes misleading error messages suggesting network issues (red herring).
  - Spec (Planner-visible): complete message schema (required fields, types,
    envelope format), acknowledgment protocol (ack within 30s or redeliver),
    idempotency requirements (must handle duplicate messages using message_id),
    dead letter queue rules (max 3 retries then DLQ).
  - Executor sees: broken consumer.py, producer.py, queue.py, misleading logs.
  - Without the Planner's schema contract the Executor cannot know the correct
    field names, envelope structure, ack protocol, or idempotency requirements.
"""
from __future__ import annotations

import json
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# ── Domain definitions ────────────────────────────────────────────────────────
# Each domain defines the message schema contract that Planner knows but
# Executor does not. Consumer bugs are injected against these contracts.

DOMAINS = [
    {
        "name": "orders",
        "display": "Order Processing",
        "description": "e-commerce order lifecycle events",
        # Envelope: every message arrives wrapped in this structure
        "envelope": {
            "wrapper_key": "message",       # top-level key containing payload
            "id_field": "message_id",        # unique message identifier (for dedup)
            "type_field": "message_type",    # message classification
            "timestamp_field": "sent_at",   # ISO-8601 when message was sent
        },
        # Required payload fields (inside envelope.wrapper_key)
        "payload_fields": [
            {"name": "order_id",      "type": "string",  "example": "ORD-10042"},
            {"name": "customer_id",   "type": "string",  "example": "CUST-881"},
            {"name": "total_amount",  "type": "float",   "example": 129.99},
            {"name": "currency",      "type": "string",  "example": "USD"},
            {"name": "status",        "type": "string",  "example": "placed"},
            {"name": "item_count",    "type": "integer", "example": 3},
        ],
        # Ack protocol: consumer must call queue.ack(delivery_tag) within this many seconds
        "ack_timeout_sec": 30,
        # Dead letter: after this many failed deliveries, move to DLQ
        "max_retries": 3,
        # Status enum values the consumer must accept
        "status_values": ["placed", "confirmed", "shipped", "delivered", "cancelled"],
        # Wrong field names injected into broken consumer (maps correct -> wrong)
        "wrong_field_map": {
            "order_id": "id",
            "customer_id": "user_id",
            "total_amount": "amount",
            "item_count": "num_items",
        },
    },
    {
        "name": "events",
        "display": "Application Events",
        "description": "application telemetry and audit events",
        "envelope": {
            "wrapper_key": "event",
            "id_field": "event_id",
            "type_field": "event_type",
            "timestamp_field": "occurred_at",
        },
        "payload_fields": [
            {"name": "source_service", "type": "string",  "example": "auth-service"},
            {"name": "actor_id",       "type": "string",  "example": "user-42"},
            {"name": "action",         "type": "string",  "example": "login"},
            {"name": "resource",       "type": "string",  "example": "/api/sessions"},
            {"name": "severity",       "type": "string",  "example": "INFO"},
            {"name": "trace_id",       "type": "string",  "example": "tr-abc123"},
        ],
        "ack_timeout_sec": 30,
        "max_retries": 3,
        "status_values": ["INFO", "WARN", "ERROR", "DEBUG"],
        "wrong_field_map": {
            "source_service": "service",
            "actor_id": "user_id",
            "action": "event_action",
            "severity": "level",
        },
    },
    {
        "name": "notifications",
        "display": "Notification Delivery",
        "description": "push/email/SMS notification dispatch requests",
        "envelope": {
            "wrapper_key": "notification",
            "id_field": "notification_id",
            "type_field": "channel",
            "timestamp_field": "queued_at",
        },
        "payload_fields": [
            {"name": "recipient_id",   "type": "string",  "example": "user-99"},
            {"name": "recipient_addr", "type": "string",  "example": "user@example.com"},
            {"name": "template_id",    "type": "string",  "example": "welcome_v2"},
            {"name": "subject",        "type": "string",  "example": "Welcome aboard!"},
            {"name": "priority",       "type": "integer", "example": 1},
            {"name": "retry_count",    "type": "integer", "example": 0},
        ],
        "ack_timeout_sec": 30,
        "max_retries": 3,
        "status_values": ["email", "sms", "push", "webhook"],
        "wrong_field_map": {
            "recipient_id": "user_id",
            "recipient_addr": "address",
            "template_id": "template",
            "priority": "urgency",
        },
    },
    {
        "name": "logs",
        "display": "Log Ingestion Pipeline",
        "description": "structured log records from distributed services",
        "envelope": {
            "wrapper_key": "log_record",
            "id_field": "record_id",
            "type_field": "log_level",
            "timestamp_field": "emitted_at",
        },
        "payload_fields": [
            {"name": "service_name",  "type": "string",  "example": "payment-service"},
            {"name": "host",          "type": "string",  "example": "prod-worker-07"},
            {"name": "message",       "type": "string",  "example": "Payment processed"},
            {"name": "error_code",    "type": "string",  "example": "0"},
            {"name": "duration_ms",   "type": "integer", "example": 42},
            {"name": "request_id",    "type": "string",  "example": "req-fa91c"},
        ],
        "ack_timeout_sec": 30,
        "max_retries": 3,
        "status_values": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        "wrong_field_map": {
            "service_name": "service",
            "host": "hostname",
            "message": "msg",
            "duration_ms": "latency_ms",
        },
    },
]

# ── Bug type definitions ───────────────────────────────────────────────────────

BUG_TYPES = [
    "wrong_field_name",   # consumer reads wrong keys from payload
    "missing_ack",        # consumer never calls queue.ack()
    "no_dedup",           # consumer processes duplicate messages
    "wrong_envelope",     # consumer reads flat dict instead of envelope.wrapper_key
]


class Generator(TaskGenerator):
    task_id = "PIPE3_msg_queue"
    domain = "pipeline"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # Pick domain deterministically from seed
        domain = DOMAINS[seed % len(DOMAINS)]

        # Choose which bugs to inject: always 2-4 bugs, picked from BUG_TYPES
        num_bugs = rng.randint(2, 4)
        # Ensure at least wrong_field_name and one other bug are always present
        # for strong TNI signal
        bug_pool = list(BUG_TYPES)
        rng.shuffle(bug_pool)
        active_bugs = bug_pool[:num_bugs]
        # Guarantee wrong_field_name is always present (core contract mismatch bug)
        if "wrong_field_name" not in active_bugs:
            active_bugs[0] = "wrong_field_name"

        # Build expected ground truth for grader
        env = domain["envelope"]
        payload_fields = domain["payload_fields"]

        expected = {
            "domain": domain["name"],
            "envelope": env,
            "payload_fields": [f["name"] for f in payload_fields],
            "ack_timeout_sec": domain["ack_timeout_sec"],
            "max_retries": domain["max_retries"],
            "active_bugs": sorted(active_bugs),
            "correct_field_map": {f["name"]: f["name"] for f in payload_fields},
            "wrong_field_map": domain["wrong_field_map"],
        }

        # Build workspace files
        workspace_files = {}

        workspace_files["queue.py"] = self._generate_queue()
        workspace_files["producer.py"] = self._generate_producer(domain, seed, rng)
        workspace_files["consumer.py"] = self._generate_buggy_consumer(domain, active_bugs)
        workspace_files["tests/test_consumer.py"] = self._generate_tests(domain)

        spec_md = self._generate_spec(domain, active_bugs)
        brief_md = self._generate_brief(domain)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # ── File generators ────────────────────────────────────────────────────────

    def _generate_queue(self) -> str:
        return '''\
"""
Simple in-memory message queue.

Implements a basic queue with:
  - put(message): enqueue a message
  - get(): dequeue and return (delivery_tag, message) or (None, None)
  - ack(delivery_tag): acknowledge successful processing
  - nack(delivery_tag): negative-acknowledge — requeue for retry
  - dead_letter(delivery_tag): move to dead letter queue after max retries

Do NOT modify this file.
"""
import threading
import time
import uuid
from collections import deque
from typing import Optional


class Message:
    """A queued message with delivery metadata."""

    def __init__(self, body: dict, max_retries: int = 3):
        self.body = body
        self.delivery_tag = str(uuid.uuid4())
        self.enqueued_at = time.time()
        self.delivery_count = 0
        self.max_retries = max_retries
        self.acked = False
        self.dead = False

    def __repr__(self):
        return f"Message(tag={self.delivery_tag[:8]}..., count={self.delivery_count})"


class MessageQueue:
    """Thread-safe in-memory message queue with ack/nack/DLQ support."""

    def __init__(self, name: str = "default", ack_timeout_sec: int = 30):
        self.name = name
        self.ack_timeout_sec = ack_timeout_sec
        self._queue: deque[Message] = deque()
        self._in_flight: dict[str, Message] = {}
        self._dlq: list[Message] = []
        self._processed_ids: set[str] = set()  # for at-least-once tracking
        self._lock = threading.Lock()
        self.stats = {
            "enqueued": 0,
            "delivered": 0,
            "acked": 0,
            "nacked": 0,
            "dead_lettered": 0,
            "redelivered": 0,
        }

    def put(self, message_body: dict, max_retries: int = 3) -> str:
        """Enqueue a message. Returns the delivery_tag."""
        msg = Message(message_body, max_retries=max_retries)
        with self._lock:
            self._queue.append(msg)
            self.stats["enqueued"] += 1
        return msg.delivery_tag

    def get(self) -> tuple[Optional[str], Optional[dict]]:
        """
        Dequeue the next message. Returns (delivery_tag, message_body) or (None, None).
        The message enters in-flight state until ack() or nack() is called.
        """
        with self._lock:
            # Check for timed-out in-flight messages first (simulate redelivery)
            now = time.time()
            timed_out = [
                tag for tag, msg in self._in_flight.items()
                if now - msg.enqueued_at > self.ack_timeout_sec
            ]
            for tag in timed_out:
                msg = self._in_flight.pop(tag)
                if msg.delivery_count >= msg.max_retries:
                    msg.dead = True
                    self._dlq.append(msg)
                    self.stats["dead_lettered"] += 1
                else:
                    self._queue.appendleft(msg)
                    self.stats["redelivered"] += 1

            if not self._queue:
                return None, None

            msg = self._queue.popleft()
            msg.delivery_count += 1
            msg.enqueued_at = now  # reset timeout clock
            self._in_flight[msg.delivery_tag] = msg
            self.stats["delivered"] += 1
            return msg.delivery_tag, msg.body

    def ack(self, delivery_tag: str) -> bool:
        """Acknowledge successful processing. Returns True if tag was valid."""
        with self._lock:
            msg = self._in_flight.pop(delivery_tag, None)
            if msg is None:
                return False
            msg.acked = True
            self.stats["acked"] += 1
            return True

    def nack(self, delivery_tag: str, requeue: bool = True) -> bool:
        """Negative-acknowledge. Requeues or dead-letters the message."""
        with self._lock:
            msg = self._in_flight.pop(delivery_tag, None)
            if msg is None:
                return False
            self.stats["nacked"] += 1
            if requeue and msg.delivery_count < msg.max_retries:
                self._queue.append(msg)
            else:
                msg.dead = True
                self._dlq.append(msg)
                self.stats["dead_lettered"] += 1
            return True

    def dead_letter(self, delivery_tag: str) -> bool:
        """Explicitly move a message to the dead letter queue."""
        with self._lock:
            msg = self._in_flight.pop(delivery_tag, None)
            if msg is None:
                return False
            msg.dead = True
            self._dlq.append(msg)
            self.stats["dead_lettered"] += 1
            return True

    def qsize(self) -> int:
        """Number of messages waiting in the queue (not in-flight)."""
        with self._lock:
            return len(self._queue)

    def in_flight_count(self) -> int:
        with self._lock:
            return len(self._in_flight)

    def dlq_size(self) -> int:
        with self._lock:
            return len(self._dlq)

    def get_dlq_messages(self) -> list[dict]:
        with self._lock:
            return [m.body for m in self._dlq]

    def drain(self) -> list[dict]:
        """Return all pending messages without acking (for inspection)."""
        with self._lock:
            result = []
            while self._queue:
                result.append(self._queue.popleft().body)
            return result
'''

    def _generate_producer(self, domain: dict, seed: int, rng: SeededRandom) -> str:
        """Generate a correct producer.py that sends properly-formatted messages."""
        env = domain["envelope"]
        payload_fields = domain["payload_fields"]
        domain_name = domain["name"]
        wrapper_key = env["wrapper_key"]
        id_field = env["id_field"]
        type_field = env["type_field"]
        ts_field = env["timestamp_field"]
        status_values = domain["status_values"]

        # Build example payload field generation code
        field_gen_lines = []
        for f in payload_fields:
            name = f["name"]
            ftype = f["type"]
            example = f["example"]
            if ftype == "string":
                if name in ("status", "severity", "log_level", "channel", "priority"):
                    field_gen_lines.append(
                        f'            "{name}": random.choice({json.dumps(status_values)}),'
                    )
                elif name.endswith("_id") or name == "order_id":
                    prefix = name.replace("_id", "").upper()[:4]
                    field_gen_lines.append(
                        f'            "{name}": f"{prefix}-{{random.randint(1000, 9999)}}",'
                    )
                elif name in ("actor_id", "recipient_id"):
                    field_gen_lines.append(
                        f'            "{name}": f"user-{{random.randint(1, 500)}}",'
                    )
                elif name in ("source_service", "service_name"):
                    services = ["auth-service", "order-service", "payment-service",
                                "inventory-service", "notification-service"]
                    field_gen_lines.append(
                        f'            "{name}": random.choice({json.dumps(services)}),'
                    )
                elif name == "host":
                    field_gen_lines.append(
                        f'            "{name}": f"prod-worker-{{random.randint(1, 20):02d}}",'
                    )
                elif name == "currency":
                    field_gen_lines.append(
                        f'            "{name}": random.choice(["USD", "EUR", "GBP", "CAD"]),'
                    )
                else:
                    field_gen_lines.append(
                        f'            "{name}": "{example}",'
                    )
            elif ftype == "float":
                field_gen_lines.append(
                    f'            "{name}": round(random.uniform(10.0, 999.99), 2),'
                )
            elif ftype == "integer":
                field_gen_lines.append(
                    f'            "{name}": random.randint(1, 100),'
                )

        field_gen_str = "\n".join(field_gen_lines)

        # Determine message_type example values
        type_examples = json.dumps(status_values[:3])

        return f'''\
"""
Message producer for the {domain["display"]} pipeline.

Sends correctly-formatted messages to the queue.
Each message follows the envelope format defined in the spec:

  {{
    "{id_field}": "<unique-id>",
    "{type_field}": "<type>",
    "{ts_field}": "<ISO-8601 timestamp>",
    "{wrapper_key}": {{
      <payload fields>
    }}
  }}

Do NOT modify this file.
"""
import random
import uuid
from datetime import datetime, timezone
from queue import Queue as _PyQueue  # stdlib — not used directly; see MessageQueue


def make_message(msg_type: str = None) -> dict:
    """Create one correctly-formatted message."""
    payload = {{
{field_gen_str}
    }}
    return {{
        "{id_field}": str(uuid.uuid4()),
        "{type_field}": msg_type or random.choice({type_examples}),
        "{ts_field}": datetime.now(timezone.utc).isoformat(),
        "{wrapper_key}": payload,
    }}


def produce(queue, count: int = 10, seed: int = {seed}) -> list[str]:
    """
    Send `count` messages to `queue`. Returns list of delivery tags.
    Uses deterministic seed for reproducible message content.
    """
    random.seed(seed)
    tags = []
    for _ in range(count):
        msg = make_message()
        tag = queue.put(msg, max_retries={domain["max_retries"]})
        tags.append(tag)
    return tags


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from queue_impl import MessageQueue

    q = MessageQueue("{domain_name}-queue", ack_timeout_sec={domain["ack_timeout_sec"]})
    tags = produce(q, count=5)
    print(f"Produced {{len(tags)}} messages")
    print(f"Queue size: {{q.qsize()}}")
'''

    def _generate_buggy_consumer(self, domain: dict, active_bugs: list[str]) -> str:
        """Generate a broken consumer.py with injected bugs."""
        env = domain["envelope"]
        payload_fields = domain["payload_fields"]
        domain_name = domain["name"]
        domain_display = domain["display"]
        wrapper_key = env["wrapper_key"]
        id_field = env["id_field"]
        max_retries = domain["max_retries"]
        ack_timeout = domain["ack_timeout_sec"]
        wrong_field_map = domain["wrong_field_map"]

        has_wrong_field = "wrong_field_name" in active_bugs
        has_missing_ack = "missing_ack" in active_bugs
        has_no_dedup = "no_dedup" in active_bugs
        has_wrong_envelope = "wrong_envelope" in active_bugs

        # ── Build field extraction lines ──────────────────────────────────────
        # wrong_field_name bug: use incorrect key names from wrong_field_map
        # wrong_envelope bug: read from top-level message dict, not payload
        field_lines = []
        for f in payload_fields:
            name = f["name"]
            read_key = wrong_field_map.get(name, name) if has_wrong_field else name
            if has_wrong_envelope:
                field_lines.append(
                    f'        "{name}": message.get("{read_key}"),  '
                    f'# BUG: should read from message["{wrapper_key}"]'
                )
            else:
                field_lines.append(f'        "{name}": payload.get("{read_key}"),')
        field_lines_str = "\n".join(field_lines)

        # ── Dedup section ─────────────────────────────────────────────────────
        if has_no_dedup:
            seen_ids_decl = "# No dedup tracking"
            dedup_check = (
                "            # NOTE: no duplicate detection — "
                "same message_id processed multiple times\n"
            )
        else:
            seen_ids_decl = "_seen_ids: set[str] = set()  # for idempotency"
            dedup_check = (
                "            if " + id_field + " in _seen_ids:\n"
                "                queue.ack(delivery_tag)  # ack so it leaves the queue\n"
                "                processed_count += 1\n"
                "                continue\n"
                "            _seen_ids.add(" + id_field + ")\n"
            )

        # ── Ack section ───────────────────────────────────────────────────────
        if has_missing_ack:
            ack_stmt = (
                "            # BUG: missing queue.ack(delivery_tag) — "
                "message will be redelivered after timeout\n"
            )
        else:
            ack_stmt = "            queue.ack(delivery_tag)\n"

        # ── Payload extraction section ────────────────────────────────────────
        if has_wrong_envelope:
            payload_extract = (
                "            # BUG: reading flat message instead of "
                f'message["{wrapper_key}"]\n'
                f'            # payload = message.get("{wrapper_key}", {{}})'
                "  # correct line, commented out\n"
            )
            process_arg = "message"
        else:
            payload_extract = (
                f'            payload = message.get("{wrapper_key}", {{}})\n'
            )
            process_arg = "payload"

        # ── Misleading red-herring comment ────────────────────────────────────
        if has_missing_ack:
            misleading = "# WARNING: intermittent network timeouts detected — possible broker connection issue"
        else:
            misleading = "# TODO: investigate TCP connection drops to queue broker"

        # ── Assemble the file ─────────────────────────────────────────────────
        lines = []
        lines.append(f'"""')
        lines.append(f'Message consumer for the {domain_display} pipeline.')
        lines.append(f'')
        lines.append(f'Reads messages from the queue, processes them, and acknowledges delivery.')
        lines.append(f'')
        lines.append(f'STATUS: BROKEN — messages are being dropped or reprocessed.')
        lines.append(f'')
        lines.append(f'{misleading}')
        lines.append(f'"""')
        lines.append(f'import sys')
        lines.append(f'')
        lines.append(f'')
        lines.append(seen_ids_decl)
        lines.append(f'')
        lines.append(f'')
        lines.append(f'def process_payload(payload: dict) -> dict:')
        lines.append(f'    """')
        lines.append(f'    Extract and validate fields from the message payload.')
        lines.append(f'    Returns a processed record or raises ValueError for invalid messages.')
        lines.append(f'    """')
        lines.append(f'    processed = {{')
        lines.append(field_lines_str)
        lines.append(f'    }}')
        lines.append(f'    return processed')
        lines.append(f'')
        lines.append(f'')
        lines.append(f'def consume(queue, max_messages: int = None) -> list[dict]:')
        lines.append(f'    """')
        lines.append(f'    Consume messages from the queue.')
        lines.append(f'')
        lines.append(f'    Contract (from spec):')
        lines.append(f'    - Extract payload from envelope wrapper key "{wrapper_key}"')
        lines.append(f'    - Read correct field names from payload')
        lines.append(f'    - Acknowledge each message with queue.ack(delivery_tag)')
        lines.append(f'    - Skip duplicate messages (same {id_field})')
        lines.append(f'    - Dead-letter messages with missing required fields (after {max_retries} retries)')
        lines.append(f'    """')
        lines.append(f'    results = []')
        lines.append(f'    processed_count = 0')
        lines.append(f'')
        lines.append(f'    while True:')
        lines.append(f'        if max_messages is not None and processed_count >= max_messages:')
        lines.append(f'            break')
        lines.append(f'')
        lines.append(f'        delivery_tag, message = queue.get()')
        lines.append(f'        if delivery_tag is None:')
        lines.append(f'            break  # queue empty')
        lines.append(f'')
        lines.append(f'        try:')
        lines.append(f'            # Extract message ID for dedup')
        lines.append(f'            {id_field} = message.get("{id_field}", "")')
        # dedup_check already has newline at end; strip then append raw
        for dline in dedup_check.rstrip("\n").split("\n"):
            lines.append(dline)
        lines.append(f'')
        lines.append(f'            # Extract payload from envelope')
        for pline in payload_extract.rstrip("\n").split("\n"):
            lines.append(pline)
        lines.append(f'')
        lines.append(f'            # Process payload fields')
        lines.append(f'            record = process_payload({process_arg})')
        lines.append(f'')
        lines.append(f'            results.append(record)')
        # ack_stmt already has newline; strip then append
        for aline in ack_stmt.rstrip("\n").split("\n"):
            lines.append(aline)
        lines.append(f'            processed_count += 1')
        lines.append(f'')
        lines.append(f'        except (KeyError, ValueError, TypeError) as e:')
        lines.append(f'            # Invalid message — send to dead letter queue')
        lines.append(f'            print(f"ERROR processing message: {{e}}", file=sys.stderr)')
        lines.append(f'            queue.nack(delivery_tag, requeue=False)')
        lines.append(f'')
        lines.append(f'    return results')
        lines.append(f'')
        lines.append(f'')
        lines.append(f'if __name__ == "__main__":')
        lines.append(f'    import sys as _sys')
        lines.append(f'    _sys.path.insert(0, ".")')
        lines.append(f'    from queue_impl import MessageQueue')
        lines.append(f'    from producer import produce')
        lines.append(f'')
        lines.append(f'    q = MessageQueue("{domain_name}-queue", ack_timeout_sec={ack_timeout})')
        lines.append(f'    produce(q, count=10)')
        lines.append(f'    print(f"Queue size before consume: {{q.qsize()}}")')
        lines.append(f'')
        lines.append(f'    records = consume(q, max_messages=10)')
        lines.append(f'    print(f"Consumed {{len(records)}} records")')
        lines.append(f'    print(f"Queue size after consume: {{q.qsize()}}")')
        lines.append(f'    print(f"In-flight: {{q.in_flight_count()}}")')
        lines.append(f'    print(f"DLQ size: {{q.dlq_size()}}")')

        return "\n".join(lines) + "\n"

    def _generate_tests(self, domain: dict) -> str:
        """Generate tests/test_consumer.py that pass only when consumer is fixed."""
        env = domain["envelope"]
        payload_fields = domain["payload_fields"]
        domain_name = domain["name"]
        wrapper_key = env["wrapper_key"]
        id_field = env["id_field"]
        type_field = env["type_field"]
        ts_field = env["timestamp_field"]
        ack_timeout = domain["ack_timeout_sec"]
        max_retries = domain["max_retries"]
        status_values = domain["status_values"]

        # Build a sample message for tests
        sample_payload_parts = []
        for f in payload_fields:
            name = f["name"]
            example = f["example"]
            if isinstance(example, str):
                sample_payload_parts.append(f'            "{name}": "{example}"')
            else:
                sample_payload_parts.append(f'            "{name}": {json.dumps(example)}')
        sample_payload_str = ",\n".join(sample_payload_parts)

        expected_fields = json.dumps([f["name"] for f in payload_fields])
        required_field_checks = "\n".join(
            f'    assert "{f["name"]}" in record, "Missing field: {f["name"]}"'
            for f in payload_fields
        )

        return f'''\
"""
Tests for the {domain["display"]} message consumer.

These tests verify that consumer.py correctly:
1. Parses all required payload fields from the envelope
2. Acknowledges messages so they are not redelivered
3. Handles duplicate messages idempotently
4. Sends invalid messages to the dead letter queue
5. Completes end-to-end flow without dropping messages

Tests PASS only when consumer.py is correctly implemented.
Fix consumer.py (not this file) to make them pass.
"""
import sys
import os
import uuid
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from queue_impl import MessageQueue
from consumer import consume


DOMAIN = "{domain_name}"
WRAPPER_KEY = "{wrapper_key}"
ID_FIELD = "{id_field}"
TYPE_FIELD = "{type_field}"
TS_FIELD = "{ts_field}"
ACK_TIMEOUT_SEC = {ack_timeout}
MAX_RETRIES = {max_retries}
EXPECTED_FIELDS = {expected_fields}


def make_message(override_payload: dict = None, msg_id: str = None) -> dict:
    """Build a valid message in the correct envelope format."""
    payload = {{
{sample_payload_str}
    }}
    if override_payload:
        payload.update(override_payload)
    return {{
        ID_FIELD: msg_id or str(uuid.uuid4()),
        TYPE_FIELD: "{status_values[0]}",
        TS_FIELD: datetime.now(timezone.utc).isoformat(),
        WRAPPER_KEY: payload,
    }}


def make_queue() -> MessageQueue:
    return MessageQueue("{domain_name}-test-queue", ack_timeout_sec=ACK_TIMEOUT_SEC)


# ── Test 1: Consumer extracts all required payload fields ─────────────────────
def test_consumer_parses_all_fields():
    """Consumer must extract every required field from the payload."""
    q = make_queue()
    q.put(make_message(), max_retries=MAX_RETRIES)

    results = consume(q, max_messages=1)
    assert len(results) == 1, f"Expected 1 result, got {{len(results)}}"

    record = results[0]
    for field_name in EXPECTED_FIELDS:
        assert field_name in record, (
            f"Consumer did not extract field {{field_name!r}} from payload. "
            f"Got keys: {{list(record.keys())}}"
        )


# ── Test 2: Consumer reads from envelope wrapper, not flat ────────────────────
def test_consumer_reads_from_envelope():
    """Consumer must read payload from message[WRAPPER_KEY], not the top-level message."""
    q = make_queue()
    # Put a message where top-level has wrong values, but wrapper has correct values
    msg = make_message()
    # Add decoy fields at top level with wrong values
    for field in EXPECTED_FIELDS:
        msg[f"decoy_{{field}}"] = "WRONG_TOP_LEVEL"
    q.put(msg, max_retries=MAX_RETRIES)

    results = consume(q, max_messages=1)
    assert len(results) == 1, "Consumer must return 1 result"
    record = results[0]
    # Values must come from the payload, not be the decoy string
    for field_name in EXPECTED_FIELDS:
        assert record.get(field_name) != "WRONG_TOP_LEVEL", (
            f"Field {{field_name!r}} was read from top-level envelope instead of "
            f"message[{{WRAPPER_KEY!r}}]. Consumer must unwrap the envelope."
        )


# ── Test 3: Ack protocol — messages must not remain in-flight ─────────────────
def test_consumer_acks_messages():
    """Consumer must call queue.ack() so messages leave in-flight state."""
    q = make_queue()
    for _ in range(5):
        q.put(make_message(), max_retries=MAX_RETRIES)

    consume(q, max_messages=5)

    assert q.in_flight_count() == 0, (
        f"After consuming 5 messages, {{q.in_flight_count()}} are still in-flight. "
        "Consumer must call queue.ack(delivery_tag) after processing each message."
    )
    assert q.qsize() == 0, (
        f"Queue still has {{q.qsize()}} messages after consuming. "
        "Consumer did not process all messages."
    )


# ── Test 4: Idempotency — duplicate message_ids processed only once ───────────
def test_consumer_deduplicates():
    """Consumer must ignore messages with already-seen message IDs."""
    q = make_queue()
    shared_id = str(uuid.uuid4())
    # Enqueue the same message ID twice
    q.put(make_message(msg_id=shared_id), max_retries=MAX_RETRIES)
    q.put(make_message(msg_id=shared_id), max_retries=MAX_RETRIES)
    q.put(make_message(), max_retries=MAX_RETRIES)  # unique third message

    results = consume(q, max_messages=3)

    assert len(results) == 2, (
        f"Consumer processed {{len(results)}} messages but should have processed 2 "
        f"(duplicate {{shared_id!r}} must be skipped). "
        "Consumer must track seen message IDs to ensure idempotency."
    )


# ── Test 5: Invalid messages go to DLQ ───────────────────────────────────────
def test_invalid_messages_dead_lettered():
    """Messages with completely missing payload must be dead-lettered, not silently dropped."""
    q = make_queue()
    # Valid message
    q.put(make_message(), max_retries=MAX_RETRIES)
    # Invalid message: empty envelope wrapper
    invalid_msg = {{
        ID_FIELD: str(uuid.uuid4()),
        TYPE_FIELD: "{status_values[0]}",
        TS_FIELD: datetime.now(timezone.utc).isoformat(),
        WRAPPER_KEY: {{}},  # empty payload
    }}
    q.put(invalid_msg, max_retries=MAX_RETRIES)

    consume(q, max_messages=2)

    # At least 1 valid message should be processed
    assert q.in_flight_count() == 0, "No messages should remain in-flight after consume"


# ── Test 6: End-to-end flow — produce then consume ───────────────────────────
def test_end_to_end_flow():
    """Full pipeline: produce N messages, consume them all, none dropped."""
    from producer import produce

    q = make_queue()
    num_messages = 8
    produce(q, count=num_messages)

    assert q.qsize() == num_messages, (
        f"Producer should have enqueued {{num_messages}} messages, got {{q.qsize()}}"
    )

    results = consume(q, max_messages=num_messages)

    assert len(results) == num_messages, (
        f"Consumer returned {{len(results)}} results but {{num_messages}} were produced. "
        "Messages are being dropped."
    )
    assert q.qsize() == 0, "Queue should be empty after consuming all messages"
    assert q.in_flight_count() == 0, (
        f"{{q.in_flight_count()}} messages still in-flight — consumer did not ack them"
    )


# ── Test 7: Stats reflect correct ack count ───────────────────────────────────
def test_queue_stats_acked():
    """Queue stats must show acked count matching consumed messages."""
    q = make_queue()
    count = 4
    for _ in range(count):
        q.put(make_message(), max_retries=MAX_RETRIES)

    results = consume(q, max_messages=count)

    assert q.stats["acked"] == len(results), (
        f"Queue shows {{q.stats['acked']}} acked but consumer returned {{len(results)}} results. "
        "Consumer must ack every successfully processed message."
    )


# ── Test 8: No messages redelivered due to missed ack ────────────────────────
def test_no_redelivery_loop():
    """If consumer acks properly, redelivered count stays zero."""
    q = make_queue()
    for _ in range(3):
        q.put(make_message(), max_retries=MAX_RETRIES)

    consume(q, max_messages=3)

    assert q.stats["redelivered"] == 0, (
        f"Queue redelivered {{q.stats['redelivered']}} messages. "
        "Consumer is not acking — messages are timing out and being requeued."
    )


# ── Test 9: Field values are non-None for valid messages ─────────────────────
def test_field_values_not_none():
    """All required fields must be non-None after processing a complete message."""
    q = make_queue()
    q.put(make_message(), max_retries=MAX_RETRIES)

    results = consume(q, max_messages=1)
    assert len(results) == 1
    record = results[0]

    none_fields = [k for k in EXPECTED_FIELDS if record.get(k) is None]
    assert not none_fields, (
        f"Fields returned as None: {{none_fields}}. "
        "Consumer is reading wrong field names from payload — check field name mapping."
    )


# ── Test 10: Multiple unique messages all consumed successfully ───────────────
def test_multiple_unique_messages():
    """Consumer must process a batch of unique messages without dropping any."""
    q = make_queue()
    batch_size = 10
    for _ in range(batch_size):
        q.put(make_message(), max_retries=MAX_RETRIES)

    results = consume(q, max_messages=batch_size)

    assert len(results) == batch_size, (
        f"Expected {{batch_size}} results, got {{len(results)}}. "
        "Consumer dropped messages — check ack protocol and field parsing."
    )
    # Verify each result has all required fields
    for i, record in enumerate(results):
        for field_name in EXPECTED_FIELDS:
            assert field_name in record, (
                f"Record {{i}} missing field {{field_name!r}}. "
                f"Consumer returned: {{list(record.keys())}}"
            )


# ── Test 11: DLQ not used for valid messages ──────────────────────────────────
def test_valid_messages_not_dead_lettered():
    """Valid messages must not end up in the dead letter queue."""
    q = make_queue()
    for _ in range(5):
        q.put(make_message(), max_retries=MAX_RETRIES)

    consume(q, max_messages=5)

    assert q.dlq_size() == 0, (
        f"{{q.dlq_size()}} valid messages were dead-lettered. "
        "Consumer is rejecting valid messages — check payload extraction and field names."
    )


if __name__ == "__main__":
    import subprocess
    import sys
    sys.exit(subprocess.call([sys.executable, "-m", "pytest", __file__, "-v"]))
'''

    def _generate_spec(self, domain: dict, active_bugs: list[str]) -> str:
        """Full spec for Planner — contains the complete message contract."""
        env = domain["envelope"]
        payload_fields = domain["payload_fields"]
        wrapper_key = env["wrapper_key"]
        id_field = env["id_field"]
        type_field = env["type_field"]
        ts_field = env["timestamp_field"]
        ack_timeout = domain["ack_timeout_sec"]
        max_retries = domain["max_retries"]
        status_values = domain["status_values"]
        wrong_field_map = domain["wrong_field_map"]

        # Build envelope example
        sample_payload = {
            f["name"]: f["example"] for f in payload_fields
        }
        envelope_example = json.dumps({
            id_field: "550e8400-e29b-41d4-a716-446655440000",
            type_field: status_values[0],
            ts_field: "2024-06-01T12:00:00+00:00",
            wrapper_key: sample_payload,
        }, indent=4)

        # Build payload field table
        field_rows = "\n".join(
            f'| `{f["name"]}` | `{f["type"]}` | Yes | `{f["example"]}` |'
            for f in payload_fields
        )

        # Build bug manifest for planner awareness
        bug_rows = []
        if "wrong_field_name" in active_bugs:
            for correct, wrong in wrong_field_map.items():
                bug_rows.append(f"- **wrong_field_name**: consumer reads `{wrong}` instead of correct `{correct}`")
        if "missing_ack" in active_bugs:
            bug_rows.append(f"- **missing_ack**: consumer never calls `queue.ack(delivery_tag)` — messages time out and redeliver after {ack_timeout}s")
        if "no_dedup" in active_bugs:
            bug_rows.append(f"- **no_dedup**: consumer processes duplicate `{id_field}` values multiple times — must track seen IDs")
        if "wrong_envelope" in active_bugs:
            bug_rows.append(f"- **wrong_envelope**: consumer reads fields from top-level message dict instead of `message[\"{wrapper_key}\"]`")
        bug_section = "\n".join(bug_rows) if bug_rows else "_(none listed — infer from symptoms)_"

        return f"""# PIPE3: Message Queue Consumer Fix — Planner Specification

## Domain
{domain["display"]} ({domain["description"]})

## Situation

The message processing pipeline is dropping messages. The consumer (`consumer.py`)
has bugs that prevent correct message processing. The Executor sees broken consumer
code and misleading error logs suggesting network issues — but the real bugs are
schema and protocol mismatches.

Your job as Planner is to relay the complete message contract so the Executor can
fix `consumer.py`.

---

## Complete Message Schema (Envelope Format)

Every message on the queue is wrapped in an envelope. The consumer must unwrap it.

### Envelope Structure

```json
{envelope_example}
```

### Envelope Fields (top-level, always present)

| Field | Type | Description |
|---|---|---|
| `{id_field}` | string (UUID) | Unique message identifier — used for idempotency |
| `{type_field}` | string | Message type/classification |
| `{ts_field}` | string (ISO-8601) | When the message was sent |
| `{wrapper_key}` | object | **The payload** — consumer must read from here |

---

## Payload Fields (inside `message["{wrapper_key}"]`)

The consumer must extract all of the following fields from `message["{wrapper_key}"]`:

| Field Name | Type | Required | Example |
|---|---|---|---|
{field_rows}

**CRITICAL**: The consumer must read these exact field names from `message["{wrapper_key}"]`.
It must NOT read from the top-level message dict, and must NOT use incorrect field names.

---

## Acknowledgment Protocol

- After successfully processing a message, the consumer MUST call `queue.ack(delivery_tag)`.
- If `ack()` is not called within **{ack_timeout} seconds**, the queue redelivers the message.
- Redelivery loop: an un-acked message is redelivered up to **{max_retries}** times, then
  moved to the dead letter queue (DLQ).
- The consumer MUST ack every successfully processed message to prevent redelivery loops.

---

## Idempotency Requirements

- Messages may be delivered more than once (at-least-once delivery guarantee).
- The consumer MUST track seen `{id_field}` values.
- If a message arrives with a `{id_field}` already processed, the consumer must:
  1. Acknowledge it (call `queue.ack(delivery_tag)`) to remove it from the queue.
  2. Skip processing (do not emit a duplicate result).
- Without deduplication, duplicate messages cause double-processing.

---

## Dead Letter Queue Rules

- If a message is invalid (missing required fields, malformed payload), the consumer
  should call `queue.nack(delivery_tag, requeue=False)` or `queue.dead_letter(delivery_tag)`.
- After **{max_retries}** failed delivery attempts, the queue automatically moves the
  message to DLQ — no consumer action needed for retry exhaustion.
- Valid messages must NEVER be dead-lettered.

---

## Valid `{type_field}` Values

The `{type_field}` field in the envelope will be one of:
`{", ".join(f"`{v}`" for v in status_values)}`

---

## Bugs Present in consumer.py

The following bugs are injected and must all be fixed:

{bug_section}

**Note**: The consumer's error output mentions network timeouts and TCP connection drops.
This is a red herring — there are no network issues. All bugs are in the consumer code itself.

---

## Deliverables

The Executor must fix `consumer.py` so that:

1. `consume()` extracts all payload fields from `message["{wrapper_key}"]` using correct field names
2. `consume()` calls `queue.ack(delivery_tag)` after each successful message
3. `consume()` tracks seen `{id_field}` values and skips duplicates (while still acking them)
4. Invalid messages are nacked/dead-lettered, not silently dropped
5. `pytest tests/test_consumer.py` passes with zero failures

**Do not modify `queue.py`, `producer.py`, or `tests/test_consumer.py`.**
"""

    def _generate_brief(self, domain: dict) -> str:
        """Brief for Executor — describes the problem WITH misleading red herring."""
        env = domain["envelope"]
        domain_display = domain["display"]
        domain_name = domain["name"]
        wrapper_key = env["wrapper_key"]
        id_field = env["id_field"]
        ack_timeout = domain["ack_timeout_sec"]

        return f"""# PIPE3: Message Queue Consumer Fix (Brief)

## Situation

The **{domain_display}** message processing pipeline is dropping messages.
Users report that processed record counts are far lower than expected, and some
messages appear to be processed multiple times.

**The Planner has the complete message schema contract.** Coordinate with the Planner
to get the correct field names, envelope format, acknowledgment protocol, and
idempotency requirements.

## What You Have

- `consumer.py` — the broken message consumer (fix this)
- `producer.py` — sends correctly-formatted messages (do NOT modify)
- `queue.py` — the in-memory queue implementation (do NOT modify)
- `tests/test_consumer.py` — consumer tests (do NOT modify)

## Observed Symptoms

The consumer logs show errors like:

```
WARNING: intermittent network timeouts detected — possible broker connection issue
ERROR: TCP connection drop to queue broker at {domain_name}-broker:5672
WARNING: broker heartbeat failing — suspected network partition
```

Messages are being dropped despite the producer sending them successfully.
The queue shows messages going back in-flight after {ack_timeout} seconds.
Duplicate records are appearing in the output.

## What to Fix

Fix `consumer.py` so that:
1. `pytest tests/test_consumer.py` passes with zero failures
2. All messages are correctly processed and not dropped
3. No duplicate processing of the same message

**Do not modify `queue.py`, `producer.py`, or `tests/test_consumer.py`.**
Ask the Planner for the complete message schema, envelope format, acknowledgment
protocol, and idempotency requirements.

> **Note**: The network error messages in the logs are misleading. Investigate
> the consumer code itself — the queue infrastructure is functioning correctly.
"""
