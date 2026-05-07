#!/usr/bin/env bash
# 03_run_all.sh.
# Drive the full 450-run role-enforcement ablation.
#
# Layout per model:
#   runs/<model>/results_<condition>.json (+ .checkpoint.jsonl)
#   runs/<model>/ablation_runs/<task>/<run_id>/  (per-run artifacts)
#   logs/<model>_<ts>.log                         (stdout/stderr)
#
# Models run in parallel; conditions are sequential within a model so the
# OpenRouter rate limit is not multiplied by 3. Resume is automatic via the
# checkpoint file.

set -euo pipefail
EXP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$EXP_DIR/../.." && pwd)"

cd "$REPO_ROOT"

# Use the repo venv python (which has openai/anthropic/google-genai installed)
# in preference to system python3 (which does not).
if [[ -x "$REPO_ROOT/venv/bin/python3" ]]; then
    export PATH="$REPO_ROOT/venv/bin:$PATH"
fi

# Load .env so harness adapters see OPENROUTER_API and OPENAI_API_KEY. The
# harness has a secondary .env loader but we also export here so child procs
# inherit the keys without re-parsing.
if [[ -f "$REPO_ROOT/.env" ]]; then
    set -a; source "$REPO_ROOT/.env"; set +a
fi
: "${OPENROUTER_API:?OPENROUTER_API missing — required for Gemini + Haiku via OR}"
: "${OPENAI_API_KEY:?OPENAI_API_KEY missing — required for gpt-5.4-mini direct}"

SELECTION="$EXP_DIR/config/task_selection.json"
LOG_DIR="$EXP_DIR/logs"
RUNS_DIR="$EXP_DIR/runs"
TS="$(date -u +%Y%m%dT%H%M%SZ)"

mkdir -p "$LOG_DIR" "$RUNS_DIR"

if [[ ! -f "$SELECTION" ]]; then
    echo "[run_all] missing $SELECTION; run scripts/02_select_tasks.py first" >&2
    exit 2
fi

TASKS="$(python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(" ".join(d["selected_flat"]))' "$SELECTION")"
if [[ -z "$TASKS" ]]; then
    echo "[run_all] task list empty in $SELECTION" >&2
    exit 2
fi

echo "[run_all] tasks: $TASKS"
echo "[run_all] timestamp tag: $TS"

# (model_name, model_slug) pairs. Slugs match harness/adapters/__init__.py.
MODELS=(
    "gemini_3_flash       openrouter:google/gemini-3-flash-preview"
    "gpt_5_4_mini         gpt-5.4-mini"
    "claude_haiku_4_5     openrouter:anthropic/claude-haiku-4.5"
)

CONDITIONS=("prompt_only" "enforced" "enforced_shared_history")
SEEDS="0 1"

run_model() {
    local name="$1"
    local slug="$2"
    local mlog="$LOG_DIR/${name}_${TS}.log"
    mkdir -p "$RUNS_DIR/$name"
    {
        echo "[$(date -u +%H:%M:%S)] start $name slug=$slug"
        for cond in "${CONDITIONS[@]}"; do
            local out="$RUNS_DIR/$name/results_${cond}.json"
            echo "[$(date -u +%H:%M:%S)]   $name :: $cond -> $out"
            python3 -m harness.ablation \
                --model "$slug" \
                --tasks $TASKS \
                --seeds $SEEDS \
                --conditions "$cond" \
                --output "$out" \
                --max-turns 20 \
                --max-remediation 2
        done
        echo "[$(date -u +%H:%M:%S)] done $name"
    } >>"$mlog" 2>&1
}

PIDS=()
for entry in "${MODELS[@]}"; do
    name="$(echo "$entry" | awk '{print $1}')"
    slug="$(echo "$entry" | awk '{print $2}')"
    echo "[run_all] launching $name -> $LOG_DIR/${name}_${TS}.log"
    run_model "$name" "$slug" &
    PIDS+=("$!")
done

EXIT=0
for pid in "${PIDS[@]}"; do
    if ! wait "$pid"; then
        echo "[run_all] worker $pid failed" >&2
        EXIT=1
    fi
done

echo "[run_all] all workers exited; status=$EXIT"
exit "$EXIT"
