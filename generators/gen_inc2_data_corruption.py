"""
Parameterized generator for INC2: Data Corruption Recovery.

Each seed produces:
  - Different record schema (customer, transaction, inventory, or sensor records)
  - Different corruption pattern (null fields, type mismatches, truncated strings,
    out-of-range numbers)
  - Different number of corrupted records (5-15 out of 50)
  - Different shadow field names
  - Different validation rules (ranges, required fields, checksums)

TNI driver: The spec tells the Planner the exact schema, which fields were corrupted,
the shadow-field recovery procedure, and the checksum/range validation rules. The brief
only says "some records are corrupted, fix them." Without the spec the Executor cannot
know to use shadow fields (vs. deletion/interpolation) or which records are affected.

The grader checks:
  1. data.json exists and is valid JSON
  2. All 50 records present (no deletion)
  3. No previously-good records modified
  4. Corrupted records have correct field values (recovered from shadow)
  5. All records pass schema validation
  6. All numeric fields within specified ranges
  7. All required fields present and non-null
  8. recover.py runs without error (exit 0)
  9. validate.py exits 0 (all records pass)
  10. Attestation verdict=pass
"""
from __future__ import annotations

import json
import hashlib

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# ---------------------------------------------------------------------------
# Schema templates
# ---------------------------------------------------------------------------

# Each schema defines:
#   name        – display name for the record type
#   fields      – list of (field_name, type, min, max) where min/max apply to numeric
#   required    – field names that must be non-null and non-empty
#   corruptible – field names that the corruption event could affect
#   shadow_prefix – prefix used for shadow backup fields
SCHEMAS = [
    {
        "name": "customer",
        "fields": [
            ("customer_id", "int", 1000, 9999),
            ("name", "str", None, None),
            ("age", "int", 18, 99),
            ("credit_score", "int", 300, 850),
            ("account_balance", "float", 0.0, 100000.0),
            ("region", "str", None, None),
            ("status", "str", None, None),
        ],
        "required": ["customer_id", "name", "age", "credit_score", "status"],
        "corruptible": ["age", "credit_score", "account_balance"],
        "shadow_prefix": "_bak_",
        "enum_fields": {"status": ["active", "inactive", "suspended"], "region": ["north", "south", "east", "west"]},
    },
    {
        "name": "transaction",
        "fields": [
            ("txn_id", "int", 100000, 999999),
            ("user_id", "int", 1, 9999),
            ("amount", "float", 0.01, 50000.0),
            ("fee", "float", 0.0, 500.0),
            ("quantity", "int", 1, 1000),
            ("category", "str", None, None),
            ("currency", "str", None, None),
        ],
        "required": ["txn_id", "user_id", "amount", "quantity", "currency"],
        "corruptible": ["amount", "fee", "quantity"],
        "shadow_prefix": "_prev_",
        "enum_fields": {"currency": ["USD", "EUR", "GBP", "JPY"], "category": ["retail", "wholesale", "online", "refund"]},
    },
    {
        "name": "inventory",
        "fields": [
            ("item_id", "int", 10000, 99999),
            ("sku", "str", None, None),
            ("stock_count", "int", 0, 10000),
            ("reorder_level", "int", 0, 500),
            ("unit_cost", "float", 0.01, 9999.99),
            ("warehouse", "str", None, None),
            ("category", "str", None, None),
        ],
        "required": ["item_id", "sku", "stock_count", "reorder_level", "unit_cost"],
        "corruptible": ["stock_count", "reorder_level", "unit_cost"],
        "shadow_prefix": "_snap_",
        "enum_fields": {"warehouse": ["WH-A", "WH-B", "WH-C", "WH-D"], "category": ["electronics", "clothing", "food", "tools"]},
    },
    {
        "name": "sensor",
        "fields": [
            ("sensor_id", "int", 1, 999),
            ("device_tag", "str", None, None),
            ("temperature", "float", -50.0, 150.0),
            ("humidity", "float", 0.0, 100.0),
            ("pressure", "float", 800.0, 1100.0),
            ("location", "str", None, None),
            ("unit", "str", None, None),
        ],
        "required": ["sensor_id", "device_tag", "temperature", "humidity", "pressure"],
        "corruptible": ["temperature", "humidity", "pressure"],
        "shadow_prefix": "_ref_",
        "enum_fields": {"unit": ["metric", "imperial"], "location": ["indoor", "outdoor", "lab", "field"]},
    },
]

# Corruption patterns applied to a numeric field:
# (pattern_id, description, corrupt_fn_template, detect_hint)
# corrupt_fn_template is a Python expression string that receives `v` = original value
CORRUPTION_PATTERNS = [
    (
        "string_garbage",
        "numeric field replaced with a non-numeric string",
        lambda v, rng: rng.choice(["N/A", "ERR", "??", "CORRUPT", "---"]),
    ),
    (
        "null_value",
        "field set to null (None in JSON)",
        lambda v, rng: None,
    ),
    (
        "out_of_range_high",
        "numeric field inflated far above valid maximum",
        lambda v, rng: v * rng.randint(100, 999) if isinstance(v, (int, float)) else None,
    ),
    (
        "truncated_string",
        "float field truncated to a short non-numeric prefix string",
        lambda v, rng: str(v)[:1] + "!" if v is not None else "!",
    ),
    (
        "zero_fill",
        "field zeroed out (0 or 0.0), invalid for fields that require positive values",
        lambda v, rng: 0,
    ),
]


class Generator(TaskGenerator):
    task_id = "INC2_data_corruption"
    domain = "incident_response"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        schema = SCHEMAS[seed % len(SCHEMAS)]
        pattern_idx = (seed * 3 + 1) % len(CORRUPTION_PATTERNS)
        pattern_id, pattern_desc, corrupt_fn = CORRUPTION_PATTERNS[pattern_idx]

        num_corrupted = rng.randint(5, 15)
        total_records = 50

        # Build clean records first
        records = _generate_records(rng, schema, total_records, seed)

        # Choose which records to corrupt
        all_indices = list(range(total_records))
        rng.shuffle(all_indices)
        corrupted_indices = set(all_indices[:num_corrupted])

        # Pick which corruptible field to corrupt (same field across all corrupted records)
        corrupt_field = rng.choice(schema["corruptible"])
        shadow_field = schema["shadow_prefix"] + corrupt_field

        # Determine field type and range for validation
        field_meta = {f[0]: f for f in schema["fields"]}
        cf_meta = field_meta[corrupt_field]
        cf_type = cf_meta[1]
        cf_min = cf_meta[2]
        cf_max = cf_meta[3]

        # Add shadow fields to all records (good records have shadow = primary; corrupted have shadow = original)
        for i, record in enumerate(records):
            original_val = record[corrupt_field]
            record[shadow_field] = original_val  # shadow always holds the correct value

        # Apply corruption (AFTER shadow is set — shadow retains the good value)
        corrupted_record_ids = []
        for i in corrupted_indices:
            original_val = records[i][corrupt_field]
            bad_val = corrupt_fn(original_val, rng)
            records[i][corrupt_field] = bad_val
            records[i]["_corrupted"] = True  # internal marker stripped before workspace
            corrupted_record_ids.append(records[i][schema["fields"][0][0]])  # primary key

        # Build expected: for each corrupted record, what the recovered value should be
        expected_values = {}
        for i in corrupted_indices:
            pk = records[i][schema["fields"][0][0]]
            expected_values[str(pk)] = records[i][shadow_field]

        # Strip internal marker and build workspace data
        workspace_records = []
        for record in records:
            r = dict(record)
            r.pop("_corrupted", None)
            workspace_records.append(r)

        # Build checksum for each record (simple: sum of numeric field values mod 1000)
        numeric_fields = [f[0] for f in schema["fields"] if f[1] in ("int", "float")]
        for record in workspace_records:
            vals = []
            for nf in numeric_fields:
                v = record.get(nf)
                try:
                    vals.append(float(v))
                except (TypeError, ValueError):
                    vals.append(0.0)
            record["_checksum"] = int(sum(vals)) % 1000

        # Expected checksums for recovered records
        expected_checksums = {}
        for i in corrupted_indices:
            pk = records[i][schema["fields"][0][0]]
            # Recompute checksum with recovered value
            vals = []
            for nf in numeric_fields:
                if nf == corrupt_field:
                    v = records[i][shadow_field]
                else:
                    v = records[i].get(nf)
                try:
                    vals.append(float(v))
                except (TypeError, ValueError):
                    vals.append(0.0)
            expected_checksums[str(pk)] = int(sum(vals)) % 1000

        expected = {
            "schema_name": schema["name"],
            "total_records": total_records,
            "num_corrupted": num_corrupted,
            "corrupt_field": corrupt_field,
            "shadow_field": shadow_field,
            "shadow_prefix": schema["shadow_prefix"],
            "pattern_id": pattern_id,
            "corrupted_primary_keys": [
                records[i][schema["fields"][0][0]] for i in corrupted_indices
            ],
            "expected_recovered_values": expected_values,
            "expected_checksums": expected_checksums,
            "field_ranges": {
                f[0]: {"type": f[1], "min": f[2], "max": f[3]}
                for f in schema["fields"]
                if f[1] in ("int", "float")
            },
            "required_fields": schema["required"],
            "primary_key": schema["fields"][0][0],
            "numeric_fields": numeric_fields,
        }

        workspace_files = {
            "data.json": json.dumps(workspace_records, indent=2) + "\n",
            "recover.py": _generate_recover_py(schema, corrupt_field, shadow_field, pattern_id),
            "validate.py": _generate_validate_py(schema, numeric_fields),
        }

        spec_md = _generate_spec(
            schema, corrupt_field, shadow_field, pattern_id, pattern_desc,
            num_corrupted, total_records, cf_type, cf_min, cf_max, numeric_fields,
            seed,
        )
        brief_md = _generate_brief(schema["name"], total_records)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )


# ---------------------------------------------------------------------------
# Record generation helpers
# ---------------------------------------------------------------------------

def _generate_records(rng: SeededRandom, schema: dict, count: int, seed: int) -> list[dict]:
    """Generate `count` clean records conforming to `schema`."""
    records = []
    used_pks = set()
    field_meta = schema["fields"]
    enum_fields = schema.get("enum_fields", {})
    pk_field = field_meta[0][0]

    for i in range(count):
        record = {}
        for fname, ftype, fmin, fmax in field_meta:
            if fname == pk_field:
                # Unique primary key
                while True:
                    if ftype == "int":
                        val = rng.randint(fmin, fmax)
                    else:
                        val = f"{fname}_{i:04d}"
                    if val not in used_pks:
                        used_pks.add(val)
                        break
                record[fname] = val
            elif fname in enum_fields:
                record[fname] = rng.choice(enum_fields[fname])
            elif ftype == "int":
                record[fname] = rng.randint(fmin, fmax)
            elif ftype == "float":
                record[fname] = round(rng.uniform(fmin, fmax), 2)
            elif ftype == "str":
                # Generate a plausible string value
                record[fname] = _gen_str_val(fname, i, rng, seed)
        records.append(record)
    return records


_NAME_POOL = [
    "Alice", "Bob", "Charlie", "Diana", "Eve", "Frank", "Grace", "Heidi",
    "Ivan", "Judy", "Karl", "Liam", "Mia", "Noah", "Olivia", "Peter",
    "Quinn", "Rose", "Sam", "Tara", "Uma", "Vera", "Will", "Xena",
    "Yuki", "Zara", "Amir", "Bina", "Carlos", "Devi", "Elena", "Faisal",
    "Gita", "Hassan", "Ingrid", "Jin", "Kenji", "Luna", "Marco", "Nadia",
    "Omar", "Priya", "Rashid", "Sofia", "Tariq", "Ursula", "Viktor", "Wen",
    "Xavier", "Yara",
]

_SKU_PARTS = ["ELEC", "CLTH", "FOOD", "TOOL", "MISC"]
_TAG_PARTS = ["SEN", "DEV", "MOD", "UNIT", "NODE"]


def _gen_str_val(fname: str, idx: int, rng: SeededRandom, seed: int) -> str:
    if fname in ("name",):
        return _NAME_POOL[idx % len(_NAME_POOL)]
    if fname in ("sku",):
        part = _SKU_PARTS[idx % len(_SKU_PARTS)]
        return f"{part}-{(seed * 13 + idx) % 10000:04d}"
    if fname in ("device_tag",):
        part = _TAG_PARTS[idx % len(_TAG_PARTS)]
        return f"{part}-{(seed * 7 + idx) % 1000:03d}"
    # generic fallback
    return f"{fname}_{idx:03d}"


# ---------------------------------------------------------------------------
# Workspace file generators
# ---------------------------------------------------------------------------

def _generate_recover_py(schema: dict, corrupt_field: str, shadow_field: str, pattern_id: str) -> str:
    pk_field = schema["fields"][0][0]
    return f'''\
"""
recover.py — Data corruption recovery script.

TODO: Implement the recovery logic using the Planner's instructions.
      The Planner has the full schema, the recovery procedure, and
      knows which field was corrupted and how to detect corrupted records.

Usage:
    python3 recover.py

Reads:  data.json
Writes: data.json  (in-place, overwrites with recovered records)
"""
import json
import sys


def is_corrupted(record: dict) -> bool:
    """
    TODO: Detect whether a record has a corrupted field.
    Hint: examine the field values and compare against valid ranges or types.
    """
    # TODO: implement detection logic
    raise NotImplementedError("implement is_corrupted()")


def recover_record(record: dict) -> dict:
    """
    TODO: Recover a corrupted record using the backup shadow field.
    The Planner's spec describes the shadow field naming convention
    and the exact recovery procedure.
    """
    # TODO: implement recovery logic using the shadow field
    raise NotImplementedError("implement recover_record()")


def main():
    with open("data.json", "r", encoding="utf-8") as f:
        records = json.load(f)

    recovered_count = 0
    for record in records:
        if is_corrupted(record):
            record = recover_record(record)
            recovered_count += 1

    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)
        f.write("\\n")

    print(f"Recovery complete: {{recovered_count}} records recovered.")


if __name__ == "__main__":
    main()
'''


def _generate_validate_py(schema: dict, numeric_fields: list) -> str:
    pk_field = schema["fields"][0][0]
    required_fields = schema["required"]
    field_ranges = {
        f[0]: (f[2], f[3]) for f in schema["fields"] if f[1] in ("int", "float")
    }
    field_types = {f[0]: f[1] for f in schema["fields"]}

    ranges_repr = json.dumps(
        {k: {"min": v[0], "max": v[1]} for k, v in field_ranges.items()},
        indent=4,
    )
    required_repr = json.dumps(required_fields)
    numeric_repr = json.dumps(numeric_fields)

    return f'''\
"""
validate.py — Schema validation script for recovered data.

Checks every record in data.json against:
  - Required fields (non-null, non-empty)
  - Numeric field types
  - Value ranges

Exits 0 if all records are valid, 1 otherwise.
"""
import json
import sys

REQUIRED_FIELDS = {required_repr}
NUMERIC_FIELDS = {numeric_repr}
FIELD_RANGES = {ranges_repr}


def validate_record(record: dict, idx: int) -> list[str]:
    """Return list of validation error strings for this record (empty = valid)."""
    errors = []

    # Required field check
    for field in REQUIRED_FIELDS:
        val = record.get(field)
        if val is None or val == "":
            errors.append(f"record[{{idx}}]: required field '{{field}}' is null/empty, got {{val!r}}")

    # Numeric type and range checks
    for field in NUMERIC_FIELDS:
        val = record.get(field)
        if val is None:
            errors.append(f"record[{{idx}}]: numeric field '{{field}}' is null")
            continue
        try:
            num = float(val)
        except (TypeError, ValueError):
            errors.append(f"record[{{idx}}]: field '{{field}}' is not numeric, got {{val!r}}")
            continue
        if field in FIELD_RANGES:
            rng = FIELD_RANGES[field]
            if num < rng["min"] or num > rng["max"]:
                errors.append(
                    f"record[{{idx}}]: field '{{field}}' = {{num}} out of range "
                    f"[{{rng['min']}}, {{rng['max']}}]"
                )

    return errors


def main():
    with open("data.json", "r", encoding="utf-8") as f:
        records = json.load(f)

    all_errors = []
    for idx, record in enumerate(records):
        errors = validate_record(record, idx)
        all_errors.extend(errors)

    if all_errors:
        print(f"VALIDATION FAILED: {{len(all_errors)}} error(s)")
        for err in all_errors:
            print(f"  ERROR: {{err}}")
        sys.exit(1)
    else:
        print(f"VALIDATION OK: all {{len(records)}} records are valid.")
        sys.exit(0)


if __name__ == "__main__":
    main()
'''


# ---------------------------------------------------------------------------
# Spec and Brief generators
# ---------------------------------------------------------------------------

def _generate_spec(
    schema: dict,
    corrupt_field: str,
    shadow_field: str,
    pattern_id: str,
    pattern_desc: str,
    num_corrupted: int,
    total_records: int,
    cf_type: str,
    cf_min,
    cf_max,
    numeric_fields: list,
    seed: int,
) -> str:
    pk_field = schema["fields"][0][0]
    shadow_prefix = schema["shadow_prefix"]

    field_table_rows = []
    for fname, ftype, fmin, fmax in schema["fields"]:
        if ftype in ("int", "float"):
            constraint = f"range [{fmin}, {fmax}]"
        else:
            enums = schema.get("enum_fields", {}).get(fname)
            constraint = f"one of {enums}" if enums else "non-empty string"
        required = "yes" if fname in schema["required"] else "no"
        field_table_rows.append(f"| `{fname}` | {ftype} | {constraint} | {required} |")
    field_table = "\n".join(field_table_rows)

    shadow_rows = "\n".join(
        f"| `{shadow_prefix}{f}` | Backup copy of `{f}` before write failure |"
        for f in schema["corruptible"]
    )

    if pattern_id == "string_garbage":
        detect_rule = (
            f'A record is corrupted if `{corrupt_field}` is a non-numeric string '
            f'(e.g. `"N/A"`, `"ERR"`, `"CORRUPT"`, `"??"`, `"---"`).'
        )
    elif pattern_id == "null_value":
        detect_rule = f"A record is corrupted if `{corrupt_field}` is `null`."
    elif pattern_id == "out_of_range_high":
        detect_rule = (
            f"A record is corrupted if `{corrupt_field}` exceeds the valid maximum of "
            f"`{cf_max}` by a large factor (100x or more)."
        )
    elif pattern_id == "truncated_string":
        detect_rule = (
            f'A record is corrupted if `{corrupt_field}` is a short string ending with `"!"` '
            f"(a truncation artifact from the partial write)."
        )
    else:  # zero_fill
        detect_rule = (
            f"A record is corrupted if `{corrupt_field}` is `0` when it should be a "
            f"positive value in range `[{cf_min}, {cf_max}]`."
        )

    numeric_range_lines = "\n".join(
        f"- `{f[0]}`: [{f[2]}, {f[3]}]"
        for f in schema["fields"]
        if f[1] in ("int", "float")
    )

    return f"""# INC2: Data Corruption Recovery — Planner Specification

## Incident Summary

**Incident ID**: INC-DC-{seed:04d}
**Severity**: P2
**Dataset**: `{schema["name"]}` records (`data.json`)
**Status**: Active — {num_corrupted} records corrupted, system integrity check failing

A partial write failure during a batch update caused {num_corrupted} of {total_records}
`{schema["name"]}` records to have their `{corrupt_field}` field corrupted
({pattern_desc}). The system wrote a shadow backup (`{shadow_field}`) for every record
**before** the update began, so all corrupted records have a valid backup value
available in the shadow field.

---

## Correct Schema

All records in `data.json` must conform to this schema after recovery:

| Field | Type | Constraint | Required |
|-------|------|------------|----------|
{field_table}

### Shadow (Backup) Fields

The write pipeline always creates shadow fields before any update. These are safe to
read and must not be removed after recovery:

| Shadow Field | Purpose |
|--------------|---------|
{shadow_rows}

---

## Corruption Details

**Corrupted field**: `{corrupt_field}`
**Corruption pattern**: {pattern_desc}
**Number of affected records**: {num_corrupted} out of {total_records}
**Corruption marker**: Each corrupted record has a field `_corrupted: true` embedded
during the partial write. *(Note: this field is for detection only; the Executor must
also validate by field value.)*

### Detection Rule

{detect_rule}

---

## Recovery Procedure

**CRITICAL**: Use the shadow field — do NOT interpolate, guess, or delete records.

For each corrupted record:

1. Detect corruption: check if `{corrupt_field}` matches the detection rule above.
2. Recover: set `{corrupt_field} = record["{shadow_field}"]`.
3. Recompute the `_checksum` field:
   - Sum the numeric values of these fields: `{", ".join(f"`{f}`" for f in numeric_fields)}`
   - `_checksum = int(sum_of_numerics) % 1000`
4. Leave all other fields unchanged.
5. Do NOT remove the shadow field `{shadow_field}` from the record.

After recovery, overwrite `data.json` in-place.

---

## Validation Rules

Run `validate.py` after recovery. It checks:

### Required Fields (must be non-null, non-empty)
{chr(10).join(f"- `{f}`" for f in schema["required"])}

### Numeric Ranges
{numeric_range_lines}

### Checksum
`_checksum` must equal `int(sum_of_numeric_fields) % 1000` for each record.

---

## Constraints

- All {total_records} records must remain in `data.json` (no deletions).
- No previously-good records may be modified.
- `recover.py` must exit 0.
- `validate.py` must exit 0 after recovery.
- Verifier must produce `attestation.json` with `verdict="pass"`.
"""


def _generate_brief(schema_name: str, total_records: int) -> str:
    return f"""# INC2: Data Corruption Recovery (Brief)

A data processing system has reported integrity check failures on the
`{schema_name}` dataset (`data.json`).

**Situation**: Some records in `data.json` are corrupted. The exact number and
location of corrupted records is unknown. The system appears to have experienced
a partial write failure during a recent batch update.

**Goal**: Recover all corrupted records so that `validate.py` passes for every record.

**Workspace files**:
- `data.json` — {total_records} records, some corrupted
- `recover.py` — skeleton recovery script (implement the TODOs)
- `validate.py` — validation script; must exit 0 after recovery

**What to do**:
1. Inspect `data.json` to understand the record structure and identify anomalies.
2. Implement the `is_corrupted()` and `recover_record()` functions in `recover.py`.
3. Run `python3 recover.py` to apply recovery.
4. Run `python3 validate.py` to confirm all records are valid.

The Planner has the full schema specification, the correct recovery procedure,
and the validation rules. Coordinate with the Planner before implementing.

**Constraint**: Do not delete any records. All {total_records} records must be present
in `data.json` after recovery.
"""
