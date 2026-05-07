# RDS9: Fraud Detection

## Research Question
**Train a logistic regression model and tune the classification threshold to achieve a false positive rate ≤ 1% while maximizing fraud recall. What is the maximum recall achievable under this FPR constraint?**

## Dataset
- File: `data/credit_card_fraud.csv`
- Rows: 1500 (subsample of credit card transactions)
- Columns: `Time`, `V1`–`V28` (PCA features), `Amount`, `Class`
- Available columns: `Time`, `V1`, `V2`, `V3`, `V4`, `V5`, `V10`, `V11`, `V12`, `V14`, `V17`, `V19`, `V21`, `V27`, `V28`, `Amount`, `Class`
- Target: `Class` (1=fraud, 0=legitimate)
- Constraint: **FPR ≤ 0.01**

## Background
The dataset is highly imbalanced (~0.17% fraud). The `Class` column is the target (1=fraud, 0=legitimate). Features V1-V28 are PCA-transformed. `Amount` and `Time` are raw. Logistic regression outputs probabilities; the threshold can be adjusted below 0.5 to increase recall. FPR = FP / (FP + TN). Find the highest threshold that keeps FPR ≤ 0.01.

## Method Hint
Use sklearn's precision_recall_curve or roc_curve to find the threshold.

## Your Task
Conduct a **Threshold-Tuned Logistic Regression** to detect credit card fraud.

Steps:
1. Load and explore the data (check class distribution)
2. Handle class imbalance appropriately
3. Implement the analysis approach described above
4. Report key performance metrics
5. Save `results.json` and `report.md`

## Required Deliverables

### 1. `analysis.py`
A Python script that:
- Loads `data/credit_card_fraud.csv`
- Handles class imbalance
- Implements Threshold-Tuned Logistic Regression
- Saves `results.json` and `report.md`

### 2. `results.json`
Must contain at minimum:
```json
{
  "analysis_type": "threshold_tuning",
  "recall_at_1pct_fpr": <float>,
  "precision": <float>,
  "recall": <float>,
  "n_fraud": <int>,
  "n_legitimate": <int>
}
```

### 3. `report.md`
A brief (300–600 word) report covering:
- Class imbalance handling
- Key performance metrics (precision, recall, FPR)
- Threshold-Tuned Logistic Regression design decisions
- **Limitations** (imbalanced data, threshold sensitivity, overfitting, etc.)

## Grading Criteria
1. `analysis.py` runs without error
2. Class imbalance handled (weights, sampling, or contamination parameter)
3. Key metric (`recall_at_1pct_fpr`) and precision/recall in `results.json`
4. Key columns (`Class`, `Amount`, `V1`, `V14`) referenced in analysis code
5. Threshold tuning or cost analysis or anomaly scoring present
6. `report.md` discusses limitations
7. Data loaded correctly (correct row count)
8. `results.json` contains required fields and is valid JSON
