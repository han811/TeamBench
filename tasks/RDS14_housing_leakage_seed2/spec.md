            # RDS14: Post-Event Feature Leakage in Housing Price Prediction

            ## Overview

            The workspace contains `analysis.py`, a housing price prediction model
            trained on the Ames Housing dataset. The script trains a Gradient Boosting
            regressor and reports R² and MAE. It runs without errors.

            **However, the model includes post-event features** — variables that are
            only known after a sale has occurred — causing data leakage and inflating R².

            ## The Flaw

            ### Post-Event Features in the Model

            The following features are included in the model but are unavailable
            at prediction time (before the sale occurs):

            - `SaleCondition`
- `SaleType`
- `YrSold`

            **Why this is wrong:**

            `SaleCondition` and `SaleType` both describe characteristics of the sale transaction itself — they are only known after a sale has occurred. `YrSold` records the year of sale, which is similarly post-event.

            The model includes `SaleCondition`, `SaleType`, and `YrSold` — all post-event features determined at or after the sale. Including them inflates R² to ~0.92 because the model indirectly uses information about the sale outcome itself.

            ### Quantitative Impact

            | Condition | R² |
            |---|---|
            | Current (flawed — leakage) | ~0.92 |
            | After fix (correct) | ~0.85 |

            ## Required Fix

            Remove `SaleCondition`, `SaleType`, and `YrSold` from the feature list. Retrain using only features available before the sale. R² should drop to ~0.85.

            ### Specific Changes to `analysis.py`

            1. **Remove** the following features from `post_event_features` / `categorical_features`:
            - `SaleCondition`
- `SaleType`
- `YrSold`
            2. **Retrain** the model without these features.
            3. Re-run so `results.json` reflects the corrected R² (should be ≤ 0.9).
            4. Update `report.md` to acknowledge the leakage issue.

            ## Deliverables

            - Fixed `analysis.py` (post-event features removed)
            - `results.json` with `r2` <= 0.9 and `n_features` key
            - `report.md` that mentions data leakage

            ## Grading Rubric

            | Check | Description |
            |---|---|
            | C1 | Post-event features absent from feature lists in `analysis.py` |
            | C2 | `results.json` contains `r2` key |
            | C3 | R² in `results.json` <= 0.9 |
            | C4 | `results.json` contains `n_features` key |
            | C5 | `report.md` mentions leakage or post-event features |
            | C6 | `analysis.py` runs without error |
