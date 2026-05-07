# RDS28: Life Expectancy Drop Investigation

## Background

WHO Global Health Observatory data shows that life expectancy in
**Syria, Yemen, Afghanistan** (SYR, YEM, AFG) dropped by approximately 4.2 years
during the period **2012–2017** — a decline not observed in
comparable countries over the same timeframe.

Your task is to investigate the root causes by synthesizing the WHO data
with three external evidence sources.

## Dataset

- File: `data/who_gho.csv`
- Rows: 264
- Key columns: `country`, `country_code`, `year`, `life_expectancy`,
  `infant_mortality`, `physicians_per_1000`, `health_expenditure_pct_gdp`,
  `income_group`, `region`

## Corpus Documents

Reference documents in `corpus/`:

| File | Description |
|------|-------------|
| `policy_timeline.md` | Healthcare policy changes timeline |
| `conflict_data.csv` | Armed conflict events with displacement data |
| `trade_sanctions.csv` | Economic sanctions and healthcare import impacts |

**Each document provides partial evidence.** You must connect the timeline
across all three to explain the magnitude of the life expectancy drop.

## Required Deliverables

### 1. `analysis.py`
- Load WHO data and quantify the life expectancy drop for affected countries
- Compare against a control group of similar-income, stable countries
- Read and analyze all three corpus documents
- Correlate each factor's timing with the observed mortality trends

### 2. `results.json`
```json
{
  "affected_countries": ["<code1>", ...],
  "life_exp_drop_years": <float>,
  "contributing_factors": ["<factor1>", "<factor2>", "<factor3>"],
  "primary_factor": "<string>",
  "counterfactual_comparison": "<description>"
}
```

### 3. `report.md`
400–700 words covering:
- Magnitude of decline vs comparable countries (counterfactual)
- Role of each factor with timeline evidence
- How the factors compound each other (interaction effects)
- Recommended policy interventions to reverse the trend

## Grading Criteria
1. `analysis.py` runs without error
2. Healthcare policy / defunding factor identified
3. Conflict / displacement factor identified
4. Sanctions / economic factor identified
5. `results.json` has `contributing_factors` with ≥ 2 entries
6. `report.md` establishes a causal timeline connecting factors
7. Data loaded correctly
8. `results.json` valid JSON with required fields
