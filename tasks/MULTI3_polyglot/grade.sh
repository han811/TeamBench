#!/usr/bin/env bash
set -o pipefail
WORKSPACE="$1"
REPORTS="$2"
SUBMISSION="$3"
TASK_DIR="$4"
EXPECTED="${5:-}"

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

# ---------------------------------------------------------------------------
# Load expected.json
# ---------------------------------------------------------------------------
EXPECTED_JSON="$REPORTS/expected.json"
if [ ! -f "$EXPECTED_JSON" ]; then
  EXPECTED_JSON="$(dirname "$0")/expected.json"
fi

# Defaults (seed=0 / user_profiles)
CORRECT_ENVELOPE_KEY="data"
CORRECT_DATE_FORMAT="%Y-%m-%d"
ID_FIELD="user_id"
DATE_FIELD="joined_at"
NULL_FIELD="full_name"
WRONG_ID_KEY="uid"
CORRECT_ID_KEY="user_id"
WRONG_SCHEMA_FIELD="fullName"
CORRECT_SCHEMA_FIELD="full_name"

if [ -f "$EXPECTED_JSON" ]; then
  CORRECT_ENVELOPE_KEY=$(python3 -c "import json; d=json.load(open('$EXPECTED_JSON')); print(d.get('correct_envelope_key','data'))" 2>/dev/null || echo "data")
  CORRECT_DATE_FORMAT=$(python3 -c "import json; d=json.load(open('$EXPECTED_JSON')); print(d.get('correct_date_format','%Y-%m-%d'))" 2>/dev/null || echo "%Y-%m-%d")
  ID_FIELD=$(python3 -c "import json; d=json.load(open('$EXPECTED_JSON')); print(d.get('id_field','user_id'))" 2>/dev/null || echo "user_id")
  DATE_FIELD=$(python3 -c "import json; d=json.load(open('$EXPECTED_JSON')); print(d.get('date_field','joined_at'))" 2>/dev/null || echo "joined_at")
  NULL_FIELD=$(python3 -c "import json; d=json.load(open('$EXPECTED_JSON')); print(d.get('null_field','full_name'))" 2>/dev/null || echo "full_name")
  WRONG_ID_KEY=$(python3 -c "import json; d=json.load(open('$EXPECTED_JSON')); print(d.get('wrong_id_key','uid'))" 2>/dev/null || echo "uid")
  CORRECT_ID_KEY=$(python3 -c "import json; d=json.load(open('$EXPECTED_JSON')); print(d.get('correct_id_key','user_id'))" 2>/dev/null || echo "user_id")
  WRONG_SCHEMA_FIELD=$(python3 -c "import json; d=json.load(open('$EXPECTED_JSON')); print(d.get('wrong_schema_field','fullName'))" 2>/dev/null || echo "fullName")
  CORRECT_SCHEMA_FIELD=$(python3 -c "import json; d=json.load(open('$EXPECTED_JSON')); print(d.get('correct_schema_field','full_name'))" 2>/dev/null || echo "full_name")
fi

# ---------------------------------------------------------------------------
# Check 1: backend/processor.py imports without error
# ---------------------------------------------------------------------------
check "cd '$WORKSPACE/backend' && python3 -c 'import processor'" "backend_import_error"

# ---------------------------------------------------------------------------
# Check 2: frontend/handler.py imports without error
# ---------------------------------------------------------------------------
check "cd '$WORKSPACE/frontend' && python3 -c 'import handler'" "frontend_import_error"

# ---------------------------------------------------------------------------
# Check 3: shared/schema.json is valid JSON
# ---------------------------------------------------------------------------
check "python3 -c \"import json; json.load(open('$WORKSPACE/shared/schema.json'))\"" "schema_invalid_json"

# ---------------------------------------------------------------------------
# Check 4: schema.json does not contain the wrong field name
# ---------------------------------------------------------------------------
check "python3 - <<'PYEOF'
import json, sys
schema = json.load(open('$WORKSPACE/shared/schema.json'))
text = open('$WORKSPACE/shared/schema.json').read()
assert '${WRONG_SCHEMA_FIELD}' not in text, \
    f'schema.json still contains wrong field name: ${WRONG_SCHEMA_FIELD}'
PYEOF" "schema_wrong_field_name"

# ---------------------------------------------------------------------------
# Check 5: schema.json contains the correct field name
# ---------------------------------------------------------------------------
check "python3 - <<'PYEOF'
import json
text = open('$WORKSPACE/shared/schema.json').read()
assert '${CORRECT_SCHEMA_FIELD}' in text, \
    f'schema.json missing correct field name: ${CORRECT_SCHEMA_FIELD}'
PYEOF" "schema_missing_correct_field"

# ---------------------------------------------------------------------------
# Check 6: backend serialize() uses correct id field key (not wrong key)
# ---------------------------------------------------------------------------
check "python3 - <<'PYEOF'
import sys, importlib
sys.path.insert(0, '$WORKSPACE/backend')
import processor
# Call serialize with a minimal record dict
fields = [f for f in dir(processor) if not f.startswith('_')]
# Try to find serialize function
assert hasattr(processor, 'serialize'), 'processor missing serialize()'
import inspect
src = inspect.getsource(processor.serialize)
assert '${CORRECT_ID_KEY}' in src, f'serialize() missing correct id key: ${CORRECT_ID_KEY}'
assert '${WRONG_ID_KEY}' not in src, f'serialize() still uses wrong id key: ${WRONG_ID_KEY}'
PYEOF" "backend_wrong_id_key"

# ---------------------------------------------------------------------------
# Check 7: backend serialize() uses ISO-8601 date format (%Y-%m-%d)
# ---------------------------------------------------------------------------
check "python3 - <<'PYEOF'
import sys, inspect
sys.path.insert(0, '$WORKSPACE/backend')
import processor
assert hasattr(processor, 'serialize'), 'processor missing serialize()'
src = inspect.getsource(processor.serialize)
assert '%Y-%m-%d' in src, 'serialize() does not use %Y-%m-%d date format'
assert '%m/%d/%Y' not in src, 'serialize() still uses wrong MM/DD/YYYY format'
PYEOF" "backend_wrong_date_format"

# ---------------------------------------------------------------------------
# Check 8: backend serialize() does not encode None as sentinel string 'NULL'
# ---------------------------------------------------------------------------
check "python3 - <<'PYEOF'
import sys, inspect
sys.path.insert(0, '$WORKSPACE/backend')
import processor
assert hasattr(processor, 'serialize'), 'processor missing serialize()'
src = inspect.getsource(processor.serialize)
assert \"'NULL'\" not in src and '\"NULL\"' not in src, \
    \"serialize() still encodes None as string 'NULL'\"
PYEOF" "backend_null_sentinel"

# ---------------------------------------------------------------------------
# Check 9: backend uses correct envelope key
# ---------------------------------------------------------------------------
check "python3 - <<'PYEOF'
import sys, inspect
sys.path.insert(0, '$WORKSPACE/backend')
import processor
src = inspect.getsource(processor)
assert '\"${CORRECT_ENVELOPE_KEY}\"' in src or \"'${CORRECT_ENVELOPE_KEY}'\" in src, \
    f'processor.py missing correct envelope key: ${CORRECT_ENVELOPE_KEY}'
PYEOF" "backend_wrong_envelope_key"

# ---------------------------------------------------------------------------
# Check 10: frontend handler.py reads correct id field key
# ---------------------------------------------------------------------------
check "python3 - <<'PYEOF'
import sys, inspect
sys.path.insert(0, '$WORKSPACE/frontend')
import handler
assert hasattr(handler, 'deserialize'), 'handler missing deserialize()'
src = inspect.getsource(handler.deserialize)
assert '${CORRECT_ID_KEY}' in src, f'deserialize() missing correct id key: ${CORRECT_ID_KEY}'
assert '${WRONG_ID_KEY}' not in src, f'deserialize() still reads wrong id key: ${WRONG_ID_KEY}'
PYEOF" "frontend_wrong_id_key"

# ---------------------------------------------------------------------------
# Check 11: frontend handler.py parses dates with correct format
# ---------------------------------------------------------------------------
check "python3 - <<'PYEOF'
import sys, inspect
sys.path.insert(0, '$WORKSPACE/frontend')
import handler
assert hasattr(handler, 'deserialize'), 'handler missing deserialize()'
src = inspect.getsource(handler.deserialize)
assert '%Y-%m-%d' in src, 'deserialize() does not use %Y-%m-%d date format'
assert '%m/%d/%Y' not in src, 'deserialize() still uses wrong MM/DD/YYYY format'
PYEOF" "frontend_wrong_date_format"

# ---------------------------------------------------------------------------
# Check 12: frontend handler.py reads correct envelope key
# ---------------------------------------------------------------------------
check "python3 - <<'PYEOF'
import sys, inspect
sys.path.insert(0, '$WORKSPACE/frontend')
import handler
src = inspect.getsource(handler)
assert '\"${CORRECT_ENVELOPE_KEY}\"' in src or \"'${CORRECT_ENVELOPE_KEY}'\" in src, \
    f'handler.py missing correct envelope key: ${CORRECT_ENVELOPE_KEY}'
PYEOF" "frontend_wrong_envelope_key"

# ---------------------------------------------------------------------------
# Check 13: tests/test_contract.py passes with pytest
# ---------------------------------------------------------------------------
check "python3 -m pytest '$WORKSPACE/tests/test_contract.py' -q --tb=no \
       --rootdir='$WORKSPACE' 2>/dev/null" "test_suite_failures"

# ---------------------------------------------------------------------------
# Check 14: backend/frontend contract round-trip (serialize then deserialize)
# ---------------------------------------------------------------------------
check "python3 - <<'PYEOF'
import sys
sys.path.insert(0, '$WORKSPACE/backend')
sys.path.insert(0, '$WORKSPACE/frontend')
import processor, handler
# Check both modules expose serialize/deserialize
assert hasattr(processor, 'serialize'), 'processor missing serialize()'
assert hasattr(handler, 'deserialize'), 'handler missing deserialize()'
# Verify the envelope key is consistent between backend and frontend
import inspect
proc_src = inspect.getsource(processor)
hand_src = inspect.getsource(handler)
env_key = '${CORRECT_ENVELOPE_KEY}'
assert env_key in proc_src or \"'\" + env_key + \"'\" in proc_src or '\"' + env_key + '\"' in proc_src, \
    f'processor.py missing envelope key {env_key}'
assert env_key in hand_src or \"'\" + env_key + \"'\" in hand_src or '\"' + env_key + '\"' in hand_src, \
    f'handler.py missing envelope key {env_key}'
PYEOF" "backend_frontend_contract_mismatch"

# ---------------------------------------------------------------------------
# Check 15: no syntax errors in any Python file
# ---------------------------------------------------------------------------
check "python3 -m py_compile '$WORKSPACE/backend/processor.py' && \
       python3 -m py_compile '$WORKSPACE/frontend/handler.py' && \
       python3 -m py_compile '$WORKSPACE/tests/test_contract.py'" "syntax_errors"

# ---------------------------------------------------------------------------
# Check 16: attestation.json verdict=pass
# ---------------------------------------------------------------------------
check "python3 -c \"
import json, sys
att = json.load(open(sys.argv[1]))
assert att.get('verdict') == 'pass', f'verdict={att.get(\\\"verdict\\\")}'
\" '$SUBMISSION/attestation.json'" "bad_attestation"

# ---------------------------------------------------------------------------
# Write score
# ---------------------------------------------------------------------------
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
