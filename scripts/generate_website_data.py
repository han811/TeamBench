#!/usr/bin/env python3
"""Generate JavaScript data snippet for teambench.github.io static website.

Reads leaderboard/data/leaderboard_data.json (produced by regenerate_leaderboard_data.py)
and outputs a JavaScript data block that can be pasted into the website's index.html.

Usage:
    python scripts/generate_website_data.py
    python scripts/generate_website_data.py --output shared/paper/website_data.js
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    ap = argparse.ArgumentParser(description="Generate website leaderboard data")
    ap.add_argument("--input", default="leaderboard/data/leaderboard_data.json")
    ap.add_argument("--output", default="shared/paper/website_leaderboard.js")
    args = ap.parse_args()

    with open(args.input) as f:
        data = json.load(f)

    cm = data.get("cross_model", {})
    per_model = cm.get("per_model", {})

    # Sort by Full Team score descending
    ranked = sorted(per_model.items(), key=lambda kv: kv[1]["avg_team"], reverse=True)

    # Provider detection
    def provider(name):
        if any(x in name for x in ["GPT", "gpt", "OSS"]):
            return "OpenAI"
        if any(x in name for x in ["Claude", "claude"]):
            return "Anthropic"
        if any(x in name for x in ["Gemini", "gemini"]):
            return "Google"
        if any(x in name for x in ["Gemma", "gemma", "CodeGemma"]):
            return "Google"
        if any(x in name for x in ["Qwen", "qwen"]):
            return "Alibaba"
        if any(x in name for x in ["DeepSeek", "deepseek"]):
            return "DeepSeek"
        if any(x in name for x in ["Devstral", "devstral"]):
            return "Mistral"
        return "Other"

    # Generate leaderboard table rows
    print(f"// Generated from {args.input}")
    print(f"// {len(ranked)} models, {cm.get('total_tasks', 28)} tasks")
    print()

    lines = []
    lines.append("const leaderboardData = [")
    for i, (model, stats) in enumerate(ranked):
        prov = provider(model)
        lines.append(f'  {{rank: {i+1}, model: "{model}", provider: "{prov}", '
                     f'oracle: {stats["avg_oracle"]:.3f}, '
                     f'restricted: {stats["avg_restricted"]:.3f}, '
                     f'noPlan: {stats["avg_no_plan"]:.3f}, '
                     f'noVerify: {stats["avg_no_verify"]:.3f}, '
                     f'full: {stats["avg_team"]:.3f}, '
                     f'uplift: {stats["avg_uplift"]:.3f}, '
                     f'tni: {stats["avg_tni"]:.3f}, '
                     f'teamHelps: {stats["team_helps_pct"]:.2f}}},')
    lines.append("];")

    # Also generate chart data for ablation comparison
    lines.append("")
    lines.append("const ablationChartLabels = [")
    for model, _ in ranked:
        lines.append(f'  "{model}",')
    lines.append("];")

    for condition, key in [("Oracle", "avg_oracle"), ("Restricted", "avg_restricted"),
                           ("No Planner", "avg_no_plan"), ("No Evaluator", "avg_no_verify"),
                           ("Full", "avg_team")]:
        lines.append(f"const ablation{condition.replace(' ', '')}Data = [" +
                     ", ".join(f"{stats[key]:.3f}" for _, stats in ranked) + "];")

    lines.append("")
    lines.append("const upliftData = [" +
                 ", ".join(f"{stats['avg_uplift']:.3f}" for _, stats in ranked) + "];")

    output = "\n".join(lines)
    print(output)

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w") as f:
        f.write(output + "\n")
    print(f"\n// Written to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
