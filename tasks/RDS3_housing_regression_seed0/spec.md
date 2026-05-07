            # RDS3: Ames Housing Regression — Predictive Modeling for SalePrice

            ## Dataset
            **File**: `data/ames_housing.csv`
            **Source**: Ames Housing dataset (Kaggle/OpenML, CC0)
            **Rows**: ~2,930 residential property sales in Ames, Iowa
            **Target variable**: `SalePrice` (continuous, USD)

            **Available columns** (20 total):
            `SalePrice`, `GrLivArea`, `OverallQual`, `YearBuilt`, `TotalBsmtSF`, `GarageCars`, `LotFrontage`, `OverallCond`, `HalfBath`, `TotRmsAbvGrd`, `Fireplaces`, `GarageArea`, `HeatingQC`, `MSSubClass`, `BedroomAbvGr`, `FullBath`, `MoSold`, `KitchenQual`, `YearRemodAdd`, `ExterQual`

            ## Goal
            Build the best predictive model you can for `SalePrice`. Evaluate on a held-out test set.

            ## Requirements
            1. **EDA**: Examine distributions, correlations, and missing values.
2. **Preprocessing**: Handle missing values; encode or drop categoricals as needed.
3. **Modelling**: Train **at least two different model types** (e.g., linear regression,
   random forest, gradient boosting, ridge, lasso, …).
4. **Evaluation**: Report RMSE and R² on a held-out 20 % test split (`random_state=42`).
5. **Comparison**: State which model performs best and why.
6. **Outliers**: Document any outlier removal or winsorisation steps in `report.md`.
7. **Random seed**: Set `random_state=42` (or equivalent) for all stochastic steps.
8. **Deliverables**: `analysis.py` (runnable script), `results.json` (RMSE and R² for
   each model), `report.md` (narrative discussion ≥ 200 words).


            ## Grading Rubric (8 criteria)

            | ID | Criterion | How to satisfy |
            |----|-----------|----------------|
            | C1 | Script runs | `analysis.py` executes end-to-end without uncaught exceptions |
            | C2 | EDA present | `analysis.py` contains at least one EDA operation (describe, histogram, scatter, correlation, etc.) |
            | C3 | Missing values handled | `analysis.py` explicitly addresses missing/null values (fillna, dropna, imputer, etc.) |
            | C4 | Uncertainty reported | `results.json` or `report.md` includes a numeric metric (RMSE, R², MAE, MSE, CI, etc.) |
            | C5 | Focus criteria met | See focus-specific requirement above |
            | C6 | Random seed set | `analysis.py` sets `random_state=42` or equivalent |
            | C7 | Outlier handling documented | `report.md` mentions outlier/leverage/influential observation strategy |
            | C8 | Report exists | `report.md` file is present |

            ## Deliverables
            - `analysis.py` — single runnable Python script
            - `results.json` — machine-readable metrics/findings
            - `report.md` — narrative write-up (≥ 200 words)

            ## Notes
            - The grading script is `check_solution.py`; run it to self-assess.
            - Do **not** modify `data/ames_housing.csv` or `check_solution.py`.
            - All stochastic operations must use `random_state=42`.
