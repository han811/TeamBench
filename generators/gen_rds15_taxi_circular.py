"""
Generator for RDS15: Circular Tip Percentage Calculation in NYC Taxi Data.

Archetype 4 — Adversarial Workspace.

The workspace contains a COMPLETE, RUNNING analysis that computes tip percentage
as tip_amount / total_amount. This is circular because total_amount INCLUDES tip,
making tip% systematically underestimated and the denominator endogenous.

Three seed variants using nyc_taxi dataset:

  Seed 0: tip_pct = tip_amount / total_amount (circular — total includes tip)
          Reports mean tip_pct ~14%. Fix: use fare_amount as denominator.
          Corrected mean tip_pct should be ~18-20%.

  Seed 1: Same circular formula, but analysis groups by payment_type.
          The circular formula affects all payment types. Fix same denominator.

  Seed 2: Circular formula used to build a tip predictor model.
          Feature importance and model predictions are biased. Fix denominator.

The spec tells the agent exactly what the flaw is and how to fix it.
The brief is vague: "Review and validate the existing analysis."

Rubric (6 checks):
  C1 — tip_pct formula uses fare_amount (or subtracted denominator) not total_amount
  C2 — results.json exists with 'mean_tip_pct' key
  C3 — mean_tip_pct in results.json >= 0.16 (corrected, higher than biased ~0.14)
  C4 — results.json contains 'n_rows' key
  C5 — report.md mentions circular / denominator / total_amount / fare_amount
  C6 — analysis.py runs without error
"""
from __future__ import annotations

import textwrap

from generators.base import GeneratedTask
from generators.real_data_base import AdversarialWorkspaceGenerator

_VARIANTS = [
    {
        "seed": 0,
        "analysis_focus": "aggregate tip statistics",
        "group_by": None,
        "bias_description": (
            "The script computes tip percentage as `tip_amount / total_amount`. "
            "However, `total_amount` is defined as fare + surcharges + tip + tolls. "
            "Since tip is already included in the denominator, the formula "
            "systematically underestimates tip percentage. For a $2 tip on a $10 "
            "fare, the circular formula gives 2/12 = 16.7% instead of the correct "
            "2/10 = 20.0%. The denominator is endogenous to the numerator."
        ),
        "fix_description": (
            "Replace `tip_pct = tip_amount / total_amount` with "
            "`tip_pct = tip_amount / fare_amount` (or equivalently, "
            "`tip_amount / (total_amount - tip_amount)`). "
            "Use `fare_amount` as the base fare denominator. Filter rows where "
            "`fare_amount > 0` to avoid division by zero. "
            "The corrected mean tip percentage should rise from ~14% to ~18-20%."
        ),
        "buggy_formula": "df['tip_pct'] = df['tip_amount'] / df['total_amount']",
        "fixed_formula": "df['tip_pct'] = df['tip_amount'] / df['fare_amount']",
    },
    {
        "seed": 1,
        "analysis_focus": "tip rates by payment type",
        "group_by": "payment_type",
        "bias_description": (
            "The script computes tip percentage as `tip_amount / total_amount` and "
            "breaks this down by `payment_type`. Since `total_amount` includes the tip, "
            "every payment type's tip rate is understated. The ranking of payment types "
            "by generosity may also be distorted because the magnitude of the circular "
            "bias varies with tip size."
        ),
        "fix_description": (
            "Replace `tip_pct = tip_amount / total_amount` with "
            "`tip_pct = tip_amount / fare_amount`. Filter `fare_amount > 0`. "
            "Re-run the group-by analysis. The corrected rates will be consistently "
            "higher across all payment types."
        ),
        "buggy_formula": "df['tip_pct'] = df['tip_amount'] / df['total_amount']",
        "fixed_formula": "df['tip_pct'] = df['tip_amount'] / df['fare_amount']",
    },
    {
        "seed": 2,
        "analysis_focus": "tip percentage predictor",
        "group_by": None,
        "bias_description": (
            "The script trains a regression model to predict tip percentage, where "
            "the target is computed as `tip_amount / total_amount`. Since `total_amount` "
            "contains the tip, the model is partially predicting a value derived from "
            "one of its potential input features. The circular definition of the target "
            "variable leads to biased feature importances and optimistic model performance."
        ),
        "fix_description": (
            "Redefine the target as `tip_pct = tip_amount / fare_amount` (base fare "
            "only). Filter `fare_amount > 0`. Retrain the model with the corrected target. "
            "Feature importances and predictions will differ from the biased model."
        ),
        "buggy_formula": "df['tip_pct'] = df['tip_amount'] / df['total_amount']",
        "fixed_formula": "df['tip_pct'] = df['tip_amount'] / df['fare_amount']",
    },
]


class Generator(AdversarialWorkspaceGenerator):
    task_id = "RDS15_taxi_circular"
    domain = "data_science"
    difficulty = "medium"
    languages = ["python"]
    dataset_name = "nyc_taxi"
    dataset_license = "Public Domain"
    dataset_source = "NYC TLC / Kaggle"

    def generate(self, seed: int) -> GeneratedTask:
        v = _VARIANTS[seed % len(_VARIANTS)]

        workspace_files = {
            "analysis.py": self._make_analysis_py(v),
            "requirements.txt": "pandas>=1.5\nnumpy>=1.23\nscikit-learn>=1.1\n",
            "check_solution.py": self._make_check_solution(v),
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._make_spec(v),
            brief_md=self._make_brief(v),
            expected={"buggy_formula": v["buggy_formula"], "seed": seed},
            workspace_files=workspace_files,
        )

    # ------------------------------------------------------------------
    # analysis.py
    # ------------------------------------------------------------------

    def _make_analysis_py(self, v: dict) -> str:
        buggy_formula = v["buggy_formula"]
        analysis_focus = v["analysis_focus"]
        group_by = v["group_by"]

        group_block = ""
        if group_by:
            group_block = textwrap.dedent(f"""\
                # ── Group analysis ───────────────────────────────────────────────────
                group_stats = (
                    df_filtered.groupby("{group_by}")["tip_pct"]
                    .agg(["mean", "median", "count"])
                    .reset_index()
                )
                group_stats.columns = ["{group_by}", "mean_tip_pct", "median_tip_pct", "count"]
                results["group_results"] = group_stats.to_dict(orient="records")
            """)

        return textwrap.dedent(f"""\
            \"\"\"
            NYC Taxi tip percentage analysis: {analysis_focus}.

            Loads the nyc_taxi dataset, computes tip percentage, and saves
            summary statistics to results.json and report.md.
            \"\"\"
            import json
            import pathlib
            import numpy as np
            import pandas as pd

            # ── Load data ────────────────────────────────────────────────────────────
            data_path = pathlib.Path(__file__).parent.parent / "datasets" / "nyc_taxi.csv"
            df = pd.read_csv(data_path, comment="#")

            # ── Compute tip percentage ────────────────────────────────────────────
            # Filter to credit-card trips (cash trips have tip_amount=0 by convention)
            df_filtered = df[df["payment_type"] == 1].copy() if "payment_type" in df.columns else df.copy()
            df_filtered = df_filtered[df_filtered["total_amount"] > 0].copy()

            # Compute tip percentage as fraction of total fare
            {buggy_formula}

            # Remove extreme outliers
            df_filtered = df_filtered[
                (df_filtered["tip_pct"] >= 0) & (df_filtered["tip_pct"] <= 1.0)
            ].copy()

            mean_tip = float(df_filtered["tip_pct"].mean())
            median_tip = float(df_filtered["tip_pct"].median())
            n_rows = int(len(df_filtered))

            # ── Save results ──────────────────────────────────────────────────────
            out_dir = pathlib.Path(__file__).parent
            results = {{
                "n_rows": n_rows,
                "mean_tip_pct": round(mean_tip, 4),
                "median_tip_pct": round(median_tip, 4),
            }}
            {group_block}
            (out_dir / "results.json").write_text(
                json.dumps(results, indent=2), encoding="utf-8"
            )

            # ── Save report ───────────────────────────────────────────────────────
            report = f\"\"\"# NYC Taxi Tip Percentage Analysis

            ## Dataset
            - Source: nyc_taxi
            - Rows analysed: {{n_rows}} (credit-card trips)

            ## Results
            - Mean tip percentage: {{mean_tip:.1%}}
            - Median tip percentage: {{median_tip:.1%}}

            ## Method
            Tip percentage computed as tip_amount divided by total_amount.
            \"\"\"
            (out_dir / "report.md").write_text(report, encoding="utf-8")

            print(f"Rows analysed    : {{n_rows}}")
            print(f"Mean tip %       : {{mean_tip:.1%}}")
            print(f"Median tip %     : {{median_tip:.1%}}")
            print("Saved results.json and report.md")
        """)

    # ------------------------------------------------------------------
    # check_solution.py
    # ------------------------------------------------------------------

    def _make_check_solution(self, v: dict) -> str:
        checks = [
            {
                "id": "C1",
                "description": "tip_pct formula uses fare_amount (not total_amount) as denominator",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib, re
                    src = (pathlib.Path(workspace_dir) / "analysis.py").read_text(encoding="utf-8")
                    # Look for tip_pct assignment lines
                    tip_lines = [l.strip() for l in src.splitlines()
                                 if "tip_pct" in l and "=" in l and not l.strip().startswith("#")]
                    # Must not divide by total_amount; must use fare_amount or (total - tip)
                    still_circular = any("total_amount" in l and "tip_amount" not in l.split("/")[0]
                                         for l in tip_lines if "/" in l)
                    uses_fare = any("fare_amount" in l for l in tip_lines)
                    uses_subtracted = any(
                        re.search(r"total_amount\\s*-\\s*tip_amount|tip_amount\\s*/\\s*\\(", l)
                        for l in tip_lines
                    )
                    passed = bool((uses_fare or uses_subtracted) and not still_circular)
                    detail = f"tip lines: {tip_lines}, uses_fare={uses_fare}, uses_subtracted={uses_subtracted}"
                """),
            },
            {
                "id": "C2",
                "description": "results.json exists with 'mean_tip_pct' key",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    rpath = pathlib.Path(workspace_dir) / "results.json"
                    if not rpath.exists():
                        passed = False
                        detail = "results.json not found"
                    else:
                        data = json.loads(rpath.read_text(encoding="utf-8"))
                        passed = "mean_tip_pct" in data
                        detail = f"keys present: {list(data.keys())}"
                """),
            },
            {
                "id": "C3",
                "description": "mean_tip_pct in results.json >= 0.16 (corrected value higher than circular ~0.14)",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    rpath = pathlib.Path(workspace_dir) / "results.json"
                    if not rpath.exists():
                        passed = False
                        detail = "results.json not found"
                    else:
                        data = json.loads(rpath.read_text(encoding="utf-8"))
                        v = data.get("mean_tip_pct", 0)
                        passed = float(v) >= 0.16
                        detail = f"mean_tip_pct={v} (need >= 0.16)"
                """),
            },
            {
                "id": "C4",
                "description": "results.json contains 'n_rows' key",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    rpath = pathlib.Path(workspace_dir) / "results.json"
                    if not rpath.exists():
                        passed = False
                        detail = "results.json not found"
                    else:
                        data = json.loads(rpath.read_text(encoding="utf-8"))
                        passed = "n_rows" in data
                        detail = f"n_rows={data.get('n_rows', 'missing')}"
                """),
            },
            {
                "id": "C5",
                "description": "report.md mentions circular formula / denominator / fare_amount",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    rpath = pathlib.Path(workspace_dir) / "report.md"
                    if not rpath.exists():
                        passed = False
                        detail = "report.md not found"
                    else:
                        content = rpath.read_text(encoding="utf-8").lower()
                        keywords = ["circular", "denominator", "fare_amount", "fare amount",
                                    "total_amount", "includes tip", "include tip"]
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
        bias_desc = v["bias_description"]
        fix_desc = v["fix_description"]
        buggy_formula = v["buggy_formula"]
        fixed_formula = v["fixed_formula"]

        return textwrap.dedent(f"""\
            # RDS15: Circular Tip Percentage Calculation in NYC Taxi Data

            ## Overview

            The workspace contains `analysis.py`, a tip percentage analysis using the
            NYC Taxi dataset. The script computes tip statistics and saves
            `results.json` and `report.md`. It runs without errors.

            **However, the tip percentage formula is circular** — the denominator
            (`total_amount`) includes the numerator (`tip_amount`), causing systematic
            underestimation of tip rates.

            ## The Flaw

            ### Circular Formula

            The following line appears in `analysis.py`:

            ```python
            {buggy_formula}
            ```

            **Why this is wrong:**

            {bias_desc}

            ### Numerical Example

            | Trip | tip_amount | fare_amount | total_amount | Circular (tip/total) | Correct (tip/fare) |
            |---|---|---|---|---|---|
            | A | $2.00 | $10.00 | $12.50 | 16.0% | 20.0% |
            | B | $3.00 | $12.00 | $15.50 | 19.4% | 25.0% |

            The circular formula consistently underestimates tip generosity.

            ## Required Fix

            {fix_desc}

            ### Specific Change to `analysis.py`

            Replace:
            ```python
            {buggy_formula}
            ```

            With:
            ```python
            {fixed_formula}
            ```

            Also add `df_filtered = df_filtered[df_filtered["fare_amount"] > 0].copy()`
            to avoid division by zero.

            ## Deliverables

            - Fixed `analysis.py` (corrected tip formula)
            - `results.json` with `mean_tip_pct` >= 0.16 and `n_rows` key
            - `report.md` that explains the circular formula issue

            ## Grading Rubric

            | Check | Description |
            |---|---|
            | C1 | `tip_pct` uses `fare_amount` as denominator (not `total_amount`) |
            | C2 | `results.json` contains `mean_tip_pct` key |
            | C3 | `mean_tip_pct` in `results.json` >= 0.16 |
            | C4 | `results.json` contains `n_rows` key |
            | C5 | `report.md` mentions circular formula or denominator issue |
            | C6 | `analysis.py` runs without error |
        """)

    # ------------------------------------------------------------------
    # brief.md
    # ------------------------------------------------------------------

    def _make_brief(self, v: dict) -> str:
        return textwrap.dedent("""\
            # RDS15: NYC Taxi Tip Analysis Review

            ## Task

            Review and validate the existing analysis in `analysis.py` for methodological issues.

            The script analyses the `nyc_taxi` dataset to compute tip percentage statistics.
            It currently runs without error and produces `results.json` and `report.md`.

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
