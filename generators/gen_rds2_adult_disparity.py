"""
Parameterized generator for RDS2: Adult Income Disparity Analysis (Archetype 3 — Open-Ended).

Uses the real UCI Adult Income dataset. Three seed variants ask different disparity questions:
  Seed 0: Gender pay disparity after controlling for occupation
  Seed 1: Race pay disparity after controlling for education
  Seed 2: Age discrimination after controlling for experience (education_num proxy)

No scaffold code is provided. The agent receives the raw data and must choose an
appropriate method (regression adjustment, stratification, matching, etc.) and
produce structured output files.

Rubric checks (8):
  C1: analysis.py runs without error
  C2: Disparity measure reported with adjustment/control (keywords in analysis.py)
  C3: Effect reported with uncertainty (disparity_estimate + ci_lower in results.json)
  C4: Key confounders referenced in analysis.py
  C5: Intersectional or subgroup analysis present
  C6: Limitations discussed (report.md contains caveat language)
  C7: Data loaded correctly (row count check)
  C8: results.json is valid JSON with required fields
"""
from __future__ import annotations

import textwrap

from generators.base import GeneratedTask
from generators.real_data_base import OpenEndedGenerator

# ── Seed-variant definitions ───────────────────────────────────────────────────

_VARIANTS = [
    {
        # Seed 0
        "group_var": "sex",
        "group_label": "gender",
        "group_values": ["Male", "Female"],
        "reference_group": "Male",
        "comparison_group": "Female",
        "control_var": "occupation",
        "control_label": "occupation",
        "outcome": "high_income",
        "outcome_label": "probability of earning >$50K",
        "outcome_col": "income",
        "research_question": (
            "Is there a statistically significant gender pay disparity in P(income >$50K) "
            "after controlling for occupation?"
        ),
        "confounders": ["occupation", "education", "age", "hours_per_week"],
        "hidden_confounder_keywords": ["occupation", "education"],
        "context": (
            "Women earn less than men on average in this dataset. However, occupational "
            "sorting (women concentrated in lower-paying occupations) and education "
            "differences partially explain the gap. A naive comparison overstates the "
            "within-occupation gender gap. The analysis should estimate the adjusted "
            "disparity — the gap that remains after holding occupation and other "
            "covariates constant."
        ),
        "subgroup_hint": "Consider analyzing the gender gap separately within high-paying vs. low-paying occupations.",
    },
    {
        # Seed 1
        "group_var": "race",
        "group_label": "race",
        "group_values": ["White", "Black", "Asian-Pac-Islander", "Amer-Indian-Eskimo", "Other"],
        "reference_group": "White",
        "comparison_group": "Black",
        "control_var": "education",
        "control_label": "education level",
        "outcome": "high_income",
        "outcome_label": "probability of earning >$50K",
        "outcome_col": "income",
        "research_question": (
            "Is there a statistically significant racial pay disparity in P(income >$50K) "
            "after controlling for education level?"
        ),
        "confounders": ["education", "occupation", "age", "hours_per_week"],
        "hidden_confounder_keywords": ["education", "occupation"],
        "context": (
            "Racial income disparities persist even after controlling for education, "
            "suggesting structural barriers beyond educational attainment. However, "
            "occupation, age, and hours worked are important additional confounders. "
            "The analysis should compare the unadjusted gap vs. the education-adjusted "
            "gap to quantify how much education explains."
        ),
        "subgroup_hint": "Consider whether the racial gap varies across education levels (interaction term).",
    },
    {
        # Seed 2
        "group_var": "age_group",
        "group_label": "age group",
        "group_values": ["young (18-35)", "prime (36-55)", "older (56+)"],
        "reference_group": "prime (36-55)",
        "comparison_group": "young (18-35)",
        "control_var": "education_num",
        "control_label": "years of education (education_num)",
        "outcome": "high_income",
        "outcome_label": "probability of earning >$50K",
        "outcome_col": "income",
        "research_question": (
            "Is there evidence of age-based income discrimination — specifically, do "
            "younger workers (18–35) earn significantly less than prime-age workers (36–55) "
            "after controlling for education and experience?"
        ),
        "confounders": ["education_num", "occupation", "hours_per_week", "workclass"],
        "hidden_confounder_keywords": ["education_num", "occupation"],
        "context": (
            "Younger workers earn less than prime-age workers. This may reflect genuine "
            "experience accumulation (human capital) rather than discrimination. "
            "education_num proxies years of schooling. Controlling for education_num "
            "and occupation isolates the age effect from human-capital accumulation. "
            "Create age groups: young=18-35, prime=36-55, older=56+."
        ),
        "subgroup_hint": "Consider whether the age effect differs by occupation or workclass sector.",
    },
]

# Columns to keep in the workspace CSV
_KEEP_COLUMNS = [
    "age",
    "workclass",
    "education",
    "education_num",
    "marital_status",
    "occupation",
    "sex",
    "race",
    "capital_gain",
    "capital_loss",
    "hours_per_week",
    "income",
]


class Generator(OpenEndedGenerator):
    task_id = "RDS2_adult_disparity"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]

    dataset_name = "adult_income"
    dataset_license = "CC BY 4.0"
    dataset_source = "UCI ML Repository"

    def generate(self, seed: int) -> GeneratedTask:
        variant = _VARIANTS[seed % len(_VARIANTS)]

        rows = self.load_dataset()
        rows = self.subsample(rows, seed=seed + 200, frac=0.04)  # ~1300 rows
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
            "data/adult_income.csv": data_csv,
            "requirements.txt": requirements_txt,
            "check_solution.py": check_py,
            "task.yaml": task_yaml,
        }

        expected = {
            "group_var": variant["group_var"],
            "group_label": variant["group_label"],
            "research_question": variant["research_question"],
            "confounders": variant["confounders"],
            "hidden_confounder_keywords": variant["hidden_confounder_keywords"],
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
        confounder_list = ", ".join(f"`{c}`" for c in variant["confounders"])
        return textwrap.dedent(f"""\
            # RDS2: Adult Income Disparity Analysis

            ## Research Question
            **{variant["research_question"]}**

            ## Dataset
            - File: `data/adult_income.csv`
            - Rows: {n_rows} (subsample of the UCI Adult Income dataset)
            - Columns: {", ".join(f"`{c}`" for c in _KEEP_COLUMNS)}
            - Outcome: `income` encoded as `>50K` or `<=50K`

            ## Group Definition
            - Protected attribute: `{variant["group_var"]}`
            - Reference group: `{variant["reference_group"]}`
            - Comparison group: `{variant["comparison_group"]}`

            ## Background and Confounding
            {variant["context"]}

            ## Your Task
            Conduct a disparity analysis to estimate the income gap between groups
            after controlling for relevant confounders. You are free to choose any
            appropriate method, including but not limited to:
            - Logistic regression with group indicator and controls
            - Stratified analysis within levels of key confounders
            - Propensity score matching or weighting
            - Oaxaca-Blinder decomposition

            **Do not report a naive unadjusted gap** — you must control for confounders.

            ### Confounders to Control For
            At minimum, adjust for: {confounder_list}

            ### Subgroup Analysis
            {variant["subgroup_hint"]}

            ## Required Deliverables

            ### 1. `analysis.py`
            A Python script that:
            - Loads `data/adult_income.csv`
            - Constructs the binary outcome (1 if income `>50K`, else 0)
            - Computes both unadjusted and adjusted disparity estimates
            - Reports a 95% confidence interval for the adjusted estimate
            - Performs at least one subgroup or intersectional analysis
            - Saves `results.json` and `report.md`

            ### 2. `results.json`
            Must contain at minimum:
            ```json
            {{
              "group_var": "<protected attribute>",
              "disparity_estimate": <float>,
              "ci_lower": <float>,
              "ci_upper": <float>,
              "method": "<method name>",
              "unadjusted_gap": <float>,
              "adjusted_gap": <float>
            }}
            ```

            ### 3. `report.md`
            A brief (300–600 word) report covering:
            - Unadjusted vs. adjusted disparity estimates
            - Method chosen and rationale
            - Subgroup findings
            - **Limitations** (unmeasured confounders, selection bias, etc.)

            ## Grading Criteria
            Your solution is evaluated on:
            1. `analysis.py` runs without error
            2. Adjusted disparity is computed (control/adjust keywords in code)
            3. Effect reported with confidence interval in `results.json`
            4. Key confounders ({confounder_list}) appear in analysis code
            5. Subgroup or intersectional analysis is present
            6. `report.md` discusses limitations
            7. Data is loaded correctly (correct row count)
            8. `results.json` contains required fields and is valid JSON
        """)

    def _make_brief(self, variant: dict) -> str:
        return textwrap.dedent(f"""\
            # RDS2: Adult Income Disparity Analysis (Brief)

            Analyze the Adult Income dataset to quantify a pay disparity.

            **Dataset**: `data/adult_income.csv`

            **Question**: {variant["research_question"]}

            Produce:
            - `analysis.py` — disparity analysis script
            - `results.json` — adjusted disparity estimate with confidence interval
            - `report.md` — findings and limitations
        """)

    def _make_check_solution(self, variant: dict, n_rows: int) -> str:
        hidden_kw = variant["hidden_confounder_keywords"]
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
                "description": "Adjusted disparity computed in analysis.py (control/adjust/regression/stratif/propensity)",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    adjustment_terms = [
                        "control", "adjust", "regression", "stratif", "propensity",
                        "logistic", "ols", "covariate", "confounder", "confound",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in adjustment_terms if t in content]
                        passed = len(found) >= 2
                        detail = f"found adjustment terms: {found}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C3",
                "description": "disparity_estimate and ci_lower present in results.json",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    if p.exists():
                        try:
                            d = json.loads(p.read_text())
                            has_est = "disparity_estimate" in d
                            has_ci = "ci_lower" in d
                            passed = has_est and has_ci
                            detail = f"disparity_estimate={has_est}, ci_lower={has_ci}"
                        except Exception as e:
                            detail = str(e)
                    else:
                        detail = "results.json not found"
                """),
            },
            {
                "id": "C4",
                "description": f"Key confounders ({', '.join(hidden_kw)}) referenced in analysis.py",
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
                "description": "Subgroup or intersectional analysis present in analysis.py",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    subgroup_terms = [
                        "subgroup", "intersect", "groupby", "group_by", "split",
                        "subset", "stratum", "strata", "within", "interaction",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in subgroup_terms if t in content]
                        passed = len(found) >= 1
                        detail = f"found subgroup terms: {found}"
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
                    caveat_terms = ["limitation", "caveat", "threat", "assumption",
                                    "unmeasured", "confounder", "selection bias",
                                    "confound", "bias"]
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
                    p = pathlib.Path(workspace_dir) / "data" / "adult_income.csv"
                    passed = False
                    detail = ""
                    expected_rows = {n_rows}
                    if p.exists():
                        with open(p, newline="", encoding="utf-8") as fh:
                            actual = sum(1 for _ in csv.reader(fh)) - 1
                        passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.01))
                        detail = f"actual={{actual}}, expected={{expected_rows}}"
                    else:
                        detail = "data/adult_income.csv not found"
                """),
            },
            {
                "id": "C8",
                "description": "results.json is valid JSON with required fields",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    required_fields = ["disparity_estimate", "ci_lower", "ci_upper", "method"]
                    if p.exists():
                        try:
                            d = json.loads(p.read_text(encoding="utf-8"))
                            missing = [f for f in required_fields if f not in d]
                            passed = len(missing) == 0
                            detail = f"missing fields: {missing}" if missing else "all required fields present"
                        except json.JSONDecodeError as e:
                            detail = f"JSON parse error: {e}"
                    else:
                        detail = "results.json not found"
                """),
            },
        ]
        return self.make_check_solution(checks)
