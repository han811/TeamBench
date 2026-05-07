# RDS4: NYC Taxi Prediction

## Research Question
**What features best predict tip amount for NYC yellow taxi trips? Specifically, how much do time-of-day, trip distance, and payment type contribute to tip size?**

## Dataset
- File: `data/nyc_taxi.csv`
- Rows: 1500 (subsample of NYC TLC Yellow Taxi data)
- Columns: `VendorID`, `tpep_pickup_datetime`, `tpep_dropoff_datetime`, `passenger_count`, `trip_distance`, `RatecodeID`, `PULocationID`, `DOLocationID`, `payment_type`, `fare_amount`, `tip_amount`, `tolls_amount`, `total_amount`
- Target variable: `tip amount (dollars)`

## Feature Engineering
Extract hour-of-day and day-of-week from `tpep_pickup_datetime`. Note: `payment_type=1` is credit card (tips recorded), `payment_type=2` is cash (tips typically not recorded). Consider whether to include or filter cash trips.

## Background
Tip amount is strongly influenced by fare amount (larger fares → larger tips). Credit card tips are systematically recorded while cash tips are not. Time-of-day matters: late-night and rush-hour trips may differ. A good model should handle the payment_type confound carefully.

## Hint
Consider filtering to credit card trips (payment_type=1) for reliable tip data.

## Your Task
Build a predictive model for `tip amount (dollars)`. You are free to choose
any appropriate regression method (linear regression, random forest, gradient
boosting, etc.). The key requirements are:

1. Engineer relevant features (datetime decomposition, filtering outliers)
2. Split data into train/test sets
3. Report RMSE on the held-out test set
4. Identify the most important predictors
5. Discuss findings and limitations

### Key Features to Include
At minimum, use: `trip_distance`, `fare_amount`, `payment_type`, `passenger_count`

## Required Deliverables

### 1. `analysis.py`
A Python script that:
- Loads `data/nyc_taxi.csv`
- Engineers features and filters outliers
- Trains a regression model with train/test split
- Reports RMSE on the test set
- Saves `results.json` and `report.md`

### 2. `results.json`
Must contain at minimum:
```json
{
  "target": "tip_amount",
  "rmse": <float>,
  "method": "<model name>",
  "n_train": <int>,
  "n_test": <int>,
  "top_features": [<feature names>]
}
```

### 3. `report.md`
A brief (300–600 word) report covering:
- Feature engineering decisions
- Model choice and RMSE on test set
- Top predictors and their relative importance
- **Limitations** (data quality, generalizability, etc.)

## Grading Criteria
1. `analysis.py` runs without error
2. Feature engineering present (datetime or distance features)
3. Model performance metric (RMSE) reported in `results.json`
4. Key features (`trip_distance`, `fare_amount`, `payment_type`, `passenger_count`) referenced in analysis code
5. Train/test split or cross-validation present
6. `report.md` discusses feature importance and limitations
7. Data loaded correctly (correct row count)
8. `results.json` contains required fields and is valid JSON
