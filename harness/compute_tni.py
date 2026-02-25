"""
TeamBench — Teamwork Necessity Index (TNI) computation.

TNI = (S_team - S_restricted) / max(epsilon, S_full - S_restricted)

Multiple input modes:
  A. From ablation results (all 5 conditions in one file)
  B. From individual condition result files
  C. From direct success rates

Usage:
    # From ablation results
    python -m harness.compute_tni --ablation shared/ablation_results.json

    # From individual result files
    python -m harness.compute_tni \
        --oracle shared/oracle_results.json \
        --restricted shared/restricted_results.json \
        --team shared/team_results.json \
        --output shared/tni_report.json

    # From direct rates (quick what-if analysis)
    python -m harness.compute_tni \
        --oracle-rate 0.85 --restricted-rate 0.20 --team-rate 0.72
"""
from __future__ import annotations
import argparse
import json
import os
from collections import defaultdict


def load_results(path: str) -> dict:
    with open(path, "r") as f:
        return json.load(f)


def success_rate(results: dict) -> float:
    """Extract overall success rate from batch results."""
    if "success_rate" in results:
        return results["success_rate"]
    tasks = results.get("results", [])
    if not tasks:
        return 0.0
    passed = sum(1 for t in tasks if t.get("pass", False))
    return passed / len(tasks)


def per_task_rates(results: dict) -> dict[str, float]:
    """Get per-task success rate (1.0 or 0.0 for single runs)."""
    rates = {}
    for t in results.get("results", []):
        tid = t.get("task_id", "")
        rates[tid] = 1.0 if t.get("pass", False) else 0.0
    return rates


def compute_tni(
    s_full: float,
    s_restricted: float,
    s_team: float,
    epsilon: float = 0.01,
) -> dict:
    """Compute TNI and related metrics."""
    necessity_gap = s_full - s_restricted
    collaboration_gain = s_team - s_restricted

    tni = collaboration_gain / max(epsilon, necessity_gap)

    return {
        "s_full": round(s_full, 4),
        "s_restricted": round(s_restricted, 4),
        "s_team": round(s_team, 4),
        "necessity_gap": round(necessity_gap, 4),
        "collaboration_gain": round(collaboration_gain, 4),
        "tni": round(tni, 4),
        "interpretation": interpret_tni(tni),
    }


def interpret_tni(tni: float) -> str:
    if tni >= 0.9:
        return "Teamwork fully recovers the performance gap."
    elif tni >= 0.5:
        return "Teamwork substantially recovers the performance gap."
    elif tni >= 0.1:
        return "Teamwork provides modest improvement."
    elif tni >= 0.0:
        return "Teamwork provides minimal improvement."
    else:
        return "Teamwork is harmful (negative collaboration gain)."


def compute_per_task_tni(
    oracle_results: dict,
    restricted_results: dict,
    team_results: dict,
) -> list[dict]:
    """Compute TNI per task for detailed analysis."""
    oracle_rates = per_task_rates(oracle_results)
    restricted_rates = per_task_rates(restricted_results)
    team_rates = per_task_rates(team_results)

    all_tasks = sorted(set(oracle_rates) | set(restricted_rates) | set(team_rates))
    per_task = []

    for tid in all_tasks:
        sf = oracle_rates.get(tid, 0.0)
        sr = restricted_rates.get(tid, 0.0)
        st = team_rates.get(tid, 0.0)
        tni_val = compute_tni(sf, sr, st)
        per_task.append({"task_id": tid, **tni_val})

    return per_task


def compute_per_domain_tni(
    oracle_results: dict,
    restricted_results: dict,
    team_results: dict,
) -> dict[str, dict]:
    """Compute TNI per domain."""
    domains = defaultdict(lambda: {"oracle": [], "restricted": [], "team": []})

    for r in oracle_results.get("results", []):
        domain = r.get("task_id", "").split("_")[0]
        domains[domain]["oracle"].append(1.0 if r.get("pass") else 0.0)
    for r in restricted_results.get("results", []):
        domain = r.get("task_id", "").split("_")[0]
        domains[domain]["restricted"].append(1.0 if r.get("pass") else 0.0)
    for r in team_results.get("results", []):
        domain = r.get("task_id", "").split("_")[0]
        domains[domain]["team"].append(1.0 if r.get("pass") else 0.0)

    result = {}
    for domain, data in sorted(domains.items()):
        sf = sum(data["oracle"]) / max(1, len(data["oracle"]))
        sr = sum(data["restricted"]) / max(1, len(data["restricted"]))
        st = sum(data["team"]) / max(1, len(data["team"]))
        result[domain] = compute_tni(sf, sr, st)

    return result


def _print_report(overall: dict, per_domain: dict | None = None) -> None:
    """Pretty-print TNI report to stdout."""
    print("=" * 60)
    print("  TEAMWORK NECESSITY INDEX REPORT")
    print("=" * 60)
    print(f"  S_full (oracle):      {overall['s_full']:.1%}")
    print(f"  S_restricted:         {overall['s_restricted']:.1%}")
    print(f"  S_team:               {overall['s_team']:.1%}")
    print(f"  Necessity Gap:        {overall['necessity_gap']:.1%}")
    print(f"  Collaboration Gain:   {overall['collaboration_gain']:.1%}")
    print(f"  TNI:                  {overall['tni']:.4f}")
    print(f"  Interpretation:       {overall['interpretation']}")

    if per_domain:
        print()
        print("  Per-domain TNI:")
        for domain, dtn in per_domain.items():
            print(f"    {domain:20s}  TNI={dtn['tni']:.4f}  ({dtn['interpretation']})")


def main() -> None:
    ap = argparse.ArgumentParser(description="Compute Teamwork Necessity Index")

    # Mode A: ablation file
    ap.add_argument("--ablation", help="Path to ablation_results.json (all 5 conditions)")

    # Mode B: individual result files
    ap.add_argument("--oracle", help="Path to oracle (full-access) batch results")
    ap.add_argument("--restricted", help="Path to restricted (single-agent) batch results")
    ap.add_argument("--team", help="Path to team (multi-agent) batch results")

    # Mode C: direct rates
    ap.add_argument("--oracle-rate", type=float, help="Oracle success rate (0-1)")
    ap.add_argument("--restricted-rate", type=float, help="Restricted success rate (0-1)")
    ap.add_argument("--team-rate", type=float, help="Team success rate (0-1)")

    ap.add_argument("--output", default="shared/tni_report.json", help="Output path")
    args = ap.parse_args()

    # Mode A: ablation file
    if args.ablation:
        ablation = load_results(args.ablation)
        metrics = ablation.get("metrics", {})
        overall = {
            "s_full": metrics.get("s_oracle", metrics.get("s_full", 0)),
            "s_restricted": metrics.get("s_restricted", 0),
            "s_team": metrics.get("s_full", 0),
            "necessity_gap": metrics.get("necessity_gap", 0),
            "collaboration_gain": metrics.get("s_full", 0) - metrics.get("s_restricted", 0),
            "tni": metrics.get("tni", 0),
            "interpretation": metrics.get("interpretation", {}).get("tni", ""),
        }
        report = {"overall": overall, "source": args.ablation, "metrics": metrics}
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        _print_report(overall)
        print(f"\n  Report saved to: {args.output}")
        return

    # Mode C: direct rates
    if args.oracle_rate is not None and args.restricted_rate is not None and args.team_rate is not None:
        overall = compute_tni(args.oracle_rate, args.restricted_rate, args.team_rate)
        report = {"overall": overall}
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        _print_report(overall)
        print(f"\n  Report saved to: {args.output}")
        return

    # Mode B: individual result files (original behavior)
    if not (args.oracle and args.restricted and args.team):
        ap.print_help()
        print("\nProvide --ablation, --oracle/--restricted/--team, or --*-rate flags.")
        return

    oracle = load_results(args.oracle)
    restricted = load_results(args.restricted)
    team = load_results(args.team)

    sf = success_rate(oracle)
    sr = success_rate(restricted)
    st = success_rate(team)

    overall = compute_tni(sf, sr, st)
    per_task = compute_per_task_tni(oracle, restricted, team)
    per_domain = compute_per_domain_tni(oracle, restricted, team)

    report = {
        "overall": overall,
        "per_domain": per_domain,
        "per_task": per_task,
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)

    _print_report(overall, per_domain)
    print(f"\n  Report saved to: {args.output}")


if __name__ == "__main__":
    main()
