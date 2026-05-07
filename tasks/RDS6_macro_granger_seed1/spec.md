# RDS6: Macroeconomic Granger Causality

## Research Question
**Does the federal funds rate Granger-cause the unemployment rate? Test whether past values of FEDFUNDS improve forecasts of UNRATE beyond what UNRATE's own lags provide.**

## Dataset
- File: `data/fred_macro.csv`
- Rows: 780 (monthly FRED macroeconomic time series)
- Columns: `date`, `UNRATE` (unemployment %), `CPIAUCSL` (CPI index),
  `FEDFUNDS` (federal funds rate %), `GDP` (billions USD, quarterly)
- Key columns for this analysis: `FEDFUNDS`, `UNRATE`

## Background
Monetary policy theory suggests that raising interest rates increases unemployment (via reduced investment and consumption). Granger causality tests the predictive relationship. Both series should be tested for stationarity. The fed funds rate shows long trends and may need differencing. Unemployment is persistent — consider using changes.

## Lag Selection Hint
Monetary policy transmission lags suggest testing lags 2-8 quarters.

## Your Task
Conduct a Granger causality analysis:

1. **Stationarity**: Test each series with ADF or KPSS. Transform if needed
   (first differences, percent changes, or log-differences).
2. **Lag selection**: Use AIC or BIC to choose the lag order.
3. **Granger test**: Run the Granger causality F-test (or use VAR model).
   Report F-statistic and p-value for H₀: `FEDFUNDS` does NOT
   Granger-cause `UNRATE`.
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
  "cause_var": "FEDFUNDS",
  "effect_var": "UNRATE",
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
4. Key columns (`FEDFUNDS`, `UNRATE`) referenced in analysis code
5. Stationarity test (ADF or KPSS) present
6. `report.md` discusses limitations
7. Data loaded correctly (correct row count)
8. `results.json` contains required fields and is valid JSON
