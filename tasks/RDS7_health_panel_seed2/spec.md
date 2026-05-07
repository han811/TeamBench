# RDS7: WHO Health Panel Analysis

## Research Question
**How has life expectancy changed over time globally and by income group? Fit linear time trends for each income group and test whether trends differ significantly across groups.**

## Dataset
- File: `data/who_gho.csv`
- Rows: 264 (WHO Global Health Observatory data)
- Columns: `country`, `country_code`, `year`, `life_expectancy`, `infant_mortality`, `under5_mortality`, `maternal_mortality`, `hiv_prevalence`, `physicians_per_1000`, `hospital_beds_per_1000`, `health_expenditure_pct_gdp`, `income_group`, `region`
- Key columns for this analysis: `life_expectancy`, `year`, `income_group`, `region`

## Background
Global life expectancy has generally risen over decades, but the rate of improvement differs by income group. Low-income countries may show faster improvement (convergence) or slower (divergence). Fit OLS trend lines per income group: life_expectancy ~ year. Test whether slopes differ across groups using interaction terms or Chow test. Report the trend slope per income group.

## Method Hint
Use OLS with year as predictor, run separately per income group. Test for parallel trends.

## Your Task
Conduct a **Time Trend Analysis** to answer the research question.

Steps:
1. Load and clean the data (handle missing values, numeric types)
2. Perform the analysis as described
3. Report key findings with statistical evidence
4. Save `results.json` and `report.md`

## Required Deliverables

### 1. `analysis.py`
A Python script that:
- Loads `data/who_gho.csv`
- Handles missing data appropriately
- Runs the Time Trend Analysis analysis
- Saves `results.json` and `report.md`

### 2. `results.json`
Must contain at minimum:
```json
{
  "analysis_type": "time_trend",
  "trend_slope_low_income": <float>,
  "trend_slopes_by_group": <value>,
  "n_countries": <int>
}
```

### 3. `report.md`
A brief (300–600 word) report covering:
- Data cleaning decisions (missing data handling)
- Key findings: annual improvement in life expectancy for low-income countries
- Statistical evidence (coefficients, p-values, R²)
- **Limitations** (data quality, causality, confounding, etc.)

## Grading Criteria
1. `analysis.py` runs without error
2. Panel/regression/trend analysis implemented
3. Key metric (`trend_slope_low_income`) present in `results.json`
4. Key columns (`life_expectancy`, `year`, `income_group`, `region`) referenced in analysis code
5. Country/region grouping or fixed effects present
6. `report.md` discusses limitations
7. Data loaded correctly (correct row count)
8. `results.json` contains required fields and is valid JSON
