#!/usr/bin/env bash
# Seed-aware grader for D5: Query Optimization
# Reads expected values from expected.json produced by the generator.
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

# ── Extract seed-specific metadata from expected.json ────────────────────────
DOMAIN=$(python3 -c "import json; e=json.load(open('$EXPECTED')); print(e.get('domain','users_orders'))" 2>/dev/null || echo "users_orders")
QUERY_COUNT=$(python3 -c "import json; e=json.load(open('$EXPECTED')); print(e.get('query_count',4))" 2>/dev/null || echo "4")
REQUIRED_INDEXES=$(python3 -c "import json; e=json.load(open('$EXPECTED')); print(json.dumps(e.get('required_indexes',[])))" 2>/dev/null || echo "[]")
FORBIDDEN_PATTERNS=$(python3 -c "import json; e=json.load(open('$EXPECTED')); print(json.dumps(e.get('forbidden_patterns',[])))" 2>/dev/null || echo "[]")

# Determine DB file from domain
DB_FILE=$(python3 -c "
d = '$DOMAIN'
print({'users_orders':'store.db','products_reviews':'catalog.db','employees_departments':'hr.db'}.get(d,'store.db'))
" 2>/dev/null || echo "store.db")

# ── Check 1: database.py runs without error ───────────────────────────────────
check "python3 database.py" "database_py_crash"

# ── Check 2: DB file exists after database.py ────────────────────────────────
check "test -f '$DB_FILE'" "db_file_missing"

# ── Check 3: queries.py imports without error ─────────────────────────────────
check "python3 -c 'import sys; sys.path.insert(0,\".\"); import queries'" "queries_import_error"

# ── Check 4: All query functions present ─────────────────────────────────────
check "python3 -c \"
import sys, json
sys.path.insert(0, '.')
import queries
n = int('$QUERY_COUNT')
missing = [f'query_{i}' for i in range(1, n+1) if not hasattr(queries, f'query_{i}')]
assert not missing, f'Missing query functions: {missing}'
print('QUERY_FUNCTIONS_OK')
\"" "missing_query_functions"

# ── Check 5: All queries return non-empty lists ───────────────────────────────
check "python3 -c \"
import sys, sqlite3, json
sys.path.insert(0, '.')
import queries
n = int('$QUERY_COUNT')
conn = sqlite3.connect('$DB_FILE')
for i in range(1, n+1):
    fn = getattr(queries, f'query_{i}')
    rows = fn(conn)
    assert isinstance(rows, list), f'query_{i} did not return a list'
    assert len(rows) > 0, f'query_{i} returned 0 rows'
conn.close()
print('ALL_QUERIES_RETURN_ROWS_OK')
\"" "queries_return_empty"

# ── Check 6: No N+1 pattern — single query per call for aggregations ──────────
check "python3 -c \"
import sys, sqlite3, json
sys.path.insert(0, '.')
forbidden = json.loads('$FORBIDDEN_PATTERNS')
if 'n_plus_1' not in forbidden:
    print('N_PLUS_1_CHECK_SKIPPED')
    exit(0)

import queries, inspect
source = inspect.getsource(queries)

# N+1 pattern: a for-loop body that contains a cursor.execute call
import re
# Look for loops that contain cursor.execute inside — simple heuristic
lines = source.split('\\n')
in_loop = False
loop_depth = 0
execute_in_loop = False
for line in lines:
    stripped = line.strip()
    if re.match(r'for .+ in .+:', stripped):
        in_loop = True
        loop_depth += 1
    if in_loop and ('cur' in stripped or 'cursor' in stripped) and '.execute' in stripped:
        execute_in_loop = True
        break

assert not execute_in_loop, (
    'N+1 pattern detected: found cursor.execute() inside a for-loop. '
    'Replace with a single aggregated query.'
)
print('N_PLUS_1_ELIMINATED_OK')
\"" "n_plus_1_pattern_present"

# ── Check 7: Required indexes exist in the database ──────────────────────────
check "python3 -c \"
import sqlite3, json
required = json.loads('$REQUIRED_INDEXES')
conn = sqlite3.connect('$DB_FILE')
cur = conn.cursor()
cur.execute(\\\"SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'\\\")
index_rows = cur.fetchall()
conn.close()

# Build set of (table.column) strings from actual index definitions
import re
indexed_cols = set()
for name, tbl, sql in index_rows:
    if sql:
        # Extract columns from CREATE INDEX ... ON table(col1, col2, ...)
        m = re.search(r'ON\s+\w+\s*\(([^)]+)\)', sql, re.IGNORECASE)
        if m:
            cols = [c.strip() for c in m.group(1).split(',')]
            for col in cols:
                indexed_cols.add(f'{tbl}.{col}')
        indexed_cols.add(f'{tbl}.*')

missing_indexes = []
for req in required:
    # req is like 'orders.user_id' or 'orders(user_id,status,total)'
    if '(' in req:
        # composite index — check table has any composite index
        tbl = req.split('(')[0]
        cols_str = req.split('(')[1].rstrip(')')
        cols = [c.strip() for c in cols_str.split(',')]
        found = any(
            all(f'{tbl}.{c}' in indexed_cols for c in cols)
            or name.startswith(tbl) and sql and all(c in sql for c in cols)
            for name, t, sql in index_rows
            if t == tbl and sql
        )
        if not found:
            missing_indexes.append(req)
    else:
        tbl, col = req.rsplit('.', 1)
        if f'{tbl}.{col}' not in indexed_cols:
            missing_indexes.append(req)

assert not missing_indexes, f'Missing required indexes: {missing_indexes}'
print('REQUIRED_INDEXES_OK')
\"" "required_indexes_missing"

# ── Check 8: database.py contains CREATE INDEX statements ────────────────────
check "python3 -c \"
with open('database.py') as f:
    src = f.read()
assert 'CREATE INDEX' in src.upper(), (
    'database.py must contain CREATE INDEX statements'
)
print('CREATE_INDEX_IN_SOURCE_OK')
\"" "no_create_index_in_database_py"

# ── Check 9: queries.py has no obvious N+1 (for-loop with execute) ───────────
check "python3 -c \"
import re
with open('queries.py') as f:
    src = f.read()
lines = src.split('\\n')
in_for = 0
violation = None
for i, line in enumerate(lines, 1):
    stripped = line.strip()
    if re.match(r'for\s+\S+\s+in\s+.+:', stripped):
        in_for += 1
    if in_for > 0 and re.search(r'\\.execute\s*\(', stripped):
        violation = i
        break
assert violation is None, (
    f'Line {violation}: cursor.execute() inside for-loop — N+1 pattern must be eliminated'
)
print('QUERY_SOURCE_CLEAN_OK')
\"" "n_plus_1_in_query_source"

# ── Check 10: pytest correctness tests pass (excludes performance tests) ──────
check "python3 -m pytest tests/ -x -q --tb=short -k 'correctness or stability' 2>&1 | tail -5 | grep -E '(passed|PASSED)'" "pytest_correctness_fail"

# ── Check 11: Each query returns dict rows (not tuples) ───────────────────────
check "python3 -c \"
import sys, sqlite3
sys.path.insert(0, '.')
import queries
n = int('$QUERY_COUNT')
conn = sqlite3.connect('$DB_FILE')
for i in range(1, n+1):
    fn = getattr(queries, f'query_{i}')
    rows = fn(conn)
    if rows:
        assert isinstance(rows[0], dict), f'query_{i} must return list of dicts, got {type(rows[0])}'
conn.close()
print('DICT_ROWS_OK')
\"" "queries_return_tuples_not_dicts"

# ── Check 12: Result stability — same output on repeated calls ────────────────
check "python3 -c \"
import sys, sqlite3
sys.path.insert(0, '.')
import queries
n = int('$QUERY_COUNT')
conn = sqlite3.connect('$DB_FILE')
for i in range(1, n+1):
    fn = getattr(queries, f'query_{i}')
    a = fn(conn)
    b = fn(conn)
    assert a == b, f'query_{i} returned different results on repeated calls'
conn.close()
print('STABILITY_OK')
\"" "query_result_unstable"

# ── Check 13: Performance — each query under target latency ──────────────────
check "python3 -c \"
import sys, sqlite3, time, json
sys.path.insert(0, '.')
import queries
expected = json.load(open('$EXPECTED'))
conn = sqlite3.connect('$DB_FILE')
failures = []
for q_name, qmeta in expected.get('queries', {}).items():
    fn_name = q_name
    if not hasattr(queries, fn_name):
        continue
    fn = getattr(queries, fn_name)
    target_ms = qmeta.get('target_ms', 100)
    # warm up
    fn(conn)
    # measure
    start = time.perf_counter()
    rows = fn(conn)
    elapsed_ms = (time.perf_counter() - start) * 1000
    if elapsed_ms >= target_ms:
        failures.append(f'{q_name}: {elapsed_ms:.1f}ms >= target {target_ms}ms')
conn.close()
assert not failures, 'Performance targets missed: ' + '; '.join(failures)
print('PERFORMANCE_OK')
\"" "performance_target_missed"

# ── Check 14: Schema unchanged — original tables still present ────────────────
check "python3 -c \"
import sqlite3, json
conn = sqlite3.connect('$DB_FILE')
cur = conn.cursor()
cur.execute(\\\"SELECT name FROM sqlite_master WHERE type='table' ORDER BY name\\\")
tables = {r[0] for r in cur.fetchall()}
conn.close()
domain = '$DOMAIN'
expected_tables = {
    'users_orders': {'users','products','orders','order_items'},
    'products_reviews': {'categories','users','products','reviews'},
    'employees_departments': {'departments','employees','projects','assignments'},
}.get(domain, set())
missing = expected_tables - tables
assert not missing, f'Tables dropped or renamed: {missing}'
print('SCHEMA_OK')
\"" "schema_tables_missing"

# ── Check 15: Attestation file (optional, bonus) ──────────────────────────────
check "python3 -c \"
import json, sys, os
att_path = os.path.join('$SUBMISSION', 'attestation.json')
if not os.path.exists(att_path):
    print('NO_ATTESTATION_FILE')
    sys.exit(0)
att = json.load(open(att_path))
assert att.get('verdict') == 'pass', f'verdict={att.get(\"verdict\")}'
print('ATTESTATION_OK')
\"" "bad_attestation"

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
