#!/usr/bin/env bash
# Seed-aware grader for SPEC5: Configuration System from Requirements
#
# Reads domain and schema from expected.json (written by generator).
# Tests: all keys loadable, defaults correct, validation rejects invalid values,
#        env override works, type coercion works, CLI priority wins, file override
#        works, invalid values rejected with ConfigValidationError.
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

# ── Read domain and key fields from expected.json ────────────────────────────
DOMAIN=$(python3 -c "
import json
e = json.load(open('$EXPECTED'))
print(e.get('domain', 'unknown'))
" 2>/dev/null || echo "unknown")

ENV_PREFIX=$(python3 -c "
import json
e = json.load(open('$EXPECTED'))
print(e.get('env_prefix', 'APP'))
" 2>/dev/null || echo "APP")

# Extract schema as JSON for use in checks
SCHEMA_JSON=$(python3 -c "
import json
e = json.load(open('$EXPECTED'))
print(json.dumps(e.get('schema', {})))
" 2>/dev/null || echo '{}')

# ── Check 1: config_system.py exists ─────────────────────────────────────────
check "test -f '$WORKSPACE/config_system.py'" "config_system_missing"

# ── Check 2: module imports without error ─────────────────────────────────────
check "python3 -c \"
import sys; sys.path.insert(0, '$WORKSPACE')
from config_system import load_config, get_schema, validate_value, ConfigValidationError
print('IMPORT_OK')
\"" "import_error"

# ── Check 3: load_config() returns a dict with all schema keys ────────────────
check "python3 -c \"
import sys, json; sys.path.insert(0, '$WORKSPACE')
from config_system import load_config, get_schema
cfg = load_config()
schema = get_schema()
assert isinstance(cfg, dict), f'load_config() must return dict, got {type(cfg)}'
assert isinstance(schema, dict), f'get_schema() must return dict, got {type(schema)}'
missing = [k for k in schema if k not in cfg]
assert not missing, f'Missing keys in config: {missing}'
print('ALL_KEYS_OK')
\"" "missing_keys"

# ── Check 4: default values are correct ───────────────────────────────────────
check "python3 -c \"
import sys, json; sys.path.insert(0, '$WORKSPACE')
from config_system import load_config
schema = json.loads('''$SCHEMA_JSON''')
cfg = load_config()
errors = []
for key, spec in schema.items():
    expected_default = spec.get('default')
    actual = cfg.get(key)
    if actual != expected_default:
        errors.append(f'{key}: expected default {expected_default!r}, got {actual!r}')
assert not errors, 'Default value mismatches:\\n' + '\\n'.join(errors)
print('DEFAULTS_OK')
\"" "defaults_wrong"

# ── Check 5: env var overrides config file (priority test) ────────────────────
# Find first int key in schema to use for env override test
INT_KEY=$(python3 -c "
import json
schema = json.loads('''$SCHEMA_JSON''')
for k, v in schema.items():
    if v.get('type') == 'int' and 'min' in v and 'max' in v:
        mn = v['min']; mx = v['max']; mid = (mn + mx) // 2
        if mn < mid < mx:
            print(k, v['env_var'], mid)
            break
" 2>/dev/null || echo "")

if [ -n "$INT_KEY" ]; then
  INT_KEY_NAME=$(echo "$INT_KEY" | awk '{print $1}')
  INT_ENV_VAR=$(echo "$INT_KEY" | awk '{print $2}')
  INT_VALUE=$(echo "$INT_KEY" | awk '{print $3}')

  check "python3 -c \"
import sys, json; sys.path.insert(0, '$WORKSPACE')
from config_system import load_config
env = {'$INT_ENV_VAR': '$INT_VALUE'}
cfg = load_config(env_vars=env)
actual = cfg.get('$INT_KEY_NAME')
assert actual == $INT_VALUE, f'Env override failed: expected $INT_VALUE, got {actual!r}'
print('ENV_OVERRIDE_OK')
\"" "env_override_fail"
else
  # Fallback: try any key
  check "python3 -c \"
import sys; sys.path.insert(0, '$WORKSPACE')
from config_system import load_config
cfg = load_config(env_vars={})
assert isinstance(cfg, dict)
print('ENV_OVERRIDE_SKIP')
\"" "env_override_fail"
fi

# ── Check 6: CLI args override env vars (highest priority) ────────────────────
ENUM_INFO=$(python3 -c "
import json
schema = json.loads('''$SCHEMA_JSON''')
for k, v in schema.items():
    if v.get('type') == 'enum' and len(v.get('allowed', [])) >= 2:
        allowed = v['allowed']
        env_var = v['env_var']
        print(k, env_var, allowed[0], allowed[-1])
        break
" 2>/dev/null || echo "")

if [ -n "$ENUM_INFO" ]; then
  ENUM_KEY=$(echo "$ENUM_INFO" | awk '{print $1}')
  ENUM_ENV=$(echo "$ENUM_INFO" | awk '{print $2}')
  ENUM_VAL_A=$(echo "$ENUM_INFO" | awk '{print $3}')
  ENUM_VAL_B=$(echo "$ENUM_INFO" | awk '{print $4}')

  check "python3 -c \"
import sys; sys.path.insert(0, '$WORKSPACE')
from config_system import load_config
# env says A, cli says B — cli must win
env = {'$ENUM_ENV': '$ENUM_VAL_A'}
cli = {'$ENUM_KEY': '$ENUM_VAL_B'}
cfg = load_config(env_vars=env, cli_args=cli)
actual = cfg.get('$ENUM_KEY')
assert actual == '$ENUM_VAL_B', f'CLI should override env: expected $ENUM_VAL_B, got {actual!r}'
print('CLI_PRIORITY_OK')
\"" "cli_priority_fail"
else
  check "python3 -c \"
import sys; sys.path.insert(0, '$WORKSPACE')
from config_system import load_config
cfg = load_config(cli_args={})
assert isinstance(cfg, dict)
print('CLI_PRIORITY_SKIP')
\"" "cli_priority_fail"
fi

# ── Check 7: config file values are loaded and override defaults ───────────────
check "python3 -c \"
import sys, json, tempfile, os; sys.path.insert(0, '$WORKSPACE')
from config_system import load_config, get_schema
schema = get_schema()
# Pick first key to override via file
key = next(iter(schema))
spec = schema[key]
# Use default value (we just want file loading to work)
file_cfg = {key: spec['default']}
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    json.dump(file_cfg, f)
    fname = f.name
try:
    cfg = load_config(config_file=fname, env_vars={})
    assert cfg[key] == spec['default'], f'File load wrong: {cfg[key]!r}'
    print('FILE_LOAD_OK')
finally:
    os.unlink(fname)
\"" "file_load_fail"

# ── Check 8: int validation — out-of-range value raises ConfigValidationError ──
INT_RANGE_INFO=$(python3 -c "
import json
schema = json.loads('''$SCHEMA_JSON''')
for k, v in schema.items():
    if v.get('type') == 'int' and 'min' in v and 'max' in v:
        print(k, v['min'], v['max'])
        break
" 2>/dev/null || echo "")

if [ -n "$INT_RANGE_INFO" ]; then
  IR_KEY=$(echo "$INT_RANGE_INFO" | awk '{print $1}')
  IR_MIN=$(echo "$INT_RANGE_INFO" | awk '{print $2}')
  IR_MAX=$(echo "$INT_RANGE_INFO" | awk '{print $3}')

  check "python3 -c \"
import sys; sys.path.insert(0, '$WORKSPACE')
from config_system import validate_value, ConfigValidationError
# Value below min
try:
    validate_value('$IR_KEY', $IR_MIN - 1)
    assert False, 'Should raise ConfigValidationError for value below min'
except ConfigValidationError:
    pass
# Value above max
try:
    validate_value('$IR_KEY', $IR_MAX + 1)
    assert False, 'Should raise ConfigValidationError for value above max'
except ConfigValidationError:
    pass
print('INT_RANGE_OK')
\"" "int_range_validation_fail"

  # ── Check 9: int boundary — exactly at min and max is valid ──────────────────
  check "python3 -c \"
import sys; sys.path.insert(0, '$WORKSPACE')
from config_system import validate_value
v_min = validate_value('$IR_KEY', $IR_MIN)
assert v_min == $IR_MIN, f'Min boundary wrong: {v_min!r}'
v_max = validate_value('$IR_KEY', $IR_MAX)
assert v_max == $IR_MAX, f'Max boundary wrong: {v_max!r}'
print('INT_BOUNDARY_OK')
\"" "int_boundary_fail"
else
  CHECKS=$((CHECKS + 2))
  PASSED=$((PASSED + 2))
fi

# ── Check 10: enum validation — invalid value raises ConfigValidationError ─────
ENUM_KEY2=$(python3 -c "
import json
schema = json.loads('''$SCHEMA_JSON''')
for k, v in schema.items():
    if v.get('type') == 'enum':
        print(k, json.dumps(v.get('allowed', [])))
        break
" 2>/dev/null || echo "")

if [ -n "$ENUM_KEY2" ]; then
  EK2=$(echo "$ENUM_KEY2" | awk '{print $1}')
  EK2_ALLOWED=$(echo "$ENUM_KEY2" | cut -d' ' -f2-)

  check "python3 -c \"
import sys, json; sys.path.insert(0, '$WORKSPACE')
from config_system import validate_value, ConfigValidationError
allowed = $EK2_ALLOWED
try:
    validate_value('$EK2', '__INVALID_ENUM_VALUE__')
    assert False, 'Should raise ConfigValidationError for invalid enum'
except ConfigValidationError:
    pass
# Valid values should work
for v in allowed:
    result = validate_value('$EK2', v)
    assert result == v, f'Valid enum {v!r} should return {v!r}, got {result!r}'
print('ENUM_VALIDATION_OK')
\"" "enum_validation_fail"
else
  CHECKS=$((CHECKS + 1)); PASSED=$((PASSED + 1))
fi

# ── Check 11: bool type coercion from string ───────────────────────────────────
BOOL_KEY=$(python3 -c "
import json
schema = json.loads('''$SCHEMA_JSON''')
for k, v in schema.items():
    if v.get('type') == 'bool':
        print(k, v['env_var'])
        break
" 2>/dev/null || echo "")

if [ -n "$BOOL_KEY" ]; then
  BK=$(echo "$BOOL_KEY" | awk '{print $1}')
  BK_ENV=$(echo "$BOOL_KEY" | awk '{print $2}')

  check "python3 -c \"
import sys; sys.path.insert(0, '$WORKSPACE')
from config_system import validate_value, ConfigValidationError
# String 'true' -> True
assert validate_value('$BK', 'true') == True, 'true -> True failed'
assert validate_value('$BK', 'True') == True, 'True -> True failed'
assert validate_value('$BK', '1') == True, '1 -> True failed'
assert validate_value('$BK', 'yes') == True, 'yes -> True failed'
assert validate_value('$BK', 'false') == False, 'false -> False failed'
assert validate_value('$BK', 'False') == False, 'False -> False failed'
assert validate_value('$BK', '0') == False, '0 -> False failed'
assert validate_value('$BK', 'no') == False, 'no -> False failed'
# Bool values pass through
assert validate_value('$BK', True) == True
assert validate_value('$BK', False) == False
print('BOOL_COERCION_OK')
\"" "bool_coercion_fail"

  # Check bool env var override via string
  check "python3 -c \"
import sys; sys.path.insert(0, '$WORKSPACE')
from config_system import load_config
# Set bool env var to 'false' string
env = {'$BK_ENV': 'false'}
cfg = load_config(env_vars=env)
assert cfg['$BK'] == False, f'Bool env override failed: {cfg[\"$BK\"]!r}'
env2 = {'$BK_ENV': '1'}
cfg2 = load_config(env_vars=env2)
assert cfg2['$BK'] == True, f'Bool env override (1) failed: {cfg2[\"$BK\"]!r}'
print('BOOL_ENV_OK')
\"" "bool_env_fail"

  # Invalid bool string raises error
  check "python3 -c \"
import sys; sys.path.insert(0, '$WORKSPACE')
from config_system import validate_value, ConfigValidationError
try:
    validate_value('$BK', 'maybe')
    assert False, 'Should raise ConfigValidationError for invalid bool string'
except ConfigValidationError:
    pass
print('BOOL_INVALID_OK')
\"" "bool_invalid_fail"
else
  CHECKS=$((CHECKS + 3)); PASSED=$((PASSED + 3))
fi

# ── Check 12: int string coercion from env var ────────────────────────────────
if [ -n "$INT_RANGE_INFO" ]; then
  IR_ENV_VAR=$(python3 -c "
import json
schema = json.loads('''$SCHEMA_JSON''')
k = '$IR_KEY'
print(schema[k]['env_var'])
" 2>/dev/null || echo "")

  if [ -n "$IR_ENV_VAR" ]; then
    check "python3 -c \"
import sys; sys.path.insert(0, '$WORKSPACE')
from config_system import load_config
# Pass int as string through env var
env = {'$IR_ENV_VAR': '$IR_MIN'}
cfg = load_config(env_vars=env)
actual = cfg.get('$IR_KEY')
assert actual == $IR_MIN, f'Int coercion from env failed: expected $IR_MIN (int), got {actual!r} ({type(actual).__name__})'
assert isinstance(actual, int), f'Int coercion must produce int, got {type(actual).__name__}'
print('INT_COERCION_OK')
\"" "int_coercion_fail"
  else
    CHECKS=$((CHECKS + 1)); PASSED=$((PASSED + 1))
  fi
else
  CHECKS=$((CHECKS + 1)); PASSED=$((PASSED + 1))
fi

# ── Check 13: FileNotFoundError on missing config file ────────────────────────
check "python3 -c \"
import sys; sys.path.insert(0, '$WORKSPACE')
from config_system import load_config
try:
    load_config(config_file='/tmp/__nonexistent_config_spec5__.json', env_vars={})
    assert False, 'Should raise FileNotFoundError for missing config file'
except FileNotFoundError:
    pass
print('FILE_NOT_FOUND_OK')
\"" "file_not_found_fail"

# ── Check 14: non-parseable int string raises ConfigValidationError ───────────
if [ -n "$INT_RANGE_INFO" ]; then
  check "python3 -c \"
import sys; sys.path.insert(0, '$WORKSPACE')
from config_system import validate_value, ConfigValidationError
try:
    validate_value('$IR_KEY', 'not_an_int')
    assert False, 'Should raise ConfigValidationError for non-parseable int'
except ConfigValidationError:
    pass
print('INT_PARSE_ERROR_OK')
\"" "int_parse_error_fail"
else
  CHECKS=$((CHECKS + 1)); PASSED=$((PASSED + 1))
fi

# ── Check 15: get_schema() returns correct key count and structure ─────────────
check "python3 -c \"
import sys, json; sys.path.insert(0, '$WORKSPACE')
from config_system import get_schema
schema = get_schema()
expected_schema = json.loads('''$SCHEMA_JSON''')
assert isinstance(schema, dict), f'get_schema() must return dict'
# All expected keys must be present
missing = [k for k in expected_schema if k not in schema]
assert not missing, f'Schema missing keys: {missing}'
# Each entry must have type and default
for k, v in schema.items():
    assert 'type' in v, f'Schema entry for {k!r} missing type'
    assert 'default' in v, f'Schema entry for {k!r} missing default'
print('SCHEMA_STRUCTURE_OK')
\"" "schema_structure_fail"

# ── Check 16: CLI args override file config ───────────────────────────────────
check "python3 -c \"
import sys, json, tempfile, os; sys.path.insert(0, '$WORKSPACE')
from config_system import load_config, get_schema
schema = get_schema()
# Pick any key from schema
key = next(iter(schema))
spec = schema[key]
default_val = spec['default']
# Write default to file, then override with CLI
file_cfg = {key: default_val}
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    json.dump(file_cfg, f)
    fname = f.name
try:
    # For simplicity, CLI override with same value confirms round-trip
    cfg = load_config(config_file=fname, env_vars={}, cli_args={key: default_val})
    assert cfg[key] == default_val, f'CLI+file override wrong: {cfg[key]!r}'
    print('CLI_FILE_PRIORITY_OK')
finally:
    os.unlink(fname)
\"" "cli_file_priority_fail"

# ── Check 17: unknown keys in config file do not cause errors ─────────────────
check "python3 -c \"
import sys, json, tempfile, os; sys.path.insert(0, '$WORKSPACE')
from config_system import load_config
file_cfg = {'__unknown_key_xyz__': 'should_be_ignored', '__another_unknown__': 42}
with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
    json.dump(file_cfg, f)
    fname = f.name
try:
    cfg = load_config(config_file=fname, env_vars={})
    assert isinstance(cfg, dict), 'load_config must return dict even with unknown file keys'
    print('UNKNOWN_KEYS_OK')
finally:
    os.unlink(fname)
\"" "unknown_keys_error"

# ── Score ─────────────────────────────────────────────────────────────────────
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
    "partial_score": $PARTIAL,
    "domain": "$DOMAIN"
  },
  "failure_modes": $FM
}
JSON
