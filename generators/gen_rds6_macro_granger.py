"""
Parameterized generator for RDS6: Macroeconomic Granger Causality (Archetype 3 — Open-Ended).

Uses the FRED macroeconomic dataset. Three seed variants:
  Seed 0: Does unemployment Granger-cause inflation?
  Seed 1: Does the fed funds rate Granger-cause unemployment?
  Seed 2: Does GDP Granger-cause inflation?

Rubric checks (8):
  C1: analysis.py runs without error
  C2: Granger causality test or VAR model implemented
  C3: Test statistic and p-value reported in results.json
  C4: Key columns (UNRATE, CPIAUCSL, FEDFUNDS, GDP) referenced
  C5: Stationarity test (ADF or KPSS) present
  C6: Limitations discussed in report.md (spurious, non-stationary, etc.)
  C7: Data loaded correctly (row count check)
  C8: results.json is valid JSON with required fields
"""
from __future__ import annotations

import textwrap

from generators.base import GeneratedTask
from generators.real_data_base import OpenEndedGenerator

_VARIANTS = [
    {
        # Seed 0 — unemployment → inflation
        "cause_var": "UNRATE",
        "cause_label": "unemployment rate (UNRATE)",
        "effect_var": "CPIAUCSL",
        "effect_label": "inflation / CPI (CPIAUCSL)",
        "research_question": (
            "Does the unemployment rate Granger-cause the CPI inflation rate? "
            "Test whether past values of UNRATE improve forecasts of CPIAUCSL "
            "beyond what CPIAUCSL's own lags provide."
        ),
        "key_cols": ["UNRATE", "CPIAUCSL"],
        "hidden_col_keywords": ["UNRATE", "CPIAUCSL"],
        "context": (
            "The Phillips Curve posits a trade-off between unemployment and inflation. "
            "Granger causality tests whether past unemployment helps predict future "
            "inflation. Both series must be stationary (use first differences or "
            "percent changes if needed). Choose lag length via AIC/BIC. "
            "Report the F-statistic and p-value for the null hypothesis that "
            "UNRATE does NOT Granger-cause CPIAUCSL."
        ),
        "lag_hint": "Try lags 1-4; use AIC to select optimal lag length.",
    },
    {
        # Seed 1 — fed funds → unemployment
        "cause_var": "FEDFUNDS",
        "cause_label": "federal funds rate (FEDFUNDS)",
        "effect_var": "UNRATE",
        "effect_label": "unemployment rate (UNRATE)",
        "research_question": (
            "Does the federal funds rate Granger-cause the unemployment rate? "
            "Test whether past values of FEDFUNDS improve forecasts of UNRATE "
            "beyond what UNRATE's own lags provide."
        ),
        "key_cols": ["FEDFUNDS", "UNRATE"],
        "hidden_col_keywords": ["FEDFUNDS", "UNRATE"],
        "context": (
            "Monetary policy theory suggests that raising interest rates increases "
            "unemployment (via reduced investment and consumption). Granger causality "
            "tests the predictive relationship. Both series should be tested for "
            "stationarity. The fed funds rate shows long trends and may need differencing. "
            "Unemployment is persistent — consider using changes."
        ),
        "lag_hint": "Monetary policy transmission lags suggest testing lags 2-8 quarters.",
    },
    {
        # Seed 2 — GDP → inflation
        "cause_var": "GDP",
        "cause_label": "GDP level (GDP)",
        "effect_var": "CPIAUCSL",
        "effect_label": "inflation / CPI (CPIAUCSL)",
        "research_question": (
            "Does GDP growth Granger-cause CPI inflation? "
            "Test whether past GDP values improve forecasts of CPIAUCSL "
            "beyond what CPIAUCSL's own lags provide."
        ),
        "key_cols": ["GDP", "CPIAUCSL"],
        "hidden_col_keywords": ["GDP", "CPIAUCSL"],
        "context": (
            "Demand-pull inflation theory suggests that GDP growth (aggregate demand) "
            "drives up prices. However, GDP is quarterly while other series may be monthly "
            "— align frequencies carefully. Both series are non-stationary in levels; "
            "use percent changes (growth rates). "
            "Report whether the null of no Granger causality is rejected."
        ),
        "lag_hint": "GDP is quarterly — interpolate or aggregate other series to match frequency.",
    },
]

# All columns — small dataset, keep everything
_KEEP_COLUMNS = ["date", "UNRATE", "CPIAUCSL", "FEDFUNDS", "GDP"]


class Generator(OpenEndedGenerator):
    task_id = "RDS6_macro_granger"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]

    dataset_name = "fred_macro"
    dataset_license = "Public Domain (FRED)"
    dataset_source = "Federal Reserve Bank of St. Louis"

    def generate(self, seed: int) -> GeneratedTask:
        variant = _VARIANTS[seed % len(_VARIANTS)]

        # fred_macro is small (780 rows) — use all of it
        rows = self.load_dataset()
        n_rows = len(rows)
        data_csv = self.rows_to_csv(rows, _KEEP_COLUMNS)

        check_py = self._make_check_solution(variant, n_rows)
        requirements_txt = self.make_requirements_txt(
            packages=[
                "pandas>=1.5",
                "numpy>=1.23",
                "scipy>=1.9",
                "statsmodels>=0.13",
            ]
        )
        task_yaml = self.make_task_yaml()

        workspace_files = {
            "data/fred_macro.csv": data_csv,
            "requirements.txt": requirements_txt,
            "check_solution.py": check_py,
            "task.yaml": task_yaml,
        }

        expected = {
            "cause_var": variant["cause_var"],
            "effect_var": variant["effect_var"],
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
            # RDS6: Macroeconomic Granger Causality

            ## Research Question
            **{variant["research_question"]}**

            ## Dataset
            - File: `data/fred_macro.csv`
            - Rows: {n_rows} (monthly FRED macroeconomic time series)
            - Columns: `date`, `UNRATE` (unemployment %), `CPIAUCSL` (CPI index),
              `FEDFUNDS` (federal funds rate %), `GDP` (billions USD, quarterly)
            - Key columns for this analysis: {col_list}

            ## Background
            {variant["context"]}

            ## Lag Selection Hint
            {variant["lag_hint"]}

            ## Your Task
            Conduct a Granger causality analysis:

            1. **Stationarity**: Test each series with ADF or KPSS. Transform if needed
               (first differences, percent changes, or log-differences).
            2. **Lag selection**: Use AIC or BIC to choose the lag order.
            3. **Granger test**: Run the Granger causality F-test (or use VAR model).
               Report F-statistic and p-value for H₀: `{variant["cause_var"]}` does NOT
               Granger-cause `{variant["effect_var"]}`.
            4. **Reverse test**: Also test the reverse direction for comparison.
            5. **Interpretation**: Discuss whether the result supports the economic theory.

            ## Required Deliverables

            ### 1. `analysis.py`
            A Python script that:
            - Loads `data/fred_macro.csv`
            - Handles stationarity (ADF test + transformation)
            - Runs Granger causality test
            - Saves `results.json` and `report.md`

            ### 2. `results.json`
            Must contain at minimum:
            ```json
            {{
              "cause_var": "{variant["cause_var"]}",
              "effect_var": "{variant["effect_var"]}",
              "granger_f_stat": <float>,
              "granger_p_value": <float>,
              "lag_order": <int>,
              "reject_null": <bool>
            }}
            ```

            ### 3. `report.md`
            A brief (300–600 word) report covering:
            - Stationarity tests and transformations applied
            - Granger test result (F-stat, p-value, lag order)
            - Economic interpretation
            - **Limitations** (spurious regression, non-causation, structural breaks, etc.)

            ## Grading Criteria
            1. `analysis.py` runs without error
            2. Granger causality test or VAR model implemented
            3. F-statistic and p-value reported in `results.json`
            4. Key columns ({col_list}) referenced in analysis code
            5. Stationarity test (ADF or KPSS) present
            6. `report.md` discusses limitations
            7. Data loaded correctly (correct row count)
            8. `results.json` contains required fields and is valid JSON
        """)

    def _make_brief(self, variant: dict) -> str:
        return textwrap.dedent(f"""\
            # RDS6: Macroeconomic Granger Causality (Brief)

            Analyze the FRED macroeconomic dataset to test Granger causality.

            **Dataset**: `data/fred_macro.csv`

            **Question**: {variant["research_question"]}

            Produce:
            - `analysis.py` — Granger causality analysis script
            - `results.json` — test statistics and result
            - `report.md` — findings and limitations
        """)

    def _make_check_solution(self, variant: dict, n_rows: int) -> str:
        hidden_kw = variant["hidden_col_keywords"]
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
                "description": "Granger causality test or VAR model implemented in analysis.py",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    granger_terms = [
                        "granger", "grangercausality", "var", "vector autoregress",
                        "f_stat", "f-stat", "causality", "forecast", "lag",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in granger_terms if t in content]
                        passed = len(found) >= 2
                        detail = f"found granger terms: {found}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C3",
                "description": "granger_f_stat and granger_p_value present in results.json",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    if p.exists():
                        try:
                            d = json.loads(p.read_text())
                            has_f = "granger_f_stat" in d or "f_stat" in d or "p_value" in d
                            has_p = "granger_p_value" in d or "p_value" in d
                            passed = has_f and has_p
                            detail = f"f_stat present={has_f}, p_value present={has_p}"
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
                "description": "Stationarity test (ADF or KPSS) present in analysis.py",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    stationary_terms = [
                        "adf", "adfuller", "kpss", "stationar", "unit root",
                        "diff", "pct_change", "first difference",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in stationary_terms if t in content]
                        passed = len(found) >= 1
                        detail = f"found stationarity terms: {found}"
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
                    caveat_terms = ["limitation", "caveat", "spurious", "causal",
                                    "assumption", "bias", "confound", "correlation"]
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
                "description": "results.json is valid JSON with required fields",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    required_fields = ["cause_var", "effect_var", "reject_null"]
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
