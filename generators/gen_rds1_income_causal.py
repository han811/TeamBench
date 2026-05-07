"""
Parameterized generator for RDS1: Income Causal Analysis (Archetype 3 — Open-Ended).

Uses the real UCI Adult Income dataset. Three seed variants ask different causal questions:
  Seed 0: Does college education causally increase P(income >$50K)?
  Seed 1: Does working 45+ hours causally increase income?
  Seed 2: Does marriage causally increase income?

No scaffold code is provided. The agent receives the raw data and must choose an
appropriate causal inference method (propensity score matching, regression adjustment,
IPW, stratification, OLS, etc.) and produce structured output files.

Rubric checks (8):
  C1: analysis.py runs without error
  C2: Confounding addressed (keyword in analysis.py)
  C3: Effect reported with uncertainty (treatment_effect + ci_lower in results.json)
  C4: Hidden confounders addressed (per-seed keywords in analysis.py)
  C5: Assumption test present (balance/overlap/diagnostic/vif/positivity keyword)
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
        "treatment": "college_education",
        "treatment_label": "college education (Bachelor's or higher)",
        "treatment_col": "education",
        "treatment_binary_desc": (
            "Create a binary treatment indicator: 1 if education is "
            "'Bachelors', 'Masters', 'Doctorate', or 'Prof-school'; 0 otherwise."
        ),
        "outcome": "high_income",
        "outcome_label": "probability of earning >$50K",
        "outcome_col": "income",
        "research_question": (
            "Does college education (Bachelor's degree or higher) causally increase "
            "the probability of earning more than $50,000 per year?"
        ),
        "confounders": ["age", "hours_per_week", "occupation", "marital_status"],
        # Hidden confounder keywords the grader looks for in analysis.py
        "hidden_confounder_keywords": ["occupation", "marital_status"],
        "context": (
            "Education and income are strongly correlated, but this correlation may be "
            "confounded by age (older workers have more education and higher pay), "
            "hours worked, occupation type, and marital status (which affects household "
            "income reporting). A naive comparison overstates the causal effect."
        ),
    },
    {
        # Seed 1
        "treatment": "long_hours",
        "treatment_label": "working 45 or more hours per week",
        "treatment_col": "hours_per_week",
        "treatment_binary_desc": (
            "Create a binary treatment indicator: 1 if hours_per_week >= 45; 0 otherwise."
        ),
        "outcome": "high_income",
        "outcome_label": "probability of earning >$50K",
        "outcome_col": "income",
        "research_question": (
            "Does working 45 or more hours per week causally increase the probability "
            "of earning more than $50,000 per year?"
        ),
        "confounders": ["education", "age", "occupation", "workclass"],
        "hidden_confounder_keywords": ["occupation", "workclass"],
        "context": (
            "Hours worked and income are positively correlated, but the relationship "
            "is confounded by occupation (high-paying salaried jobs require long hours), "
            "education level, age, and work sector (workclass). Self-employed and "
            "executive-track workers both work long hours and earn more — the treatment "
            "effect may be partly a selection artifact."
        ),
    },
    {
        # Seed 2
        "treatment": "married",
        "treatment_label": "being married (spouse present)",
        "treatment_col": "marital_status",
        "treatment_binary_desc": (
            "Create a binary treatment indicator: 1 if marital_status is "
            "'Married-civ-spouse' or 'Married-AF-spouse'; 0 otherwise."
        ),
        "outcome": "high_income",
        "outcome_label": "probability of earning >$50K",
        "outcome_col": "income",
        "research_question": (
            "Does being married (spouse present) causally increase the probability "
            "of earning more than $50,000 per year?"
        ),
        "confounders": ["age", "education", "hours_per_week", "occupation"],
        "hidden_confounder_keywords": ["age", "occupation"],
        "context": (
            "Married individuals have significantly higher income on average, but age "
            "is a major confounder (older workers are more likely to be married AND earn "
            "more). Education and occupation further confound the relationship. The "
            "observed gap is likely a combination of selection into marriage (higher-earning "
            "individuals marry at higher rates) and genuine household economic effects."
        ),
    },
]

# Columns to keep in the workspace CSV (all causally relevant; drop fnlwgt/relationship)
_KEEP_COLUMNS = [
    "age",
    "workclass",
    "education",
    "education_num",
    "marital_status",
    "occupation",
    "sex",
    "capital_gain",
    "capital_loss",
    "hours_per_week",
    "native_country",
    "income",
]


class Generator(OpenEndedGenerator):
    task_id = "RDS1_income_causal"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]

    dataset_name = "adult_income"
    dataset_license = "CC BY 4.0"
    dataset_source = "UCI ML Repository"

    def generate(self, seed: int) -> GeneratedTask:
        variant = _VARIANTS[seed % len(_VARIANTS)]

        # Load and subsample real data — 1200 rows, seed-specific sample
        rows = self.load_dataset()
        rows = self.subsample(rows, seed=seed + 100, frac=0.025)   # ~1200 rows
        rows = self.select_columns(rows, _KEEP_COLUMNS)
        n_rows = len(rows)
        data_csv = self.rows_to_csv(rows, _KEEP_COLUMNS)

        # Build workspace files
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
            "treatment": variant["treatment"],
            "treatment_label": variant["treatment_label"],
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

    # ── Spec / brief generators ───────────────────────────────────────────────

    def _make_spec(self, variant: dict, n_rows: int) -> str:
        confounder_list = ", ".join(f"`{c}`" for c in variant["confounders"])
        return textwrap.dedent(f"""\
            # RDS1: Income Causal Analysis

            ## Research Question
            **{variant["research_question"]}**

            ## Dataset
            - File: `data/adult_income.csv`
            - Rows: {n_rows} (subsample of the UCI Adult Income dataset)
            - Columns: {", ".join(f"`{c}`" for c in _KEEP_COLUMNS)}
            - Outcome: `income` encoded as `>50K` or `<=50K`

            ## Treatment Definition
            {variant["treatment_binary_desc"]}

            ## Background and Confounding
            {variant["context"]}

            ## Your Task
            Conduct a causal analysis to estimate the effect of the treatment on income.
            You are free to choose any appropriate causal inference method, including but
            not limited to:
            - Regression adjustment (OLS / logistic regression with controls)
            - Propensity score matching or weighting (IPW)
            - Stratification on confounders
            - Doubly robust estimation

            **Do not use a naive unadjusted comparison** — you must address confounding.

            ### Confounders to Control For
            At minimum, adjust for: {confounder_list}

            ## Required Deliverables

            ### 1. `analysis.py`
            A Python script that:
            - Loads `data/adult_income.csv`
            - Constructs the binary treatment indicator
            - Applies a causal method that controls for confounders
            - Estimates the Average Treatment Effect (ATE) or Average Treatment Effect
              on the Treated (ATT) with a 95% confidence interval
            - Tests at least one key assumption (e.g., covariate balance, overlap/positivity,
              or VIF for multicollinearity)
            - Saves `results.json` and `report.md`

            ### 2. `results.json`
            Must contain at minimum:
            ```json
            {{
              "treatment": "<treatment name>",
              "treatment_effect": <float>,
              "ci_lower": <float>,
              "ci_upper": <float>,
              "method": "<method name>",
              "n_treated": <int>,
              "n_control": <int>
            }}
            ```

            ### 3. `report.md`
            A brief (300–600 word) report covering:
            - Method chosen and rationale
            - Point estimate and confidence interval
            - Assumption checks performed and their results
            - **Limitations** and threats to causal validity (unmeasured confounders,
              selection bias, SUTVA violations, etc.)

            ## Grading Criteria
            Your solution is evaluated on:
            1. `analysis.py` runs without error
            2. Confounding is explicitly addressed in the code
            3. Effect estimate is reported with confidence interval in `results.json`
            4. Key confounders ({confounder_list}) appear in the analysis code
            5. At least one assumption test is present
            6. `report.md` discusses limitations
            7. Data is loaded correctly (correct row count)
            8. `results.json` contains required fields and is valid JSON
        """)

    def _make_brief(self, variant: dict) -> str:
        return textwrap.dedent(f"""\
            # RDS1: Income Causal Analysis (Brief)

            Analyze the Adult Income dataset to answer a causal question.

            **Dataset**: `data/adult_income.csv`

            **Question**: {variant["research_question"]}

            Produce:
            - `analysis.py` — causal analysis script
            - `results.json` — effect estimate with confidence interval
            - `report.md` — findings and limitations
        """)

    # ── Rubric check generator ────────────────────────────────────────────────

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
                "description": "Confounding addressed in analysis.py",
                "type": "output_contains",
                "path": "analysis.py",
                "patterns": [
                    # at least one of these causal/adjustment terms must appear
                    # we use OR logic via custom_python below, but output_contains
                    # checks all patterns — so we use a single broad OR check via
                    # custom_python for C2 instead
                ],
            },
            {
                "id": "C3",
                "description": "treatment_effect and ci_lower present in results.json",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    if p.exists():
                        try:
                            d = json.loads(p.read_text())
                            has_te = "treatment_effect" in d
                            has_ci = "ci_lower" in d
                            passed = has_te and has_ci
                            detail = f"treatment_effect={has_te}, ci_lower={has_ci}"
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
                "description": "Assumption test present in analysis.py (balance/overlap/diagnostic/vif/positivity)",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    assumption_terms = ["balance", "overlap", "positivity", "diagnostic", "vif",
                                        "standardized", "smd", "common support", "assumption"]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in assumption_terms if t in content]
                        passed = len(found) > 0
                        detail = f"found assumption terms: {found}"
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
                            actual = sum(1 for _ in csv.reader(fh)) - 1  # minus header
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
                    required_fields = ["treatment_effect", "ci_lower", "ci_upper", "method"]
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

        # C2 requires OR logic — replace the empty output_contains with custom_python
        checks[1] = {
            "id": "C2",
            "description": "Confounding addressed in analysis.py (propensity/matching/stratif/control/adjust/covariate/ols/logistic/ipw)",
            "type": "custom_python",
            "code": textwrap.dedent("""\
                import pathlib
                p = pathlib.Path(workspace_dir) / "analysis.py"
                passed = False
                detail = ""
                causal_terms = [
                    "propensity", "matching", "stratif", "control", "adjust",
                    "covariate", "ols", "logistic", "ipw", "weighting",
                    "regression", "confound", "confounder",
                ]
                if p.exists():
                    content = p.read_text(encoding="utf-8").lower()
                    found = [t for t in causal_terms if t in content]
                    passed = len(found) >= 2
                    detail = f"found causal terms: {found}"
                else:
                    detail = "analysis.py not found"
            """),
        }

        return self.make_check_solution(checks)
