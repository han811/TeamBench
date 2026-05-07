# RDS9: Fraud Detection (Brief)

Detect credit card fraud under operational constraints.

**Dataset**: `data/credit_card_fraud.csv`

**Question**: Frame fraud detection as a cost minimization problem. Assume: missing a fraud costs $500 (false negative), and a false alarm costs $10 (false positive). Find the classification threshold that minimizes total expected cost.

**Constraint**: FN cost = $500, FP cost = $10

Produce:
- `analysis.py` — fraud detection script
- `results.json` — performance metrics
- `report.md` — findings and limitations
