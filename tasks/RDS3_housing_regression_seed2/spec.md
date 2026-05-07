            # RDS3: Ames Housing Regression — Linear Regression Assumption Testing for SalePrice

            ## Dataset
            **File**: `data/ames_housing.csv`
            **Source**: Ames Housing dataset (Kaggle/OpenML, CC0)
            **Rows**: ~2,930 residential property sales in Ames, Iowa
            **Target variable**: `SalePrice` (continuous, USD)

            **Available columns** (14 total):
            `SalePrice`, `GrLivArea`, `OverallQual`, `YearBuilt`, `TotalBsmtSF`, `GarageCars`, `YearRemodAdd`, `ExterQual`, `BedroomAbvGr`, `LotFrontage`, `KitchenQual`, `YrSold`, `MoSold`, `HalfBath`

            ## Goal
            Assess whether linear regression is appropriate for `SalePrice` prediction by formally testing its core assumptions.

            ## Requirements
            1. **EDA**: Examine distributions, correlations, and missing values.
2. **Preprocessing**: Handle missing values; encode or drop categoricals as needed.
3. **Fit a baseline linear regression** (`random_state=42`) on the provided features.
4. **Test assumptions**:
   - *Normality of residuals*: Shapiro-Wilk test or Q-Q plot.
   - *Homoscedasticity*: Breusch-Pagan test or residuals-vs-fitted plot.
   - *Linearity*: Partial regression plots or RESET test.
5. **Propose corrections**: Based on findings, propose at least one remediation
   (e.g., log-transform target, Box-Cox, polynomial features, robust regression).
6. **Outliers**: Document influential observations (Cook's distance or leverage)
   in `report.md`.
7. **Random seed**: Set `random_state=42` for all stochastic steps.
8. **Deliverables**: `analysis.py` (runnable script), `results.json` (p-values or
   test statistics for each assumption test), `report.md` (narrative ≥ 200 words
   discussing findings and corrections).


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
