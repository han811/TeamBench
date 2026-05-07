#!/usr/bin/env bash
# Run ALL open-source models with FULL 5-condition ablation on 100-task set.
# This is the CORRECT evaluation pipeline for the leaderboard.
#
# Usage: nohup bash scripts/run_all_opensource_100_ablation.sh > logs/oss_100_ablation.log 2>&1 &

set -o pipefail
cd "$(dirname "$0")/.."

CONDA_BASE="${CONDA_BASE:-$HOME/miniconda3}"
source "$CONDA_BASE/etc/profile.d/conda.sh"
conda activate vllm-qwen
export PYTHONNOUSERSITE=1

mkdir -p logs shared/ablation_results

run_model() {
    local HF_ID="$1"
    local SHORT_NAME="$2"
    local PORT="$3"
    local TP="$4"
    local PARSER="$5"
    local DTYPE="$6"
    local MAX_LEN="$7"
    local GPUS="$8"
    local EXTRA="${9:-}"

    local OUTFILE="shared/ablation_results/lb100_${SHORT_NAME}_seed0.json"
    local LOG_SERVER="logs/vllm_${SHORT_NAME}_abl.log"

    echo ""
    echo "================================================================"
    echo "  MODEL: $SHORT_NAME ($HF_ID)"
    echo "  Port=$PORT TP=$TP Parser=$PARSER GPUs=$GPUS"
    echo "  Output: $OUTFILE"
    echo "  $(date)"
    echo "================================================================"

    # Skip if already done
    if [ -f "$OUTFILE" ]; then
        echo "  Output exists. Skipping."
        return 0
    fi

    # Kill leftover GPU processes
    fuser /dev/nvidia0 /dev/nvidia1 /dev/nvidia2 /dev/nvidia3 2>/dev/null | tr ' ' '\n' | grep -v '^$' | xargs -r kill -9 2>/dev/null
    sleep 5

    # Start vLLM server
    echo "  Starting vLLM server..."
    CUDA_VISIBLE_DEVICES="$GPUS" python -s -m vllm.entrypoints.openai.api_server \
        --model "$HF_ID" \
        --port "$PORT" \
        --trust-remote-code \
        --enable-auto-tool-choice \
        --tool-call-parser "$PARSER" \
        --max-model-len "$MAX_LEN" \
        --gpu-memory-utilization 0.70 \
        --dtype "$DTYPE" \
        --tensor-parallel-size "$TP" \
        --enforce-eager $EXTRA > "$LOG_SERVER" 2>&1 &
    local SERVER_PID=$!

    # Wait for server (up to 40 min for large models on NFS)
    echo "  Waiting for server (up to 40 min)..."
    for i in $(seq 1 240); do
        if curl -s -m 2 "http://localhost:$PORT/v1/models" > /dev/null 2>&1; then
            echo "  Server ready after $((i*10))s"
            break
        fi
        if ! kill -0 $SERVER_PID 2>/dev/null; then
            echo "  ERROR: Server crashed. Check $LOG_SERVER"
            tail -5 "$LOG_SERVER"
            return 1
        fi
        sleep 10
    done

    if ! curl -s -m 3 "http://localhost:$PORT/v1/models" > /dev/null 2>&1; then
        echo "  ERROR: Server never started. Killing."
        kill $SERVER_PID 2>/dev/null; kill -9 $SERVER_PID 2>/dev/null
        return 1
    fi

    # Run FULL 5-condition ablation
    echo "  Starting 5-condition ablation on 100 tasks..."
    PYTHONUNBUFFERED=1 python3 -s scripts/run_leaderboard_100_ablation.py \
        --model "vllm:${HF_ID}@http://localhost:${PORT}/v1" \
        --seeds 0 \
        --output "$OUTFILE" \
        2>&1 | tee "logs/eval_${SHORT_NAME}_abl.log"

    echo "  Evaluation finished."

    # Kill server
    kill $SERVER_PID 2>/dev/null
    sleep 3
    kill -9 $SERVER_PID 2>/dev/null
    wait $SERVER_PID 2>/dev/null
    echo "  Server stopped."
}

echo "========================================"
echo "  TeamBench 100-Task ABLATION Eval"
echo "  5 conditions × 100 tasks × seed 0"
echo "  $(date)"
echo "========================================"

# PARSER NOTES:
#   - Qwen3.5 family emits XML tool-call format → must use qwen3_xml parser
#     (hermes parser silently drops calls — confirmed bug, see memory/lb100_tokenizer_parser_bug.md)
#   - Qwen3 (NOT 3.5) emits proper JSON → hermes works
#   - Qwen3-Coder uses dedicated qwen3_coder parser
#   - Phi-4 family uses phi4_mini_json
#   - GLM-4 uses glm45 parser (no glm4 parser in vllm 0.17.1)
#   - gemma-3 uses functiongemma
#   - gemma-4 (E4B etc.) needs newer vLLM with gemma4 parser — DO NOT run from this env

# --- Small models (1 GPU) ---
run_model "Qwen/Qwen3.5-0.8B" "qwen35-0.8b" 8000 1 "qwen3_xml" "bfloat16" 32768 "0"
run_model "Qwen/Qwen3.5-2B" "qwen35-2b" 8000 1 "qwen3_xml" "bfloat16" 32768 "0"
run_model "Qwen/Qwen3-4B" "qwen3-4b" 8000 1 "hermes" "bfloat16" 32768 "0"
run_model "Qwen/Qwen3.5-4B" "qwen35-4b" 8000 1 "qwen3_xml" "bfloat16" 32768 "0"
run_model "google/codegemma-7b-it" "codegemma-7b" 8000 1 "hermes" "bfloat16" 32768 "0"
run_model "Qwen/Qwen3-8B" "qwen3-8b" 8000 1 "hermes" "bfloat16" 32768 "0"
run_model "Qwen/Qwen3.5-9B" "qwen35-9b" 8000 1 "qwen3_xml" "bfloat16" 32768 "0"
run_model "Qwen/Qwen3-14B" "qwen3-14b" 8000 1 "hermes" "bfloat16" 32768 "0"

# --- Medium models (1 GPU, 20-27B) ---
run_model "mistralai/Devstral-Small-2-24B-Instruct-2512" "devstral-24b" 8000 1 "mistral" "bfloat16" 32768 "0"

# --- MoE models (need 2 GPUs — full expert weights don't fit in 1x48GB) ---
run_model "Qwen/Qwen3.5-35B-A3B" "qwen35-35b-a3b" 8000 2 "qwen3_xml" "bfloat16" 32768 "0,1"
run_model "Qwen/Qwen3-Coder-30B-A3B-Instruct" "qwen3-coder-30b" 8000 2 "qwen3_coder" "bfloat16" 32768 "0,1"

# --- Large dense models (TP=2, 2 GPUs) ---
run_model "Qwen/Qwen3.5-27B" "qwen35-27b" 8000 2 "qwen3_xml" "bfloat16" 32768 "0,1"
run_model "google/gemma-3-27b-it" "gemma3-27b" 8000 2 "functiongemma" "bfloat16" 32768 "0,1"
run_model "Qwen/Qwen2.5-Coder-32B-Instruct" "qwen25-coder-32b" 8000 2 "hermes" "bfloat16" 32768 "0,1"
run_model "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B" "deepseek-r1-32b" 8000 2 "hermes" "bfloat16" 32768 "0,1"

# --- Additional models (Phi-4, GLM-4, Qwen3-32B) ---
run_model "microsoft/Phi-4-mini-instruct" "phi4-mini" 8000 1 "phi4_mini_json" "bfloat16" 32768 "0"
run_model "microsoft/phi-4" "phi4" 8000 1 "phi4_mini_json" "bfloat16" 32768 "0"
run_model "THUDM/glm-4-9b-chat" "glm4-9b" 8000 1 "glm45" "bfloat16" 32768 "0"
run_model "Qwen/Qwen3-32B" "qwen3-32b" 8000 2 "hermes" "bfloat16" 32768 "0,1"

echo ""
echo "========================================"
echo "  ALL MODELS COMPLETE — $(date)"
echo "========================================"
