#!/usr/bin/env bash
# Serve a model via vLLM with OpenAI-compatible API.
#
# Usage:
#   bash scripts/serve_vllm.sh Qwen/Qwen3-4B  0 8001
#   bash scripts/serve_vllm.sh Qwen/Qwen3-8B  1 8002
#   bash scripts/serve_vllm.sh Qwen/Qwen3-14B 2 8003
#   bash scripts/serve_vllm.sh Qwen/Qwen3.5-27B 2,3 8004        # TP=2
#   bash scripts/serve_vllm.sh Qwen/Qwen3-Coder-30B-A3B-Instruct 1 8005
#
# Args: <model_id> <gpu_ids> <port> [extra_args...]

set -euo pipefail

MODEL="${1:?Usage: serve_vllm.sh <model> <gpu_ids> <port> [extra_args...]}"
GPU="${2:-0}"
PORT="${3:-8000}"
shift 3 || true
EXTRA_ARGS=("$@")

# Use vllm-qwen env Python directly (conda activate is broken due to frozendict conflict)
VLLM_PYTHON="${VLLM_PYTHON:-<HOME>/<redacted-user>/miniconda3/envs/vllm-qwen/bin/python}"
if [ ! -x "$VLLM_PYTHON" ]; then
    # Fallback: try conda activate
    CONDA_BASE="${CONDA_BASE:-<HOME>/<redacted-user>/miniconda3}"
    if [ -f "$CONDA_BASE/etc/profile.d/conda.sh" ]; then
        source "$CONDA_BASE/etc/profile.d/conda.sh"
        conda activate vllm-qwen 2>/dev/null || true
    fi
    VLLM_PYTHON="python"
fi

# Determine tensor parallelism from GPU count
IFS=',' read -ra GPU_ARRAY <<< "$GPU"
TP=${#GPU_ARRAY[@]}

echo "=== Serving $MODEL on GPU $GPU (TP=$TP), port $PORT ==="
echo "  Python: $VLLM_PYTHON"
echo "  vLLM:   $($VLLM_PYTHON -c 'import vllm; print(vllm.__version__)' 2>/dev/null || echo 'not found')"

mkdir -p logs

TP_ARGS=()
if [ "$TP" -gt 1 ]; then
    TP_ARGS=(--tensor-parallel-size "$TP")
fi

CUDA_VISIBLE_DEVICES="$GPU" $VLLM_PYTHON -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" \
    --port "$PORT" \
    --trust-remote-code \
    --enable-auto-tool-choice \
    --tool-call-parser "${TOOL_CALL_PARSER:-hermes}" \
    --max-model-len "${MAX_MODEL_LEN:-32768}" \
    --gpu-memory-utilization 0.90 \
    --dtype auto \
    "${TP_ARGS[@]}" \
    "${EXTRA_ARGS[@]}" \
    2>&1 | tee "logs/vllm_${MODEL##*/}_gpu${GPU}.log"
