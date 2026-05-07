# RDS26: Fraud Ring Investigation

## Background

The fraud operations team has flagged an unusual cluster of fraudulent
transactions in the credit card dataset. Standard anomaly detection
models flagged elevated fraud rates, but the pattern is not explained
by the usual individual-cardholder indicators alone.

Your task is to identify the fraud ring's operational signature by
synthesizing evidence from the transaction data and three reference
documents.

## Dataset

- File: `data/credit_card_fraud.csv`
- Rows: 2500 (subsample)
- Columns: Time (seconds from first transaction), V1–V28 (PCA-transformed
  features), Amount (transaction amount), Class (1=fraud, 0=legitimate)

## Corpus Documents

Reference documents in `corpus/`:

| File | Description |
|------|-------------|
| `mcc_codes.csv` | Merchant category codes, descriptions, and fraud risk tiers |
| `holiday_calendar.csv` | Holiday and long-weekend dates with is_long_weekend flag |
| `fraud_intelligence.md` | Internal fraud intelligence report |

**No single document reveals the full pattern.** You must cross-reference
the intelligence report's claims against the calendar and MCC reference data,
then verify against the transaction data.

## Required Deliverables

### 1. `analysis.py`
- Load transaction data and compute basic fraud statistics
- Read all three corpus documents
- Identify the MCC category and temporal pattern consistent with the
  intelligence report
- Quantify how the fraud rate varies by identified dimensions

### 2. `results.json`
```json
{
  "overall_fraud_rate": <float>,
  "fraud_pattern": "<description of the cluster>",
  "target_merchant_category": "<mcc group>",
  "temporal_pattern": "<holiday/weekend/timing>",
  "ring_hypothesis": "<string>",
  "detection_rule": "<proposed rule>"
}
```

### 3. `report.md`
400–600 words covering:
- Statistical evidence for the anomalous cluster
- MCC and temporal signature
- Hypothesis about organized ring activity
- Proposed targeted detection rule or real-time monitoring approach

## Grading Criteria
1. `analysis.py` runs without error
2. MCC / merchant category pattern identified
3. Holiday / weekend temporal pattern identified
4. Organized ring hypothesis stated
5. `results.json` has `fraud_pattern` key
6. `report.md` proposes detection rule or monitoring
7. Data loaded correctly
8. `results.json` valid JSON with required fields
