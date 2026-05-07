# RDS9: Fraud Detection

## Research Question
**Apply an unsupervised anomaly detection method (Isolation Forest or Local Outlier Factor) to detect fraud. Compare its precision and recall against a supervised baseline (logistic regression).**

## Dataset
- File: `data/credit_card_fraud.csv`
- Rows: 1500 (subsample of credit card transactions)
- Columns: `Time`, `V1`–`V28` (PCA features), `Amount`, `Class`
- Available columns: `Time`, `V1`, `V2`, `V3`, `V4`, `V5`, `V10`, `V11`, `V12`, `V14`, `V17`, `V19`, `V21`, `V27`, `V28`, `Amount`, `Class`
- Target: `Class` (1=fraud, 0=legitimate)
- Constraint: **No labels used during anomaly detection training**

## Background
Unsupervised anomaly detection treats fraud as statistical outliers. Isolation Forest assigns anomaly scores; lower scores indicate anomalies. The contamination parameter should be set to the approximate fraud rate (~0.002). Compare: precision, recall, and F1 of anomaly detection vs. a simple logistic regression baseline. Discuss trade-offs.

## Method Hint
Use sklearn IsolationForest with contamination≈0.002. Compare to LogisticRegression.

## Your Task
Conduct a **Anomaly Detection** to detect credit card fraud.

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
- Implements Anomaly Detection
- Saves `results.json` and `report.md`

### 2. `results.json`
Must contain at minimum:
```json
{
  "analysis_type": "anomaly_detection",
  "anomaly_f1": <float>,
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
- Anomaly Detection design decisions
- **Limitations** (imbalanced data, threshold sensitivity, overfitting, etc.)

## Grading Criteria
1. `analysis.py` runs without error
2. Class imbalance handled (weights, sampling, or contamination parameter)
3. Key metric (`anomaly_f1`) and precision/recall in `results.json`
4. Key columns (`Class`, `Amount`, `V1`, `V14`, `V17`) referenced in analysis code
5. Threshold tuning or cost analysis or anomaly scoring present
6. `report.md` discusses limitations
7. Data loaded correctly (correct row count)
8. `results.json` contains required fields and is valid JSON
