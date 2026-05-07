# RDS10: Stack Overflow Survey Analysis

## Research Question
**How does years of professional coding experience (YearsCodePro) predict annual compensation (ConvertedCompYearly), after controlling for education level and developer type?**

## Dataset
- File: `data/stackoverflow.csv`
- Rows: 1250 (subsample of Stack Overflow Developer Survey)
- Columns: `ResponseId`, `Employment`, `EdLevel`, `YearsCode`, `YearsCodePro`, `DevType`, `OrgSize`, `LanguageHaveWorkedWith`, `Age`, `JobSat`, `ConvertedCompYearly`
- Key columns: `ConvertedCompYearly`, `YearsCodePro`, `EdLevel`, `DevType`

## Treatment / Predictor Definition
YearsCodePro as numeric predictor (clean string values to numbers).

## Background
ConvertedCompYearly is the outcome (USD, log-transform recommended). YearsCodePro contains years of professional experience (may have string values like 'Less than 1 year' — clean to numeric). EdLevel encodes education (e.g. Bachelor's, Master's, etc.). DevType is a multi-value field (may need multi-hot encoding or simplification). Filter to full-time employed developers with valid compensation data.

## Your Task
Conduct a regression analysis to answer the research question.

Steps:
1. Load and clean the data (handle missing values, parse string fields)
2. Create the treatment/predictor variable as described
3. Control for confounders: `EdLevel`, `DevType`, `OrgSize`
4. Fit a regression model (OLS for continuous outcome, logistic for binary)
5. Report the effect estimate with standard error and p-value
6. Discuss whether the relationship is likely causal

**Important**: Survey data has self-selection bias — be careful about
causal language. Report associations, not causal claims.

## Required Deliverables

### 1. `analysis.py`
A Python script that:
- Loads `data/stackoverflow.csv`
- Cleans and encodes variables
- Controls for confounders: `EdLevel`, `DevType`, `OrgSize`
- Fits the regression model
- Saves `results.json` and `report.md`

### 2. `results.json`
Must contain at minimum:
```json
{
  "analysis_type": "experience_salary",
  "years_exp_salary_coefficient": <float>,
  "r2": <value>,
  "n_observations": <int>
}
```

### 3. `report.md`
A brief (300–600 word) report covering:
- Data cleaning decisions (missing values, string parsing)
- Effect estimate and statistical significance
- Confounders controlled for
- **Limitations** (self-selection bias, survey design, missing data, etc.)

## Grading Criteria
1. `analysis.py` runs without error
2. Regression analysis implemented with controls
3. Key metric (`years_exp_salary_coefficient`) present in `results.json`
4. Key columns (`ConvertedCompYearly`, `YearsCodePro`, `EdLevel`, `DevType`) referenced in analysis code
5. At least one confounder (`EdLevel`, `DevType`, `OrgSize`) controlled for
6. `report.md` discusses limitations (survey bias, self-selection)
7. Data loaded correctly (correct row count)
8. `results.json` contains required fields and is valid JSON
