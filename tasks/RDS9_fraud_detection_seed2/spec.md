# RDS9: Fraud Detection

## Research Question
**Frame fraud detection as a cost minimization problem. Assume: missing a fraud costs $500 (false negative), and a false alarm costs $10 (false positive). Find the classification threshold that minimizes total expected cost.**

## Dataset
- File: `data/credit_card_fraud.csv`
- Rows: 1500 (subsample of credit card transactions)
- Columns: `Time`, `V1`–`V28` (PCA features), `Amount`, `Class`
- Available columns: `Time`, `V1`, `V2`, `V3`, `V4`, `V5`, `V10`, `V11`, `V12`, `V14`, `V17`, `V19`, `V21`, `V27`, `V28`, `Amount`, `Class`
- Target: `Class` (1=fraud, 0=legitimate)
- Constraint: **FN cost = $500, FP cost = $10**

## Background
In fraud detection, false negatives (missed fraud) and false positives (false alarms) have very different costs. The optimal threshold trades off these costs. Total cost = FN_cost × FN_count + FP_cost × FP_count. Sweep thresholds from 0.01 to 0.99, compute total cost at each, and report the cost-minimizing threshold and its precision/recall.

## Method Hint
Train a logistic regression or gradient boosting model, then sweep decision thresholds.

## Your Task
Conduct a **Cost-Sensitive Classification** to detect credit card fraud.

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
- Implements Cost-Sensitive Classification
- Saves `results.json` and `report.md`

### 2. `results.json`
Must contain at minimum:
```json
{
  "analysis_type": "cost_sensitive",
  "min_total_cost": <float>,
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
- Cost-Sensitive Classification design decisions
- **Limitations** (imbalanced data, threshold sensitivity, overfitting, etc.)

## Grading Criteria
1. `analysis.py` runs without error
2. Class imbalance handled (weights, sampling, or contamination parameter)
3. Key metric (`min_total_cost`) and precision/recall in `results.json`
4. Key columns (`Class`, `Amount`, `V1`, `V14`) referenced in analysis code
5. Threshold tuning or cost analysis or anomaly scoring present
6. `report.md` discusses limitations
7. Data loaded correctly (correct row count)
8. `results.json` contains required fields and is valid JSON
