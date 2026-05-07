# RDS5: Retail Customer Lifetime Value

## Research Question
**Model purchase frequency per customer: fit a statistical model (e.g. negative binomial or Poisson regression) to explain the number of distinct invoices per customer over the observation period, and identify which customer characteristics (country, order size) drive frequency.**

## Dataset
- File: `data/online_retail.csv`
- Rows: 1500 (subsample of the UCI Online Retail dataset)
- Columns: `InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `UnitPrice`, `CustomerID`, `Country`
- Key columns for this analysis: `CustomerID`, `InvoiceNo`, `Country`, `Quantity`, `UnitPrice`

## Background
Purchase frequency varies widely across customers. Aggregate to the customer level: count distinct invoices, total spend, average order value, and country. Fit a count model (Poisson or negative binomial) to explain frequency. UK customers dominate the dataset. Exclude cancelled orders (InvoiceNo starting with 'C').

## Analysis Type
**Purchase Frequency Modeling**

## Your Task
Perform a `Purchase Frequency Modeling` on the retail transaction data.
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
- Saves `results.json`, `report.md`, and A CSV file `customer_features.csv` with per-customer aggregated features.

### 2. `results.json`
Must contain at minimum:
```json
{
  "analysis_type": "Purchase Frequency Modeling",
  "pseudo_r2": <float>,
  "n_customers": <int>,
  "n_transactions": <int>
}
```

### 3. `report.md`
A brief (300–600 word) report covering:
- Data cleaning decisions
- Key findings: pseudo R² of the frequency model
- Customer segments or model results
- **Limitations** (data quality, time horizon, etc.)

## Grading Criteria
1. `analysis.py` runs without error
2. RFM/cohort/frequency features computed correctly
3. Key metric (`pseudo_r2`) present in `results.json`
4. Key columns (`CustomerID`, `InvoiceNo`, `Country`, `Quantity`, `UnitPrice`) referenced in analysis code
5. Customer segmentation or grouping present
6. `report.md` discusses limitations
7. Data loaded correctly (correct row count)
8. `results.json` contains required fields and is valid JSON
