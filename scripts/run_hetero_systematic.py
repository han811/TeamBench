#!/usr/bin/env python3
"""Run systematic heterogeneous team experiments.

Tests all 27 permutations of 3 model tiers (weak/mid/strong) across 3 roles,
plus 3 cross-family configs, on the 28-task Mini subset.

Usage:
    python scripts/run_hetero_systematic.py --output shared/ablation_results/hetero_systematic.json
    python scripts/run_hetero_systematic.py --config permutations --seed 0
    python scripts/run_hetero_systematic.py --config cross_family --tasks MULTI1_fullstack_fix TEST1_spec_to_tests
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness.ablation import AblationCondition, run_ablation_condition
from harness.adapters import create_adapter
from harness.run_all import discover_tasks, setup_run, grade_run

# ---------------------------------------------------------------------------
# Model tiers
# ---------------------------------------------------------------------------
WEAK = "gemini-3.1-flash-lite-preview"
MID = "gemini-3-flash-preview"
STRONG = "gpt-5-mini"

TIERS = {"weak": WEAK, "mid": MID, "strong": STRONG}

ROLES = ("planner", "executor", "verifier")

# ---------------------------------------------------------------------------
# 28-task Mini subset (same as run_hetero_ablation.py)
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Build all 27 permutation configs
# ---------------------------------------------------------------------------

def _build_permutation_configs() -> dict[str, dict[str, str]]:
    """Return all 27 tier permutations keyed by a short name."""
    configs: dict[str, dict[str, str]] = {}
    tier_names = list(TIERS.keys())  # weak, mid, strong
    for p_tier, e_tier, v_tier in itertools.product(tier_names, repeat=3):
        name = f"P{p_tier[0]}E{e_tier[0]}V{v_tier[0]}"  # e.g. PwEmVs
        configs[name] = {
            "planner": TIERS[p_tier],
            "executor": TIERS[e_tier],
            "verifier": TIERS[v_tier],
        }
    return configs


PERMUTATION_CONFIGS = _build_permutation_configs()

# 3 cross-family configs
CROSS_FAMILY_CONFIGS: dict[str, dict[str, str]] = {
    "cross_claude_plan": {
        "planner": "claude-sonnet-4-6-20250514",
        "executor": "gemini-3-flash-preview",
        "verifier": "gpt-5-nano",
    },
    "cross_gpt_plan": {
        "planner": "gpt-5-mini",
        "executor": "claude-sonnet-4-6-20250514",
        "verifier": "gemini-3-flash-preview",
    },
    "cross_gemini_plan": {
        "planner": "gemini-3-flash-preview",
        "executor": "gpt-5-mini",
        "verifier": "claude-sonnet-4-6-20250514",
    },
}

ALL_CONFIGS: dict[str, dict[str, str]] = {
    **PERMUTATION_CONFIGS,
    **CROSS_FAMILY_CONFIGS,
}

CONFIG_GROUPS = {
    "permutations": PERMUTATION_CONFIGS,
    "cross_family": CROSS_FAMILY_CONFIGS,
    "all": ALL_CONFIGS,
}


# ---------------------------------------------------------------------------
# Approximate per-call cost in USD (input+output tokens, rough estimate)
# Used for Pareto analysis only — not billed here.
# ---------------------------------------------------------------------------
MODEL_COST: dict[str, float] = {
    WEAK: 0.0001,          # gemini-3.1-flash-lite
    MID: 0.0005,           # gemini-3-flash
    STRONG: 0.002,         # gpt-5-mini
    "gpt-5-nano": 0.0001,
    "claude-sonnet-4-6-20250514": 0.003,
}


def _config_cost(model_config: dict[str, str]) -> float:
    """Rough per-task cost estimate for a config (sum of role costs)."""
    return sum(MODEL_COST.get(v, 0.001) for v in model_config.values())


# ---------------------------------------------------------------------------
# Core runner
# ---------------------------------------------------------------------------

def run_hetero_config(
    config_name: str,
    model_config: dict[str, str],
    tasks: list[str],
    tasks_dir: str,
    seed: int,
    runs_base: str,
) -> list[dict]:
    """Run a single heterogeneous config across all tasks for a given seed."""
    fallback_model = model_config.get("executor", next(iter(model_config.values())))
    adapter = create_adapter(model=fallback_model, temperature=0.2)

    run_records: list[dict] = []
    total = len(tasks)

    for i, task_name in enumerate(tasks, 1):
        print(f"  [{i}/{total}] {config_name} x {task_name} (seed={seed})", flush=True)
        start_time = time.time()
        record: dict = {
            "config": config_name,
            "model_config": model_config,
            "task_id": task_name,
            "seed": seed,
            "run_id": "",
            "run_dir": "",
            "pass": False,
            "partial_score": 0.0,
            "elapsed_sec": 0.0,
            "failure_modes": [],
            "error": None,
        }

        try:
            run_id, run_dir, task_dir = setup_run(task_name, tasks_dir, runs_base, seed=seed)
            record["run_id"] = run_id
            record["run_dir"] = run_dir

            meta_path = os.path.join(run_dir, "run_meta.json")
            if os.path.isfile(meta_path):
                with open(meta_path, "r") as mf:
                    meta = json.load(mf)
                meta["condition"] = "hetero"
                meta["model_config"] = model_config
                meta["hetero_config_name"] = config_name
                with open(meta_path, "w") as mf:
                    json.dump(meta, mf, indent=2)

            orch_result = run_ablation_condition(
                condition=AblationCondition.HETERO,
                task_dir=task_dir,
                run_dir=run_dir,
                adapter=adapter,
                max_turns=20,
                max_remediation=2,
                model_config=model_config,
            )

            elapsed = time.time() - start_time
            score = grade_run(task_name, task_dir, run_dir)
            passed = bool(score.get("pass", False))
            partial = score.get("secondary", {}).get(
                "partial_score", 1.0 if passed else 0.0
            )
            record.update({
                "pass": passed,
                "partial_score": float(partial),
                "elapsed_sec": round(elapsed, 1),
                "failure_modes": score.get("failure_modes", []),
            })
            status = "PASS" if passed else "FAIL"
            print(
                f"    {status} (partial={partial:.2f}, {elapsed:.1f}s, "
                f"{orch_result.total_turns} turns)",
                flush=True,
            )

        except Exception as e:
            record["error"] = str(e)
            record["elapsed_sec"] = round(time.time() - start_time, 1)
            print(f"    ERROR: {e}", flush=True)

        run_records.append(record)

    return run_records


# ---------------------------------------------------------------------------
# Analysis helpers (also used by analyze_hetero.py)
# ---------------------------------------------------------------------------

def compute_per_config_summary(
    runs: list[dict],
    configs: dict[str, dict[str, str]],
) -> dict[str, dict]:
    """Compute pass rate and avg partial score per config."""
    per_config: dict[str, dict] = {}
    config_names = {r["config"] for r in runs}
    for cfg_name in config_names:
        cfg_runs = [r for r in runs if r["config"] == cfg_name]
        passes = sum(1 for r in cfg_runs if r["pass"])
        total = len(cfg_runs)
        avg_partial = sum(r["partial_score"] for r in cfg_runs) / max(1, total)
        model_cfg = configs.get(cfg_name, cfg_runs[0]["model_config"] if cfg_runs else {})
        per_config[cfg_name] = {
            "passes": passes,
            "total": total,
            "success_rate": round(passes / max(1, total), 4),
            "avg_partial": round(avg_partial, 4),
            "model_config": model_cfg,
            "estimated_cost_per_task": round(_config_cost(model_cfg), 6),
        }
    return per_config


def compute_marginal_contributions(
    per_config: dict[str, dict],
) -> dict[str, dict]:
    """
    For each role, compute marginal contribution by averaging the score
    improvement from upgrading that role while holding the other two fixed.

    Returns a dict mapping role -> {weak->mid, mid->strong, overall} deltas.
    """
    tier_order = ["weak", "mid", "strong"]
    tier_map = {v: k for k, v in TIERS.items()}  # model -> tier name

    # Decode each permutation config into (p_tier, e_tier, v_tier)
    def decode(cfg_name: str, model_cfg: dict[str, str]) -> tuple[str, str, str] | None:
        if cfg_name not in PERMUTATION_CONFIGS:
            return None
        p = tier_map.get(model_cfg.get("planner", ""), None)
        e = tier_map.get(model_cfg.get("executor", ""), None)
        v = tier_map.get(model_cfg.get("verifier", ""), None)
        if p and e and v:
            return (p, e, v)
        return None

    # Build lookup: (p_tier, e_tier, v_tier) -> success_rate
    tier_to_rate: dict[tuple[str, str, str], float] = {}
    for cfg_name, summary in per_config.items():
        decoded = decode(cfg_name, summary["model_config"])
        if decoded:
            tier_to_rate[decoded] = summary["success_rate"]

    if not tier_to_rate:
        return {}

    marginals: dict[str, dict] = {}
    role_indices = {"planner": 0, "executor": 1, "verifier": 2}

    for role, idx in role_indices.items():
        deltas_wm: list[float] = []  # weak -> mid
        deltas_ms: list[float] = []  # mid -> strong
        # Iterate over all combinations of the OTHER two roles
        other_roles = [r for r in tier_order if True]  # all tiers for other dims
        for t1 in tier_order:
            for t2 in tier_order:
                # Build the "other two roles" context
                if idx == 0:
                    base_w = ("weak", t1, t2)
                    base_m = ("mid", t1, t2)
                    base_s = ("strong", t1, t2)
                elif idx == 1:
                    base_w = (t1, "weak", t2)
                    base_m = (t1, "mid", t2)
                    base_s = (t1, "strong", t2)
                else:
                    base_w = (t1, t2, "weak")
                    base_m = (t1, t2, "mid")
                    base_s = (t1, t2, "strong")

                r_w = tier_to_rate.get(base_w)
                r_m = tier_to_rate.get(base_m)
                r_s = tier_to_rate.get(base_s)
                if r_w is not None and r_m is not None:
                    deltas_wm.append(r_m - r_w)
                if r_m is not None and r_s is not None:
                    deltas_ms.append(r_s - r_m)

        avg_wm = round(sum(deltas_wm) / len(deltas_wm), 4) if deltas_wm else None
        avg_ms = round(sum(deltas_ms) / len(deltas_ms), 4) if deltas_ms else None
        all_deltas = deltas_wm + deltas_ms
        overall = round(sum(all_deltas) / len(all_deltas), 4) if all_deltas else None
        marginals[role] = {
            "avg_delta_weak_to_mid": avg_wm,
            "avg_delta_mid_to_strong": avg_ms,
            "avg_delta_overall": overall,
        }

    return marginals


def compute_pareto_frontier(
    per_config: dict[str, dict],
) -> list[dict]:
    """
    Identify Pareto-optimal configs on (score, -cost) axes.
    A config is Pareto-optimal if no other config has both higher score AND lower cost.
    """
    points = [
        {
            "config": name,
            "score": s["success_rate"],
            "cost": s["estimated_cost_per_task"],
            "model_config": s["model_config"],
        }
        for name, s in per_config.items()
    ]
    pareto: list[dict] = []
    for p in points:
        dominated = False
        for q in points:
            if q is p:
                continue
            if q["score"] >= p["score"] and q["cost"] <= p["cost"]:
                if q["score"] > p["score"] or q["cost"] < p["cost"]:
                    dominated = True
                    break
        if not dominated:
            pareto.append(p)
    pareto.sort(key=lambda x: x["cost"])
    return pareto


def best_per_cost_tier(
    per_config: dict[str, dict],
) -> dict[str, dict]:
    """Return the best-scoring config in each of three cost buckets."""
    items = sorted(per_config.items(), key=lambda kv: kv[1]["estimated_cost_per_task"])
    if not items:
        return {}
    min_cost = items[0][1]["estimated_cost_per_task"]
    max_cost = items[-1][1]["estimated_cost_per_task"]
    span = max_cost - min_cost or 1.0
    low_thresh = min_cost + span / 3
    high_thresh = min_cost + 2 * span / 3

    buckets: dict[str, list] = {"low": [], "mid": [], "high": []}
    for name, s in per_config.items():
        c = s["estimated_cost_per_task"]
        if c <= low_thresh:
            buckets["low"].append((name, s))
        elif c <= high_thresh:
            buckets["mid"].append((name, s))
        else:
            buckets["high"].append((name, s))

    result: dict[str, dict] = {}
    for tier_name, candidates in buckets.items():
        if candidates:
            best_name, best_s = max(candidates, key=lambda x: x[1]["success_rate"])
            result[tier_name] = {"config": best_name, **best_s}
    return result


def generate_latex_table(
    per_config: dict[str, dict],
    pareto: list[dict],
    marginals: dict[str, dict],
    output_path: str,
) -> None:
    """Write a LaTeX table summarising the systematic heterogeneous experiment."""
    pareto_names = {p["config"] for p in pareto}

    lines: list[str] = []
    lines.append(r"% Auto-generated by scripts/run_hetero_systematic.py")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(r"\small")
    lines.append(r"\caption{Systematic Heterogeneous Team Study (27 tier permutations + 3 cross-family configs, 28-task Mini subset, seed 0). ")
    lines.append(r"W=\textit{gemini-3.1-flash-lite}, M=\textit{gemini-3-flash}, S=\textit{gpt-5-mini}. ")
    lines.append(r"$\dagger$ marks Pareto-optimal configs.}")
    lines.append(r"\label{tab:hetero_systematic}")
    lines.append(r"\begin{tabular}{lccccc}")
    lines.append(r"\toprule")
    lines.append(r"Config & Planner & Executor & Verifier & Score & Cost\,(\$) \\")
    lines.append(r"\midrule")
    lines.append(r"\multicolumn{6}{l}{\textit{Tier permutations (27 configs)}} \\")
    lines.append(r"\midrule")

    tier_abbrev = {WEAK: "W", MID: "M", STRONG: "S"}

    def fmt_model(m: str) -> str:
        return tier_abbrev.get(m, m.split("-")[0][:8])

    # Sort permutation configs by score descending
    perm_items = sorted(
        [(n, s) for n, s in per_config.items() if n in PERMUTATION_CONFIGS],
        key=lambda x: x[1]["success_rate"],
        reverse=True,
    )
    for cfg_name, s in perm_items:
        mc = s["model_config"]
        marker = r"$\dagger$" if cfg_name in pareto_names else ""
        lines.append(
            f"  {cfg_name}{marker} & {fmt_model(mc['planner'])} & {fmt_model(mc['executor'])} & "
            f"{fmt_model(mc['verifier'])} & {s['success_rate']:.1%} & {s['estimated_cost_per_task']:.4f} \\\\"
        )

    lines.append(r"\midrule")
    lines.append(r"\multicolumn{6}{l}{\textit{Cross-family configs}} \\")
    lines.append(r"\midrule")

    cross_items = sorted(
        [(n, s) for n, s in per_config.items() if n in CROSS_FAMILY_CONFIGS],
        key=lambda x: x[1]["success_rate"],
        reverse=True,
    )
    for cfg_name, s in cross_items:
        mc = s["model_config"]
        marker = r"$\dagger$" if cfg_name in pareto_names else ""
        lines.append(
            f"  {cfg_name}{marker} & {fmt_model(mc['planner'])} & {fmt_model(mc['executor'])} & "
            f"{fmt_model(mc['verifier'])} & {s['success_rate']:.1%} & {s['estimated_cost_per_task']:.4f} \\\\"
        )

    lines.append(r"\midrule")
    lines.append(r"\multicolumn{6}{l}{\textit{Marginal role contributions (avg $\Delta$ success rate)}} \\")
    lines.append(r"\midrule")
    lines.append(r"Role & \multicolumn{2}{c}{W$\to$M} & \multicolumn{2}{c}{M$\to$S} & Overall \\")
    for role, m in marginals.items():
        wm = f"{m['avg_delta_weak_to_mid']:+.1%}" if m["avg_delta_weak_to_mid"] is not None else "---"
        ms = f"{m['avg_delta_mid_to_strong']:+.1%}" if m["avg_delta_mid_to_strong"] is not None else "---"
        ov = f"{m['avg_delta_overall']:+.1%}" if m["avg_delta_overall"] is not None else "---"
        lines.append(f"  {role.capitalize()} & \\multicolumn{{2}}{{c}}{{{wm}}} & \\multicolumn{{2}}{{c}}{{{ms}}} & {ov} \\\\")

    lines.append(r"\bottomrule")
    lines.append(r"\end{tabular}")
    lines.append(r"\end{table}")

    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"  LaTeX table written to {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(
        description="Run systematic heterogeneous team ablation (27 permutations + 3 cross-family)."
    )
    ap.add_argument(
        "--config",
        default="all",
        choices=list(CONFIG_GROUPS.keys()) + list(ALL_CONFIGS.keys()),
        help="Config group or individual config name (default: all)",
    )
    ap.add_argument(
        "--output",
        default="shared/ablation_results/hetero_systematic.json",
        help="Output JSON path (default: shared/ablation_results/hetero_systematic.json)",
    )
    ap.add_argument(
        "--latex",
        default="shared/paper/table_hetero_systematic.tex",
        help="Output LaTeX table path",
    )
    ap.add_argument(
        "--analysis-output",
        default="shared/ablation_results/hetero_systematic_analysis.json",
        help="Output analysis JSON path",
    )
    ap.add_argument(
        "--tasks-dir",
        default="tasks",
        help="Tasks directory (default: tasks)",
    )
    ap.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Seed to use (default: 0)",
    )
    ap.add_argument(
        "--tasks",
        nargs="*",
        default=None,
        help="Subset of tasks to run (default: all 28 cross-model tasks)",
    )
    args = ap.parse_args()

    # Load .env if present
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env_path = os.path.join(repo_root, ".env")
    if os.path.isfile(env_path):
        with open(env_path) as ef:
            for line in ef:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("=")
                    os.environ.setdefault(k.strip(), v.strip())

    # Resolve configs to run
    if args.config in CONFIG_GROUPS:
        configs_to_run = list(CONFIG_GROUPS[args.config].items())
    elif args.config in ALL_CONFIGS:
        configs_to_run = [(args.config, ALL_CONFIGS[args.config])]
    else:
        ap.error(f"Unknown config '{args.config}'")

    tasks_dir = os.path.abspath(args.tasks_dir)
    task_names = args.tasks if args.tasks else TASKS

    available = set(discover_tasks(tasks_dir))
    missing = [t for t in task_names if t not in available]
    if missing:
        print(f"WARNING: {len(missing)} tasks not found on disk and will be skipped: {missing}")
    task_names = [t for t in task_names if t in available]

    if not task_names:
        print("ERROR: No valid tasks to run.", file=sys.stderr)
        sys.exit(1)

    output_dir = os.path.dirname(os.path.abspath(args.output))
    runs_base = os.path.join(output_dir, "hetero_systematic_runs")

    print("TeamBench Systematic Heterogeneous Team Ablation")
    print(f"Configs: {len(configs_to_run)} ({args.config})")
    print(f"Tasks:   {len(task_names)}")
    print(f"Seed:    {args.seed}")
    print(f"Total runs: {len(configs_to_run) * len(task_names)}")
    print("=" * 60)

    all_runs: list[dict] = []

    for config_name, model_config in configs_to_run:
        print(f"\n--- Config: {config_name} ---")
        for role, mdl in model_config.items():
            print(f"  {role}: {mdl}")

        records = run_hetero_config(
            config_name=config_name,
            model_config=model_config,
            tasks=task_names,
            tasks_dir=tasks_dir,
            seed=args.seed,
            runs_base=runs_base,
        )
        all_runs.extend(records)

    # Compute summaries and analysis
    all_configs_dict = dict(configs_to_run)
    per_config = compute_per_config_summary(all_runs, all_configs_dict)
    marginals = compute_marginal_contributions(per_config)
    pareto = compute_pareto_frontier(per_config)
    best_tiers = best_per_cost_tier(per_config)

    # Determine which role explains the most variance (highest overall marginal)
    if marginals:
        top_role = max(
            marginals.items(),
            key=lambda kv: abs(kv[1]["avg_delta_overall"] or 0.0),
        )
        top_role_name = top_role[0]
        top_role_delta = top_role[1]["avg_delta_overall"]
    else:
        top_role_name = None
        top_role_delta = None

    analysis = {
        "experiment": "hetero_systematic",
        "seed": args.seed,
        "tasks": task_names,
        "n_permutation_configs": len(PERMUTATION_CONFIGS),
        "n_cross_family_configs": len(CROSS_FAMILY_CONFIGS),
        "completed": datetime.now(timezone.utc).isoformat(),
        "per_config": per_config,
        "marginal_contributions": marginals,
        "top_role_by_marginal": {
            "role": top_role_name,
            "avg_delta_overall": top_role_delta,
        },
        "pareto_frontier": pareto,
        "best_per_cost_tier": best_tiers,
        "runs": all_runs,
    }

    # Write main output JSON
    os.makedirs(output_dir, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2)

    # Write analysis JSON (same content, separate path for clarity)
    analysis_no_runs = {k: v for k, v in analysis.items() if k != "runs"}
    os.makedirs(os.path.dirname(os.path.abspath(args.analysis_output)), exist_ok=True)
    with open(args.analysis_output, "w", encoding="utf-8") as f:
        json.dump(analysis_no_runs, f, indent=2)

    # Write LaTeX table
    generate_latex_table(per_config, pareto, marginals, args.latex)

    # Print summary
    print(f"\n{'=' * 60}")
    print("HETERO SYSTEMATIC COMPLETE")
    print(f"{'=' * 60}")
    print(f"  {'Config':<22} {'Score':>6}  {'AvgPartial':>10}  {'Cost/task':>10}  {'Pareto':>6}")
    pareto_names = {p["config"] for p in pareto}
    sorted_summary = sorted(per_config.items(), key=lambda kv: kv[1]["success_rate"], reverse=True)
    for cfg_name, s in sorted_summary[:15]:
        pareto_mark = "*" if cfg_name in pareto_names else ""
        print(
            f"  {cfg_name:<22} {s['success_rate']:>6.1%}  {s['avg_partial']:>10.4f}  "
            f"${s['estimated_cost_per_task']:>9.4f}  {pareto_mark:>6}"
        )
    if len(sorted_summary) > 15:
        print(f"  ... ({len(sorted_summary) - 15} more configs)")

    print(f"\n  Marginal Contributions (avg delta success rate):")
    for role, m in marginals.items():
        ov = f"{m['avg_delta_overall']:+.1%}" if m["avg_delta_overall"] is not None else "---"
        print(f"    {role:<12}: overall {ov}")
    if top_role_name and top_role_delta is not None:
        print(f"\n  Role with highest marginal impact: {top_role_name} ({top_role_delta:+.1%})")

    print(f"\n  Pareto-optimal configs ({len(pareto)}):")
    for p in pareto:
        print(f"    {p['config']:<22} score={p['score']:.1%}  cost=${p['cost']:.4f}")

    print(f"\n  Best per cost tier:")
    for tier_name, b in best_tiers.items():
        print(f"    {tier_name:<6}: {b['config']} (score={b['success_rate']:.1%}, cost=${b['estimated_cost_per_task']:.4f})")

    print(f"\n  Full results:    {args.output}")
    print(f"  Analysis JSON:   {args.analysis_output}")
    print(f"  LaTeX table:     {args.latex}")


if __name__ == "__main__":
    main()
