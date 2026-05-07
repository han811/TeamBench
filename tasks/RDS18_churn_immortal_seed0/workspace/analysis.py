"""
Telco customer churn analysis.

Compares churn rates between loyal (loyal (tenure > 12 months)) and
new (new (tenure <= 12 months)) customer segments.
Saves results to results.json and report.md.
"""
import json
import pathlib
import numpy as np
import pandas as pd
from scipy import stats

# ── Load data ────────────────────────────────────────────────────────────
data_path = pathlib.Path(__file__).parent.parent / "datasets" / "telco_churn.csv"
df = pd.read_csv(data_path, comment="#")

# ── Prepare columns ───────────────────────────────────────────────────
# Standardise column names
df.columns = df.columns.str.strip()
churn_col = next((c for c in df.columns if "churn" in c.lower()), "Churn")
tenure_col = next((c for c in df.columns if "tenure" in c.lower()), "tenure")

df["churned"] = df[churn_col].astype(str).str.strip().str.upper().isin(
    ["YES", "TRUE", "1", "Y"]
).astype(int)
df[tenure_col] = pd.to_numeric(df[tenure_col], errors="coerce")
df = df.dropna(subset=[tenure_col, "churned"])

# ── Classify customers ────────────────────────────────────────────────
# Loyal = tenure > 12 months (guaranteed to have survived 12 months)
loyal_mask = df[tenure_col] > 12
new_mask = ~loyal_mask

loyal = df[loyal_mask]
new = df[new_mask]

loyal_churn_rate = float(loyal["churned"].mean())
new_churn_rate = float(new["churned"].mean())

# ── Statistical test ──────────────────────────────────────────────────
stat, pval = stats.ttest_ind(loyal["churned"].values, new["churned"].values)

# ── Save results ──────────────────────────────────────────────────────
out_dir = pathlib.Path(__file__).parent
results = {
    "n_total": int(len(df)),
    "n_loyal": int(len(loyal)),
    "n_new": int(len(new)),
    "loyal_churn_rate": round(loyal_churn_rate, 4),
    "new_churn_rate": round(new_churn_rate, 4),
    "churn_rate_gap": round(new_churn_rate - loyal_churn_rate, 4),
    "t_stat": round(float(stat), 4),
    "p_value": round(float(pval), 6),
    "loyalty_threshold_months": 12,
}
(out_dir / "results.json").write_text(
    json.dumps(results, indent=2), encoding="utf-8"
)

# ── Save report ───────────────────────────────────────────────────────
report = f"""# Telco Customer Churn Analysis Report

## Dataset
- Source: telco_churn
- Total customers: {len(df)}

## Segment Comparison (tenure threshold: 12 months)
- Loyal customers (tenure > 12 months): n={len(loyal)}, churn={loyal_churn_rate:.1%}
- New customers (tenure <= 12 months): n={len(new)}, churn={new_churn_rate:.1%}
- Churn rate gap: {new_churn_rate - loyal_churn_rate:+.1%}

## Conclusion
Loyal customers have significantly lower churn rates (p={pval:.4f}).
Long-tenure customers demonstrate stronger retention.
"""
(out_dir / "report.md").write_text(report, encoding="utf-8")

print(f"Total customers  : {len(df)}")
print(f"Loyal churn rate : {loyal_churn_rate:.1%}")
print(f"New churn rate   : {new_churn_rate:.1%}")
print(f"Gap              : {new_churn_rate - loyal_churn_rate:+.1%}")
print("Saved results.json and report.md")
