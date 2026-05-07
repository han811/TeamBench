# RDS15: Circular Tip Percentage Calculation in NYC Taxi Data

## Overview

The workspace contains `analysis.py`, a tip percentage analysis using the
NYC Taxi dataset. The script computes tip statistics and saves
`results.json` and `report.md`. It runs without errors.

**However, the tip percentage formula is circular** — the denominator
(`total_amount`) includes the numerator (`tip_amount`), causing systematic
underestimation of tip rates.

## The Flaw

### Circular Formula

The following line appears in `analysis.py`:

```python
df['tip_pct'] = df['tip_amount'] / df['total_amount']
```

**Why this is wrong:**

The script computes tip percentage as `tip_amount / total_amount`. However, `total_amount` is defined as fare + surcharges + tip + tolls. Since tip is already included in the denominator, the formula systematically underestimates tip percentage. For a $2 tip on a $10 fare, the circular formula gives 2/12 = 16.7% instead of the correct 2/10 = 20.0%. The denominator is endogenous to the numerator.

### Numerical Example

| Trip | tip_amount | fare_amount | total_amount | Circular (tip/total) | Correct (tip/fare) |
|---|---|---|---|---|---|
| A | $2.00 | $10.00 | $12.50 | 16.0% | 20.0% |
| B | $3.00 | $12.00 | $15.50 | 19.4% | 25.0% |

The circular formula consistently underestimates tip generosity.

## Required Fix

Replace `tip_pct = tip_amount / total_amount` with `tip_pct = tip_amount / fare_amount` (or equivalently, `tip_amount / (total_amount - tip_amount)`). Use `fare_amount` as the base fare denominator. Filter rows where `fare_amount > 0` to avoid division by zero. The corrected mean tip percentage should rise from ~14% to ~18-20%.

### Specific Change to `analysis.py`

Replace:
```python
df['tip_pct'] = df['tip_amount'] / df['total_amount']
```

With:
```python
df['tip_pct'] = df['tip_amount'] / df['fare_amount']
```

Also add `df_filtered = df_filtered[df_filtered["fare_amount"] > 0].copy()`
to avoid division by zero.

## Deliverables

- Fixed `analysis.py` (corrected tip formula)
- `results.json` with `mean_tip_pct` >= 0.16 and `n_rows` key
- `report.md` that explains the circular formula issue

## Grading Rubric

| Check | Description |
|---|---|
| C1 | `tip_pct` uses `fare_amount` as denominator (not `total_amount`) |
| C2 | `results.json` contains `mean_tip_pct` key |
| C3 | `mean_tip_pct` in `results.json` >= 0.16 |
| C4 | `results.json` contains `n_rows` key |
| C5 | `report.md` mentions circular formula or denominator issue |
| C6 | `analysis.py` runs without error |
