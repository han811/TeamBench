# RDS12: Simpson's Paradox in Income Analysis

## Overview

The workspace contains `analysis.py`, an analysis of the Adult Income
(Census) dataset that computes aggregate income rates by sex.
The script runs without errors and produces `results.json` and `report.md`.

**However, the analysis suffers from Simpson's Paradox** — it reports
aggregate statistics that conceal a reversal when data are properly
stratified by `marital_status`.

## The Flaw

### Missing Stratification

The aggregate mean hours_per_week by sex shows women work fewer hours. However, within each marital-status group women work MORE hours than men in the same group. This reversal — a Simpson's paradox driven by the strong correlation between marital status and sex — is hidden by the aggregate figure.

### Why This Matters

Simpson's Paradox occurs when a trend that appears in aggregate data
disappears or reverses when the data are split into subgroups. The
confounding variable (`marital_status`) is correlated with both the
grouping variable (`sex`) and the outcome (`income`), causing the
aggregate statistic to be misleading.

Reporting only aggregate rates leads to incorrect conclusions about the
relationship between sex and income.

## Required Fix

Add stratification by marital_status. Compute mean hours_per_week for each (marital_status, sex) pair and store these in `results.json` under `stratified_results`. Show that the aggregate direction reverses within strata.

### Specific Changes to `analysis.py`

1. **Add stratification** by `marital_status` — compute income rates (or the
   relevant metric) for each combination of `marital_status` and `sex`.
2. **Store stratified results** in `results.json` under the key
   `stratified_results` (a list of dicts with the group columns and values).
3. **Update `report.md`** to acknowledge the Simpson's Paradox, show
   both aggregate and stratified results, and draw the correct conclusion.

## Deliverables

- Fixed `analysis.py` (stratification added)
- `results.json` with both `aggregate_results` and `stratified_results` keys
- `report.md` that mentions Simpson's paradox or stratification

## Grading Rubric

| Check | Description |
|---|---|
| C1 | Stratification code present in `analysis.py` |
| C2 | `results.json` contains `stratified_results` key |
| C3 | `marital_status` and `sex` used together in groupby/analysis |
| C4 | `results.json` contains `aggregate_results` key |
| C5 | `report.md` mentions Simpson's paradox or stratification |
| C6 | `analysis.py` runs without error |
