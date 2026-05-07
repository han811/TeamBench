"""
Generator for RDS11: Survivorship Bias in Income Analysis.

Archetype 4 — Adversarial Workspace.

The workspace contains a COMPLETE, RUNNING logistic regression analysis
that silently applies a survivorship filter before computing statistics.
The script runs without error and produces results — but analyzes the
WRONG (filtered) subset, inflating apparent income rates.

Three seed variants using adult_income dataset:

  Seed 0: Filters education_num < 10 before analysis.
          Removes ~45% of rows (lower-educated workers who are lower income),
          inflating the >50K rate from 24.1% → 33.3%.

  Seed 1: Filters hours_per_week <= 20 before analysis.
          Removes ~9% of rows (part-time workers with only 6.7% >50K rate),
          inflating the >50K rate from 24.1% → 25.8%.

  Seed 2: Filters workclass == 'Private' only.
          Drops government workers (who have a smaller gender pay gap),
          subtly biasing gender-pay-gap coefficients upward.

The spec tells the agent exactly what the flaw is and how to fix it.
The brief is vague: "Review and validate the existing analysis."

Rubric (6 checks):
  C1 — The survivorship filter line is REMOVED from analysis.py
  C2 — Full dataset used: n_rows in results.json >= 90% of original
  C3 — Filter column used as covariate, not as filter
  C4 — results.json exists with a 'model_results' key
  C5 — report.md mentions bias / survivor / filter / removed
  C6 — analysis.py runs without error (script_runs)
"""
from __future__ import annotations

import textwrap

from generators.base import GeneratedTask
from generators.real_data_base import AdversarialWorkspaceGenerator

# ---------------------------------------------------------------------------
# Seed-variant definitions
# ---------------------------------------------------------------------------

_VARIANTS = [
    {
        "seed": 0,
        "dataset": "adult_income",
        "filter_col": "education_num",
        "filter_op": "<",
        "filter_val": 10,
        "filter_val_repr": "10",
        # Python expression used in the buggy analysis.py
        "filter_expr": "df['education_num'] < 10",
        "filter_line": "df = df[df['education_num'] >= 10]  # keep only workers with some secondary education",
        "covariate": "education_num",
        "target": "income",
        "target_positive": ">50K",
        "features": ["age", "education_num", "hours_per_week", "capital_gain", "capital_loss"],
        "cat_features": ["workclass", "marital_status", "occupation", "sex"],
        "original_n": 32561,
        "filtered_n": 17807,
        "original_rate_pct": 24.1,
        "filtered_rate_pct": 33.3,
        "bias_description": (
            "Filtering to `education_num >= 10` removes approximately 45% of the dataset "
            "(workers with less than high-school-level education). These workers are "
            "disproportionately low-income, so excluding them inflates the apparent >50K income "
            "rate from 24.1% to 33.3% and biases every model coefficient that correlates "
            "with educational attainment."
        ),
        "fix_description": (
            "Remove the filter line. Instead, keep `education_num` as a covariate in the "
            "logistic regression model so the analysis represents the full working population."
        ),
    },
    {
        "seed": 1,
        "dataset": "adult_income",
        "filter_col": "hours_per_week",
        "filter_op": "<=",
        "filter_val": 20,
        "filter_val_repr": "20",
        "filter_expr": "df['hours_per_week'] <= 20",
        "filter_line": "df = df[df['hours_per_week'] > 20]  # focus on full-time and near-full-time workers",
        "covariate": "hours_per_week",
        "target": "income",
        "target_positive": ">50K",
        "features": ["age", "education_num", "hours_per_week", "capital_gain", "capital_loss"],
        "cat_features": ["workclass", "marital_status", "occupation", "sex"],
        "original_n": 32561,
        "filtered_n": 29633,
        "original_rate_pct": 24.1,
        "filtered_rate_pct": 25.8,
        "bias_description": (
            "Filtering to `hours_per_week > 20` removes part-time workers. This group has a "
            "far lower >50K rate (6.7%) than the overall population (24.1%). Excluding them "
            "inflates the apparent income rate to 25.8% and severely biases the `hours_per_week` "
            "coefficient — the very variable being studied disappears from its own subgroup."
        ),
        "fix_description": (
            "Remove the filter line. Keep `hours_per_week` as a covariate in the regression "
            "so that part-time workers contribute to the estimate of how work hours affect income."
        ),
    },
    {
        "seed": 2,
        "dataset": "adult_income",
        "filter_col": "workclass",
        "filter_op": "==",
        "filter_val": "Private",
        "filter_val_repr": "'Private'",
        "filter_expr": "df['workclass'] == 'Private'",
        "filter_line": "df = df[df['workclass'] == 'Private']  # private-sector employees only for consistency",
        "covariate": "workclass",
        "target": "income",
        "target_positive": ">50K",
        "features": ["age", "education_num", "hours_per_week", "capital_gain", "capital_loss"],
        "cat_features": ["workclass", "marital_status", "occupation", "sex"],
        "original_n": 32561,
        "filtered_n": 22696,
        "original_rate_pct": 24.1,
        "filtered_rate_pct": 21.9,
        "bias_description": (
            "Filtering to private-sector workers only drops government employees (Federal, State, "
            "Local), who tend to have smaller gender pay gaps and higher rates of public-sector "
            "wage transparency. Excluding them inflates the estimated gender pay gap coefficient "
            "and prevents generalizing conclusions to the full workforce. The `workclass` variable "
            "is also silently excluded from the model, removing an important structural predictor."
        ),
        "fix_description": (
            "Remove the workclass filter. Include `workclass` as a categorical covariate in the "
            "logistic regression model so all employment sectors are represented and controlled for."
        ),
    },
]


class Generator(AdversarialWorkspaceGenerator):
    task_id = "RDS11_survivorship_bias"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]
    dataset_name = "adult_income"
    dataset_license = "CC BY 4.0"
    dataset_source = "UCI ML Repository"

    def generate(self, seed: int) -> GeneratedTask:
        v = _VARIANTS[seed % len(_VARIANTS)]

        analysis_py = self._make_analysis_py(v)
        check_py = self._make_check_solution(v)
        requirements_txt = "pandas>=1.5\nnumpy>=1.23\nscikit-learn>=1.1\n"

        workspace_files = {
            "analysis.py": analysis_py,
            "requirements.txt": requirements_txt,
            "check_solution.py": check_py,
        }

        spec_md = self._make_spec(v)
        brief_md = self._make_brief(v)

        expected = {
            "filter_col": v["filter_col"],
            "filter_op": v["filter_op"],
            "filter_val": v["filter_val"],
            "filter_line": v["filter_line"],
            "covariate": v["covariate"],
            "original_n": v["original_n"],
            "min_n_after_fix": int(v["original_n"] * 0.9),
            "dataset": v["dataset"],
            "seed": seed,
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # ------------------------------------------------------------------
    # analysis.py — the buggy but runnable script
    # ------------------------------------------------------------------

    def _make_analysis_py(self, v: dict) -> str:
        filter_col = v["filter_col"]
        filter_line = v["filter_line"]
        covariate = v["covariate"]
        cat_features = v["cat_features"]
        num_features = v["features"]
        target = v["target"]
        target_positive = v["target_positive"]
        dataset = v["dataset"]

        # Build covariate list: all numerics + cats (covariate already in num_features)
        num_feat_repr = repr(num_features)
        cat_feat_repr = repr(cat_features)

        return textwrap.dedent(f"""\
            \"\"\"
            Income analysis script.

            Loads the {dataset} dataset, fits a logistic regression model
            predicting high income (>{target_positive[1:]}), and saves results.
            \"\"\"
            import json
            import pathlib
            import numpy as np
            import pandas as pd
            from sklearn.linear_model import LogisticRegression
            from sklearn.preprocessing import LabelEncoder
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import roc_auc_score, accuracy_score

            # ── Load data ────────────────────────────────────────────────────────────
            data_path = pathlib.Path(__file__).parent.parent / "datasets" / "{dataset}.csv"
            df = pd.read_csv(data_path, comment="#")

            # ── Preprocessing filter ─────────────────────────────────────────────────
            {filter_line}

            # ── Feature engineering ──────────────────────────────────────────────────
            num_features = {num_feat_repr}
            cat_features = {cat_feat_repr}

            df = df.copy()
            for col in cat_features:
                df[col] = LabelEncoder().fit_transform(df[col].astype(str))

            feature_cols = [c for c in num_features + cat_features if c in df.columns]
            df["target"] = (df["{target}"].str.strip() == "{target_positive}").astype(int)

            X = df[feature_cols].fillna(0)
            y = df["target"]

            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42, stratify=y
            )

            # ── Model ────────────────────────────────────────────────────────────────
            model = LogisticRegression(max_iter=500, random_state=42)
            model.fit(X_train, y_train)

            y_pred_proba = model.predict_proba(X_test)[:, 1]
            y_pred = model.predict(X_test)
            auc = roc_auc_score(y_test, y_pred_proba)
            acc = accuracy_score(y_test, y_pred)

            coef_dict = dict(zip(feature_cols, model.coef_[0].tolist()))

            # ── Save results ─────────────────────────────────────────────────────────
            out_dir = pathlib.Path(__file__).parent
            results = {{
                "n_rows": int(len(df)),
                "positive_rate": float(y.mean()),
                "model_results": {{
                    "auc": round(float(auc), 4),
                    "accuracy": round(float(acc), 4),
                    "coefficients": {{k: round(v, 4) for k, v in coef_dict.items()}},
                    "features": feature_cols,
                }},
            }}
            (out_dir / "results.json").write_text(
                json.dumps(results, indent=2), encoding="utf-8"
            )

            # ── Save report ──────────────────────────────────────────────────────────
            report = f\"\"\"# Income Analysis Report

            ## Dataset
            - Source: {dataset}
            - Rows analysed: {{len(df)}}
            - Positive rate (>50K): {{y.mean():.1%}}

            ## Model Performance
            - AUC: {{auc:.4f}}
            - Accuracy: {{acc:.4f}}

            ## Coefficients
            \"\"\"
            for feat, coef in coef_dict.items():
                report += f"- {{feat}}: {{coef:+.4f}}\\n"
            (out_dir / "report.md").write_text(report, encoding="utf-8")

            print(f"Rows analysed : {{len(df)}}")
            print(f"Positive rate : {{y.mean():.1%}}")
            print(f"AUC           : {{auc:.4f}}")
            print(f"Accuracy      : {{acc:.4f}}")
            print("Saved results.json and report.md")
        """)

    # ------------------------------------------------------------------
    # check_solution.py — rubric grader
    # ------------------------------------------------------------------

    def _make_check_solution(self, v: dict) -> str:
        filter_expr = v["filter_expr"]
        covariate = v["covariate"]
        min_n = int(v["original_n"] * 0.9)
        filter_col = v["filter_col"]

        checks = [
            {
                "id": "C1",
                "description": "Survivorship filter line removed from analysis.py",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import pathlib
                    src = (pathlib.Path(workspace_dir) / "analysis.py").read_text(encoding="utf-8")
                    filter_expr = {repr(filter_expr)}
                    passed = filter_expr not in src
                    detail = "filter expression still present in analysis.py" if not passed else "filter removed"
                """),
            },
            {
                "id": "C2",
                "description": f"Full dataset used: n_rows >= {min_n} (90% of original {v['original_n']})",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import json, pathlib
                    rpath = pathlib.Path(workspace_dir) / "results.json"
                    if not rpath.exists():
                        passed = False
                        detail = "results.json not found"
                    else:
                        data = json.loads(rpath.read_text(encoding="utf-8"))
                        n = data.get("n_rows", 0)
                        passed = int(n) >= {min_n}
                        detail = f"n_rows={{n}} (need >= {min_n})"
                """),
            },
            {
                "id": "C3",
                "description": f"Filter column '{covariate}' used as covariate in analysis.py",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import pathlib, re
                    src = (pathlib.Path(workspace_dir) / "analysis.py").read_text(encoding="utf-8")
                    col = {repr(covariate)}
                    # Check that the column name appears in the feature lists (not only as a filter)
                    in_num = bool(re.search(r"num_features\\s*=\\s*\\[", src) and col in src)
                    in_cat = bool(re.search(r"cat_features\\s*=\\s*\\[", src) and col in src)
                    passed = bool(in_num or in_cat or (col in src and "feature" in src.lower()))
                    detail = "'" + col + "' covariate presence: " + str(passed)
                """),
            },
            {
                "id": "C4",
                "description": "results.json exists and contains 'model_results' key",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    rpath = pathlib.Path(workspace_dir) / "results.json"
                    if not rpath.exists():
                        passed = False
                        detail = "results.json not found"
                    else:
                        data = json.loads(rpath.read_text(encoding="utf-8"))
                        passed = "model_results" in data
                        detail = f"keys present: {list(data.keys())}"
                """),
            },
            {
                "id": "C5",
                "description": "report.md explains survivorship bias (mentions bias/survivor/filter/removed)",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib, re
                    rpath = pathlib.Path(workspace_dir) / "report.md"
                    if not rpath.exists():
                        passed = False
                        detail = "report.md not found"
                    else:
                        content = rpath.read_text(encoding="utf-8").lower()
                        keywords = ["bias", "survivor", "filter", "removed", "exclusion", "subset"]
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
        filter_col = v["filter_col"]
        filter_op = v["filter_op"]
        filter_val_repr = v["filter_val_repr"]
        filter_line = v["filter_line"]
        covariate = v["covariate"]
        original_n = v["original_n"]
        filtered_n = v["filtered_n"]
        original_rate = v["original_rate_pct"]
        filtered_rate = v["filtered_rate_pct"]
        bias_desc = v["bias_description"]
        fix_desc = v["fix_description"]

        return textwrap.dedent(f"""\
            # RDS11: Survivorship Bias in Income Analysis

            ## Overview

            The workspace contains `analysis.py`, a logistic regression analysis of the
            Adult Income (Census) dataset that predicts whether a worker earns >50K per year.
            The script runs without errors and produces `results.json` and `report.md`.

            **However, the analysis contains a survivorship bias flaw** that silently
            excludes a large portion of the dataset before modelling, distorting results.

            ## The Flaw

            ### Survivorship Filter

            The following line appears near the top of `analysis.py`:

            ```python
            {filter_line}
            ```

            This filter removes all rows where `{filter_col} {filter_op} {filter_val_repr}`.

            **Why this is wrong:**

            {bias_desc}

            ### Quantitative Impact

            | | Rows | >50K rate |
            |---|---|---|
            | Full dataset | {original_n:,} | {original_rate}% |
            | After filter | {filtered_n:,} | {filtered_rate}% |

            The filtered subset is systematically different from the population of interest,
            making any conclusions drawn from it misleading.

            ## Required Fix

            {fix_desc}

            ### Specific Changes to `analysis.py`

            1. **Remove** the filter line:
               ```python
               {filter_line}
               ```
            2. **Ensure** `{covariate}` appears in `num_features` or `cat_features` so it
               is used as a covariate in the logistic regression.
            3. Re-run the analysis so `results.json` reflects the full dataset
               (`n_rows` should be approximately {original_n:,}).
            4. Update `report.md` to acknowledge the survivorship bias issue and explain
               what was fixed.

            ## Deliverables

            - Fixed `analysis.py` (filter removed, `{covariate}` used as covariate)
            - `results.json` with `n_rows >= {int(original_n * 0.9):,}` and a `model_results` key
            - `report.md` that mentions the bias issue (must contain at least one of:
              bias, survivor, filter, removed, exclusion, subset)

            ## Grading Rubric

            | Check | Description |
            |---|---|
            | C1 | Filter expression removed from `analysis.py` |
            | C2 | `results.json` `n_rows` >= {int(original_n * 0.9):,} |
            | C3 | `{covariate}` present as covariate in `analysis.py` |
            | C4 | `results.json` contains `model_results` key |
            | C5 | `report.md` mentions survivorship bias |
            | C6 | `analysis.py` runs without error |
        """)

    # ------------------------------------------------------------------
    # brief.md
    # ------------------------------------------------------------------

    def _make_brief(self, v: dict) -> str:
        dataset = v["dataset"]
        return textwrap.dedent(f"""\
            # RDS11: Income Analysis Review

            ## Task

            Review and validate the existing analysis in `analysis.py` for methodological issues.

            The script analyses the `{dataset}` dataset to predict high-income earners
            using logistic regression. It currently runs without error and produces
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
