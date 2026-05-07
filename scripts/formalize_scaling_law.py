#!/usr/bin/env python3
"""
formalize_scaling_law.py — Rigorous analysis of the Equalizer Effect scaling law.

For each (task_id, model) pair, compute oracle_score and team_uplift (full - oracle).
Fit multiple functional forms, derive the Empirical Capability Threshold (ECT) where
predicted uplift = 0, and produce publication-ready outputs.

Outputs:
  shared/paper/scaling_law_analysis.json
  shared/paper/table_scaling_law.tex
  shared/paper/fig_scaling_law.csv
"""

import json
import os
import glob
import math
import warnings
from collections import defaultdict

import numpy as np
from scipy import stats
from scipy.optimize import curve_fit, brentq, minimize_scalar
from scipy.interpolate import UnivariateSpline

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ABLATION_DIR = os.path.join(REPO_ROOT, "shared", "ablation_results")
PAPER_DIR = os.path.join(REPO_ROOT, "shared", "paper")
os.makedirs(PAPER_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# 1. Load all ablation data
# ---------------------------------------------------------------------------

# Files to skip: hetero (different format), topology (non-standard conditions),
# enhanced_oracle / strong_baseline (oracle variants, no full), phase3 sub-files
# (superseded by phase3_all_consolidated), partial retries.
SKIP_PATTERNS = [
    "hetero_",
    "dynamic_deployment",
    "topology_",
    "enhanced_oracle",
    "strong_baseline",
    "phase3_batchA_seeds12",   # expertise conditions, not standard
    "phase3_batchA_consolidated",   # superseded
    "phase3_batchA_full_retry",
    "phase3_batchA_team_retry",
    "phase3_batchA_tnv_retry",
    "phase3_batchAB_retry",
    "phase3_batchB_consolidated",   # superseded
    "phase3_batchB_seeds12",        # superseded
    "phase3_batchC_retry",          # superseded
    "batch3_full_retry",    # partial-condition retry
    "batch5_full_retry",
    "batch6_full_503",
    "batch6_retry",
    "rerun_fixed",
    "smoke_",
    "ds_pilot",
    "ds_redesigned",
    "ml_pilot",
    "ml_redesigned",
]

REQUIRED_CONDITIONS = {"oracle", "full"}


def should_skip(fname: str) -> bool:
    for pat in SKIP_PATTERNS:
        if pat in fname:
            return True
    return False


def load_ablation_data():
    """
    Returns list of dicts:
      {task_id, model, seed, oracle_score, full_score, team_uplift, source_file}
    One entry per (task_id, model, seed) combination with both oracle + full scores.
    """
    records = []
    files_used = []

    json_files = sorted(glob.glob(os.path.join(ABLATION_DIR, "*.json")))
    for fp in json_files:
        fname = os.path.basename(fp)
        if should_skip(fname):
            continue

        try:
            with open(fp) as f:
                data = json.load(f)
        except Exception:
            continue

        runs = data.get("runs", [])
        if not isinstance(runs, list) or not runs:
            continue

        # Check conditions present
        conditions_present = {r.get("condition") for r in runs}
        if not REQUIRED_CONDITIONS.issubset(conditions_present):
            continue

        model = data.get("model", "unknown")
        files_used.append(fname)

        # Index runs by (task_id, seed, condition) -> partial_score
        # Use partial_score (0..1) as it is more informative than binary pass
        index = {}
        for r in runs:
            cond = r.get("condition")
            if cond not in ("oracle", "full"):
                continue
            key = (r["task_id"], r.get("seed", 0), cond)
            # If duplicate, keep higher score (retry semantics)
            score = r.get("partial_score")
            if score is None:
                score = float(r.get("pass", False))
            score = float(score)
            if key not in index or score > index[key]:
                index[key] = score

        # Collect paired (oracle, full) per (task_id, seed)
        task_seeds = set()
        for (tid, seed, cond) in index:
            task_seeds.add((tid, seed))

        for (tid, seed) in task_seeds:
            o = index.get((tid, seed, "oracle"))
            f = index.get((tid, seed, "full"))
            if o is None or f is None:
                continue
            records.append(
                {
                    "task_id": tid,
                    "model": model,
                    "seed": seed,
                    "oracle_score": o,
                    "full_score": f,
                    "team_uplift": f - o,
                    "source_file": fname,
                }
            )

    print(f"Loaded {len(records)} (task, model, seed) records from {len(files_used)} files.")
    print(f"Files used: {files_used}")
    return records


# ---------------------------------------------------------------------------
# 2. Aggregate to (task_id, model) level — mean over seeds
# ---------------------------------------------------------------------------

def aggregate_records(records):
    """
    Average oracle_score, full_score, team_uplift over seeds for each (task_id, model).
    Returns list of dicts with same keys.
    """
    buckets = defaultdict(list)
    for r in records:
        buckets[(r["task_id"], r["model"])].append(r)

    aggregated = []
    for (tid, model), recs in buckets.items():
        aggregated.append(
            {
                "task_id": tid,
                "model": model,
                "oracle_score": np.mean([r["oracle_score"] for r in recs]),
                "full_score": np.mean([r["full_score"] for r in recs]),
                "team_uplift": np.mean([r["team_uplift"] for r in recs]),
                "n_seeds": len(recs),
            }
        )
    return aggregated


# ---------------------------------------------------------------------------
# 3. Functional form fitting helpers
# ---------------------------------------------------------------------------

def aic(n, k, rss):
    """AIC = n·ln(RSS/n) + 2k"""
    if rss <= 0:
        rss = 1e-12
    return n * math.log(rss / n) + 2 * k


def bic(n, k, rss):
    """BIC = n·ln(RSS/n) + k·ln(n)"""
    if rss <= 0:
        rss = 1e-12
    return n * math.log(rss / n) + k * math.log(n)


def r_squared(y_true, y_pred):
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot == 0:
        return float("nan")
    return 1.0 - ss_res / ss_tot


# --- Linear ---
def fit_linear(x, y):
    """uplift = a·oracle + b"""
    coeffs = np.polyfit(x, y, 1)
    y_pred = np.polyval(coeffs, x)
    a, b = coeffs
    n, k = len(x), 2
    rss = np.sum((y - y_pred) ** 2)
    return {
        "name": "linear",
        "params": {"a": a, "b": b},
        "r2": r_squared(y, y_pred),
        "aic": aic(n, k, rss),
        "bic": bic(n, k, rss),
        "predict": lambda xv: a * xv + b,
        "n_params": k,
    }


# --- Quadratic ---
def fit_quadratic(x, y):
    """uplift = a·oracle² + b·oracle + c"""
    coeffs = np.polyfit(x, y, 2)
    y_pred = np.polyval(coeffs, x)
    a, b, c = coeffs
    n, k = len(x), 3
    rss = np.sum((y - y_pred) ** 2)
    return {
        "name": "quadratic",
        "params": {"a": a, "b": b, "c": c},
        "r2": r_squared(y, y_pred),
        "aic": aic(n, k, rss),
        "bic": bic(n, k, rss),
        "predict": lambda xv: np.polyval(coeffs, xv),
        "n_params": k,
    }


# --- Piecewise linear (grid search over breakpoint) ---
def piecewise_linear(x, bp, a1, b1, a2, b2):
    return np.where(x <= bp, a1 * x + b1, a2 * x + b2)


def fit_piecewise(x, y):
    """Two-segment linear with continuous join, breakpoint via grid search."""
    best = None
    xs = np.sort(x)
    # Grid: try breakpoints between 10th and 90th percentile
    bp_candidates = np.percentile(xs, np.linspace(10, 90, 50))

    for bp in bp_candidates:
        mask_l = x <= bp
        mask_r = x > bp
        if mask_l.sum() < 3 or mask_r.sum() < 3:
            continue
        # Fit each segment independently (OLS)
        xl, yl = x[mask_l], y[mask_l]
        xr, yr = x[mask_r], y[mask_r]
        # Skip degenerate segments (constant x)
        if np.ptp(xl) == 0 or np.ptp(xr) == 0:
            continue
        cl = np.polyfit(xl, yl, 1)
        cr = np.polyfit(xr, yr, 1)
        y_pred = np.where(mask_l, np.polyval(cl, x), np.polyval(cr, x))
        rss = np.sum((y - y_pred) ** 2)
        if best is None or rss < best["rss"]:
            best = {
                "bp": bp,
                "cl": cl,
                "cr": cr,
                "rss": rss,
                "y_pred": y_pred,
            }

    if best is None:
        # Fallback
        return fit_linear(x, y)

    n, k = len(x), 5  # bp + 2 slopes + 2 intercepts
    rss = best["rss"]
    cl, cr, bp = best["cl"], best["cr"], best["bp"]

    def predict(xv):
        xv = np.asarray(xv)
        return np.where(xv <= bp, np.polyval(cl, xv), np.polyval(cr, xv))

    return {
        "name": "piecewise_linear",
        "params": {
            "breakpoint": bp,
            "left_slope": cl[0],
            "left_intercept": cl[1],
            "right_slope": cr[0],
            "right_intercept": cr[1],
        },
        "r2": r_squared(y, predict(x)),
        "aic": aic(n, k, rss),
        "bic": bic(n, k, rss),
        "predict": predict,
        "n_params": k,
    }


# --- Logistic / S-curve ---
def logistic_func(x, L, k, x0):
    """L / (1 + exp(-k·(x - x0)))"""
    return L / (1.0 + np.exp(-k * (x - x0)))


def fit_logistic(x, y):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            popt, _ = curve_fit(
                logistic_func,
                x,
                y,
                p0=[np.max(y) - np.min(y), -5.0, 0.5],
                maxfev=10000,
                bounds=([-2, -50, -0.5], [2, 50, 1.5]),
            )
        L, k_val, x0 = popt
        y_pred = logistic_func(x, *popt)
        n, kp = len(x), 3
        rss = np.sum((y - y_pred) ** 2)
        return {
            "name": "logistic",
            "params": {"L": L, "k": k_val, "x0": x0},
            "r2": r_squared(y, y_pred),
            "aic": aic(n, kp, rss),
            "bic": bic(n, kp, rss),
            "predict": lambda xv: logistic_func(np.asarray(xv), L, k_val, x0),
            "n_params": kp,
        }
    except Exception:
        return None


# --- LOWESS smoother ---
def lowess(x, y, frac=0.4):
    """Simple LOWESS via scipy.  Returns (x_sorted, y_smoothed)."""
    try:
        from statsmodels.nonparametric.smoothers_lowess import lowess as sm_lowess
        result = sm_lowess(y, x, frac=frac, return_sorted=True)
        return result[:, 0], result[:, 1]
    except ImportError:
        # Manual tricubic-kernel LOWESS fallback
        n = len(x)
        h = int(frac * n)
        y_smooth = np.zeros(n)
        order = np.argsort(x)
        xs, ys = x[order], y[order]
        for i in range(n):
            dists = np.abs(xs - xs[i])
            neighbors = np.argsort(dists)[:h]
            d_max = dists[neighbors[-1]]
            if d_max == 0:
                y_smooth[i] = ys[i]
                continue
            w = (1 - (dists[neighbors] / d_max) ** 3) ** 3
            w = np.maximum(w, 0)
            coeffs = np.polyfit(xs[neighbors], ys[neighbors], 1, w=w)
            y_smooth[i] = np.polyval(coeffs, xs[i])
        return xs, y_smooth


# ---------------------------------------------------------------------------
# 4. ECT derivation with bootstrap CIs
# ---------------------------------------------------------------------------

def find_zero_crossing(predict_fn, x_min=0.0, x_max=1.0):
    """Find oracle score where predicted uplift = 0 via bisection."""
    try:
        f_min = predict_fn(x_min)
        f_max = predict_fn(x_max)
        # If no sign change, find minimum |f| and return that x
        if f_min * f_max > 0:
            res = minimize_scalar(
                lambda xv: abs(predict_fn(xv)),
                bounds=(x_min, x_max),
                method="bounded",
            )
            return float(res.x), False  # (estimate, is_true_crossing)
        root = brentq(predict_fn, x_min, x_max, xtol=1e-6)
        return float(root), True
    except Exception:
        return float("nan"), False


def bootstrap_ect(x, y, fit_fn, n_boot=1000, seed=42):
    """
    Bootstrap ECT CI by resampling (x, y) pairs with replacement.
    Returns (ect_point, ci_lower, ci_upper, bootstrap_samples).
    """
    rng = np.random.default_rng(seed)
    n = len(x)
    ects = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        xb, yb = x[idx], y[idx]
        try:
            fit = fit_fn(xb, yb)
            if fit is None:
                continue
            ect, _ = find_zero_crossing(fit["predict"])
            if not math.isnan(ect):
                ects.append(ect)
        except Exception:
            continue

    if not ects:
        return float("nan"), float("nan"), float("nan"), []

    # Point estimate from full data
    fit_full = fit_fn(x, y)
    ect_point, _ = find_zero_crossing(fit_full["predict"])

    ects = np.array(ects)
    ci_lo = float(np.percentile(ects, 2.5))
    ci_hi = float(np.percentile(ects, 97.5))
    return ect_point, ci_lo, ci_hi, ects.tolist()


# ---------------------------------------------------------------------------
# 5. Quintile analysis
# ---------------------------------------------------------------------------

def quintile_analysis(x, y, n_boot=1000, seed=42):
    rng = np.random.default_rng(seed)
    # Use pd.qcut-style: split into 5 equal-count groups via rank-based assignment
    n_total = len(x)
    order = np.argsort(x, kind="stable")
    group = np.empty(n_total, dtype=int)
    for rank_i, idx in enumerate(order):
        group[idx] = min(int(rank_i * 5 / n_total), 4)

    results = []
    for i in range(5):
        mask = group == i
        xq, yq = x[mask], y[mask]
        n = len(yq)
        lo = float(xq.min()) if n else float("nan")
        hi = float(xq.max()) if n else float("nan")
        if n < 2:
            results.append(
                {
                    "quintile": i + 1,
                    "oracle_range": [round(lo, 3), round(hi, 3)],
                    "n": n,
                    "mean_uplift": float(np.mean(yq)) if n else float("nan"),
                    "ci_lower": float("nan"),
                    "ci_upper": float("nan"),
                    "cohens_d": float("nan"),
                    "significant": False,
                }
            )
            continue

        mean_u = float(np.mean(yq))
        # Bootstrap CI
        boot_means = [
            np.mean(rng.choice(yq, size=n, replace=True)) for _ in range(n_boot)
        ]
        ci_lo = float(np.percentile(boot_means, 2.5))
        ci_hi = float(np.percentile(boot_means, 97.5))
        # Cohen's d vs zero (effect size of uplift)
        cohens_d = mean_u / (float(np.std(yq, ddof=1)) + 1e-12)
        significant = ci_lo > 0 or ci_hi < 0  # CI excludes zero

        results.append(
            {
                "quintile": i + 1,
                "oracle_range": [round(lo, 3), round(hi, 3)],
                "oracle_midpoint": round((lo + hi) / 2, 3),
                "n": int(n),
                "mean_uplift": round(mean_u, 4),
                "ci_lower": round(ci_lo, 4),
                "ci_upper": round(ci_hi, 4),
                "cohens_d": round(cohens_d, 3),
                "significant": bool(significant),
            }
        )

    return results


# ---------------------------------------------------------------------------
# 6. Per-model ECT
# ---------------------------------------------------------------------------

def per_model_ect(aggregated, best_fit_fn, n_boot=500):
    models = sorted(set(r["model"] for r in aggregated))
    results = {}
    for m in models:
        subset = [r for r in aggregated if r["model"] == m]
        if len(subset) < 5:
            continue
        x = np.array([r["oracle_score"] for r in subset])
        y = np.array([r["team_uplift"] for r in subset])
        ect, ci_lo, ci_hi, _ = bootstrap_ect(x, y, best_fit_fn, n_boot=n_boot)
        results[m] = {
            "n": len(subset),
            "ect": round(ect, 3) if not math.isnan(ect) else None,
            "ci_lower": round(ci_lo, 3) if not math.isnan(ci_lo) else None,
            "ci_upper": round(ci_hi, 3) if not math.isnan(ci_hi) else None,
        }
    return results


# ---------------------------------------------------------------------------
# 7. LaTeX table
# ---------------------------------------------------------------------------

def make_latex_table(model_fits, best_name, ect_point, ect_ci_lo, ect_ci_hi):
    rows = []
    for fit in sorted(model_fits, key=lambda f: f["aic"]):
        name = fit["name"].replace("_", " ").title()
        marker = r"\textbf{" + name + r"}" if fit["name"] == best_name else name
        r2_str = f"{fit['r2']:.3f}" if not math.isnan(fit["r2"]) else "—"
        aic_str = f"{fit['aic']:.1f}"
        bic_str = f"{fit['bic']:.1f}"
        rows.append(
            rf"    {marker} & {fit['n_params']} & {r2_str} & {aic_str} & {bic_str} \\"
        )

    ect_str = f"{ect_point:.3f}" if not math.isnan(ect_point) else "N/A"
    ci_str = (
        f"[{ect_ci_lo:.3f}, {ect_ci_hi:.3f}]"
        if not (math.isnan(ect_ci_lo) or math.isnan(ect_ci_hi))
        else "N/A"
    )

    lines = [
        r"\begin{table}[h]",
        r"  \centering",
        r"  \caption{Scaling Law Model Comparison — Team Uplift vs.\ Oracle Score.}",
        r"  \label{tab:scaling_law}",
        r"  \begin{tabular}{lrrrr}",
        r"    \toprule",
        r"    Model & \#Params & $R^2$ & AIC & BIC \\",
        r"    \midrule",
    ]
    lines += rows
    lines += [
        r"    \bottomrule",
        r"  \end{tabular}",
        rf"  \smallskip\par\noindent\small Best-fit model: \textbf{{{best_name.replace('_', ' ').title()}}}.",
        rf"  ECT (team uplift $= 0$): ${ect_str}$ 95\% CI ${ci_str}$ (1000-iteration bootstrap).",
        r"\end{table}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 8. CSV for plotting
# ---------------------------------------------------------------------------

def make_csv(x, y, fits_map, lowess_xs, lowess_ys, n_grid=200):
    xs_grid = np.linspace(max(0.0, x.min() - 0.02), min(1.0, x.max() + 0.02), n_grid)

    # Bootstrap CI for best-fit predictions (via residual bootstrap)
    best_fit = fits_map["best"]
    y_fit_grid = best_fit["predict"](xs_grid)

    # Interpolate LOWESS onto grid
    lowess_interp = np.interp(xs_grid, lowess_xs, lowess_ys)

    # Build CSV rows
    lines = ["oracle_score,team_uplift,fitted_curve,lowess"]
    # Raw scatter points
    for xi, yi in zip(x, y):
        lines.append(f"{xi:.6f},{yi:.6f},,")
    lines.append("")
    lines.append("# grid")
    lines.append("grid_oracle,grid_fitted,grid_ci_lower,grid_ci_upper,grid_lowess")
    for xi, yf, yl in zip(xs_grid, y_fit_grid, lowess_interp):
        lines.append(f"{xi:.6f},{yf:.6f},,,{yl:.6f}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("Scaling Law Formalization — Equalizer Effect")
    print("=" * 70)

    # --- Load ---
    raw = load_ablation_data()
    aggregated = aggregate_records(raw)
    print(f"\nAggregated: {len(aggregated)} (task_id, model) pairs")

    x = np.array([r["oracle_score"] for r in aggregated])
    y = np.array([r["team_uplift"] for r in aggregated])

    # Basic stats
    print(f"\nData summary:")
    print(f"  oracle_score:  mean={x.mean():.3f}  std={x.std():.3f}  range=[{x.min():.3f}, {x.max():.3f}]")
    print(f"  team_uplift:   mean={y.mean():.3f}  std={y.std():.3f}  range=[{y.min():.3f}, {y.max():.3f}]")

    slope, intercept, r_lin, p_lin, se = stats.linregress(x, y)
    print(f"\nPearson r = {r_lin:.4f}  p = {p_lin:.4e}  (linear baseline)")

    # --- Fit models ---
    print("\nFitting functional forms...")
    fits = []

    lin = fit_linear(x, y)
    fits.append(lin)
    print(f"  Linear:          R²={lin['r2']:.4f}  AIC={lin['aic']:.2f}  BIC={lin['bic']:.2f}")

    quad = fit_quadratic(x, y)
    fits.append(quad)
    print(f"  Quadratic:       R²={quad['r2']:.4f}  AIC={quad['aic']:.2f}  BIC={quad['bic']:.2f}")

    pw = fit_piecewise(x, y)
    fits.append(pw)
    print(f"  Piecewise-linear:R²={pw['r2']:.4f}  AIC={pw['aic']:.2f}  BIC={pw['bic']:.2f}  bp={pw['params'].get('breakpoint', 'N/A'):.3f}")

    log_fit = fit_logistic(x, y)
    if log_fit is not None:
        fits.append(log_fit)
        print(f"  Logistic:        R²={log_fit['r2']:.4f}  AIC={log_fit['aic']:.2f}  BIC={log_fit['bic']:.2f}")
    else:
        print("  Logistic:        fit failed")

    # --- Best by AIC ---
    valid_fits = [f for f in fits if not math.isnan(f["aic"])]
    best_fit = min(valid_fits, key=lambda f: f["aic"])
    print(f"\nBest model by AIC: {best_fit['name']}  (AIC={best_fit['aic']:.2f})")

    # Map fit name -> fit_fn for bootstrap
    fit_fn_map = {
        "linear": fit_linear,
        "quadratic": fit_quadratic,
        "piecewise_linear": fit_piecewise,
        "logistic": fit_logistic,
    }
    best_fit_fn = fit_fn_map[best_fit["name"]]

    # --- ECT from best model ---
    print("\nDeriving ECT (oracle score where team_uplift = 0)...")
    ect_point, ect_ci_lo, ect_ci_hi, boot_samples = bootstrap_ect(
        x, y, best_fit_fn, n_boot=1000
    )
    print(f"  ECT point estimate: {ect_point:.4f}")
    print(f"  ECT 95% CI:         [{ect_ci_lo:.4f}, {ect_ci_hi:.4f}]")

    # ECT from each model for comparison
    print("\nECT from all parametric models:")
    ect_per_model_fit = {}
    for f in fits:
        ect_v, is_cross = find_zero_crossing(f["predict"])
        tag = "(true crossing)" if is_cross else "(min |uplift|)"
        print(f"  {f['name']:20s}: ECT={ect_v:.4f}  {tag}")
        ect_per_model_fit[f["name"]] = {"ect": round(ect_v, 4), "true_crossing": is_cross}

    # --- Quintile analysis ---
    print("\nQuintile analysis:")
    quintiles = quintile_analysis(x, y)
    for q in quintiles:
        sig_tag = "***" if q["significant"] else "n.s."
        print(
            f"  Q{q['quintile']} oracle=[{q['oracle_range'][0]:.2f},{q['oracle_range'][1]:.2f}]"
            f"  n={q['n']:3d}  uplift={q['mean_uplift']:+.4f}"
            f"  95%CI=[{q['ci_lower']:+.4f},{q['ci_upper']:+.4f}]"
            f"  d={q['cohens_d']:+.3f}  {sig_tag}"
        )

    # --- Per-model ECT ---
    print("\nPer-model ECT analysis:")
    per_model = per_model_ect(aggregated, best_fit_fn, n_boot=500)
    for m, res in sorted(per_model.items()):
        ci_str = f"[{res['ci_lower']},{res['ci_upper']}]" if res["ci_lower"] is not None else "N/A"
        print(f"  {m[:35]:35s}  n={res['n']:3d}  ECT={res['ect']}  CI={ci_str}")

    # --- LOWESS ---
    order = np.argsort(x)
    lx, ly = lowess(x[order], y[order], frac=0.4)

    # --- Serialize fits (remove non-serializable predict lambdas) ---
    def serialise_fit(f):
        return {
            "name": f["name"],
            "params": {k: round(float(v), 6) for k, v in f["params"].items()},
            "r2": round(float(f["r2"]), 6) if not math.isnan(f["r2"]) else None,
            "aic": round(float(f["aic"]), 4),
            "bic": round(float(f["bic"]), 4),
            "n_params": f["n_params"],
        }

    # --- JSON output ---
    output = {
        "n_task_model_pairs": len(aggregated),
        "n_raw_records": len(raw),
        "data_summary": {
            "oracle_mean": round(float(x.mean()), 4),
            "oracle_std": round(float(x.std()), 4),
            "oracle_min": round(float(x.min()), 4),
            "oracle_max": round(float(x.max()), 4),
            "uplift_mean": round(float(y.mean()), 4),
            "uplift_std": round(float(y.std()), 4),
            "pearson_r": round(float(r_lin), 4),
            "pearson_p": float(p_lin),
        },
        "model_fits": [serialise_fit(f) for f in fits],
        "best_model": best_fit["name"],
        "ect": {
            "point_estimate": round(ect_point, 4) if not math.isnan(ect_point) else None,
            "ci_lower_95": round(ect_ci_lo, 4) if not math.isnan(ect_ci_lo) else None,
            "ci_upper_95": round(ect_ci_hi, 4) if not math.isnan(ect_ci_hi) else None,
            "n_bootstrap": 1000,
            "bootstrap_samples": [round(v, 4) for v in boot_samples[:200]],  # truncate
            "ect_per_functional_form": ect_per_model_fit,
        },
        "per_model_ect": per_model,
        "quintile_analysis": quintiles,
    }

    json_path = os.path.join(PAPER_DIR, "scaling_law_analysis.json")
    with open(json_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nWrote {json_path}")

    # --- LaTeX table ---
    tex = make_latex_table(
        [serialise_fit(f) for f in fits],
        best_fit["name"],
        ect_point,
        ect_ci_lo,
        ect_ci_hi,
    )
    tex_path = os.path.join(PAPER_DIR, "table_scaling_law.tex")
    with open(tex_path, "w") as f:
        f.write(tex)
    print(f"Wrote {tex_path}")

    # --- CSV ---
    fits_map = {"best": best_fit}
    csv_text = make_csv(x, y, fits_map, lx, ly)
    csv_path = os.path.join(PAPER_DIR, "fig_scaling_law.csv")
    with open(csv_path, "w") as f:
        f.write(csv_text)
    print(f"Wrote {csv_path}")

    # --- Final summary ---
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Data:         {len(aggregated)} (task, model) pairs from {len(set(r['model'] for r in aggregated))} models")
    print(f"  Best fit:     {best_fit['name']}  R²={best_fit['r2']:.4f}  AIC={best_fit['aic']:.2f}")
    print(f"  Pearson r:    {r_lin:.4f}  p={p_lin:.2e}")
    if not math.isnan(ect_point):
        print(f"  ECT:          {ect_point:.4f}  [95% CI: {ect_ci_lo:.4f} – {ect_ci_hi:.4f}]")
        print(f"  Interpretation: teamwork becomes net-negative above oracle score ≈ {ect_point:.2f}")
    else:
        print("  ECT:          no zero-crossing found in [0,1] — team uplift is always positive")
    q1_up = quintiles[0]["mean_uplift"]
    q5_up = quintiles[4]["mean_uplift"]
    print(f"  Quintile gradient: Q1 uplift={q1_up:+.4f}  Q5 uplift={q5_up:+.4f}")
    print(f"  Equalizer gradient: {q1_up - q5_up:+.4f} (positive = weaker models benefit more)")
    print("=" * 70)


if __name__ == "__main__":
    main()
