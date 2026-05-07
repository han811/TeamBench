# RDS18: Immortal Time Bias in Churn Analysis

## Overview

The workspace contains `analysis.py`, a customer churn analysis on the
Telco Churn dataset. It classifies customers as 'loyal (tenure > 24 months)' or
'new (tenure <= 24 months)' and compares their churn rates.
The script runs without errors and produces `results.json` and `report.md`.

**However, the analysis contains immortal time bias** — the 'loyal' group
classification criterion guarantees that these customers survived
`tenure > 24` months, creating an artificial immortal period
that inflates the apparent loyalty effect.

## The Flaw

### Immortal Time Bias

The analysis classifies customers with `tenure > 24` as 'loyal'. Every customer in this group has already survived 24 months — they cannot have churned before month 24 by definition. This immortal time of 24 months guarantees an artificially low apparent churn rate for 'loyal' customers, severely confounding the comparison.

### Quantitative Impact

| Group | Biased churn rate | Expected after fix |
|---|---|---|
| Loyal (loyal (tenure > 24 months)) | ~3% | >= 8% |
| New (new (tenure <= 24 months)) | ~32% | (similar) |

The biased analysis overstates the difference between groups because the
'loyal' group's low churn rate is partly a definitional artifact.

## Required Fix

Apply a landmark analysis at month 24: restrict to customers with `tenure >= 24`. Among this cohort, compare churners vs non-churners. The churn rates for long-tenure customers will be higher than the biased analysis suggests once the immortal period is removed.

### Specific Changes to `analysis.py`

1. **Apply landmark analysis**: filter the dataset to customers with
   `tenure >= 24` to form the landmark cohort.
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
| C3 | Corrected loyal churn rate >= 8% (bias reduced) |
| C4 | `results.json` contains a landmark cohort size key |
| C5 | `report.md` mentions immortal time bias or landmark analysis |
| C6 | `analysis.py` runs without error |
