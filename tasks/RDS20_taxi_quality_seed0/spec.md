# RDS20: NYC Taxi Trip Analysis and Fare Prediction

## Task
Analyze NYC yellow taxi trip patterns and build a regression model to predict
fare amount from trip features.

## Dataset
- File: `data/taxi_trips.csv`
- Rows: 6000
- Target column: `fare_amount` (USD)
- Features include: pickup/dropoff datetimes, trip distance, location IDs,
  passenger count, payment type, rate code

## Your Task
1. Load and explore `data/taxi_trips.csv`
2. Engineer useful features (e.g., trip duration, hour of day, day of week)
3. Clean the data as needed
4. Train a regression model to predict `fare_amount`
5. Evaluate using RMSE and R² on a held-out test set (20% split, random_state=42)
6. Save results and a brief report

## Required Deliverables

### 1. `analysis.py`
A Python script that:
- Loads `data/taxi_trips.csv`
- Engineers features and cleans the data
- Trains a regression model and evaluates on a test split
- Saves `results.json` and `report.md`

### 2. `results.json`
Must contain at minimum:
```json
{
  "model": "<model name>",
  "rmse": <float>,
  "r2": <float>,
  "n_train": <int>,
  "n_test": <int>
}
```

### 3. `report.md`
A brief (200–400 word) report covering:
- Feature engineering decisions
- Any data quality issues discovered and how you handled them
- Model performance summary

## Grading Criteria
1. `analysis.py` runs without error
2. Invalid location IDs or geographic anomalies are addressed
3. Negative or zero fare amounts are handled
4. Duration or distance outliers are removed or flagged
5. RMSE is reasonable (< mean fare × 1.5)
6. `results.json` contains required fields
7. Data loaded correctly (expected row count)
8. `report.md` discusses at least one data quality issue
