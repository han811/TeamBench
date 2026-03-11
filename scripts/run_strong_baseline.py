#!/usr/bin/env python3
"""Run strong baseline conditions (oracle_cot, oracle_2pass) on cross-model tasks.

These control for the "more compute" confound: if a team of 3 agents uses
3x the compute of a single oracle, does the team benefit come from role
separation or just more thinking?

Usage:
    python scripts/run_strong_baseline.py --model gemini-3-flash-preview
    python scripts/run_strong_baseline.py --model gemini-3-flash-preview --conditions oracle_cot
"""
import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Same 28 tasks as cross-model evaluation
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

BASELINE_CONDITIONS = ["oracle_cot", "oracle_2pass"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--conditions", nargs="+", default=BASELINE_CONDITIONS,
                    help="Which baseline conditions to run")
    ap.add_argument("--seeds", nargs="+", type=int, default=[0])
    args = ap.parse_args()

    model_tag = args.model.replace("-", "").replace(".", "")
    fname = f"strong_baseline_{model_tag}_seed0.json"
    outpath = os.path.join("shared", "ablation_results", fname)

    from harness.ablation import run_full_ablation, AblationCondition
    conds = [AblationCondition(c) for c in args.conditions]
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
