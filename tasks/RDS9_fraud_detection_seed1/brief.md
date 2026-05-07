# RDS9: Fraud Detection (Brief)

Detect credit card fraud under operational constraints.

**Dataset**: `data/credit_card_fraud.csv`

**Question**: Apply an unsupervised anomaly detection method (Isolation Forest or Local Outlier Factor) to detect fraud. Compare its precision and recall against a supervised baseline (logistic regression).

**Constraint**: No labels used during anomaly detection training

Produce:
- `analysis.py` — fraud detection script
- `results.json` — performance metrics
- `report.md` — findings and limitations
