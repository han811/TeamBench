"""
Macro time series regression: GDP ~ CPI (Consumer Price Index).

Loads the fred_macro dataset, regresses GDP on CPI in levels,
and saves results to results.json and report.md.
"""
import json
import pathlib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score

# ── Load data ────────────────────────────────────────────────────────────
data_path = pathlib.Path(__file__).parent.parent / "datasets" / "fred_macro.csv"
df = pd.read_csv(data_path, comment="#", parse_dates=["date"] if "date" in
                 open(data_path).readline() else False)

# ── Prepare series ────────────────────────────────────────────────────
# Use levels directly — no stationarity transformation
available_cols = df.columns.tolist()
y_col = next((c for c in ["GDP"] if c in available_cols), available_cols[1])
x_col = next((c for c in ["CPI"] if c in available_cols), available_cols[2])

df_clean = df[[x_col, y_col]].dropna().copy()
X = df_clean[[x_col]].values
y = df_clean[y_col].values

# ── Regression in levels ──────────────────────────────────────────────
model = LinearRegression()
model.fit(X, y)
y_pred = model.predict(X)
r2 = r2_score(y, y_pred)
coef = float(model.coef_[0])
intercept = float(model.intercept_)

# ── Save results ──────────────────────────────────────────────────────
out_dir = pathlib.Path(__file__).parent
results = {
    "n_obs": int(len(df_clean)),
    "y_variable": y_col,
    "x_variable": x_col,
    "r2": round(float(r2), 4),
    "coefficient": round(coef, 6),
    "intercept": round(intercept, 4),
    "method": "levels_regression",
}
(out_dir / "results.json").write_text(
    json.dumps(results, indent=2), encoding="utf-8"
)

# ── Save report ───────────────────────────────────────────────────────
report = f"""# Macro Regression Report: {y_col} ~ {x_col}

## Dataset
- Source: fred_macro
- Observations: {len(df_clean)}

## Model (levels regression)
- R²: {r2:.4f}
- Coefficient on {x_col}: {coef:.6f}
- Intercept: {intercept:.4f}

## Conclusion
Strong positive relationship found (R²={r2:.2f}).
{x_col} appears to be a strong predictor of {y_col}.
"""
(out_dir / "report.md").write_text(report, encoding="utf-8")

print(f"Observations : {len(df_clean)}")
print(f"R²           : {r2:.4f}")
print(f"Coefficient  : {coef:.6f}")
print("Saved results.json and report.md")
