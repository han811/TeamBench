"""
Parameterized generator for RDS9: Fraud Detection (Archetype 3 — Open-Ended).

Uses the Credit Card Fraud dataset. Three seed variants:
  Seed 0: Threshold tuning on logistic regression with ≤1% FPR constraint
  Seed 1: Anomaly detection approach (Isolation Forest or LOF)
  Seed 2: Cost-sensitive classification

Rubric checks (8):
  C1: analysis.py runs without error
  C2: Class imbalance handled (oversampling, undersampling, or class weights)
  C3: Precision/recall/FPR metric reported in results.json
  C4: Class column and key features referenced in analysis code
  C5: Threshold or cost-sensitivity analysis present
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
        # Seed 0 — threshold tuning
        "analysis_type": "threshold_tuning",
        "analysis_label": "Threshold-Tuned Logistic Regression",
        "research_question": (
            "Train a logistic regression model and tune the classification threshold "
            "to achieve a false positive rate ≤ 1% while maximizing fraud recall. "
            "What is the maximum recall achievable under this FPR constraint?"
        ),
        "key_cols": ["Class", "Amount", "V1", "V14"],
        "hidden_col_keywords": ["Class", "Amount"],
        "context": (
            "The dataset is highly imbalanced (~0.17% fraud). The `Class` column is the "
            "target (1=fraud, 0=legitimate). Features V1-V28 are PCA-transformed. "
            "`Amount` and `Time` are raw. Logistic regression outputs probabilities; "
            "the threshold can be adjusted below 0.5 to increase recall. "
            "FPR = FP / (FP + TN). Find the highest threshold that keeps FPR ≤ 0.01."
        ),
        "metric_key": "recall_at_1pct_fpr",
        "metric_label": "fraud recall at ≤1% false positive rate",
        "constraint": "FPR ≤ 0.01",
        "method_hint": "Use sklearn's precision_recall_curve or roc_curve to find the threshold.",
    },
    {
        # Seed 1 — anomaly detection
        "analysis_type": "anomaly_detection",
        "analysis_label": "Anomaly Detection",
        "research_question": (
            "Apply an unsupervised anomaly detection method (Isolation Forest or "
            "Local Outlier Factor) to detect fraud. Compare its precision and recall "
            "against a supervised baseline (logistic regression)."
        ),
        "key_cols": ["Class", "Amount", "V1", "V14", "V17"],
        "hidden_col_keywords": ["Class", "Amount"],
        "context": (
            "Unsupervised anomaly detection treats fraud as statistical outliers. "
            "Isolation Forest assigns anomaly scores; lower scores indicate anomalies. "
            "The contamination parameter should be set to the approximate fraud rate (~0.002). "
            "Compare: precision, recall, and F1 of anomaly detection vs. "
            "a simple logistic regression baseline. Discuss trade-offs."
        ),
        "metric_key": "anomaly_f1",
        "metric_label": "F1 score of the anomaly detection model",
        "constraint": "No labels used during anomaly detection training",
        "method_hint": "Use sklearn IsolationForest with contamination≈0.002. Compare to LogisticRegression.",
    },
    {
        # Seed 2 — cost-sensitive classification
        "analysis_type": "cost_sensitive",
        "analysis_label": "Cost-Sensitive Classification",
        "research_question": (
            "Frame fraud detection as a cost minimization problem. "
            "Assume: missing a fraud costs $500 (false negative), "
            "and a false alarm costs $10 (false positive). "
            "Find the classification threshold that minimizes total expected cost."
        ),
        "key_cols": ["Class", "Amount", "V1", "V14"],
        "hidden_col_keywords": ["Class", "Amount"],
        "context": (
            "In fraud detection, false negatives (missed fraud) and false positives "
            "(false alarms) have very different costs. The optimal threshold trades off "
            "these costs. Total cost = FN_cost × FN_count + FP_cost × FP_count. "
            "Sweep thresholds from 0.01 to 0.99, compute total cost at each, "
            "and report the cost-minimizing threshold and its precision/recall."
        ),
        "metric_key": "min_total_cost",
        "metric_label": "minimum total cost at the optimal threshold",
        "constraint": "FN cost = $500, FP cost = $10",
        "method_hint": "Train a logistic regression or gradient boosting model, then sweep decision thresholds.",
    },
]

# Only keep a subset of PCA features + key columns to keep file size manageable
_KEEP_COLUMNS = [
    "Time", "V1", "V2", "V3", "V4", "V5",
    "V10", "V11", "V12", "V14", "V17", "V19",
    "V21", "V27", "V28", "Amount", "Class",
]


class Generator(OpenEndedGenerator):
    task_id = "RDS9_fraud_detection"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]

    dataset_name = "credit_card_fraud"
    dataset_license = "Open Database License"
    dataset_source = "ULB Machine Learning Group / Kaggle"

    def generate(self, seed: int) -> GeneratedTask:
        variant = _VARIANTS[seed % len(_VARIANTS)]

        rows = self.load_dataset()
        rows = self.subsample(rows, seed=seed + 900, frac=0.03)  # ~1500 rows
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
            ]
        )
        task_yaml = self.make_task_yaml()

        workspace_files = {
            "data/credit_card_fraud.csv": data_csv,
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
            # RDS9: Fraud Detection

            ## Research Question
            **{variant["research_question"]}**

            ## Dataset
            - File: `data/credit_card_fraud.csv`
            - Rows: {n_rows} (subsample of credit card transactions)
            - Columns: `Time`, `V1`–`V28` (PCA features), `Amount`, `Class`
            - Available columns: {", ".join(f"`{c}`" for c in _KEEP_COLUMNS)}
            - Target: `Class` (1=fraud, 0=legitimate)
            - Constraint: **{variant["constraint"]}**

            ## Background
            {variant["context"]}

            ## Method Hint
            {variant["method_hint"]}

            ## Your Task
            Conduct a **{variant["analysis_label"]}** to detect credit card fraud.

            Steps:
            1. Load and explore the data (check class distribution)
            2. Handle class imbalance appropriately
            3. Implement the analysis approach described above
            4. Report key performance metrics
            5. Save `results.json` and `report.md`

            ## Required Deliverables

            ### 1. `analysis.py`
            A Python script that:
            - Loads `data/credit_card_fraud.csv`
            - Handles class imbalance
            - Implements {variant["analysis_label"]}
            - Saves `results.json` and `report.md`

            ### 2. `results.json`
            Must contain at minimum:
            ```json
            {{
              "analysis_type": "{variant["analysis_type"]}",
              "{variant["metric_key"]}": <float>,
              "precision": <float>,
              "recall": <float>,
              "n_fraud": <int>,
              "n_legitimate": <int>
            }}
            ```

            ### 3. `report.md`
            A brief (300–600 word) report covering:
            - Class imbalance handling
            - Key performance metrics (precision, recall, FPR)
            - {variant["analysis_label"]} design decisions
            - **Limitations** (imbalanced data, threshold sensitivity, overfitting, etc.)

            ## Grading Criteria
            1. `analysis.py` runs without error
            2. Class imbalance handled (weights, sampling, or contamination parameter)
            3. Key metric (`{variant["metric_key"]}`) and precision/recall in `results.json`
            4. Key columns ({col_list}) referenced in analysis code
            5. Threshold tuning or cost analysis or anomaly scoring present
            6. `report.md` discusses limitations
            7. Data loaded correctly (correct row count)
            8. `results.json` contains required fields and is valid JSON
        """)

    def _make_brief(self, variant: dict) -> str:
        return textwrap.dedent(f"""\
            # RDS9: Fraud Detection (Brief)

            Detect credit card fraud under operational constraints.

            **Dataset**: `data/credit_card_fraud.csv`

            **Question**: {variant["research_question"]}

            **Constraint**: {variant["constraint"]}

            Produce:
            - `analysis.py` — fraud detection script
            - `results.json` — performance metrics
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
                "description": "Class imbalance handled in analysis.py",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    imbalance_terms = [
                        "class_weight", "imbalance", "oversamp", "undersamp",
                        "smote", "resamp", "contamination", "scale_pos_weight",
                        "balanced", "weight",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in imbalance_terms if t in content]
                        passed = len(found) >= 1
                        detail = f"found imbalance terms: {found}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C3",
                "description": f"Key metric ({metric_key}) and precision/recall in results.json",
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
                            has_pr = "precision" in d or "recall" in d
                            passed = has_metric and has_pr
                            detail = f"{metric_key} present={{has_metric}}, precision/recall={{has_pr}}"
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
                "description": "Threshold tuning, cost analysis, or anomaly scoring present",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    threshold_terms = [
                        "threshold", "cost", "fpr", "roc", "precision_recall",
                        "anomaly", "isolation", "score", "predict_proba",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in threshold_terms if t in content]
                        passed = len(found) >= 1
                        detail = f"found threshold/cost terms: {found}"
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
                    caveat_terms = ["limitation", "caveat", "imbalance", "bias",
                                    "overfit", "threshold", "assumption", "tradeoff"]
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
                    p = pathlib.Path(workspace_dir) / "data" / "credit_card_fraud.csv"
                    passed = False
                    detail = ""
                    expected_rows = {n_rows}
                    if p.exists():
                        with open(p, newline="", encoding="utf-8") as fh:
                            actual = sum(1 for _ in csv.reader(fh)) - 1
                        passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.01))
                        detail = f"actual={{actual}}, expected={{expected_rows}}"
                    else:
                        detail = "data/credit_card_fraud.csv not found"
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
                    required_fields = ["analysis_type", "{metric_key}", "precision", "recall"]
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
