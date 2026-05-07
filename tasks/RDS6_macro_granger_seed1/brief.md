# RDS6: Macroeconomic Granger Causality (Brief)

Analyze the FRED macroeconomic dataset to test Granger causality.

**Dataset**: `data/fred_macro.csv`

**Question**: Does the federal funds rate Granger-cause the unemployment rate? Test whether past values of FEDFUNDS improve forecasts of UNRATE beyond what UNRATE's own lags provide.

Produce:
- `analysis.py` — Granger causality analysis script
- `results.json` — test statistics and result
- `report.md` — findings and limitations
