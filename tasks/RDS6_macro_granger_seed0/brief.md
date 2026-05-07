# RDS6: Macroeconomic Granger Causality (Brief)

Analyze the FRED macroeconomic dataset to test Granger causality.

**Dataset**: `data/fred_macro.csv`

**Question**: Does the unemployment rate Granger-cause the CPI inflation rate? Test whether past values of UNRATE improve forecasts of CPIAUCSL beyond what CPIAUCSL's own lags provide.

Produce:
- `analysis.py` — Granger causality analysis script
- `results.json` — test statistics and result
- `report.md` — findings and limitations
