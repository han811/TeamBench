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

# 1. config.json is valid JSON
check "python3 -c \"
import json, sys
with open('config.json') as f:
    cfg = json.load(f)
assert isinstance(cfg, dict), 'config.json must be a JSON object'
print('CONFIG_VALID_JSON')
\"" "invalid_json"

# 2. config.json contains required keys
check "python3 -c \"
import json
with open('config.json') as f:
    cfg = json.load(f)
required = ['instance_type', 'instance_count', 'cache_size_mb',
            'thread_count', 'batch_size', 'connection_pool_size',
            'enable_compression', 'enable_keep_alive']
missing = [k for k in required if k not in cfg]
assert not missing, 'Missing keys: ' + str(missing)
print('CONFIG_KEYS_OK')
\"" "missing_config_keys"

# 3. Cost within budget
check "python3 -c \"
import json, sys
sys.path.insert(0, '.')
from simulator import compute_cost, BUDGET_PER_MONTH
with open('config.json') as f:
    cfg = json.load(f)
cost = compute_cost(cfg)
assert cost <= BUDGET_PER_MONTH, 'Cost ' + str(cost) + ' exceeds budget ' + str(BUDGET_PER_MONTH)
print('COST_OK: ' + str(round(cost, 2)))
\"" "cost_exceeds_budget"

# 4. p50 latency meets target
check "python3 -c \"
import json, sys
sys.path.insert(0, '.')
from simulator import compute_performance, P50_TARGET_MS
with open('config.json') as f:
    cfg = json.load(f)
perf = compute_performance(cfg)
p50 = perf.get('p50_ms', 9999)
assert p50 <= P50_TARGET_MS, 'p50=' + str(p50) + 'ms exceeds target ' + str(P50_TARGET_MS) + 'ms'
print('P50_OK: ' + str(p50) + 'ms')
\"" "p50_target_missed"

# 5. p99 latency meets target
check "python3 -c \"
import json, sys
sys.path.insert(0, '.')
from simulator import compute_performance, P99_TARGET_MS
with open('config.json') as f:
    cfg = json.load(f)
perf = compute_performance(cfg)
p99 = perf.get('p99_ms', 9999)
assert p99 <= P99_TARGET_MS, 'p99=' + str(p99) + 'ms exceeds target ' + str(P99_TARGET_MS) + 'ms'
print('P99_OK: ' + str(p99) + 'ms')
\"" "p99_target_missed"

# 6. Throughput meets target
check "python3 -c \"
import json, sys
sys.path.insert(0, '.')
from simulator import compute_performance, THROUGHPUT_TARGET_RPS
with open('config.json') as f:
    cfg = json.load(f)
perf = compute_performance(cfg)
tput = perf.get('throughput_rps', 0)
assert tput >= THROUGHPUT_TARGET_RPS, 'throughput=' + str(tput) + 'rps below target ' + str(THROUGHPUT_TARGET_RPS) + 'rps'
print('THROUGHPUT_OK: ' + str(tput) + 'rps')
\"" "throughput_target_missed"

# 7. Reliability above threshold
check "python3 -c \"
import json, sys
sys.path.insert(0, '.')
from simulator import compute_performance, RELIABILITY_TARGET
with open('config.json') as f:
    cfg = json.load(f)
perf = compute_performance(cfg)
rel = perf.get('reliability', 0)
assert rel >= RELIABILITY_TARGET, 'reliability=' + str(rel) + ' below target ' + str(RELIABILITY_TARGET)
print('RELIABILITY_OK: ' + str(rel))
\"" "reliability_below_threshold"

# 8. Weighted score above baseline (0.40)
check "python3 -c \"
import json, sys
sys.path.insert(0, '.')
from simulator import compute_cost, compute_performance, weighted_score
with open('config.json') as f:
    cfg = json.load(f)
cost = compute_cost(cfg)
perf = compute_performance(cfg)
ws = weighted_score(cost, perf)
assert ws > 0.40, 'Weighted score ' + str(ws) + ' not above baseline 0.40'
print('SCORE_OK: ' + str(ws))
\"" "score_below_baseline"

# 9. Not over-provisioned (cost <= 95% of budget)
check "python3 -c \"
import json, sys
sys.path.insert(0, '.')
from simulator import compute_cost, BUDGET_PER_MONTH
with open('config.json') as f:
    cfg = json.load(f)
cost = compute_cost(cfg)
cap = BUDGET_PER_MONTH * 0.95
assert cost <= cap, 'Over-provisioned: cost ' + str(cost) + ' > 95pct budget ' + str(cap)
print('EFFICIENCY_OK: ' + str(round(cost, 2)))
\"" "over_provisioned"

# 10. instance_type is valid
check "python3 -c \"
import json, sys
sys.path.insert(0, '.')
from simulator import INSTANCE_TYPES
with open('config.json') as f:
    cfg = json.load(f)
itype = cfg.get('instance_type', '')
assert itype in INSTANCE_TYPES, 'Invalid instance_type: ' + str(itype)
print('INSTANCE_TYPE_OK: ' + itype)
\"" "invalid_instance_type"

# 11. instance_count >= 1
check "python3 -c \"
import json
with open('config.json') as f:
    cfg = json.load(f)
count = cfg.get('instance_count', 0)
assert isinstance(count, int) and count >= 1, 'instance_count must be int >= 1, got ' + str(count)
print('INSTANCE_COUNT_OK: ' + str(count))
\"" "invalid_instance_count"

# 12. All targets pass simultaneously via simulator --check
check "python3 simulator.py --check" "simulator_check_fail"

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
