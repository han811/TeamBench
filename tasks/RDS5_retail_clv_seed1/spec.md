# RDS5: Retail Customer Lifetime Value

## Research Question
**Perform a cohort retention analysis: for each monthly cohort (customers who made their first purchase in a given month), compute the month-over-month retention rate for the following 6 months.**

## Dataset
- File: `data/online_retail.csv`
- Rows: 1500 (subsample of the UCI Online Retail dataset)
- Columns: `InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `UnitPrice`, `CustomerID`, `Country`
- Key columns for this analysis: `CustomerID`, `InvoiceDate`, `InvoiceNo`

## Background
Cohort analysis groups customers by acquisition month. For each cohort, compute the percentage of customers who returned in subsequent months. A retention matrix (cohort × month offset) reveals how quickly customer engagement decays. Exclude cancelled orders (InvoiceNo starting with 'C').

## Analysis Type
**Cohort Retention Analysis**

## Your Task
Perform a `Cohort Retention Analysis` on the retail transaction data.
You must:
1. Clean the data (remove cancelled orders, handle missing CustomerIDs)
2. Aggregate transactions to the customer level
3. Compute the required metrics
4. Segment or model customers as described
5. Report key metrics in `results.json`

## Required Deliverables

### 1. `analysis.py`
A Python script that:
- Loads `data/online_retail.csv`
- Cleans data (removes cancellations, handles nulls)
- Performs the analysis described above
- Saves `results.json`, `report.md`, and A CSV file `retention_matrix.csv` with cohorts as rows and month offsets as columns.

### 2. `results.json`
Must contain at minimum:
```json
{
  "analysis_type": "Cohort Retention Analysis",
  "avg_month1_retention": <float>,
  "n_customers": <int>,
  "n_transactions": <int>
}
```

### 3. `report.md`
A brief (300–600 word) report covering:
- Data cleaning decisions
- Key findings: average month-1 retention rate across cohorts (fraction)
- Customer segments or model results
- **Limitations** (data quality, time horizon, etc.)

## Grading Criteria
1. `analysis.py` runs without error
2. RFM/cohort/frequency features computed correctly
3. Key metric (`avg_month1_retention`) present in `results.json`
4. Key columns (`CustomerID`, `InvoiceDate`, `InvoiceNo`) referenced in analysis code
5. Customer segmentation or grouping present
6. `report.md` discusses limitations
7. Data loaded correctly (correct row count)
8. `results.json` contains required fields and is valid JSON
