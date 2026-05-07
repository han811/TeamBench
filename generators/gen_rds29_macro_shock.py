"""
Generator for RDS29: Macroeconomic Inflation Shock Investigation (Archetype 2 — Synthesis).

Dataset: fred_macro (date, UNRATE, CPIAUCSL, FEDFUNDS, GDP)

Task: Explain an inflation spike in a specific period. Requires distinguishing
supply-side from demand-side drivers using corpus documents.

Corpus documents:
  - fed_minutes.md   : Fed meeting summaries showing demand-side analysis
  - oil_prices.csv   : Oil price data showing supply shock
  - trade_balance.csv: Import cost data showing rising import prices

Synthesis: Supply-side shock (oil + import costs) not demand (Fed minutes confirm
demand was not the primary driver). The key insight is that the Fed minutes explicitly
note demand conditions were not exceptional — pointing to supply-side explanation.

Rubric (8 checks):
  C1 — analysis.py runs without error
  C2 — Supply-side cause identified (oil or import costs)
  C3 — Demand-side ruled out using Fed minutes evidence
  C4 — Oil price shock specifically mentioned
  C5 — results.json has inflation_drivers key with supply vs demand classification
  C6 — report.md cites Fed minutes as evidence against demand explanation
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
        "shock_period": "2021-Q3 to 2022-Q2",
        "shock_start": "2021-07",
        "shock_end": "2022-06",
        "cpi_spike_pct": 8.5,
        "oil_price_start": 68.0,
        "oil_price_peak": 114.0,
        "oil_shock_event": "OPEC+ production restraint combined with post-pandemic demand recovery",
        "import_cost_increase_pct": 22.0,
        "fed_assessment": "committee noted that demand conditions, while recovering, remained below pre-pandemic trend; labor market slack persisted in services sectors",
        "fed_action": "maintained accommodative stance with forward guidance; first rate hike deferred",
    },
    {
        "seed": 1,
        "shock_period": "2007-Q4 to 2008-Q3",
        "shock_start": "2007-10",
        "shock_end": "2008-09",
        "cpi_spike_pct": 5.6,
        "oil_price_start": 70.0,
        "oil_price_peak": 145.0,
        "oil_shock_event": "geopolitical tensions in Middle East and speculative demand pressure on futures markets",
        "import_cost_increase_pct": 18.0,
        "fed_assessment": "committee observed that consumer spending had weakened materially; housing market contraction reducing aggregate demand; financial conditions tightening",
        "fed_action": "eased policy rate aggressively to support growth; primary concern was recession risk, not overheating",
    },
    {
        "seed": 2,
        "shock_period": "2010-Q3 to 2011-Q2",
        "shock_start": "2010-07",
        "shock_end": "2011-06",
        "cpi_spike_pct": 3.9,
        "oil_price_start": 72.0,
        "oil_price_peak": 113.0,
        "oil_shock_event": "Arab Spring disruptions to North African and Middle Eastern oil supply",
        "import_cost_increase_pct": 14.5,
        "fed_assessment": "unemployment remained elevated at 9.1%; wage growth subdued; core inflation ex-energy remained contained; output gap estimated at -5%",
        "fed_action": "continued QE2 program; committee judged that underlying inflation trend remained well-anchored despite headline CPI acceleration",
    },
]

_KEEP_COLUMNS = ["date", "UNRATE", "CPIAUCSL", "FEDFUNDS", "GDP"]


class Generator(SynthesisGenerator):
    task_id = "RDS29_macro_shock"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]

    dataset_name = "fred_macro"
    dataset_license = "Public Domain"
    dataset_source = "FRED / St. Louis Fed"

    def generate(self, seed: int) -> GeneratedTask:
        v = _VARIANTS[seed % len(_VARIANTS)]
        rng = SeededRandom(seed + 290)

        rows = self.load_dataset()
        rows = self.select_columns(rows, _KEEP_COLUMNS)
        n_rows = len(rows)
        data_csv = self.rows_to_csv(rows, _KEEP_COLUMNS)

        corpus = {
            "fed_minutes.md": self._gen_fed_minutes_md(v),
            "oil_prices.csv": self._gen_oil_prices_csv(v, rng),
            "trade_balance.csv": self._gen_trade_balance_csv(v, rng),
        }

        requirements_txt = "pandas>=1.5\nnumpy>=1.23\nscipy>=1.9\n"
        task_yaml = self.make_task_yaml()
        check_py = self._make_check_solution(v, n_rows)

        workspace_files = {
            "data/fred_macro.csv": data_csv,
            "requirements.txt": requirements_txt,
            "check_solution.py": check_py,
            "task.yaml": task_yaml,
        }

        expected = {
            "shock_period": v["shock_period"],
            "inflation_drivers": {"supply_side": True, "demand_side": False},
            "primary_driver": "oil_price_shock",
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

    def _gen_fed_minutes_md(self, v: dict) -> str:
        return textwrap.dedent(f"""\
            # Federal Open Market Committee — Meeting Minutes (Excerpts)
            **Period**: {v['shock_period']}
            **Classification**: Public (released with standard 3-week lag)

            ## Staff Economic Outlook

            The staff presented projections indicating that headline CPI had
            accelerated to {v['cpi_spike_pct']:.1f}% year-over-year, primarily
            driven by energy and import prices.

            ## Committee Discussion — Inflation Assessment

            Members discussed at length whether the inflation acceleration
            reflected demand-side pressures or supply-side cost-push factors.

            **Key passage from discussion record:**

            > "{v['fed_assessment'].capitalize()}. Members agreed that the current
            > inflation reading did not reflect broad-based demand overheating but
            > rather a concentrated supply disruption being transmitted through
            > energy and goods prices."

            ## Committee Action

            {v['fed_action'].capitalize()}.

            ## Energy Price Discussion

            Several members cited {v['oil_shock_event']} as the proximate cause
            of the energy price acceleration. The transmission mechanism through
            transportation costs and production inputs was identified as amplifying
            the pass-through to core goods prices.

            Staff noted that import price indices had risen sharply, consistent
            with a cost-push rather than demand-pull inflation dynamic.

            ## Distractor: Housing Market Discussion

            The committee also discussed residential investment trends. While
            housing starts had shown some recovery, members noted that this was
            unlikely to contribute materially to near-term inflation given
            long construction lags. This discussion was not considered directly
            relevant to the current inflation episode.

            ---
            *Federal Reserve — Public Record*
        """)

    def _gen_oil_prices_csv(self, v: dict, rng: SeededRandom) -> str:
        lines = ["date,wti_crude_usd_bbl,brent_crude_usd_bbl,gasoline_retail_usd_gal"]
        shock_start_yr = int(v["shock_start"][:4])
        shock_start_mo = int(v["shock_start"][5:7])
        shock_end_yr = int(v["shock_end"][:4])
        shock_end_mo = int(v["shock_end"][5:7])

        # Generate 5 years of monthly data around the shock
        for yr in range(shock_start_yr - 2, shock_end_yr + 2):
            for mo in range(1, 13):
                date_str = f"{yr}-{mo:02d}-01"
                in_shock = (
                    (yr > shock_start_yr) or (yr == shock_start_yr and mo >= shock_start_mo)
                ) and (
                    (yr < shock_end_yr) or (yr == shock_end_yr and mo <= shock_end_mo)
                )
                if in_shock:
                    # Ramp up then plateau
                    progress = min(1.0, (yr - shock_start_yr) * 12 + (mo - shock_start_mo)) / 8
                    wti = round(v["oil_price_start"] + (v["oil_price_peak"] - v["oil_price_start"]) * progress + rng.uniform(-3, 3), 2)
                else:
                    wti = round(v["oil_price_start"] + rng.uniform(-8, 8), 2)
                brent = round(wti + rng.uniform(1.5, 4.5), 2)
                gas = round(wti * 0.025 + rng.uniform(0.1, 0.3), 2)
                lines.append(f"{date_str},{wti},{brent},{gas}")

        return "\n".join(lines) + "\n"

    def _gen_trade_balance_csv(self, v: dict, rng: SeededRandom) -> str:
        lines = ["date,imports_bn_usd,exports_bn_usd,trade_balance_bn_usd,import_price_index,energy_import_share_pct"]
        shock_start_yr = int(v["shock_start"][:4])
        shock_start_mo = int(v["shock_start"][5:7])
        shock_end_yr = int(v["shock_end"][:4])
        shock_end_mo = int(v["shock_end"][5:7])

        for yr in range(shock_start_yr - 2, shock_end_yr + 2):
            for mo in range(1, 13):
                date_str = f"{yr}-{mo:02d}-01"
                in_shock = (
                    (yr > shock_start_yr) or (yr == shock_start_yr and mo >= shock_start_mo)
                ) and (
                    (yr < shock_end_yr) or (yr == shock_end_yr and mo <= shock_end_mo)
                )
                imports = round(200 + rng.uniform(-10, 10), 1)
                exports = round(180 + rng.uniform(-8, 8), 1)
                if in_shock:
                    import_idx = round(100 + v["import_cost_increase_pct"] * rng.uniform(0.6, 1.0), 1)
                    energy_share = round(rng.uniform(18, 28), 1)
                else:
                    import_idx = round(100 + rng.uniform(-2, 4), 1)
                    energy_share = round(rng.uniform(10, 14), 1)
                balance = round(exports - imports, 1)
                lines.append(f"{date_str},{imports},{exports},{balance},{import_idx},{energy_share}")

        return "\n".join(lines) + "\n"

    # ── Spec / brief ──────────────────────────────────────────────────────────

    def _make_spec(self, v: dict, n_rows: int) -> str:
        return textwrap.dedent(f"""\
            # RDS29: Macroeconomic Inflation Shock Analysis

            ## Background

            FRED macroeconomic data shows headline CPI (CPIAUCSL) spiked to
            approximately **{v['cpi_spike_pct']:.1f}% year-over-year** during
            **{v['shock_period']}**. Economists debate whether this reflects
            demand-side overheating or supply-side cost-push forces.

            Your task is to determine the primary driver — supply vs. demand —
            by synthesizing the FRED data with three corpus documents.

            ## Dataset

            - File: `data/fred_macro.csv`
            - Rows: {n_rows} (monthly observations)
            - Columns: `date`, `UNRATE` (unemployment rate, %), `CPIAUCSL` (CPI index),
              `FEDFUNDS` (federal funds rate, %), `GDP` (billions, quarterly)

            ## Corpus Documents

            Reference documents in `corpus/`:

            | File | Description |
            |------|-------------|
            | `fed_minutes.md` | FOMC meeting minutes excerpts for the shock period |
            | `oil_prices.csv` | Monthly WTI/Brent crude and retail gasoline prices |
            | `trade_balance.csv` | Monthly import/export data with import price index |

            **The Fed minutes are critical**: they contain the committee's explicit
            assessment of whether demand or supply was driving inflation. Use them
            as primary qualitative evidence, cross-checked against the quantitative
            oil and trade data.

            ## Required Deliverables

            ### 1. `analysis.py`
            - Load FRED data and compute YoY CPI change to identify the shock period
            - Read and synthesize all three corpus documents
            - Test the demand hypothesis (UNRATE, GDP growth) and supply hypothesis
              (oil prices, import costs)
            - Draw a conclusion about the primary inflation driver

            ### 2. `results.json`
            ```json
            {{
              "shock_period": "<period>",
              "cpi_peak_yoy": <float>,
              "inflation_drivers": {{
                "supply_side": <bool>,
                "demand_side": <bool>
              }},
              "primary_driver": "<string>",
              "evidence_sources": ["<source1>", "<source2>"]
            }}
            ```

            ### 3. `report.md`
            400–700 words covering:
            - CPI spike magnitude and timing
            - Evidence FOR supply-side (oil prices, import costs)
            - Evidence AGAINST demand-side (Fed minutes assessment, unemployment/GDP)
            - Policy implications and Fed's response rationale

            ## Grading Criteria
            1. `analysis.py` runs without error
            2. Supply-side cause identified (oil prices or import costs)
            3. Demand-side explanation evaluated and ruled out using Fed minutes
            4. Oil price shock specifically cited as a factor
            5. `results.json` has `inflation_drivers` with supply vs demand classification
            6. `report.md` cites Fed minutes as evidence against demand explanation
            7. Data loaded correctly
            8. `results.json` valid JSON with required fields
        """)

    def _make_brief(self, v: dict) -> str:
        return textwrap.dedent(f"""\
            # RDS29: Macroeconomic Inflation Shock Analysis (Brief)

            FRED data shows a CPI spike during {v['shock_period']}. Determine
            whether the primary driver was supply-side or demand-side using the
            macro dataset and three corpus documents.

            **Dataset**: `data/fred_macro.csv`

            **Corpus docs** (in `corpus/`):
            - `fed_minutes.md`
            - `oil_prices.csv`
            - `trade_balance.csv`

            Produce:
            - `analysis.py` — investigation script
            - `results.json` — supply vs demand classification with evidence
            - `report.md` — narrative analysis and policy context
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
                "description": "Supply-side cause identified (oil or import costs)",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    passed = False
                    detail = ""
                    terms = ["supply", "oil", "import cost", "cost-push", "cost push",
                             "energy price", "supply shock", "supply-side",
                             "import price", "production cost", "commodity"]
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
                        detail = "supply-side terms not found"
                """),
            },
            {
                "id": "C3",
                "description": "Demand-side evaluated and ruled out using Fed minutes",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    passed = False
                    detail = ""
                    # Must reference demand AND show it was not primary (ruling out)
                    demand_terms = ["demand", "fomc", "fed minutes", "committee",
                                    "unemployment", "aggregate demand", "overheating"]
                    ruling_out_terms = ["not demand", "supply driven", "supply-driven",
                                        "demand was not", "not the primary", "ruled out",
                                        "cost push", "cost-push", "supply shock"]
                    for fname in ["analysis.py", "report.md"]:
                        p = pathlib.Path(workspace_dir) / fname
                        if p.exists():
                            content = p.read_text(encoding="utf-8").lower()
                            has_demand = any(t in content for t in demand_terms)
                            has_ruling = any(t in content for t in ruling_out_terms)
                            if has_demand and has_ruling:
                                passed = True
                                detail = f"demand referenced and ruled out in {fname}"
                                break
                    if not passed:
                        detail = "demand ruling-out not found in analysis or report"
                """),
            },
            {
                "id": "C4",
                "description": "Oil price shock specifically cited",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    passed = False
                    detail = ""
                    terms = ["oil", "crude", "wti", "brent", "petroleum",
                             "energy price", "oil price", "oil_price", "opec"]
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
                        detail = "oil price terms not found"
                """),
            },
            {
                "id": "C5",
                "description": "results.json has inflation_drivers key with supply/demand classification",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    if p.exists():
                        try:
                            d = json.loads(p.read_text(encoding="utf-8"))
                            drivers = d.get("inflation_drivers", {})
                            has_supply = "supply_side" in drivers or "supply" in str(d).lower()
                            has_demand = "demand_side" in drivers or "demand" in str(d).lower()
                            passed = has_supply and has_demand
                            detail = f"inflation_drivers={drivers}"
                        except Exception as e:
                            detail = str(e)
                    else:
                        detail = "results.json not found"
                """),
            },
            {
                "id": "C6",
                "description": "report.md cites Fed minutes as evidence against demand explanation",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "report.md"
                    passed = False
                    detail = ""
                    fed_terms = ["fed minutes", "fomc", "committee", "federal reserve",
                                 "meeting minutes", "fed_minutes", "central bank"]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in fed_terms if t in content]
                        passed = len(found) > 0
                        detail = f"found Fed references: {found}"
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
                    p = pathlib.Path(workspace_dir) / "data" / "fred_macro.csv"
                    passed = False
                    detail = ""
                    expected_rows = {n_rows}
                    if p.exists():
                        with open(p, newline="", encoding="utf-8") as fh:
                            actual = sum(1 for _ in csv.reader(fh)) - 1
                        passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.02))
                        detail = f"actual={{actual}}, expected={{expected_rows}}"
                    else:
                        detail = "data/fred_macro.csv not found"
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
                    required = ["shock_period", "inflation_drivers", "primary_driver"]
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
