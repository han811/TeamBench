# RDS8: Telco Churn Survival Analysis

## Research Question
**How does customer survival (non-churn) differ across contract types (month-to-month, one-year, two-year)? Use Kaplan-Meier curves to estimate and compare survival functions.**

## Dataset
- File: `data/telco_churn.csv`
- Rows: 1408 (subsample of Telco Customer Churn dataset)
- Columns: `customerID`, `gender`, `SeniorCitizen`, `Partner`, `Dependents`, `tenure`, `PhoneService`, `MultipleLines`, `InternetService`, `OnlineSecurity`, `Contract`, `PaperlessBilling`, `PaymentMethod`, `MonthlyCharges`, `TotalCharges`, `Churn`
- Key columns: `tenure`, `Churn`, `Contract`
- Target: `Churn` (Yes/No) — whether the customer left

## Background
In survival analysis, `tenure` is the time variable (months with company) and `Churn` is the event indicator (Yes/No). Customers still active are right-censored. Kaplan-Meier estimates the survival function S(t) = P(T > t). Compare curves across three contract types: month-to-month (highest churn risk), one-year, and two-year. Use log-rank test to test for significant differences.

## Method Hint
Use lifelines library (KaplanMeierFitter) or implement KM manually. Log-rank test from lifelines or scipy.

## Your Task
Conduct a **Kaplan-Meier Survival Analysis** to answer the research question.

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
- Performs the Kaplan-Meier Survival Analysis analysis
- Saves `results.json` and `report.md`

### 2. `results.json`
Must contain at minimum:
```json
{
  "analysis_type": "kaplan_meier",
  "median_survival_month_to_month": <float>,
  "n_churned": <int>,
  "n_retained": <int>
}
```

### 3. `report.md`
A brief (300–600 word) report covering:
- Data cleaning decisions
- Key findings: median survival time for month-to-month contract customers
- A PNG or description of KM curves in the report.
- **Limitations** (censoring assumptions, selection bias, etc.)

## Grading Criteria
1. `analysis.py` runs without error
2. Survival/prediction method implemented correctly
3. Key metric (`median_survival_month_to_month`) present in `results.json`
4. Key columns (`tenure`, `Churn`, `Contract`) referenced in analysis code
5. Group comparison or covariate analysis present
6. `report.md` discusses limitations
7. Data loaded correctly (correct row count)
8. `results.json` contains required fields and is valid JSON
