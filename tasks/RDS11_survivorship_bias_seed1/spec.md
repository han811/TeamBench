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
df = df[df['hours_per_week'] > 20]  # focus on full-time and near-full-time workers
```

This filter removes all rows where `hours_per_week <= 20`.

**Why this is wrong:**

Filtering to `hours_per_week > 20` removes part-time workers. This group has a far lower >50K rate (6.7%) than the overall population (24.1%). Excluding them inflates the apparent income rate to 25.8% and severely biases the `hours_per_week` coefficient — the very variable being studied disappears from its own subgroup.

### Quantitative Impact

| | Rows | >50K rate |
|---|---|---|
| Full dataset | 32,561 | 24.1% |
| After filter | 29,633 | 25.8% |

The filtered subset is systematically different from the population of interest,
making any conclusions drawn from it misleading.

## Required Fix

Remove the filter line. Keep `hours_per_week` as a covariate in the regression so that part-time workers contribute to the estimate of how work hours affect income.

### Specific Changes to `analysis.py`

1. **Remove** the filter line:
   ```python
   df = df[df['hours_per_week'] > 20]  # focus on full-time and near-full-time workers
   ```
2. **Ensure** `hours_per_week` appears in `num_features` or `cat_features` so it
   is used as a covariate in the logistic regression.
3. Re-run the analysis so `results.json` reflects the full dataset
   (`n_rows` should be approximately 32,561).
4. Update `report.md` to acknowledge the survivorship bias issue and explain
   what was fixed.

## Deliverables

- Fixed `analysis.py` (filter removed, `hours_per_week` used as covariate)
- `results.json` with `n_rows >= 29,304` and a `model_results` key
- `report.md` that mentions the bias issue (must contain at least one of:
  bias, survivor, filter, removed, exclusion, subset)

## Grading Rubric

| Check | Description |
|---|---|
| C1 | Filter expression removed from `analysis.py` |
| C2 | `results.json` `n_rows` >= 29,304 |
| C3 | `hours_per_week` present as covariate in `analysis.py` |
| C4 | `results.json` contains `model_results` key |
| C5 | `report.md` mentions survivorship bias |
| C6 | `analysis.py` runs without error |
