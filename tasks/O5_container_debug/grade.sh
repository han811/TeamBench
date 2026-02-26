#!/usr/bin/env bash
set -o pipefail
WORKSPACE="$1"
REPORTS="$2"
SUBMISSION="$3"
TASK_DIR="$4"

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

# ── Load seed-specific expected values ───────────────────────────────────────
EXPECTED_JSON="$REPORTS/expected.json"
if [ -f "$EXPECTED_JSON" ]; then
  APP_TYPE=$(python3 -c "import json; print(json.load(open('$EXPECTED_JSON'))['app_type'])")
  PORT=$(python3 -c "import json; print(json.load(open('$EXPECTED_JSON'))['port'])")
  ENV_KEY=$(python3 -c "import json; print(json.load(open('$EXPECTED_JSON'))['env_key'])")
  ENV_VALUE=$(python3 -c "import json; print(json.load(open('$EXPECTED_JSON'))['env_value'])")
  CORRECT_BASE=$(python3 -c "import json; print(json.load(open('$EXPECTED_JSON'))['correct_base_image'])")
  CORRECT_RUN=$(python3 -c "import json; print(json.load(open('$EXPECTED_JSON'))['correct_run'])")
  BUG_TYPES=$(python3 -c "import json; print(','.join(json.load(open('$EXPECTED_JSON'))['bug_types']))")
  PACKAGES=$(python3 -c "import json; print(','.join(json.load(open('$EXPECTED_JSON')).get('packages', [])))")
else
  echo "ERROR: expected.json not found at $EXPECTED_JSON" >&2
  APP_TYPE="python-flask"
  PORT=5000
  ENV_KEY="APP_SECRET"
  ENV_VALUE="secret-1234"
  CORRECT_BASE="python:3.11-slim"
  CORRECT_RUN="pip install --no-cache-dir flask gunicorn"
  BUG_TYPES=""
  PACKAGES=""
fi

cd "$WORKSPACE"

DOCKERFILE="$WORKSPACE/Dockerfile"

# ── CHECK 1: Dockerfile exists ────────────────────────────────────────────────
check "[ -f '$DOCKERFILE' ]" "dockerfile_missing"

# ── CHECK 2: Correct base image ───────────────────────────────────────────────
check "python3 -c \"
with open('$DOCKERFILE') as f:
    lines = f.read().splitlines()
from_lines = [l.strip() for l in lines if l.strip().upper().startswith('FROM')]
assert any('${CORRECT_BASE}' in l for l in from_lines), \
    f'Expected FROM ${CORRECT_BASE}, got: {from_lines}'
print('BASE_IMAGE_OK')
\"" "wrong_base_image"

# ── CHECK 3: WORKDIR /app is set ─────────────────────────────────────────────
check "python3 -c \"
with open('$DOCKERFILE') as f:
    content = f.read()
assert 'WORKDIR /app' in content, 'WORKDIR /app not found'
print('WORKDIR_OK')
\"" "workdir_missing"

# ── CHECK 4: COPY instruction present ────────────────────────────────────────
check "python3 -c \"
with open('$DOCKERFILE') as f:
    lines = f.read().splitlines()
copy_lines = [l.strip() for l in lines if l.strip().upper().startswith('COPY')]
assert len(copy_lines) >= 1, 'No COPY instruction found'
print('COPY_OK')
\"" "copy_missing"

# ── CHECK 5: Correct RUN / dependency install ─────────────────────────────────
# Check that the correct install command (or a valid subset of it) appears in a RUN line
check "python3 -c \"
import re
with open('$DOCKERFILE') as f:
    content = f.read()

# Normalise: collapse line continuations
content_flat = re.sub(r'\\\\\s*\n\s*', ' ', content)
run_lines = [l.strip() for l in content_flat.splitlines() if l.strip().upper().startswith('RUN')]

correct_run = '${CORRECT_RUN}'
app_type = '${APP_TYPE}'

found = False
for rl in run_lines:
    rl_lower = rl.lower()
    if app_type in ('python-flask', 'python-fastapi'):
        # Must use pip install with the right packages
        if 'pip install' in rl_lower and '--no-cache-dir' in rl_lower:
            found = True
            break
    elif app_type == 'node-express':
        if 'npm install' in rl_lower:
            found = True
            break
    elif app_type == 'go-http':
        if 'go build' in rl_lower:
            found = True
            break

assert found, f'Correct dependency install not found. Expected something like: {correct_run}. Got RUN lines: {run_lines}'
print('DEPENDENCY_INSTALL_OK')
\"" "missing_dependency_install"

# ── CHECK 6: Correct EXPOSE port ─────────────────────────────────────────────
check "python3 -c \"
with open('$DOCKERFILE') as f:
    lines = f.read().splitlines()
expose_lines = [l.strip() for l in lines if l.strip().upper().startswith('EXPOSE')]
assert any('${PORT}' in l for l in expose_lines), \
    f'EXPOSE ${PORT} not found. Got: {expose_lines}'
print('EXPOSE_OK')
\"" "wrong_port_expose"

# ── CHECK 7: Required ENV var declared ────────────────────────────────────────
check "python3 -c \"
with open('$DOCKERFILE') as f:
    content = f.read()
assert '${ENV_KEY}' in content, 'ENV ${ENV_KEY} not declared in Dockerfile'
# Must appear in an ENV line
lines = content.splitlines()
env_lines = [l.strip() for l in lines if l.strip().upper().startswith('ENV')]
assert any('${ENV_KEY}' in l for l in env_lines), \
    f'${ENV_KEY} found but not in an ENV line. ENV lines: {env_lines}'
print('ENV_KEY_OK')
\"" "missing_env_var"

# ── CHECK 8: APP_PORT ENV var declared ───────────────────────────────────────
check "python3 -c \"
with open('$DOCKERFILE') as f:
    content = f.read()
lines = content.splitlines()
env_lines = [l.strip() for l in lines if l.strip().upper().startswith('ENV')]
assert any('APP_PORT' in l for l in env_lines), \
    f'APP_PORT not declared in any ENV line. ENV lines: {env_lines}'
print('APP_PORT_ENV_OK')
\"" "missing_app_port_env"

# ── CHECK 9: Correct CMD / ENTRYPOINT ────────────────────────────────────────
check "python3 -c \"
import re, json
with open('$DOCKERFILE') as f:
    content = f.read()
# Flatten continuations
content_flat = re.sub(r'\\\\\s*\n\s*', ' ', content)
cmd_lines = [l.strip() for l in content_flat.splitlines()
             if l.strip().upper().startswith('CMD') or l.strip().upper().startswith('ENTRYPOINT')]
assert len(cmd_lines) >= 1, 'No CMD or ENTRYPOINT found'

app_type = '${APP_TYPE}'
port_str = '${PORT}'
combined = ' '.join(cmd_lines).lower()

if app_type == 'python-flask':
    assert 'gunicorn' in combined, f'gunicorn not in CMD. Got: {cmd_lines}'
    assert 'server' in combined, f'server module not in CMD. Got: {cmd_lines}'
elif app_type == 'python-fastapi':
    assert 'uvicorn' in combined, f'uvicorn not in CMD. Got: {cmd_lines}'
    assert 'server' in combined, f'server module not in CMD. Got: {cmd_lines}'
elif app_type == 'node-express':
    assert 'node' in combined, f'node not in CMD. Got: {cmd_lines}'
    assert 'server.js' in combined, f'server.js not in CMD. Got: {cmd_lines}'
elif app_type == 'go-http':
    assert './server' in combined or '\"./server\"' in combined, f'./server not in CMD. Got: {cmd_lines}'

print('CMD_OK')
\"" "wrong_cmd"

# ── CHECK 10: HEALTHCHECK defined ────────────────────────────────────────────
check "python3 -c \"
with open('$DOCKERFILE') as f:
    content = f.read()
assert 'HEALTHCHECK' in content.upper(), 'No HEALTHCHECK instruction found'
# Health check must reference the correct port
assert '${PORT}' in content, \
    f'HEALTHCHECK does not reference port ${PORT}'
print('HEALTHCHECK_OK')
\"" "healthcheck_missing"

# ── CHECK 11: app_config.json references correct port ────────────────────────
check "python3 -c \"
import json
cfg = json.load(open('app_config.json'))
assert cfg.get('port') == ${PORT}, \
    f'app_config.json port={cfg.get(\"port\")} != ${PORT}'
print('CONFIG_PORT_OK')
\"" "config_port_wrong"

# ── CHECK 12: app_config.json references correct host ────────────────────────
check "python3 -c \"
import json
cfg = json.load(open('app_config.json'))
assert cfg.get('host') == '0.0.0.0', \
    f'app_config.json host={cfg.get(\"host\")} != 0.0.0.0'
print('CONFIG_HOST_OK')
\"" "config_host_wrong"

# ── CHECK 13: submission/fix_notes.txt exists and is non-empty ───────────────
check "[ -s '$SUBMISSION/fix_notes.txt' ]" "missing_fix_notes"

# ── CHECK 14: fix_notes.txt mentions key bug types that were fixed ────────────
check "python3 -c \"
import os, sys

fix_notes_path = '$SUBMISSION/fix_notes.txt'
if not os.path.isfile(fix_notes_path):
    sys.exit(1)

with open(fix_notes_path) as f:
    notes = f.read().lower()

bug_types_raw = '${BUG_TYPES}'
if not bug_types_raw:
    print('NO_BUGS_TO_CHECK')
    sys.exit(0)

bug_types = [b.strip() for b in bug_types_raw.split(',') if b.strip()]

# Map each bug type to keywords that should appear in fix notes
keyword_map = {
    'wrong_base_image':            ['base image', 'from', 'base'],
    'missing_dependency_install':  ['install', 'dependencies', 'packages', 'pip', 'npm', 'go build'],
    'wrong_port_expose':           ['expose', 'port'],
    'missing_env_var':             ['env', 'environment', 'variable'],
    'wrong_cmd':                   ['cmd', 'command', 'entrypoint', 'start'],
}

missing = []
for bt in bug_types:
    kws = keyword_map.get(bt, [bt.replace('_', ' ')])
    if not any(kw in notes for kw in kws):
        missing.append(bt)

assert not missing, f'fix_notes.txt does not mention fixes for: {missing}'
print('FIX_NOTES_COMPLETE')
\"" "fix_notes_incomplete"

# ── CHECK 15: Dockerfile diff was actually applied ────────────────────────────
ORIG="$WORKSPACE/.Dockerfile.orig"
DIFF_LINES=0
if [ -f "$ORIG" ] && [ -f "$DOCKERFILE" ]; then
  DIFF_LINES=$(diff "$ORIG" "$DOCKERFILE" | grep -c '^[<>]' || true)
fi
check "[ $DIFF_LINES -gt 0 ]" "dockerfile_not_modified"

# ── Scoring ───────────────────────────────────────────────────────────────────
PARTIAL=$(python3 -c "print(round($PASSED/max(1,$CHECKS), 2))")
if [ "$PASSED" -eq "$CHECKS" ]; then SUCCESS=1; PASS=true; else SUCCESS=0; PASS=false; fi
FM=$(python3 -c "import json; print(json.dumps([x for x in '${FAILURES}'.split(',') if x]))")

cat > "$REPORTS/score.json" <<JSON
{
  "pass": $PASS,
  "primary": {"success": $SUCCESS},
  "secondary": {
    "checks_passed": $PASSED,
    "checks_total": $CHECKS,
    "partial_score": $PARTIAL,
    "diff_lines": $DIFF_LINES,
    "app_type": "${APP_TYPE}",
    "port": ${PORT},
    "bug_types": "${BUG_TYPES}"
  },
  "failure_modes": $FM
}
JSON
