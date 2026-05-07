# RDS11: Survivorship Bias in Income Analysis

## Overview

The workspace contains `analysis.py`, a logistic regression analysis of the
Adult Income (Census) dataset that predicts whether a worker earns >50K per year.
The script runs without errors and produces `results.json` and `report.md`.

**However, the analysis contains a survivorship bias flaw** that silently
excludes a large portion of the dataset before modelling, distorting results.

## The Flaw

### Survivorship Filter

The following line appears near the top of `analysis.py`:

```python
df = df[df['workclass'] == 'Private']  # private-sector employees only for consistency
```

This filter removes all rows where `workclass == 'Private'`.

**Why this is wrong:**

Filtering to private-sector workers only drops government employees (Federal, State, Local), who tend to have smaller gender pay gaps and higher rates of public-sector wage transparency. Excluding them inflates the estimated gender pay gap coefficient and prevents generalizing conclusions to the full workforce. The `workclass` variable is also silently excluded from the model, removing an important structural predictor.

### Quantitative Impact

| | Rows | >50K rate |
|---|---|---|
| Full dataset | 32,561 | 24.1% |
| After filter | 22,696 | 21.9% |

The filtered subset is systematically different from the population of interest,
making any conclusions drawn from it misleading.

## Required Fix

Remove the workclass filter. Include `workclass` as a categorical covariate in the logistic regression model so all employment sectors are represented and controlled for.

### Specific Changes to `analysis.py`

1. **Remove** the filter line:
   ```python
   df = df[df['workclass'] == 'Private']  # private-sector employees only for consistency
   ```
2. **Ensure** `workclass` appears in `num_features` or `cat_features` so it
   is used as a covariate in the logistic regression.
3. Re-run the analysis so `results.json` reflects the full dataset
   (`n_rows` should be approximately 32,561).
4. Update `report.md` to acknowledge the survivorship bias issue and explain
   what was fixed.

## Deliverables

- Fixed `analysis.py` (filter removed, `workclass` used as covariate)
- `results.json` with `n_rows >= 29,304` and a `model_results` key
- `report.md` that mentions the bias issue (must contain at least one of:
  bias, survivor, filter, removed, exclusion, subset)

## Grading Rubric

| Check | Description |
|---|---|
| C1 | Filter expression removed from `analysis.py` |
| C2 | `results.json` `n_rows` >= 29,304 |
| C3 | `workclass` present as covariate in `analysis.py` |
| C4 | `results.json` contains `model_results` key |
| C5 | `report.md` mentions survivorship bias |
| C6 | `analysis.py` runs without error |
