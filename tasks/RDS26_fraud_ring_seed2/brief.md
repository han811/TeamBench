# RDS26: Fraud Ring Investigation (Brief)

Investigate an unusual fraud cluster in credit card transaction data.
Synthesize transaction patterns with corpus reference documents to
identify the fraud ring's signature.

**Dataset**: `data/credit_card_fraud.csv`

**Corpus docs** (in `corpus/`):
- `mcc_codes.csv`
- `holiday_calendar.csv`
- `fraud_intelligence.md`

Produce:
- `analysis.py` — investigation script
- `results.json` — fraud pattern summary
- `report.md` — findings and detection recommendations
