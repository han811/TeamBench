"""
Generator for RDS14: Post-Event Feature Leakage in Housing Price Prediction.

Archetype 4 — Adversarial Workspace.

The workspace contains a COMPLETE, RUNNING regression analysis on the Ames
Housing dataset that includes post-event features (SaleCondition, MoSold,
YrSold) which leak information about the sale itself. R² is inflated.

Three seed variants using ames_housing dataset:

  Seed 0: Includes SaleCondition + MoSold + YrSold as features.
          R² ~0.92. Fix: remove these 3 post-event features. R² should drop to ~0.85.

  Seed 1: Includes SaleType + MoSold + YrSold.
          SaleType encodes the financing mechanism (WD, New, COD) — decided at sale.
          R² ~0.91. Fix: remove post-event features. R² drops to ~0.85.

  Seed 2: Includes SaleCondition + SaleType + YrSold.
          Both SaleCondition and SaleType are post-event.
          R² ~0.92. Fix: remove post-event features. R² drops to ~0.85.

The spec tells the agent exactly what the flaw is and how to fix it.
The brief is vague: "Review and validate the existing analysis."

Rubric (6 checks):
  C1 — Post-event features absent from feature list in analysis.py
  C2 — results.json exists with 'r2' key
  C3 — R² in results.json <= 0.90 (leakage removed)
  C4 — results.json contains 'n_features' key showing fewer features
  C5 — report.md mentions leakage / post-event / sale / removed
  C6 — analysis.py runs without error
"""
from __future__ import annotations

import textwrap

from generators.base import GeneratedTask
from generators.real_data_base import AdversarialWorkspaceGenerator

_VARIANTS = [
    {
        "seed": 0,
        "leaky_features": ["SaleCondition", "MoSold", "YrSold"],
        "leak_reason": (
            "`SaleCondition` (Normal/Abnorml/Partial/AdjLand/Alloca/Family) describes the "
            "condition of the sale itself — it is only known after the transaction. "
            "`MoSold` and `YrSold` capture seasonal and temporal market conditions at sale "
            "time, which are unavailable when making a pre-sale price prediction."
        ),
        "inflated_r2": 0.92,
        "expected_r2_max": 0.90,
        "bias_description": (
            "The model includes `SaleCondition`, `MoSold`, and `YrSold` as predictor "
            "features. These are all determined AT or AFTER the time of sale, meaning "
            "they cannot be known when predicting the price of a house that has not yet "
            "sold. Including them inflates R² to ~0.92 by giving the model access to "
            "sale-time information."
        ),
        "fix_description": (
            "Remove `SaleCondition`, `MoSold`, and `YrSold` from the feature list. "
            "Retrain the model using only features known before the sale occurs. "
            "R² should drop to approximately 0.85."
        ),
    },
    {
        "seed": 1,
        "leaky_features": ["SaleType", "MoSold", "YrSold"],
        "leak_reason": (
            "`SaleType` encodes the type of sale financing (Warranty Deed, New Construction, "
            "Contract Of Deed, etc.) — this is negotiated and decided at the time of sale. "
            "`MoSold` and `YrSold` capture when the sale occurred, which is unavailable "
            "before a sale has been agreed."
        ),
        "inflated_r2": 0.91,
        "expected_r2_max": 0.90,
        "bias_description": (
            "The model includes `SaleType`, `MoSold`, and `YrSold` as predictor features. "
            "`SaleType` describes the financing mechanism decided at sale time. `MoSold` "
            "and `YrSold` record when the sale happened. All three are post-event features "
            "that inflate R² to ~0.91."
        ),
        "fix_description": (
            "Remove `SaleType`, `MoSold`, and `YrSold` from the feature list. "
            "Retrain using only pre-sale features. R² should drop to approximately 0.85."
        ),
    },
    {
        "seed": 2,
        "leaky_features": ["SaleCondition", "SaleType", "YrSold"],
        "leak_reason": (
            "`SaleCondition` and `SaleType` both describe characteristics of the sale "
            "transaction itself — they are only known after a sale has occurred. `YrSold` "
            "records the year of sale, which is similarly post-event."
        ),
        "inflated_r2": 0.92,
        "expected_r2_max": 0.90,
        "bias_description": (
            "The model includes `SaleCondition`, `SaleType`, and `YrSold` — all post-event "
            "features determined at or after the sale. Including them inflates R² to ~0.92 "
            "because the model indirectly uses information about the sale outcome itself."
        ),
        "fix_description": (
            "Remove `SaleCondition`, `SaleType`, and `YrSold` from the feature list. "
            "Retrain using only features available before the sale. R² should drop to ~0.85."
        ),
    },
]


class Generator(AdversarialWorkspaceGenerator):
    task_id = "RDS14_housing_leakage"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]
    dataset_name = "ames_housing"
    dataset_license = "Public Domain"
    dataset_source = "Dean De Cock / Kaggle"

    def generate(self, seed: int) -> GeneratedTask:
        v = _VARIANTS[seed % len(_VARIANTS)]

        workspace_files = {
            "analysis.py": self._make_analysis_py(v),
            "requirements.txt": "pandas>=1.5\nnumpy>=1.23\nscikit-learn>=1.1\n",
            "check_solution.py": self._make_check_solution(v),
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._make_spec(v),
            brief_md=self._make_brief(v),
            expected={"leaky_features": v["leaky_features"], "seed": seed},
            workspace_files=workspace_files,
        )

    # ------------------------------------------------------------------
    # analysis.py — buggy regression with post-event features
    # ------------------------------------------------------------------

    def _make_analysis_py(self, v: dict) -> str:
        leaky = v["leaky_features"]
        leaky_repr = repr(leaky)

        return textwrap.dedent(f"""\
            \"\"\"
            Ames Housing price prediction analysis.

            Loads the ames_housing dataset, trains a Gradient Boosting regressor
            to predict SalePrice, and evaluates on a held-out test set.
            Saves results to results.json and report.md.
            \"\"\"
            import json
            import pathlib
            import numpy as np
            import pandas as pd
            from sklearn.ensemble import GradientBoostingRegressor
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import r2_score, mean_absolute_error
            from sklearn.preprocessing import LabelEncoder

            # ── Load data ────────────────────────────────────────────────────────────
            data_path = pathlib.Path(__file__).parent.parent / "datasets" / "ames_housing.csv"
            df = pd.read_csv(data_path, comment="#")

            target_col = "SalePrice"
            drop_cols = [target_col, "Id"] if "Id" in df.columns else [target_col]

            # ── Feature selection ─────────────────────────────────────────────────
            # Select numeric and key categorical features including sale-time info
            numeric_features = [
                "LotArea", "OverallQual", "OverallCond", "YearBuilt",
                "YearRemodAdd", "TotalBsmtSF", "GrLivArea", "FullBath",
                "BedroomAbvGr", "GarageCars", "GarageArea",
            ]
            # Post-event categorical features (describing the sale itself)
            post_event_features = {leaky_repr}
            categorical_features = post_event_features

            all_features = numeric_features + categorical_features
            available = [c for c in all_features if c in df.columns]

            df_model = df[available + [target_col]].dropna()

            for col in categorical_features:
                if col in df_model.columns:
                    df_model = df_model.copy()
                    df_model[col] = LabelEncoder().fit_transform(df_model[col].astype(str))

            X = df_model[[c for c in available if c in df_model.columns]].values
            y = np.log1p(df_model[target_col].values)

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )

            # ── Model ─────────────────────────────────────────────────────────────
            model = GradientBoostingRegressor(
                n_estimators=200, learning_rate=0.1, max_depth=4, random_state=42
            )
            model.fit(X_train, y_train)

            y_pred = model.predict(X_test)
            r2 = r2_score(y_test, y_pred)
            mae = mean_absolute_error(np.expm1(y_test), np.expm1(y_pred))

            # ── Save results ──────────────────────────────────────────────────────
            out_dir = pathlib.Path(__file__).parent
            feat_names = [c for c in available if c in df_model.columns]
            results = {{
                "n_rows": int(len(df_model)),
                "n_features": int(len(feat_names)),
                "features_used": feat_names,
                "r2": round(float(r2), 4),
                "mae": round(float(mae), 2),
            }}
            (out_dir / "results.json").write_text(
                json.dumps(results, indent=2), encoding="utf-8"
            )

            # ── Save report ───────────────────────────────────────────────────────
            report = f\"\"\"# Ames Housing Price Prediction Report

            ## Dataset
            - Source: ames_housing
            - Rows: {{len(df_model)}}
            - Features: {{len(feat_names)}}

            ## Model Performance
            - R²: {{r2:.4f}}
            - MAE: ${{mae:,.0f}}

            ## Features Used
            {{', '.join(feat_names)}}
            \"\"\"
            (out_dir / "report.md").write_text(report, encoding="utf-8")

            print(f"Rows          : {{len(df_model)}}")
            print(f"Features      : {{len(feat_names)}}")
            print(f"R²            : {{r2:.4f}}")
            print(f"MAE           : ${{mae:,.0f}}")
            print("Saved results.json and report.md")
        """)

    # ------------------------------------------------------------------
    # check_solution.py
    # ------------------------------------------------------------------

    def _make_check_solution(self, v: dict) -> str:
        leaky = v["leaky_features"]
        expected_r2_max = v["expected_r2_max"]

        checks = [
            {
                "id": "C1",
                "description": f"Post-event features {leaky} absent from feature list in analysis.py",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import pathlib, ast
                    src = (pathlib.Path(workspace_dir) / "analysis.py").read_text(encoding="utf-8")
                    leaky = {repr(leaky)}
                    still_present = [f for f in leaky if f in src
                                     and "remove" not in src.lower().split(f)[0][-50:]]
                    # Accept if none of the leaky features appear in a feature list context
                    in_feature_list = []
                    for feat in leaky:
                        # Check if the feature appears in a list-like structure (not just a comment)
                        lines_with_feat = [l.strip() for l in src.splitlines()
                                           if feat in l and not l.strip().startswith("#")]
                        if any('"' + feat + '"' in l or "'" + feat + "'" in l
                               for l in lines_with_feat):
                            in_feature_list.append(feat)
                    passed = len(in_feature_list) == 0
                    detail = f"post-event features still in feature lists: {{in_feature_list}}"
                """),
            },
            {
                "id": "C2",
                "description": "results.json exists with 'r2' key",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    rpath = pathlib.Path(workspace_dir) / "results.json"
                    if not rpath.exists():
                        passed = False
                        detail = "results.json not found"
                    else:
                        data = json.loads(rpath.read_text(encoding="utf-8"))
                        passed = "r2" in data
                        detail = f"keys present: {list(data.keys())}"
                """),
            },
            {
                "id": "C3",
                "description": f"R² in results.json <= {expected_r2_max} (leakage removed)",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import json, pathlib
                    rpath = pathlib.Path(workspace_dir) / "results.json"
                    if not rpath.exists():
                        passed = False
                        detail = "results.json not found"
                    else:
                        data = json.loads(rpath.read_text(encoding="utf-8"))
                        r2 = data.get("r2", 1.0)
                        passed = float(r2) <= {expected_r2_max}
                        detail = f"r2={{r2}} (need <= {expected_r2_max})"
                """),
            },
            {
                "id": "C4",
                "description": "results.json contains 'n_features' key",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    rpath = pathlib.Path(workspace_dir) / "results.json"
                    if not rpath.exists():
                        passed = False
                        detail = "results.json not found"
                    else:
                        data = json.loads(rpath.read_text(encoding="utf-8"))
                        passed = "n_features" in data
                        detail = f"n_features={data.get('n_features', 'missing')}"
                """),
            },
            {
                "id": "C5",
                "description": "report.md mentions leakage or post-event features",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    rpath = pathlib.Path(workspace_dir) / "report.md"
                    if not rpath.exists():
                        passed = False
                        detail = "report.md not found"
                    else:
                        content = rpath.read_text(encoding="utf-8").lower()
                        keywords = ["leakage", "leak", "post-event", "post event",
                                    "sale condition", "removed", "future information"]
                        found = [kw for kw in keywords if kw in content]
                        passed = len(found) >= 1
                        detail = f"found keywords: {found}"
                """),
            },
            {
                "id": "C6",
                "description": "analysis.py runs without error",
                "type": "script_runs",
                "path": "analysis.py",
                "timeout": 120,
            },
        ]

        return self.make_check_solution(checks)

    # ------------------------------------------------------------------
    # spec.md
    # ------------------------------------------------------------------

    def _make_spec(self, v: dict) -> str:
        leaky = v["leaky_features"]
        leak_reason = v["leak_reason"]
        bias_desc = v["bias_description"]
        fix_desc = v["fix_description"]
        inflated_r2 = v["inflated_r2"]
        expected_r2_max = v["expected_r2_max"]

        leaky_list = "\n".join(f"- `{f}`" for f in leaky)

        return textwrap.dedent(f"""\
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

            {leaky_list}

            **Why this is wrong:**

            {leak_reason}

            {bias_desc}

            ### Quantitative Impact

            | Condition | R² |
            |---|---|
            | Current (flawed — leakage) | ~{inflated_r2:.2f} |
            | After fix (correct) | ~0.85 |

            ## Required Fix

            {fix_desc}

            ### Specific Changes to `analysis.py`

            1. **Remove** the following features from `post_event_features` / `categorical_features`:
            {leaky_list}
            2. **Retrain** the model without these features.
            3. Re-run so `results.json` reflects the corrected R² (should be ≤ {expected_r2_max}).
            4. Update `report.md` to acknowledge the leakage issue.

            ## Deliverables

            - Fixed `analysis.py` (post-event features removed)
            - `results.json` with `r2` <= {expected_r2_max} and `n_features` key
            - `report.md` that mentions data leakage

            ## Grading Rubric

            | Check | Description |
            |---|---|
            | C1 | Post-event features absent from feature lists in `analysis.py` |
            | C2 | `results.json` contains `r2` key |
            | C3 | R² in `results.json` <= {expected_r2_max} |
            | C4 | `results.json` contains `n_features` key |
            | C5 | `report.md` mentions leakage or post-event features |
            | C6 | `analysis.py` runs without error |
        """)

    # ------------------------------------------------------------------
    # brief.md
    # ------------------------------------------------------------------

    def _make_brief(self, v: dict) -> str:
        return textwrap.dedent("""\
            # RDS14: Housing Price Prediction Review

            ## Task

            Review and validate the existing analysis in `analysis.py` for methodological issues.

            The script analyses the `ames_housing` dataset to predict house sale prices
            using a Gradient Boosting model. It currently runs without error and produces
            `results.json` and `report.md`.

            Your job is to identify any issues with the analysis methodology, fix them,
            and update the outputs accordingly.

            ## Files

            - `analysis.py` — the analysis script to review and fix
            - `results.json` — output (regenerated after fix)
            - `report.md` — summary report (update after fix)
            - `requirements.txt` — dependencies

            ## Deliverables

            1. Fixed `analysis.py`
            2. Regenerated `results.json`
            3. Updated `report.md` explaining what was wrong and what was fixed
        """)
