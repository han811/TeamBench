# RDS17: Spurious Regression on Non-Stationary Macro Time Series

## Overview

The workspace contains `analysis.py`, a regression analysis of FRED
macroeconomic data that regresses `UNRATE` (Unemployment Rate) on `FEDFUNDS`
(Federal Funds Rate) in levels. The script reports R²≈0.87 and
concludes a strong relationship. It runs without errors.

**However, this is a spurious regression** — both series are non-stationary
(I(1)), and the high R² reflects shared trend, not genuine economic signal.

## The Flaw

### Non-Stationary Levels Regression

Both the unemployment rate and the federal funds rate exhibit persistent trends and structural breaks over the sample period. Regressing unemployment on the fed funds rate without accounting for non-stationarity produces a spurious correlation driven by shared low-frequency movements, not any direct policy transmission mechanism.

### Stationarity Context

Both series fail the ADF stationarity test (p >> 0.05 in levels).

### Quantitative Impact

| Condition | R² |
|---|---|
| Current (levels regression — spurious) | ~0.87 |
| After fix (differenced series) | ~0.1–0.2 |

Granger (1974) showed that regressing two independent random walks produces
t-statistics that appear significant roughly 75% of the time even when the
series are completely unrelated.

## Required Fix

Apply first-differencing to both series before regression: `diff_y = y.diff().dropna()` and `diff_x = x.diff().dropna()`. Optionally run an ADF test (`statsmodels.tsa.stattools.adfuller`) to confirm non-stationarity before differencing. After differencing, R² should drop substantially.

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
