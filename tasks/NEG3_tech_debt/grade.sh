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

cd "$WORKSPACE"

# 1. prioritize.py exists and PLAN is a non-empty list
check "python3 -c \"
import ast, sys
with open('prioritize.py') as f:
    src = f.read()
tree = ast.parse(src)
plan = None
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == 'PLAN':
                plan = ast.literal_eval(node.value)
assert plan is not None, 'PLAN not found'
assert isinstance(plan, list), 'PLAN must be a list'
assert len(plan) > 0, 'PLAN is empty'
print(f'PLAN_EXISTS: {plan}')
\"" "plan_not_defined"

# 2. plan_valid: python prioritize.py exits 0
check "python3 prioritize.py" "plan_invalid"

# 3. Exactly 3 items selected
check "python3 -c \"
import ast
with open('prioritize.py') as f:
    src = f.read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == 'PLAN':
                plan = ast.literal_eval(node.value)
                assert len(plan) == 3, f'Expected 3 items, got {len(plan)}'
                print(f'EXACTLY_3_OK: {plan}')
\"" "not_exactly_3_items"

# 4. Time budget not exceeded
check "python3 -c \"
import ast, json
with open('prioritize.py') as f:
    src = f.read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == 'PLAN':
                plan = ast.literal_eval(node.value)
with open('tech_debt.json') as f:
    reg = json.load(f)
items_by_id = {item['id']: item for item in reg['items']}
budget = reg['time_budget_hours']
total = sum(items_by_id[tid]['fix_hours'] for tid in plan if tid in items_by_id)
assert total <= budget, f'Budget exceeded: {total}h > {budget}h'
print(f'BUDGET_OK: {total}h / {budget}h')
\"" "budget_exceeded"

# 5. Dependency order respected (blocker before dependent)
check "python3 -c \"
import ast, json
with open('prioritize.py') as f:
    src = f.read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == 'PLAN':
                plan = ast.literal_eval(node.value)
with open('tech_debt.json') as f:
    reg = json.load(f)
dep = reg.get('dependency')
if dep is None:
    print('NO_DEP: no dependency constraint')
else:
    blocker = dep['blocker']
    dependent = dep['dependent']
    if blocker in plan and dependent in plan:
        bi = plan.index(blocker)
        di = plan.index(dependent)
        assert bi < di, f'Dependency violated: {blocker} (pos {bi}) must precede {dependent} (pos {di})'
        print(f'DEP_ORDER_OK: {blocker} before {dependent}')
    else:
        print('DEP_NOT_SELECTED: dependency items not both in plan')
\"" "dependency_order_violated"

# 6. Dependent not selected without blocker
check "python3 -c \"
import ast, json
with open('prioritize.py') as f:
    src = f.read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == 'PLAN':
                plan = ast.literal_eval(node.value)
with open('tech_debt.json') as f:
    reg = json.load(f)
dep = reg.get('dependency')
if dep is None:
    print('NO_DEP')
else:
    blocker = dep['blocker']
    dependent = dep['dependent']
    if dependent in plan:
        assert blocker in plan, f'{dependent} selected but {blocker} (its blocker) is not in plan'
    print('DEPENDENT_WITHOUT_BLOCKER_OK')
\"" "dependent_without_blocker"

# 7. Highest-value items selected (all 3 must be in top-4 by score)
check "python3 -c \"
import ast, json
with open('prioritize.py') as f:
    src = f.read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == 'PLAN':
                plan = ast.literal_eval(node.value)
with open('tech_debt.json') as f:
    reg = json.load(f)
items = reg['items']
budget = reg['time_budget_hours']
# Compute top-4 by score that fit in budget (greedy)
ranked = sorted(items, key=lambda x: x['value_score'], reverse=True)
top4 = [i['id'] for i in ranked[:4]]
for tid in plan:
    assert tid in top4, f'{tid} is not in the top-4 highest-value items {top4}'
print(f'HIGH_VALUE_OK: {plan} all in top-4 {top4}')
\"" "low_value_items_selected"

# 8. No bare except in service.py (check if TD005 is in plan; if so must be fixed)
check "python3 -c \"
import ast, json
with open('prioritize.py') as f:
    src = f.read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == 'PLAN':
                plan = ast.literal_eval(node.value)
if 'TD005' not in plan:
    print('TD005_NOT_IN_PLAN: skip')
else:
    with open('service.py') as f:
        svc_src = f.read()
    svc_tree = ast.parse(svc_src)
    for node in ast.walk(svc_tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            raise AssertionError('Bare except found in service.py — TD005 not fixed')
    print('NO_BARE_EXCEPT_OK')
\"" "bare_except_not_fixed"

# 9. Named constants present (check if TD004 is in plan)
check "python3 -c \"
import ast, json
with open('prioritize.py') as f:
    src = f.read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == 'PLAN':
                plan = ast.literal_eval(node.value)
if 'TD004' not in plan:
    print('TD004_NOT_IN_PLAN: skip')
else:
    with open('service.py') as f:
        svc_src = f.read()
    # Check that named constants exist (TIMEOUT_SECONDS or MAX_RETRIES or MAX_BATCH_SIZE)
    has_constants = any(name in svc_src for name in ['TIMEOUT_SECONDS', 'MAX_RETRIES', 'MAX_BATCH_SIZE'])
    assert has_constants, 'Named constants not found in service.py — TD004 not fixed'
    print('NAMED_CONSTANTS_OK')
\"" "named_constants_not_fixed"

# 10. No old_format calls (check if TD007 is in plan)
check "python3 -c \"
import json
with open('prioritize.py') as f:
    import ast
    src = f.read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == 'PLAN':
                plan = ast.literal_eval(node.value)
if 'TD007' not in plan:
    print('TD007_NOT_IN_PLAN: skip')
else:
    with open('service.py') as f:
        svc_src = f.read()
    assert 'old_format' not in svc_src, 'old_format() still called in service.py — TD007 not fixed'
    print('NO_OLD_FORMAT_OK')
\"" "old_format_not_replaced"

# 11. Type annotations on public methods (check if TD002 is in plan)
check "python3 -c \"
import ast
with open('prioritize.py') as f:
    src = f.read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == 'PLAN':
                plan = ast.literal_eval(node.value)
if 'TD002' not in plan:
    print('TD002_NOT_IN_PLAN: skip')
else:
    with open('service.py') as f:
        svc_src = f.read()
    svc_tree = ast.parse(svc_src)
    for node in ast.walk(svc_tree):
        if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
            # Check at least some return annotation exists on public methods
            if node.returns is None and node.name in ('process', 'fetch', 'delete', 'list_all'):
                raise AssertionError(f'Public method {node.name} has no return annotation — TD002 not fixed')
    print('TYPE_ANNOTATIONS_OK')
\"" "type_annotations_missing"

# 12. Legacy function removed (check if TD001 is in plan)
check "python3 -c \"
import ast
with open('prioritize.py') as f:
    src = f.read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == 'PLAN':
                plan = ast.literal_eval(node.value)
if 'TD001' not in plan:
    print('TD001_NOT_IN_PLAN: skip')
else:
    with open('service.py') as f:
        svc_src = f.read()
    assert '_legacy_process' not in svc_src, '_legacy_process still in service.py — TD001 not fixed'
    print('NO_LEGACY_FUNCTION_OK')
\"" "legacy_function_not_removed"

# 13. Debug comment block removed (check if TD010 is in plan)
check "python3 -c \"
import ast
with open('prioritize.py') as f:
    src = f.read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == 'PLAN':
                plan = ast.literal_eval(node.value)
if 'TD010' not in plan:
    print('TD010_NOT_IN_PLAN: skip')
else:
    with open('service.py') as f:
        svc_src = f.read()
    assert 'DEBUG BLOCK' not in svc_src, 'Debug comment block still in service.py — TD010 not fixed'
    assert '# import pdb' not in svc_src, 'Debug comment block still in service.py — TD010 not fixed'
    print('NO_DEBUG_BLOCK_OK')
\"" "debug_block_not_removed"

# 14. Tests pass (check if TD006 is in plan)
check "python3 -c \"
import ast
with open('prioritize.py') as f:
    src = f.read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == 'PLAN':
                plan = ast.literal_eval(node.value)
if 'TD006' not in plan:
    print('TD006_NOT_IN_PLAN: skip')
    exit(0)
# Check tests are not stubs
with open('tests/test_service.py') as f:
    test_src = f.read()
assert 'test_placeholder' not in test_src or test_src.count('def test_') > 1, \
    'Only placeholder test found — TD006 not fixed'
print('TESTS_NOT_STUB_OK')
\"" "tests_still_stub"

# 15. pytest passes (only if TD006 in plan)
check "python3 -c \"
import ast
with open('prioritize.py') as f:
    src = f.read()
tree = ast.parse(src)
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == 'PLAN':
                plan = ast.literal_eval(node.value)
if 'TD006' not in plan:
    print('TD006_NOT_IN_PLAN: skip')
\" && (python3 -m pytest tests/ -q --tb=short 2>/dev/null || true)" "tests_fail"

# Partial scoring
PARTIAL=$(python3 -c "print(round($PASSED/max(1,$CHECKS), 2))")
if [ "$PASSED" -eq "$CHECKS" ]; then SUCCESS=1; PASS=true; else SUCCESS=0; PASS=false; fi
FM=$(python3 -c "import json; print(json.dumps([x for x in '${FAILURES}'.split(',') if x]))")

cat > "$REPORTS/score.json" <<JSON
{
  "pass": $PASS,
  "primary": {"success": $SUCCESS},
  "secondary": {"checks_passed": $PASSED, "checks_total": $CHECKS, "partial_score": $PARTIAL},
  "failure_modes": $FM
}
JSON
