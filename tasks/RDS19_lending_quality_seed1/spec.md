# RDS19: Lending Default Prediction

## Task
Build a binary classification model to predict loan default using the provided
Lending Club loan dataset.

## Dataset
- File: `data/loans.csv`
- Rows: 2000
- Target column: `default_ind` (1 = defaulted, 0 = fully paid)
- Features include: loan amount, term, interest rate, grade, employment length,
  annual income, purpose, debt-to-income ratio, FICO scores, and delinquency history

## Your Task
1. Load and explore `data/loans.csv`
2. Prepare features for modelling (handle types, missing values, encoding)
3. Train a classification model (logistic regression, random forest, or gradient boosting)
4. Evaluate using AUC-ROC on a held-out test set (20% split, random_state=42)
5. Save results and a brief report

## Required Deliverables

### 1. `analysis.py`
A Python script that:
- Loads `data/loans.csv`
- Prepares features (handle types, missing values, categorical encoding)
- Trains a classifier and evaluates on a test split
- Saves `results.json` and `report.md`

### 2. `results.json`
Must contain at minimum:
```json
{
  "model": "<model name>",
  "auc_roc": <float>,
  "accuracy": <float>,
  "n_train": <int>,
  "n_test": <int>
}
```

### 3. `report.md`
A brief (200–400 word) report covering:
- Feature engineering decisions
- Any data quality issues discovered and how you handled them
- Model performance summary

## Grading Criteria
1. `analysis.py` runs without error
2. `emp_length` column is converted to numeric (not used as raw string)
3. Outliers in `annual_inc` are addressed
4. `purpose` column is cleaned (consistent values)
5. Model achieves AUC > 0.5 on the test set
6. `results.json` contains required fields
7. Data is loaded correctly (expected row count)
8. `report.md` discusses at least one data quality issue
