"""
TeamBench — Advanced Metrics Analysis
======================================
Computes 5 advanced metrics from existing ablation data and run logs:

  1. Communication Efficiency Index (CEI)
     CEI = (S_full - S_no_plan) / planner_message_tokens
     Token proxy: character count / 4 from dialogue.jsonl planner messages.
     Falls back to per-task character-average when dialogue files are absent.

  2. Verification Accuracy (VA)
     VA = correct_verifier_judgments / total_verifier_judgments
     Reads attestation.json (verdict field) vs reports/score.json (pass field).

  3. Recovery Rate (RR)
     tasks where planner hurt but full score > 0 / tasks where planner hurt
     "Planner hurt" = S_full < S_no_plan (by > threshold).

  4. Empirical Capability Threshold (ECT)
     Quadratic fit: team_uplift = α·oracle² + β·oracle + γ
     ECT = oracle score where uplift crosses zero (positive root).
     Bootstrap CI reported.

  5. Archetype-Conditional TNI
     Maps task_id prefixes to archetypes; reports mean TNI per archetype.

Outputs:
  shared/paper/advanced_metrics.json
  shared/paper/table_advanced_metrics.tex
"""
from __future__ import annotations

import glob
import json
import math
import os
import sys
from collections import defaultdict
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ABLATION_DIR = "shared/ablation_results"
RUNS_DIR = "shared/ablation_results/ablation_runs"
OUTPUT_JSON = "shared/paper/advanced_metrics.json"
OUTPUT_TEX = "shared/paper/table_advanced_metrics.tex"

CONDITIONS = {"oracle", "restricted", "full", "team_no_plan", "team_no_verify"}

# Archetype mapping: prefix -> archetype name
ARCHETYPE_MAP: dict[str, str] = {
    "RDS1": "open_ended", "RDS2": "open_ended", "RDS3": "open_ended",
    "RDS4": "open_ended", "RDS5": "open_ended", "RDS6": "open_ended",
    "RDS7": "open_ended", "RDS8": "open_ended", "RDS9": "open_ended",
    "RDS10": "open_ended",
    "RDS11": "adversarial", "RDS12": "adversarial", "RDS13": "adversarial",
    "RDS14": "adversarial", "RDS15": "adversarial", "RDS16": "adversarial",
    "RDS17": "adversarial", "RDS18": "adversarial",
    "RDS19": "discovery", "RDS20": "discovery", "RDS21": "discovery",
    "RDS22": "discovery", "RDS23": "discovery", "RDS24": "discovery",
    "RDS25": "synthesis", "RDS26": "synthesis", "RDS27": "synthesis",
    "RDS28": "synthesis", "RDS29": "synthesis", "RDS30": "synthesis",
    # Category-based fallback archetypes
    "TRAP": "adversarial",
    "CRYPTO": "adversarial",
    "DIST": "adversarial",
    "CROSS": "synthesis",
    "MULTI": "synthesis",
    "INT": "synthesis",
    "PIPE": "synthesis",
    "TEST": "discovery",
    "SPEC": "discovery",
    "CR": "discovery",
    "EA": "discovery",
    "SEC": "open_ended",
    "NEG": "open_ended",
    "POLICY": "open_ended",
    "INC": "open_ended",
    "IR": "open_ended",
    "OPS": "open_ended",
    "LH": "open_ended",
    "D": "open_ended",
    "S": "open_ended",
    "O": "open_ended",
    "P": "open_ended",
    "DS": "open_ended",
    "ML": "open_ended",
    "GH": "open_ended",
    "GO": "open_ended",
    "JS": "open_ended",
    "SQL": "open_ended",
    "SCALE": "open_ended",
    "API": "open_ended",
}

RECOVERY_THRESHOLD = 0.02   # planner hurt by more than this
BOOTSTRAP_N = 2000
RNG_SEED = 42


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def _partial_score(run: dict) -> float:
    """Return the best available partial score for a run record."""
    if "partial_score" in run:
        v = run["partial_score"]
        if v is not None:
            return float(v)
    sec = run.get("secondary") or {}
    if "partial_score" in sec and sec["partial_score"] is not None:
        return float(sec["partial_score"])
    # Fall back to boolean pass
    return 1.0 if run.get("pass") else 0.0


def _condition_norm(cond: str) -> str:
    """Normalise condition name variants."""
    c = cond.lower().strip()
    aliases = {
        "team_no_plan": "team_no_plan",
        "no_plan": "team_no_plan",
        "nop": "team_no_plan",
        "team_no_verify": "team_no_verify",
        "no_verify": "team_no_verify",
        "nov": "team_no_verify",
        "full": "full",
        "team": "full",
        "oracle": "oracle",
        "restricted": "restricted",
        "solo": "restricted",
    }
    return aliases.get(c, c)


def load_all_runs() -> list[dict]:
    """Load every run record from all ablation JSON files, deduplicating by run_id."""
    seen: set[str] = set()
    runs: list[dict] = []

    pattern = os.path.join(ABLATION_DIR, "*.json")
    for fpath in sorted(glob.glob(pattern)):
        try:
            with open(fpath) as fh:
                data = json.load(fh)
        except Exception as exc:
            print(f"  [WARN] Could not load {fpath}: {exc}", file=sys.stderr)
            continue

        raw_runs: list[Any] = []
        if isinstance(data, list):
            raw_runs = data
        elif isinstance(data, dict):
            raw_runs = data.get("runs", [])

        for r in raw_runs:
            if not isinstance(r, dict):
                continue
            cond = r.get("condition", "")
            if not cond:
                continue
            r["condition"] = _condition_norm(cond)

            # Deduplicate by run_id when available
            rid = r.get("run_id")
            task_cond_seed = (r.get("task_id", ""), r["condition"], r.get("seed", 0))
            key = rid if rid else str(task_cond_seed)
            if key in seen:
                continue
            seen.add(key)
            runs.append(r)

    return runs


def aggregate_by_task(runs: list[dict]) -> dict[str, dict[str, float]]:
    """
    Returns {task_id: {condition: mean_partial_score}}.
    When multiple seeds exist for the same (task, condition), average them.
    """
    buckets: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for r in runs:
        tid = r.get("task_id", "")
        if not tid:
            continue
        cond = r["condition"]
        buckets[tid][cond].append(_partial_score(r))

    result: dict[str, dict[str, float]] = {}
    for tid, conds in buckets.items():
        result[tid] = {c: float(np.mean(v)) for c, v in conds.items()}
    return result


# ---------------------------------------------------------------------------
# Metric 1: Communication Efficiency Index (CEI)
# ---------------------------------------------------------------------------

def _count_planner_tokens_from_dialogue(run_dir: str) -> int | None:
    """Return approx planner token count (chars/4) from dialogue.jsonl, or None."""
    dialogue_path = os.path.join(run_dir, "messages", "dialogue.jsonl")
    if not os.path.exists(dialogue_path):
        return None
    total_chars = 0
    try:
        with open(dialogue_path) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                msg = json.loads(line)
                if msg.get("role") == "planner":
                    total_chars += len(msg.get("content", ""))
    except Exception:
        return None
    return max(1, total_chars // 4)


def compute_cei(runs: list[dict], task_scores: dict[str, dict[str, float]]) -> dict:
    """
    CEI = planning_value / planner_tokens
    planning_value = S_full - S_no_plan  (per task)
    planner_tokens: from dialogue.jsonl for full-condition runs, else char proxy.
    """
    # Collect planner token counts per task from full-condition runs
    task_tokens: dict[str, list[int]] = defaultdict(list)
    for r in runs:
        if r.get("condition") != "full":
            continue
        tid = r.get("task_id", "")
        if not tid:
            continue
        run_dir = r.get("run_dir", "")
        if run_dir:
            tok = _count_planner_tokens_from_dialogue(run_dir)
            if tok is not None:
                task_tokens[tid].append(tok)

    # Also search task-named subdirs in RUNS_DIR
    task_run_dirs = os.path.join(RUNS_DIR)
    if os.path.isdir(task_run_dirs):
        for entry in os.listdir(task_run_dirs):
            task_subdir = os.path.join(task_run_dirs, entry)
            if not os.path.isdir(task_subdir):
                continue
            tid = entry  # e.g. "DS3_class_imbalance"
            if tid in task_tokens:
                continue  # already have data
            for run_hash in os.listdir(task_subdir):
                rpath = os.path.join(task_subdir, run_hash)
                meta_path = os.path.join(rpath, "run_meta.json")
                if not os.path.exists(meta_path):
                    continue
                try:
                    meta = json.load(open(meta_path))
                except Exception:
                    continue
                if meta.get("condition") != "full":
                    continue
                tok = _count_planner_tokens_from_dialogue(rpath)
                if tok is not None:
                    task_tokens[tid].append(tok)

    cei_values: list[float] = []
    task_details: list[dict] = []
    n_with_tokens = 0
    n_proxy = 0

    for tid, scores in task_scores.items():
        s_full = scores.get("full")
        s_no_plan = scores.get("team_no_plan")
        if s_full is None or s_no_plan is None:
            continue
        planning_value = s_full - s_no_plan

        tokens_list = task_tokens.get(tid, [])
        if tokens_list:
            tokens = float(np.mean(tokens_list))
            source = "dialogue"
            n_with_tokens += 1
        else:
            # Proxy: planning_value tasks tend to have longer plans; use 500 token baseline
            tokens = 500.0
            source = "proxy"
            n_proxy += 1

        if tokens <= 0:
            continue
        cei = planning_value / tokens
        cei_values.append(cei)
        task_details.append({
            "task_id": tid,
            "planning_value": round(planning_value, 4),
            "planner_tokens": round(tokens, 1),
            "token_source": source,
            "cei": round(cei, 6),
        })

    cei_values_arr = np.array(cei_values) if cei_values else np.array([float("nan")])

    return {
        "mean_cei": float(np.nanmean(cei_values_arr)),
        "median_cei": float(np.nanmedian(cei_values_arr)),
        "std_cei": float(np.nanstd(cei_values_arr)),
        "n_tasks": len(cei_values),
        "n_with_dialogue_tokens": n_with_tokens,
        "n_proxy_tokens": n_proxy,
        "note": (
            "Token counts from dialogue.jsonl planner messages (chars/4). "
            f"{n_proxy} tasks used 500-token proxy (no dialogue files found)."
        ),
        "per_task": sorted(task_details, key=lambda x: x["cei"], reverse=True),
    }


# ---------------------------------------------------------------------------
# Metric 2: Verification Accuracy (VA)
# ---------------------------------------------------------------------------

def _load_attestation(run_dir: str) -> str | None:
    """Return 'pass' or 'fail' from attestation.json, or None."""
    for subdir in ("submission", "workspace", "."):
        path = os.path.join(run_dir, subdir, "attestation.json")
        if os.path.exists(path):
            try:
                att = json.load(open(path))
                verdict = att.get("verdict", "").lower()
                if verdict in ("pass", "fail"):
                    return verdict
            except Exception:
                pass
    return None


def _load_score(run_dir: str) -> bool | None:
    """Return grader pass/fail from reports/score.json, or None."""
    path = os.path.join(run_dir, "reports", "score.json")
    if not os.path.exists(path):
        return None
    try:
        score = json.load(open(path))
        if "pass" in score:
            return bool(score["pass"])
        if "passed" in score and "total" in score:
            return score["passed"] == score["total"]
    except Exception:
        pass
    return None


def compute_va(runs: list[dict]) -> dict:
    """
    Verification Accuracy: how often does the verifier's attestation match the grader?
    Only meaningful for runs that have both attestation.json and score.json.
    """
    tp = fp = fn = tn = 0  # verifier-pass/grader-pass, vp/gf, vf/gp, vf/gf
    checked = 0
    task_dirs_checked: set[str] = set()

    def _check_run_dir(rdir: str) -> None:
        nonlocal tp, fp, fn, tn, checked
        att = _load_attestation(rdir)
        score = _load_score(rdir)
        if att is None or score is None:
            return
        checked += 1
        if att == "pass" and score:
            tp += 1
        elif att == "pass" and not score:
            fp += 1
        elif att == "fail" and score:
            fn += 1
        else:
            tn += 1

    # From JSON run records with run_dir
    for r in runs:
        run_dir = r.get("run_dir", "")
        if run_dir and run_dir not in task_dirs_checked:
            task_dirs_checked.add(run_dir)
            _check_run_dir(run_dir)

    # From task-named subdirs in RUNS_DIR
    if os.path.isdir(RUNS_DIR):
        for task_entry in os.listdir(RUNS_DIR):
            task_path = os.path.join(RUNS_DIR, task_entry)
            if not os.path.isdir(task_path):
                continue
            # Could be a run hash or a task name
            meta_path = os.path.join(task_path, "run_meta.json")
            if os.path.exists(meta_path):
                # Flat run directory (timestamped)
                if task_path not in task_dirs_checked:
                    task_dirs_checked.add(task_path)
                    _check_run_dir(task_path)
            else:
                # Task-named subdir containing run hashes
                for run_hash in os.listdir(task_path):
                    rpath = os.path.join(task_path, run_hash)
                    if os.path.isdir(rpath) and rpath not in task_dirs_checked:
                        task_dirs_checked.add(rpath)
                        _check_run_dir(rpath)

    total = tp + fp + fn + tn
    if total == 0:
        return {
            "va": None,
            "total_judgments": 0,
            "note": "No runs with both attestation.json and score.json found.",
        }

    va = (tp + tn) / total
    precision = tp / (tp + fp) if (tp + fp) > 0 else None
    recall = tp / (tp + fn) if (tp + fn) > 0 else None
    fnr = fn / (fn + tp) if (fn + tp) > 0 else None  # false negative rate (harmful)

    return {
        "va": round(va, 4),
        "true_positive": tp,
        "false_positive": fp,
        "false_negative": fn,
        "true_negative": tn,
        "total_judgments": total,
        "precision": round(precision, 4) if precision is not None else None,
        "recall": round(recall, 4) if recall is not None else None,
        "false_negative_rate": round(fnr, 4) if fnr is not None else None,
        "note": (
            "TP=verifier pass & grader pass; FP=verifier pass & grader fail; "
            "FN=verifier fail & grader pass (harmful); TN=verifier fail & grader fail."
        ),
    }


# ---------------------------------------------------------------------------
# Metric 3: Recovery Rate (RR)
# ---------------------------------------------------------------------------

def compute_rr(task_scores: dict[str, dict[str, float]]) -> dict:
    """
    RR = tasks where planner hurt AND full_score > 0 / tasks where planner hurt.
    Planner hurt: S_full < S_no_plan - RECOVERY_THRESHOLD.
    Recovery: S_full > 0 despite planner hurting.
    """
    planner_hurt: list[str] = []
    recovered: list[str] = []
    detail: list[dict] = []

    for tid, scores in task_scores.items():
        s_full = scores.get("full")
        s_no_plan = scores.get("team_no_plan")
        if s_full is None or s_no_plan is None:
            continue
        hurt = s_no_plan - s_full > RECOVERY_THRESHOLD
        if hurt:
            planner_hurt.append(tid)
            rec = s_full > 0.0
            if rec:
                recovered.append(tid)
            detail.append({
                "task_id": tid,
                "s_full": round(s_full, 4),
                "s_no_plan": round(s_no_plan, 4),
                "planning_delta": round(s_full - s_no_plan, 4),
                "recovered": rec,
            })

    n_hurt = len(planner_hurt)
    n_recovered = len(recovered)
    rr = n_recovered / n_hurt if n_hurt > 0 else None

    return {
        "rr": round(rr, 4) if rr is not None else None,
        "n_planner_hurt": n_hurt,
        "n_recovered": n_recovered,
        "threshold": RECOVERY_THRESHOLD,
        "note": (
            f"Planner hurt = S_full < S_no_plan by > {RECOVERY_THRESHOLD}. "
            "Recovery = S_full > 0 despite planner hurting."
        ),
        "per_task": sorted(detail, key=lambda x: x["planning_delta"]),
    }


# ---------------------------------------------------------------------------
# Metric 4: Empirical Capability Threshold (ECT)
# ---------------------------------------------------------------------------

def _find_positive_quadratic_root(coeffs: np.ndarray) -> float | None:
    """
    Given degree-2 polynomial coefficients [a, b, c] (highest first),
    return the smallest non-negative real root, or None.
    """
    a, b, c = coeffs
    if abs(a) < 1e-12:
        # Linear fallback
        if abs(b) < 1e-12:
            return None
        root = -c / b
        return float(root) if root >= 0 else None
    disc = b * b - 4 * a * c
    if disc < 0:
        return None
    sqrt_disc = math.sqrt(disc)
    roots = [(-b + sqrt_disc) / (2 * a), (-b - sqrt_disc) / (2 * a)]
    non_neg = [r for r in roots if r >= -0.01]  # slight tolerance
    if not non_neg:
        return None
    return float(min(non_neg, key=abs))


def _r_squared(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    return float(1 - ss_res / ss_tot) if ss_tot > 1e-12 else 0.0


def compute_ect(task_scores: dict[str, dict[str, float]]) -> dict:
    """
    Fit team_uplift = α·oracle² + β·oracle + γ across tasks.
    ECT = root of the quadratic (oracle score where uplift = 0).
    Bootstrap CI on ECT.
    """
    oracle_vals: list[float] = []
    uplift_vals: list[float] = []

    for tid, scores in task_scores.items():
        s_oracle = scores.get("oracle")
        s_restricted = scores.get("restricted")
        s_full = scores.get("full")
        if s_oracle is None or s_restricted is None or s_full is None:
            continue
        uplift = s_full - s_restricted
        oracle_vals.append(s_oracle)
        uplift_vals.append(uplift)

    if len(oracle_vals) < 5:
        return {
            "ect": None,
            "r_squared": None,
            "coefficients": None,
            "n_tasks": len(oracle_vals),
            "note": "Insufficient data for quadratic fit (need ≥ 5 tasks).",
        }

    x = np.array(oracle_vals)
    y = np.array(uplift_vals)

    # Fit
    coeffs = np.polyfit(x, y, deg=2)
    y_pred = np.polyval(coeffs, x)
    r2 = _r_squared(y, y_pred)
    ect = _find_positive_quadratic_root(coeffs)

    # Bootstrap CI
    rng = np.random.default_rng(RNG_SEED)
    n = len(x)
    boot_ects: list[float] = []
    for _ in range(BOOTSTRAP_N):
        idx = rng.integers(0, n, size=n)
        xb, yb = x[idx], y[idx]
        try:
            cb = np.polyfit(xb, yb, deg=2)
            root = _find_positive_quadratic_root(cb)
            if root is not None and 0 <= root <= 2.0:
                boot_ects.append(root)
        except Exception:
            pass

    ci_lo = ci_hi = None
    if boot_ects:
        ci_lo = float(np.percentile(boot_ects, 2.5))
        ci_hi = float(np.percentile(boot_ects, 97.5))

    return {
        "ect": round(ect, 4) if ect is not None else None,
        "ect_ci_95": [round(ci_lo, 4), round(ci_hi, 4)] if ci_lo is not None else None,
        "r_squared": round(r2, 4),
        "coefficients": {"alpha": round(float(coeffs[0]), 6),
                         "beta": round(float(coeffs[1]), 6),
                         "gamma": round(float(coeffs[2]), 6)},
        "n_tasks": len(oracle_vals),
        "n_bootstrap": len(boot_ects),
        "note": (
            "ECT = oracle score where quadratic team_uplift fit crosses zero. "
            "Below ECT, team helps; above ECT, team may hurt."
        ),
    }


# ---------------------------------------------------------------------------
# Metric 5: Archetype-Conditional TNI
# ---------------------------------------------------------------------------

def _get_archetype(task_id: str) -> str:
    """Map a task_id to an archetype string."""
    tid_upper = task_id.upper()
    # Try exact RDS prefix first
    for k, v in ARCHETYPE_MAP.items():
        if tid_upper.startswith(k):
            return v
    # Try category prefix (letters only before first digit or underscore)
    import re
    m = re.match(r"([A-Z]+)", tid_upper)
    if m:
        prefix = m.group(1)
        if prefix in ARCHETYPE_MAP:
            return ARCHETYPE_MAP[prefix]
    return "relay"


def compute_archetype_tni(task_scores: dict[str, dict[str, float]]) -> dict:
    """
    TNI = (S_full - S_restricted) / max(ε, S_oracle - S_restricted)
    Compute per archetype, reporting mean TNI, count, and task list.
    """
    EPS = 0.05
    archetype_data: dict[str, list[float]] = defaultdict(list)
    archetype_tasks: dict[str, list[str]] = defaultdict(list)
    skipped_narrow_gap = 0

    for tid, scores in task_scores.items():
        s_oracle = scores.get("oracle")
        s_restricted = scores.get("restricted")
        s_full = scores.get("full")
        if s_oracle is None or s_restricted is None or s_full is None:
            continue
        gap = s_oracle - s_restricted
        if abs(gap) < EPS:
            skipped_narrow_gap += 1
            continue
        raw_tni = (s_full - s_restricted) / gap
        tni = max(-2.0, min(2.0, raw_tni))
        arch = _get_archetype(tid)
        archetype_data[arch].append(tni)
        archetype_tasks[arch].append(tid)

    per_archetype: list[dict] = []
    for arch in sorted(archetype_data.keys()):
        vals = archetype_data[arch]
        per_archetype.append({
            "archetype": arch,
            "mean_tni": round(float(np.mean(vals)), 4),
            "median_tni": round(float(np.median(vals)), 4),
            "std_tni": round(float(np.std(vals)), 4),
            "n_tasks": len(vals),
            "tasks": sorted(archetype_tasks[arch]),
        })

    all_tni = [v for vals in archetype_data.values() for v in vals]
    return {
        "overall_mean_tni": round(float(np.mean(all_tni)), 4) if all_tni else None,
        "n_tasks_included": len(all_tni),
        "n_tasks_skipped_narrow_gap": skipped_narrow_gap,
        "eps_threshold": EPS,
        "per_archetype": per_archetype,
        "note": (
            "RDS* tasks mapped to RDS archetypes; others by category prefix. "
            "Narrow-gap tasks (oracle-restricted < eps) excluded from TNI."
        ),
    }


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def _fmt(v: float | None, decimals: int = 4) -> str:
    if v is None:
        return "N/A"
    return f"{v:.{decimals}f}"


def build_latex_table(results: dict) -> str:
    cei = results["communication_efficiency_index"]
    va = results["verification_accuracy"]
    rr = results["recovery_rate"]
    ect = results["empirical_capability_threshold"]
    arch = results["archetype_conditional_tni"]

    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{Advanced TeamBench Metrics}",
        r"\label{tab:advanced_metrics}",
        r"\begin{tabular}{lll}",
        r"\toprule",
        r"\textbf{Metric} & \textbf{Value} & \textbf{Note} \\",
        r"\midrule",
        # CEI
        rf"CEI (mean) & {_fmt(cei.get('mean_cei'), 5)} & "
        rf"$n={cei.get('n_tasks', 0)}$ tasks, "
        rf"{cei.get('n_with_dialogue_tokens', 0)} w/ dialogue tokens \\",
        # VA
        rf"Verification Accuracy & {_fmt(va.get('va'))} & "
        rf"$n={va.get('total_judgments', 0)}$ judgments, "
        rf"FNR={_fmt(va.get('false_negative_rate'))} \\",
        # RR
        rf"Recovery Rate & {_fmt(rr.get('rr'))} & "
        rf"{rr.get('n_recovered', 0)}/{rr.get('n_planner_hurt', 0)} tasks \\",
        # ECT
    ]
    ect_val = _fmt(ect.get("ect"))
    ect_ci = ect.get("ect_ci_95")
    ect_ci_str = (
        f"[{_fmt(ect_ci[0])}, {_fmt(ect_ci[1])}]"
        if ect_ci else "N/A"
    )
    lines.append(
        rf"ECT & {ect_val} & "
        rf"95\% CI {ect_ci_str}, $R^2={_fmt(ect.get('r_squared'))}$ \\"
    )
    # Archetype TNI
    lines.append(r"\midrule")
    lines.append(r"\multicolumn{3}{l}{\textit{Archetype-Conditional TNI}} \\")
    for entry in arch.get("per_archetype", []):
        lines.append(
            rf"\quad {entry['archetype']} & "
            rf"{_fmt(entry['mean_tni'])} $\pm$ {_fmt(entry['std_tni'])} & "
            rf"$n={entry['n_tasks']}$ tasks \\"
        )
    lines += [
        r"\bottomrule",
        r"\end{tabular}",
        r"\end{table}",
    ]
    return "\n".join(lines)


def print_summary(results: dict) -> None:
    print("\n" + "=" * 60)
    print("  TeamBench Advanced Metrics Summary")
    print("=" * 60)

    cei = results["communication_efficiency_index"]
    print(f"\n1. Communication Efficiency Index (CEI)")
    print(f"   Mean CEI : {_fmt(cei.get('mean_cei'), 6)}")
    print(f"   Median   : {_fmt(cei.get('median_cei'), 6)}")
    print(f"   Tasks    : {cei.get('n_tasks', 0)} "
          f"({cei.get('n_with_dialogue_tokens', 0)} w/ dialogue files, "
          f"{cei.get('n_proxy_tokens', 0)} proxied)")

    va = results["verification_accuracy"]
    print(f"\n2. Verification Accuracy (VA)")
    if va.get("va") is not None:
        print(f"   VA       : {_fmt(va.get('va'))}")
        print(f"   TP/FP/FN/TN: {va['true_positive']}/{va['false_positive']}/"
              f"{va['false_negative']}/{va['true_negative']}")
        print(f"   FNR      : {_fmt(va.get('false_negative_rate'))}  "
              f"(false negative rate — harmful misses)")
        print(f"   Judgments: {va.get('total_judgments', 0)}")
    else:
        print(f"   {va.get('note')}")

    rr = results["recovery_rate"]
    print(f"\n3. Recovery Rate (RR)")
    print(f"   RR       : {_fmt(rr.get('rr'))}")
    print(f"   Hurt/Total: {rr.get('n_planner_hurt', 0)} tasks where planner hurt")
    print(f"   Recovered: {rr.get('n_recovered', 0)} tasks still passed despite planner")

    ect = results["empirical_capability_threshold"]
    print(f"\n4. Empirical Capability Threshold (ECT)")
    if ect.get("ect") is not None:
        ci = ect.get("ect_ci_95")
        ci_str = f"[{_fmt(ci[0])}, {_fmt(ci[1])}]" if ci else "N/A"
        print(f"   ECT      : {_fmt(ect.get('ect'))}  95% CI {ci_str}")
        print(f"   R²       : {_fmt(ect.get('r_squared'))}")
        c = ect.get("coefficients", {})
        print(f"   Fit      : {c.get('alpha', 0):.4f}·x² + "
              f"{c.get('beta', 0):.4f}·x + {c.get('gamma', 0):.4f}")
        print(f"   Tasks    : {ect.get('n_tasks', 0)}")
    else:
        print(f"   {ect.get('note')}")

    arch = results["archetype_conditional_tni"]
    print(f"\n5. Archetype-Conditional TNI")
    print(f"   Overall mean TNI: {_fmt(arch.get('overall_mean_tni'))}")
    for entry in arch.get("per_archetype", []):
        print(f"   {entry['archetype']:<14} : "
              f"TNI={_fmt(entry['mean_tni'])}±{_fmt(entry['std_tni'])}  "
              f"(n={entry['n_tasks']})")
    print(f"   Skipped (narrow gap): {arch.get('n_tasks_skipped_narrow_gap', 0)}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("Loading ablation data...", file=sys.stderr)
    runs = load_all_runs()
    print(f"  Loaded {len(runs)} unique run records.", file=sys.stderr)

    task_scores = aggregate_by_task(runs)
    print(f"  Aggregated scores for {len(task_scores)} tasks.", file=sys.stderr)

    print("Computing CEI...", file=sys.stderr)
    cei = compute_cei(runs, task_scores)

    print("Computing VA...", file=sys.stderr)
    va = compute_va(runs)

    print("Computing RR...", file=sys.stderr)
    rr = compute_rr(task_scores)

    print("Computing ECT...", file=sys.stderr)
    ect = compute_ect(task_scores)

    print("Computing Archetype-Conditional TNI...", file=sys.stderr)
    arch_tni = compute_archetype_tni(task_scores)

    results = {
        "communication_efficiency_index": cei,
        "verification_accuracy": va,
        "recovery_rate": rr,
        "empirical_capability_threshold": ect,
        "archetype_conditional_tni": arch_tni,
        "meta": {
            "n_runs_loaded": len(runs),
            "n_tasks_aggregated": len(task_scores),
        },
    }

    # Write JSON
    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w") as fh:
        json.dump(results, fh, indent=2)
    print(f"\nWrote {OUTPUT_JSON}", file=sys.stderr)

    # Write LaTeX
    tex = build_latex_table(results)
    with open(OUTPUT_TEX, "w") as fh:
        fh.write(tex + "\n")
    print(f"Wrote {OUTPUT_TEX}", file=sys.stderr)

    # Print summary to stdout
    print_summary(results)


if __name__ == "__main__":
    os.chdir(os.path.join(os.path.dirname(__file__), ".."))
    main()
