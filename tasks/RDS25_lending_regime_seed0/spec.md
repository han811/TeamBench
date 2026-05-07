# RDS25: Lending Model Performance Investigation

## Background

A logistic regression model was trained on Lending Club loan data from
**2016-01 to 2017-12** to predict
loan defaults. In the recent period (**2018-01 to
2018-12**) the model's AUC dropped from 0.78 to 0.61.

Your task is to investigate WHY model performance degraded.

## Dataset

- File: `data/lending_club.csv`
- Rows: 2000 (subsample)
- Key columns: `loan_amnt`, `int_rate`, `grade`, `dti`, `fico_range_low`,
  `annual_inc`, `default_ind`, `verification_status`

## Corpus Documents

Additional reference documents are provided in `corpus/`:

| File | Description |
|------|-------------|
| `interest_rates.csv` | Monthly Fed funds rate, prime rate, 10yr treasury |
| `state_unemployment.csv` | State-level unemployment by year and quarter |
| `policy_changes.md` | Internal underwriting policy change bulletin |

**Important**: No single document fully explains the performance drop.
You must synthesize evidence across all three sources.

## Required Deliverables

### 1. `analysis.py`
A Python script that:
- Loads the loan dataset and compares default rates baseline vs recent periods
- Reads and analyzes all three corpus documents
- Identifies distributional shifts in loan features between periods
- Quantifies the contribution of each identified factor

### 2. `results.json`
```json
{
  "baseline_default_rate": <float>,
  "recent_default_rate": <float>,
  "drift_factors": ["<factor1>", "<factor2>", ...],
  "primary_cause": "<string>",
  "recommendation": "<string>"
}
```

### 3. `report.md`
A 400–700 word report explaining:
- What changed between baseline and recent periods
- Which external factors drove the regime shift
- Why the model degraded (not just what degraded)
- Recommended remediation (recalibration, retrain, monitoring)

## Grading Criteria
1. `analysis.py` runs without error
2. Interest rate / rate hike factor identified
3. Unemployment spike factor identified
4. Policy / underwriting change factor identified
5. `results.json` contains `drift_factors` with ≥ 2 entries
6. `report.md` recommends recalibration or retraining
7. Data loaded correctly (correct row count)
8. `results.json` is valid JSON with required fields
