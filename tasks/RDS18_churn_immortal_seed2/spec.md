# RDS18: Immortal Time Bias in Churn Analysis

## Overview

The workspace contains `analysis.py`, a customer churn analysis on the
Telco Churn dataset. It classifies customers as 'high-value (top MonthlyCharges quintile, tenure > 6)' or
'standard (remaining customers)' and compares their churn rates.
The script runs without errors and produces `results.json` and `report.md`.

**However, the analysis contains immortal time bias** — the 'loyal' group
classification criterion guarantees that these customers survived
`tenure > 6` months, creating an artificial immortal period
that inflates the apparent loyalty effect.

## The Flaw

### Immortal Time Bias

The analysis defines 'high-value' customers as those in the top quintile of MonthlyCharges AND with tenure > 6 months. The tenure > 6 filter introduces immortal time: high-value customers are guaranteed to have survived at least 6 months. Their lower apparent churn rate partly reflects this 6-month immortal window, not just their high-value status.

### Quantitative Impact

| Group | Biased churn rate | Expected after fix |
|---|---|---|
| Loyal (high-value (top MonthlyCharges quintile, tenure > 6)) | ~8% | >= 10% |
| New (standard (remaining customers)) | ~30% | (similar) |

The biased analysis overstates the difference between groups because the
'loyal' group's low churn rate is partly a definitional artifact.

## Required Fix

Apply a landmark analysis at month 6: restrict all comparisons to customers with `tenure >= 6`. Compare high-value vs standard customers within this landmark cohort. The churn gap will narrow once the immortal period is removed from both groups.

### Specific Changes to `analysis.py`

1. **Apply landmark analysis**: filter the dataset to customers with
   `tenure >= 6` to form the landmark cohort.
2. **Compare churn rates** within this cohort (rather than comparing
   different-tenure groups).
3. **Save** the landmark cohort size (`n_at_landmark`) and corrected
   churn rates (`landmark_churn_rates` or `corrected_loyal_churn_rate`)
   to `results.json`.
4. **Update `report.md`** to acknowledge immortal time bias and explain
   the landmark analysis fix.

## Deliverables

- Fixed `analysis.py` (landmark analysis applied)
- `results.json` with `landmark_churn_rates` or `corrected_loyal_churn_rate`
  key, and `n_at_landmark` key
- `report.md` that mentions immortal time bias

## Grading Rubric

| Check | Description |
|---|---|
| C1 | Landmark or survival-aware method in `analysis.py` |
| C2 | `results.json` contains `landmark_churn_rates` or `corrected_churn_rates` |
| C3 | Corrected loyal churn rate >= 10% (bias reduced) |
| C4 | `results.json` contains a landmark cohort size key |
| C5 | `report.md` mentions immortal time bias or landmark analysis |
| C6 | `analysis.py` runs without error |
