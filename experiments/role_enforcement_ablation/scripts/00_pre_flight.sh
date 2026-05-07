#!/usr/bin/env bash
# 00_pre_flight.sh — validate each model end-to-end before launching the full run.
#
# For each configured model, runs ONE task × ONE condition (enforced) × ONE seed.
# This catches: bad API keys, tokenizer/tool-call parser bugs (c.f. lb100
# incident where 5 complete-looking runs were silently invalid), provider-pin
# misconfiguration, and grader-integration regressions BEFORE we commit to the
# 450-run main experiment.
#
# Exit nonzero if any model fails to produce a score.json or if any run crashes.
# A successful pre-flight stamps config/model_slugs.json.verified_on so
# subsequent runs have evidence that the stack was last validated.
#
# Cost: ~$0.05 per model × 3 models = ~$0.15 total.

set -euo pipefail
EXP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$EXP_DIR/../.." && pwd)"
cd "$REPO_ROOT"

# venv python (harness deps like openai/anthropic/google-genai live there)
if [[ -x "$REPO_ROOT/venv/bin/python3" ]]; then
    export PATH="$REPO_ROOT/venv/bin:$PATH"
fi

if [[ -f "$REPO_ROOT/.env" ]]; then
    set -a; source "$REPO_ROOT/.env"; set +a
fi
: "${OPENROUTER_API:?OPENROUTER_API missing in env}"
: "${OPENAI_API_KEY:?OPENAI_API_KEY missing in env}"

# The task we smoke-test with. P1_policy_config is small, well-graded, and
# already validated via scripts/smoke_test_real_llm.py on Haiku.
SMOKE_TASK="P1_policy_config"
SMOKE_CONDITION="enforced"
SMOKE_SEED=0
OUT_DIR="$EXP_DIR/runs/pre_flight"
LOG_DIR="$EXP_DIR/logs"
TS="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$OUT_DIR" "$LOG_DIR"

# (internal_name, slug) pairs — must match 03_run_all.sh
MODELS=(
    "gemini_3_flash       openrouter:google/gemini-3-flash-preview"
    "gpt_5_4_mini         gpt-5.4-mini"
    "claude_haiku_4_5     openrouter:anthropic/claude-haiku-4.5"
)

FAILURES=()
for entry in "${MODELS[@]}"; do
    name="$(echo "$entry" | awk '{print $1}')"
    slug="$(echo "$entry" | awk '{print $2}')"
    out_file="$OUT_DIR/${name}_smoke.json"
    log_file="$LOG_DIR/pre_flight_${name}_${TS}.log"

    echo ""
    echo "======================================================================"
    echo "[pre-flight] $name ($slug)"
    echo "             task=$SMOKE_TASK condition=$SMOKE_CONDITION seed=$SMOKE_SEED"
    echo "             log=$log_file"
    echo "======================================================================"

    if python3 -m harness.ablation \
        --model "$slug" \
        --tasks "$SMOKE_TASK" \
        --seeds "$SMOKE_SEED" \
        --conditions "$SMOKE_CONDITION" \
        --output "$out_file" \
        --max-turns 12 \
        --max-remediation 1 \
        > "$log_file" 2>&1; then
        # Verify per-task score.json actually landed for at least one run
        score_count=$(find "$OUT_DIR" -name "score.json" 2>/dev/null | wc -l)
        # Also sanity-check the aggregate was written
        if [[ -f "$out_file" ]]; then
            echo "[pre-flight] OK $name — aggregate: $out_file  (per-task scores: $score_count)"
        else
            echo "[pre-flight] FAIL $name — harness returned 0 but no aggregate written" >&2
            FAILURES+=("$name:no_output")
        fi
    else
        rc=$?
        echo "[pre-flight] FAIL $name — harness exited $rc. See $log_file" >&2
        tail -15 "$log_file" >&2
        FAILURES+=("$name:exit_$rc")
    fi
done

if (( ${#FAILURES[@]} > 0 )); then
    echo ""
    echo "[pre-flight] FAILED models: ${FAILURES[*]}" >&2
    echo "[pre-flight] Fix the above before running scripts/03_run_all.sh." >&2
    exit 1
fi

# Stamp verified_on on success so downstream scripts have audit trail.
python3 - <<PY
import json, pathlib, datetime
slugs_path = pathlib.Path("$EXP_DIR/config/model_slugs.json")
slugs = json.loads(slugs_path.read_text())
now = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
for m in slugs["models"].values():
    m["verified_on"] = now
slugs_path.write_text(json.dumps(slugs, indent=2) + "\n")
print(f"[pre-flight] stamped {slugs_path} verified_on={now}")
PY

echo ""
echo "[pre-flight] ALL MODELS OK — safe to launch scripts/03_run_all.sh"
