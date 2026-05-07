"""
Generator for RDS28: Life Expectancy Drop Investigation (Archetype 2 — Synthesis).

Dataset: who_gho (country, year, life_expectancy, infant_mortality, physicians_per_1000, ...)

Task: Investigate why life expectancy dropped significantly in specific countries
over a particular period. Requires synthesizing evidence from policy, conflict,
and trade data.

Corpus documents:
  - policy_timeline.md  : Healthcare policy changes (defunding, structural changes)
  - conflict_data.csv   : Armed conflict events with displacement and casualty data
  - trade_sanctions.csv : Economic sanctions imposed and their healthcare import impacts

Synthesis: Sanctions + conflict + healthcare defunding = compounding causes of
life expectancy drop. No single source tells the full story.

Rubric (8 checks):
  C1 — analysis.py runs without error
  C2 — Healthcare policy / defunding factor identified
  C3 — Conflict / displacement factor identified
  C4 — Sanctions / economic factor identified
  C5 — results.json has contributing_factors key with >= 2 entries
  C6 — report.md identifies a timeline showing factor sequence
  C7 — Data loaded correctly
  C8 — results.json valid JSON with required fields
"""
from __future__ import annotations

import textwrap

from generators.base import GeneratedTask
from generators.real_data_base import SynthesisGenerator
from generators.primitives import SeededRandom


_VARIANTS = [
    {
        "seed": 0,
        "affected_countries": ["SYR", "YEM", "AFG"],
        "affected_names": ["Syria", "Yemen", "Afghanistan"],
        "drop_period": "2012–2017",
        "drop_start_year": 2012,
        "drop_end_year": 2017,
        "life_exp_drop_yrs": 4.2,
        "conflict_type": "civil war and armed conflict",
        "policy_change": "dissolution of primary healthcare network, closure of 60% of hospitals",
        "sanction_imposer": "UN Security Council and EU",
        "sanction_target": "medical equipment imports restricted due to dual-use classification",
    },
    {
        "seed": 1,
        "affected_countries": ["VEN", "ZWE", "SSD"],
        "affected_names": ["Venezuela", "Zimbabwe", "South Sudan"],
        "drop_period": "2015–2020",
        "drop_start_year": 2015,
        "drop_end_year": 2020,
        "life_exp_drop_yrs": 3.1,
        "conflict_type": "political instability and armed conflict",
        "policy_change": "healthcare budget cut by 55%, suspension of vaccination programs",
        "sanction_imposer": "United States and EU",
        "sanction_target": "financial sector sanctions limiting import financing for pharmaceuticals",
    },
    {
        "seed": 2,
        "affected_countries": ["HTI", "MLI", "CAF"],
        "affected_names": ["Haiti", "Mali", "Central African Republic"],
        "drop_period": "2010–2016",
        "drop_start_year": 2010,
        "drop_end_year": 2016,
        "life_exp_drop_yrs": 2.8,
        "conflict_type": "natural disaster compounded by armed insurgency",
        "policy_change": "international aid withdrawal following governance disputes, NGO expulsions",
        "sanction_imposer": "Regional economic bodies (ECOWAS)",
        "sanction_target": "trade restrictions limiting medical supply chain access",
    },
]

_KEEP_COLUMNS = [
    "country", "country_code", "year", "life_expectancy",
    "infant_mortality", "under5_mortality", "maternal_mortality",
    "hiv_prevalence", "physicians_per_1000", "hospital_beds_per_1000",
    "health_expenditure_pct_gdp", "income_group", "region",
]


class Generator(SynthesisGenerator):
    task_id = "RDS28_health_crisis"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]

    dataset_name = "who_gho"
    dataset_license = "CC-BY 4.0"
    dataset_source = "WHO Global Health Observatory"

    def generate(self, seed: int) -> GeneratedTask:
        v = _VARIANTS[seed % len(_VARIANTS)]
        rng = SeededRandom(seed + 280)

        rows = self.load_dataset()
        # Use all rows — WHO dataset is small (264 rows)
        rows = self.select_columns(rows, _KEEP_COLUMNS)
        n_rows = len(rows)
        data_csv = self.rows_to_csv(rows, _KEEP_COLUMNS)

        corpus = {
            "policy_timeline.md": self._gen_policy_md(v),
            "conflict_data.csv": self._gen_conflict_csv(v, rng),
            "trade_sanctions.csv": self._gen_sanctions_csv(v, rng),
        }

        requirements_txt = "pandas>=1.5\nnumpy>=1.23\nscipy>=1.9\n"
        task_yaml = self.make_task_yaml()
        check_py = self._make_check_solution(v, n_rows)

        workspace_files = {
            "data/who_gho.csv": data_csv,
            "requirements.txt": requirements_txt,
            "check_solution.py": check_py,
            "task.yaml": task_yaml,
        }

        expected = {
            "affected_countries": v["affected_countries"],
            "contributing_factors": ["healthcare_policy", "armed_conflict", "economic_sanctions"],
            "drop_period": v["drop_period"],
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

    def _gen_policy_md(self, v: dict) -> str:
        names_str = ", ".join(v["affected_names"])
        return textwrap.dedent(f"""\
            # Healthcare Policy Timeline — {names_str}
            **Compiled by**: Global Health Policy Monitor
            **Period**: {v['drop_period']}
            **Reference**: GHPM-{v['drop_start_year']}-POLICY

            ## Key Policy Events

            ### {v['drop_start_year']} — Initial Deterioration
            - Government healthcare budget reduced by 30–40% following fiscal crisis
            - Primary healthcare network restructuring begins; rural clinics consolidated
            - International NGO operations restricted in several provinces

            ### {v['drop_start_year'] + 1}–{v['drop_start_year'] + 2} — Accelerating Decline
            - {v['policy_change'].capitalize()}
            - Maternal health programs suspended in conflict-affected regions
            - Medical professional emigration accelerates — estimated 35% of physicians
              departed by end of period
            - WHO vaccination coverage falls below 50% in affected areas

            ### {v['drop_start_year'] + 3}–{v['drop_end_year']} — Crisis Period
            - Remaining healthcare infrastructure operating at 20–30% capacity
            - Preventable disease mortality increases 2–4x above pre-crisis baseline
            - Malnutrition-related deaths rise significantly, particularly in children under 5

            ## Distractor: Regional Comparative Data

            Note: Neighboring countries with similar income levels but stable governance
            showed continued improvement in life expectancy over the same period,
            suggesting the decline is policy/conflict-driven rather than structural
            or demographic.

            ---
            *Global Health Policy Monitor — Research Division*
        """)

    def _gen_conflict_csv(self, v: dict, rng: SeededRandom) -> str:
        lines = ["year,country_code,conflict_type,fatalities_est,displaced_persons_thousands,infrastructure_damage_pct"]
        for yr in range(v["drop_start_year"] - 2, v["drop_end_year"] + 2):
            for cc in v["affected_countries"]:
                is_crisis = v["drop_start_year"] <= yr <= v["drop_end_year"]
                if is_crisis:
                    fat = round(rng.uniform(800, 8000))
                    disp = round(rng.uniform(50, 500))
                    damage = round(rng.uniform(20, 65))
                    ctype = v["conflict_type"]
                else:
                    fat = round(rng.uniform(10, 200))
                    disp = round(rng.uniform(2, 20))
                    damage = round(rng.uniform(1, 8))
                    ctype = "low-level unrest"
                lines.append(f"{yr},{cc},{ctype},{fat},{disp},{damage}")
        # Add distractor rows for stable neighboring countries
        for yr in range(v["drop_start_year"], v["drop_end_year"] + 1):
            for cc in ["KEN", "GHA", "TUN"]:
                lines.append(f"{yr},{cc},stable,{round(rng.uniform(0,50))},{round(rng.uniform(0,5))},{round(rng.uniform(0,3))}")
        return "\n".join(lines) + "\n"

    def _gen_sanctions_csv(self, v: dict, rng: SeededRandom) -> str:
        lines = ["year,country_code,imposing_body,sanction_type,healthcare_import_impact,gdp_impact_pct"]
        for yr in range(v["drop_start_year"] - 1, v["drop_end_year"] + 2):
            for cc in v["affected_countries"]:
                is_sanctions = v["drop_start_year"] <= yr <= v["drop_end_year"]
                if is_sanctions:
                    impact = round(rng.uniform(25, 60))
                    gdp = round(rng.uniform(3, 12), 1)
                    stype = v["sanction_target"]
                    imposer = v["sanction_imposer"]
                else:
                    impact = round(rng.uniform(0, 5))
                    gdp = round(rng.uniform(0, 1), 1)
                    stype = "none"
                    imposer = "none"
                lines.append(f"{yr},{cc},{imposer},{stype},{impact},{gdp}")
        # Distractor: sanctions on unrelated countries
        for cc in ["IRN", "CUB"]:
            for yr in range(v["drop_start_year"], v["drop_end_year"] + 1):
                lines.append(f"{yr},{cc},US Treasury,financial sector,{round(rng.uniform(15,40))},{round(rng.uniform(1,5), 1)}")
        return "\n".join(lines) + "\n"

    # ── Spec / brief ──────────────────────────────────────────────────────────

    def _make_spec(self, v: dict, n_rows: int) -> str:
        names_str = ", ".join(v["affected_names"])
        codes_str = ", ".join(v["affected_countries"])
        return textwrap.dedent(f"""\
            # RDS28: Life Expectancy Drop Investigation

            ## Background

            WHO Global Health Observatory data shows that life expectancy in
            **{names_str}** ({codes_str}) dropped by approximately {v['life_exp_drop_yrs']} years
            during the period **{v['drop_period']}** — a decline not observed in
            comparable countries over the same timeframe.

            Your task is to investigate the root causes by synthesizing the WHO data
            with three external evidence sources.

            ## Dataset

            - File: `data/who_gho.csv`
            - Rows: {n_rows}
            - Key columns: `country`, `country_code`, `year`, `life_expectancy`,
              `infant_mortality`, `physicians_per_1000`, `health_expenditure_pct_gdp`,
              `income_group`, `region`

            ## Corpus Documents

            Reference documents in `corpus/`:

            | File | Description |
            |------|-------------|
            | `policy_timeline.md` | Healthcare policy changes timeline |
            | `conflict_data.csv` | Armed conflict events with displacement data |
            | `trade_sanctions.csv` | Economic sanctions and healthcare import impacts |

            **Each document provides partial evidence.** You must connect the timeline
            across all three to explain the magnitude of the life expectancy drop.

            ## Required Deliverables

            ### 1. `analysis.py`
            - Load WHO data and quantify the life expectancy drop for affected countries
            - Compare against a control group of similar-income, stable countries
            - Read and analyze all three corpus documents
            - Correlate each factor's timing with the observed mortality trends

            ### 2. `results.json`
            ```json
            {{
              "affected_countries": ["<code1>", ...],
              "life_exp_drop_years": <float>,
              "contributing_factors": ["<factor1>", "<factor2>", "<factor3>"],
              "primary_factor": "<string>",
              "counterfactual_comparison": "<description>"
            }}
            ```

            ### 3. `report.md`
            400–700 words covering:
            - Magnitude of decline vs comparable countries (counterfactual)
            - Role of each factor with timeline evidence
            - How the factors compound each other (interaction effects)
            - Recommended policy interventions to reverse the trend

            ## Grading Criteria
            1. `analysis.py` runs without error
            2. Healthcare policy / defunding factor identified
            3. Conflict / displacement factor identified
            4. Sanctions / economic factor identified
            5. `results.json` has `contributing_factors` with ≥ 2 entries
            6. `report.md` establishes a causal timeline connecting factors
            7. Data loaded correctly
            8. `results.json` valid JSON with required fields
        """)

    def _make_brief(self, v: dict) -> str:
        names_str = ", ".join(v["affected_names"])
        return textwrap.dedent(f"""\
            # RDS28: Life Expectancy Drop Investigation (Brief)

            WHO data shows a significant life expectancy decline in {names_str}
            during {v['drop_period']}. Investigate the root causes using the WHO
            dataset and three corpus documents.

            **Dataset**: `data/who_gho.csv`

            **Corpus docs** (in `corpus/`):
            - `policy_timeline.md`
            - `conflict_data.csv`
            - `trade_sanctions.csv`

            Produce:
            - `analysis.py` — investigation script
            - `results.json` — contributing factors
            - `report.md` — causal narrative and policy recommendations
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
                "description": "Healthcare policy / defunding factor identified",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    passed = False
                    detail = ""
                    terms = ["policy", "healthcare", "hospital", "defund", "budget cut",
                             "health expenditure", "physicians", "health system",
                             "health_expenditure", "medical", "clinic"]
                    for fname in ["analysis.py", "report.md"]:
                        p = pathlib.Path(workspace_dir) / fname
                        if p.exists():
                            content = p.read_text(encoding="utf-8").lower()
                            found = [t for t in terms if t in content]
                            if len(found) >= 2:
                                passed = True
                                detail = f"found in {fname}: {found}"
                                break
                    if not passed:
                        detail = "healthcare policy terms not found"
                """),
            },
            {
                "id": "C3",
                "description": "Conflict / displacement factor identified",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    passed = False
                    detail = ""
                    terms = ["conflict", "war", "armed", "displacement", "refugee",
                             "fatalities", "instability", "insurgency", "civil war",
                             "displaced", "violence"]
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
                        detail = "conflict terms not found"
                """),
            },
            {
                "id": "C4",
                "description": "Sanctions / economic factor identified",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    passed = False
                    detail = ""
                    terms = ["sanction", "embargo", "trade restriction", "economic",
                             "import", "financial", "gdp", "restriction", "trade_sanction",
                             "trade sanctions"]
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
                        detail = "sanctions/economic terms not found"
                """),
            },
            {
                "id": "C5",
                "description": "results.json has contributing_factors with >= 2 entries",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    if p.exists():
                        try:
                            d = json.loads(p.read_text(encoding="utf-8"))
                            factors = d.get("contributing_factors", [])
                            passed = isinstance(factors, list) and len(factors) >= 2
                            detail = f"contributing_factors={factors}"
                        except Exception as e:
                            detail = str(e)
                    else:
                        detail = "results.json not found"
                """),
            },
            {
                "id": "C6",
                "description": "report.md identifies a causal timeline connecting factors",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "report.md"
                    passed = False
                    detail = ""
                    timeline_terms = ["timeline", "sequence", "following", "led to",
                                      "resulted in", "caused by", "compound",
                                      "exacerbat", "first", "then", "subsequently",
                                      "period", "between"]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in timeline_terms if t in content]
                        passed = len(found) >= 3
                        detail = f"found timeline terms: {found}"
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
                        passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.05))
                        detail = f"actual={{actual}}, expected={{expected_rows}}"
                    else:
                        detail = "data/who_gho.csv not found"
                """),
            },
            {
                "id": "C8",
                "description": "results.json valid JSON with required fields",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    required = ["contributing_factors", "primary_factor", "life_exp_drop_years"]
                    if p.exists():
                        try:
                            d = json.loads(p.read_text(encoding="utf-8"))
                            missing = [f for f in required if f not in d]
                            passed = len(missing) == 0
                            detail = f"missing={missing}" if missing else "all fields present"
                        except json.JSONDecodeError as e:
                            detail = f"JSON error: {e}"
                    else:
                        detail = "results.json not found"
                """),
            },
        ]
        return self.make_check_solution(checks)
