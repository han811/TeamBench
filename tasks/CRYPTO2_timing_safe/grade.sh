#!/usr/bin/env bash
# CRYPTO2 grader: verify 4 timing-unsafe comparisons fixed + 1 non-secret comparison preserved
set -euo pipefail

WORKSPACE="${1:-${WORKSPACE_DIR:-/workspace}}"
REPORTS="${2:-${REPORTS_DIR:-/reports}}"
SUBMISSION="${3:-/submission}"
TASK_DIR="${4:-/task}"

cd "$WORKSPACE"

pass=true
partial=0
total=10
findings=""

check() {
    local id="$1"
    local desc="$2"
    local result="$3"
    if [ "$result" = "pass" ]; then
        partial=$((partial + 1))
        findings="${findings}{\"id\":\"${id}\",\"ok\":true,\"note\":\"${desc}\"},"
    else
        pass=false
        findings="${findings}{\"id\":\"${id}\",\"ok\":false,\"note\":\"${desc}\"},"
    fi
}

# Install dependencies if needed
pip install pytest 2>/dev/null || true

# -------------------------------------------------------------------
# C1: pytest tests/ passes overall
# -------------------------------------------------------------------
if python -m pytest tests/ -q --tb=no 2>/dev/null; then
    check "C1" "All pytest tests pass" "pass"
else
    check "C1" "pytest tests/ failed" "fail"
fi

# -------------------------------------------------------------------
# C2: auth/api_keys.py uses compare_digest
# -------------------------------------------------------------------
if python3 - <<'PYEOF' 2>/dev/null
import ast, sys
src = open('auth/api_keys.py').read()
if 'compare_digest' in src:
    sys.exit(0)
sys.exit(1)
PYEOF
then
    check "C2" "api_keys.py uses compare_digest for key validation" "pass"
else
    check "C2" "api_keys.py still uses == for key comparison (timing-unsafe)" "fail"
fi

# -------------------------------------------------------------------
# C3: auth/signatures.py uses compare_digest
# -------------------------------------------------------------------
if python3 - <<'PYEOF' 2>/dev/null
import ast, sys
src = open('auth/signatures.py').read()
if 'compare_digest' in src:
    sys.exit(0)
sys.exit(1)
PYEOF
then
    check "C3" "signatures.py uses compare_digest for HMAC verification" "pass"
else
    check "C3" "signatures.py still uses == for signature comparison (timing-unsafe)" "fail"
fi

# -------------------------------------------------------------------
# C4: auth/passwords.py uses compare_digest
# -------------------------------------------------------------------
if python3 - <<'PYEOF' 2>/dev/null
import ast, sys
src = open('auth/passwords.py').read()
if 'compare_digest' in src:
    sys.exit(0)
sys.exit(1)
PYEOF
then
    check "C4" "passwords.py uses compare_digest for hash comparison" "pass"
else
    check "C4" "passwords.py still uses == for hash comparison (timing-unsafe)" "fail"
fi

# -------------------------------------------------------------------
# C5: auth/sessions.py uses compare_digest
# -------------------------------------------------------------------
if python3 - <<'PYEOF' 2>/dev/null
import ast, sys
src = open('auth/sessions.py').read()
if 'compare_digest' in src:
    sys.exit(0)
sys.exit(1)
PYEOF
then
    check "C5" "sessions.py uses compare_digest for token validation" "pass"
else
    check "C5" "sessions.py still uses == for token comparison (timing-unsafe)" "fail"
fi

# -------------------------------------------------------------------
# C6: auth/users.py does NOT use compare_digest (no-overfix check)
# -------------------------------------------------------------------
if python3 - <<'PYEOF' 2>/dev/null
import ast, sys
src = open('auth/users.py').read()
if 'compare_digest' in src:
    sys.exit(1)  # Over-fixed: username lookup must NOT use compare_digest
sys.exit(0)
PYEOF
then
    check "C6" "users.py preserved: username lookup still uses simple == (not over-fixed)" "pass"
else
    check "C6" "users.py over-fixed: compare_digest added to username lookup (security theater)" "fail"
fi

# -------------------------------------------------------------------
# C7: test_timing.py passes (timing variance statistical test)
# -------------------------------------------------------------------
if python -m pytest tests/test_timing.py -q --tb=no 2>/dev/null; then
    check "C7" "Timing variance test passes (comparison not key-position-dependent)" "pass"
else
    check "C7" "Timing variance test failed (comparison may still be timing-unsafe)" "fail"
fi

# -------------------------------------------------------------------
# C8: test_no_overfix.py passes (verifies users.py unchanged)
# -------------------------------------------------------------------
if python -m pytest tests/test_no_overfix.py -q --tb=no 2>/dev/null; then
    check "C8" "No-overfix test passes (users.py uses simple comparison)" "pass"
else
    check "C8" "No-overfix test failed (users.py was incorrectly modified)" "fail"
fi

# -------------------------------------------------------------------
# C9: Functional tests (all non-timing/non-overfix tests) pass
# -------------------------------------------------------------------
if python -m pytest tests/ -q --tb=no \
    --ignore=tests/test_timing.py \
    --ignore=tests/test_no_overfix.py 2>/dev/null; then
    check "C9" "All functional tests pass (api_keys, signatures, passwords, sessions)" "pass"
else
    check "C9" "Functional tests failed after changes" "fail"
fi

# -------------------------------------------------------------------
# C10: Syntax validity — all auth modules parse cleanly
# -------------------------------------------------------------------
if python3 - <<'PYEOF' 2>/dev/null
import ast, sys, os
modules = [
    'auth/api_keys.py',
    'auth/signatures.py',
    'auth/passwords.py',
    'auth/sessions.py',
    'auth/users.py',
]
for path in modules:
    if not os.path.exists(path):
        print(f"Missing: {path}", file=sys.stderr)
        sys.exit(1)
    try:
        ast.parse(open(path).read())
    except SyntaxError as e:
        print(f"SyntaxError in {path}: {e}", file=sys.stderr)
        sys.exit(1)
sys.exit(0)
PYEOF
then
    check "C10" "All auth modules have valid syntax" "pass"
else
    check "C10" "Syntax error in one or more auth modules" "fail"
fi

# -------------------------------------------------------------------
# Collect pytest summary
# -------------------------------------------------------------------
pytest_out=$(python -m pytest tests/ -q --tb=no 2>&1 || true)
pytest_pass=$(echo "$pytest_out" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+' || echo "0")
pytest_fail=$(echo "$pytest_out" | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+' || echo "0")

partial_score=$(awk "BEGIN {printf \"%.4f\", $partial / $total}")
findings="${findings%,}"  # Remove trailing comma

cat > "${REPORTS}/score.json" <<EOF
{
  "pass": $( [ "$pass" = "true" ] && echo "true" || echo "false" ),
  "secondary": {
    "partial_score": $partial_score,
    "checks_passed": $partial,
    "total_checks": $total,
    "pytest_passed": ${pytest_pass:-0},
    "pytest_failed": ${pytest_fail:-0}
  },
  "failure_modes": [],
  "checklist": [$findings]
}
EOF
