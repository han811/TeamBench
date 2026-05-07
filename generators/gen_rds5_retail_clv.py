"""
Parameterized generator for RDS5: Retail Customer Lifetime Value (Archetype 3 — Open-Ended).

Uses the Online Retail dataset. Three seed variants:
  Seed 0: RFM-based CLV estimation
  Seed 1: Cohort retention analysis
  Seed 2: Purchase frequency modeling

Rubric checks (8):
  C1: analysis.py runs without error
  C2: RFM or cohort or frequency features computed
  C3: CLV/retention/frequency metric reported in results.json
  C4: Key columns (CustomerID, InvoiceDate, etc.) referenced
  C5: Segmentation or grouping of customers present
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
        # Seed 0 — RFM-based CLV
        "analysis_type": "RFM-based CLV",
        "research_question": (
            "Estimate Customer Lifetime Value using RFM (Recency, Frequency, Monetary) "
            "analysis. Segment customers into value tiers and identify the top 20% "
            "of customers by estimated CLV."
        ),
        "key_columns": ["CustomerID", "InvoiceDate", "Quantity", "UnitPrice"],
        "hidden_col_keywords": ["CustomerID", "InvoiceDate"],
        "context": (
            "RFM analysis uses three dimensions: Recency (days since last purchase), "
            "Frequency (number of transactions), and Monetary (total spend). "
            "CLV = Average Order Value × Purchase Frequency × Customer Lifespan. "
            "Customers should be segmented (e.g. quintiles or k-means) and the "
            "top value tier identified. Exclude cancelled orders (InvoiceNo starting with 'C')."
        ),
        "metric_key": "top_20pct_clv_share",
        "metric_label": "share of total CLV held by top 20% of customers",
        "deliverable_extra": "A CSV file `customer_segments.csv` with CustomerID and CLV tier.",
    },
    {
        # Seed 1 — cohort retention analysis
        "analysis_type": "Cohort Retention Analysis",
        "research_question": (
            "Perform a cohort retention analysis: for each monthly cohort (customers "
            "who made their first purchase in a given month), compute the month-over-month "
            "retention rate for the following 6 months."
        ),
        "key_columns": ["CustomerID", "InvoiceDate", "InvoiceNo"],
        "hidden_col_keywords": ["CustomerID", "InvoiceDate"],
        "context": (
            "Cohort analysis groups customers by acquisition month. "
            "For each cohort, compute the percentage of customers who returned in "
            "subsequent months. A retention matrix (cohort × month offset) reveals "
            "how quickly customer engagement decays. "
            "Exclude cancelled orders (InvoiceNo starting with 'C')."
        ),
        "metric_key": "avg_month1_retention",
        "metric_label": "average month-1 retention rate across cohorts (fraction)",
        "deliverable_extra": "A CSV file `retention_matrix.csv` with cohorts as rows and month offsets as columns.",
    },
    {
        # Seed 2 — purchase frequency modeling
        "analysis_type": "Purchase Frequency Modeling",
        "research_question": (
            "Model purchase frequency per customer: fit a statistical model "
            "(e.g. negative binomial or Poisson regression) to explain the number of "
            "distinct invoices per customer over the observation period, and identify "
            "which customer characteristics (country, order size) drive frequency."
        ),
        "key_columns": ["CustomerID", "InvoiceNo", "Country", "Quantity", "UnitPrice"],
        "hidden_col_keywords": ["CustomerID", "InvoiceNo"],
        "context": (
            "Purchase frequency varies widely across customers. "
            "Aggregate to the customer level: count distinct invoices, total spend, "
            "average order value, and country. Fit a count model (Poisson or negative "
            "binomial) to explain frequency. UK customers dominate the dataset. "
            "Exclude cancelled orders (InvoiceNo starting with 'C')."
        ),
        "metric_key": "pseudo_r2",
        "metric_label": "pseudo R² of the frequency model",
        "deliverable_extra": "A CSV file `customer_features.csv` with per-customer aggregated features.",
    },
]

_KEEP_COLUMNS = [
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
]


class Generator(OpenEndedGenerator):
    task_id = "RDS5_retail_clv"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]

    dataset_name = "online_retail"
    dataset_license = "CC BY 4.0"
    dataset_source = "UCI ML Repository"

    def generate(self, seed: int) -> GeneratedTask:
        variant = _VARIANTS[seed % len(_VARIANTS)]

        rows = self.load_dataset()
        rows = self.subsample(rows, seed=seed + 500, frac=0.003)  # ~1500 rows
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
            ]
        )
        task_yaml = self.make_task_yaml()

        workspace_files = {
            "data/online_retail.csv": data_csv,
            "requirements.txt": requirements_txt,
            "check_solution.py": check_py,
            "task.yaml": task_yaml,
        }

        expected = {
            "analysis_type": variant["analysis_type"],
            "research_question": variant["research_question"],
            "key_columns": variant["key_columns"],
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
        col_list = ", ".join(f"`{c}`" for c in variant["key_columns"])
        return textwrap.dedent(f"""\
            # RDS5: Retail Customer Lifetime Value

            ## Research Question
            **{variant["research_question"]}**

            ## Dataset
            - File: `data/online_retail.csv`
            - Rows: {n_rows} (subsample of the UCI Online Retail dataset)
            - Columns: {", ".join(f"`{c}`" for c in _KEEP_COLUMNS)}
            - Key columns for this analysis: {col_list}

            ## Background
            {variant["context"]}

            ## Analysis Type
            **{variant["analysis_type"]}**

            ## Your Task
            Perform a `{variant["analysis_type"]}` on the retail transaction data.
            You must:
            1. Clean the data (remove cancelled orders, handle missing CustomerIDs)
            2. Aggregate transactions to the customer level
            3. Compute the required metrics
            4. Segment or model customers as described
            5. Report key metrics in `results.json`

            ## Required Deliverables

            ### 1. `analysis.py`
            A Python script that:
            - Loads `data/online_retail.csv`
            - Cleans data (removes cancellations, handles nulls)
            - Performs the analysis described above
            - Saves `results.json`, `report.md`, and {variant["deliverable_extra"]}

            ### 2. `results.json`
            Must contain at minimum:
            ```json
            {{
              "analysis_type": "{variant["analysis_type"]}",
              "{variant["metric_key"]}": <float>,
              "n_customers": <int>,
              "n_transactions": <int>
            }}
            ```

            ### 3. `report.md`
            A brief (300–600 word) report covering:
            - Data cleaning decisions
            - Key findings: {variant["metric_label"]}
            - Customer segments or model results
            - **Limitations** (data quality, time horizon, etc.)

            ## Grading Criteria
            1. `analysis.py` runs without error
            2. RFM/cohort/frequency features computed correctly
            3. Key metric (`{variant["metric_key"]}`) present in `results.json`
            4. Key columns ({col_list}) referenced in analysis code
            5. Customer segmentation or grouping present
            6. `report.md` discusses limitations
            7. Data loaded correctly (correct row count)
            8. `results.json` contains required fields and is valid JSON
        """)

    def _make_brief(self, variant: dict) -> str:
        return textwrap.dedent(f"""\
            # RDS5: Retail Customer Lifetime Value (Brief)

            Analyze the Online Retail dataset for customer value insights.

            **Dataset**: `data/online_retail.csv`

            **Question**: {variant["research_question"]}

            Produce:
            - `analysis.py` — customer analysis script
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
                "description": "RFM/cohort/frequency features computed in analysis.py",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    feature_terms = [
                        "recency", "frequency", "monetary", "cohort", "retention",
                        "rfm", "invoice", "groupby", "group_by", "agg", "aggregate",
                        "clv", "lifetime", "purchase",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in feature_terms if t in content]
                        passed = len(found) >= 2
                        detail = f"found feature terms: {found}"
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
                "description": "Customer segmentation or grouping present in analysis.py",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    segment_terms = [
                        "segment", "cluster", "kmeans", "k_means", "quintile",
                        "percentile", "tier", "group", "cohort", "bin",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in segment_terms if t in content]
                        passed = len(found) >= 1
                        detail = f"found segmentation terms: {found}"
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
                                    "quality", "missing", "incomplete", "caveats"]
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
                    p = pathlib.Path(workspace_dir) / "data" / "online_retail.csv"
                    passed = False
                    detail = ""
                    expected_rows = {n_rows}
                    if p.exists():
                        with open(p, newline="", encoding="utf-8") as fh:
                            actual = sum(1 for _ in csv.reader(fh)) - 1
                        passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.01))
                        detail = f"actual={{actual}}, expected={{expected_rows}}"
                    else:
                        detail = "data/online_retail.csv not found"
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
                    required_fields = ["{metric_key}", "n_customers", "n_transactions"]
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
