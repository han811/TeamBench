# RDS21: WHO Health Indicator Trend Analysis

## Task
Analyze health indicator trends across countries using WHO Global Health
Observatory data, and summarize findings about global health progress.

## Dataset
- File: `data/health_indicators.csv`
- Rows: 92
- Columns: country, country_code, year, life_expectancy, infant_mortality,
  under5_mortality, maternal_mortality, physicians_per_1000,
  health_expenditure_pct_gdp, income_group
- Years covered: 2000–2020

## Your Task
1. Load and explore `data/health_indicators.csv`
2. Analyze trends over time for key indicators
3. Compare patterns across income groups (Low / Middle / High income)
4. Identify any countries with notable improvements or declines
5. Save results and a report

## Required Deliverables

### 1. `analysis.py`
A Python script that:
- Loads the health indicators data
- Handles missing values appropriately
- Computes trends per indicator and income group
- Saves `results.json` and `report.md`

### 2. `results.json`
Must contain at minimum:
```json
{
  "n_countries": <int>,
  "years_covered": [<int>, ...],
  "missing_pct": <float>,
  "top_improvers": [<str>, ...]
}
```

### 3. `report.md`
A brief (300–500 word) report covering:
- Key trends observed across indicators and income groups
- How missing data was handled and any patterns in missingness
- Notable outliers or anomalies encountered
- Limitations of the analysis

## Grading Criteria
1. `analysis.py` runs without error
2. Missing data pattern is analyzed or documented
3. Country name inconsistencies are addressed
4. Scale anomalies or outliers in indicators are detected/handled
5. Trend analysis produces meaningful output
6. `results.json` contains required fields
7. Data loaded correctly (expected row count)
8. `report.md` discusses missing data mechanism
