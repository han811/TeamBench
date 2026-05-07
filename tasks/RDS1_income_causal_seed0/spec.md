# RDS1: Income Causal Analysis

## Research Question
**Does college education (Bachelor's degree or higher) causally increase the probability of earning more than $50,000 per year?**

## Dataset
- File: `data/adult_income.csv`
- Rows: 814 (subsample of the UCI Adult Income dataset)
- Columns: `age`, `workclass`, `education`, `education_num`, `marital_status`, `occupation`, `sex`, `capital_gain`, `capital_loss`, `hours_per_week`, `native_country`, `income`
- Outcome: `income` encoded as `>50K` or `<=50K`

## Treatment Definition
Create a binary treatment indicator: 1 if education is 'Bachelors', 'Masters', 'Doctorate', or 'Prof-school'; 0 otherwise.

## Background and Confounding
Education and income are strongly correlated, but this correlation may be confounded by age (older workers have more education and higher pay), hours worked, occupation type, and marital status (which affects household income reporting). A naive comparison overstates the causal effect.

## Your Task
Conduct a causal analysis to estimate the effect of the treatment on income.
You are free to choose any appropriate causal inference method, including but
not limited to:
- Regression adjustment (OLS / logistic regression with controls)
- Propensity score matching or weighting (IPW)
- Stratification on confounders
- Doubly robust estimation

**Do not use a naive unadjusted comparison** — you must address confounding.

### Confounders to Control For
At minimum, adjust for: `age`, `hours_per_week`, `occupation`, `marital_status`

## Required Deliverables

### 1. `analysis.py`
A Python script that:
- Loads `data/adult_income.csv`
- Constructs the binary treatment indicator
- Applies a causal method that controls for confounders
- Estimates the Average Treatment Effect (ATE) or Average Treatment Effect
  on the Treated (ATT) with a 95% confidence interval
- Tests at least one key assumption (e.g., covariate balance, overlap/positivity,
  or VIF for multicollinearity)
- Saves `results.json` and `report.md`

### 2. `results.json`
Must contain at minimum:
```json
{
  "treatment": "<treatment name>",
  "treatment_effect": <float>,
  "ci_lower": <float>,
  "ci_upper": <float>,
  "method": "<method name>",
  "n_treated": <int>,
  "n_control": <int>
}
```

### 3. `report.md`
A brief (300–600 word) report covering:
- Method chosen and rationale
- Point estimate and confidence interval
- Assumption checks performed and their results
- **Limitations** and threats to causal validity (unmeasured confounders,
  selection bias, SUTVA violations, etc.)

## Grading Criteria
Your solution is evaluated on:
1. `analysis.py` runs without error
2. Confounding is explicitly addressed in the code
3. Effect estimate is reported with confidence interval in `results.json`
4. Key confounders (`age`, `hours_per_week`, `occupation`, `marital_status`) appear in the analysis code
5. At least one assumption test is present
6. `report.md` discusses limitations
7. Data is loaded correctly (correct row count)
8. `results.json` contains required fields and is valid JSON
