#!/usr/bin/env python3
"""Resume cross-model ablation, running only missing conditions/tasks.

Loads existing results JSON, identifies runs that errored or are missing,
and re-runs only those. Merges new results into the existing file.

Usage:
    python scripts/resume_crossmodel.py --model claude-sonnet-4-6
    python scripts/resume_crossmodel.py --model claude-haiku-4-5-20251001
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.run_crossmodel import TASKS, MODEL_TO_FILE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--seeds", nargs="+", type=int, default=[0])
    args = ap.parse_args()

    fname = MODEL_TO_FILE.get(args.model, f"crossmodel_{args.model.replace('-','')}_seed0.json")
    outpath = os.path.join("shared", "ablation_results", fname)

    # Load existing results
    existing_runs = []
    if os.path.exists(outpath):
        with open(outpath) as f:
            data = json.load(f)
            existing_runs = data.get("runs", [])

    # Build set of (condition, task_id, seed) that completed successfully (no error)
    completed = set()
    for r in existing_runs:
        if not r.get("error"):
            completed.add((r["condition"], r["task_id"], r["seed"]))

    print(f"Existing results: {len(existing_runs)} total, {len(completed)} successful", flush=True)

    from harness.ablation import AblationCondition, run_ablation_condition
    from harness.adapters import create_adapter
    from harness.run_all import setup_run, grade_run

    conditions = [
        AblationCondition.ORACLE,
        AblationCondition.RESTRICTED,
        AblationCondition.TEAM_NO_VERIFY,
        AblationCondition.TEAM_NO_PLAN,
        AblationCondition.FULL,
    ]

    adapter = create_adapter(model=args.model, temperature=0.2)
    tasks_dir = os.path.abspath("tasks")
    runs_base = os.path.join(os.path.dirname(outpath), "ablation_runs")

    # Compute what needs to run
    missing = []
    for cond in conditions:
        for task in TASKS:
            for seed in args.seeds:
                if (cond.value, task, seed) not in completed:
                    missing.append((cond, task, seed))

    print(f"Missing runs: {len(missing)}", flush=True)
    if not missing:
        print("Nothing to do!")
        return

    # Keep only successful existing runs for merge
    good_runs = [r for r in existing_runs if not r.get("error")]

    # Run missing
    for i, (cond, task, seed) in enumerate(missing):
        print(f"\n[{i+1}/{len(missing)}] {cond.value} x {task} (seed={seed})", flush=True)
        start = time.time()
        try:
            run_id, run_dir, task_dir = setup_run(task, tasks_dir, runs_base, seed=seed)

            # Store condition in run_meta.json
            meta_path = os.path.join(run_dir, "run_meta.json")
            if os.path.isfile(meta_path):
                with open(meta_path, "r") as mf:
                    meta = json.load(mf)
                meta["condition"] = cond.value
                with open(meta_path, "w") as mf:
                    json.dump(meta, mf, indent=2)

            orch_result = run_ablation_condition(
                condition=cond,
                task_dir=task_dir,
                run_dir=run_dir,
                adapter=adapter,
                max_turns=20,
                max_remediation=2,
            )

            elapsed = time.time() - start
            score = grade_run(task, task_dir, run_dir)
            partial = score.get("secondary", {}).get(
                "partial_score", 1.0 if score.get("pass") else 0.0
            )
            status = "PASS" if score.get("pass") else "FAIL"
            print(f"  {status} (partial={partial:.2f}, {elapsed:.1f}s, {orch_result.total_turns} turns)", flush=True)

            good_runs.append({
                "condition": cond.value,
                "task_id": task,
                "seed": seed,
                "run_id": run_id,
                "run_dir": run_dir,
                "pass": bool(score.get("pass", False)),
                "partial_score": partial,
                "elapsed_sec": round(elapsed, 1),
                "failure_modes": score.get("failure_modes", []),
                "error": None,
            })

        except Exception as exc:
            elapsed = time.time() - start
            print(f"  ERROR ({elapsed:.1f}s): {exc}", flush=True)
            good_runs.append({
                "condition": cond.value,
                "task_id": task,
                "seed": seed,
                "run_id": None,
                "run_dir": None,
                "pass": False,
                "partial_score": 0.0,
                "elapsed_sec": round(elapsed, 1),
                "failure_modes": [],
                "error": str(exc),
            })

        # Save after every run (incremental)
        out = {
            "model": args.model,
            "tasks": TASKS,
            "seeds": args.seeds,
            "runs": good_runs,
        }
        with open(outpath, "w") as f:
            json.dump(out, f, indent=2)

    # Final summary
    print(f"\n{'='*60}")
    print(f"RESUME COMPLETE — {len(good_runs)} total runs in {outpath}")
    print(f"{'='*60}")
    from collections import Counter
    by_cond = Counter()
    by_cond_total = Counter()
    for r in good_runs:
        c = r["condition"]
        by_cond_total[c] += 1
        if r.get("pass"):
            by_cond[c] += 1
    for c in ["oracle", "restricted", "team_no_verify", "team_no_plan", "full"]:
        t = by_cond_total.get(c, 0)
        p = by_cond.get(c, 0)
        print(f"  {c:20s} {p:2d}/{t:2d} passed")


if __name__ == "__main__":
    main()
