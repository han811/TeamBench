#!/usr/bin/env bash
# Quick progress check for all running ablation experiments
echo "=== $(date) ==="
echo ""
echo "Running processes:"
ps -o pid,pcpu,pmem,etime,args -p $(pgrep -f "run_crossmodel|run_strong|rerun_fixed|smoke_fix" | tr '\n' ',')0 2>/dev/null | grep -v "^$"
echo ""

echo "Result files:"
for f in shared/ablation_results/crossmodel_sonnet46_seed0.json \
         shared/ablation_results/crossmodel_haiku45_seed0.json \
         shared/ablation_results/strong_baseline_gemini3flashpreview_seed0.json \
         shared/ablation_results/rerun_fixed_full_condition.json \
         shared/ablation_results/smoke_fix_test2.json; do
    if [ -f "$f" ]; then
        scored=$(python3 -c "import json; d=json.load(open('$f')); runs=d.get('runs',[]); print(sum(1 for r in runs if r.get('partial_score') is not None))" 2>/dev/null)
        total=$(python3 -c "import json; d=json.load(open('$f')); print(len(d.get('runs',[])))" 2>/dev/null)
        echo "  DONE: $(basename $f): $scored/$total scored"
    else
        echo "  WAIT: $(basename $f)"
    fi
done
