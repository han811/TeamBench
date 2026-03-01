"""
Parameterized generator for CROSS3: Protocol Bridge.

Each seed produces a different domain (event streaming, IoT telemetry, media catalog)
but the same 4 translation bugs + 2 error mapping bugs. The Planner must compare
Service A's JSON models against Service B's proto3-style schema to identify every
type mismatch.
"""
from __future__ import annotations
import os
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# Per-seed domain configuration
DOMAINS = [
    {
        # Seed 0: Event streaming
        "name": "event_streaming",
        "service_a_title": "Event Streaming API",
        "service_b_title": "Event Queue Consumer",
        "record_class": "EventRecord",
        "message_class": "EventMessage",
        "record_id_field": "event_id",
        "type_field": "event_type",
        "payload_field": "payload",
        "content_text_key": "text_content",
        "content_binary_key": "binary_content",
        "status_field": "status",
        "timestamp_field": "occurred_at",
        "sample_type": "user.login",
        "sample_text": "User logged in from 192.168.1.1",
        "status_values": ["STATUS_UNKNOWN", "STATUS_ACTIVE", "STATUS_INACTIVE", "STATUS_PENDING"],
        "status_class": "EventStatus",
        "flask_resource": "events",
        "flask_endpoint": "events_api",
    },
    {
        # Seed 1: IoT telemetry
        "name": "iot_telemetry",
        "service_a_title": "IoT Telemetry API",
        "service_b_title": "Sensor Data Consumer",
        "record_class": "TelemetryRecord",
        "message_class": "TelemetryMessage",
        "record_id_field": "device_id",
        "type_field": "reading_type",
        "payload_field": "raw_bytes",
        "content_text_key": "label",
        "content_binary_key": "blob",
        "status_field": "device_status",
        "timestamp_field": "sampled_at",
        "sample_type": "temperature",
        "sample_text": "Sensor label: temp-probe-01",
        "status_values": ["STATUS_UNKNOWN", "STATUS_ONLINE", "STATUS_OFFLINE", "STATUS_DEGRADED"],
        "status_class": "DeviceStatus",
        "flask_resource": "readings",
        "flask_endpoint": "telemetry_api",
    },
    {
        # Seed 2: Media catalog
        "name": "media_catalog",
        "service_a_title": "Media Catalog API",
        "service_b_title": "Media Index Consumer",
        "record_class": "MediaRecord",
        "message_class": "MediaMessage",
        "record_id_field": "asset_id",
        "type_field": "media_type",
        "payload_field": "thumbnail",
        "content_text_key": "caption",
        "content_binary_key": "preview_bytes",
        "status_field": "publish_status",
        "timestamp_field": "created_at",
        "sample_type": "video",
        "sample_text": "Caption: Summer highlights reel",
        "status_values": ["STATUS_UNKNOWN", "STATUS_PUBLISHED", "STATUS_DRAFT", "STATUS_ARCHIVED"],
        "status_class": "PublishStatus",
        "flask_resource": "assets",
        "flask_endpoint": "media_api",
    },
]


class Generator(TaskGenerator):
    task_id = "cross3_protocol_bridge"
    domain = "Cross-System"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        d = DOMAINS[seed % len(DOMAINS)]

        workspace_files = self._make_workspace(d, seed)

        tasks_dir = os.path.join(os.path.dirname(__file__), "..", "tasks", "CROSS3_protocol_bridge")
        with open(os.path.join(tasks_dir, "spec.md")) as f:
            spec_md = f.read()
        with open(os.path.join(tasks_dir, "brief.md")) as f:
            brief_md = f.read()

        return GeneratedTask(
            task_id="cross3_protocol_bridge",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected={
                "bugs_fixed": ["B1_int64", "B2_bytes", "B3_oneof", "B4_enum", "B5_404", "B6_429"],
                "seed": seed,
                "domain": d["name"],
            },
            workspace_files=workspace_files,
            metadata={"difficulty": "hard", "category": "Cross-System"},
        )

    def _make_workspace(self, d: dict, seed: int) -> dict:
        files = {}

        # ---------- service_a/__init__.py ----------
        files["service_a/__init__.py"] = ""

        # ---------- service_a/models.py ----------
        files["service_a/models.py"] = self._service_a_models(d)

        # ---------- service_a/app.py ----------
        files["service_a/app.py"] = self._service_a_app(d)

        # ---------- service_b/__init__.py ----------
        files["service_b/__init__.py"] = ""

        # ---------- service_b/schema.py ----------
        files["service_b/schema.py"] = self._service_b_schema(d)

        # ---------- service_b/consumer.py ----------
        files["service_b/consumer.py"] = self._service_b_consumer(d)

        # ---------- bridge/__init__.py ----------
        files["bridge/__init__.py"] = ""

        # ---------- bridge/translator.py (with 4 bugs) ----------
        files["bridge/translator.py"] = self._bridge_translator(d)

        # ---------- bridge/error_mapper.py (with 2 bugs) ----------
        files["bridge/error_mapper.py"] = self._bridge_error_mapper(d)

        # ---------- bridge/publisher.py ----------
        files["bridge/publisher.py"] = self._bridge_publisher(d)

        # ---------- bridge/config.py ----------
        files["bridge/config.py"] = self._bridge_config(d)

        # ---------- tests/__init__.py ----------
        files["tests/__init__.py"] = ""

        # ---------- tests/fixtures.py ----------
        files["tests/fixtures.py"] = self._tests_fixtures(d, seed)

        # ---------- tests/test_translation.py ----------
        files["tests/test_translation.py"] = self._tests_translation(d)

        # ---------- tests/test_errors.py ----------
        files["tests/test_errors.py"] = self._tests_errors(d)

        # ---------- tests/test_e2e.py ----------
        files["tests/test_e2e.py"] = self._tests_e2e(d)

        return files

    # ------------------------------------------------------------------
    # Service A
    # ------------------------------------------------------------------

    def _service_a_models(self, d: dict) -> str:
        status_values_repr = ", ".join(f'"{v}"' for v in d["status_values"])
        return f'''"""
{d["service_a_title"]} — JSON data models.

These models define the JSON structure that Service A returns.
Note: binary data is base64-encoded as strings; large IDs are plain numbers.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
import base64


class {d["record_class"]}:
    """JSON response model from {d["service_a_title"]}."""

    VALID_STATUSES = [{status_values_repr}]

    def __init__(
        self,
        {d["record_id_field"]}: int,
        {d["type_field"]}: str,
        {d["payload_field"]}: str,          # base64-encoded binary
        {d["status_field"]}: str,           # string enum name
        {d["timestamp_field"]}: int,        # unix timestamp (int64)
        {d["content_text_key"]}: str = "",  # optional text content (oneof)
        {d["content_binary_key"]}: str = "",# optional binary content as base64 (oneof)
    ):
        self.{d["record_id_field"]} = {d["record_id_field"]}
        self.{d["type_field"]} = {d["type_field"]}
        self.{d["payload_field"]} = {d["payload_field"]}
        self.{d["status_field"]} = {d["status_field"]}
        self.{d["timestamp_field"]} = {d["timestamp_field"]}
        self.{d["content_text_key"]} = {d["content_text_key"]}
        self.{d["content_binary_key"]} = {d["content_binary_key"]}

    def to_dict(self) -> dict:
        return {{
            "{d["record_id_field"]}": self.{d["record_id_field"]},
            "{d["type_field"]}": self.{d["type_field"]},
            "{d["payload_field"]}": self.{d["payload_field"]},
            "{d["status_field"]}": self.{d["status_field"]},
            "{d["timestamp_field"]}": self.{d["timestamp_field"]},
            "{d["content_text_key"]}": self.{d["content_text_key"]},
            "{d["content_binary_key"]}": self.{d["content_binary_key"]},
        }}

    @classmethod
    def from_dict(cls, data: dict) -> "{d["record_class"]}":
        return cls(
            {d["record_id_field"]}=data["{d["record_id_field"]}"],
            {d["type_field"]}=data.get("{d["type_field"]}", ""),
            {d["payload_field"]}=data.get("{d["payload_field"]}", ""),
            {d["status_field"]}=data.get("{d["status_field"]}", "{d["status_values"][0]}"),
            {d["timestamp_field"]}=data.get("{d["timestamp_field"]}", 0),
            {d["content_text_key"]}=data.get("{d["content_text_key"]}", ""),
            {d["content_binary_key"]}=data.get("{d["content_binary_key"]}", ""),
        )
'''

    def _service_a_app(self, d: dict) -> str:
        return f'''"""
{d["service_a_title"]} — Flask REST API.

This is the source-of-truth REST service. The bridge polls these endpoints
and translates responses into Service B messages.
"""
from flask import Flask, jsonify, abort
from service_a.models import {d["record_class"]}
import base64

app = Flask(__name__)

# Sample data store
_STORE = {{
    1: {d["record_class"]}(
        {d["record_id_field"]}=9007199254740993,
        {d["type_field"]}="{d["sample_type"]}",
        {d["payload_field"]}=base64.b64encode(b"sample binary data").decode(),
        {d["status_field"]}="{d["status_values"][1]}",
        {d["timestamp_field"]}=1700000000,
        {d["content_text_key"]}="{d["sample_text"]}",
        {d["content_binary_key"]}="",
    ),
}}


@app.route("/{d["flask_resource"]}/<int:record_id>", methods=["GET"])
def get_record(record_id: int):
    """Return a single record as JSON."""
    record = _STORE.get(record_id)
    if record is None:
        abort(404)
    return jsonify(record.to_dict())


@app.route("/{d["flask_resource"]}", methods=["GET"])
def list_records():
    """Return all records as JSON."""
    return jsonify([r.to_dict() for r in _STORE.values()])


if __name__ == "__main__":
    app.run(port=5000)
'''

    # ------------------------------------------------------------------
    # Service B
    # ------------------------------------------------------------------

    def _service_b_schema(self, d: dict) -> str:
        sv = d["status_values"]
        enum_lines = "\n".join(
            f"    {v} = {i}" for i, v in enumerate(sv)
        )
        return f'''"""
{d["service_b_title"]} — Proto3-style message schema.

This module defines the structured messages that Service B consumes.
Field semantics follow proto3 rules:
  - int64 fields hold arbitrary-precision Python ints
  - bytes fields hold raw bytes (NOT base64 strings)
  - oneof fields allow exactly one variant to be set
  - enum fields use integer codes, not string names
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional


class {d["status_class"]}(IntEnum):
    """Proto3 enum — integer codes only."""
{enum_lines}


class ErrorCode(IntEnum):
    """gRPC-style error codes."""
    OK = 0
    CANCELLED = 1
    UNKNOWN = 2
    INVALID_ARGUMENT = 3
    NOT_FOUND = 5
    ALREADY_EXISTS = 6
    RESOURCE_EXHAUSTED = 8
    INTERNAL = 13


@dataclass
class {d["message_class"]}:
    """Proto3-style message for {d["service_b_title"]}."""
    {d["record_id_field"]}: int = 0          # int64: must hold values > 2^32
    {d["type_field"]}: str = ""
    {d["payload_field"]}: bytes = b""        # bytes: base64-decoded from JSON
    {d["status_field"]}: int = 0             # {d["status_class"]} integer code (not string)
    {d["timestamp_field"]}: int = 0          # int64 unix timestamp

    # oneof content {{ {d["content_text_key"]}, {d["content_binary_key"]} }}
    {d["content_text_key"]}: str = ""        # set this OR content_binary, not both
    {d["content_binary_key"]}: bytes = b""   # set this OR content_text, not both

    def validate_oneof(self) -> bool:
        """Exactly one of {d["content_text_key"]} or {d["content_binary_key"]} must be set."""
        set_fields = []
        if self.{d["content_text_key"]}:
            set_fields.append("{d["content_text_key"]}")
        if self.{d["content_binary_key"]}:
            set_fields.append("{d["content_binary_key"]}")
        if len(set_fields) > 1:
            raise ValueError(
                f"oneof violation: multiple variants set: {{set_fields}}"
            )
        return True


@dataclass
class StatusMessage:
    """Error/status response for Service B."""
    code: int = 0
    message: str = ""
'''

    def _service_b_consumer(self, d: dict) -> str:
        return f'''"""
{d["service_b_title"]} — message consumer stub.

In production this would read from a queue (Kafka, Pub/Sub, etc.).
For the benchmark this is a simple in-memory collector.
"""
from __future__ import annotations
from service_b.schema import {d["message_class"]}, StatusMessage
from typing import List


class MessageConsumer:
    """Receives and validates {d["message_class"]} objects."""

    def __init__(self):
        self._received: List[{d["message_class"]}] = []
        self._errors: List[StatusMessage] = []

    def consume(self, msg: {d["message_class"]}) -> None:
        """Accept a message after validation."""
        msg.validate_oneof()
        if not isinstance(msg.{d["payload_field"]}, bytes):
            raise TypeError(f"{d["payload_field"]} must be bytes, got {{type(msg.{d["payload_field"]})}}")
        if not isinstance(msg.{d["status_field"]}, int):
            raise TypeError(f"{d["status_field"]} must be int, got {{type(msg.{d["status_field"]})}}")
        self._received.append(msg)

    def consume_error(self, status: StatusMessage) -> None:
        self._errors.append(status)

    @property
    def received(self) -> List[{d["message_class"]}]:
        return list(self._received)

    @property
    def errors(self) -> List[StatusMessage]:
        return list(self._errors)
'''

    # ------------------------------------------------------------------
    # Bridge (buggy)
    # ------------------------------------------------------------------

    def _bridge_translator(self, d: dict) -> str:
        return f'''"""
Bridge translator: converts Service A JSON dicts into Service B messages.

Contains 4 bugs — see spec.md for details.
"""
import base64
from service_b.schema import {d["message_class"]}, {d["status_class"]}

STATUS_MAP = {{
    "{d["status_values"][0]}": 0,
    "{d["status_values"][1]}": 1,
    "{d["status_values"][2]}": 2,
    "{d["status_values"][3]}": 3,
}}


def translate_{d["name"]}(data: dict) -> {d["message_class"]}:
    """Translate JSON data from Service A to {d["message_class"]} for Service B."""
    msg = {d["message_class"]}()

    # Bug 1: int64 truncation — masks large IDs to 32-bit
    msg.{d["record_id_field"]} = int(data.get("{d["record_id_field"]}", 0)) & 0xFFFFFFFF

    msg.{d["type_field"]} = data.get("{d["type_field"]}", "")
    msg.{d["timestamp_field"]} = int(data.get("{d["timestamp_field"]}", 0))

    # Bug 2: bytes field not base64-decoded — assigns raw string instead of bytes
    msg.{d["payload_field"]} = data.get("{d["payload_field"]}", "")

    # Bug 3: oneof — sets both content fields instead of exactly one
    msg.{d["content_text_key"]} = data.get("{d["content_text_key"]}", "")
    msg.{d["content_binary_key"]} = data.get("{d["content_binary_key"]}", b"")

    # Bug 4: enum string not mapped to int — assigns string directly
    msg.{d["status_field"]} = data.get("{d["status_field"]}", "{d["status_values"][0]}")

    return msg


# Alias used by tests
translate_event = translate_{d["name"]}
'''

    def _bridge_error_mapper(self, d: dict) -> str:
        return f'''"""
Bridge error mapper: converts HTTP status codes to Service B error codes.

Contains 2 bugs — see spec.md for details.
"""
from service_b.schema import ErrorCode, StatusMessage


def map_http_error(status_code: int, message: str = "") -> StatusMessage:
    """Map HTTP status code from Service A to a Service B error code."""
    if status_code == 200:
        return StatusMessage(code=ErrorCode.OK)
    elif status_code == 400:
        return StatusMessage(code=ErrorCode.INVALID_ARGUMENT, message=message)
    elif status_code in (401, 403):
        return StatusMessage(code=ErrorCode.INVALID_ARGUMENT, message=message)
    elif status_code == 404:
        # Bug 5: should be NOT_FOUND (5), not INVALID_ARGUMENT (3)
        return StatusMessage(code=ErrorCode.INVALID_ARGUMENT, message=message)
    elif status_code == 429:
        # Bug 6: should be RESOURCE_EXHAUSTED (8), not INTERNAL (13)
        return StatusMessage(code=ErrorCode.INTERNAL, message=message)
    elif 500 <= status_code < 600:
        return StatusMessage(code=ErrorCode.INTERNAL, message=message)
    else:
        return StatusMessage(code=ErrorCode.UNKNOWN, message=message)
'''

    def _bridge_publisher(self, d: dict) -> str:
        return f'''"""
Bridge publisher: sends translated messages to Service B's consumer.
"""
from __future__ import annotations
from service_b.schema import {d["message_class"]}, StatusMessage
from service_b.consumer import MessageConsumer
from bridge.translator import translate_{d["name"]}
from bridge.error_mapper import map_http_error
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class BridgePublisher:
    """Fetches from Service A and publishes to Service B."""

    def __init__(self, consumer: MessageConsumer):
        self.consumer = consumer

    def publish_record(self, json_data: dict) -> None:
        """Translate and publish a single record."""
        try:
            msg = translate_{d["name"]}(json_data)
            self.consumer.consume(msg)
        except Exception as e:
            logger.error(f"Translation failed: {{e}}")
            raise

    def publish_error(self, http_status: int, detail: str = "") -> None:
        """Map an HTTP error and publish as error status."""
        status_msg = map_http_error(http_status, detail)
        self.consumer.consume_error(status_msg)
'''

    def _bridge_config(self, d: dict) -> str:
        return f'''"""Bridge configuration."""
import os

SERVICE_A_BASE_URL = os.getenv("SERVICE_A_URL", "http://localhost:5000")
SERVICE_A_RESOURCE = "{d["flask_resource"]}"
POLL_INTERVAL_SECONDS = int(os.getenv("POLL_INTERVAL", "5"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
'''

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def _tests_fixtures(self, d: dict, seed: int) -> str:
        import base64 as b64mod
        raw_bytes = b"binary data here"
        b64_str = b64mod.b64encode(raw_bytes).decode()
        large_id = 9007199254740993 + seed  # differs per seed, always > 2^32
        return f'''"""
Test fixtures: sample JSON inputs and expected translated messages.
"""
import base64

# A large int64 value that would be corrupted by a 32-bit mask
LARGE_RECORD_ID = {large_id}

# Raw binary payload and its base64 encoding (as Service A would send it)
RAW_PAYLOAD = b"binary data here"
B64_PAYLOAD = base64.b64encode(RAW_PAYLOAD).decode()  # "{b64_str}"

# Minimal valid JSON dict from Service A (text_content oneof variant)
SAMPLE_JSON_TEXT = {{
    "{d["record_id_field"]}": LARGE_RECORD_ID,
    "{d["type_field"]}": "{d["sample_type"]}",
    "{d["payload_field"]}": B64_PAYLOAD,
    "{d["status_field"]}": "{d["status_values"][1]}",
    "{d["timestamp_field"]}": 1700000000,
    "{d["content_text_key"]}": "{d["sample_text"]}",
    # {d["content_binary_key"]} intentionally absent -> only content_text set
}}

# JSON dict using binary content oneof variant
SAMPLE_JSON_BINARY = {{
    "{d["record_id_field"]}": LARGE_RECORD_ID,
    "{d["type_field"]}": "{d["sample_type"]}",
    "{d["payload_field"]}": B64_PAYLOAD,
    "{d["status_field"]}": "{d["status_values"][2]}",
    "{d["timestamp_field"]}": 1700000001,
    # {d["content_text_key"]} intentionally absent -> only content_binary set
    "{d["content_binary_key"]}": B64_PAYLOAD,
}}
'''

    def _tests_translation(self, d: dict) -> str:
        return f'''"""
Tests for bridge/translator.py — each test targets one of the 4 translation bugs.
"""
import pytest
import base64
from bridge.translator import translate_event


def test_int64_not_truncated():
    """Bug 1: Large int64 values must not be truncated to 32-bit.

    9007199254740993 = 2^53 + 1, which exceeds int32 range (2^31 - 1 = 2147483647).
    After & 0xFFFFFFFF the value becomes 1, which is wrong.
    """
    large_id = 9007199254740993
    data = {{
        "{d["record_id_field"]}": large_id,
        "{d["type_field"]}": "test",
        "{d["payload_field"]}": "dGVzdA==",
        "{d["status_field"]}": "{d["status_values"][1]}",
        "{d["timestamp_field"]}": 0,
    }}
    msg = translate_event(data)
    assert msg.{d["record_id_field"]} == large_id, (
        f"int64 truncated: got {{msg.{d["record_id_field"]}}}, expected {{large_id}}. "
        "Remove the & 0xFFFFFFFF mask."
    )


def test_bytes_field_base64_decoded():
    """Bug 2: Payload must be base64-decoded bytes, not a raw string."""
    raw = b"binary data here"
    b64 = base64.b64encode(raw).decode()
    data = {{
        "{d["record_id_field"]}": 1,
        "{d["type_field"]}": "test",
        "{d["payload_field"]}": b64,
        "{d["status_field"]}": "{d["status_values"][1]}",
        "{d["timestamp_field"]}": 0,
    }}
    msg = translate_event(data)
    assert isinstance(msg.{d["payload_field"]}, bytes), (
        f"{d["payload_field"]} must be bytes, got {{type(msg.{d["payload_field"]})}}. "
        "Use base64.b64decode()."
    )
    assert msg.{d["payload_field"]} == raw, (
        f"Decoded payload mismatch: {{msg.{d["payload_field"]}!r}} != {{raw!r}}"
    )


def test_oneof_single_variant_text():
    """Bug 3: When text_content is present, only content_text must be set."""
    data = {{
        "{d["record_id_field"]}": 1,
        "{d["type_field"]}": "test",
        "{d["payload_field"]}": "dGVzdA==",
        "{d["status_field"]}": "{d["status_values"][1]}",
        "{d["timestamp_field"]}": 0,
        "{d["content_text_key"]}": "hello world",
        # {d["content_binary_key"]} absent
    }}
    msg = translate_event(data)
    assert not (msg.{d["content_text_key"]} and msg.{d["content_binary_key"]}), (
        f"oneof violation: both variants set "
        f"(text={{msg.{d["content_text_key"]}!r}}, binary={{msg.{d["content_binary_key"]}!r}}). "
        "Only set one oneof variant."
    )
    assert msg.{d["content_text_key"]} == "hello world", (
        f"content_text not set: {{msg.{d["content_text_key"]}!r}}"
    )


def test_oneof_single_variant_empty():
    """Bug 3: When neither content field present, both must remain falsy."""
    data = {{
        "{d["record_id_field"]}": 1,
        "{d["type_field"]}": "test",
        "{d["payload_field"]}": "dGVzdA==",
        "{d["status_field"]}": "{d["status_values"][1]}",
        "{d["timestamp_field"]}": 0,
    }}
    msg = translate_event(data)
    assert not (msg.{d["content_text_key"]} and msg.{d["content_binary_key"]}), (
        "oneof violation: both variants truthy when neither content key is in input"
    )


def test_enum_mapped_to_int():
    """Bug 4: Status must be an integer code, not a string name."""
    status_map = {{
        "{d["status_values"][0]}": 0,
        "{d["status_values"][1]}": 1,
        "{d["status_values"][2]}": 2,
        "{d["status_values"][3]}": 3,
    }}
    for status_str, expected_int in status_map.items():
        data = {{
            "{d["record_id_field"]}": 1,
            "{d["type_field"]}": "test",
            "{d["payload_field"]}": "dGVzdA==",
            "{d["status_field"]}": status_str,
            "{d["timestamp_field"]}": 0,
        }}
        msg = translate_event(data)
        assert isinstance(msg.{d["status_field"]}, int), (
            f"status must be int, got {{type(msg.{d["status_field"]})}}: {{msg.{d["status_field"]}!r}}. "
            "Map string through STATUS_MAP."
        )
        assert msg.{d["status_field"]} == expected_int, (
            f"{{status_str}} -> expected {{expected_int}}, got {{msg.{d["status_field"]}}}"
        )
'''

    def _tests_errors(self, d: dict) -> str:
        return f'''"""
Tests for bridge/error_mapper.py — tests the 2 HTTP→error code mapping bugs.
"""
import pytest
from bridge.error_mapper import map_http_error
from service_b.schema import ErrorCode


def test_200_maps_to_ok():
    """200 OK must map to ErrorCode.OK (0)."""
    result = map_http_error(200)
    assert result.code == ErrorCode.OK, f"200 -> expected OK(0), got {{result.code}}"


def test_400_maps_to_invalid_argument():
    """400 must map to INVALID_ARGUMENT (3)."""
    result = map_http_error(400, "bad request")
    assert result.code == ErrorCode.INVALID_ARGUMENT, (
        f"400 -> expected INVALID_ARGUMENT(3), got {{result.code}}"
    )


def test_404_maps_to_not_found():
    """Bug 5: HTTP 404 must map to NOT_FOUND (5), not INVALID_ARGUMENT (3)."""
    result = map_http_error(404, "resource not found")
    assert result.code == ErrorCode.NOT_FOUND, (
        f"404 must map to NOT_FOUND (5), got {{result.code}} ({{int(result.code)}}). "
        "Change ErrorCode.INVALID_ARGUMENT to ErrorCode.NOT_FOUND in error_mapper.py."
    )


def test_429_maps_to_resource_exhausted():
    """Bug 6: HTTP 429 must map to RESOURCE_EXHAUSTED (8), not INTERNAL (13)."""
    result = map_http_error(429, "too many requests")
    assert result.code == ErrorCode.RESOURCE_EXHAUSTED, (
        f"429 must map to RESOURCE_EXHAUSTED (8), got {{result.code}} ({{int(result.code)}}). "
        "Change ErrorCode.INTERNAL to ErrorCode.RESOURCE_EXHAUSTED in error_mapper.py."
    )


def test_500_maps_to_internal():
    """500 must map to INTERNAL (13)."""
    result = map_http_error(500, "server error")
    assert result.code == ErrorCode.INTERNAL, (
        f"500 -> expected INTERNAL(13), got {{result.code}}"
    )
'''

    def _tests_e2e(self, d: dict) -> str:
        return f'''"""
End-to-end pipeline test: verifies that the full bridge pipeline
(translate + publish + consume) works correctly after all bugs are fixed.
"""
import pytest
import base64
from bridge.publisher import BridgePublisher
from service_b.consumer import MessageConsumer
from service_b.schema import ErrorCode


def make_consumer_and_publisher():
    consumer = MessageConsumer()
    publisher = BridgePublisher(consumer)
    return consumer, publisher


def test_e2e_translate_and_consume():
    """Full pipeline: JSON -> translate -> consume without errors."""
    consumer, publisher = make_consumer_and_publisher()

    raw = b"end to end binary"
    b64 = base64.b64encode(raw).decode()
    json_data = {{
        "{d["record_id_field"]}": 9007199254740993,
        "{d["type_field"]}": "{d["sample_type"]}",
        "{d["payload_field"]}": b64,
        "{d["status_field"]}": "{d["status_values"][1]}",
        "{d["timestamp_field"]}": 1700000000,
        "{d["content_text_key"]}": "{d["sample_text"]}",
    }}

    # Should not raise (consumer validates types and oneof)
    publisher.publish_record(json_data)

    assert len(consumer.received) == 1
    msg = consumer.received[0]
    assert msg.{d["record_id_field"]} == 9007199254740993
    assert msg.{d["payload_field"]} == raw
    assert isinstance(msg.{d["status_field"]}, int)


def test_e2e_error_routing():
    """Error path: HTTP 404 and 429 must reach consumer with correct codes."""
    consumer, publisher = make_consumer_and_publisher()

    publisher.publish_error(404, "not found")
    publisher.publish_error(429, "rate limited")

    assert len(consumer.errors) == 2
    codes = [e.code for e in consumer.errors]
    assert ErrorCode.NOT_FOUND in codes, f"NOT_FOUND missing from errors: {{codes}}"
    assert ErrorCode.RESOURCE_EXHAUSTED in codes, (
        f"RESOURCE_EXHAUSTED missing from errors: {{codes}}"
    )
'''
