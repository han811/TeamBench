# RDS18: Immortal Time Bias in Churn Analysis

## Overview

The workspace contains `analysis.py`, a customer churn analysis on the
Telco Churn dataset. It classifies customers as 'loyal (tenure > 12 months)' or
'new (tenure <= 12 months)' and compares their churn rates.
The script runs without errors and produces `results.json` and `report.md`.

**However, the analysis contains immortal time bias** — the 'loyal' group
classification criterion guarantees that these customers survived
`tenure > 12` months, creating an artificial immortal period
that inflates the apparent loyalty effect.

## The Flaw

### Immortal Time Bias

The analysis classifies customers with `tenure > 12` as 'loyal' and `tenure <= 12` as 'new', then compares churn rates. This introduces immortal time bias: every customer in the 'loyal' group is GUARANTEED to have survived at least 12 months without churning (otherwise they would be in the 'new' group). The low churn rate in the loyal group partially reflects this survival guarantee, not genuine loyalty.

### Quantitative Impact

| Group | Biased churn rate | Expected after fix |
|---|---|---|
| Loyal (loyal (tenure > 12 months)) | ~6% | >= 10% |
| New (new (tenure <= 12 months)) | ~35% | (similar) |

The biased analysis overstates the difference between groups because the
'loyal' group's low churn rate is partly a definitional artifact.

## Required Fix

Apply a landmark analysis: restrict the comparison to customers who reached month 12 (tenure >= 12). Among these customers, compare those who subsequently churned vs those who did not. This eliminates the immortal time period. Report churn rates for the landmark cohort.

### Specific Changes to `analysis.py`

1. **Apply landmark analysis**: filter the dataset to customers with
   `tenure >= 12` to form the landmark cohort.
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
