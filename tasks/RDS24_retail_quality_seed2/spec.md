# RDS24: Customer Segmentation from Retail Transactions

## Task
Segment customers by their purchase behavior using RFM (Recency, Frequency,
Monetary) analysis on the provided online retail transaction dataset.

## Dataset
- File: `data/transactions.csv`
- Rows: 30000
- Columns: InvoiceNo, StockCode, Description, Quantity, InvoiceDate,
  UnitPrice, CustomerID, Country
- Each row represents a line item in a retail transaction

## Your Task
1. Load and explore `data/transactions.csv`
2. Compute RFM metrics per customer:
   - **Recency**: days since last purchase
   - **Frequency**: number of unique invoices
   - **Monetary**: total spend
3. Clean and filter the data as needed before computing RFM
4. Segment customers into at least 2 groups (e.g., using K-means or
   quantile-based scoring)
5. Save results and a report

## Required Deliverables

### 1. `analysis.py`
A Python script that:
- Loads `data/transactions.csv`
- Cleans the data and computes RFM metrics per customer
- Segments customers and saves `results.json` and `report.md`

### 2. `results.json`
Must contain at minimum:
```json
{
  "n_customers": <int>,
  "n_segments": <int>,
  "segment_sizes": {<str>: <int>, ...},
  "rfm_stats": {
    "mean_recency": <float>,
    "mean_frequency": <float>,
    "mean_monetary": <float>
  }
}
```

### 3. `report.md`
A brief (300–500 word) report covering:
- Data cleaning decisions made before computing RFM
- Description of each customer segment
- Business recommendations for at least one segment
- Limitations

## Grading Criteria
1. `analysis.py` runs without error
2. Cancellation invoices (InvoiceNo starting with 'C') are excluded
3. Rows with missing CustomerID are excluded from segmentation
4. Zero or negative prices / quantities are handled
5. At least 2 customer segments are produced
6. `results.json` contains required fields
7. Data loaded correctly (expected row count)
8. `report.md` discusses at least one data quality issue
