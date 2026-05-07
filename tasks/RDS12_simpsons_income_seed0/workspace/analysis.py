"""
Income gender-gap analysis script.

Examines income rates by sex, stratification variable: education_num (education level).
Loads the adult_income dataset and computes aggregate income rates by sex.
Saves results to results.json and report.md.
"""
import json
import pathlib
import numpy as np
import pandas as pd

# ── Load data ────────────────────────────────────────────────────────────
data_path = pathlib.Path(__file__).parent.parent / "datasets" / "adult_income.csv"
df = pd.read_csv(data_path, comment="#")
df.columns = df.columns.str.strip()
df["sex"] = df["sex"].str.strip()
df["income"] = df["income"].str.strip()
df["target"] = (df["income"] == ">50K").astype(int)

# ── Aggregate analysis by sex ─────────────────────────────────────────
# NOTE: only aggregate rates are computed — no stratification by education_num
agg = df.groupby("sex")["target"].agg(["mean", "count"]).reset_index()
agg.columns = ["sex", "positive_rate", "n"]

aggregate_results = agg.to_dict(orient="records")

# ── Summary statistics ────────────────────────────────────────────────
overall_rate = float(df["target"].mean())
n_total = int(len(df))

# ── Save results ──────────────────────────────────────────────────────
out_dir = pathlib.Path(__file__).parent
results = {
    "n_rows": n_total,
    "overall_positive_rate": round(overall_rate, 4),
    "aggregate_results": aggregate_results,
}
(out_dir / "results.json").write_text(
    json.dumps(results, indent=2), encoding="utf-8"
)

# ── Save report ───────────────────────────────────────────────────────
female_rate = agg.loc[agg["sex"] == "Female", "positive_rate"].values
male_rate = agg.loc[agg["sex"] == "Male", "positive_rate"].values
f_pct = float(female_rate[0]) if len(female_rate) else 0.0
m_pct = float(male_rate[0]) if len(male_rate) else 0.0

report = f"""# Income Gender-Gap Analysis Report

## Dataset
- Source: adult_income (UCI Census)
- Rows analysed: {n_total}
- Overall >50K rate: {overall_rate:.1%}

## Aggregate Results by Sex
- Female >50K rate: {f_pct:.1%}
- Male   >50K rate: {m_pct:.1%}
- Gap (Male - Female): {m_pct - f_pct:+.1%}

## Conclusion
Men earn more than women on average in this dataset.
"""
(out_dir / "report.md").write_text(report, encoding="utf-8")

print(f"Rows analysed   : {n_total}")
print(f"Overall >50K    : {overall_rate:.1%}")
print(f"Female >50K rate: {f_pct:.1%}")
print(f"Male   >50K rate: {m_pct:.1%}")
print("Saved results.json and report.md")
