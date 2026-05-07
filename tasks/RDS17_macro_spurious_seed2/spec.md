# RDS17: Spurious Regression on Non-Stationary Macro Time Series

## Overview

The workspace contains `analysis.py`, a regression analysis of FRED
macroeconomic data that regresses `M2SL` (M2 Money Supply) on `GDP`
(GDP) in levels. The script reports R²≈0.98 and
concludes a strong relationship. It runs without errors.

**However, this is a spurious regression** — both series are non-stationary
(I(1)), and the high R² reflects shared trend, not genuine economic signal.

## The Flaw

### Non-Stationary Levels Regression

Both M2 money supply and GDP grow exponentially over time. Their levels regression yields R²≈0.98 almost entirely because both series trend upward together — a hallmark of spurious regression. Any two series that grow over time will show high R² in levels regardless of whether they are economically linked.

### Stationarity Context

Both M2 and GDP levels are I(1) — they fail the ADF test in levels but pass after differencing.

### Quantitative Impact

| Condition | R² |
|---|---|
| Current (levels regression — spurious) | ~0.98 |
| After fix (differenced series) | ~0.1–0.2 |

Granger (1974) showed that regressing two independent random walks produces
t-statistics that appear significant roughly 75% of the time even when the
series are completely unrelated.

## Required Fix

Apply log-differencing (growth rates): `diff_y = np.log(y).diff().dropna()` and `diff_x = np.log(x).diff().dropna()`. This converts the series to stationary growth rates. Regress the growth rates on each other. R² should drop to ~0.1-0.3 reflecting only genuine co-movement.

### Specific Changes to `analysis.py`

1. **Apply first-differences** (or log-differences for exponential series):
   ```python
   diff_y = df_clean[y_col].diff().dropna()
   diff_x = df_clean[x_col].diff().dropna()
   ```
2. **Regress** `diff_y` on `diff_x` instead of the levels.
3. **Update** `results.json` with the corrected R² and set `method` to
   indicate differencing (e.g. `"first_difference"` or `"log_difference"`).
4. **Update** `report.md` to acknowledge the spurious regression issue and
   explain the stationarity fix.

## Deliverables

- Fixed `analysis.py` (differencing applied)
- `results.json` with `r2` <= 0.5 and `method` indicating differencing
- `report.md` that mentions spurious regression or non-stationarity

## Grading Rubric

| Check | Description |
|---|---|
| C1 | Differencing or stationarity test present in `analysis.py` |
| C2 | `results.json` contains `r2` key |
| C3 | R² in `results.json` <= 0.5 |
| C4 | `results.json` `method` field indicates differencing |
| C5 | `report.md` mentions spurious regression or non-stationarity |
| C6 | `analysis.py` runs without error |
