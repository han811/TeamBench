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
df = df[df['education_num'] >= 10]  # keep only workers with some secondary education
```

This filter removes all rows where `education_num < 10`.

**Why this is wrong:**

Filtering to `education_num >= 10` removes approximately 45% of the dataset (workers with less than high-school-level education). These workers are disproportionately low-income, so excluding them inflates the apparent >50K income rate from 24.1% to 33.3% and biases every model coefficient that correlates with educational attainment.

### Quantitative Impact

| | Rows | >50K rate |
|---|---|---|
| Full dataset | 32,561 | 24.1% |
| After filter | 17,807 | 33.3% |

The filtered subset is systematically different from the population of interest,
making any conclusions drawn from it misleading.

## Required Fix

Remove the filter line. Instead, keep `education_num` as a covariate in the logistic regression model so the analysis represents the full working population.

### Specific Changes to `analysis.py`

1. **Remove** the filter line:
   ```python
   df = df[df['education_num'] >= 10]  # keep only workers with some secondary education
   ```
2. **Ensure** `education_num` appears in `num_features` or `cat_features` so it
   is used as a covariate in the logistic regression.
3. Re-run the analysis so `results.json` reflects the full dataset
   (`n_rows` should be approximately 32,561).
4. Update `report.md` to acknowledge the survivorship bias issue and explain
   what was fixed.

## Deliverables

- Fixed `analysis.py` (filter removed, `education_num` used as covariate)
- `results.json` with `n_rows >= 29,304` and a `model_results` key
- `report.md` that mentions the bias issue (must contain at least one of:
  bias, survivor, filter, removed, exclusion, subset)

## Grading Rubric

| Check | Description |
|---|---|
| C1 | Filter expression removed from `analysis.py` |
| C2 | `results.json` `n_rows` >= 29,304 |
| C3 | `education_num` present as covariate in `analysis.py` |
| C4 | `results.json` contains `model_results` key |
| C5 | `report.md` mentions survivorship bias |
| C6 | `analysis.py` runs without error |
