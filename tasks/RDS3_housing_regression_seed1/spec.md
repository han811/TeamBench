            # RDS3: Ames Housing Regression — Feature Importance Analysis for SalePrice

            ## Dataset
            **File**: `data/ames_housing.csv`
            **Source**: Ames Housing dataset (Kaggle/OpenML, CC0)
            **Rows**: ~2,930 residential property sales in Ames, Iowa
            **Target variable**: `SalePrice` (continuous, USD)

            **Available columns** (16 total):
            `SalePrice`, `GrLivArea`, `OverallQual`, `YearBuilt`, `TotalBsmtSF`, `GarageCars`, `YearRemodAdd`, `TotRmsAbvGrd`, `OverallCond`, `Fireplaces`, `MSSubClass`, `LotFrontage`, `YrSold`, `GarageArea`, `FullBath`, `HeatingQC`

            ## Goal
            Identify which features most influence `SalePrice` using at least two different importance methods.

            ## Requirements
            1. **EDA**: Examine distributions, correlations, and missing values.
2. **Preprocessing**: Handle missing values; encode or drop categoricals as needed.
3. **Importance methods**: Apply **at least two** methods, e.g.:
   - Pearson / Spearman correlation ranking
   - Random Forest feature importances
   - Permutation importance
   - SHAP values
   - Lasso / ElasticNet coefficients (standardised)
4. **Multicollinearity**: Discuss any high correlations between top features
   (VIF or pairwise correlation matrix).
5. **Outliers**: Document any outlier removal in `report.md`.
6. **Random seed**: Set `random_state=42` (or equivalent) for all stochastic steps.
7. **Deliverables**: `analysis.py` (runnable script), `results.json` (ranked feature
   list from at least one method), `report.md` (narrative ≥ 200 words discussing
   multicollinearity and top features).


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
