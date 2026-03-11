#!/usr/bin/env python3
"""Re-run the 16 tasks where verifier damage caused full=0.

These tasks scored full=0.0 with the old orchestrator but team_no_verify>0.3,
indicating the verifier+remediation loop destroyed working solutions.

Now re-running with the fixed orchestrator (workspace snapshots + improved prompts).
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Tasks where full=0 but team_no_verify > 0.3
VERIFIER_DAMAGE_TASKS = [
    "CROSS6_grpc_rest_bridge",
    "PIPE2_api_gateway",
    "LH7_zero_downtime",
    "IR8_search_index",
    "GO1_concurrency_fix",
    "PIPE3_msg_queue",
    "SEC9_vuln_triage",
    "D4_data_pipeline",
    "LH6_audit_trail",
    "CR1_review_respond",
    "INT3_db_migration",
    "INC10_rollback_plan",
    "SEC4_input_validation",
    "S6_caching",
    "INC7_rollback",
    "P2_spec_arbitration",
]


def main():
    from harness.ablation import run_full_ablation, AblationCondition

    # Only re-run the 'full' condition since that's what was broken
    run_full_ablation(
        model="gemini-3-flash-preview",
        tasks=VERIFIER_DAMAGE_TASKS,
        seeds=[0],
        tasks_dir="tasks",
        output="shared/ablation_results/rerun_fixed_full_condition.json",
        conditions=[AblationCondition.FULL],
    )


if __name__ == "__main__":
    main()
