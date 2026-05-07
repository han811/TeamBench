"""
TeamBench paper figure generation using matplotlib.

Produces publication-ready PDF/PNG figures from ablation data.

Usage:
    python -m harness.plot_results \
        --ablation shared/ablation_5task.json shared/ablation_10task.json \
        --output-dir shared/paper/figures/
"""
from __future__ import annotations

import argparse
import json
import math
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from harness.paper_tables import (
    merge_ablation_files,
    runs_to_task_metrics,
    _task_category,
)
from harness.compute_tni import TaskMetrics


# Paper-quality defaults
plt.rcParams.update({
    "font.size": 10,
    "font.family": "serif",
    "axes.labelsize": 11,
    "axes.titlesize": 12,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "legend.fontsize": 9,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.1,
})

# Google-style blue palette
CONDITION_COLORS = {
    "oracle": "#1565C0",
    "restricted": "#90CAF9",
    "full": "#0D47A1",
    "no_plan": "#42A5F5",
    "no_verify": "#1E88E5",
}

CONDITION_LABELS = {
    "oracle": "Oracle",
    "restricted": "Restricted",
    "full": "Full Team",
    "no_plan": "No Planner",
    "no_verify": "No Verifier",
}


def plot_condition_comparison(
    metrics: list[TaskMetrics],
    output_dir: str,
) -> None:
    """Figure 2: Two-panel figure."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4), gridspec_kw={"width_ratios": [1, 1.2]})

    classifications = defaultdict(int)
    for m in metrics:
        if m.team_partial > m.oracle_partial + 0.05:
            tni_val = getattr(m, "tni", None)
            if tni_val is not None and not math.isnan(tni_val) and tni_val >= 0.5:
                classifications["HIGH-TNI"] += 1
            else:
                classifications["TEAM-HELPS"] += 1
        elif m.team_partial < m.oracle_partial - 0.05:
            classifications["TEAM-HURTS"] += 1
        else:
            classifications["NEUTRAL"] += 1

    cats = ["HIGH-TNI", "TEAM-HELPS", "NEUTRAL", "TEAM-HURTS"]
    cat_colors = ["#0D47A1", "#1976D2", "#B0BEC5", "#90CAF9"]
    counts = [classifications.get(c, 0) for c in cats]
    total = sum(counts)

    bars = ax1.barh(range(len(cats)), counts, color=cat_colors, alpha=0.85,
                    edgecolor="white", height=0.6)
    ax1.set_yticks(range(len(cats)))
    ax1.set_yticklabels(cats, fontsize=10, fontweight="bold")
    ax1.set_xlabel("Number of Tasks", fontsize=10)
    ax1.invert_yaxis()
    for bar, count in zip(bars, counts):
        pct = count / total * 100
        ax1.text(bar.get_width() + 1, bar.get_y() + bar.get_height() / 2,
                 f"{count} ({pct:.0f}%)", va="center", fontsize=9)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    ax1.grid(axis="x", alpha=0.2)
    ax1.text(0.02, 0.98, "(a)", transform=ax1.transAxes, fontsize=11,
             fontweight="bold", va="top")

    conds = ["oracle", "restricted", "full", "no_plan", "no_verify"]
    cond_avgs = {}
    for cond in conds:
        vals = []
        for m in metrics:
            if cond == "oracle":
                vals.append(m.oracle_partial)
            elif cond == "restricted":
                vals.append(m.restricted_partial)
            elif cond == "full":
                vals.append(m.team_partial)
            elif cond == "no_plan":
                v = m.no_plan_partial
                if not math.isnan(v):
                    vals.append(v)
            elif cond == "no_verify":
                v = m.no_verify_partial
                if not math.isnan(v):
                    vals.append(v)
        cond_avgs[cond] = sum(vals) / len(vals) if vals else 0

    x_pos = np.arange(len(conds))
    colors = [CONDITION_COLORS[c] for c in conds]
    labels = [CONDITION_LABELS[c] for c in conds]
    values = [cond_avgs[c] for c in conds]

    bars2 = ax2.bar(x_pos, values, color=colors, alpha=0.85, edgecolor="white", width=0.6)
    ax2.set_xticks(x_pos)
    ax2.set_xticklabels(labels, rotation=20, ha="right", fontsize=9)
    ax2.set_ylabel("Avg. Partial Score", fontsize=10)
    ax2.set_ylim(0, 0.75)
    ax2.grid(axis="y", alpha=0.2)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.text(0.02, 0.98, "(b)", transform=ax2.transAxes, fontsize=11,
             fontweight="bold", va="top")
    for bar, val in zip(bars2, values):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                 f"{val:.3f}", ha="center", va="bottom", fontsize=9, fontweight="bold")
    best_idx = values.index(max(values))
    bars2[best_idx].set_edgecolor("black")
    bars2[best_idx].set_linewidth(2)

    plt.tight_layout(w_pad=3)
    fig.savefig(os.path.join(output_dir, "fig2_conditions.pdf"))
    plt.close(fig)
    print(f"  {output_dir}/fig2_conditions.pdf")


def plot_category_uplift(
    metrics: list[TaskMetrics],
    output_dir: str,
) -> None:
    """Figure 3: Horizontal bar chart of per-category team uplift."""
    cat_data: dict[str, list[float]] = defaultdict(list)
    for m in metrics:
        cat = _task_category(m.task_id)
        cat_data[cat].append(m.team_uplift)

    cats = sorted(cat_data, key=lambda c: sum(cat_data[c]) / len(cat_data[c]))
    avgs = [sum(cat_data[c]) / len(cat_data[c]) for c in cats]
    colors = ["#1565C0" if v > 0 else "#90CAF9" for v in avgs]

    fig, ax = plt.subplots(figsize=(7, max(3, len(cats) * 0.45)))
    y = np.arange(len(cats))
    bars = ax.barh(y, avgs, color=colors, alpha=0.85, edgecolor="white", height=0.6)
    for bar, val in zip(bars, avgs):
        x_pos = bar.get_width()
        ha = "left" if val >= 0 else "right"
        ax.text(x_pos + 0.01 * (1 if val >= 0 else -1), bar.get_y() + bar.get_height() / 2,
                f"{val:+.2f}", va="center", ha=ha, fontsize=8)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{c} (n={len(cat_data[c])})" for c in cats])
    ax.set_xlabel("Team Uplift (Full Team $-$ Oracle)")
    ax.axvline(x=0, color="black", linewidth=0.8)
    ax.grid(axis="x", alpha=0.3)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    fig.savefig(os.path.join(output_dir, "fig3_category_uplift.pdf"))
    plt.close(fig)
    print(f"  {output_dir}/fig3_category_uplift.pdf")


def plot_component_scatter(
    metrics: list[TaskMetrics],
    output_dir: str,
) -> None:
    """Figure 4: Planning vs Verification scatter. Clean, no outlier labels."""
    fig, ax = plt.subplots(figsize=(4.5, 3.5))

    plan_vals, ver_vals, team_wins_list = [], [], []
    for m in metrics:
        pv = m.planning_value if not math.isnan(m.planning_value) else 0.0
        vv = m.verification_value if not math.isnan(m.verification_value) else 0.0
        plan_vals.append(pv)
        ver_vals.append(vv)
        team_wins_list.append(m.team_partial > m.oracle_partial + 0.01)

    tw_pv = [p for p, tw in zip(plan_vals, team_wins_list) if tw]
    tw_vv = [v for v, tw in zip(ver_vals, team_wins_list) if tw]
    ow_pv = [p for p, tw in zip(plan_vals, team_wins_list) if not tw]
    ow_vv = [v for v, tw in zip(ver_vals, team_wins_list) if not tw]

    ax.scatter(tw_pv, tw_vv, c="#0D47A1", marker="^", s=45, alpha=0.7,
              edgecolors="white", linewidth=0.5, label="Team > Oracle", zorder=3)
    ax.scatter(ow_pv, ow_vv, c="#90CAF9", marker="o", s=35, alpha=0.6,
              edgecolors="white", linewidth=0.5, label=r"Oracle $\geq$ Team", zorder=3)

    ax.set_xlabel("Planning Value (Full $-$ No Planner)")
    ax.set_ylabel("Verification Value (Full $-$ No Verifier)")
    ax.axhline(y=0, color="gray", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.axvline(x=0, color="gray", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.grid(alpha=0.15)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.legend(loc="lower left", framealpha=0.9, fontsize=9)
    ax.fill_between([0, 1.1], 0, 1.1, alpha=0.04, color="#1565C0", zorder=0)
    ax.fill_between([-1.1, 0], -1.1, 0, alpha=0.04, color="#90CAF9", zorder=0)

    fig.savefig(os.path.join(output_dir, "fig4_components.pdf"))
    plt.close(fig)
    print(f"  {output_dir}/fig4_components.pdf")


def plot_oracle_vs_team(
    metrics: list[TaskMetrics],
    output_dir: str,
) -> None:
    """Figure 5: Oracle vs Team scatter. No individual labels, compact."""
    fig, ax = plt.subplots(figsize=(4.5, 4))

    oracle_vals = [m.oracle_partial for m in metrics]
    team_vals = [m.team_partial for m in metrics]
    uplifts = [t - o for o, t in zip(oracle_vals, team_vals)]

    for ov, tv, up in zip(oracle_vals, team_vals, uplifts):
        color = "#0D47A1" if up > 0.01 else "#64B5F6" if up < -0.01 else "#B0BEC5"
        ax.scatter(ov, tv, c=color, s=30, alpha=0.7, edgecolors="white", linewidth=0.5, zorder=3)

    ax.plot([0, 1], [0, 1], color="#1565C0", linestyle="--", alpha=0.3, linewidth=1)
    ax.fill_between([0, 1], [0, 1], [1, 1], alpha=0.03, color="#1565C0")
    ax.fill_between([0, 1], [0, 0], [0, 1], alpha=0.03, color="#90CAF9")
    ax.set_xlabel("Oracle Partial Score", fontsize=9)
    ax.set_ylabel("Full Team Partial Score", fontsize=9)
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.05, 1.05)
    ax.set_aspect("equal")
    ax.grid(alpha=0.15)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    tw = mpatches.Patch(color="#0D47A1", alpha=0.7, label="Team > Oracle")
    ow = mpatches.Patch(color="#64B5F6", alpha=0.7, label="Oracle > Team")
    ne = mpatches.Patch(color="#B0BEC5", alpha=0.7, label="Neutral")
    ax.legend(handles=[tw, ow, ne], loc="lower right", framealpha=0.9, fontsize=7)

    fig.savefig(os.path.join(output_dir, "fig5_oracle_vs_team.pdf"))
    plt.close(fig)
    print(f"  {output_dir}/fig5_oracle_vs_team.pdf")


def plot_category_distribution(
    metrics: list[TaskMetrics],
    output_dir: str,
) -> None:
    """Donut chart. Large format with big fonts."""
    meta_map = {
        "Security": [], "Data Engineering": [], "Incident Response": [],
        "Software Engineering": [], "Testing": [], "Operations": [],
        "Multi-language": [], "Adversarial": [], "Policy": [],
        "Long-Horizon": [], "Cross-System": [], "Distributed": [],
        "Other": [],
    }
    for m in metrics:
        cat = _task_category(m.task_id)
        placed = False
        for mk in meta_map:
            if mk.lower().replace("-", " ") in cat.lower().replace("-", " "):
                meta_map[mk].append(m)
                placed = True
                break
        if not placed:
            cl = cat.lower()
            if "spec" in cl:
                meta_map["Adversarial"].append(m)
            elif "pipe" in cl:
                meta_map["Data Engineering"].append(m)
            elif "code review" in cl or "info" in cl:
                meta_map["Other"].append(m)
            elif "negot" in cl:
                meta_map["Other"].append(m)
            elif "integ" in cl:
                meta_map["Software Engineering"].append(m)
            elif "expertise" in cl:
                meta_map["Testing"].append(m)
            else:
                meta_map["Other"].append(m)

    data = {k: len(v) for k, v in meta_map.items() if v}
    data = dict(sorted(data.items(), key=lambda x: -x[1]))

    fig, ax = plt.subplots(figsize=(9, 6.5))
    colors = [
        "#0D47A1", "#1565C0", "#1976D2", "#1E88E5", "#2196F3",
        "#42A5F5", "#64B5F6", "#90CAF9", "#BBDEFB", "#0277BD",
        "#00838F", "#283593", "#B0BEC5",
    ]
    labels = [f"{k} (n={v})" for k, v in data.items()]
    sizes = list(data.values())

    wedges, texts, autotexts = ax.pie(
        sizes, labels=None, autopct=lambda pct: f"{pct:.0f}%" if pct > 4 else "",
        colors=colors[:len(data)], startangle=90, pctdistance=0.78,
        wedgeprops=dict(width=0.5, edgecolor="white", linewidth=2.5),
        textprops=dict(fontsize=11),
    )
    for at in autotexts:
        at.set_fontsize(10)
        at.set_color("white")
        at.set_fontweight("bold")
    ax.legend(labels, loc="center left", bbox_to_anchor=(1, 0.5), fontsize=11, frameon=False)
    plt.tight_layout()
    fig.savefig(os.path.join(output_dir, "fig_category_pie.pdf"))
    plt.close(fig)
    print(f"  {output_dir}/fig_category_pie.pdf")


def plot_capability_scaling(output_dir: str) -> None:
    """Figure: Model capability vs team uplift (the 'teamwork scaling law').
    Uses cross-model stats to show weaker models benefit more from teamwork."""
    cross_model_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "shared", "paper", "cross_model_stats.json"
    )
    if not os.path.exists(cross_model_path):
        print("  (skipped capability scaling: cross_model_stats.json not found)")
        return

    with open(cross_model_path) as f:
        data = json.load(f)

    models = []
    restricted_scores = []
    win_rates = []

    for model_name, stats in data["per_model"].items():
        short = model_name.replace("-preview", "").replace("gemini-", "G").replace("gpt-", "GPT-")
        short = short.replace("3-flash", "3-Flash").replace("3.1-flash-lite", "3.1-Lite")
        short = short.replace("5-mini", "5-Mini").replace("5-nano", "5-Nano")
        models.append(short)
        restricted_scores.append(stats["avg_restricted"])
        win_rates.append(stats["team_helps_pct"] * 100)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4.5))

    # Panel (a): Bar chart of team win rate per model
    x = np.arange(len(models))
    bar_colors = ["#0D47A1", "#1976D2", "#42A5F5", "#90CAF9"]
    bars = ax1.bar(x, win_rates, color=bar_colors, alpha=0.85, edgecolor="white", width=0.55)
    ax1.set_xticks(x)
    ax1.set_xticklabels(models, fontsize=10, rotation=15, ha="right")
    ax1.set_ylabel("Team Win Rate (\% tasks Team $>$ Oracle)", fontsize=11)
    ax1.set_ylim(0, 100)
    ax1.grid(axis="y", alpha=0.2)
    ax1.spines["top"].set_visible(False)
    ax1.spines["right"].set_visible(False)
    for bar, val in zip(bars, win_rates):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                 f"{val:.0f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax1.text(0.02, 0.98, "(a)", transform=ax1.transAxes, fontsize=11,
             fontweight="bold", va="top")

    # Panel (b): Restricted score vs win rate (inverse relationship)
    ax2.scatter(restricted_scores, win_rates, c=bar_colors, s=120, zorder=3,
               edgecolors="white", linewidth=1.5)
    offsets_b = [(8, 10), (-8, -14), (8, -14), (8, 10)]
    for i, (m, rx, wr) in enumerate(zip(models, restricted_scores, win_rates)):
        dx, dy = offsets_b[i % len(offsets_b)]
        ax2.annotate(m, (rx, wr), fontsize=8,
                    xytext=(dx, dy), textcoords="offset points",
                    ha="left" if dx > 0 else "right",
                    arrowprops=dict(arrowstyle="-", color="#AAA", lw=0.5))

    # Trend line
    z = np.polyfit(restricted_scores, win_rates, 1)
    p = np.poly1d(z)
    x_line = np.linspace(min(restricted_scores) - 0.02, max(restricted_scores) + 0.02, 100)
    ax2.plot(x_line, p(x_line), "--", color="#1565C0", alpha=0.5, linewidth=1.5)

    ax2.set_xlabel("Restricted Score (Without Specification Access)", fontsize=11)
    ax2.set_ylabel("Team Win Rate (\%)", fontsize=11)
    ax2.grid(alpha=0.2)
    ax2.spines["top"].set_visible(False)
    ax2.spines["right"].set_visible(False)
    ax2.text(0.02, 0.98, "(b)", transform=ax2.transAxes, fontsize=11,
             fontweight="bold", va="top")

    plt.tight_layout(w_pad=3)
    fig.savefig(os.path.join(output_dir, "fig_capability_scaling.pdf"))
    plt.close(fig)
    print(f"  {output_dir}/fig_capability_scaling.pdf")


def plot_radar_cross_model(output_dir: str) -> None:
    """Radar: team UPLIFT per category, aggregated across 4 cross-model models."""
    cross_model_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "shared", "paper", "cross_model_stats.json"
    )
    if not os.path.exists(cross_model_path):
        print("  (skipped radar: cross_model_stats.json not found)")
        return

    with open(cross_model_path) as f:
        data = json.load(f)

    # Aggregate team-oracle uplift per category across all models
    cat_uplifts: dict[str, list[float]] = defaultdict(list)
    for task_data in data.get("per_task", []):
        cat = task_data.get("category", "Unknown")
        for model_name, model_data in task_data.get("models", {}).items():
            team = model_data.get("team", 0)
            oracle = model_data.get("oracle", 0)
            if team is not None and oracle is not None:
                cat_uplifts[cat].append(team - oracle)

    # Filter to categories with enough data
    valid_cats = sorted([c for c in cat_uplifts if len(cat_uplifts[c]) >= 3])
    if len(valid_cats) < 4:
        print("  (skipped radar: too few categories)")
        return

    avg_uplifts = [sum(cat_uplifts[c]) / len(cat_uplifts[c]) for c in valid_cats]

    # Shift to make all values positive for radar (add min offset)
    min_val = min(avg_uplifts)
    offset = abs(min_val) + 0.05 if min_val < 0 else 0
    shifted = [v + offset for v in avg_uplifts]

    angles = np.linspace(0, 2 * np.pi, len(valid_cats), endpoint=False).tolist()
    angles += angles[:1]
    shifted_closed = shifted + shifted[:1]

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    ax.plot(angles, shifted_closed, "o-", color="#0D47A1", linewidth=2.5,
            markersize=7, alpha=0.8)
    ax.fill(angles, shifted_closed, color="#1565C0", alpha=0.2)

    # Zero line (prominent red dashed circle)
    zero_line = [offset] * (len(valid_cats) + 1)
    ax.plot(angles, zero_line, "--", color="#D32F2F", linewidth=2.0, alpha=0.8,
            label="Zero uplift", zorder=5)

    short_names = []
    for c in valid_cats:
        name = c.replace("Engineering", "Eng.").replace("Response", "Resp.")
        name = name.replace("language", "lang").replace("Information", "Info.")
        name = name.replace("Distributed", "Dist.").replace("Integration", "Integ.")
        if len(name) > 15:
            name = name[:13] + "."
        short_names.append(name)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(short_names, fontsize=10, fontweight="bold")

    # Custom ytick labels showing actual uplift values
    yticks_shifted = np.linspace(0, max(shifted_closed) * 1.1, 5)
    yticks_actual = [v - offset for v in yticks_shifted]
    ax.set_yticks(yticks_shifted)
    ax.set_yticklabels([f"{v:+.2f}" for v in yticks_actual], fontsize=8, color="gray")
    ax.set_ylim(0, max(shifted_closed) * 1.15)
    ax.grid(alpha=0.3)

    # Annotation
    ax.text(0.5, -0.08, "Dashed red line = zero uplift (team = oracle)",
            transform=ax.transAxes, fontsize=9, ha="center", color="#666", style="italic")

    fig.savefig(os.path.join(output_dir, "fig_radar_categories.pdf"))
    plt.close(fig)
    print(f"  {output_dir}/fig_radar_categories.pdf")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate TeamBench paper figures")
    ap.add_argument("--ablation", nargs="+", required=True, help="Ablation JSON files")
    ap.add_argument("--output-dir", default="shared/paper/figures", help="Output directory")
    ap.add_argument("--format", default="pdf", choices=["pdf", "png"], help="Output format")
    args = ap.parse_args()

    runs = merge_ablation_files(args.ablation)
    metrics = runs_to_task_metrics(runs)

    print(f"Generating figures for {len(metrics)} tasks ({len(runs)} runs)")
    os.makedirs(args.output_dir, exist_ok=True)

    plot_condition_comparison(metrics, args.output_dir)
    plot_category_uplift(metrics, args.output_dir)
    plot_component_scatter(metrics, args.output_dir)
    plot_oracle_vs_team(metrics, args.output_dir)
    plot_category_distribution(metrics, args.output_dir)
    plot_capability_scaling(args.output_dir)
    plot_radar_cross_model(args.output_dir)

    print(f"\nAll figures saved to: {args.output_dir}/")


if __name__ == "__main__":
    main()
