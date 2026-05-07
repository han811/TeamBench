"""
Income analysis script.

Loads the adult_income dataset, fits a logistic regression model
predicting high income (>50K), and saves results.
"""
import json
import pathlib
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, accuracy_score

# ── Load data ────────────────────────────────────────────────────────────
data_path = pathlib.Path(__file__).parent.parent / "datasets" / "adult_income.csv"
df = pd.read_csv(data_path, comment="#")

# ── Preprocessing filter ─────────────────────────────────────────────────
df = df[df['hours_per_week'] > 20]  # focus on full-time and near-full-time workers

# ── Feature engineering ──────────────────────────────────────────────────
num_features = ['age', 'education_num', 'hours_per_week', 'capital_gain', 'capital_loss']
cat_features = ['workclass', 'marital_status', 'occupation', 'sex']

df = df.copy()
for col in cat_features:
    df[col] = LabelEncoder().fit_transform(df[col].astype(str))

feature_cols = [c for c in num_features + cat_features if c in df.columns]
df["target"] = (df["income"].str.strip() == ">50K").astype(int)

X = df[feature_cols].fillna(0)
y = df["target"]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# ── Model ────────────────────────────────────────────────────────────────
model = LogisticRegression(max_iter=500, random_state=42)
model.fit(X_train, y_train)

y_pred_proba = model.predict_proba(X_test)[:, 1]
y_pred = model.predict(X_test)
auc = roc_auc_score(y_test, y_pred_proba)
acc = accuracy_score(y_test, y_pred)

coef_dict = dict(zip(feature_cols, model.coef_[0].tolist()))

# ── Save results ─────────────────────────────────────────────────────────
out_dir = pathlib.Path(__file__).parent
results = {
    "n_rows": int(len(df)),
    "positive_rate": float(y.mean()),
    "model_results": {
        "auc": round(float(auc), 4),
        "accuracy": round(float(acc), 4),
        "coefficients": {k: round(v, 4) for k, v in coef_dict.items()},
        "features": feature_cols,
    },
}
(out_dir / "results.json").write_text(
    json.dumps(results, indent=2), encoding="utf-8"
)

# ── Save report ──────────────────────────────────────────────────────────
report = f"""# Income Analysis Report

## Dataset
- Source: adult_income
- Rows analysed: {len(df)}
- Positive rate (>50K): {y.mean():.1%}

## Model Performance
- AUC: {auc:.4f}
- Accuracy: {acc:.4f}

## Coefficients
"""
for feat, coef in coef_dict.items():
    report += f"- {feat}: {coef:+.4f}\n"
(out_dir / "report.md").write_text(report, encoding="utf-8")

print(f"Rows analysed : {len(df)}")
print(f"Positive rate : {y.mean():.1%}")
print(f"AUC           : {auc:.4f}")
print(f"Accuracy      : {acc:.4f}")
print("Saved results.json and report.md")
