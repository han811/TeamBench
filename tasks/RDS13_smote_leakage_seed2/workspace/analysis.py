"""
Credit card fraud detection pipeline.

Loads the credit_card_fraud dataset, applies SMOTETomek to handle
class imbalance, trains a Random Forest classifier, and evaluates on a
held-out test set. Saves results to results.json and report.md.
"""
import json
import pathlib
import numpy as np
import pandas as pd
from imblearn.combine import SMOTETomek
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_auc_score, average_precision_score
from sklearn.preprocessing import StandardScaler

# ── Load data ────────────────────────────────────────────────────────────
data_path = pathlib.Path(__file__).parent.parent / "datasets" / "credit_card_fraud.csv"
df = pd.read_csv(data_path, comment="#")

feature_cols = [c for c in df.columns if c not in ["Class"]]
X = df[feature_cols].values
y = df["Class"].values

# ── Resample BEFORE split ─────────────────────────────────────────────
# Apply SMOTETomek to handle class imbalance
smt = SMOTETomek(random_state=42)
X_res, y_res = smt.fit_resample(X, y)

# ── Train / test split ────────────────────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    X_res, y_res, test_size=0.2, random_state=42, stratify=y_res
)

# ── Scale features ────────────────────────────────────────────────────
scaler = StandardScaler()
X_train = scaler.fit_transform(X_train)
X_test = scaler.transform(X_test)

# ── Model ─────────────────────────────────────────────────────────────
clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
clf.fit(X_train, y_train)

y_proba = clf.predict_proba(X_test)[:, 1]
auc = roc_auc_score(y_test, y_proba)
ap = average_precision_score(y_test, y_proba)

# ── Save results ──────────────────────────────────────────────────────
out_dir = pathlib.Path(__file__).parent
results = {
    "n_original": int(len(df)),
    "n_resampled": int(len(X_res)),
    "n_train": int(len(X_train)),
    "n_test": int(len(X_test)),
    "auc": round(float(auc), 4),
    "average_precision": round(float(ap), 4),
    "resampler": "SMOTETomek",
}
(out_dir / "results.json").write_text(
    json.dumps(results, indent=2), encoding="utf-8"
)

# ── Save report ───────────────────────────────────────────────────────
report = f"""# Fraud Detection Pipeline Report

## Dataset
- Source: credit_card_fraud
- Original rows: {len(df)}
- After SMOTETomek: {len(X_res)}

## Model Performance
- AUC-ROC: {auc:.4f}
- Average Precision: {ap:.4f}

## Method
Applied SMOTETomek to address class imbalance, then trained a
Random Forest classifier.
"""
(out_dir / "report.md").write_text(report, encoding="utf-8")

print(f"Original rows   : {len(df)}")
print(f"After resample  : {len(X_res)}")
print(f"Train size      : {len(X_train)}")
print(f"Test size       : {len(X_test)}")
print(f"AUC-ROC         : {auc:.4f}")
print(f"Avg Precision   : {ap:.4f}")
print("Saved results.json and report.md")
