"""
Parameterized generator for RDS10: Stack Overflow Survey Analysis (Archetype 3 — Open-Ended).

Uses the Stack Overflow Developer Survey dataset. Three seed variants:
  Seed 0: Remote work → job satisfaction, controlling for salary
  Seed 1: Experience → salary, controlling for education
  Seed 2: Language popularity → job satisfaction

Rubric checks (8):
  C1: analysis.py runs without error
  C2: Regression or comparison analysis implemented
  C3: Effect estimate with uncertainty reported in results.json
  C4: Key survey columns referenced in analysis code
  C5: Confounding controlled for (at least one control variable)
  C6: Limitations discussed in report.md (self-selection, survey bias, etc.)
  C7: Data loaded correctly (row count check)
  C8: results.json is valid JSON with required fields
"""
from __future__ import annotations

import textwrap

from generators.base import GeneratedTask
from generators.real_data_base import OpenEndedGenerator

_VARIANTS = [
    {
        # Seed 0 — remote work → job satisfaction
        "analysis_type": "remote_satisfaction",
        "analysis_label": "Remote Work and Job Satisfaction",
        "research_question": (
            "Does remote work predict higher job satisfaction among developers, "
            "after controlling for compensation (ConvertedCompYearly) and employment type?"
        ),
        "key_cols": ["JobSat", "Employment", "ConvertedCompYearly", "EdLevel"],
        "hidden_col_keywords": ["JobSat", "ConvertedCompYearly"],
        "context": (
            "JobSat is the outcome variable (job satisfaction). Employment column "
            "contains information about remote/hybrid/in-person work arrangements. "
            "ConvertedCompYearly is compensation in USD. "
            "A naive comparison of remote vs. in-person may be confounded by salary "
            "(remote workers may earn more) and employment type. "
            "Create a binary remote indicator from Employment field. "
            "Control for ConvertedCompYearly (log-transform recommended) and EdLevel."
        ),
        "treatment_col": "Employment",
        "treatment_binary_desc": "Create a binary: 1 if Employment contains 'remote', 0 otherwise (case-insensitive).",
        "confounders": ["ConvertedCompYearly", "EdLevel", "YearsCodePro"],
        "metric_key": "remote_effect_on_satisfaction",
        "metric_label": "regression coefficient for remote work on job satisfaction",
        "result_extra_field": "p_value",
    },
    {
        # Seed 1 — experience → salary
        "analysis_type": "experience_salary",
        "analysis_label": "Experience and Salary",
        "research_question": (
            "How does years of professional coding experience (YearsCodePro) predict "
            "annual compensation (ConvertedCompYearly), after controlling for education "
            "level and developer type?"
        ),
        "key_cols": ["ConvertedCompYearly", "YearsCodePro", "EdLevel", "DevType"],
        "hidden_col_keywords": ["YearsCodePro", "EdLevel"],
        "context": (
            "ConvertedCompYearly is the outcome (USD, log-transform recommended). "
            "YearsCodePro contains years of professional experience (may have string "
            "values like 'Less than 1 year' — clean to numeric). "
            "EdLevel encodes education (e.g. Bachelor's, Master's, etc.). "
            "DevType is a multi-value field (may need multi-hot encoding or simplification). "
            "Filter to full-time employed developers with valid compensation data."
        ),
        "treatment_col": "YearsCodePro",
        "treatment_binary_desc": "YearsCodePro as numeric predictor (clean string values to numbers).",
        "confounders": ["EdLevel", "DevType", "OrgSize"],
        "metric_key": "years_exp_salary_coefficient",
        "metric_label": "regression coefficient for YearsCodePro on log(salary)",
        "result_extra_field": "r2",
    },
    {
        # Seed 2 — language popularity → satisfaction
        "analysis_type": "language_satisfaction",
        "analysis_label": "Programming Language and Job Satisfaction",
        "research_question": (
            "Do developers who use Python or JavaScript report higher job satisfaction "
            "than those using other languages, after controlling for experience and salary?"
        ),
        "key_cols": ["JobSat", "LanguageHaveWorkedWith", "YearsCodePro", "ConvertedCompYearly"],
        "hidden_col_keywords": ["LanguageHaveWorkedWith", "JobSat"],
        "context": (
            "LanguageHaveWorkedWith is a semicolon-separated list of languages. "
            "Create binary indicators: python_user=1 if 'Python' in the list, "
            "js_user=1 if 'JavaScript' in the list. "
            "JobSat is the outcome. Control for experience (YearsCodePro) and "
            "compensation (ConvertedCompYearly, log-transformed). "
            "Compare satisfaction across language groups with adjustment."
        ),
        "treatment_col": "LanguageHaveWorkedWith",
        "treatment_binary_desc": "Create python_user and js_user binary indicators from semicolon-separated list.",
        "confounders": ["YearsCodePro", "ConvertedCompYearly", "Employment"],
        "metric_key": "python_effect_on_satisfaction",
        "metric_label": "regression coefficient for Python use on job satisfaction",
        "result_extra_field": "js_effect_on_satisfaction",
    },
]

_KEEP_COLUMNS = [
    "ResponseId",
    "Employment",
    "EdLevel",
    "YearsCode",
    "YearsCodePro",
    "DevType",
    "OrgSize",
    "LanguageHaveWorkedWith",
    "Age",
    "JobSat",
    "ConvertedCompYearly",
]


class Generator(OpenEndedGenerator):
    task_id = "RDS10_survey_analysis"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]

    dataset_name = "stackoverflow"
    dataset_license = "ODbL"
    dataset_source = "Stack Overflow Developer Survey"

    def generate(self, seed: int) -> GeneratedTask:
        variant = _VARIANTS[seed % len(_VARIANTS)]

        rows = self.load_dataset()
        rows = self.subsample(rows, seed=seed + 1000, frac=0.025)  # ~1250 rows
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
            "data/stackoverflow.csv": data_csv,
            "requirements.txt": requirements_txt,
            "check_solution.py": check_py,
            "task.yaml": task_yaml,
        }

        expected = {
            "analysis_type": variant["analysis_type"],
            "research_question": variant["research_question"],
            "key_cols": variant["key_cols"],
            "hidden_col_keywords": variant["hidden_col_keywords"],
            "confounders": variant["confounders"],
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
        confounder_list = ", ".join(f"`{c}`" for c in variant["confounders"])
        return textwrap.dedent(f"""\
            # RDS10: Stack Overflow Survey Analysis

            ## Research Question
            **{variant["research_question"]}**

            ## Dataset
            - File: `data/stackoverflow.csv`
            - Rows: {n_rows} (subsample of Stack Overflow Developer Survey)
            - Columns: {", ".join(f"`{c}`" for c in _KEEP_COLUMNS)}
            - Key columns: {col_list}

            ## Treatment / Predictor Definition
            {variant["treatment_binary_desc"]}

            ## Background
            {variant["context"]}

            ## Your Task
            Conduct a regression analysis to answer the research question.

            Steps:
            1. Load and clean the data (handle missing values, parse string fields)
            2. Create the treatment/predictor variable as described
            3. Control for confounders: {confounder_list}
            4. Fit a regression model (OLS for continuous outcome, logistic for binary)
            5. Report the effect estimate with standard error and p-value
            6. Discuss whether the relationship is likely causal

            **Important**: Survey data has self-selection bias — be careful about
            causal language. Report associations, not causal claims.

            ## Required Deliverables

            ### 1. `analysis.py`
            A Python script that:
            - Loads `data/stackoverflow.csv`
            - Cleans and encodes variables
            - Controls for confounders: {confounder_list}
            - Fits the regression model
            - Saves `results.json` and `report.md`

            ### 2. `results.json`
            Must contain at minimum:
            ```json
            {{
              "analysis_type": "{variant["analysis_type"]}",
              "{variant["metric_key"]}": <float>,
              "{variant["result_extra_field"]}": <value>,
              "n_observations": <int>
            }}
            ```

            ### 3. `report.md`
            A brief (300–600 word) report covering:
            - Data cleaning decisions (missing values, string parsing)
            - Effect estimate and statistical significance
            - Confounders controlled for
            - **Limitations** (self-selection bias, survey design, missing data, etc.)

            ## Grading Criteria
            1. `analysis.py` runs without error
            2. Regression analysis implemented with controls
            3. Key metric (`{variant["metric_key"]}`) present in `results.json`
            4. Key columns ({col_list}) referenced in analysis code
            5. At least one confounder ({confounder_list}) controlled for
            6. `report.md` discusses limitations (survey bias, self-selection)
            7. Data loaded correctly (correct row count)
            8. `results.json` contains required fields and is valid JSON
        """)

    def _make_brief(self, variant: dict) -> str:
        return textwrap.dedent(f"""\
            # RDS10: Stack Overflow Survey Analysis (Brief)

            Analyze the Stack Overflow Developer Survey to answer a question about
            developer work and satisfaction.

            **Dataset**: `data/stackoverflow.csv`

            **Question**: {variant["research_question"]}

            Produce:
            - `analysis.py` — regression analysis script
            - `results.json` — effect estimates with uncertainty
            - `report.md` — findings and limitations
        """)

    def _make_check_solution(self, variant: dict, n_rows: int) -> str:
        hidden_kw = variant["hidden_col_keywords"]
        metric_key = variant["metric_key"]
        extra_field = variant["result_extra_field"]
        confounders = variant["confounders"]
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
                "description": "Regression or comparison analysis implemented in analysis.py",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    regression_terms = [
                        "regression", "ols", "logistic", "linear", "statsmodels",
                        "linearregression", "logisticregression", "smf", "fit(",
                        "coefficient", "coef",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in regression_terms if t in content]
                        passed = len(found) >= 2
                        detail = f"found regression terms: {found}"
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
                "description": f"At least one confounder ({', '.join(confounders)}) controlled for in analysis.py",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    confounders = {confounders!r}
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [c for c in confounders if c.lower() in content]
                        passed = len(found) >= 1
                        detail = f"confounders found in code: {{found}}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C6",
                "description": "Limitations (survey bias, self-selection) discussed in report.md",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "report.md"
                    passed = False
                    detail = ""
                    caveat_terms = ["limitation", "caveat", "bias", "self-selection",
                                    "survey", "confound", "missing", "assumption"]
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
                    p = pathlib.Path(workspace_dir) / "data" / "stackoverflow.csv"
                    passed = False
                    detail = ""
                    expected_rows = {n_rows}
                    if p.exists():
                        with open(p, newline="", encoding="utf-8") as fh:
                            actual = sum(1 for _ in csv.reader(fh)) - 1
                        passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.01))
                        detail = f"actual={{actual}}, expected={{expected_rows}}"
                    else:
                        detail = "data/stackoverflow.csv not found"
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
                    required_fields = ["analysis_type", "{metric_key}", "n_observations"]
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
