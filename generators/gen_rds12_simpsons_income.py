"""
Generator for RDS12: Simpson's Paradox in Income Analysis.

Archetype 4 — Adversarial Workspace.

The workspace contains a COMPLETE, RUNNING analysis that computes aggregate
income statistics without stratification, masking a Simpson's paradox where
the direction of the gender income gap reverses when stratified by education.

Three seed variants using adult_income dataset:

  Seed 0: Aggregate shows women have higher >50K rate in SOME education group,
          but overall women < men. The analysis only reports aggregate rates.
          Fix: stratify by education_num buckets (low/medium/high).

  Seed 1: Aggregate shows women earn more than men in a narrow occupation subset,
          but full stratification by occupation + education reverses this.
          Fix: stratify by occupation × sex.

  Seed 2: Aggregate hours_per_week is misleading — women work fewer hours on
          average, but within each marital-status group women work MORE hours.
          Fix: stratify by marital_status.

The spec tells the agent exactly what the flaw is and how to fix it.
The brief is vague: "Review and validate the existing analysis."

Rubric (6 checks):
  C1 — Stratification code present in analysis.py (groupby / pivot / crosstab)
  C2 — results.json contains 'stratified_results' key
  C3 — Both 'sex' and a stratification column appear in results.json groupby
  C4 — results.json exists and has 'aggregate_results' key
  C5 — report.md mentions Simpson / paradox / stratif / reversal
  C6 — analysis.py runs without error
"""
from __future__ import annotations

import textwrap

from generators.base import GeneratedTask
from generators.real_data_base import AdversarialWorkspaceGenerator

_VARIANTS = [
    {
        "seed": 0,
        "strat_col": "education_num",
        "strat_label": "education level",
        "strat_bucket_code": (
            "df['edu_group'] = pd.cut(df['education_num'], bins=[0,9,12,16], "
            "labels=['low','medium','high'])"
        ),
        "group_col": "edu_group",
        "bias_description": (
            "The analysis reports only aggregate >50K rates by sex. However, when "
            "stratified by education level (low/medium/high), the direction of the "
            "gender gap within some strata reverses relative to the aggregate — a "
            "classic Simpson's paradox caused by the confounding between sex and "
            "educational attainment in the dataset."
        ),
        "fix_description": (
            "Add stratification by education level. Create an `edu_group` column "
            "using `pd.cut` on `education_num` with bins [0,9,12,16] labelled "
            "low/medium/high. Report `positive_rate` for each (edu_group, sex) cell "
            "and store these in `results.json` under `stratified_results`."
        ),
        "keywords": ["simpson", "paradox", "stratif", "reversal", "confound"],
    },
    {
        "seed": 1,
        "strat_col": "occupation",
        "strat_label": "occupation",
        "strat_bucket_code": "# occupation is already categorical — no bucketing needed",
        "group_col": "occupation",
        "bias_description": (
            "The aggregate income rate by sex conceals an occupation-confounded "
            "Simpson's paradox. Women are over-represented in a few high-paying "
            "occupations (e.g. Exec-managerial) but under-represented overall. "
            "Reporting only aggregate rates misrepresents the within-occupation "
            "gender income gap."
        ),
        "fix_description": (
            "Add stratification by occupation. Compute the >50K rate for each "
            "(occupation, sex) pair and store these in `results.json` under "
            "`stratified_results`. Report whether the aggregate trend holds "
            "within individual occupation groups."
        ),
        "keywords": ["simpson", "paradox", "stratif", "reversal", "confound"],
    },
    {
        "seed": 2,
        "strat_col": "marital_status",
        "strat_label": "marital status",
        "strat_bucket_code": "# marital_status is already categorical — no bucketing needed",
        "group_col": "marital_status",
        "bias_description": (
            "The aggregate mean hours_per_week by sex shows women work fewer hours. "
            "However, within each marital-status group women work MORE hours than men "
            "in the same group. This reversal — a Simpson's paradox driven by the "
            "strong correlation between marital status and sex — is hidden by the "
            "aggregate figure."
        ),
        "fix_description": (
            "Add stratification by marital_status. Compute mean hours_per_week for "
            "each (marital_status, sex) pair and store these in `results.json` under "
            "`stratified_results`. Show that the aggregate direction reverses within "
            "strata."
        ),
        "keywords": ["simpson", "paradox", "stratif", "reversal", "confound"],
    },
]


class Generator(AdversarialWorkspaceGenerator):
    task_id = "RDS12_simpsons_income"
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
            "strat_col": v["strat_col"],
            "group_col": v["group_col"],
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
        strat_col = v["strat_col"]
        strat_label = v["strat_label"]

        return textwrap.dedent(f"""\
            \"\"\"
            Income gender-gap analysis script.

            Examines income rates by sex, stratification variable: {strat_col} ({strat_label}).
            Loads the adult_income dataset and computes aggregate income rates by sex.
            Saves results to results.json and report.md.
            \"\"\"
            import json
            import pathlib
            import numpy as np
            import pandas as pd

            # ── Load data ────────────────────────────────────────────────────────────
            data_path = pathlib.Path(__file__).parent.parent / "datasets" / "adult_income.csv"
            df = pd.read_csv(data_path, comment="#")
            df.columns = df.columns.str.strip()
            df["sex"] = df["sex"].str.strip()
            df["income"] = df["income"].str.strip()
            df["target"] = (df["income"] == ">50K").astype(int)

            # ── Aggregate analysis by sex ─────────────────────────────────────────
            # NOTE: only aggregate rates are computed — no stratification by {strat_col}
            agg = df.groupby("sex")["target"].agg(["mean", "count"]).reset_index()
            agg.columns = ["sex", "positive_rate", "n"]

            aggregate_results = agg.to_dict(orient="records")

            # ── Summary statistics ────────────────────────────────────────────────
            overall_rate = float(df["target"].mean())
            n_total = int(len(df))

            # ── Save results ──────────────────────────────────────────────────────
            out_dir = pathlib.Path(__file__).parent
            results = {{
                "n_rows": n_total,
                "overall_positive_rate": round(overall_rate, 4),
                "aggregate_results": aggregate_results,
            }}
            (out_dir / "results.json").write_text(
                json.dumps(results, indent=2), encoding="utf-8"
            )

            # ── Save report ───────────────────────────────────────────────────────
            female_rate = agg.loc[agg["sex"] == "Female", "positive_rate"].values
            male_rate = agg.loc[agg["sex"] == "Male", "positive_rate"].values
            f_pct = float(female_rate[0]) if len(female_rate) else 0.0
            m_pct = float(male_rate[0]) if len(male_rate) else 0.0

            report = f\"\"\"# Income Gender-Gap Analysis Report

            ## Dataset
            - Source: adult_income (UCI Census)
            - Rows analysed: {{n_total}}
            - Overall >50K rate: {{overall_rate:.1%}}

            ## Aggregate Results by Sex
            - Female >50K rate: {{f_pct:.1%}}
            - Male   >50K rate: {{m_pct:.1%}}
            - Gap (Male - Female): {{m_pct - f_pct:+.1%}}

            ## Conclusion
            Men earn more than women on average in this dataset.
            \"\"\"
            (out_dir / "report.md").write_text(report, encoding="utf-8")

            print(f"Rows analysed   : {{n_total}}")
            print(f"Overall >50K    : {{overall_rate:.1%}}")
            print(f"Female >50K rate: {{f_pct:.1%}}")
            print(f"Male   >50K rate: {{m_pct:.1%}}")
            print("Saved results.json and report.md")
        """)

    # ------------------------------------------------------------------
    # check_solution.py — rubric grader
    # ------------------------------------------------------------------

    def _make_check_solution(self, v: dict) -> str:
        group_col = v["group_col"]
        strat_col = v["strat_col"]

        checks = [
            {
                "id": "C1",
                "description": "Stratification code present in analysis.py (groupby/pivot/crosstab with strat column)",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import pathlib
                    src = (pathlib.Path(workspace_dir) / "analysis.py").read_text(encoding="utf-8")
                    col = {repr(strat_col)}
                    # Check for stratification: the strat column used alongside sex in a groupby
                    has_groupby = "groupby" in src or "pivot" in src or "crosstab" in src
                    has_col = col in src
                    has_sex = "sex" in src
                    passed = bool(has_groupby and has_col and has_sex)
                    detail = f"groupby={{has_groupby}}, col={{has_col}}, sex={{has_sex}}"
                """),
            },
            {
                "id": "C2",
                "description": "results.json contains 'stratified_results' key",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    rpath = pathlib.Path(workspace_dir) / "results.json"
                    if not rpath.exists():
                        passed = False
                        detail = "results.json not found"
                    else:
                        data = json.loads(rpath.read_text(encoding="utf-8"))
                        passed = "stratified_results" in data
                        detail = f"keys present: {list(data.keys())}"
                """),
            },
            {
                "id": "C3",
                "description": f"Stratification column '{strat_col}' referenced alongside 'sex' in analysis",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import pathlib
                    src = (pathlib.Path(workspace_dir) / "analysis.py").read_text(encoding="utf-8")
                    col = {repr(strat_col)}
                    # Both must appear in a groupby or similar multi-column operation
                    lines_with_both = [l for l in src.splitlines()
                                       if col in l and "sex" in l]
                    passed = len(lines_with_both) >= 1
                    detail = f"lines with both col+sex: {{len(lines_with_both)}}"
                """),
            },
            {
                "id": "C4",
                "description": "results.json exists and has 'aggregate_results' key",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    rpath = pathlib.Path(workspace_dir) / "results.json"
                    if not rpath.exists():
                        passed = False
                        detail = "results.json not found"
                    else:
                        data = json.loads(rpath.read_text(encoding="utf-8"))
                        passed = "aggregate_results" in data
                        detail = f"keys present: {list(data.keys())}"
                """),
            },
            {
                "id": "C5",
                "description": "report.md mentions Simpson's paradox or stratification",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    rpath = pathlib.Path(workspace_dir) / "report.md"
                    if not rpath.exists():
                        passed = False
                        detail = "report.md not found"
                    else:
                        content = rpath.read_text(encoding="utf-8").lower()
                        keywords = ["simpson", "paradox", "stratif", "reversal", "confound"]
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
        strat_col = v["strat_col"]
        strat_label = v["strat_label"]
        bias_desc = v["bias_description"]
        fix_desc = v["fix_description"]

        return textwrap.dedent(f"""\
            # RDS12: Simpson's Paradox in Income Analysis

            ## Overview

            The workspace contains `analysis.py`, an analysis of the Adult Income
            (Census) dataset that computes aggregate income rates by sex.
            The script runs without errors and produces `results.json` and `report.md`.

            **However, the analysis suffers from Simpson's Paradox** — it reports
            aggregate statistics that conceal a reversal when data are properly
            stratified by `{strat_col}`.

            ## The Flaw

            ### Missing Stratification

            {bias_desc}

            ### Why This Matters

            Simpson's Paradox occurs when a trend that appears in aggregate data
            disappears or reverses when the data are split into subgroups. The
            confounding variable (`{strat_col}`) is correlated with both the
            grouping variable (`sex`) and the outcome (`income`), causing the
            aggregate statistic to be misleading.

            Reporting only aggregate rates leads to incorrect conclusions about the
            relationship between sex and income.

            ## Required Fix

            {fix_desc}

            ### Specific Changes to `analysis.py`

            1. **Add stratification** by `{strat_col}` — compute income rates (or the
               relevant metric) for each combination of `{strat_col}` and `sex`.
            2. **Store stratified results** in `results.json` under the key
               `stratified_results` (a list of dicts with the group columns and values).
            3. **Update `report.md`** to acknowledge the Simpson's Paradox, show
               both aggregate and stratified results, and draw the correct conclusion.

            ## Deliverables

            - Fixed `analysis.py` (stratification added)
            - `results.json` with both `aggregate_results` and `stratified_results` keys
            - `report.md` that mentions Simpson's paradox or stratification

            ## Grading Rubric

            | Check | Description |
            |---|---|
            | C1 | Stratification code present in `analysis.py` |
            | C2 | `results.json` contains `stratified_results` key |
            | C3 | `{strat_col}` and `sex` used together in groupby/analysis |
            | C4 | `results.json` contains `aggregate_results` key |
            | C5 | `report.md` mentions Simpson's paradox or stratification |
            | C6 | `analysis.py` runs without error |
        """)

    # ------------------------------------------------------------------
    # brief.md
    # ------------------------------------------------------------------

    def _make_brief(self, v: dict) -> str:
        strat_label = v["strat_label"]
        return textwrap.dedent(f"""\
            # RDS12: Income Gender-Gap Analysis Review

            ## Task

            Review and validate the existing analysis in `analysis.py` for methodological issues.

            The script analyses the `adult_income` dataset to examine the gender income
            gap. It currently runs without error and produces `results.json` and `report.md`.

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
