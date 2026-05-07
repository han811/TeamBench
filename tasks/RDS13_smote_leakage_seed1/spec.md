# RDS13: SMOTE Data Leakage in Fraud Detection

## Overview

The workspace contains `analysis.py`, a fraud detection pipeline using the
`credit_card_fraud` dataset. The script trains a Random Forest classifier
with RandomOverSampler oversampling and reports AUC-ROC.
It runs without errors and produces `results.json` and `report.md`.

**However, the pipeline contains a data leakage flaw** — RandomOverSampler
is applied BEFORE the train/test split, causing the test set to be
contaminated with synthetic samples derived from real test points.

## The Flaw

### RandomOverSampler Applied Before Split

The script applies RandomOverSampler — which duplicates minority-class examples — BEFORE the train/test split. Exact duplicates of test-set fraud records end up in the training set. The model learns to perfectly recognise these duplicates, inflating AUC to ~0.998.

### Quantitative Impact

| Condition | AUC-ROC |
|---|---|
| Current (flawed — leakage) | ~0.998 |
| After fix (correct) | ~0.95 |

The inflated AUC of ~0.998 will never replicate in production,
making the model appear far more capable than it actually is.

## Required Fix

Split the data FIRST with `train_test_split`, then apply RandomOverSampler only to the training portion. Never resample the test set. After the fix, AUC should drop to a realistic ~0.95.

### Specific Changes to `analysis.py`

1. **Move `train_test_split`** to occur BEFORE `ros.fit_resample(...)`.
2. **Apply resampling only to training data**:
   ```python
   X_train_res, y_train_res = ros.fit_resample(X_train, y_train)
   ```
3. **Train** on `X_train_res, y_train_res`.
4. **Evaluate** on the original (unmodified) `X_test, y_test`.
5. Re-run so `results.json` reflects the corrected AUC (should be ≤ 0.97).
6. Update `report.md` to acknowledge the leakage issue and explain the fix.

## Deliverables

- Fixed `analysis.py` (resampling after split, only on train)
- `results.json` with `auc` <= 0.97 and `n_train`/`n_test` keys
- `report.md` that mentions data leakage and the correction

## Grading Rubric

| Check | Description |
|---|---|
| C1 | `fit_resample` called after `train_test_split` in `analysis.py` |
| C2 | `results.json` contains `auc` key |
| C3 | AUC in `results.json` <= 0.97 |
| C4 | `results.json` contains `n_train` and `n_test` keys |
| C5 | `report.md` mentions data leakage |
| C6 | `analysis.py` runs without error |
