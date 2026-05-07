#!/usr/bin/env bash
# Run TeamBench crossmodel evaluation for Qwen3.5 models.
#
# Prerequisites:
#   1. Launch vLLM servers: bash scripts/launch_qwen35_vllm.sh
#   2. Wait for servers to be ready: bash scripts/launch_qwen35_vllm.sh status
#
# Usage:
#   bash scripts/run_qwen35_experiments.sh batch1    # Run 0.8B, 2B, 4B, 9B sequentially
#   bash scripts/run_qwen35_experiments.sh 0.8b      # Run single model
#   bash scripts/run_qwen35_experiments.sh 2b
#   bash scripts/run_qwen35_experiments.sh 4b
#   bash scripts/run_qwen35_experiments.sh 9b
#   bash scripts/run_qwen35_experiments.sh 35b       # Run 35B (batch 2, after launch_qwen35_vllm.sh batch2)
#   bash scripts/run_qwen35_experiments.sh all        # Run all (batch1 then batch2)

set -euo pipefail
cd "$(dirname "$0")/.."

# Model configs: name:port:output_file
declare -A MODELS=(
    ["0.8b"]="vllm:Qwen/Qwen3.5-0.8B@http://localhost:8010/v1:crossmodel_qwen3.5_0.8b_seed0.json"
    ["2b"]="vllm:Qwen/Qwen3.5-2B@http://localhost:8011/v1:crossmodel_qwen3.5_2b_seed0.json"
    ["4b"]="vllm:Qwen/Qwen3.5-4B@http://localhost:8012/v1:crossmodel_qwen3.5_4b_seed0.json"
    ["9b"]="vllm:Qwen/Qwen3.5-9B@http://localhost:8013/v1:crossmodel_qwen3.5_9b_seed0.json"
    ["35b"]="vllm:Qwen/Qwen3.5-35B-A3B@http://localhost:8014/v1:crossmodel_qwen3.5_35b_a3b_seed0.json"
)

wait_for_server() {
    local port="$1"
    local name="$2"
    local max_wait=300  # 5 minutes
    local elapsed=0
    echo "  Waiting for $name on port $port..."
    while ! curl -s --max-time 2 "http://localhost:$port/v1/models" >/dev/null 2>&1; do
        sleep 5
        elapsed=$((elapsed + 5))
        if [ "$elapsed" -ge "$max_wait" ]; then
            echo "  ERROR: $name on port $port not ready after ${max_wait}s"
            return 1
        fi
    done
    echo "  $name ready!"
    return 0
}

run_model() {
    local key="$1"
    local config="${MODELS[$key]}"
    IFS=':' read -r prefix_and_model port_part output_file <<< "$config"
    local model_str="${prefix_and_model}:${port_part}"
    local port
    port=$(echo "$port_part" | grep -oP ':\K\d+(?=/)')

    echo ""
    echo "========================================="
    echo "Running: $model_str"
    echo "Output:  shared/ablation_results/$output_file"
    echo "========================================="

    wait_for_server "$port" "$key" || return 1

    python scripts/run_crossmodel.py \
        --model "$model_str" \
        2>&1 | tee "logs/crossmodel_qwen35_${key}.log"

    # Move output to expected location if run_crossmodel.py wrote a different name
    echo "  Done: $key"
}

case "${1:-batch1}" in
    0.8b|2b|4b|9b|35b)
        run_model "$1"
        ;;
    batch1)
        echo "Running Qwen3.5 batch 1: 0.8B, 2B, 4B, 9B"
        for size in 0.8b 2b 4b 9b; do
            run_model "$size"
        done
        echo ""
        echo "Batch 1 complete!"
        ;;
    batch2)
        echo "Running Qwen3.5 batch 2: 35B-A3B"
        run_model "35b"
        echo ""
        echo "Batch 2 complete!"
        ;;
    all)
        echo "Running all Qwen3.5 models"
        for size in 0.8b 2b 4b 9b; do
            run_model "$size"
        done
        echo ""
        echo "Batch 1 complete. Now launching batch 2 (35B)..."
        echo "First stop batch 1 servers and start 35B..."
        bash scripts/launch_qwen35_vllm.sh batch2
        run_model "35b"
        echo ""
        echo "All Qwen3.5 experiments complete!"
        ;;
    *)
        echo "Usage: $0 {batch1|batch2|all|0.8b|2b|4b|9b|35b}"
        exit 1
        ;;
esac
