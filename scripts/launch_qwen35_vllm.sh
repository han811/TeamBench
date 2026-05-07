#!/usr/bin/env bash
# Launch Qwen3.5 vLLM servers for TeamBench evaluation.
#
# Batch 1 (4 GPUs parallel, all fit on 1 GPU each):
#   GPU 0 -> Qwen3.5-0.8B  (port 8010, ~2GB)
#   GPU 1 -> Qwen3.5-2B    (port 8011, ~4GB)
#   GPU 2 -> Qwen3.5-4B    (port 8012, ~10GB)
#   GPU 3 -> Qwen3.5-9B    (port 8013, ~20GB)
#
# Batch 2 (TP=2, after batch 1 completes):
#   GPU 0,1 -> Qwen3.5-35B-A3B  (port 8014, MoE ~72GB, TP=2 + FP8)
#
# Usage:
#   bash scripts/launch_qwen35_vllm.sh           # Launch batch 1
#   bash scripts/launch_qwen35_vllm.sh batch2     # Launch batch 2 (35B MoE)
#   bash scripts/launch_qwen35_vllm.sh stop       # Stop all
#   bash scripts/launch_qwen35_vllm.sh status     # Check status

set -euo pipefail
cd "$(dirname "$0")/.."

MODELS_BATCH1=(
    "Qwen/Qwen3.5-0.8B:0:8010"
    "Qwen/Qwen3.5-2B:1:8011"
    "Qwen/Qwen3.5-4B:2:8012"
    "Qwen/Qwen3.5-9B:3:8013"
)

session_name() {
    local model="$1"
    echo "vllm-qwen35-$(echo "$model" | sed 's|.*/||' | tr '[:upper:]' '[:lower:]' | tr '.' '-')"
}

if [ "${1:-}" = "stop" ]; then
    echo "Stopping all Qwen3.5 vLLM servers..."
    for entry in "${MODELS_BATCH1[@]}"; do
        IFS=':' read -r model gpu port <<< "$entry"
        sess=$(session_name "$model")
        tmux kill-session -t "$sess" 2>/dev/null && echo "  Stopped $sess" || echo "  $sess not running"
    done
    tmux kill-session -t vllm-qwen35-35b-a3b 2>/dev/null && echo "  Stopped vllm-qwen35-35b-a3b" || echo "  vllm-qwen35-35b-a3b not running"
    exit 0
fi

if [ "${1:-}" = "status" ]; then
    echo "Qwen3.5 vLLM server status:"
    for entry in "${MODELS_BATCH1[@]}"; do
        IFS=':' read -r model gpu port <<< "$entry"
        sess=$(session_name "$model")
        if tmux has-session -t "$sess" 2>/dev/null; then
            # Check if endpoint responds
            if curl -s --max-time 2 "http://localhost:$port/v1/models" >/dev/null 2>&1; then
                echo "  ✓ $model (port $port) — READY"
            else
                echo "  ⏳ $model (port $port) — loading..."
            fi
        else
            echo "  ✗ $model (port $port) — not running"
        fi
    done
    # Check batch 2
    if tmux has-session -t vllm-qwen35-35b-a3b 2>/dev/null; then
        if curl -s --max-time 2 "http://localhost:8014/v1/models" >/dev/null 2>&1; then
            echo "  ✓ Qwen3.5-35B-A3B (port 8014) — READY"
        else
            echo "  ⏳ Qwen3.5-35B-A3B (port 8014) — loading..."
        fi
    else
        echo "  ✗ Qwen3.5-35B-A3B (port 8014) — not running"
    fi
    exit 0
fi

if [ "${1:-}" = "batch2" ]; then
    echo "Launching Qwen3.5-35B-A3B (MoE) on GPUs 0,1 (TP=2)..."
    # Stop batch 1 servers on GPU 0 and 1 first
    for entry in "${MODELS_BATCH1[@]}"; do
        IFS=':' read -r model gpu port <<< "$entry"
        sess=$(session_name "$model")
        tmux kill-session -t "$sess" 2>/dev/null || true
    done
    echo "  Stopped batch 1 servers"

    tmux kill-session -t vllm-qwen35-35b-a3b 2>/dev/null || true
    tmux new-session -d -s vllm-qwen35-35b-a3b \
        "TOOL_CALL_PARSER=qwen3_xml bash scripts/serve_vllm.sh Qwen/Qwen3.5-35B-A3B 0,1,2,3 8014"
    echo "  [GPU 0,1,2,3] Qwen3.5-35B-A3B -> port 8014 (tmux: vllm-qwen35-35b-a3b)"
    echo ""
    echo "Wait ~5-10 min for model loading."
    echo "Check status: bash scripts/launch_qwen35_vllm.sh status"
    exit 0
fi

# Default: launch batch 1
echo "Launching Qwen3.5 batch 1 (4 models on 4 GPUs)..."
echo ""

for entry in "${MODELS_BATCH1[@]}"; do
    IFS=':' read -r model gpu port <<< "$entry"
    sess=$(session_name "$model")
    tmux kill-session -t "$sess" 2>/dev/null || true
    tmux new-session -d -s "$sess" "TOOL_CALL_PARSER=qwen3_xml bash scripts/serve_vllm.sh $model $gpu $port"
    echo "  [GPU $gpu] $model -> port $port (tmux: $sess, parser=qwen3_xml)"
done

echo ""
echo "Servers launching in background. Wait ~2-5 min for model loading."
echo "Check status:  bash scripts/launch_qwen35_vllm.sh status"
echo "View logs:     tmux attach -t vllm-qwen35-0-8b"
echo "Stop all:      bash scripts/launch_qwen35_vllm.sh stop"
