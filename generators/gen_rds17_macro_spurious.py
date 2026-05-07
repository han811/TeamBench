"""
Generator for RDS17: Spurious Regression on Non-Stationary Macro Time Series.

Archetype 4 — Adversarial Workspace.

The workspace contains a COMPLETE, RUNNING analysis that regresses two
non-stationary macro time series (both trending upward), reports r²=0.95,
and concludes a strong relationship. This is a classic spurious regression.

Three seed variants using fred_macro dataset:

  Seed 0: Regresses GDP on CPI. Both trend upward. r²≈0.95 (spurious).
          Fix: first-difference both series. r² drops to ~0.1-0.2.

  Seed 1: Regresses unemployment on federal funds rate. Both non-stationary.
          Fix: first-difference. r² drops dramatically.

  Seed 2: Regresses M2 money supply on GDP. Both trend upward.
          Fix: first-difference or log-difference. r² drops.

The spec tells the agent exactly what the flaw is and how to fix it.
The brief is vague: "Review and validate the existing analysis."

Rubric (6 checks):
  C1 — Stationarity test or differencing applied in analysis.py
  C2 — results.json exists with 'r2' key
  C3 — r2 in results.json <= 0.5 (spurious relationship removed)
  C4 — results.json contains 'method' key indicating differencing/stationarity
  C5 — report.md mentions spurious / non-stationary / differencing / unit root
  C6 — analysis.py runs without error
"""
from __future__ import annotations

import textwrap

from generators.base import GeneratedTask
from generators.real_data_base import AdversarialWorkspaceGenerator

_VARIANTS = [
    {
        "seed": 0,
        "y_col": "GDP",
        "x_col": "CPI",
        "y_label": "GDP",
        "x_label": "CPI (Consumer Price Index)",
        "spurious_r2": 0.95,
        "expected_r2_max": 0.5,
        "bias_description": (
            "Both GDP and CPI exhibit strong upward trends over time (non-stationarity). "
            "Regressing one non-stationary series on another produces a high R² purely "
            "because both series share a common time trend — not because of any genuine "
            "causal or equilibrium relationship. The R²≈0.95 reflects shared trend, "
            "not economic signal."
        ),
        "fix_description": (
            "Apply first-differencing to both series: `diff_y = y.diff().dropna()` and "
            "`diff_x = x.diff().dropna()`. Regress the differenced series on each other. "
            "Alternatively, test for stationarity (ADF test) and cointegration before "
            "running a levels regression. After differencing, R² should drop to ~0.1-0.2."
        ),
        "adf_context": "GDP and CPI both fail the ADF stationarity test (p >> 0.05).",
    },
    {
        "seed": 1,
        "y_col": "UNRATE",
        "x_col": "FEDFUNDS",
        "y_label": "Unemployment Rate",
        "x_label": "Federal Funds Rate",
        "spurious_r2": 0.87,
        "expected_r2_max": 0.5,
        "bias_description": (
            "Both the unemployment rate and the federal funds rate exhibit persistent "
            "trends and structural breaks over the sample period. Regressing unemployment "
            "on the fed funds rate without accounting for non-stationarity produces a "
            "spurious correlation driven by shared low-frequency movements, not any "
            "direct policy transmission mechanism."
        ),
        "fix_description": (
            "Apply first-differencing to both series before regression: "
            "`diff_y = y.diff().dropna()` and `diff_x = x.diff().dropna()`. "
            "Optionally run an ADF test (`statsmodels.tsa.stattools.adfuller`) to "
            "confirm non-stationarity before differencing. After differencing, R² "
            "should drop substantially."
        ),
        "adf_context": "Both series fail the ADF stationarity test (p >> 0.05 in levels).",
    },
    {
        "seed": 2,
        "y_col": "M2SL",
        "x_col": "GDP",
        "y_label": "M2 Money Supply",
        "x_label": "GDP",
        "spurious_r2": 0.98,
        "expected_r2_max": 0.5,
        "bias_description": (
            "Both M2 money supply and GDP grow exponentially over time. Their levels "
            "regression yields R²≈0.98 almost entirely because both series trend "
            "upward together — a hallmark of spurious regression. Any two series "
            "that grow over time will show high R² in levels regardless of whether "
            "they are economically linked."
        ),
        "fix_description": (
            "Apply log-differencing (growth rates): `diff_y = np.log(y).diff().dropna()` "
            "and `diff_x = np.log(x).diff().dropna()`. This converts the series to "
            "stationary growth rates. Regress the growth rates on each other. "
            "R² should drop to ~0.1-0.3 reflecting only genuine co-movement."
        ),
        "adf_context": "Both M2 and GDP levels are I(1) — they fail the ADF test in levels but pass after differencing.",
    },
]


class Generator(AdversarialWorkspaceGenerator):
    task_id = "RDS17_macro_spurious"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]
    dataset_name = "fred_macro"
    dataset_license = "Public Domain"
    dataset_source = "FRED / St. Louis Fed"

    def generate(self, seed: int) -> GeneratedTask:
        v = _VARIANTS[seed % len(_VARIANTS)]

        workspace_files = {
            "analysis.py": self._make_analysis_py(v),
            "requirements.txt": "pandas>=1.5\nnumpy>=1.23\nscipy>=1.9\nstatsmodels>=0.13\n",
            "check_solution.py": self._make_check_solution(v),
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._make_spec(v),
            brief_md=self._make_brief(v),
            expected={"y_col": v["y_col"], "x_col": v["x_col"], "seed": seed},
            workspace_files=workspace_files,
        )

    # ------------------------------------------------------------------
    # analysis.py — buggy levels regression on non-stationary series
    # ------------------------------------------------------------------

    def _make_analysis_py(self, v: dict) -> str:
        y_col = v["y_col"]
        x_col = v["x_col"]
        y_label = v["y_label"]
        x_label = v["x_label"]

        return textwrap.dedent(f"""\
            \"\"\"
            Macro time series regression: {y_label} ~ {x_label}.

            Loads the fred_macro dataset, regresses {y_col} on {x_col} in levels,
            and saves results to results.json and report.md.
            \"\"\"
            import json
            import pathlib
            import numpy as np
            import pandas as pd
            from sklearn.linear_model import LinearRegression
            from sklearn.metrics import r2_score

            # ── Load data ────────────────────────────────────────────────────────────
            data_path = pathlib.Path(__file__).parent.parent / "datasets" / "fred_macro.csv"
            df = pd.read_csv(data_path, comment="#", parse_dates=["date"] if "date" in
                             open(data_path).readline() else False)

            # ── Prepare series ────────────────────────────────────────────────────
            # Use levels directly — no stationarity transformation
            available_cols = df.columns.tolist()
            y_col = next((c for c in ["{y_col}"] if c in available_cols), available_cols[1])
            x_col = next((c for c in ["{x_col}"] if c in available_cols), available_cols[2])

            df_clean = df[[x_col, y_col]].dropna().copy()
            X = df_clean[[x_col]].values
            y = df_clean[y_col].values

            # ── Regression in levels ──────────────────────────────────────────────
            model = LinearRegression()
            model.fit(X, y)
            y_pred = model.predict(X)
            r2 = r2_score(y, y_pred)
            coef = float(model.coef_[0])
            intercept = float(model.intercept_)

            # ── Save results ──────────────────────────────────────────────────────
            out_dir = pathlib.Path(__file__).parent
            results = {{
                "n_obs": int(len(df_clean)),
                "y_variable": y_col,
                "x_variable": x_col,
                "r2": round(float(r2), 4),
                "coefficient": round(coef, 6),
                "intercept": round(intercept, 4),
                "method": "levels_regression",
            }}
            (out_dir / "results.json").write_text(
                json.dumps(results, indent=2), encoding="utf-8"
            )

            # ── Save report ───────────────────────────────────────────────────────
            report = f\"\"\"# Macro Regression Report: {{y_col}} ~ {{x_col}}

            ## Dataset
            - Source: fred_macro
            - Observations: {{len(df_clean)}}

            ## Model (levels regression)
            - R²: {{r2:.4f}}
            - Coefficient on {{x_col}}: {{coef:.6f}}
            - Intercept: {{intercept:.4f}}

            ## Conclusion
            Strong positive relationship found (R²={{r2:.2f}}).
            {{x_col}} appears to be a strong predictor of {{y_col}}.
            \"\"\"
            (out_dir / "report.md").write_text(report, encoding="utf-8")

            print(f"Observations : {{len(df_clean)}}")
            print(f"R²           : {{r2:.4f}}")
            print(f"Coefficient  : {{coef:.6f}}")
            print("Saved results.json and report.md")
        """)

    # ------------------------------------------------------------------
    # check_solution.py
    # ------------------------------------------------------------------

    def _make_check_solution(self, v: dict) -> str:
        expected_r2_max = v["expected_r2_max"]

        checks = [
            {
                "id": "C1",
                "description": "Stationarity test or differencing applied in analysis.py",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    src = (pathlib.Path(workspace_dir) / "analysis.py").read_text(encoding="utf-8")
                    src_lower = src.lower()
                    terms = ["diff()", ".diff(", "adfuller", "adf", "difference",
                             "first_diff", "log_diff", "pct_change", "stationar"]
                    found = [t for t in terms if t in src_lower]
                    passed = len(found) >= 1
                    detail = f"stationarity/differencing terms found: {found}"
                """),
            },
            {
                "id": "C2",
                "description": "results.json exists with 'r2' key",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    rpath = pathlib.Path(workspace_dir) / "results.json"
                    if not rpath.exists():
                        passed = False
                        detail = "results.json not found"
                    else:
                        data = json.loads(rpath.read_text(encoding="utf-8"))
                        passed = "r2" in data
                        detail = f"keys present: {list(data.keys())}"
                """),
            },
            {
                "id": "C3",
                "description": f"R² in results.json <= {expected_r2_max} (spurious regression corrected)",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import json, pathlib
                    rpath = pathlib.Path(workspace_dir) / "results.json"
                    if not rpath.exists():
                        passed = False
                        detail = "results.json not found"
                    else:
                        data = json.loads(rpath.read_text(encoding="utf-8"))
                        r2 = data.get("r2", 1.0)
                        passed = float(r2) <= {expected_r2_max}
                        detail = f"r2={{r2}} (need <= {expected_r2_max})"
                """),
            },
            {
                "id": "C4",
                "description": "results.json contains 'method' key indicating differencing",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    rpath = pathlib.Path(workspace_dir) / "results.json"
                    if not rpath.exists():
                        passed = False
                        detail = "results.json not found"
                    else:
                        data = json.loads(rpath.read_text(encoding="utf-8"))
                        method = str(data.get("method", "")).lower()
                        passed = any(t in method for t in
                                     ["diff", "stationary", "growth", "change", "log"])
                        detail = f"method={data.get('method', 'missing')}"
                """),
            },
            {
                "id": "C5",
                "description": "report.md mentions spurious regression or non-stationarity",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    rpath = pathlib.Path(workspace_dir) / "report.md"
                    if not rpath.exists():
                        passed = False
                        detail = "report.md not found"
                    else:
                        content = rpath.read_text(encoding="utf-8").lower()
                        keywords = ["spurious", "non-stationary", "nonstationarity",
                                    "unit root", "differenc", "stationarity", "adf"]
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
        y_col = v["y_col"]
        x_col = v["x_col"]
        y_label = v["y_label"]
        x_label = v["x_label"]
        spurious_r2 = v["spurious_r2"]
        expected_r2_max = v["expected_r2_max"]
        bias_desc = v["bias_description"]
        fix_desc = v["fix_description"]
        adf_context = v["adf_context"]

        return textwrap.dedent(f"""\
            # RDS17: Spurious Regression on Non-Stationary Macro Time Series

            ## Overview

            The workspace contains `analysis.py`, a regression analysis of FRED
            macroeconomic data that regresses `{y_col}` ({y_label}) on `{x_col}`
            ({x_label}) in levels. The script reports R²≈{spurious_r2:.2f} and
            concludes a strong relationship. It runs without errors.

            **However, this is a spurious regression** — both series are non-stationary
            (I(1)), and the high R² reflects shared trend, not genuine economic signal.

            ## The Flaw

            ### Non-Stationary Levels Regression

            {bias_desc}

            ### Stationarity Context

            {adf_context}

            ### Quantitative Impact

            | Condition | R² |
            |---|---|
            | Current (levels regression — spurious) | ~{spurious_r2:.2f} |
            | After fix (differenced series) | ~0.1–0.2 |

            Granger (1974) showed that regressing two independent random walks produces
            t-statistics that appear significant roughly 75% of the time even when the
            series are completely unrelated.

            ## Required Fix

            {fix_desc}

            ### Specific Changes to `analysis.py`

            1. **Apply first-differences** (or log-differences for exponential series):
               ```python
               diff_y = df_clean[y_col].diff().dropna()
               diff_x = df_clean[x_col].diff().dropna()
               ```
            2. **Regress** `diff_y` on `diff_x` instead of the levels.
            3. **Update** `results.json` with the corrected R² and set `method` to
               indicate differencing (e.g. `"first_difference"` or `"log_difference"`).
            4. **Update** `report.md` to acknowledge the spurious regression issue and
               explain the stationarity fix.

            ## Deliverables

            - Fixed `analysis.py` (differencing applied)
            - `results.json` with `r2` <= {expected_r2_max} and `method` indicating differencing
            - `report.md` that mentions spurious regression or non-stationarity

            ## Grading Rubric

            | Check | Description |
            |---|---|
            | C1 | Differencing or stationarity test present in `analysis.py` |
            | C2 | `results.json` contains `r2` key |
            | C3 | R² in `results.json` <= {expected_r2_max} |
            | C4 | `results.json` `method` field indicates differencing |
            | C5 | `report.md` mentions spurious regression or non-stationarity |
            | C6 | `analysis.py` runs without error |
        """)

    # ------------------------------------------------------------------
    # brief.md
    # ------------------------------------------------------------------

    def _make_brief(self, v: dict) -> str:
        y_col = v["y_col"]
        x_col = v["x_col"]
        return textwrap.dedent(f"""\
            # RDS17: Macro Time Series Regression Review

            ## Task

            Review and validate the existing analysis in `analysis.py` for methodological issues.

            The script analyses `fred_macro` macroeconomic data to examine the relationship
            between `{y_col}` and `{x_col}`. It currently runs without error and produces
            `results.json` and `report.md`.

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
