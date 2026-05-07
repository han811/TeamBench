# RDS5: Retail Customer Lifetime Value

## Research Question
**Estimate Customer Lifetime Value using RFM (Recency, Frequency, Monetary) analysis. Segment customers into value tiers and identify the top 20% of customers by estimated CLV.**

## Dataset
- File: `data/online_retail.csv`
- Rows: 1500 (subsample of the UCI Online Retail dataset)
- Columns: `InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `UnitPrice`, `CustomerID`, `Country`
- Key columns for this analysis: `CustomerID`, `InvoiceDate`, `Quantity`, `UnitPrice`

## Background
RFM analysis uses three dimensions: Recency (days since last purchase), Frequency (number of transactions), and Monetary (total spend). CLV = Average Order Value × Purchase Frequency × Customer Lifespan. Customers should be segmented (e.g. quintiles or k-means) and the top value tier identified. Exclude cancelled orders (InvoiceNo starting with 'C').

## Analysis Type
**RFM-based CLV**

## Your Task
Perform a `RFM-based CLV` on the retail transaction data.
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
- Saves `results.json`, `report.md`, and A CSV file `customer_segments.csv` with CustomerID and CLV tier.

### 2. `results.json`
Must contain at minimum:
```json
{
  "analysis_type": "RFM-based CLV",
  "top_20pct_clv_share": <float>,
  "n_customers": <int>,
  "n_transactions": <int>
}
```

### 3. `report.md`
A brief (300–600 word) report covering:
- Data cleaning decisions
- Key findings: share of total CLV held by top 20% of customers
- Customer segments or model results
- **Limitations** (data quality, time horizon, etc.)

## Grading Criteria
1. `analysis.py` runs without error
2. RFM/cohort/frequency features computed correctly
3. Key metric (`top_20pct_clv_share`) present in `results.json`
4. Key columns (`CustomerID`, `InvoiceDate`, `Quantity`, `UnitPrice`) referenced in analysis code
5. Customer segmentation or grouping present
6. `report.md` discusses limitations
7. Data loaded correctly (correct row count)
8. `results.json` contains required fields and is valid JSON
