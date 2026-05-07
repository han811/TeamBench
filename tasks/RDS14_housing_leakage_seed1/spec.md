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

            - `SaleType`
- `MoSold`
- `YrSold`

            **Why this is wrong:**

            `SaleType` encodes the type of sale financing (Warranty Deed, New Construction, Contract Of Deed, etc.) — this is negotiated and decided at the time of sale. `MoSold` and `YrSold` capture when the sale occurred, which is unavailable before a sale has been agreed.

            The model includes `SaleType`, `MoSold`, and `YrSold` as predictor features. `SaleType` describes the financing mechanism decided at sale time. `MoSold` and `YrSold` record when the sale happened. All three are post-event features that inflate R² to ~0.91.

            ### Quantitative Impact

            | Condition | R² |
            |---|---|
            | Current (flawed — leakage) | ~0.91 |
            | After fix (correct) | ~0.85 |

            ## Required Fix

            Remove `SaleType`, `MoSold`, and `YrSold` from the feature list. Retrain using only pre-sale features. R² should drop to approximately 0.85.

            ### Specific Changes to `analysis.py`

            1. **Remove** the following features from `post_event_features` / `categorical_features`:
            - `SaleType`
- `MoSold`
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
