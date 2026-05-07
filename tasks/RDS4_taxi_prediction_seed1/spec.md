# RDS4: NYC Taxi Prediction

## Research Question
**What features best predict NYC yellow taxi trip duration? How do distance, time-of-day, and pickup/dropoff location affect duration?**

## Dataset
- File: `data/nyc_taxi.csv`
- Rows: 1500 (subsample of NYC TLC Yellow Taxi data)
- Columns: `VendorID`, `tpep_pickup_datetime`, `tpep_dropoff_datetime`, `passenger_count`, `trip_distance`, `RatecodeID`, `PULocationID`, `DOLocationID`, `payment_type`, `fare_amount`, `tip_amount`, `tolls_amount`, `total_amount`
- Target variable: `trip duration (minutes)`

## Feature Engineering
Compute trip duration in minutes from `tpep_pickup_datetime` and `tpep_dropoff_datetime`. Extract hour-of-day and day-of-week. Filter out trips with duration < 1 minute or > 180 minutes as outliers.

## Background
Trip duration depends heavily on distance but also on congestion. Pickup and dropoff location IDs encode geographic information. Rush hour (7-9am, 5-7pm weekdays) dramatically increases duration. The target must be computed from datetime columns — it is not directly in the data.

## Hint
Filter out extreme outliers: trips < 1 min or > 3 hours, distance < 0.1 miles.

## Your Task
Build a predictive model for `trip duration (minutes)`. You are free to choose
any appropriate regression method (linear regression, random forest, gradient
boosting, etc.). The key requirements are:

1. Engineer relevant features (datetime decomposition, filtering outliers)
2. Split data into train/test sets
3. Report RMSE on the held-out test set
4. Identify the most important predictors
5. Discuss findings and limitations

### Key Features to Include
At minimum, use: `trip_distance`, `PULocationID`, `DOLocationID`, `passenger_count`

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
  "target": "trip_duration_minutes",
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
4. Key features (`trip_distance`, `PULocationID`, `DOLocationID`, `passenger_count`) referenced in analysis code
5. Train/test split or cross-validation present
6. `report.md` discusses feature importance and limitations
7. Data loaded correctly (correct row count)
8. `results.json` contains required fields and is valid JSON
