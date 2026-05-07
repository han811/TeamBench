# RDS7: WHO Health Panel Analysis

## Research Question
**Which health and economic factors (physicians per 1000, health expenditure, HIV prevalence, income group) most strongly predict life expectancy across countries and years? Use panel regression with country fixed effects.**

## Dataset
- File: `data/who_gho.csv`
- Rows: 264 (WHO Global Health Observatory data)
- Columns: `country`, `country_code`, `year`, `life_expectancy`, `infant_mortality`, `under5_mortality`, `maternal_mortality`, `hiv_prevalence`, `physicians_per_1000`, `hospital_beds_per_1000`, `health_expenditure_pct_gdp`, `income_group`, `region`
- Key columns for this analysis: `life_expectancy`, `physicians_per_1000`, `health_expenditure_pct_gdp`, `hiv_prevalence`, `income_group`

## Background
Life expectancy differs enormously across countries. Panel data allows controlling for time-invariant country characteristics via fixed effects. Key predictors: physicians per 1000 (healthcare access), health expenditure as % GDP (investment), HIV prevalence (disease burden), income group. Use OLS with country fixed effects or a mixed effects model.

## Method Hint
Use statsmodels OLS with country dummy variables, or use within-group demeaning for fixed effects.

## Your Task
Conduct a **Panel Regression** to answer the research question.

Steps:
1. Load and clean the data (handle missing values, numeric types)
2. Perform the analysis as described
3. Report key findings with statistical evidence
4. Save `results.json` and `report.md`

## Required Deliverables

### 1. `analysis.py`
A Python script that:
- Loads `data/who_gho.csv`
- Handles missing data appropriately
- Runs the Panel Regression analysis
- Saves `results.json` and `report.md`

### 2. `results.json`
Must contain at minimum:
```json
{
  "analysis_type": "panel_regression",
  "r2": <float>,
  "top_predictor": <value>,
  "n_countries": <int>
}
```

### 3. `report.md`
A brief (300–600 word) report covering:
- Data cleaning decisions (missing data handling)
- Key findings: R² of the panel model
- Statistical evidence (coefficients, p-values, R²)
- **Limitations** (data quality, causality, confounding, etc.)

## Grading Criteria
1. `analysis.py` runs without error
2. Panel/regression/trend analysis implemented
3. Key metric (`r2`) present in `results.json`
4. Key columns (`life_expectancy`, `physicians_per_1000`, `health_expenditure_pct_gdp`, `hiv_prevalence`, `income_group`) referenced in analysis code
5. Country/region grouping or fixed effects present
6. `report.md` discusses limitations
7. Data loaded correctly (correct row count)
8. `results.json` contains required fields and is valid JSON
