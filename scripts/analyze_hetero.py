#!/usr/bin/env python3
"""Analyze heterogeneous team experiment results.

Reads hetero_systematic.json (or hetero_seed0.json) and computes:
  - Marginal contribution of each role (Planner / Executor / Verifier)
  - One-way ANOVA: which role explains the most variance in success rate?
  - Pareto frontier (score vs estimated cost)
  - LaTeX table summarising the findings

Usage:
    python scripts/analyze_hetero.py --input shared/ablation_results/hetero_systematic.json
    python scripts/analyze_hetero.py --input shared/ablation_results/hetero_seed0.json \\
        --latex shared/paper/table_hetero_analysis.tex
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------------------------------
# Model tier / cost constants (mirrors run_hetero_systematic.py)
# ---------------------------------------------------------------------------
WEAK = "gemini-3.1-flash-lite-preview"
MID = "gemini-3-flash-preview"
STRONG = "gpt-5-mini"

TIERS = {"weak": WEAK, "mid": MID, "strong": STRONG}
TIER_MAP = {v: k for k, v in TIERS.items()}  # model -> tier name

MODEL_COST: dict[str, float] = {
    WEAK: 0.0001,
    MID: 0.0005,
    STRONG: 0.002,
    "gpt-5-nano": 0.0001,
    "claude-sonnet-4-6-20250514": 0.003,
}


def _config_cost(model_config: dict[str, str]) -> float:
    return sum(MODEL_COST.get(v, 0.001) for v in model_config.values())


# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------

def _mean(xs: list[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0


def _variance(xs: list[float]) -> float:
    if len(xs) < 2:
        return 0.0
    m = _mean(xs)
    return sum((x - m) ** 2 for x in xs) / (len(xs) - 1)


def one_way_anova(groups: dict[str, list[float]]) -> dict[str, Any]:
    """
    Compute one-way ANOVA: F-statistic and p-value (approximated via F-distribution
    CDF using a regularised incomplete beta function).

    Returns {F, p_value, df_between, df_within, ss_between, ss_within, eta_squared}.
    """
    all_vals: list[float] = []
    for v in groups.values():
        all_vals.extend(v)
    if not all_vals:
        return {}

    grand_mean = _mean(all_vals)
    k = len(groups)
    n_total = len(all_vals)

    ss_between = sum(
        len(v) * (_mean(v) - grand_mean) ** 2 for v in groups.values() if v
    )
    ss_within = sum(
        sum((x - _mean(v)) ** 2 for x in v) for v in groups.values() if v
    )
    df_between = k - 1
    df_within = n_total - k

    if df_between <= 0 or df_within <= 0 or ss_within == 0:
        return {
            "F": None, "p_value": None,
            "df_between": df_between, "df_within": df_within,
            "ss_between": ss_between, "ss_within": ss_within,
            "eta_squared": None,
        }

    ms_between = ss_between / df_between
    ms_within = ss_within / df_within
    F = ms_between / ms_within if ms_within > 0 else None
    eta_sq = ss_between / (ss_between + ss_within) if (ss_between + ss_within) > 0 else None

    # Approximate p-value via regularised incomplete beta for F distribution
    p_value: float | None = None
    if F is not None:
        try:
            p_value = _f_pvalue(F, df_between, df_within)
        except Exception:
            p_value = None

    return {
        "F": round(F, 4) if F is not None else None,
        "p_value": round(p_value, 6) if p_value is not None else None,
        "df_between": df_between,
        "df_within": df_within,
        "ss_between": round(ss_between, 6),
        "ss_within": round(ss_within, 6),
        "eta_squared": round(eta_sq, 4) if eta_sq is not None else None,
    }


def _regularised_incomplete_beta(x: float, a: float, b: float, max_iter: int = 200) -> float:
    """Approximate I_x(a, b) using the continued fraction method (Lentz)."""
    if x < 0 or x > 1:
        raise ValueError(f"x={x} out of [0,1]")
    if x == 0:
        return 0.0
    if x == 1:
        return 1.0
    # Use the symmetry relation when x > (a+1)/(a+b+2)
    if x > (a + 1) / (a + b + 2):
        return 1.0 - _regularised_incomplete_beta(1 - x, b, a, max_iter)

    lbeta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - lbeta) / a

    # Continued fraction via modified Lentz
    tiny = 1e-30
    f = tiny
    C = f
    D = 0.0
    for m in range(0, max_iter):
        for n_iter in range(2):
            if n_iter == 0:
                if m == 0:
                    d = 1.0
                else:
                    d = -(a + m - 1) * (a + b + m - 1) * x / ((a + 2 * m - 1) * (a + 2 * m))
            else:
                d = m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m))

            D = 1 + d * D
            if abs(D) < tiny:
                D = tiny
            C = 1 + d / C
            if abs(C) < tiny:
                C = tiny
            D = 1 / D
            delta = C * D
            f *= delta
            if abs(delta - 1) < 1e-10:
                return front * f
    return front * f


def _f_pvalue(F: float, df1: int, df2: int) -> float:
    """P(X >= F) for F ~ F(df1, df2)."""
    x = df1 * F / (df1 * F + df2)
    return 1.0 - _regularised_incomplete_beta(x, df1 / 2, df2 / 2)


# ---------------------------------------------------------------------------
# Core analysis
# ---------------------------------------------------------------------------

def load_results(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def extract_per_config(data: dict) -> dict[str, dict]:
    """Return per_config summary, building it from runs if absent."""
    if "per_config" in data:
        return data["per_config"]

    # Build from raw runs
    runs: list[dict] = data.get("runs", [])
    configs: dict[str, dict] = data.get("configs", {})
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


def compute_marginal_contributions(per_config: dict[str, dict]) -> dict[str, dict]:
    """Compute per-role marginal contribution using all tier permutation configs."""
    # Identify permutation configs (3-letter names like PwEmVs)
    # We decode from model_config directly
    tier_order = ["weak", "mid", "strong"]

    def decode_tiers(mc: dict[str, str]) -> tuple[str, str, str] | None:
        p = TIER_MAP.get(mc.get("planner", ""))
        e = TIER_MAP.get(mc.get("executor", ""))
        v = TIER_MAP.get(mc.get("verifier", ""))
        return (p, e, v) if p and e and v else None

    tier_to_rate: dict[tuple[str, str, str], float] = {}
    for cfg_name, s in per_config.items():
        decoded = decode_tiers(s.get("model_config", {}))
        if decoded:
            tier_to_rate[decoded] = s["success_rate"]

    if not tier_to_rate:
        return {}

    role_indices = {"planner": 0, "executor": 1, "verifier": 2}
    marginals: dict[str, dict] = {}

    for role, idx in role_indices.items():
        deltas_wm: list[float] = []
        deltas_ms: list[float] = []
        for t1 in tier_order:
            for t2 in tier_order:
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

        all_d = deltas_wm + deltas_ms
        marginals[role] = {
            "avg_delta_weak_to_mid": round(_mean(deltas_wm), 4) if deltas_wm else None,
            "avg_delta_mid_to_strong": round(_mean(deltas_ms), 4) if deltas_ms else None,
            "avg_delta_overall": round(_mean(all_d), 4) if all_d else None,
            "variance": round(_variance(all_d), 6) if len(all_d) >= 2 else None,
            "n_pairs": len(all_d),
        }

    return marginals


def compute_anova_by_role(per_config: dict[str, dict]) -> dict[str, Any]:
    """
    For each role, group configs by the tier assigned to that role and
    run a one-way ANOVA to see how much variance in success_rate each
    role assignment explains.
    """
    results: dict[str, Any] = {}
    roles = ["planner", "executor", "verifier"]

    for role in roles:
        groups: dict[str, list[float]] = {"weak": [], "mid": [], "strong": []}
        for s in per_config.values():
            mc = s.get("model_config", {})
            tier = TIER_MAP.get(mc.get(role, ""))
            if tier in groups:
                groups[tier].append(s["success_rate"])

        if any(groups.values()):
            anova = one_way_anova(groups)
            anova["group_means"] = {t: round(_mean(v), 4) for t, v in groups.items() if v}
            anova["group_sizes"] = {t: len(v) for t, v in groups.items() if v}
            results[role] = anova

    return results


def compute_pareto_frontier(per_config: dict[str, dict]) -> list[dict]:
    """Pareto-optimal on (score, -cost)."""
    points = [
        {
            "config": name,
            "score": s["success_rate"],
            "cost": s.get("estimated_cost_per_task", _config_cost(s.get("model_config", {}))),
            "model_config": s.get("model_config", {}),
        }
        for name, s in per_config.items()
    ]
    pareto: list[dict] = []
    for p in points:
        dominated = any(
            q["score"] >= p["score"] and q["cost"] <= p["cost"]
            and (q["score"] > p["score"] or q["cost"] < p["cost"])
            for q in points if q is not p
        )
        if not dominated:
            pareto.append(p)
    pareto.sort(key=lambda x: x["cost"])
    return pareto


def best_per_cost_tier(per_config: dict[str, dict]) -> dict[str, dict]:
    """Best config in three equal-width cost buckets."""
    items = sorted(per_config.items(), key=lambda kv: kv[1].get("estimated_cost_per_task", 0))
    if not items:
        return {}
    costs = [s.get("estimated_cost_per_task", 0) for _, s in items]
    lo, hi = min(costs), max(costs)
    span = hi - lo or 1.0
    low_t, high_t = lo + span / 3, lo + 2 * span / 3

    buckets: dict[str, list] = {"low": [], "mid": [], "high": []}
    for name, s in per_config.items():
        c = s.get("estimated_cost_per_task", 0)
        bucket = "low" if c <= low_t else ("mid" if c <= high_t else "high")
        buckets[bucket].append((name, s))

    result: dict[str, dict] = {}
    for tier_name, candidates in buckets.items():
        if candidates:
            best_name, best_s = max(candidates, key=lambda x: x[1]["success_rate"])
            result[tier_name] = {
                "config": best_name,
                "success_rate": best_s["success_rate"],
                "estimated_cost_per_task": best_s.get("estimated_cost_per_task", 0),
                "model_config": best_s.get("model_config", {}),
            }
    return result


# ---------------------------------------------------------------------------
# Pareto data for plotting (score vs cost, annotated)
# ---------------------------------------------------------------------------

def pareto_plot_data(per_config: dict[str, dict], pareto: list[dict]) -> list[dict]:
    """Return a list of dicts suitable for scatter/line plotting."""
    pareto_names = {p["config"] for p in pareto}
    rows = []
    for name, s in per_config.items():
        rows.append({
            "config": name,
            "score": s["success_rate"],
            "cost": s.get("estimated_cost_per_task", _config_cost(s.get("model_config", {}))),
            "is_pareto": name in pareto_names,
            "planner_tier": TIER_MAP.get(s.get("model_config", {}).get("planner", ""), "unknown"),
            "executor_tier": TIER_MAP.get(s.get("model_config", {}).get("executor", ""), "unknown"),
            "verifier_tier": TIER_MAP.get(s.get("model_config", {}).get("verifier", ""), "unknown"),
        })
    rows.sort(key=lambda x: x["cost"])
    return rows


# ---------------------------------------------------------------------------
# LaTeX output
# ---------------------------------------------------------------------------

def generate_latex_table(
    per_config: dict[str, dict],
    marginals: dict[str, dict],
    anova: dict[str, Any],
    pareto: list[dict],
    output_path: str,
) -> None:
    pareto_names = {p["config"] for p in pareto}
    tier_abbrev = {WEAK: "W", MID: "M", STRONG: "S"}

    def fmt_model(m: str) -> str:
        return tier_abbrev.get(m, m.split("-")[0][:8])

    lines: list[str] = []
    lines.append(r"% Auto-generated by scripts/analyze_hetero.py")
    lines.append(r"\begin{table}[t]")
    lines.append(r"\centering")
    lines.append(r"\small")
    lines.append(r"\caption{Heterogeneous team analysis: marginal role contributions and ANOVA. "
                 r"$\dagger$ = Pareto-optimal (score vs cost). "
                 r"W=\textit{gemini-3.1-flash-lite}, M=\textit{gemini-3-flash}, S=\textit{gpt-5-mini}.}")
    lines.append(r"\label{tab:hetero_analysis}")

    # Part 1: top configs
    lines.append(r"\begin{tabular}{lccccr}")
    lines.append(r"\toprule")
    lines.append(r"Config & Planner & Executor & Verifier & Score & Cost \\")
    lines.append(r"\midrule")
    top_configs = sorted(per_config.items(), key=lambda kv: kv[1]["success_rate"], reverse=True)[:10]
    for cfg_name, s in top_configs:
        mc = s.get("model_config", {})
        marker = r"$\dagger$" if cfg_name in pareto_names else r"\phantom{$\dagger$}"
        cost = s.get("estimated_cost_per_task", _config_cost(mc))
        lines.append(
            f"  {cfg_name}{marker} & {fmt_model(mc.get('planner','?'))} & "
            f"{fmt_model(mc.get('executor','?'))} & {fmt_model(mc.get('verifier','?'))} & "
            f"{s['success_rate']:.1%} & \\${cost:.4f} \\\\"
        )
    lines.append(r"\midrule")

    # Part 2: marginal contributions
    lines.append(r"\multicolumn{6}{l}{\textit{Marginal contribution (avg $\Delta$ success rate across all contexts)}} \\")
    lines.append(r"\midrule")
    lines.append(r"Role & \multicolumn{2}{c}{W$\to$M} & \multicolumn{2}{c}{M$\to$S} & Overall \\")
    for role, m in marginals.items():
        wm = f"{m['avg_delta_weak_to_mid']:+.1%}" if m.get("avg_delta_weak_to_mid") is not None else "---"
        ms = f"{m['avg_delta_mid_to_strong']:+.1%}" if m.get("avg_delta_mid_to_strong") is not None else "---"
        ov = f"{m['avg_delta_overall']:+.1%}" if m.get("avg_delta_overall") is not None else "---"
        lines.append(
            f"  {role.capitalize()} & \\multicolumn{{2}}{{c}}{{{wm}}} & "
            f"\\multicolumn{{2}}{{c}}{{{ms}}} & {ov} \\\\"
        )
    lines.append(r"\midrule")

    # Part 3: ANOVA
    lines.append(r"\multicolumn{6}{l}{\textit{One-way ANOVA: role-tier explains variance in success rate}} \\")
    lines.append(r"\midrule")
    lines.append(r"Role & $F$ & $p$ & $\eta^2$ & \multicolumn{2}{l}{Group means (W/M/S)} \\")
    for role, av in anova.items():
        F_str = f"{av['F']:.2f}" if av.get("F") is not None else "---"
        p_str = f"{av['p_value']:.4f}" if av.get("p_value") is not None else "---"
        eta_str = f"{av['eta_squared']:.3f}" if av.get("eta_squared") is not None else "---"
        gm = av.get("group_means", {})
        means_str = "/".join(
            f"{gm.get(t, 0):.1%}" for t in ["weak", "mid", "strong"] if t in gm
        )
        lines.append(
            f"  {role.capitalize()} & {F_str} & {p_str} & {eta_str} & "
            f"\\multicolumn{{2}}{{l}}{{{means_str}}} \\\\"
        )

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
        description="Analyze heterogeneous team experiment results."
    )
    ap.add_argument(
        "--input",
        default="shared/ablation_results/hetero_systematic.json",
        help="Input JSON from run_hetero_systematic.py or run_hetero_ablation.py",
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
        "--pareto-data",
        default=None,
        help="Optional output path for Pareto plot data (JSON)",
    )
    args = ap.parse_args()

    input_path = os.path.abspath(args.input)
    if not os.path.isfile(input_path):
        print(f"ERROR: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    print(f"Loading results from {input_path} ...", flush=True)
    data = load_results(input_path)
    per_config = extract_per_config(data)
    print(f"  {len(per_config)} configs found.")

    print("Computing marginal contributions ...", flush=True)
    marginals = compute_marginal_contributions(per_config)

    print("Running one-way ANOVA per role ...", flush=True)
    anova = compute_anova_by_role(per_config)

    print("Computing Pareto frontier ...", flush=True)
    pareto = compute_pareto_frontier(per_config)

    print("Computing best per cost tier ...", flush=True)
    best_tiers = best_per_cost_tier(per_config)

    # Identify top role by marginal impact
    if marginals:
        top_role = max(
            marginals.items(),
            key=lambda kv: abs(kv[1].get("avg_delta_overall") or 0.0),
        )
        top_role_name = top_role[0]
        top_role_delta = top_role[1].get("avg_delta_overall")
    else:
        top_role_name = None
        top_role_delta = None

    # Identify top role by ANOVA eta_squared
    if anova:
        top_anova_role = max(
            anova.items(),
            key=lambda kv: kv[1].get("eta_squared") or 0.0,
        )
        top_anova_name = top_anova_role[0]
        top_anova_eta = top_anova_role[1].get("eta_squared")
    else:
        top_anova_name = None
        top_anova_eta = None

    # Write analysis JSON
    analysis = {
        "source": input_path,
        "n_configs": len(per_config),
        "marginal_contributions": marginals,
        "top_role_by_marginal": {"role": top_role_name, "avg_delta_overall": top_role_delta},
        "anova_by_role": anova,
        "top_role_by_anova_eta_squared": {"role": top_anova_name, "eta_squared": top_anova_eta},
        "pareto_frontier": pareto,
        "best_per_cost_tier": best_tiers,
        "pareto_plot_data": pareto_plot_data(per_config, pareto),
    }

    os.makedirs(os.path.dirname(os.path.abspath(args.analysis_output)), exist_ok=True)
    with open(args.analysis_output, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2)
    print(f"  Analysis JSON written to {args.analysis_output}")

    if args.pareto_data:
        pdata = pareto_plot_data(per_config, pareto)
        os.makedirs(os.path.dirname(os.path.abspath(args.pareto_data)), exist_ok=True)
        with open(args.pareto_data, "w", encoding="utf-8") as f:
            json.dump(pdata, f, indent=2)
        print(f"  Pareto plot data written to {args.pareto_data}")

    print("Generating LaTeX table ...", flush=True)
    generate_latex_table(per_config, marginals, anova, pareto, args.latex)

    # Print summary
    print(f"\n{'=' * 60}")
    print("HETERO ANALYSIS SUMMARY")
    print(f"{'=' * 60}")

    print("\n  Marginal Contributions (avg delta success rate):")
    for role, m in marginals.items():
        wm = f"{m['avg_delta_weak_to_mid']:+.1%}" if m.get("avg_delta_weak_to_mid") is not None else "---"
        ms = f"{m['avg_delta_mid_to_strong']:+.1%}" if m.get("avg_delta_mid_to_strong") is not None else "---"
        ov = f"{m['avg_delta_overall']:+.1%}" if m.get("avg_delta_overall") is not None else "---"
        print(f"    {role:<12}: W->M {wm}, M->S {ms}, overall {ov}")
    if top_role_name:
        print(f"\n  -> Role with highest marginal impact: {top_role_name} ({top_role_delta:+.1%})")

    print("\n  One-way ANOVA (role-tier explains variance):")
    for role, av in anova.items():
        F_str = f"F={av['F']:.2f}" if av.get("F") is not None else "F=---"
        p_str = f"p={av['p_value']:.4f}" if av.get("p_value") is not None else "p=---"
        eta_str = f"eta2={av['eta_squared']:.3f}" if av.get("eta_squared") is not None else "eta2=---"
        print(f"    {role:<12}: {F_str}, {p_str}, {eta_str}")
    if top_anova_name:
        print(f"\n  -> Role explaining most variance (ANOVA eta^2): {top_anova_name} (eta2={top_anova_eta:.3f})")

    print(f"\n  Pareto-optimal configs ({len(pareto)}):")
    for p in pareto:
        print(f"    {p['config']:<22} score={p['score']:.1%}  cost=${p['cost']:.4f}")

    print("\n  Best per cost tier:")
    for tier_name, b in best_tiers.items():
        print(f"    {tier_name:<6}: {b['config']} (score={b['success_rate']:.1%}, cost=${b['estimated_cost_per_task']:.4f})")

    print(f"\n  Analysis JSON: {args.analysis_output}")
    print(f"  LaTeX table:   {args.latex}")


if __name__ == "__main__":
    main()
