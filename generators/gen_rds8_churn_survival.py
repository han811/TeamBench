"""
Parameterized generator for RDS8: Telco Churn Survival Analysis (Archetype 3 — Open-Ended).

Uses the Telco Customer Churn dataset. Three seed variants:
  Seed 0: Kaplan-Meier survival curves by contract type
  Seed 1: Cox proportional hazards model with covariates
  Seed 2: Churn prediction with time-varying features

Rubric checks (8):
  C1: analysis.py runs without error
  C2: Survival analysis or churn prediction method implemented
  C3: Key survival metric reported in results.json
  C4: Key columns (tenure, Churn, Contract) referenced
  C5: Comparison across groups or covariate analysis present
  C6: Limitations discussed in report.md
  C7: Data loaded correctly (row count check)
  C8: results.json is valid JSON with required fields
"""
from __future__ import annotations

import textwrap

from generators.base import GeneratedTask
from generators.real_data_base import OpenEndedGenerator

_VARIANTS = [
    {
        # Seed 0 — Kaplan-Meier by contract type
        "analysis_type": "kaplan_meier",
        "analysis_label": "Kaplan-Meier Survival Analysis",
        "research_question": (
            "How does customer survival (non-churn) differ across contract types "
            "(month-to-month, one-year, two-year)? Use Kaplan-Meier curves to estimate "
            "and compare survival functions."
        ),
        "key_cols": ["tenure", "Churn", "Contract"],
        "hidden_col_keywords": ["tenure", "Contract"],
        "context": (
            "In survival analysis, `tenure` is the time variable (months with company) "
            "and `Churn` is the event indicator (Yes/No). Customers still active are "
            "right-censored. Kaplan-Meier estimates the survival function S(t) = P(T > t). "
            "Compare curves across three contract types: month-to-month (highest churn risk), "
            "one-year, and two-year. Use log-rank test to test for significant differences."
        ),
        "metric_key": "median_survival_month_to_month",
        "metric_label": "median survival time for month-to-month contract customers",
        "method_hint": "Use lifelines library (KaplanMeierFitter) or implement KM manually. Log-rank test from lifelines or scipy.",
        "extra_deliverable": "A PNG or description of KM curves in the report.",
    },
    {
        # Seed 1 — Cox proportional hazards
        "analysis_type": "cox_ph",
        "analysis_label": "Cox Proportional Hazards Model",
        "research_question": (
            "Which customer features are significant predictors of churn risk? "
            "Fit a Cox proportional hazards model with covariates: contract type, "
            "monthly charges, internet service, and senior citizen status."
        ),
        "key_cols": ["tenure", "Churn", "Contract", "MonthlyCharges",
                     "InternetService", "SeniorCitizen"],
        "hidden_col_keywords": ["MonthlyCharges", "InternetService"],
        "context": (
            "The Cox model estimates the hazard ratio for each covariate: "
            "HR > 1 means increased churn risk. Key questions: Does higher monthly "
            "charges increase churn? Does fiber optic internet increase risk vs DSL? "
            "Are senior citizens at higher risk? Check the proportional hazards "
            "assumption (Schoenfeld residuals or log-log plot)."
        ),
        "metric_key": "top_hazard_ratio",
        "metric_label": "highest hazard ratio among covariates",
        "method_hint": "Use lifelines CoxPHFitter or statsmodels PHReg. Encode categorical variables before fitting.",
        "extra_deliverable": "A table of hazard ratios with 95% CIs in the report.",
    },
    {
        # Seed 2 — churn prediction with ML
        "analysis_type": "churn_prediction",
        "analysis_label": "Churn Prediction Model",
        "research_question": (
            "Build a churn prediction model that achieves the best AUC while "
            "identifying the top 5 most predictive features. Compare logistic "
            "regression vs. a tree-based model."
        ),
        "key_cols": ["tenure", "Churn", "MonthlyCharges", "TotalCharges",
                     "Contract", "InternetService"],
        "hidden_col_keywords": ["tenure", "MonthlyCharges"],
        "context": (
            "Churn prediction is a binary classification task. `Churn` is the target "
            "(Yes/No → 1/0). Features include numeric (tenure, MonthlyCharges, TotalCharges) "
            "and categorical (Contract, InternetService, PaymentMethod, etc.). "
            "TotalCharges may have missing values — handle them. "
            "Report AUC on held-out test set and identify top 5 predictive features "
            "by feature importance or coefficient magnitude."
        ),
        "metric_key": "auc",
        "metric_label": "AUC on the held-out test set",
        "method_hint": "Use sklearn LogisticRegression and RandomForestClassifier. Compare AUC for both.",
        "extra_deliverable": "Feature importance ranking in results.json as `top_features`.",
    },
]

_KEEP_COLUMNS = [
    "customerID",
    "gender",
    "SeniorCitizen",
    "Partner",
    "Dependents",
    "tenure",
    "PhoneService",
    "MultipleLines",
    "InternetService",
    "OnlineSecurity",
    "Contract",
    "PaperlessBilling",
    "PaymentMethod",
    "MonthlyCharges",
    "TotalCharges",
    "Churn",
]


class Generator(OpenEndedGenerator):
    task_id = "RDS8_churn_survival"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]

    dataset_name = "telco_churn"
    dataset_license = "Apache 2.0"
    dataset_source = "IBM Telco Customer Churn"

    def generate(self, seed: int) -> GeneratedTask:
        variant = _VARIANTS[seed % len(_VARIANTS)]

        rows = self.load_dataset()
        rows = self.subsample(rows, seed=seed + 800, frac=0.2)  # ~1400 rows
        rows = self.select_columns(rows, _KEEP_COLUMNS)
        n_rows = len(rows)
        data_csv = self.rows_to_csv(rows, _KEEP_COLUMNS)

        check_py = self._make_check_solution(variant, n_rows)
        requirements_txt = self.make_requirements_txt(
            packages=[
                "pandas>=1.5",
                "numpy>=1.23",
                "scipy>=1.9",
                "scikit-learn>=1.1",
                "statsmodels>=0.13",
                "lifelines>=0.27",
            ]
        )
        task_yaml = self.make_task_yaml()

        workspace_files = {
            "data/telco_churn.csv": data_csv,
            "requirements.txt": requirements_txt,
            "check_solution.py": check_py,
            "task.yaml": task_yaml,
        }

        expected = {
            "analysis_type": variant["analysis_type"],
            "research_question": variant["research_question"],
            "key_cols": variant["key_cols"],
            "hidden_col_keywords": variant["hidden_col_keywords"],
            "n_rows": n_rows,
            "columns": _KEEP_COLUMNS,
            "required_output_files": ["analysis.py", "results.json", "report.md"],
        }

        spec_md = self._make_spec(variant, n_rows)
        brief_md = self._make_brief(variant)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _make_spec(self, variant: dict, n_rows: int) -> str:
        col_list = ", ".join(f"`{c}`" for c in variant["key_cols"])
        return textwrap.dedent(f"""\
            # RDS8: Telco Churn Survival Analysis

            ## Research Question
            **{variant["research_question"]}**

            ## Dataset
            - File: `data/telco_churn.csv`
            - Rows: {n_rows} (subsample of Telco Customer Churn dataset)
            - Columns: {", ".join(f"`{c}`" for c in _KEEP_COLUMNS)}
            - Key columns: {col_list}
            - Target: `Churn` (Yes/No) — whether the customer left

            ## Background
            {variant["context"]}

            ## Method Hint
            {variant["method_hint"]}

            ## Your Task
            Conduct a **{variant["analysis_label"]}** to answer the research question.

            Steps:
            1. Load and clean the data (`TotalCharges` may have non-numeric values)
            2. Encode `Churn` as binary: Yes=1, No=0
            3. Perform the analysis described above
            4. Report key metrics in `results.json`

            ## Required Deliverables

            ### 1. `analysis.py`
            A Python script that:
            - Loads `data/telco_churn.csv`
            - Cleans and encodes variables
            - Performs the {variant["analysis_label"]} analysis
            - Saves `results.json` and `report.md`

            ### 2. `results.json`
            Must contain at minimum:
            ```json
            {{
              "analysis_type": "{variant["analysis_type"]}",
              "{variant["metric_key"]}": <float>,
              "n_churned": <int>,
              "n_retained": <int>
            }}
            ```

            ### 3. `report.md`
            A brief (300–600 word) report covering:
            - Data cleaning decisions
            - Key findings: {variant["metric_label"]}
            - {variant["extra_deliverable"]}
            - **Limitations** (censoring assumptions, selection bias, etc.)

            ## Grading Criteria
            1. `analysis.py` runs without error
            2. Survival/prediction method implemented correctly
            3. Key metric (`{variant["metric_key"]}`) present in `results.json`
            4. Key columns ({col_list}) referenced in analysis code
            5. Group comparison or covariate analysis present
            6. `report.md` discusses limitations
            7. Data loaded correctly (correct row count)
            8. `results.json` contains required fields and is valid JSON
        """)

    def _make_brief(self, variant: dict) -> str:
        return textwrap.dedent(f"""\
            # RDS8: Telco Churn Survival Analysis (Brief)

            Analyze the Telco Churn dataset using survival analysis or prediction.

            **Dataset**: `data/telco_churn.csv`

            **Question**: {variant["research_question"]}

            Produce:
            - `analysis.py` — survival/churn analysis script
            - `results.json` — key metrics
            - `report.md` — findings and limitations
        """)

    def _make_check_solution(self, variant: dict, n_rows: int) -> str:
        hidden_kw = variant["hidden_col_keywords"]
        metric_key = variant["metric_key"]
        checks = [
            {
                "id": "C1",
                "description": "analysis.py runs without error",
                "type": "script_runs",
                "path": "analysis.py",
                "timeout": 120,
            },
            {
                "id": "C2",
                "description": "Survival analysis or churn prediction method implemented",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    method_terms = [
                        "kaplan", "km", "survival", "cox", "hazard",
                        "lifelines", "churn", "predict", "classifier",
                        "logistic", "auc", "roc",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in method_terms if t in content]
                        passed = len(found) >= 2
                        detail = f"found method terms: {found}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C3",
                "description": f"Key metric ({metric_key}) present in results.json",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    if p.exists():
                        try:
                            d = json.loads(p.read_text())
                            has_metric = "{metric_key}" in d
                            passed = has_metric
                            detail = f"{metric_key} present={{has_metric}}"
                        except Exception as e:
                            detail = str(e)
                    else:
                        detail = "results.json not found"
                """),
            },
            {
                "id": "C4",
                "description": f"Key columns ({', '.join(hidden_kw)}) referenced in analysis.py",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    keywords = {hidden_kw!r}
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [kw for kw in keywords if kw.lower() in content]
                        passed = len(found) == len(keywords)
                        detail = f"found={{found}}, missing={{[kw for kw in keywords if kw.lower() not in content]}}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C5",
                "description": "Group comparison or covariate analysis present in analysis.py",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    comparison_terms = [
                        "groupby", "group_by", "contract", "compare", "covariate",
                        "coefficient", "hazard", "feature_importance", "feature",
                        "log_rank", "logrank",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in comparison_terms if t in content]
                        passed = len(found) >= 1
                        detail = f"found comparison terms: {found}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C6",
                "description": "Limitations discussed in report.md",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "report.md"
                    passed = False
                    detail = ""
                    caveat_terms = ["limitation", "caveat", "assumption", "bias",
                                    "censor", "confound", "selection", "missing"]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in caveat_terms if t in content]
                        passed = len(found) >= 1
                        detail = f"found caveat terms: {found}"
                    else:
                        detail = "report.md not found"
                """),
            },
            {
                "id": "C7",
                "description": f"Data loaded correctly (expected ~{n_rows} rows)",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import pathlib, csv
                    p = pathlib.Path(workspace_dir) / "data" / "telco_churn.csv"
                    passed = False
                    detail = ""
                    expected_rows = {n_rows}
                    if p.exists():
                        with open(p, newline="", encoding="utf-8") as fh:
                            actual = sum(1 for _ in csv.reader(fh)) - 1
                        passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.01))
                        detail = f"actual={{actual}}, expected={{expected_rows}}"
                    else:
                        detail = "data/telco_churn.csv not found"
                """),
            },
            {
                "id": "C8",
                "description": "results.json is valid JSON with required fields",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    required_fields = ["analysis_type", "{metric_key}", "n_churned", "n_retained"]
                    if p.exists():
                        try:
                            d = json.loads(p.read_text(encoding="utf-8"))
                            missing = [f for f in required_fields if f not in d]
                            passed = len(missing) == 0
                            detail = f"missing fields: {{missing}}" if missing else "all required fields present"
                        except json.JSONDecodeError as e:
                            detail = f"JSON parse error: {{e}}"
                    else:
                        detail = "results.json not found"
                """),
            },
        ]
        return self.make_check_solution(checks)
