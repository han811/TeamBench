# RDS6: Macroeconomic Granger Causality (Brief)

Analyze the FRED macroeconomic dataset to test Granger causality.

**Dataset**: `data/fred_macro.csv`

**Question**: Does GDP growth Granger-cause CPI inflation? Test whether past GDP values improve forecasts of CPIAUCSL beyond what CPIAUCSL's own lags provide.

Produce:
- `analysis.py` — Granger causality analysis script
- `results.json` — test statistics and result
- `report.md` — findings and limitations
