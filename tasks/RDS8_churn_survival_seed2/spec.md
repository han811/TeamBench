# RDS8: Telco Churn Survival Analysis

## Research Question
**Build a churn prediction model that achieves the best AUC while identifying the top 5 most predictive features. Compare logistic regression vs. a tree-based model.**

## Dataset
- File: `data/telco_churn.csv`
- Rows: 1408 (subsample of Telco Customer Churn dataset)
- Columns: `customerID`, `gender`, `SeniorCitizen`, `Partner`, `Dependents`, `tenure`, `PhoneService`, `MultipleLines`, `InternetService`, `OnlineSecurity`, `Contract`, `PaperlessBilling`, `PaymentMethod`, `MonthlyCharges`, `TotalCharges`, `Churn`
- Key columns: `tenure`, `Churn`, `MonthlyCharges`, `TotalCharges`, `Contract`, `InternetService`
- Target: `Churn` (Yes/No) — whether the customer left

## Background
Churn prediction is a binary classification task. `Churn` is the target (Yes/No → 1/0). Features include numeric (tenure, MonthlyCharges, TotalCharges) and categorical (Contract, InternetService, PaymentMethod, etc.). TotalCharges may have missing values — handle them. Report AUC on held-out test set and identify top 5 predictive features by feature importance or coefficient magnitude.

## Method Hint
Use sklearn LogisticRegression and RandomForestClassifier. Compare AUC for both.

## Your Task
Conduct a **Churn Prediction Model** to answer the research question.

Steps:
1. Load and clean the data (`TotalCharges` may have non-numeric values)
2. Encode `Churn` as binary: Yes=1, No=0
3. Perform the analysis described above
4. Report key metrics in `results.json`

## Required Deliverables

### 1. `analysis.py`
A Python script that:
- Loads `data/telco_churn.csv`
- Cleans and encodes variables
- Performs the Churn Prediction Model analysis
- Saves `results.json` and `report.md`

### 2. `results.json`
Must contain at minimum:
```json
{
  "analysis_type": "churn_prediction",
  "auc": <float>,
  "n_churned": <int>,
  "n_retained": <int>
}
```

### 3. `report.md`
A brief (300–600 word) report covering:
- Data cleaning decisions
- Key findings: AUC on the held-out test set
- Feature importance ranking in results.json as `top_features`.
- **Limitations** (censoring assumptions, selection bias, etc.)

## Grading Criteria
1. `analysis.py` runs without error
2. Survival/prediction method implemented correctly
3. Key metric (`auc`) present in `results.json`
4. Key columns (`tenure`, `Churn`, `MonthlyCharges`, `TotalCharges`, `Contract`, `InternetService`) referenced in analysis code
5. Group comparison or covariate analysis present
6. `report.md` discusses limitations
7. Data loaded correctly (correct row count)
8. `results.json` contains required fields and is valid JSON
