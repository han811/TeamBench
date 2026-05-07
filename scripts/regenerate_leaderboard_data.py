#!/usr/bin/env python3
"""Regenerate leaderboard/data/leaderboard_data.json from all crossmodel results.

Reads all shared/ablation_results/crossmodel_*.json files and
shared/submissions/*.json files, computes per-model metrics, and writes
the unified leaderboard JSON consumed by the Gradio app and website.

Usage:
    python scripts/regenerate_leaderboard_data.py
    python scripts/regenerate_leaderboard_data.py --results-dir shared/ablation_results
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from harness.compute_tni import TaskMetrics
from harness.paper_tables import CATEGORY_MAP

# ---------------------------------------------------------------------------
# Display name mapping (model string -> human-readable)
# ---------------------------------------------------------------------------

MODEL_DISPLAY = {
    # API models
    "gemini-3-flash-preview": "Gemini 3 Flash",
    "gemini-3.1-flash-lite-preview": "Gemini 3.1 Lite",
    "gpt-5-mini": "GPT-5 Mini",
    "gpt-5-nano": "GPT-5 Nano",
    "gpt-5.3-chat-latest": "GPT-5.3 Chat",
    "gpt-5.4": "GPT-5.4",
    "claude-sonnet-4-6": "Claude Sonnet 4.6",
    "claude-haiku-4-5-20251001": "Claude Haiku 4.5",
    # vLLM-served models (strip vllm: prefix and URL)
    "Qwen/Qwen3-4B": "Qwen3-4B",
    "Qwen/Qwen3-8B": "Qwen3-8B",
    "Qwen/Qwen3-14B": "Qwen3-14B",
    "Qwen/Qwen3-32B": "Qwen3-32B",
    "Qwen/Qwen3.5-0.8B": "Qwen3.5-0.8B",
    "Qwen/Qwen3.5-2B": "Qwen3.5-2B",
    "Qwen/Qwen3.5-4B": "Qwen3.5-4B",
    "Qwen/Qwen3.5-9B": "Qwen3.5-9B",
    "Qwen/Qwen3.5-27B": "Qwen3.5-27B",
    "Qwen/Qwen3.5-35B-A3B": "Qwen3.5-35B-A3B",
    "Qwen/Qwen2.5-Coder-32B-Instruct": "Qwen2.5-Coder-32B",
    "Qwen/Qwen3-Coder-30B-A3B-Instruct": "Qwen3-Coder-30B-A3B",
    "deepseek-ai/DeepSeek-R1-Distill-Qwen-32B": "DeepSeek-R1-Distill-32B",
    "google/gemma-3-27b-it": "Gemma 3 27B",
    "openai/gpt-oss-20b": "GPT-OSS-20B",
    "mistralai/Devstral-Small-2-24B-Instruct-2512": "Devstral-24B",
    "google/codegemma-7b-it": "CodeGemma 7B",
}

# Provider mapping for display
MODEL_PROVIDER = {
    "Gemini": "Google", "GPT": "OpenAI", "Claude": "Anthropic",
    "Qwen": "Alibaba", "DeepSeek": "DeepSeek", "Gemma": "Google",
    "Devstral": "Mistral", "CodeGemma": "Google",
}


def _normalize_model_name(raw: str) -> str:
    """Extract clean model name from vllm:Org/Model@url format."""
    name = raw
    if name.startswith("vllm:"):
        name = name[5:]
    if "@" in name:
        name = name.split("@")[0]
    return name


def _display_name(raw: str) -> str:
    clean = _normalize_model_name(raw)
    return MODEL_DISPLAY.get(clean, MODEL_DISPLAY.get(raw, clean))


def _provider(display: str) -> str:
    for prefix, prov in MODEL_PROVIDER.items():
        if display.startswith(prefix):
            return prov
    return "Other"


def _task_category(task_id: str) -> str:
    prefix = ""
    first_part = task_id.split("_")[0] if "_" in task_id else task_id
    for ch in first_part:
        if ch.isalpha():
            prefix += ch
        else:
            break
    return CATEGORY_MAP.get(prefix.upper(), prefix.upper())


# ---------------------------------------------------------------------------
# Load results
# ---------------------------------------------------------------------------

def load_crossmodel_results(results_dir: str) -> dict[str, list[dict]]:
    """Load all crossmodel_*.json files, return {model: [runs]}."""
    model_runs: dict[str, list[dict]] = {}
    results_path = Path(results_dir)

    for f in sorted(results_path.glob("crossmodel_*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            print(f"  WARN: skipping {f} (parse error)")
            continue

        model = data.get("model", "")
        runs = data.get("runs", [])
        if not model or not runs:
            print(f"  WARN: skipping {f} (no model or runs)")
            continue

        model_runs[model] = runs
        print(f"  Loaded {f.name}: {len(runs)} runs, model={_display_name(model)}")

    return model_runs


def load_submissions(submissions_dir: str) -> dict[str, list[dict]]:
    """Load submitted leaderboard JSONs."""
    model_runs: dict[str, list[dict]] = {}
    sub_path = Path(submissions_dir)
    if not sub_path.exists():
        return model_runs

    for f in sorted(sub_path.glob("*.json")):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        model = data.get("model", "")
        runs = data.get("raw_runs", [])
        if model and runs:
            model_runs[model] = runs
            print(f"  Loaded submission {f.name}: {len(runs)} runs")

    return model_runs


# ---------------------------------------------------------------------------
# Compute per-model stats
# ---------------------------------------------------------------------------

def compute_model_stats(runs: list[dict]) -> dict:
    """Compute aggregate stats for a single model."""
    cond_scores: dict[str, list[float]] = defaultdict(list)
    task_ids = set()

    for r in runs:
        partial = float(r.get("partial_score", 1.0 if r.get("pass") else 0.0))
        cond_scores[r["condition"]].append(partial)
        task_ids.add(r["task_id"])

    def avg(lst: list[float]) -> float:
        return sum(lst) / len(lst) if lst else 0.0

    avg_oracle = avg(cond_scores.get("oracle", []))
    avg_restricted = avg(cond_scores.get("restricted", []))
    avg_team = avg(cond_scores.get("full", []))
    avg_no_plan = avg(cond_scores.get("team_no_plan", []))
    avg_no_verify = avg(cond_scores.get("team_no_verify", []))

    # Per-task metrics for TNI
    task_cond: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in runs:
        partial = float(r.get("partial_score", 1.0 if r.get("pass") else 0.0))
        task_cond[r["task_id"]][r["condition"]].append(partial)

    metrics_list = []
    for tid in sorted(task_ids):
        tc = task_cond[tid]
        m = TaskMetrics(
            task_id=tid,
            oracle_partial=avg(tc.get("oracle", [])),
            restricted_partial=avg(tc.get("restricted", [])),
            team_partial=avg(tc.get("full", [])),
            no_plan_partial=avg(tc.get("team_no_plan", [])),
            no_verify_partial=avg(tc.get("team_no_verify", [])),
        )
        metrics_list.append(m)

    valid_tni = [m.tni for m in metrics_list
                 if not math.isnan(m.tni) and abs(m.necessity_gap) > 0.05]
    avg_tni = sum(valid_tni) / len(valid_tni) if valid_tni else 0.0

    team_helps = sum(1 for m in metrics_list if m.team_uplift > 0.01)

    return {
        "task_count": len(task_ids),
        "run_count": len(runs),
        "avg_oracle": round(avg_oracle, 4),
        "avg_restricted": round(avg_restricted, 4),
        "avg_team": round(avg_team, 4),
        "avg_no_plan": round(avg_no_plan, 4),
        "avg_no_verify": round(avg_no_verify, 4),
        "avg_uplift": round(avg_team - avg_oracle, 4),
        "avg_tni": round(avg_tni, 4),
        "valid_tni_count": len(valid_tni),
        "team_helps_count": team_helps,
        "team_helps_pct": round(team_helps / max(1, len(task_ids)), 4),
    }


def compute_per_task_cross_model(all_model_runs: dict[str, list[dict]]) -> list[dict]:
    """Compute per-task stats across all models."""
    # Collect all task IDs
    all_tasks = set()
    for runs in all_model_runs.values():
        for r in runs:
            all_tasks.add(r["task_id"])

    per_task = []
    for tid in sorted(all_tasks):
        task_entry = {
            "task_id": tid,
            "category": _task_category(tid),
            "models": {},
        }
        for model, runs in all_model_runs.items():
            task_runs = [r for r in runs if r["task_id"] == tid]
            if not task_runs:
                continue

            cond_scores: dict[str, list[float]] = defaultdict(list)
            for r in task_runs:
                partial = float(r.get("partial_score", 1.0 if r.get("pass") else 0.0))
                cond_scores[r["condition"]].append(partial)

            def avg(lst):
                return sum(lst) / len(lst) if lst else 0.0

            o = avg(cond_scores.get("oracle", []))
            t = avg(cond_scores.get("full", []))
            r_val = avg(cond_scores.get("restricted", []))
            gap = o - r_val
            tni = (t - r_val) / max(0.05, gap) if abs(gap) > 0.05 else None

            uplift = t - o
            if uplift > 0.01:
                cls = "HIGH-TNI" if (tni and tni >= 1.0) else "TEAM-HELPS"
            elif uplift < -0.01:
                cls = "TEAM-HURTS"
            else:
                cls = "NEUTRAL"

            display = _display_name(model)
            task_entry["models"][display] = {
                "oracle": round(o, 4),
                "restricted": round(r_val, 4),
                "team": round(t, 4),
                "no_plan": round(avg(cond_scores.get("team_no_plan", [])), 4),
                "no_verify": round(avg(cond_scores.get("team_no_verify", [])), 4),
                "team_uplift": round(uplift, 4),
                "tni": round(tni, 4) if tni is not None else None,
                "classification": cls,
            }

        per_task.append(task_entry)

    return per_task


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Regenerate leaderboard data")
    ap.add_argument("--results-dir", default="shared/ablation_results",
                    help="Directory containing crossmodel_*.json files")
    ap.add_argument("--submissions-dir", default="shared/submissions",
                    help="Directory containing submission JSONs")
    ap.add_argument("--output", default="leaderboard/data/leaderboard_data.json",
                    help="Output path for leaderboard JSON")
    ap.add_argument("--cross-model-output", default="leaderboard/data/cross_model_stats.json",
                    help="Output path for cross-model stats JSON")
    args = ap.parse_args()

    print("=== Regenerating leaderboard data ===\n")

    # Load all results
    print("Loading crossmodel results:")
    model_runs = load_crossmodel_results(args.results_dir)

    print("\nLoading submissions:")
    sub_runs = load_submissions(args.submissions_dir)
    model_runs.update(sub_runs)

    if not model_runs:
        print("ERROR: No model results found!")
        sys.exit(1)

    # Filter out models with 0 runs
    model_runs = {m: r for m, r in model_runs.items() if len(r) > 0}
    print(f"\nTotal: {len(model_runs)} models with data\n")

    # Compute per-model stats
    per_model: dict[str, dict] = {}
    models_list = []
    for model, runs in sorted(model_runs.items(), key=lambda kv: _display_name(kv[0])):
        display = _display_name(model)
        stats = compute_model_stats(runs)
        per_model[display] = stats
        models_list.append(display)
        print(f"  {display:30s}  oracle={stats['avg_oracle']:.1%}  "
              f"team={stats['avg_team']:.1%}  uplift={stats['avg_uplift']:+.1%}  "
              f"TNI={stats['avg_tni']:.3f}")

    # Compute per-task cross-model data
    # Use display names as keys
    display_runs = {_display_name(m): r for m, r in model_runs.items()}
    per_task_cross = compute_per_task_cross_model(model_runs)

    # Consistent team-helps/hurts
    task_votes: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for task in per_task_cross:
        for mname, mdata in task["models"].items():
            cls = mdata.get("classification", "NEUTRAL")
            task_votes[task["task_id"]][cls] += 1

    n_models = len(models_list)
    consistent_helps = [tid for tid, votes in task_votes.items()
                        if votes.get("TEAM-HELPS", 0) + votes.get("HIGH-TNI", 0) >= n_models * 0.7]
    consistent_hurts = [tid for tid, votes in task_votes.items()
                        if votes.get("TEAM-HURTS", 0) >= n_models * 0.7]

    # Build cross_model_stats
    cross_model_stats = {
        "models": models_list,
        "total_tasks": len(per_task_cross),
        "per_model": per_model,
        "consistent_team_helps": sorted(consistent_helps),
        "consistent_team_hurts": sorted(consistent_hurts),
        "per_task": per_task_cross,
    }

    # Build the main leaderboard_data.json (keep backward compatibility)
    # Use the reference model (Gemini 3 Flash) for the overview section
    ref_model = "gemini-3-flash-preview"
    ref_runs = model_runs.get(ref_model, [])

    # Compute categories
    categories = sorted(set(_task_category(t["task_id"]) for t in per_task_cross))

    # Per-category from reference model
    per_category = {}
    if ref_runs:
        cat_tasks: dict[str, list] = defaultdict(list)
        task_cond: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        for r in ref_runs:
            partial = float(r.get("partial_score", 1.0 if r.get("pass") else 0.0))
            task_cond[r["task_id"]][r["condition"]].append(partial)

        def avg(lst):
            return sum(lst) / len(lst) if lst else 0.0

        for tid, tc in task_cond.items():
            cat = _task_category(tid)
            o = avg(tc.get("oracle", []))
            t = avg(tc.get("full", []))
            cat_tasks[cat].append({"oracle": o, "team": t, "uplift": t - o})

        for cat in sorted(cat_tasks):
            entries = cat_tasks[cat]
            n = len(entries)
            avg_o = sum(e["oracle"] for e in entries) / n
            avg_t = sum(e["team"] for e in entries) / n
            avg_u = sum(e["uplift"] for e in entries) / n
            helps = sum(1 for e in entries if e["uplift"] > 0.01)
            per_category[cat] = {
                "count": n,
                "avg_team": round(avg_t, 3),
                "avg_oracle": round(avg_o, 3),
                "avg_uplift": round(avg_u, 3),
                "team_helps": helps,
            }

    # Aggregate stats from reference model
    ref_stats = per_model.get(_display_name(ref_model), {})
    aggregate = {
        "avg_team": ref_stats.get("avg_team", 0),
        "avg_oracle": ref_stats.get("avg_oracle", 0),
        "avg_uplift": ref_stats.get("avg_uplift", 0),
        "avg_tni": ref_stats.get("avg_tni", 0),
        "team_helps_count": ref_stats.get("team_helps_count", 0),
        "high_tni_count": sum(1 for m in per_task_cross
                              for md in m["models"].values()
                              if md.get("classification") == "HIGH-TNI") // max(1, n_models),
    }

    leaderboard_data = {
        "total_tasks": len(per_task_cross),
        "total_hard": len(per_task_cross),  # placeholder
        "total_standard": 0,
        "model": _display_name(ref_model),
        "cross_model_count": len(per_task_cross),
        "cross_model_models": models_list,
        "aggregate": aggregate,
        "categories": categories,
        "per_category": per_category,
        "cross_model": cross_model_stats,
    }

    # Write outputs
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(leaderboard_data, f, indent=2, ensure_ascii=False)
    print(f"\nWrote {args.output}")

    os.makedirs(os.path.dirname(args.cross_model_output), exist_ok=True)
    with open(args.cross_model_output, "w", encoding="utf-8") as f:
        json.dump(cross_model_stats, f, indent=2, ensure_ascii=False)
    print(f"Wrote {args.cross_model_output}")

    print(f"\n=== Leaderboard: {len(models_list)} models, {len(per_task_cross)} tasks ===")


if __name__ == "__main__":
    main()
