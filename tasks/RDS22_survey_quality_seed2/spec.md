# RDS22: Developer Satisfaction Predictors

## Task
Analyze the Stack Overflow Developer Survey to identify key predictors
of job satisfaction among software developers.

## Dataset
- File: `data/survey_responses.csv`
- Rows: 4000
- Target: `JobSat` — developer job satisfaction
- Features include: employment type, education level, years of coding experience,
  developer type, organization size, compensation, programming languages used

## Your Task
1. Load and explore `data/survey_responses.csv`
2. Prepare the satisfaction target and features for analysis
3. Identify the strongest predictors of job satisfaction
   (use regression, correlation analysis, or a classification model)
4. Quantify the relationship between compensation and satisfaction
5. Save results and a report

## Required Deliverables

### 1. `analysis.py`
A Python script that:
- Loads the survey data
- Handles data types, encoding, and missing values
- Identifies top predictors of job satisfaction
- Saves `results.json` and `report.md`

### 2. `results.json`
Must contain at minimum:
```json
{
  "top_predictors": [<str>, ...],
  "compensation_correlation": <float>,
  "n_valid_responses": <int>
}
```

### 3. `report.md`
A brief (300–500 word) report covering:
- Key predictors of developer satisfaction
- Relationship between compensation and satisfaction
- Any data quality issues discovered and how you handled them
- Limitations

## Grading Criteria
1. `analysis.py` runs without error
2. JobSat scale is harmonized (consistent numeric scale)
3. Extreme compensation outliers are handled
4. YearsCode / YearsCodePro values are validated and parsed correctly
5. At least one predictor of satisfaction is identified
6. `results.json` contains required fields
7. Data loaded correctly (expected row count)
8. `report.md` discusses a data quality issue
