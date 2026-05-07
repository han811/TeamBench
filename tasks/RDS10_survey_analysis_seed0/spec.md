# RDS10: Stack Overflow Survey Analysis

## Research Question
**Does remote work predict higher job satisfaction among developers, after controlling for compensation (ConvertedCompYearly) and employment type?**

## Dataset
- File: `data/stackoverflow.csv`
- Rows: 1250 (subsample of Stack Overflow Developer Survey)
- Columns: `ResponseId`, `Employment`, `EdLevel`, `YearsCode`, `YearsCodePro`, `DevType`, `OrgSize`, `LanguageHaveWorkedWith`, `Age`, `JobSat`, `ConvertedCompYearly`
- Key columns: `JobSat`, `Employment`, `ConvertedCompYearly`, `EdLevel`

## Treatment / Predictor Definition
Create a binary: 1 if Employment contains 'remote', 0 otherwise (case-insensitive).

## Background
JobSat is the outcome variable (job satisfaction). Employment column contains information about remote/hybrid/in-person work arrangements. ConvertedCompYearly is compensation in USD. A naive comparison of remote vs. in-person may be confounded by salary (remote workers may earn more) and employment type. Create a binary remote indicator from Employment field. Control for ConvertedCompYearly (log-transform recommended) and EdLevel.

## Your Task
Conduct a regression analysis to answer the research question.

Steps:
1. Load and clean the data (handle missing values, parse string fields)
2. Create the treatment/predictor variable as described
3. Control for confounders: `ConvertedCompYearly`, `EdLevel`, `YearsCodePro`
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
- Controls for confounders: `ConvertedCompYearly`, `EdLevel`, `YearsCodePro`
- Fits the regression model
- Saves `results.json` and `report.md`

### 2. `results.json`
Must contain at minimum:
```json
{
  "analysis_type": "remote_satisfaction",
  "remote_effect_on_satisfaction": <float>,
  "p_value": <value>,
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
3. Key metric (`remote_effect_on_satisfaction`) present in `results.json`
4. Key columns (`JobSat`, `Employment`, `ConvertedCompYearly`, `EdLevel`) referenced in analysis code
5. At least one confounder (`ConvertedCompYearly`, `EdLevel`, `YearsCodePro`) controlled for
6. `report.md` discusses limitations (survey bias, self-selection)
7. Data loaded correctly (correct row count)
8. `results.json` contains required fields and is valid JSON
