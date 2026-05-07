# RDS6: Macroeconomic Granger Causality

## Research Question
**Does GDP growth Granger-cause CPI inflation? Test whether past GDP values improve forecasts of CPIAUCSL beyond what CPIAUCSL's own lags provide.**

## Dataset
- File: `data/fred_macro.csv`
- Rows: 780 (monthly FRED macroeconomic time series)
- Columns: `date`, `UNRATE` (unemployment %), `CPIAUCSL` (CPI index),
  `FEDFUNDS` (federal funds rate %), `GDP` (billions USD, quarterly)
- Key columns for this analysis: `GDP`, `CPIAUCSL`

## Background
Demand-pull inflation theory suggests that GDP growth (aggregate demand) drives up prices. However, GDP is quarterly while other series may be monthly — align frequencies carefully. Both series are non-stationary in levels; use percent changes (growth rates). Report whether the null of no Granger causality is rejected.

## Lag Selection Hint
GDP is quarterly — interpolate or aggregate other series to match frequency.

## Your Task
Conduct a Granger causality analysis:

1. **Stationarity**: Test each series with ADF or KPSS. Transform if needed
   (first differences, percent changes, or log-differences).
2. **Lag selection**: Use AIC or BIC to choose the lag order.
3. **Granger test**: Run the Granger causality F-test (or use VAR model).
   Report F-statistic and p-value for H₀: `GDP` does NOT
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
  "cause_var": "GDP",
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
4. Key columns (`GDP`, `CPIAUCSL`) referenced in analysis code
5. Stationarity test (ADF or KPSS) present
6. `report.md` discusses limitations
7. Data loaded correctly (correct row count)
8. `results.json` contains required fields and is valid JSON
