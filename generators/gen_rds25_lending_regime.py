"""
Generator for RDS25: Lending Regime Shift Investigation (Archetype 2 — Synthesis).

Dataset: lending_club (loan_amnt, int_rate, grade, loan_status, default_ind, ...)

Task: A model that predicted loan defaults was trained on historical data but has
shown degraded performance in the "recent" period. The agent must synthesize evidence
from three corpus documents to explain why.

Corpus documents (information distributed — no single source tells the whole story):
  - interest_rates.csv   : FRED-style rate data showing a significant rate hike
  - state_unemployment.csv : State-level unemployment spike in 3 key states
  - policy_changes.md    : Lending policy document noting underwriting criteria changed

Synthesis required: Rate hike + unemployment spike + underwriting policy change =
regime shift that caused distributional drift, invalidating the trained model.

Rubric (8 checks):
  C1 — analysis.py runs without error
  C2 — Rate/interest regime factor mentioned in analysis.py or report.md
  C3 — Unemployment factor mentioned
  C4 — Policy/underwriting change mentioned
  C5 — results.json exists with drift_factors key listing >= 2 factors
  C6 — report.md recommends recalibration or retraining
  C7 — Data loaded correctly (row count check)
  C8 — results.json is valid JSON with required fields
"""
from __future__ import annotations

import textwrap

from generators.base import GeneratedTask
from generators.real_data_base import SynthesisGenerator
from generators.primitives import SeededRandom


# Seed variants — different "recent period" windows and affected states
_VARIANTS = [
    {
        "seed": 0,
        "recent_start_month": "2018-01",
        "recent_end_month": "2018-12",
        "baseline_start_month": "2016-01",
        "baseline_end_month": "2017-12",
        "affected_states": ["OH", "MI", "PA"],
        "rate_hike_from": 1.5,
        "rate_hike_to": 2.25,
        "rate_hike_period": "Q2 2018",
        "unemployment_spike_states": "Ohio, Michigan, and Pennsylvania",
        "policy_change_date": "March 2018",
        "policy_change_detail": "minimum FICO score raised from 620 to 660, DTI cap lowered from 45% to 40%",
    },
    {
        "seed": 1,
        "recent_start_month": "2019-01",
        "recent_end_month": "2019-12",
        "baseline_start_month": "2017-01",
        "baseline_end_month": "2018-12",
        "affected_states": ["TX", "FL", "GA"],
        "rate_hike_from": 2.0,
        "rate_hike_to": 2.75,
        "rate_hike_period": "Q1 2019",
        "unemployment_spike_states": "Texas, Florida, and Georgia",
        "policy_change_date": "January 2019",
        "policy_change_detail": "maximum loan term reduced from 60 to 48 months for grades C-E, verification required for all loans > $15k",
    },
    {
        "seed": 2,
        "recent_start_month": "2017-06",
        "recent_end_month": "2018-05",
        "baseline_start_month": "2015-06",
        "baseline_end_month": "2016-05",
        "affected_states": ["CA", "NY", "IL"],
        "rate_hike_from": 0.75,
        "rate_hike_to": 1.5,
        "rate_hike_period": "Q3 2017",
        "unemployment_spike_states": "California, New York, and Illinois",
        "policy_change_date": "June 2017",
        "policy_change_detail": "employment verification now required for all self-employed borrowers, maximum DTI for grade A loans set to 35%",
    },
]

_KEEP_COLUMNS = [
    "loan_amnt", "funded_amnt", "term", "int_rate", "installment",
    "grade", "sub_grade", "emp_length", "home_ownership", "annual_inc",
    "verification_status", "loan_status", "purpose", "dti",
    "delinq_2yrs", "fico_range_low", "fico_range_high",
    "open_acc", "revol_util", "default_ind",
]


class Generator(SynthesisGenerator):
    task_id = "RDS25_lending_regime"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]

    dataset_name = "lending_club"
    dataset_license = "CC0"
    dataset_source = "Kaggle / Lending Club"

    def generate(self, seed: int) -> GeneratedTask:
        v = _VARIANTS[seed % len(_VARIANTS)]
        rng = SeededRandom(seed + 250)

        rows = self.load_dataset()
        rows = self.subsample(rows, seed=seed + 250, frac=0.04)   # ~2000 rows
        rows = self.select_columns(rows, _KEEP_COLUMNS)
        n_rows = len(rows)
        data_csv = self.rows_to_csv(rows, _KEEP_COLUMNS)

        corpus = {
            "interest_rates.csv": self._gen_rates_csv(v, rng),
            "state_unemployment.csv": self._gen_unemployment_csv(v, rng),
            "policy_changes.md": self._gen_policy_md(v),
        }

        requirements_txt = "pandas>=1.5\nnumpy>=1.23\nscipy>=1.9\nscikit-learn>=1.1\n"
        task_yaml = self.make_task_yaml()
        check_py = self._make_check_solution(v, n_rows)

        workspace_files = {
            "data/lending_club.csv": data_csv,
            "requirements.txt": requirements_txt,
            "check_solution.py": check_py,
            "task.yaml": task_yaml,
        }

        expected = {
            "drift_factors": ["interest_rate_hike", "unemployment_spike", "policy_change"],
            "recent_period": f"{v['recent_start_month']} to {v['recent_end_month']}",
            "affected_states": v["affected_states"],
            "n_rows": n_rows,
            "required_output_files": ["analysis.py", "results.json", "report.md"],
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._make_spec(v, n_rows),
            brief_md=self._make_brief(v),
            expected=expected,
            workspace_files=workspace_files,
            corpus_files=corpus,
        )

    # ── Corpus generators ─────────────────────────────────────────────────────

    def _gen_rates_csv(self, v: dict, rng: SeededRandom) -> str:
        lines = ["date,fed_funds_rate,prime_rate,10yr_treasury"]
        # Generate 36 months of rate data showing a hike
        base_fed = v["rate_hike_from"]
        hike_to = v["rate_hike_to"]
        # months before, during, after hike
        months = [
            "2015-01", "2015-04", "2015-07", "2015-10",
            "2016-01", "2016-04", "2016-07", "2016-10",
            "2017-01", "2017-04", "2017-07", "2017-10",
            "2018-01", "2018-04", "2018-07", "2018-10",
            "2019-01", "2019-04", "2019-07", "2019-10",
        ]
        for i, m in enumerate(months):
            # Rate hike occurs around index 12-14 depending on seed
            hike_idx = {"2018-01": 12, "2019-01": 16, "2017-06": 10}.get(
                v["recent_start_month"], 12
            )
            if i < hike_idx:
                fed = round(base_fed + rng.uniform(-0.1, 0.1), 2)
            else:
                fed = round(hike_to + rng.uniform(-0.05, 0.1), 2)
            prime = round(fed + 3.0, 2)
            treasury = round(fed + 0.5 + rng.uniform(-0.1, 0.2), 2)
            lines.append(f"{m},{fed},{prime},{treasury}")
        # Add distractor column: stock market index (irrelevant)
        header = lines[0] + ",sp500_monthly_return"
        data_lines = []
        for line in lines[1:]:
            data_lines.append(line + f",{round(rng.uniform(-3.0, 5.0), 2)}")
        return header + "\n" + "\n".join(data_lines) + "\n"

    def _gen_unemployment_csv(self, v: dict, rng: SeededRandom) -> str:
        states = v["affected_states"]
        all_states = states + ["WA", "CO", "MN", "NC", "VA"]
        lines = ["state,year,quarter,unemployment_rate"]
        for st in all_states:
            for yr in [2016, 2017, 2018, 2019]:
                for q in [1, 2, 3, 4]:
                    base = rng.uniform(3.5, 5.5)
                    # Spike for affected states in recent period
                    if st in states and yr >= int(v["recent_start_month"][:4]):
                        rate = round(base + rng.uniform(1.5, 3.0), 2)
                    else:
                        rate = round(base + rng.uniform(-0.3, 0.3), 2)
                    lines.append(f"{st},{yr},{q},{rate}")
        return "\n".join(lines) + "\n"

    def _gen_policy_md(self, v: dict) -> str:
        return textwrap.dedent(f"""\
            # Lending Policy Bulletin — Underwriting Criteria Update
            **Effective Date**: {v['policy_change_date']}
            **Reference**: UW-POLICY-2018-004

            ## Summary of Changes

            Following a quarterly risk review, the Credit Risk Committee has approved
            the following amendments to lending underwriting criteria:

            **Changes implemented ({v['policy_change_date']}):**
            - {v['policy_change_detail'].capitalize()}.
            - Enhanced fraud screening for applications in elevated-risk ZIP codes.
            - Automated income verification cross-referenced with IRS records for
              all loan grades B and below.

            ## Rationale

            The committee reviewed default patterns from the past 18 months and
            identified elevated risk concentration in certain borrower segments.
            These changes are intended to reduce exposure while maintaining growth
            targets.

            ## Impact Assessment

            Models trained on pre-{v['policy_change_date']} data may underestimate
            default risk for the post-change population due to compositional shift
            in the approved loan book. Risk teams should evaluate model performance
            separately for the pre- and post-policy cohorts.

            ## Historical Note (Distractor)

            The committee also reviewed mortgage prepayment speeds and concluded
            no changes to prepayment assumptions are warranted at this time.
            Consumer auto loan policies remain unchanged.

            ---
            *Confidential — Internal Use Only*
        """)

    # ── Spec / brief ──────────────────────────────────────────────────────────

    def _make_spec(self, v: dict, n_rows: int) -> str:
        return textwrap.dedent(f"""\
            # RDS25: Lending Model Performance Investigation

            ## Background

            A logistic regression model was trained on Lending Club loan data from
            **{v['baseline_start_month']} to {v['baseline_end_month']}** to predict
            loan defaults. In the recent period (**{v['recent_start_month']} to
            {v['recent_end_month']}**) the model's AUC dropped from 0.78 to 0.61.

            Your task is to investigate WHY model performance degraded.

            ## Dataset

            - File: `data/lending_club.csv`
            - Rows: {n_rows} (subsample)
            - Key columns: `loan_amnt`, `int_rate`, `grade`, `dti`, `fico_range_low`,
              `annual_inc`, `default_ind`, `verification_status`

            ## Corpus Documents

            Additional reference documents are provided in `corpus/`:

            | File | Description |
            |------|-------------|
            | `interest_rates.csv` | Monthly Fed funds rate, prime rate, 10yr treasury |
            | `state_unemployment.csv` | State-level unemployment by year and quarter |
            | `policy_changes.md` | Internal underwriting policy change bulletin |

            **Important**: No single document fully explains the performance drop.
            You must synthesize evidence across all three sources.

            ## Required Deliverables

            ### 1. `analysis.py`
            A Python script that:
            - Loads the loan dataset and compares default rates baseline vs recent periods
            - Reads and analyzes all three corpus documents
            - Identifies distributional shifts in loan features between periods
            - Quantifies the contribution of each identified factor

            ### 2. `results.json`
            ```json
            {{
              "baseline_default_rate": <float>,
              "recent_default_rate": <float>,
              "drift_factors": ["<factor1>", "<factor2>", ...],
              "primary_cause": "<string>",
              "recommendation": "<string>"
            }}
            ```

            ### 3. `report.md`
            A 400–700 word report explaining:
            - What changed between baseline and recent periods
            - Which external factors drove the regime shift
            - Why the model degraded (not just what degraded)
            - Recommended remediation (recalibration, retrain, monitoring)

            ## Grading Criteria
            1. `analysis.py` runs without error
            2. Interest rate / rate hike factor identified
            3. Unemployment spike factor identified
            4. Policy / underwriting change factor identified
            5. `results.json` contains `drift_factors` with ≥ 2 entries
            6. `report.md` recommends recalibration or retraining
            7. Data loaded correctly (correct row count)
            8. `results.json` is valid JSON with required fields
        """)

    def _make_brief(self, v: dict) -> str:
        return textwrap.dedent(f"""\
            # RDS25: Lending Model Performance Investigation (Brief)

            A loan default prediction model trained on data from
            {v['baseline_start_month']}–{v['baseline_end_month']} has degraded in
            the recent period {v['recent_start_month']}–{v['recent_end_month']}.

            **Dataset**: `data/lending_club.csv`

            **Corpus docs** (in `corpus/`):
            - `interest_rates.csv`
            - `state_unemployment.csv`
            - `policy_changes.md`

            Investigate the root causes of the performance drop. Produce:
            - `analysis.py` — investigation script
            - `results.json` — structured findings
            - `report.md` — narrative explanation and recommendations
        """)

    # ── Grader ────────────────────────────────────────────────────────────────

    def _make_check_solution(self, v: dict, n_rows: int) -> str:
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
                "description": "Interest rate / rate hike factor identified in analysis or report",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    passed = False
                    detail = ""
                    terms = ["interest_rate", "rate hike", "fed funds", "rate_hike",
                             "interest rate", "fedfunds", "fed_funds", "prime_rate"]
                    for fname in ["analysis.py", "report.md"]:
                        p = pathlib.Path(workspace_dir) / fname
                        if p.exists():
                            content = p.read_text(encoding="utf-8").lower()
                            found = [t for t in terms if t in content]
                            if found:
                                passed = True
                                detail = f"found in {fname}: {found}"
                                break
                    if not passed:
                        detail = "rate hike terms not found in analysis.py or report.md"
                """),
            },
            {
                "id": "C3",
                "description": "Unemployment factor identified in analysis or report",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    passed = False
                    detail = ""
                    terms = ["unemployment", "unrate", "jobless", "labor market",
                             "employment rate", "job loss"]
                    for fname in ["analysis.py", "report.md"]:
                        p = pathlib.Path(workspace_dir) / fname
                        if p.exists():
                            content = p.read_text(encoding="utf-8").lower()
                            found = [t for t in terms if t in content]
                            if found:
                                passed = True
                                detail = f"found in {fname}: {found}"
                                break
                    if not passed:
                        detail = "unemployment terms not found"
                """),
            },
            {
                "id": "C4",
                "description": "Policy / underwriting change factor identified in analysis or report",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    passed = False
                    detail = ""
                    terms = ["policy", "underwriting", "criteria", "fico", "dti",
                             "policy_change", "policy change", "underwrite"]
                    for fname in ["analysis.py", "report.md"]:
                        p = pathlib.Path(workspace_dir) / fname
                        if p.exists():
                            content = p.read_text(encoding="utf-8").lower()
                            found = [t for t in terms if t in content]
                            if found:
                                passed = True
                                detail = f"found in {fname}: {found}"
                                break
                    if not passed:
                        detail = "policy/underwriting terms not found"
                """),
            },
            {
                "id": "C5",
                "description": "results.json contains drift_factors with >= 2 entries",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    if p.exists():
                        try:
                            d = json.loads(p.read_text(encoding="utf-8"))
                            factors = d.get("drift_factors", [])
                            passed = isinstance(factors, list) and len(factors) >= 2
                            detail = f"drift_factors={factors}"
                        except Exception as e:
                            detail = str(e)
                    else:
                        detail = "results.json not found"
                """),
            },
            {
                "id": "C6",
                "description": "report.md recommends recalibration or retraining",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "report.md"
                    passed = False
                    detail = ""
                    terms = ["recalibrat", "retrain", "retrained", "refit",
                             "recalibrate", "re-train", "re-calibrat",
                             "update the model", "new model", "monitoring"]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in terms if t in content]
                        passed = len(found) > 0
                        detail = f"found recommendation terms: {found}"
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
                    p = pathlib.Path(workspace_dir) / "data" / "lending_club.csv"
                    passed = False
                    detail = ""
                    expected_rows = {n_rows}
                    if p.exists():
                        with open(p, newline="", encoding="utf-8") as fh:
                            actual = sum(1 for _ in csv.reader(fh)) - 1
                        passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.02))
                        detail = f"actual={{actual}}, expected={{expected_rows}}"
                    else:
                        detail = "data/lending_club.csv not found"
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
                    required = ["drift_factors", "primary_cause", "recommendation"]
                    if p.exists():
                        try:
                            d = json.loads(p.read_text(encoding="utf-8"))
                            missing = [f for f in required if f not in d]
                            passed = len(missing) == 0
                            detail = f"missing={missing}" if missing else "all required fields present"
                        except json.JSONDecodeError as e:
                            detail = f"JSON error: {e}"
                    else:
                        detail = "results.json not found"
                """),
            },
        ]
        return self.make_check_solution(checks)
