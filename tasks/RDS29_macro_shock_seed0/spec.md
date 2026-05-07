# RDS29: Macroeconomic Inflation Shock Analysis

## Background

FRED macroeconomic data shows headline CPI (CPIAUCSL) spiked to
approximately **8.5% year-over-year** during
**2021-Q3 to 2022-Q2**. Economists debate whether this reflects
demand-side overheating or supply-side cost-push forces.

Your task is to determine the primary driver — supply vs. demand —
by synthesizing the FRED data with three corpus documents.

## Dataset

- File: `data/fred_macro.csv`
- Rows: 780 (monthly observations)
- Columns: `date`, `UNRATE` (unemployment rate, %), `CPIAUCSL` (CPI index),
  `FEDFUNDS` (federal funds rate, %), `GDP` (billions, quarterly)

## Corpus Documents

Reference documents in `corpus/`:

| File | Description |
|------|-------------|
| `fed_minutes.md` | FOMC meeting minutes excerpts for the shock period |
| `oil_prices.csv` | Monthly WTI/Brent crude and retail gasoline prices |
| `trade_balance.csv` | Monthly import/export data with import price index |

**The Fed minutes are critical**: they contain the committee's explicit
assessment of whether demand or supply was driving inflation. Use them
as primary qualitative evidence, cross-checked against the quantitative
oil and trade data.

## Required Deliverables

### 1. `analysis.py`
- Load FRED data and compute YoY CPI change to identify the shock period
- Read and synthesize all three corpus documents
- Test the demand hypothesis (UNRATE, GDP growth) and supply hypothesis
  (oil prices, import costs)
- Draw a conclusion about the primary inflation driver

### 2. `results.json`
```json
{
  "shock_period": "<period>",
  "cpi_peak_yoy": <float>,
  "inflation_drivers": {
    "supply_side": <bool>,
    "demand_side": <bool>
  },
  "primary_driver": "<string>",
  "evidence_sources": ["<source1>", "<source2>"]
}
```

### 3. `report.md`
400–700 words covering:
- CPI spike magnitude and timing
- Evidence FOR supply-side (oil prices, import costs)
- Evidence AGAINST demand-side (Fed minutes assessment, unemployment/GDP)
- Policy implications and Fed's response rationale

## Grading Criteria
1. `analysis.py` runs without error
2. Supply-side cause identified (oil prices or import costs)
3. Demand-side explanation evaluated and ruled out using Fed minutes
4. Oil price shock specifically cited as a factor
5. `results.json` has `inflation_drivers` with supply vs demand classification
6. `report.md` cites Fed minutes as evidence against demand explanation
7. Data loaded correctly
8. `results.json` valid JSON with required fields
