# RDS10: Stack Overflow Survey Analysis

## Research Question
**Do developers who use Python or JavaScript report higher job satisfaction than those using other languages, after controlling for experience and salary?**

## Dataset
- File: `data/stackoverflow.csv`
- Rows: 1250 (subsample of Stack Overflow Developer Survey)
- Columns: `ResponseId`, `Employment`, `EdLevel`, `YearsCode`, `YearsCodePro`, `DevType`, `OrgSize`, `LanguageHaveWorkedWith`, `Age`, `JobSat`, `ConvertedCompYearly`
- Key columns: `JobSat`, `LanguageHaveWorkedWith`, `YearsCodePro`, `ConvertedCompYearly`

## Treatment / Predictor Definition
Create python_user and js_user binary indicators from semicolon-separated list.

## Background
LanguageHaveWorkedWith is a semicolon-separated list of languages. Create binary indicators: python_user=1 if 'Python' in the list, js_user=1 if 'JavaScript' in the list. JobSat is the outcome. Control for experience (YearsCodePro) and compensation (ConvertedCompYearly, log-transformed). Compare satisfaction across language groups with adjustment.

## Your Task
Conduct a regression analysis to answer the research question.

Steps:
1. Load and clean the data (handle missing values, parse string fields)
2. Create the treatment/predictor variable as described
3. Control for confounders: `YearsCodePro`, `ConvertedCompYearly`, `Employment`
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
- Controls for confounders: `YearsCodePro`, `ConvertedCompYearly`, `Employment`
- Fits the regression model
- Saves `results.json` and `report.md`

### 2. `results.json`
Must contain at minimum:
```json
{
  "analysis_type": "language_satisfaction",
  "python_effect_on_satisfaction": <float>,
  "js_effect_on_satisfaction": <value>,
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
3. Key metric (`python_effect_on_satisfaction`) present in `results.json`
4. Key columns (`JobSat`, `LanguageHaveWorkedWith`, `YearsCodePro`, `ConvertedCompYearly`) referenced in analysis code
5. At least one confounder (`YearsCodePro`, `ConvertedCompYearly`, `Employment`) controlled for
6. `report.md` discusses limitations (survey bias, self-selection)
7. Data loaded correctly (correct row count)
8. `results.json` contains required fields and is valid JSON
