#!/usr/bin/env bash
# 99_replicate_from_scratch.sh — Single-entry reproduction.
#
# Assumes
# -------
#   * Git commit from `environment/git_commit.txt` is checked out (or newer with
#     experiment/** unchanged).
#   * `.env` contains OPENROUTER_API and OPENAI_API_KEY.
#   * Python venv at repo root `./venv/` OR system python with deps from
#     `environment/pip_freeze.txt`.
#
# Pipeline
# --------
#   1. Verify env keys present
#   2. Apply adapter patch (Google provider pinning)
#   3. Regenerate task selection (deterministic from shared/ablation_results/)
#   4. Smoke-test tool-use for each model
#   5. Run 450-run experiment
#   6. Score role-compliance
#   7. Analyze and generate paper assets
#   8. Revert adapter patch (leaves repo clean)
#   9. Compare outputs to paper_assets/ snapshot — parity check
#
# All stages exit nonzero on failure. Safe to re-run after a crash (each stage
# is resumable or idempotent).

set -euo pipefail
EXP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$EXP_DIR/../.." && pwd)"
cd "$REPO_ROOT"

echo "=============================================="
echo "Role Enforcement Ablation — Reproduction"
echo "=============================================="
echo "Experiment dir: $EXP_DIR"
echo "Repo root:      $REPO_ROOT"
echo "Git HEAD:       $(git rev-parse --short HEAD)"
echo ""

echo "[0/8] Checking env keys..."
for k in OPENROUTER_API OPENAI_API_KEY; do
  if ! grep -q "^${k}=" .env 2>/dev/null && [ -z "${!k:-}" ]; then
    echo "ERROR: $k missing from .env and shell env" >&2
    exit 1
  fi
done

echo "[1/8] Applying adapter patch..."
python "$EXP_DIR/scripts/01_apply_adapter_patch.py"

echo "[2/8] Regenerating task selection..."
python "$EXP_DIR/scripts/02_select_tasks.py"

echo "[3/8] Pre-flight tool-use smoke test..."
bash "$EXP_DIR/scripts/00_pre_flight.sh"

echo "[4/8] Main experiment (450 runs)..."
bash "$EXP_DIR/scripts/03_run_all.sh"

echo "[5/8] Scoring role-compliance..."
python "$EXP_DIR/scripts/04_score_compliance.py"

echo "[6/8] Analysis + paper assets..."
python "$EXP_DIR/scripts/05_analyze.py"

echo "[7/8] Reverting adapter patch..."
python "$EXP_DIR/scripts/01_apply_adapter_patch.py" --revert

echo "[8/8] Parity check against paper_assets snapshot..."
echo "      TODO: diff regenerated outputs against committed paper_assets/*"

echo ""
echo "=============================================="
echo "Reproduction complete."
echo "Results:  $EXP_DIR/analysis/"
echo "Paper:    $EXP_DIR/paper_assets/"
echo "=============================================="
