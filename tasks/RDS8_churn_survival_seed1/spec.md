# RDS8: Telco Churn Survival Analysis

## Research Question
**Which customer features are significant predictors of churn risk? Fit a Cox proportional hazards model with covariates: contract type, monthly charges, internet service, and senior citizen status.**

## Dataset
- File: `data/telco_churn.csv`
- Rows: 1408 (subsample of Telco Customer Churn dataset)
- Columns: `customerID`, `gender`, `SeniorCitizen`, `Partner`, `Dependents`, `tenure`, `PhoneService`, `MultipleLines`, `InternetService`, `OnlineSecurity`, `Contract`, `PaperlessBilling`, `PaymentMethod`, `MonthlyCharges`, `TotalCharges`, `Churn`
- Key columns: `tenure`, `Churn`, `Contract`, `MonthlyCharges`, `InternetService`, `SeniorCitizen`
- Target: `Churn` (Yes/No) — whether the customer left

## Background
The Cox model estimates the hazard ratio for each covariate: HR > 1 means increased churn risk. Key questions: Does higher monthly charges increase churn? Does fiber optic internet increase risk vs DSL? Are senior citizens at higher risk? Check the proportional hazards assumption (Schoenfeld residuals or log-log plot).

## Method Hint
Use lifelines CoxPHFitter or statsmodels PHReg. Encode categorical variables before fitting.

## Your Task
Conduct a **Cox Proportional Hazards Model** to answer the research question.

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
- Performs the Cox Proportional Hazards Model analysis
- Saves `results.json` and `report.md`

### 2. `results.json`
Must contain at minimum:
```json
{
  "analysis_type": "cox_ph",
  "top_hazard_ratio": <float>,
  "n_churned": <int>,
  "n_retained": <int>
}
```

### 3. `report.md`
A brief (300–600 word) report covering:
- Data cleaning decisions
- Key findings: highest hazard ratio among covariates
- A table of hazard ratios with 95% CIs in the report.
- **Limitations** (censoring assumptions, selection bias, etc.)

## Grading Criteria
1. `analysis.py` runs without error
2. Survival/prediction method implemented correctly
3. Key metric (`top_hazard_ratio`) present in `results.json`
4. Key columns (`tenure`, `Churn`, `Contract`, `MonthlyCharges`, `InternetService`, `SeniorCitizen`) referenced in analysis code
5. Group comparison or covariate analysis present
6. `report.md` discusses limitations
7. Data loaded correctly (correct row count)
8. `results.json` contains required fields and is valid JSON
