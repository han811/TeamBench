# RDS30: Retail Revenue Drop Diagnosis

## Background

Online retail transaction data shows a **19% revenue
decline** during **Q3 2011 (Jul–Sep)** relative to the prior year's
comparable period. The business stakeholders are puzzled because a major
marketing campaign was running at the time.

Your task is to diagnose the true root cause of the revenue drop.

## Dataset

- File: `data/online_retail.csv`
- Rows: 5000 (subsample)
- Columns: `InvoiceNo`, `StockCode`, `Description`, `Quantity`,
  `InvoiceDate`, `UnitPrice`, `CustomerID`, `Country`
- Revenue = `Quantity × UnitPrice` per line item

## Corpus Documents

Reference documents in `corpus/`:

| File | Description |
|------|-------------|
| `marketing_campaigns.csv` | Campaign schedule with dates, channels, and budgets |
| `inventory_levels.csv` | Stock levels by SKU and date, including stockout events |
| `customer_complaints.md` | Customer support complaint summary report |

**The diagnosis is counter-intuitive**: a marketing campaign was actively
running during the revenue drop. Do not assume the campaign failed.
Synthesize all three documents to identify the actual root cause.

## Required Deliverables

### 1. `analysis.py`
- Compute monthly/weekly revenue from transaction data
- Identify the revenue drop period and magnitude
- Read all three corpus documents
- Identify the top revenue-generating SKUs and check their inventory status
- Quantify the campaign-period overlap with the stockout event

### 2. `results.json`
```json
{
  "drop_period": "<period>",
  "revenue_drop_pct": <float>,
  "root_cause": "<string>",
  "stockout_skus": ["<sku1>", ...],
  "campaign_was_running": <bool>,
  "estimated_lost_revenue": <float>,
  "recommendation": "<string>"
}
```

### 3. `report.md`
400–700 words covering:
- Revenue decline magnitude and timing
- Why demand was NOT the issue (campaign was running, driving traffic)
- The stockout evidence and its timeline relative to the campaign
- Customer complaint evidence corroborating the diagnosis
- Estimated lost revenue and recommendation to prevent recurrence

## Grading Criteria
1. `analysis.py` runs without error
2. Stockout / inventory depletion identified
3. Marketing campaign overlap with revenue drop identified
4. Counter-intuitive diagnosis: campaign + stockout, not demand failure
5. `results.json` has `root_cause` indicating stockout/inventory
6. `report.md` quantifies or estimates lost revenue
7. Data loaded correctly
8. `results.json` valid JSON with required fields
