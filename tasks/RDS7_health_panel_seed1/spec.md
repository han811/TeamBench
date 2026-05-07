# RDS7: WHO Health Panel Analysis

## Research Question
**How do life expectancy determinants differ across WHO regions? For the most recent year available, run a cross-sectional regression per region and compare which factors matter most in each region.**

## Dataset
- File: `data/who_gho.csv`
- Rows: 264 (WHO Global Health Observatory data)
- Columns: `country`, `country_code`, `year`, `life_expectancy`, `infant_mortality`, `under5_mortality`, `maternal_mortality`, `hiv_prevalence`, `physicians_per_1000`, `hospital_beds_per_1000`, `health_expenditure_pct_gdp`, `income_group`, `region`
- Key columns for this analysis: `life_expectancy`, `region`, `income_group`, `physicians_per_1000`, `infant_mortality`

## Background
Regional analysis reveals heterogeneity in the drivers of life expectancy. In high-income regions, marginal gains in physicians may matter less than in low-income regions. Use the most recent year with complete data. Run a separate regression per region (or use interaction terms). Compare R² and top predictors across regions.

## Method Hint
Filter to the most recent year, then run OLS by region. Report coefficients and R² per region.

## Your Task
Conduct a **Cross-Sectional Regional Analysis** to answer the research question.

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
- Runs the Cross-Sectional Regional Analysis analysis
- Saves `results.json` and `report.md`

### 2. `results.json`
Must contain at minimum:
```json
{
  "analysis_type": "cross_sectional",
  "avg_r2_across_regions": <float>,
  "regions_analyzed": <value>,
  "n_countries": <int>
}
```

### 3. `report.md`
A brief (300–600 word) report covering:
- Data cleaning decisions (missing data handling)
- Key findings: average R² across regional models
- Statistical evidence (coefficients, p-values, R²)
- **Limitations** (data quality, causality, confounding, etc.)

## Grading Criteria
1. `analysis.py` runs without error
2. Panel/regression/trend analysis implemented
3. Key metric (`avg_r2_across_regions`) present in `results.json`
4. Key columns (`life_expectancy`, `region`, `income_group`, `physicians_per_1000`, `infant_mortality`) referenced in analysis code
5. Country/region grouping or fixed effects present
6. `report.md` discusses limitations
7. Data loaded correctly (correct row count)
8. `results.json` contains required fields and is valid JSON
