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

# ── Locate python + pytest ──────────────────────────────────────────────────
PYTHON="${PYTHON:-python3}"
PYTEST="${PYTEST:-pytest}"

export PYTHONPATH="$WORKSPACE${PYTHONPATH:+:$PYTHONPATH}"

# ── Load seed-specific expected values ─────────────────────────────────────
EXPECTED_JSON="$REPORTS/expected.json"

APP_TYPE=$($PYTHON -c "import json; d=json.load(open('$EXPECTED_JSON')); print(d.get('app_type','web_api'))")
MONOLITH_FILE=$($PYTHON -c "import json; d=json.load(open('$EXPECTED_JSON')); print(d.get('monolith_file','app.py'))")

# Write per-check data to temp dir so Python scripts can read without quoting issues
GDIR=$(mktemp -d)
$PYTHON - <<PYEOF
import json
d = json.load(open('$EXPECTED_JSON'))
json.dump(d.get('modules', []),         open('$GDIR/modules.json','w'))
json.dump(d.get('public_apis', {}),     open('$GDIR/public_apis.json','w'))
json.dump(d.get('module_contents', {}), open('$GDIR/module_contents.json','w'))
PYEOF

# Write all check scripts to files (avoids all shell quoting issues)
cat > "$GDIR/check1.py" <<'PYEOF'
import json, os, sys
ws = sys.argv[1]; gdir = sys.argv[2]
modules = json.load(open(gdir + '/modules.json'))
missing = [m for m in modules if not os.path.isfile(ws + '/' + m + '.py')]
assert not missing, 'Missing module files: ' + str(missing)
print('MODULE_FILES_OK')
PYEOF

cat > "$GDIR/check2.py" <<'PYEOF'
import json, subprocess, sys, os
ws = sys.argv[1]; gdir = sys.argv[2]
modules = json.load(open(gdir + '/modules.json'))
env = dict(os.environ)
env['PYTHONPATH'] = ws + (':' + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
for m in modules:
    r = subprocess.run([sys.executable, '-c', 'import ' + m],
                       capture_output=True, text=True, cwd=ws, env=env)
    assert r.returncode == 0, m + ' not independently importable: ' + r.stderr
print('INDEPENDENT_IMPORT_OK')
PYEOF

cat > "$GDIR/check3.py" <<'PYEOF'
import json, subprocess, sys, os
ws = sys.argv[1]; gdir = sys.argv[2]
modules = json.load(open(gdir + '/modules.json'))
import_all = '; '.join('import ' + m for m in modules)
env = dict(os.environ)
env['PYTHONPATH'] = ws + (':' + env['PYTHONPATH'] if env.get('PYTHONPATH') else '')
r = subprocess.run([sys.executable, '-c', import_all],
                   capture_output=True, text=True, cwd=ws, env=env)
assert r.returncode == 0, 'Circular/import error: ' + r.stderr
print('NO_CIRCULAR_OK')
PYEOF

cat > "$GDIR/check4.py" <<'PYEOF'
import json, sys
ws = sys.argv[1]; gdir = sys.argv[2]
sys.path.insert(0, ws)
public_apis = json.load(open(gdir + '/public_apis.json'))
for mod_name, api_items in public_apis.items():
    mod = __import__(mod_name)
    for item in api_items:
        assert hasattr(mod, item), mod_name + '.' + item + ' missing from public API'
print('PUBLIC_API_OK')
PYEOF

cat > "$GDIR/check5.py" <<'PYEOF'
import json, sys
ws = sys.argv[1]; gdir = sys.argv[2]
sys.path.insert(0, ws)
contents = json.load(open(gdir + '/module_contents.json'))
for mod_name, expected_items in contents.items():
    mod = __import__(mod_name)
    for item in expected_items:
        assert hasattr(mod, item), 'Expected ' + item + ' in ' + mod_name + ' but not found'
print('MODULE_CONTENTS_OK')
PYEOF

cat > "$GDIR/check8.py" <<'PYEOF'
import sys, os
ws = sys.argv[1]; monolith = sys.argv[3]
mf = ws + '/' + monolith
if not os.path.exists(mf):
    print('MONOLITH_GONE_OK')
else:
    lines = [l for l in open(mf).readlines() if l.strip() and not l.strip().startswith('#')]
    assert len(lines) < 20, 'Monolith still has ' + str(len(lines)) + ' non-blank lines'
    print('MONOLITH_THINNED_OK')
PYEOF

cat > "$GDIR/check9.py" <<'PYEOF'
import json, os, sys
ws = sys.argv[1]; gdir = sys.argv[2]
modules = json.load(open(gdir + '/modules.json'))
total_lines = sum(
    len(open(ws + '/' + m + '.py').readlines())
    for m in modules if os.path.isfile(ws + '/' + m + '.py')
)
assert total_lines >= 30, 'New modules only have ' + str(total_lines) + ' lines — functionality likely deleted'
print('LINE_COUNT_OK (' + str(total_lines) + ' lines)')
PYEOF

cat > "$GDIR/check10.py" <<'PYEOF'
import json, ast, os, sys
ws = sys.argv[1]; gdir = sys.argv[2]
modules = json.load(open(gdir + '/modules.json'))

def get_imports(filepath):
    try: tree = ast.parse(open(filepath).read())
    except: return set()
    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module: imports.add(node.module.split('.')[0])
    return imports & set(modules)

module_imports = {}
for m in modules:
    fp = ws + '/' + m + '.py'
    if os.path.isfile(fp):
        module_imports[m] = get_imports(fp)

def has_cycle(graph):
    visited = set()
    def dfs(node, path):
        if node in path: return True
        if node in visited: return False
        path.add(node); visited.add(node)
        for nb in graph.get(node, set()):
            if dfs(nb, path): return True
        path.discard(node)
        return False
    return any(dfs(n, set()) for n in graph)

assert not has_cycle(module_imports), 'Circular import in module graph: ' + str(module_imports)
print('IMPORT_RULES_OK')
PYEOF

cat > "$GDIR/check11.py" <<'PYEOF'
import json, os, sys
ws = sys.argv[1]; gdir = sys.argv[2]
modules = json.load(open(gdir + '/modules.json'))
for m in modules:
    fp = ws + '/' + m + '.py'
    if os.path.isfile(fp):
        lines = [l for l in open(fp).readlines() if l.strip()]
        assert len(lines) >= 5, m + '.py has only ' + str(len(lines)) + ' non-blank lines'
print('MODULE_NONEMPTY_OK')
PYEOF

cat > "$GDIR/check12.py" <<'PYEOF'
import json, sys
submission = sys.argv[4]
att = json.load(open(submission + '/attestation.json'))
assert att.get('verdict') == 'pass'
print('ATTESTATION_OK')
PYEOF

cd "$WORKSPACE"

# Run all checks (each script receives: ws gdir monolith_file submission)
check "$PYTHON '$GDIR/check1.py'  '$WORKSPACE' '$GDIR' '$MONOLITH_FILE' '$SUBMISSION'" "missing_module_files"
check "$PYTHON '$GDIR/check2.py'  '$WORKSPACE' '$GDIR' '$MONOLITH_FILE' '$SUBMISSION'" "module_not_independently_importable"
check "$PYTHON '$GDIR/check3.py'  '$WORKSPACE' '$GDIR' '$MONOLITH_FILE' '$SUBMISSION'" "circular_imports_detected"
check "$PYTHON '$GDIR/check4.py'  '$WORKSPACE' '$GDIR' '$MONOLITH_FILE' '$SUBMISSION'" "public_api_missing"
check "$PYTHON '$GDIR/check5.py'  '$WORKSPACE' '$GDIR' '$MONOLITH_FILE' '$SUBMISSION'" "module_contents_wrong"
check "$PYTEST tests/ -q --tb=no -p no:cacheprovider --import-mode=importlib 2>&1 | tail -1 | grep -E '^[0-9]+ passed'" "tests_fail"
check "$PYTEST tests/ -q --tb=no -p no:cacheprovider --import-mode=importlib 2>&1 | grep -v 'warning' | grep -qv 'failed'" "tests_have_failures"
check "$PYTHON '$GDIR/check8.py'  '$WORKSPACE' '$GDIR' '$MONOLITH_FILE' '$SUBMISSION'" "monolith_not_split"
check "$PYTHON '$GDIR/check9.py'  '$WORKSPACE' '$GDIR' '$MONOLITH_FILE' '$SUBMISSION'" "too_few_lines"
check "$PYTHON '$GDIR/check10.py' '$WORKSPACE' '$GDIR' '$MONOLITH_FILE' '$SUBMISSION'" "import_rules_violated"
check "$PYTHON '$GDIR/check11.py' '$WORKSPACE' '$GDIR' '$MONOLITH_FILE' '$SUBMISSION'" "module_file_too_small"
check "$PYTHON '$GDIR/check12.py' '$WORKSPACE' '$GDIR' '$MONOLITH_FILE' '$SUBMISSION'" "bad_attestation"

# Cleanup
rm -rf "$GDIR"

# Score
PARTIAL=$($PYTHON -c "print(round($PASSED/max(1,$CHECKS), 2))")
if [ "$PASSED" -eq "$CHECKS" ]; then SUCCESS=1; PASS=true; else SUCCESS=0; PASS=false; fi
FM=$($PYTHON -c "import json; print(json.dumps([x for x in '${FAILURES}'.split(',') if x]))")

cat > "$REPORTS/score.json" <<JSON
{
  "pass": $PASS,
  "primary": {"success": $SUCCESS},
  "secondary": {"checks_passed": $PASSED, "checks_total": $CHECKS, "partial_score": $PARTIAL},
  "failure_modes": $FM
}
JSON
