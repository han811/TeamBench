"""
Parameterized generator for MULTI3: Polyglot Interface Bug Fix.

TNI Pattern D (Cross-Language Contract): Spec has the complete interface
contract between a Python backend and a Python "frontend" handler (simulating
a JS/shell consumer). Bugs exist at the serialization boundary where data is
produced by the backend and consumed by the frontend.

Each seed produces:
  - Different data domain (user_profiles, product_catalog, event_stream, config_sync)
  - Different bug set (3-5 bugs from pool): wrong field name, wrong encoding,
    wrong date format, wrong null handling, wrong type coercion, wrong
    list/dict structure, wrong status key name
  - Workspace: backend/processor.py + frontend/handler.py + shared/schema.json
  - Spec: full interface contract with field mappings, encoding rules,
    date format, null semantics, response envelope shape
  - Brief: vague ("the system is broken — data isn't flowing correctly")

The 10+ grading checks cover:
  1. backend/processor.py imports without error
  2. frontend/handler.py imports without error
  3. shared/schema.json is valid JSON
  4. schema.json fields match spec contract (correct field names)
  5. Backend serialize() returns dict with correct field names
  6. Backend encodes dates in ISO-8601 format (YYYY-MM-DD)
  7. Backend handles None/null correctly (uses None not sentinel string)
  8. Frontend deserialize() reads correct field names
  9. Frontend handles null values correctly (maps None to default)
  10. Round-trip test: serialize then deserialize produces original data
  11. Field type contract satisfied (strings are strings, ints are ints)
  12. Envelope key correct ("data" not wrong key like "result" or "items")
"""
from __future__ import annotations

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── Domain configurations ─────────────────────────────────────────────────────
# Each domain has: (domain_key, display_name, entity, fields)
# fields: list of (field_name, type, nullable, description)
DOMAIN_CONFIGS = [
    (
        "user_profiles",
        "User Profiles",
        "user",
        [
            ("user_id",    "int",    False, "unique user identifier"),
            ("username",   "str",    False, "login handle"),
            ("email",      "str",    False, "contact email address"),
            ("full_name",  "str",    True,  "display name (optional)"),
            ("joined_at",  "date",   False, "account creation date (YYYY-MM-DD)"),
            ("is_active",  "bool",   False, "account enabled flag"),
            ("score",      "float",  True,  "reputation score (optional)"),
        ],
    ),
    (
        "product_catalog",
        "Product Catalog",
        "product",
        [
            ("product_id",   "int",   False, "unique product identifier"),
            ("sku",          "str",   False, "stock-keeping unit code"),
            ("name",         "str",   False, "product display name"),
            ("price",        "float", False, "unit price in USD"),
            ("category",     "str",   False, "product category"),
            ("released_on",  "date",  False, "release date (YYYY-MM-DD)"),
            ("description",  "str",   True,  "product description (optional)"),
        ],
    ),
    (
        "event_stream",
        "Event Stream",
        "event",
        [
            ("event_id",    "int",   False, "monotonic event identifier"),
            ("event_type",  "str",   False, "event classification label"),
            ("source",      "str",   False, "originating service name"),
            ("occurred_at", "date",  False, "event date (YYYY-MM-DD)"),
            ("payload",     "str",   True,  "JSON-encoded payload string (optional)"),
            ("severity",    "int",   False, "severity level 1-5"),
            ("resolved",    "bool",  False, "whether event has been resolved"),
        ],
    ),
    (
        "config_sync",
        "Config Sync",
        "config",
        [
            ("config_id",    "int",   False, "unique config entry identifier"),
            ("service_name", "str",   False, "target service identifier"),
            ("key",          "str",   False, "configuration key name"),
            ("value",        "str",   False, "configuration value (always string)"),
            ("updated_at",   "date",  False, "last update date (YYYY-MM-DD)"),
            ("enabled",      "bool",  False, "whether config entry is active"),
            ("note",         "str",   True,  "operator note (optional)"),
        ],
    ),
]

# ── Bug pool ──────────────────────────────────────────────────────────────────
# Each bug: (bug_id, layer, description_template, what_is_wrong, fix_description)
# Placeholders: {id_field}, {date_field}, {null_field}, {str_field}, {bool_field}
BUG_POOL = [
    # Backend bugs
    (
        "backend_wrong_id_key",
        "backend",
        "Backend serializer emits the ID field under the wrong key name",
        "id_key_wrong",    # discriminator used in code generation
        "Rename the emitted ID key to match the spec contract",
    ),
    (
        "backend_date_format",
        "backend",
        "Backend serializer formats dates as MM/DD/YYYY instead of YYYY-MM-DD (ISO-8601)",
        "date_format_wrong",
        "Change strftime format string to '%Y-%m-%d'",
    ),
    (
        "backend_null_sentinel",
        "backend",
        "Backend serializer encodes None values as the string 'NULL' instead of JSON null",
        "null_sentinel",
        "Return None (JSON null) for missing optional fields, not the string 'NULL'",
    ),
    (
        "backend_bool_as_int",
        "backend",
        "Backend serializer encodes boolean fields as integers (0/1) instead of true/false",
        "bool_as_int",
        "Return Python bool values directly so they serialize as JSON true/false",
    ),
    (
        "backend_wrong_envelope",
        "backend",
        "Backend wraps the record list under the key 'result' instead of 'data'",
        "wrong_envelope_key",
        "Change the envelope key from 'result' to 'data' per the spec contract",
    ),
    # Frontend bugs
    (
        "frontend_wrong_id_read",
        "frontend",
        "Frontend reads the ID field using the wrong key name",
        "id_key_read_wrong",
        "Read the ID using the correct field name from the spec contract",
    ),
    (
        "frontend_date_parse",
        "frontend",
        "Frontend parses dates assuming MM/DD/YYYY format instead of YYYY-MM-DD",
        "date_parse_wrong",
        "Parse dates with datetime.strptime(val, '%Y-%m-%d')",
    ),
    (
        "frontend_null_crash",
        "frontend",
        "Frontend does not guard against None values in nullable fields, causing AttributeError",
        "null_not_guarded",
        "Add a None-check before accessing optional field values",
    ),
    (
        "frontend_wrong_envelope",
        "frontend",
        "Frontend reads records from the 'result' key instead of the 'data' key",
        "wrong_envelope_read",
        "Read records from the 'data' key per the spec contract",
    ),
    (
        "schema_wrong_field_name",
        "schema",
        "shared/schema.json uses a wrong field name that disagrees with spec",
        "schema_field_wrong",
        "Correct the field name in schema.json to match the spec contract",
    ),
]

# ── Bug selection rules ───────────────────────────────────────────────────────
# We always inject 3-5 bugs. The combination varies per seed.
# We guarantee at least 1 backend bug, 1 frontend bug, 1 schema bug.
BUG_COMBOS = [
    # seed%5 -> list of bug_ids to inject
    ["backend_wrong_id_key",   "backend_date_format",   "frontend_null_crash",    "schema_wrong_field_name"],
    ["backend_null_sentinel",  "backend_wrong_envelope","frontend_wrong_envelope","frontend_date_parse",    "schema_wrong_field_name"],
    ["backend_bool_as_int",    "backend_date_format",   "frontend_wrong_id_read", "frontend_null_crash",    "schema_wrong_field_name"],
    ["backend_wrong_id_key",   "backend_null_sentinel", "frontend_wrong_envelope","schema_wrong_field_name"],
    ["backend_bool_as_int",    "backend_wrong_envelope","frontend_date_parse",    "frontend_null_crash",    "schema_wrong_field_name"],
]

# Wrong field-name alternatives (for backend_wrong_id_key / frontend_wrong_id_read)
WRONG_ID_KEY_ALTS = {
    "user_id":    ["uid",     "id",       "userId",    "user_key"],
    "product_id": ["pid",     "id",       "productId", "prod_id"],
    "event_id":   ["eid",     "id",       "eventId",   "evt_id"],
    "config_id":  ["cid",     "id",       "configId",  "cfg_id"],
}

# Wrong schema field-name alts (for schema_wrong_field_name)
WRONG_SCHEMA_FIELD_ALTS = {
    "user_profiles":   [("full_name",  "fullName"),   ("joined_at",  "joinedAt"),   ("is_active", "isActive")],
    "product_catalog": [("released_on","releaseDate"), ("product_id", "id"),         ("price",     "unitPrice")],
    "event_stream":    [("event_type", "type"),        ("occurred_at","occurredAt"), ("event_id",  "id")],
    "config_sync":     [("service_name","service"),    ("updated_at", "updatedAt"),  ("config_id", "id")],
}


class Generator(TaskGenerator):
    task_id = "MULTI3_polyglot"
    domain = "polyglot"
    difficulty = "hard"
    languages = ["python", "json"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # Pick domain
        domain_cfg = rng.choice(DOMAIN_CONFIGS)
        domain_key, domain_display, entity, fields = domain_cfg

        # Pick bug combo
        bug_combo_idx = seed % len(BUG_COMBOS)
        active_bug_ids = set(BUG_COMBOS[bug_combo_idx])
        active_bugs = [b for b in BUG_POOL if b[0] in active_bug_ids]

        # Derive specific wrong values
        id_field = fields[0][0]  # first field is always the ID
        date_field = next(f for f in fields if f[1] == "date")
        null_field = next(f for f in fields if f[2])  # first nullable field
        bool_field = next((f for f in fields if f[1] == "bool"), None)

        wrong_id_key = rng.choice(WRONG_ID_KEY_ALTS[id_field])
        wrong_schema_pair = rng.choice(WRONG_SCHEMA_FIELD_ALTS[domain_key])
        wrong_schema_field, wrong_schema_name = wrong_schema_pair

        # Sample data records for tests
        sample_records = self._make_sample_records(rng, domain_key, fields)

        # Generate workspace files
        processor_py = self._gen_processor(
            domain_key, entity, fields, id_field, date_field, null_field,
            bool_field, wrong_id_key, active_bug_ids
        )
        handler_py = self._gen_handler(
            domain_key, entity, fields, id_field, date_field, null_field,
            wrong_id_key, active_bug_ids
        )
        schema_json = self._gen_schema(
            domain_key, entity, fields, wrong_schema_field, wrong_schema_name,
            active_bug_ids
        )
        test_py = self._gen_test(
            domain_key, entity, fields, id_field, date_field, null_field,
            bool_field, sample_records
        )

        workspace_files = {
            "backend/processor.py": processor_py,
            "frontend/handler.py":  handler_py,
            "shared/schema.json":   schema_json,
            "tests/test_contract.py": test_py,
        }

        expected = {
            "domain": domain_key,
            "entity": entity,
            "bug_count": len(active_bugs),
            "active_bug_ids": sorted(active_bug_ids),
            "id_field": id_field,
            "date_field": date_field[0],
            "null_field": null_field[0],
            "correct_envelope_key": "data",
            "correct_date_format": "%Y-%m-%d",
            "wrong_id_key": wrong_id_key,
            "correct_id_key": id_field,
            "wrong_schema_field": wrong_schema_name,
            "correct_schema_field": wrong_schema_field,
            "bugs": [
                {
                    "id": b[0],
                    "layer": b[1],
                    "description": b[2],
                    "fix": b[4],
                }
                for b in active_bugs
            ],
        }

        spec_md  = self._gen_spec(domain_key, domain_display, entity, fields,
                                  id_field, date_field, null_field, bool_field,
                                  wrong_schema_field, wrong_schema_name, active_bug_ids)
        brief_md = self._gen_brief(domain_display, entity, len(active_bugs))

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # ── Sample data ───────────────────────────────────────────────────────────

    def _make_sample_records(self, rng: SeededRandom, domain_key: str,
                             fields: list) -> list[dict]:
        """Produce 3 concrete sample records for the test suite."""
        records = []
        for i in range(1, 4):
            rec = {}
            for fname, ftype, nullable, _ in fields:
                if ftype == "int":
                    rec[fname] = rng.randint(100, 9999)
                elif ftype == "float":
                    rec[fname] = round(rng.uniform(1.0, 999.0), 2)
                elif ftype == "bool":
                    rec[fname] = rng.choice([True, False])
                elif ftype == "date":
                    yr  = rng.randint(2020, 2024)
                    mo  = rng.randint(1, 12)
                    day = rng.randint(1, 28)
                    rec[fname] = f"{yr:04d}-{mo:02d}-{day:02d}"
                elif ftype == "str":
                    if nullable and rng.random() < 0.35:
                        rec[fname] = None
                    else:
                        rec[fname] = f"sample_{fname}_{i}"
            # Force id to be sequential
            rec[fields[0][0]] = i
        records.append(rec)
        return records

    # ── backend/processor.py ──────────────────────────────────────────────────

    def _gen_processor(self, domain_key: str, entity: str, fields: list,
                       id_field: str, date_field: tuple, null_field: tuple,
                       bool_field: tuple | None, wrong_id_key: str,
                       active_bugs: set) -> str:
        """
        Generate backend/processor.py with injected bugs.

        Bugs that may appear here:
          - backend_wrong_id_key    : emits id under wrong_id_key instead of id_field
          - backend_date_format     : uses '%m/%d/%Y' instead of '%Y-%m-%d'
          - backend_null_sentinel   : uses 'NULL' string for None
          - backend_bool_as_int     : casts bool to int(val) before emitting
          - backend_wrong_envelope  : wraps list under 'result' instead of 'data'
        """
        date_fname = date_field[0]
        null_fname  = null_field[0]
        null_ftype  = null_field[1]

        # Determine emitted id key
        emitted_id_key = wrong_id_key if "backend_wrong_id_key" in active_bugs else id_field

        # Date format string
        date_fmt = "'%m/%d/%Y'" if "backend_date_format" in active_bugs else "'%Y-%m-%d'"

        # Null encoding
        null_encode = (
            "'NULL'" if "backend_null_sentinel" in active_bugs else "None"
        )

        # Bool encoding
        bool_encode_comment = (
            "# BUG: bool cast to int — should remain bool"
            if "backend_bool_as_int" in active_bugs else ""
        )

        # Envelope key
        envelope_key = "'result'" if "backend_wrong_envelope" in active_bugs else "'data'"

        # Build the serialize_record function body
        field_lines = []
        for fname, ftype, nullable, _ in fields:
            if fname == id_field:
                field_lines.append(f"        {repr(emitted_id_key)}: record[{repr(fname)}],")
            elif ftype == "date":
                field_lines.append(
                    f"        {repr(fname)}: record[{repr(fname)}].strftime({date_fmt}) "
                    f"if record[{repr(fname)}] is not None else None,"
                )
            elif ftype == "bool" and "backend_bool_as_int" in active_bugs:
                field_lines.append(
                    f"        {repr(fname)}: int(record[{repr(fname)}]),  "
                    f"# BUG: should be bool, not int"
                )
            elif nullable:
                field_lines.append(
                    f"        {repr(fname)}: {null_encode} if record[{repr(fname)}] is None "
                    f"else record[{repr(fname)}],"
                )
            else:
                field_lines.append(f"        {repr(fname)}: record[{repr(fname)}],")

        fields_block = "\n".join(field_lines)

        return f'''"""
backend/processor.py — Data processor (Python backend).

Responsibilities:
  - Accept raw records as Python dicts (loaded from a datastore)
  - Serialize them into the wire format defined by shared/schema.json
  - Wrap results in the standard envelope before returning to the caller

WARNING: This file contains intentional bugs for the TeamBench exercise.
"""
from __future__ import annotations

import datetime
import json
from typing import Any


# ---------------------------------------------------------------------------
# Internal record type (as stored in the datastore)
# ---------------------------------------------------------------------------

def make_record(**kwargs) -> dict:
    """Helper: build a typed record dict. Dates accepted as date objects or ISO strings."""
    rec = dict(kwargs)
    # Coerce date strings to date objects for internal storage
    for k, v in rec.items():
        if isinstance(v, str):
            try:
                rec[k] = datetime.date.fromisoformat(v)
            except ValueError:
                pass
    return rec


# ---------------------------------------------------------------------------
# Serialization — converts internal records to wire format
# ---------------------------------------------------------------------------

def serialize_record(record: dict) -> dict:
    """
    Serialize one internal record to the wire format dict.

    Contract (from shared/schema.json):
      - ID field key: {repr(id_field)}
      - Date format: YYYY-MM-DD (ISO-8601)
      - Null representation: JSON null (Python None)
      - Boolean representation: JSON true/false (Python bool)
    """
    return {{
{fields_block}
    }}


def serialize_batch(records: list[dict]) -> dict:
    """
    Serialize a list of records and wrap in the response envelope.

    Envelope contract:
      {{
        "data": [ <record>, ... ],
        "count": <int>
      }}
    """
    serialized = [serialize_record(r) for r in records]
    return {{
        {envelope_key}: serialized,
        "count": len(serialized),
    }}


# ---------------------------------------------------------------------------
# Deserialization — converts wire format back to internal records (for testing)
# ---------------------------------------------------------------------------

def deserialize_record(wire: dict) -> dict:
    """
    Convert a wire-format dict back to an internal record.
    Used by the round-trip test in tests/test_contract.py.
    """
    rec = dict(wire)
    # Restore date fields from ISO strings
    date_fields = {{{repr(date_fname)}}}
    for k in date_fields:
        if k in rec and rec[k] is not None:
            if isinstance(rec[k], str):
                rec[k] = datetime.date.fromisoformat(rec[k])
    return rec
'''

    # ── frontend/handler.py ───────────────────────────────────────────────────

    def _gen_handler(self, domain_key: str, entity: str, fields: list,
                     id_field: str, date_field: tuple, null_field: tuple,
                     wrong_id_key: str, active_bugs: set) -> str:
        """
        Generate frontend/handler.py with injected bugs.

        Bugs that may appear here:
          - frontend_wrong_id_read  : reads id using wrong_id_key instead of id_field
          - frontend_date_parse     : parses with '%m/%d/%Y' instead of '%Y-%m-%d'
          - frontend_null_crash     : no None-guard on nullable field access
          - frontend_wrong_envelope : reads from 'result' key instead of 'data'
        """
        date_fname  = date_field[0]
        null_fname  = null_field[0]
        null_ftype  = null_field[1]

        # ID key used when reading
        read_id_key = wrong_id_key if "frontend_wrong_id_read" in active_bugs else id_field

        # Date parse format
        date_parse = "'%m/%d/%Y'" if "frontend_date_parse" in active_bugs else "'%Y-%m-%d'"

        # Envelope key used when reading
        env_key = "'result'" if "frontend_wrong_envelope" in active_bugs else "'data'"

        # Null field access pattern
        if "frontend_null_crash" in active_bugs:
            # Comma must come before the comment so Python parses the dict entry correctly.
            null_line = (
                f"        {repr(null_fname)}: wire_record[{repr(null_fname)}].strip(),"
                f"  # BUG: crashes when {null_fname} is None — missing None-guard"
            )
        else:
            null_line = (
                f"        {repr(null_fname)}: wire_record[{repr(null_fname)}].strip() "
                f"if wire_record[{repr(null_fname)}] is not None else None,"
            )

        # Build field extraction lines
        field_lines = []
        for fname, ftype, nullable, _ in fields:
            if fname == id_field:
                field_lines.append(
                    f"        {repr(fname)}: wire_record[{repr(read_id_key)}],"
                )
            elif ftype == "date":
                field_lines.append(
                    f"        {repr(fname)}: datetime.datetime.strptime("
                    f"wire_record[{repr(fname)}], {date_parse}).date(),"
                )
            elif fname == null_fname and nullable:
                field_lines.append(null_line)
            elif nullable:
                field_lines.append(
                    f"        {repr(fname)}: wire_record.get({repr(fname)}),",
                )
            else:
                field_lines.append(
                    f"        {repr(fname)}: wire_record[{repr(fname)}],",
                )

        fields_block = "\n".join(field_lines)

        return f'''"""
frontend/handler.py — Data consumer handler (Python, simulating a frontend consumer).

Responsibilities:
  - Accept the wire-format envelope from the backend
  - Deserialize records into typed Python dicts
  - Expose helper functions for downstream display/processing logic

WARNING: This file contains intentional bugs for the TeamBench exercise.
"""
from __future__ import annotations

import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Deserialization — converts wire-format records to typed Python dicts
# ---------------------------------------------------------------------------

def deserialize_record(wire_record: dict) -> dict:
    """
    Deserialize one wire-format record into a typed Python dict.

    Contract (from shared/schema.json):
      - ID field key: {repr(id_field)}
      - Date format: YYYY-MM-DD (ISO-8601)
      - Null values: JSON null (Python None) — must not crash on None
      - Boolean values: JSON true/false (Python bool)
    """
    return {{
{fields_block}
    }}


def process_envelope(envelope: dict) -> list[dict]:
    """
    Extract and deserialize all records from a response envelope.

    Envelope contract:
      {{
        "data": [ <record>, ... ],
        "count": <int>
      }}
    """
    raw_records = envelope[{env_key}]
    return [deserialize_record(r) for r in raw_records]


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def format_record(record: dict) -> str:
    """Return a human-readable string for one deserialized record."""
    parts = []
    for k, v in record.items():
        if isinstance(v, datetime.date):
            parts.append(f"{{k}}={{v.isoformat()}}")
        elif v is None:
            parts.append(f"{{k}}=<none>")
        else:
            parts.append(f"{{k}}={{v}}")
    return ", ".join(parts)


def display_all(envelope: dict) -> list[str]:
    """Process envelope and return formatted string list."""
    records = process_envelope(envelope)
    return [format_record(r) for r in records]
'''

    # ── shared/schema.json ────────────────────────────────────────────────────

    def _gen_schema(self, domain_key: str, entity: str, fields: list,
                    wrong_schema_field: str, wrong_schema_name: str,
                    active_bugs: set) -> str:
        """
        Generate shared/schema.json with an injected field-name bug if active.
        """
        import json

        schema_fields = {}
        for fname, ftype, nullable, desc in fields:
            # Apply the wrong field name if the schema bug is active
            emitted_name = (
                wrong_schema_name
                if "schema_wrong_field_name" in active_bugs and fname == wrong_schema_field
                else fname
            )
            schema_fields[emitted_name] = {
                "type": ftype,
                "nullable": nullable,
                "description": desc,
            }

        schema = {
            "$schema": "http://json-schema.org/draft-07/schema",
            "title": f"{entity.capitalize()} wire format",
            "description": (
                f"Interface contract between backend/processor.py and "
                f"frontend/handler.py for domain '{domain_key}'"
            ),
            "envelope": {
                "data": {
                    "type": "array",
                    "description": "Array of serialized records. Key MUST be 'data'.",
                },
                "count": {
                    "type": "integer",
                    "description": "Number of records in the data array.",
                },
            },
            "record_fields": schema_fields,
            "encoding_rules": {
                "dates": "ISO-8601 format: YYYY-MM-DD",
                "nulls": "JSON null (never use sentinel strings like 'NULL' or 'N/A')",
                "booleans": "JSON true/false (never use 0/1 integers)",
                "strings": "UTF-8, no trailing whitespace",
            },
        }
        return json.dumps(schema, indent=2)

    # ── tests/test_contract.py ────────────────────────────────────────────────

    def _gen_test(self, domain_key: str, entity: str, fields: list,
                  id_field: str, date_field: tuple, null_field: tuple,
                  bool_field: tuple | None, sample_records: list) -> str:
        """
        Generate a comprehensive self-contained test suite (10+ checks).

        Design principle: backend tests use self.wire (produced by the buggy
        backend, so backend bugs cause those tests to fail). Frontend tests use
        self.correct_wire (hardcoded with correct field names/values), so
        frontend bugs fail *only* the frontend tests without cascading from
        unrelated backend bugs.
        """
        date_fname  = date_field[0]
        null_fname  = null_field[0]
        null_ftype  = null_field[1]
        bool_fname  = bool_field[0] if bool_field else None
        entity_cap  = entity.capitalize()

        # Build the internal record (original) — used as input to backend.
        # Rule: id_field=42, nullable fields=None, date=date(2024,6,15),
        #       bool=True, float=19.99, int=7, str='test_value'.
        field_inits = []
        for fname, ftype, nullable, _ in fields:
            if fname == id_field:
                field_inits.append(f"            {repr(fname)}: 42,")
            elif nullable:
                field_inits.append(f"            {repr(fname)}: None,  # nullable")
            elif ftype == "date":
                field_inits.append(f"            {repr(fname)}: datetime.date(2024, 6, 15),")
            elif ftype == "bool":
                field_inits.append(f"            {repr(fname)}: True,")
            elif ftype == "float":
                field_inits.append(f"            {repr(fname)}: 19.99,")
            elif ftype == "int":
                field_inits.append(f"            {repr(fname)}: 7,")
            else:
                field_inits.append(f"            {repr(fname)}: 'test_value',")
        field_inits_block = "\n".join(field_inits)

        # Build the correct wire dict (hardcoded, independent of backend bugs).
        # This is what a *fixed* backend would produce — used by frontend tests.
        # Rule: id_field=42, nullable=None, date='2024-06-15',
        #       bool=True, float=19.99, int=7, str='test_value'.
        correct_wire_lines = []
        for fname, ftype, nullable, _ in fields:
            if fname == id_field:
                correct_wire_lines.append(f"            {repr(fname)}: 42,  # matches self.original[{repr(id_field)}]")
            elif nullable:
                correct_wire_lines.append(f"            {repr(fname)}: None,  # nullable")
            elif ftype == "date":
                correct_wire_lines.append(f"            {repr(fname)}: '2024-06-15',")
            elif ftype == "bool":
                correct_wire_lines.append(f"            {repr(fname)}: True,")
            elif ftype == "float":
                correct_wire_lines.append(f"            {repr(fname)}: 19.99,")
            elif ftype == "int":
                correct_wire_lines.append(f"            {repr(fname)}: 7,")
            else:
                correct_wire_lines.append(f"            {repr(fname)}: 'test_value',")
        correct_wire_block = "\n".join(correct_wire_lines)

        # Correct envelope (what a fixed backend+envelope produces)
        correct_envelope_lines = (
            f"        self.correct_envelope = {{\n"
            f"            'data': [self.correct_wire],\n"
            f"            'count': 1,\n"
            f"        }}"
        )

        # Assertions for round-trip test (uses correct_wire -> handler)
        # correct_wire values: id_field=42, date='2024-06-15', bool=True,
        #   float=19.99, other int=7, nullable str=None, str='test_value'
        roundtrip_asserts = []
        for fname, ftype, nullable, _ in fields:
            if fname == id_field:
                # ID field is always 42 in correct_wire
                roundtrip_asserts.append(
                    f"        self.assertEqual(recovered[{repr(fname)}], 42, "
                    f"msg='round-trip failed for id field {fname}')"
                )
            elif ftype == "date":
                roundtrip_asserts.append(
                    f"        self.assertEqual(recovered[{repr(fname)}], "
                    f"datetime.date(2024, 6, 15), "
                    f"msg='round-trip failed for date field {fname}')"
                )
            elif nullable:
                roundtrip_asserts.append(
                    f"        self.assertIsNone(recovered.get({repr(fname)}), "
                    f"msg='round-trip: nullable {fname} should be None')"
                )
            elif ftype == "bool":
                roundtrip_asserts.append(
                    f"        self.assertIs(recovered[{repr(fname)}], True, "
                    f"msg='round-trip: bool {fname} must be Python bool True')"
                )
            elif ftype == "float":
                roundtrip_asserts.append(
                    f"        self.assertAlmostEqual(recovered[{repr(fname)}], 19.99, places=2, "
                    f"msg='round-trip failed for float field {fname}')"
                )
            elif ftype == "int":
                roundtrip_asserts.append(
                    f"        self.assertEqual(recovered[{repr(fname)}], 7, "
                    f"msg='round-trip failed for int field {fname}')"
                )
            else:
                roundtrip_asserts.append(
                    f"        self.assertEqual(recovered[{repr(fname)}], 'test_value', "
                    f"msg='round-trip failed for str field {fname}')"
                )
        roundtrip_block = "\n".join(roundtrip_asserts)

        # Optional bool tests
        bool_tests = ""
        if bool_fname:
            bool_tests = f"""
    # ------------------------------------------------------------------
    # Test 7: Boolean fields must remain Python bool (not int 0/1)
    # ------------------------------------------------------------------
    def test_bool_is_bool(self):
        \"\"\"serialize_record must emit Python bool for {bool_fname}, not int.\"\"\"
        rec = dict(self.original)
        rec[{repr(bool_fname)}] = True
        wire = processor.serialize_record(rec)
        val = wire[{repr(bool_fname)}]
        self.assertIsInstance(
            val, bool,
            msg=f"Expected bool for {bool_fname}, got {{type(val).__name__}}: {{val!r}}"
        )

    # ------------------------------------------------------------------
    # Test 8: Frontend bool passthrough (uses correct_wire to isolate)
    # ------------------------------------------------------------------
    def test_frontend_bool_passthrough(self):
        \"\"\"Frontend handler must preserve bool type for {bool_fname}.\"\"\"
        wire = dict(self.correct_wire)
        wire[{repr(bool_fname)}] = True
        recovered = handler.deserialize_record(wire)
        self.assertIsInstance(
            recovered.get({repr(bool_fname)}),
            (bool, type(None)),
            msg=f"{bool_fname} must deserialize to bool or None, got {{type(recovered.get({repr(bool_fname)})).__name__}}"
        )
"""

        # spec_fields list literal for schema test
        spec_fields_list = repr([f[0] for f in fields])

        return f'''"""
Test suite for MULTI3_polyglot — Interface contract verification.
Tests cover backend serialization, frontend deserialization, schema validity,
and end-to-end round-trip correctness.

Design:
  - Backend tests use self.wire (output of buggy backend) so backend bugs fail them.
  - Frontend tests use self.correct_wire (hardcoded correct wire dict) so frontend
    bugs fail independently without cascading from backend bugs.

Do NOT modify this file.
"""
from __future__ import annotations

import datetime
import json
import os
import sys
import unittest

# ---------------------------------------------------------------------------
# Path setup — allow importing from sibling directories
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_WORKSPACE = os.path.dirname(_HERE)
sys.path.insert(0, _WORKSPACE)

import backend.processor as processor
import frontend.handler as handler


class {entity_cap}ContractTestCase(unittest.TestCase):

    def setUp(self):
        """Build canonical records for use across tests."""
        # Internal (datastore) record — input to the backend
        self.original = {{
{field_inits_block}
        }}
        # Wire produced by the backend under test (may be buggy)
        self.wire = processor.serialize_record(self.original)
        # Envelope produced by the backend under test
        self.envelope = processor.serialize_batch([self.original])

        # Correct wire dict — hardcoded, independent of backend bugs.
        # Frontend tests use this so they are isolated from backend bugs.
        self.correct_wire = {{
{correct_wire_block}
        }}
{correct_envelope_lines}

    # ------------------------------------------------------------------
    # Test 1: Modules import cleanly
    # ------------------------------------------------------------------
    def test_processor_imports(self):
        """backend/processor.py must import without error."""
        import importlib
        self.assertIsNotNone(importlib.import_module("backend.processor"))

    def test_handler_imports(self):
        """frontend/handler.py must import without error."""
        import importlib
        self.assertIsNotNone(importlib.import_module("frontend.handler"))

    # ------------------------------------------------------------------
    # Test 2: schema.json validity and field names
    # ------------------------------------------------------------------
    def test_schema_json_valid(self):
        """shared/schema.json must be parseable JSON with required top-level keys."""
        schema_path = os.path.join(_WORKSPACE, "shared", "schema.json")
        self.assertTrue(os.path.exists(schema_path), msg="shared/schema.json not found")
        with open(schema_path) as f:
            schema = json.load(f)
        self.assertIn("record_fields", schema, msg="schema.json missing 'record_fields' key")
        self.assertIn("envelope", schema, msg="schema.json missing 'envelope' key")

    def test_schema_fields_match_spec(self):
        """shared/schema.json record_fields must list all spec-defined field names."""
        schema_path = os.path.join(_WORKSPACE, "shared", "schema.json")
        with open(schema_path) as f:
            schema = json.load(f)
        record_fields = schema["record_fields"]
        spec_fields = {spec_fields_list}
        for field_name in spec_fields:
            self.assertIn(
                field_name, record_fields,
                msg=(
                    f"schema.json missing required field {{field_name!r}} — "
                    f"found: {{list(record_fields.keys())}}"
                )
            )

    # ------------------------------------------------------------------
    # Test 3: Backend emits correct ID field name
    # ------------------------------------------------------------------
    def test_backend_id_field_name(self):
        """serialize_record must emit the ID under the key {repr(id_field)}."""
        self.assertIn(
            {repr(id_field)}, self.wire,
            msg=f"Wire record missing key {repr(id_field)}. Keys present: {{list(self.wire.keys())}}"
        )

    # ------------------------------------------------------------------
    # Test 4: Backend date format is ISO-8601 (YYYY-MM-DD)
    # ------------------------------------------------------------------
    def test_backend_date_format(self):
        """serialize_record must format {date_fname} as YYYY-MM-DD (ISO-8601)."""
        date_val = self.wire.get({repr(date_fname)})
        self.assertIsInstance(date_val, str,
            msg=f"{date_fname} must be a string in wire format, got {{type(date_val).__name__}}")
        parts = date_val.split("-")
        self.assertEqual(len(parts), 3,
            msg=f"Expected YYYY-MM-DD with 3 dash-separated parts, got {{date_val!r}}")
        self.assertEqual(len(parts[0]), 4,
            msg=f"Year part must be 4 digits (YYYY), got {{parts[0]!r}} from {{date_val!r}}")
        try:
            datetime.date.fromisoformat(date_val)
        except ValueError:
            self.fail(f"{date_fname} value {{date_val!r}} is not valid ISO-8601")

    # ------------------------------------------------------------------
    # Test 5: Backend null handling — None, not sentinel string
    # ------------------------------------------------------------------
    def test_backend_null_is_none(self):
        """serialize_record must emit None for nullable {null_fname} when value is None."""
        null_val = self.wire.get({repr(null_fname)})
        self.assertIsNone(
            null_val,
            msg=(
                f"Expected None for nullable field {null_fname}, got {{null_val!r}}. "
                f"Do not use sentinel strings like 'NULL'."
            )
        )

    # ------------------------------------------------------------------
    # Test 6: Backend envelope uses 'data' key
    # ------------------------------------------------------------------
    def test_envelope_key(self):
        """serialize_batch must wrap serialized records under the key 'data'."""
        self.assertIn(
            "data", self.envelope,
            msg=f"Envelope missing 'data' key. Keys present: {{list(self.envelope.keys())}}"
        )
        self.assertIsInstance(self.envelope["data"], list,
            msg="envelope['data'] must be a list")
        self.assertEqual(self.envelope.get("count"), 1,
            msg=f"envelope['count'] should be 1, got {{self.envelope.get('count')}}")
{bool_tests}
    # ------------------------------------------------------------------
    # Test 9: Frontend reads correct ID field name (uses correct_wire)
    # ------------------------------------------------------------------
    def test_frontend_id_field_read(self):
        """deserialize_record must read the ID from key {repr(id_field)}."""
        recovered = handler.deserialize_record(self.correct_wire)
        self.assertIn(
            {repr(id_field)}, recovered,
            msg=f"Deserialized record missing key {repr(id_field)}. Keys: {{list(recovered.keys())}}"
        )
        self.assertEqual(
            recovered[{repr(id_field)}], 42,
            msg=f"Frontend read wrong value for {id_field}: {{recovered[{repr(id_field)}]!r}}"
        )

    # ------------------------------------------------------------------
    # Test 10: Frontend null guard — no crash on None (uses correct_wire)
    # ------------------------------------------------------------------
    def test_frontend_null_guard(self):
        """deserialize_record must not crash when nullable {null_fname} is None."""
        wire = dict(self.correct_wire)
        wire[{repr(null_fname)}] = None
        try:
            recovered = handler.deserialize_record(wire)
        except AttributeError as exc:
            self.fail(
                f"deserialize_record crashed with AttributeError when {null_fname}=None: {{exc}}"
            )
        self.assertIsNone(
            recovered.get({repr(null_fname)}),
            msg=f"Deserialized {null_fname} should be None, got {{recovered.get({repr(null_fname)})!r}}"
        )

    # ------------------------------------------------------------------
    # Test 11: Frontend parses dates as datetime.date (uses correct_wire)
    # ------------------------------------------------------------------
    def test_frontend_date_parse(self):
        """deserialize_record must parse {date_fname} into a datetime.date object."""
        recovered = handler.deserialize_record(self.correct_wire)
        date_val = recovered.get({repr(date_fname)})
        self.assertIsInstance(
            date_val, datetime.date,
            msg=f"Expected datetime.date for {date_fname}, got {{type(date_val).__name__}}"
        )
        self.assertEqual(
            date_val, datetime.date(2024, 6, 15),
            msg=f"{date_fname} parsed to wrong date: {{date_val!r}}"
        )

    # ------------------------------------------------------------------
    # Test 12: Frontend reads records from 'data' envelope key
    # ------------------------------------------------------------------
    def test_frontend_envelope_read(self):
        """process_envelope must extract records from the 'data' key."""
        records = handler.process_envelope(self.correct_envelope)
        self.assertIsInstance(records, list,
            msg="process_envelope must return a list")
        self.assertEqual(len(records), 1,
            msg=f"Expected 1 deserialized record, got {{len(records)}}")

    # ------------------------------------------------------------------
    # Test 13: Full round-trip using correct_wire -> handler
    # ------------------------------------------------------------------
    def test_round_trip(self):
        """Deserializing a correctly-formed wire dict must reproduce all field values."""
        recovered = handler.deserialize_record(self.correct_wire)
{roundtrip_block}


if __name__ == "__main__":
    unittest.main(verbosity=2)
'''

    # ── spec.md ───────────────────────────────────────────────────────────────

    def _gen_spec(self, domain_key: str, domain_display: str, entity: str,
                  fields: list, id_field: str, date_field: tuple,
                  null_field: tuple, bool_field: tuple | None,
                  wrong_schema_field: str, wrong_schema_name: str,
                  active_bugs: set) -> str:
        date_fname = date_field[0]
        null_fname = null_field[0]
        bool_fname = bool_field[0] if bool_field else None

        field_table_rows = "\n".join(
            f"| `{fname}` | `{ftype}` | {'yes' if nullable else 'no'} | {desc} |"
            for fname, ftype, nullable, desc in fields
        )

        bug_list_items = []
        for bug_id in sorted(active_bugs):
            bug = next(b for b in BUG_POOL if b[0] == bug_id)
            bug_list_items.append(f"- **{bug[1].capitalize()} layer**: {bug[2]}")
        bug_list = "\n".join(bug_list_items)

        return f"""# MULTI3: Polyglot Interface Bug Fix — Full Specification (Planner Only)

## Overview

A two-component data pipeline for the **{domain_display}** domain.  The Python
backend (`backend/processor.py`) serializes internal records into a wire format
defined by `shared/schema.json`.  The Python frontend (`frontend/handler.py`)
consumes that wire format.

The system has **{len(active_bugs)} bugs** spread across the two components and
the shared schema. All bugs must be fixed so that `python3 -m pytest
tests/test_contract.py -v` (or `python3 tests/test_contract.py`) passes all
tests.

---

## Interface Contract

### Wire Format — Envelope

Every response from the backend is wrapped in an envelope:

```json
{{
  "data": [ <record>, ... ],
  "count": <integer>
}}
```

- The array of records MUST be under the key **`"data"`** (not `"result"`, not `"items"`).
- `count` MUST equal the length of the `data` array.

### Wire Format — Record Fields

| Field | Type | Nullable | Description |
|-------|------|----------|-------------|
{field_table_rows}

### Encoding Rules

| Concern | Rule |
|---------|------|
| **Dates** | ISO-8601 string `YYYY-MM-DD` — never `MM/DD/YYYY` |
| **Nulls** | JSON `null` (Python `None`) — never the string `"NULL"` or `"N/A"` |
| **Booleans** | JSON `true`/`false` (Python `bool`) — never integers `0`/`1` |
| **Strings** | UTF-8, stripped of leading/trailing whitespace |
| **ID field** | Key name MUST be `"{id_field}"` in the wire dict |

---

## Bug Inventory

{bug_list}

### Additional schema bug

`shared/schema.json` declares one field under the wrong name
(`"{wrong_schema_name}"` instead of `"{wrong_schema_field}"`). The schema must
agree with the encoding rules table above.

---

## File Layout

```
workspace/
  backend/
    processor.py       # Python backend — serialize + batch functions
  frontend/
    handler.py         # Python frontend consumer — deserialize + display
  shared/
    schema.json        # Interface contract (JSON Schema-style)
  tests/
    test_contract.py   # Test suite — DO NOT MODIFY
```

---

## Expected Outcome

After all {len(active_bugs)} fixes:

```
python3 tests/test_contract.py
```

Output:
```
.............
----------------------------------------------------------------------
Ran 13 tests in 0.XXXs

OK
```

All 13 tests pass:

1. `test_processor_imports` — backend module imports cleanly
2. `test_handler_imports` — frontend module imports cleanly
3. `test_schema_json_valid` — schema.json is valid JSON with required keys
4. `test_schema_fields_match_spec` — schema field names match the spec contract
5. `test_backend_id_field_name` — backend emits correct ID key `"{id_field}"`
6. `test_backend_date_format` — backend formats dates as `YYYY-MM-DD`
7. `test_backend_null_is_none` — backend emits `null` not sentinel string for `{null_fname}`
8. `test_envelope_key` — backend wraps records under `"data"` key
9. `test_bool_is_bool` — backend emits Python `bool` not `int` for boolean fields
10. `test_frontend_id_field_read` — frontend reads ID from correct key `"{id_field}"`
11. `test_frontend_null_guard` — frontend handles `None` in `{null_fname}` without crash
12. `test_frontend_date_parse` — frontend parses `{date_fname}` as `datetime.date`
13. `test_frontend_envelope_read` — frontend reads records from `"data"` key
14. `test_round_trip` — full serialize → deserialize round-trip reproduces original data

---

## Constraints

- Do NOT modify `tests/test_contract.py`
- Only Python standard library is required (`json`, `datetime`)
- `shared/schema.json` is informational — tests read it but the pipeline code must also be consistent with it
"""

    # ── brief.md ──────────────────────────────────────────────────────────────

    def _gen_brief(self, domain_display: str, entity: str, bug_count: int) -> str:
        return f"""# MULTI3: Polyglot Interface Bug Fix (Brief)

The {domain_display} data pipeline is broken. The backend processor and
frontend handler disagree on the wire format, causing data to be lost or
corrupted at the interface boundary.

Fix the bugs so that `python3 tests/test_contract.py` passes all tests.

Files to investigate:
- `backend/processor.py` — Python data serializer
- `frontend/handler.py` — Python data consumer
- `shared/schema.json` — shared interface schema (may also be wrong)

Do NOT modify `tests/test_contract.py`.
"""
