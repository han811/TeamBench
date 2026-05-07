# RDS4: NYC Taxi Prediction

## Research Question
**What drives NYC yellow taxi fare amount — trip distance, trip duration, or the pickup/dropoff borough combination?**

## Dataset
- File: `data/nyc_taxi.csv`
- Rows: 1500 (subsample of NYC TLC Yellow Taxi data)
- Columns: `VendorID`, `tpep_pickup_datetime`, `tpep_dropoff_datetime`, `passenger_count`, `trip_distance`, `RatecodeID`, `PULocationID`, `DOLocationID`, `payment_type`, `fare_amount`, `tip_amount`, `tolls_amount`, `total_amount`
- Target variable: `fare amount (dollars)`

## Feature Engineering
Compute trip duration in minutes from the datetime columns. Use `RatecodeID` (rate code: 1=standard, 2=JFK, 3=Newark, 4=Nassau, 5=negotiated). Group `PULocationID` and `DOLocationID` into broad borough categories if possible, or use them as categorical features directly.

## Background
Fare amount follows a metered structure: $3 base + $0.70/0.2 mile. However RatecodeID creates special flat-rate zones (e.g. JFK flat $70). The interaction between distance and rate code matters. Decompose the variance explained by distance alone vs. additional location factors.

## Hint
Filter to standard rate (RatecodeID=1) and JFK (RatecodeID=2) trips for cleaner analysis.

## Your Task
Build a predictive model for `fare amount (dollars)`. You are free to choose
any appropriate regression method (linear regression, random forest, gradient
boosting, etc.). The key requirements are:

1. Engineer relevant features (datetime decomposition, filtering outliers)
2. Split data into train/test sets
3. Report R2 on the held-out test set
4. Identify the most important predictors
5. Discuss findings and limitations

### Key Features to Include
At minimum, use: `trip_distance`, `PULocationID`, `DOLocationID`, `RatecodeID`

## Required Deliverables

### 1. `analysis.py`
A Python script that:
- Loads `data/nyc_taxi.csv`
- Engineers features and filters outliers
- Trains a regression model with train/test split
- Reports R2 on the test set
- Saves `results.json` and `report.md`

### 2. `results.json`
Must contain at minimum:
```json
{
  "target": "fare_amount",
  "r2": <float>,
  "method": "<model name>",
  "n_train": <int>,
  "n_test": <int>,
  "top_features": [<feature names>]
}
```

### 3. `report.md`
A brief (300–600 word) report covering:
- Feature engineering decisions
- Model choice and R2 on test set
- Top predictors and their relative importance
- **Limitations** (data quality, generalizability, etc.)

## Grading Criteria
1. `analysis.py` runs without error
2. Feature engineering present (datetime or distance features)
3. Model performance metric (R2) reported in `results.json`
4. Key features (`trip_distance`, `PULocationID`, `DOLocationID`, `RatecodeID`) referenced in analysis code
5. Train/test split or cross-validation present
6. `report.md` discusses feature importance and limitations
7. Data loaded correctly (correct row count)
8. `results.json` contains required fields and is valid JSON
