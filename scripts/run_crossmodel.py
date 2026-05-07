#!/usr/bin/env python3
"""Launch cross-model ablation for a single model.

Usage:
    python scripts/run_crossmodel.py --model gpt-5-nano
"""
import argparse
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TASKS = [
    "MULTI1_fullstack_fix", "TEST1_spec_to_tests", "O2_incident_rootcause",
    "PIPE1_etl_fix", "TRAP1_spec_conflict", "TRAP3_metric_mirage",
    "TRAP5_security_theater", "CROSS1_api_contract", "CROSS3_protocol_bridge",
    "CRYPTO1_nonce_reuse", "DIST1_queue_race", "SEC1_vuln_patch",
    "SEC3_crypto_upgrade", "D1_schema_drift", "D8_csv_cleanup",
    "TEST2_regression", "TEST5_mutation_resistant", "O1_service_health",
    "O3_log_analysis", "P1_policy_config", "P3_access_control",
    "SPEC1_feature_impl", "SPEC3_data_model", "INC1_cascade_failure",
    "INC4_dns_miscfg", "IR1_evidence_qa", "NEG1_tradeoff_config",
    "CR5_test_coverage",
]

CONDITIONS = ["oracle", "restricted", "team_no_verify", "team_no_plan", "full"]

MODEL_TO_FILE = {
    "gpt-5-nano": "crossmodel_gpt5nano_seed0.json",
    "gpt-5-mini": "crossmodel_gpt5mini_seed0.json",
    "gemini-3.1-flash-lite-preview": "crossmodel_g31lite_seed0.json",
    "gemini-3-flash-preview": "crossmodel_g3flash_seed0.json",
    "claude-sonnet-4-6": "crossmodel_sonnet46_seed0.json",
    "claude-haiku-4-5-20251001": "crossmodel_haiku45_seed0.json",
    # Qwen3.5 family (vLLM-served)
    "vllm:Qwen/Qwen3.5-0.8B@http://localhost:8010/v1": "crossmodel_qwen3.5_0.8b_seed0.json",
    "vllm:Qwen/Qwen3.5-2B@http://localhost:8011/v1": "crossmodel_qwen3.5_2b_seed0.json",
    "vllm:Qwen/Qwen3.5-4B@http://localhost:8012/v1": "crossmodel_qwen3.5_4b_seed0.json",
    "vllm:Qwen/Qwen3.5-9B@http://localhost:8013/v1": "crossmodel_qwen3.5_9b_seed0.json",
    "vllm:Qwen/Qwen3.5-35B-A3B@http://localhost:8014/v1": "crossmodel_qwen3.5_35b_a3b_seed0.json",
    # Batch 1: Phi-4, Mistral Small, GLM
    "vllm:microsoft/Phi-4-mini-instruct@http://localhost:8010/v1": "crossmodel_phi4_mini_seed0.json",
    "vllm:microsoft/phi-4@http://localhost:8011/v1": "crossmodel_phi4_14b_seed0.json",
    "vllm:mistralai/Mistral-Small-3.2-24B-Instruct-2506@http://localhost:8012/v1": "crossmodel_mistral_small_3.2_seed0.json",
    "vllm:THUDM/glm-4-9b-chat@http://localhost:8013/v1": "crossmodel_glm4_9b_seed0.json",
    # Batch 2: Llama 4 Scout (TP=4)
    "vllm:meta-llama/Llama-4-Scout-17B-16E-Instruct@http://localhost:8014/v1": "crossmodel_llama4_scout_seed0.json",
    # Batch 3: Nemotron 3 Super (TP=4)
    "vllm:nvidia/NVIDIA-Nemotron-3-Super-49B-v1@http://localhost:8014/v1": "crossmodel_nemotron3_super_seed0.json",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--seeds", nargs="+", type=int, default=[0])
    args = ap.parse_args()

    fname = MODEL_TO_FILE.get(args.model, f"crossmodel_{args.model.replace('-','')}_seed0.json")
    outpath = os.path.join("shared", "ablation_results", fname)

    from harness.ablation import run_full_ablation, AblationCondition
    conds = [AblationCondition(c) for c in CONDITIONS]
    run_full_ablation(
        model=args.model,
        tasks=TASKS,
        seeds=args.seeds,
        tasks_dir="tasks",
        output=outpath,
        conditions=conds,
    )


if __name__ == "__main__":
    main()
