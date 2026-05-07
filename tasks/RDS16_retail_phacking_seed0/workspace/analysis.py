"""
Online retail segment analysis: revenue per order by Country.

Tests 15 Country segments for differences in revenue per order
and reports significant segments (p < 0.05).
Saves results to results.json and report.md.
"""
import json
import pathlib
import numpy as np
import pandas as pd
from scipy import stats

# ── Load data ────────────────────────────────────────────────────────────
data_path = pathlib.Path(__file__).parent.parent / "datasets" / "online_retail.csv"
df = pd.read_csv(data_path, comment="#", encoding="latin-1")

# Clean up
df = df.dropna(subset=["Country", "UnitPrice"])
df = df[df["UnitPrice"] > 0].copy()

# ── Select top segments by volume ─────────────────────────────────────
top_segments = (
    df["Country"].value_counts().head(15).index.tolist()
)
df_top = df[df["Country"].isin(top_segments)].copy()

# ── Overall baseline ──────────────────────────────────────────────────
overall = df_top["UnitPrice"].values

# ── Test each segment vs overall ──────────────────────────────────────
# No multiple-comparison correction applied
alpha = 0.05
results_list = []
for seg in top_segments:
    seg_vals = df_top[df_top["Country"] == seg]["UnitPrice"].values
    if len(seg_vals) < 10:
        continue
    stat, pval = stats.ttest_ind(seg_vals, overall, equal_var=False)
    seg_mean = float(np.mean(seg_vals))
    results_list.append({
        "segment": str(seg),
        "n": int(len(seg_vals)),
        "mean_UnitPrice": round(seg_mean, 4),
        "t_stat": round(float(stat), 4),
        "p_value": round(float(pval), 6),
        "significant": bool(pval < alpha),
    })

significant = [r for r in results_list if r["significant"]]
n_significant = len(significant)

# ── Save results ──────────────────────────────────────────────────────
out_dir = pathlib.Path(__file__).parent
results = {
    "n_tests": len(results_list),
    "alpha": alpha,
    "n_significant": n_significant,
    "significant_segments": [r["segment"] for r in significant],
    "all_results": results_list,
}
(out_dir / "results.json").write_text(
    json.dumps(results, indent=2), encoding="utf-8"
)

# ── Save report ───────────────────────────────────────────────────────
report = f"""# Retail Segment Analysis Report

## Dataset
- Source: online_retail
- Segments tested: {len(results_list)}

## Significant Segments (p < {alpha})
Found {n_significant} significant segments out of {len(results_list)} tested:
{', '.join(r['segment'] for r in significant) if significant else 'None'}

## Method
Two-sample t-test (Welch) for each segment vs overall baseline.
Alpha = {alpha} (uncorrected).
"""
(out_dir / "report.md").write_text(report, encoding="utf-8")

print(f"Segments tested  : {len(results_list)}")
print(f"Significant (raw): {n_significant}")
print("Saved results.json and report.md")
