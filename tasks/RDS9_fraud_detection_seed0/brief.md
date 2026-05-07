# RDS9: Fraud Detection (Brief)

Detect credit card fraud under operational constraints.

**Dataset**: `data/credit_card_fraud.csv`

**Question**: Train a logistic regression model and tune the classification threshold to achieve a false positive rate ≤ 1% while maximizing fraud recall. What is the maximum recall achievable under this FPR constraint?

**Constraint**: FPR ≤ 0.01

Produce:
- `analysis.py` — fraud detection script
- `results.json` — performance metrics
- `report.md` — findings and limitations
