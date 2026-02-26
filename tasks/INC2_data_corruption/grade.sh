#!/usr/bin/env bash
# Seed-aware grader for INC2: Data Corruption Recovery
# Reads expected values from expected.json for seed-specific grading.
#
# Args: $1=WORKSPACE $2=REPORTS $3=SUBMISSION $4=TASK_DIR [$5=EXPECTED_JSON]
set -o pipefail
WORKSPACE="$1"
REPORTS="$2"
SUBMISSION="$3"
TASK_DIR="$4"
EXPECTED="${5:-$REPORTS/expected.json}"

mkdir -p "$REPORTS"

CHECKS=0; PASSED=0; FAILURES=""
check() {
  CHECKS=$((CHECKS + 1))
  if eval "$1" 2>/dev/null; then
    PASSED=$((PASSED + 1))
  else
    FAILURES="${FAILURES:+${FAILURES},}$2"
  fi
}

cd "$WORKSPACE"

# ── Check 1: data.json exists and is valid JSON ──────────────────────────────
check "python3 -c \"
import json
with open('data.json', 'r', encoding='utf-8') as f:
    records = json.load(f)
assert isinstance(records, list) and len(records) > 0, 'data.json is empty or not a list'
print('DATA_JSON_VALID')
\"" "data_json_invalid"

# ── Check 2: recover.py runs without error ───────────────────────────────────
# Save a pre-recovery snapshot for idempotency testing later
cp data.json data.json.pre_recovery 2>/dev/null || true
check "python3 recover.py" "recover_py_crashes"

# ── Check 3: All records present after recovery (no deletion) ────────────────
check "python3 -c \"
import json
expected = json.load(open('$EXPECTED'))
total = expected['total_records']
with open('data.json', 'r', encoding='utf-8') as f:
    records = json.load(f)
assert len(records) == total, f'Expected {total} records, got {len(records)}'
print('RECORD_COUNT_OK')
\"" "record_count_wrong"

# ── Check 4: No previously-good records corrupted ────────────────────────────
check "python3 -c \"
import json
expected = json.load(open('$EXPECTED'))
pk = expected['primary_key']
corrupt_field = expected['corrupt_field']
corrupted_pks = set(str(x) for x in expected['corrupted_primary_keys'])
ranges = expected['field_ranges']
cf_range = ranges.get(corrupt_field, {})

with open('data.json', 'r', encoding='utf-8') as f:
    records = json.load(f)

for record in records:
    pk_val = str(record.get(pk))
    if pk_val not in corrupted_pks:
        val = record.get(corrupt_field)
        if val is None:
            raise AssertionError(f'Good record pk={pk_val} has null {corrupt_field}')
        try:
            num = float(val)
        except (TypeError, ValueError):
            raise AssertionError(f'Good record pk={pk_val} {corrupt_field}={val!r} is not numeric')
        if cf_range:
            assert cf_range[\"min\"] <= num <= cf_range[\"max\"], \
                f'Good record pk={pk_val} {corrupt_field}={num} out of range'
print('GOOD_RECORDS_INTACT')
\"" "good_records_modified"

# ── Check 5: Corrupted records have correct recovered values ─────────────────
check "python3 -c \"
import json
expected = json.load(open('$EXPECTED'))
pk = expected['primary_key']
corrupt_field = expected['corrupt_field']
expected_vals = expected['expected_recovered_values']

with open('data.json', 'r', encoding='utf-8') as f:
    records = json.load(f)

pk_map = {str(r.get(pk)): r for r in records}
for pk_val, exp_val in expected_vals.items():
    record = pk_map.get(pk_val)
    assert record is not None, f'Record pk={pk_val} missing from data.json'
    actual = record.get(corrupt_field)
    try:
        assert abs(float(actual) - float(exp_val)) < 0.01, \
            f'pk={pk_val}: {corrupt_field}={actual!r}, expected {exp_val!r}'
    except (TypeError, ValueError):
        assert str(actual) == str(exp_val), \
            f'pk={pk_val}: {corrupt_field}={actual!r}, expected {exp_val!r}'
print('CORRUPTED_RECORDS_RECOVERED')
\"" "corrupted_records_not_recovered"

# ── Check 6: All numeric fields within specified ranges ──────────────────────
check "python3 -c \"
import json
expected = json.load(open('$EXPECTED'))
field_ranges = expected['field_ranges']

with open('data.json', 'r', encoding='utf-8') as f:
    records = json.load(f)

for idx, record in enumerate(records):
    for field, rng in field_ranges.items():
        val = record.get(field)
        if val is None:
            continue
        try:
            num = float(val)
        except (TypeError, ValueError):
            raise AssertionError(f'record[{idx}]: field {field!r} is not numeric: {val!r}')
        assert rng['min'] <= num <= rng['max'], \
            f'record[{idx}]: {field}={num} out of range [{rng[\"min\"]}, {rng[\"max\"]}]'
print('NUMERIC_RANGES_OK')
\"" "numeric_ranges_violated"

# ── Check 7: All required fields present and non-null in every record ─────────
check "python3 -c \"
import json
expected = json.load(open('$EXPECTED'))
required = expected['required_fields']
pk = expected['primary_key']

with open('data.json', 'r', encoding='utf-8') as f:
    records = json.load(f)

for idx, record in enumerate(records):
    pk_val = record.get(pk, f'index_{idx}')
    for field in required:
        val = record.get(field)
        assert val is not None, f'pk={pk_val}: field {field!r} is null'
        assert str(val).strip() != '', f'pk={pk_val}: field {field!r} is empty string'
print('ALL_REQUIRED_FIELDS_PRESENT')
\"" "required_fields_null"

# ── Check 8: validate.py passes all records ───────────────────────────────────
check "python3 validate.py" "validate_py_fails"

# ── Check 9: recover.py is idempotent (re-running does not break good records) ─
# Restore pre-recovery snapshot and re-run to ensure it is stable
if [ -f data.json.pre_recovery ]; then
    cp data.json.pre_recovery data.json
    python3 recover.py 2>/dev/null || true
fi
check "python3 -c \"
import json
expected = json.load(open('$EXPECTED'))
pk = expected['primary_key']
corrupt_field = expected['corrupt_field']
expected_vals = expected['expected_recovered_values']
total = expected['total_records']

with open('data.json', 'r', encoding='utf-8') as f:
    records = json.load(f)

assert len(records) == total, f'Idempotency: record count changed to {len(records)}'
pk_map = {str(r.get(pk)): r for r in records}
for pk_val, exp_val in expected_vals.items():
    actual = pk_map.get(pk_val, {}).get(corrupt_field)
    try:
        assert abs(float(actual) - float(exp_val)) < 0.01
    except (TypeError, ValueError):
        assert str(actual) == str(exp_val), f'Idempotency failed for pk={pk_val}'
print('IDEMPOTENT_OK')
\"" "recover_not_idempotent"

# ── Check 10: Attestation verdict=pass ───────────────────────────────────────
check "python3 -c \"
import json, sys
att = json.load(open(sys.argv[1]))
assert att.get('verdict') == 'pass', f'verdict={att.get(\"verdict\")!r}'
\" '$SUBMISSION/attestation.json'" "bad_attestation"

# ── Write score ───────────────────────────────────────────────────────────────
PARTIAL=$(python3 -c "print(round($PASSED/max(1,$CHECKS), 2))")
if [ "$PASSED" -eq "$CHECKS" ]; then
    SUCCESS=1; PASS=true
else
    SUCCESS=0; PASS=false
fi
FM=$(python3 -c "import json; print(json.dumps([x for x in '${FAILURES}'.split(',') if x]))")

cat > "$REPORTS/score.json" <<JSON
{
  "pass": $PASS,
  "primary": {"success": $SUCCESS},
  "secondary": {
    "checks_passed": $PASSED,
    "checks_total": $CHECKS,
    "partial_score": $PARTIAL
  },
  "failure_modes": $FM
}
JSON
