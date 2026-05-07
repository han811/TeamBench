# RDS23: Ames Housing Price Prediction

## Task
Build a regression model to predict residential property sale prices using the
Ames, Iowa housing dataset.

## Dataset
- File: `data/housing.csv`
- Rows: 1465
- Target column: `SalePrice` (USD)
- Features include: lot area, neighborhood, building type, house style,
  overall quality/condition, year built, year remodeled, basement and living area,
  bathrooms, bedrooms, kitchen quality, garage capacity, utilities

## Your Task
1. Load and explore `data/housing.csv`
2. Perform feature engineering and data cleaning
3. Select relevant features and handle categorical variables
4. Train a regression model to predict `SalePrice`
5. Evaluate using RMSE and R² on a held-out test set (20% split, random_state=42)
6. Save results and a report

## Required Deliverables

### 1. `analysis.py`
A Python script that:
- Loads `data/housing.csv`
- Cleans and engineers features
- Trains a regression model and evaluates on a test split
- Saves `results.json` and `report.md`

### 2. `results.json`
Must contain at minimum:
```json
{
  "model": "<model name>",
  "rmse": <float>,
  "r2": <float>,
  "n_features": <int>,
  "n_train": <int>
}
```

### 3. `report.md`
A brief (200–400 word) report covering:
- Feature engineering decisions (which features were most useful)
- Any data quality issues discovered and how you handled them
- Model performance summary

## Grading Criteria
1. `analysis.py` runs without error
2. Implausible year values are corrected or handled
3. Extreme area outliers (LotArea or GrLivArea) are addressed
4. Zero-variance or near-constant features are removed from the model
5. Model RMSE is reasonable (< $100,000 or < 50% of mean SalePrice)
6. `results.json` contains required fields
7. Data loaded correctly (expected row count)
8. `report.md` discusses at least one data quality issue
