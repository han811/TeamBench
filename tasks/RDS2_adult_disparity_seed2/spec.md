# RDS2: Adult Income Disparity Analysis

## Research Question
**Is there evidence of age-based income discrimination — specifically, do younger workers (18–35) earn significantly less than prime-age workers (36–55) after controlling for education and experience?**

## Dataset
- File: `data/adult_income.csv`
- Rows: 1302 (subsample of the UCI Adult Income dataset)
- Columns: `age`, `workclass`, `education`, `education_num`, `marital_status`, `occupation`, `sex`, `race`, `capital_gain`, `capital_loss`, `hours_per_week`, `income`
- Outcome: `income` encoded as `>50K` or `<=50K`

## Group Definition
- Protected attribute: `age_group`
- Reference group: `prime (36-55)`
- Comparison group: `young (18-35)`

## Background and Confounding
Younger workers earn less than prime-age workers. This may reflect genuine experience accumulation (human capital) rather than discrimination. education_num proxies years of schooling. Controlling for education_num and occupation isolates the age effect from human-capital accumulation. Create age groups: young=18-35, prime=36-55, older=56+.

## Your Task
Conduct a disparity analysis to estimate the income gap between groups
after controlling for relevant confounders. You are free to choose any
appropriate method, including but not limited to:
- Logistic regression with group indicator and controls
- Stratified analysis within levels of key confounders
- Propensity score matching or weighting
- Oaxaca-Blinder decomposition

**Do not report a naive unadjusted gap** — you must control for confounders.

### Confounders to Control For
At minimum, adjust for: `education_num`, `occupation`, `hours_per_week`, `workclass`

### Subgroup Analysis
Consider whether the age effect differs by occupation or workclass sector.

## Required Deliverables

### 1. `analysis.py`
A Python script that:
- Loads `data/adult_income.csv`
- Constructs the binary outcome (1 if income `>50K`, else 0)
- Computes both unadjusted and adjusted disparity estimates
- Reports a 95% confidence interval for the adjusted estimate
- Performs at least one subgroup or intersectional analysis
- Saves `results.json` and `report.md`

### 2. `results.json`
Must contain at minimum:
```json
{
  "group_var": "<protected attribute>",
  "disparity_estimate": <float>,
  "ci_lower": <float>,
  "ci_upper": <float>,
  "method": "<method name>",
  "unadjusted_gap": <float>,
  "adjusted_gap": <float>
}
```

### 3. `report.md`
A brief (300–600 word) report covering:
- Unadjusted vs. adjusted disparity estimates
- Method chosen and rationale
- Subgroup findings
- **Limitations** (unmeasured confounders, selection bias, etc.)

## Grading Criteria
Your solution is evaluated on:
1. `analysis.py` runs without error
2. Adjusted disparity is computed (control/adjust keywords in code)
3. Effect reported with confidence interval in `results.json`
4. Key confounders (`education_num`, `occupation`, `hours_per_week`, `workclass`) appear in analysis code
5. Subgroup or intersectional analysis is present
6. `report.md` discusses limitations
7. Data is loaded correctly (correct row count)
8. `results.json` contains required fields and is valid JSON
