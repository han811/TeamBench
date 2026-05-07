"""
Parameterized generator for RDS7: WHO Health Panel Analysis (Archetype 3 — Open-Ended).

Uses the WHO GHO dataset. Three seed variants:
  Seed 0: Panel regression for life expectancy determinants
  Seed 1: Cross-sectional analysis by region
  Seed 2: Time trend analysis

Rubric checks (8):
  C1: analysis.py runs without error
  C2: Panel/regression/trend analysis implemented
  C3: Key coefficient or trend reported in results.json
  C4: Key health indicators referenced in analysis code
  C5: Country/region grouping or fixed effects present
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
        # Seed 0 — panel regression
        "analysis_type": "panel_regression",
        "analysis_label": "Panel Regression",
        "research_question": (
            "Which health and economic factors (physicians per 1000, health expenditure, "
            "HIV prevalence, income group) most strongly predict life expectancy across "
            "countries and years? Use panel regression with country fixed effects."
        ),
        "key_cols": ["life_expectancy", "physicians_per_1000", "health_expenditure_pct_gdp",
                     "hiv_prevalence", "income_group"],
        "hidden_col_keywords": ["physicians_per_1000", "health_expenditure_pct_gdp"],
        "context": (
            "Life expectancy differs enormously across countries. Panel data allows "
            "controlling for time-invariant country characteristics via fixed effects. "
            "Key predictors: physicians per 1000 (healthcare access), health expenditure "
            "as % GDP (investment), HIV prevalence (disease burden), income group. "
            "Use OLS with country fixed effects or a mixed effects model."
        ),
        "method_hint": "Use statsmodels OLS with country dummy variables, or use within-group demeaning for fixed effects.",
        "metric_key": "r2",
        "metric_label": "R² of the panel model",
        "result_extra_field": "top_predictor",
    },
    {
        # Seed 1 — cross-sectional by region
        "analysis_type": "cross_sectional",
        "analysis_label": "Cross-Sectional Regional Analysis",
        "research_question": (
            "How do life expectancy determinants differ across WHO regions? "
            "For the most recent year available, run a cross-sectional regression "
            "per region and compare which factors matter most in each region."
        ),
        "key_cols": ["life_expectancy", "region", "income_group",
                     "physicians_per_1000", "infant_mortality"],
        "hidden_col_keywords": ["region", "infant_mortality"],
        "context": (
            "Regional analysis reveals heterogeneity in the drivers of life expectancy. "
            "In high-income regions, marginal gains in physicians may matter less than "
            "in low-income regions. Use the most recent year with complete data. "
            "Run a separate regression per region (or use interaction terms). "
            "Compare R² and top predictors across regions."
        ),
        "method_hint": "Filter to the most recent year, then run OLS by region. Report coefficients and R² per region.",
        "metric_key": "avg_r2_across_regions",
        "metric_label": "average R² across regional models",
        "result_extra_field": "regions_analyzed",
    },
    {
        # Seed 2 — time trend analysis
        "analysis_type": "time_trend",
        "analysis_label": "Time Trend Analysis",
        "research_question": (
            "How has life expectancy changed over time globally and by income group? "
            "Fit linear time trends for each income group and test whether trends "
            "differ significantly across groups."
        ),
        "key_cols": ["life_expectancy", "year", "income_group", "region"],
        "hidden_col_keywords": ["income_group", "year"],
        "context": (
            "Global life expectancy has generally risen over decades, but the rate "
            "of improvement differs by income group. Low-income countries may show "
            "faster improvement (convergence) or slower (divergence). "
            "Fit OLS trend lines per income group: life_expectancy ~ year. "
            "Test whether slopes differ across groups using interaction terms or "
            "Chow test. Report the trend slope per income group."
        ),
        "method_hint": "Use OLS with year as predictor, run separately per income group. Test for parallel trends.",
        "metric_key": "trend_slope_low_income",
        "metric_label": "annual improvement in life expectancy for low-income countries",
        "result_extra_field": "trend_slopes_by_group",
    },
]

_KEEP_COLUMNS = [
    "country",
    "country_code",
    "year",
    "life_expectancy",
    "infant_mortality",
    "under5_mortality",
    "maternal_mortality",
    "hiv_prevalence",
    "physicians_per_1000",
    "hospital_beds_per_1000",
    "health_expenditure_pct_gdp",
    "income_group",
    "region",
]


class Generator(OpenEndedGenerator):
    task_id = "RDS7_health_panel"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]

    dataset_name = "who_gho"
    dataset_license = "CC BY-NC-SA 3.0 IGO"
    dataset_source = "WHO Global Health Observatory"

    def generate(self, seed: int) -> GeneratedTask:
        variant = _VARIANTS[seed % len(_VARIANTS)]

        # who_gho is small (264 rows) — use all of it
        rows = self.load_dataset()
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
            "data/who_gho.csv": data_csv,
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
            # RDS7: WHO Health Panel Analysis

            ## Research Question
            **{variant["research_question"]}**

            ## Dataset
            - File: `data/who_gho.csv`
            - Rows: {n_rows} (WHO Global Health Observatory data)
            - Columns: {", ".join(f"`{c}`" for c in _KEEP_COLUMNS)}
            - Key columns for this analysis: {col_list}

            ## Background
            {variant["context"]}

            ## Method Hint
            {variant["method_hint"]}

            ## Your Task
            Conduct a **{variant["analysis_label"]}** to answer the research question.

            Steps:
            1. Load and clean the data (handle missing values, numeric types)
            2. Perform the analysis as described
            3. Report key findings with statistical evidence
            4. Save `results.json` and `report.md`

            ## Required Deliverables

            ### 1. `analysis.py`
            A Python script that:
            - Loads `data/who_gho.csv`
            - Handles missing data appropriately
            - Runs the {variant["analysis_label"]} analysis
            - Saves `results.json` and `report.md`

            ### 2. `results.json`
            Must contain at minimum:
            ```json
            {{
              "analysis_type": "{variant["analysis_type"]}",
              "{variant["metric_key"]}": <float>,
              "{variant["result_extra_field"]}": <value>,
              "n_countries": <int>
            }}
            ```

            ### 3. `report.md`
            A brief (300–600 word) report covering:
            - Data cleaning decisions (missing data handling)
            - Key findings: {variant["metric_label"]}
            - Statistical evidence (coefficients, p-values, R²)
            - **Limitations** (data quality, causality, confounding, etc.)

            ## Grading Criteria
            1. `analysis.py` runs without error
            2. Panel/regression/trend analysis implemented
            3. Key metric (`{variant["metric_key"]}`) present in `results.json`
            4. Key columns ({col_list}) referenced in analysis code
            5. Country/region grouping or fixed effects present
            6. `report.md` discusses limitations
            7. Data loaded correctly (correct row count)
            8. `results.json` contains required fields and is valid JSON
        """)

    def _make_brief(self, variant: dict) -> str:
        return textwrap.dedent(f"""\
            # RDS7: WHO Health Panel Analysis (Brief)

            Analyze the WHO GHO dataset to understand life expectancy determinants.

            **Dataset**: `data/who_gho.csv`

            **Question**: {variant["research_question"]}

            Produce:
            - `analysis.py` — health panel analysis script
            - `results.json` — key metrics and coefficients
            - `report.md` — findings and limitations
        """)

    def _make_check_solution(self, variant: dict, n_rows: int) -> str:
        hidden_kw = variant["hidden_col_keywords"]
        metric_key = variant["metric_key"]
        extra_field = variant["result_extra_field"]
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
                "description": "Panel/regression/trend analysis implemented in analysis.py",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    analysis_terms = [
                        "regression", "ols", "linear", "fixed effect", "panel",
                        "trend", "slope", "coefficient", "fit", "predict",
                        "smf", "statsmodels", "linearregression",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in analysis_terms if t in content]
                        passed = len(found) >= 2
                        detail = f"found analysis terms: {found}"
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
                "description": "Country/region grouping or fixed effects present in analysis.py",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    grouping_terms = [
                        "country", "region", "groupby", "group_by", "fixed",
                        "dummy", "income_group", "C(", "dummies",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in grouping_terms if t in content]
                        passed = len(found) >= 1
                        detail = f"found grouping terms: {found}"
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
                                    "confound", "missing", "causal", "correlation"]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in caveat_terms if t in content]
                        passed = len(found) >= 2
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
                    p = pathlib.Path(workspace_dir) / "data" / "who_gho.csv"
                    passed = False
                    detail = ""
                    expected_rows = {n_rows}
                    if p.exists():
                        with open(p, newline="", encoding="utf-8") as fh:
                            actual = sum(1 for _ in csv.reader(fh)) - 1
                        passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.02))
                        detail = f"actual={{actual}}, expected={{expected_rows}}"
                    else:
                        detail = "data/who_gho.csv not found"
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
                    required_fields = ["analysis_type", "{metric_key}", "n_countries"]
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
