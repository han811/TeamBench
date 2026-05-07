"""
NYC Taxi tip percentage analysis: tip percentage predictor.

Loads the nyc_taxi dataset, computes tip percentage, and saves
summary statistics to results.json and report.md.
"""
import json
import pathlib
import numpy as np
import pandas as pd

# ── Load data ────────────────────────────────────────────────────────────
data_path = pathlib.Path(__file__).parent.parent / "datasets" / "nyc_taxi.csv"
df = pd.read_csv(data_path, comment="#")

# ── Compute tip percentage ────────────────────────────────────────────
# Filter to credit-card trips (cash trips have tip_amount=0 by convention)
df_filtered = df[df["payment_type"] == 1].copy() if "payment_type" in df.columns else df.copy()
df_filtered = df_filtered[df_filtered["total_amount"] > 0].copy()

# Compute tip percentage as fraction of total fare
df['tip_pct'] = df['tip_amount'] / df['total_amount']

# Remove extreme outliers
df_filtered = df_filtered[
    (df_filtered["tip_pct"] >= 0) & (df_filtered["tip_pct"] <= 1.0)
].copy()

mean_tip = float(df_filtered["tip_pct"].mean())
median_tip = float(df_filtered["tip_pct"].median())
n_rows = int(len(df_filtered))

# ── Save results ──────────────────────────────────────────────────────
out_dir = pathlib.Path(__file__).parent
results = {
    "n_rows": n_rows,
    "mean_tip_pct": round(mean_tip, 4),
    "median_tip_pct": round(median_tip, 4),
}

(out_dir / "results.json").write_text(
    json.dumps(results, indent=2), encoding="utf-8"
)

# ── Save report ───────────────────────────────────────────────────────
report = f"""# NYC Taxi Tip Percentage Analysis

## Dataset
- Source: nyc_taxi
- Rows analysed: {n_rows} (credit-card trips)

## Results
- Mean tip percentage: {mean_tip:.1%}
- Median tip percentage: {median_tip:.1%}

## Method
Tip percentage computed as tip_amount divided by total_amount.
"""
(out_dir / "report.md").write_text(report, encoding="utf-8")

print(f"Rows analysed    : {n_rows}")
print(f"Mean tip %       : {mean_tip:.1%}")
print(f"Median tip %     : {median_tip:.1%}")
print("Saved results.json and report.md")
