# RDS6: Macroeconomic Granger Causality

## Research Question
**Does the unemployment rate Granger-cause the CPI inflation rate? Test whether past values of UNRATE improve forecasts of CPIAUCSL beyond what CPIAUCSL's own lags provide.**

## Dataset
- File: `data/fred_macro.csv`
- Rows: 780 (monthly FRED macroeconomic time series)
- Columns: `date`, `UNRATE` (unemployment %), `CPIAUCSL` (CPI index),
  `FEDFUNDS` (federal funds rate %), `GDP` (billions USD, quarterly)
- Key columns for this analysis: `UNRATE`, `CPIAUCSL`

## Background
The Phillips Curve posits a trade-off between unemployment and inflation. Granger causality tests whether past unemployment helps predict future inflation. Both series must be stationary (use first differences or percent changes if needed). Choose lag length via AIC/BIC. Report the F-statistic and p-value for the null hypothesis that UNRATE does NOT Granger-cause CPIAUCSL.

## Lag Selection Hint
Try lags 1-4; use AIC to select optimal lag length.

## Your Task
Conduct a Granger causality analysis:

1. **Stationarity**: Test each series with ADF or KPSS. Transform if needed
   (first differences, percent changes, or log-differences).
2. **Lag selection**: Use AIC or BIC to choose the lag order.
3. **Granger test**: Run the Granger causality F-test (or use VAR model).
   Report F-statistic and p-value for H₀: `UNRATE` does NOT
   Granger-cause `CPIAUCSL`.
4. **Reverse test**: Also test the reverse direction for comparison.
5. **Interpretation**: Discuss whether the result supports the economic theory.

## Required Deliverables

### 1. `analysis.py`
A Python script that:
- Loads `data/fred_macro.csv`
- Handles stationarity (ADF test + transformation)
- Runs Granger causality test
- Saves `results.json` and `report.md`

### 2. `results.json`
Must contain at minimum:
```json
{
  "cause_var": "UNRATE",
  "effect_var": "CPIAUCSL",
  "granger_f_stat": <float>,
  "granger_p_value": <float>,
  "lag_order": <int>,
  "reject_null": <bool>
}
```

### 3. `report.md`
A brief (300–600 word) report covering:
- Stationarity tests and transformations applied
- Granger test result (F-stat, p-value, lag order)
- Economic interpretation
- **Limitations** (spurious regression, non-causation, structural breaks, etc.)

## Grading Criteria
1. `analysis.py` runs without error
2. Granger causality test or VAR model implemented
3. F-statistic and p-value reported in `results.json`
4. Key columns (`UNRATE`, `CPIAUCSL`) referenced in analysis code
5. Stationarity test (ADF or KPSS) present
6. `report.md` discusses limitations
7. Data loaded correctly (correct row count)
8. `results.json` contains required fields and is valid JSON
