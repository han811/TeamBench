"""
Ames Housing price prediction analysis.

Loads the ames_housing dataset, trains a Gradient Boosting regressor
to predict SalePrice, and evaluates on a held-out test set.
Saves results to results.json and report.md.
"""
import json
import pathlib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import r2_score, mean_absolute_error
from sklearn.preprocessing import LabelEncoder

# ── Load data ────────────────────────────────────────────────────────────
data_path = pathlib.Path(__file__).parent.parent / "datasets" / "ames_housing.csv"
df = pd.read_csv(data_path, comment="#")

target_col = "SalePrice"
drop_cols = [target_col, "Id"] if "Id" in df.columns else [target_col]

# ── Feature selection ─────────────────────────────────────────────────
# Select numeric and key categorical features including sale-time info
numeric_features = [
    "LotArea", "OverallQual", "OverallCond", "YearBuilt",
    "YearRemodAdd", "TotalBsmtSF", "GrLivArea", "FullBath",
    "BedroomAbvGr", "GarageCars", "GarageArea",
]
# Post-event categorical features (describing the sale itself)
post_event_features = ['SaleType', 'MoSold', 'YrSold']
categorical_features = post_event_features

all_features = numeric_features + categorical_features
available = [c for c in all_features if c in df.columns]

df_model = df[available + [target_col]].dropna()

for col in categorical_features:
    if col in df_model.columns:
        df_model = df_model.copy()
        df_model[col] = LabelEncoder().fit_transform(df_model[col].astype(str))

X = df_model[[c for c in available if c in df_model.columns]].values
y = np.log1p(df_model[target_col].values)

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# ── Model ─────────────────────────────────────────────────────────────
model = GradientBoostingRegressor(
    n_estimators=200, learning_rate=0.1, max_depth=4, random_state=42
)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
r2 = r2_score(y_test, y_pred)
mae = mean_absolute_error(np.expm1(y_test), np.expm1(y_pred))

# ── Save results ──────────────────────────────────────────────────────
out_dir = pathlib.Path(__file__).parent
feat_names = [c for c in available if c in df_model.columns]
results = {
    "n_rows": int(len(df_model)),
    "n_features": int(len(feat_names)),
    "features_used": feat_names,
    "r2": round(float(r2), 4),
    "mae": round(float(mae), 2),
}
(out_dir / "results.json").write_text(
    json.dumps(results, indent=2), encoding="utf-8"
)

# ── Save report ───────────────────────────────────────────────────────
report = f"""# Ames Housing Price Prediction Report

## Dataset
- Source: ames_housing
- Rows: {len(df_model)}
- Features: {len(feat_names)}

## Model Performance
- R²: {r2:.4f}
- MAE: ${mae:,.0f}

## Features Used
{', '.join(feat_names)}
"""
(out_dir / "report.md").write_text(report, encoding="utf-8")

print(f"Rows          : {len(df_model)}")
print(f"Features      : {len(feat_names)}")
print(f"R²            : {r2:.4f}")
print(f"MAE           : ${mae:,.0f}")
print("Saved results.json and report.md")
