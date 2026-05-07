"""
Generator for RDS18: Immortal Time Bias in Churn Analysis.

Archetype 4 — Adversarial Workspace.

The workspace contains a COMPLETE, RUNNING churn analysis that compares
'loyal' customers (tenure > 12 months) vs 'new' customers. The loyal group
is GUARANTEED to have survived 12 months — this is immortal time bias.
The analysis finds that loyal customers have lower churn rates, but this is
partially an artifact of the classification criterion itself.

Three seed variants using telco_churn dataset:

  Seed 0: Classifies loyal = tenure > 12, new = tenure <= 12.
          Reports loyal churn rate 6% vs new 35%. Fix: landmark analysis at
          month 12 — only compare customers who have reached month 12.

  Seed 1: Classifies loyal = tenure > 24, new = tenure <= 24.
          Same immortal time bias with longer window.

  Seed 2: Uses monthly_charges quintile to define 'high-value' (top quintile)
          vs 'low-value', but restricts high-value to tenure > 6.
          The tenure restriction introduces immortal time for high-value group.

The spec tells the agent exactly what the flaw is and how to fix it.
The brief is vague: "Review and validate the existing analysis."

Rubric (6 checks):
  C1 — Landmark analysis or survival-aware comparison in analysis.py
  C2 — results.json exists with 'landmark_churn_rates' or 'corrected_churn_rates' key
  C3 — Churn rate gap between groups reduced vs biased analysis (loyal_rate >= 0.10)
  C4 — results.json contains 'n_at_landmark' or 'n_landmark' key
  C5 — report.md mentions immortal / landmark / survival / bias
  C6 — analysis.py runs without error
"""
from __future__ import annotations

import textwrap

from generators.base import GeneratedTask
from generators.real_data_base import AdversarialWorkspaceGenerator

_VARIANTS = [
    {
        "seed": 0,
        "loyal_threshold": 12,
        "loyal_label": "loyal (tenure > 12 months)",
        "new_label": "new (tenure <= 12 months)",
        "group_col": "tenure",
        "threshold_val": 12,
        "bias_description": (
            "The analysis classifies customers with `tenure > 12` as 'loyal' and "
            "`tenure <= 12` as 'new', then compares churn rates. This introduces "
            "immortal time bias: every customer in the 'loyal' group is GUARANTEED "
            "to have survived at least 12 months without churning (otherwise they "
            "would be in the 'new' group). The low churn rate in the loyal group "
            "partially reflects this survival guarantee, not genuine loyalty."
        ),
        "fix_description": (
            "Apply a landmark analysis: restrict the comparison to customers who "
            "reached month 12 (tenure >= 12). Among these customers, compare those "
            "who subsequently churned vs those who did not. This eliminates the "
            "immortal time period. Report churn rates for the landmark cohort."
        ),
        "biased_loyal_churn": 0.06,
        "biased_new_churn": 0.35,
        "corrected_loyal_churn_min": 0.10,
    },
    {
        "seed": 1,
        "loyal_threshold": 24,
        "loyal_label": "loyal (tenure > 24 months)",
        "new_label": "new (tenure <= 24 months)",
        "group_col": "tenure",
        "threshold_val": 24,
        "bias_description": (
            "The analysis classifies customers with `tenure > 24` as 'loyal'. Every "
            "customer in this group has already survived 24 months — they cannot "
            "have churned before month 24 by definition. This immortal time of 24 "
            "months guarantees an artificially low apparent churn rate for 'loyal' "
            "customers, severely confounding the comparison."
        ),
        "fix_description": (
            "Apply a landmark analysis at month 24: restrict to customers with "
            "`tenure >= 24`. Among this cohort, compare churners vs non-churners. "
            "The churn rates for long-tenure customers will be higher than the "
            "biased analysis suggests once the immortal period is removed."
        ),
        "biased_loyal_churn": 0.03,
        "biased_new_churn": 0.32,
        "corrected_loyal_churn_min": 0.08,
    },
    {
        "seed": 2,
        "loyal_threshold": 6,
        "loyal_label": "high-value (top MonthlyCharges quintile, tenure > 6)",
        "new_label": "standard (remaining customers)",
        "group_col": "tenure",
        "threshold_val": 6,
        "bias_description": (
            "The analysis defines 'high-value' customers as those in the top quintile "
            "of MonthlyCharges AND with tenure > 6 months. The tenure > 6 filter "
            "introduces immortal time: high-value customers are guaranteed to have "
            "survived at least 6 months. Their lower apparent churn rate partly "
            "reflects this 6-month immortal window, not just their high-value status."
        ),
        "fix_description": (
            "Apply a landmark analysis at month 6: restrict all comparisons to customers "
            "with `tenure >= 6`. Compare high-value vs standard customers within this "
            "landmark cohort. The churn gap will narrow once the immortal period "
            "is removed from both groups."
        ),
        "biased_loyal_churn": 0.08,
        "biased_new_churn": 0.30,
        "corrected_loyal_churn_min": 0.10,
    },
]


class Generator(AdversarialWorkspaceGenerator):
    task_id = "RDS18_churn_immortal"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]
    dataset_name = "telco_churn"
    dataset_license = "Public Domain"
    dataset_source = "IBM / Kaggle"

    def generate(self, seed: int) -> GeneratedTask:
        v = _VARIANTS[seed % len(_VARIANTS)]

        workspace_files = {
            "analysis.py": self._make_analysis_py(v),
            "requirements.txt": "pandas>=1.5\nnumpy>=1.23\nscipy>=1.9\n",
            "check_solution.py": self._make_check_solution(v),
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._make_spec(v),
            brief_md=self._make_brief(v),
            expected={"threshold": v["loyal_threshold"], "seed": seed},
            workspace_files=workspace_files,
        )

    # ------------------------------------------------------------------
    # analysis.py — buggy: immortal time bias
    # ------------------------------------------------------------------

    def _make_analysis_py(self, v: dict) -> str:
        threshold = v["loyal_threshold"]
        loyal_label = v["loyal_label"]
        new_label = v["new_label"]

        return textwrap.dedent(f"""\
            \"\"\"
            Telco customer churn analysis.

            Compares churn rates between loyal ({loyal_label}) and
            new ({new_label}) customer segments.
            Saves results to results.json and report.md.
            \"\"\"
            import json
            import pathlib
            import numpy as np
            import pandas as pd
            from scipy import stats

            # ── Load data ────────────────────────────────────────────────────────────
            data_path = pathlib.Path(__file__).parent.parent / "datasets" / "telco_churn.csv"
            df = pd.read_csv(data_path, comment="#")

            # ── Prepare columns ───────────────────────────────────────────────────
            # Standardise column names
            df.columns = df.columns.str.strip()
            churn_col = next((c for c in df.columns if "churn" in c.lower()), "Churn")
            tenure_col = next((c for c in df.columns if "tenure" in c.lower()), "tenure")

            df["churned"] = df[churn_col].astype(str).str.strip().str.upper().isin(
                ["YES", "TRUE", "1", "Y"]
            ).astype(int)
            df[tenure_col] = pd.to_numeric(df[tenure_col], errors="coerce")
            df = df.dropna(subset=[tenure_col, "churned"])

            # ── Classify customers ────────────────────────────────────────────────
            # Loyal = tenure > {threshold} months (guaranteed to have survived {threshold} months)
            loyal_mask = df[tenure_col] > {threshold}
            new_mask = ~loyal_mask

            loyal = df[loyal_mask]
            new = df[new_mask]

            loyal_churn_rate = float(loyal["churned"].mean())
            new_churn_rate = float(new["churned"].mean())

            # ── Statistical test ──────────────────────────────────────────────────
            stat, pval = stats.ttest_ind(loyal["churned"].values, new["churned"].values)

            # ── Save results ──────────────────────────────────────────────────────
            out_dir = pathlib.Path(__file__).parent
            results = {{
                "n_total": int(len(df)),
                "n_loyal": int(len(loyal)),
                "n_new": int(len(new)),
                "loyal_churn_rate": round(loyal_churn_rate, 4),
                "new_churn_rate": round(new_churn_rate, 4),
                "churn_rate_gap": round(new_churn_rate - loyal_churn_rate, 4),
                "t_stat": round(float(stat), 4),
                "p_value": round(float(pval), 6),
                "loyalty_threshold_months": {threshold},
            }}
            (out_dir / "results.json").write_text(
                json.dumps(results, indent=2), encoding="utf-8"
            )

            # ── Save report ───────────────────────────────────────────────────────
            report = f\"\"\"# Telco Customer Churn Analysis Report

            ## Dataset
            - Source: telco_churn
            - Total customers: {{len(df)}}

            ## Segment Comparison (tenure threshold: {threshold} months)
            - Loyal customers (tenure > {threshold} months): n={{len(loyal)}}, churn={{loyal_churn_rate:.1%}}
            - New customers (tenure <= {threshold} months): n={{len(new)}}, churn={{new_churn_rate:.1%}}
            - Churn rate gap: {{new_churn_rate - loyal_churn_rate:+.1%}}

            ## Conclusion
            Loyal customers have significantly lower churn rates (p={{pval:.4f}}).
            Long-tenure customers demonstrate stronger retention.
            \"\"\"
            (out_dir / "report.md").write_text(report, encoding="utf-8")

            print(f"Total customers  : {{len(df)}}")
            print(f"Loyal churn rate : {{loyal_churn_rate:.1%}}")
            print(f"New churn rate   : {{new_churn_rate:.1%}}")
            print(f"Gap              : {{new_churn_rate - loyal_churn_rate:+.1%}}")
            print("Saved results.json and report.md")
        """)

    # ------------------------------------------------------------------
    # check_solution.py
    # ------------------------------------------------------------------

    def _make_check_solution(self, v: dict) -> str:
        threshold = v["loyal_threshold"]
        corrected_loyal_churn_min = v["corrected_loyal_churn_min"]

        checks = [
            {
                "id": "C1",
                "description": "Landmark analysis or survival-aware method present in analysis.py",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    src = (pathlib.Path(workspace_dir) / "analysis.py").read_text(encoding="utf-8")
                    src_lower = src.lower()
                    terms = ["landmark", "survival", "kaplan", "km_", "lifelines",
                             "tenure >=", "tenure>=", "at_risk", "at risk",
                             "reached", "month_12", "month_24", "cohort"]
                    found = [t for t in terms if t in src_lower]
                    passed = len(found) >= 1
                    detail = f"landmark/survival terms found: {found}"
                """),
            },
            {
                "id": "C2",
                "description": "results.json contains 'landmark_churn_rates' or 'corrected_churn_rates' key",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    rpath = pathlib.Path(workspace_dir) / "results.json"
                    if not rpath.exists():
                        passed = False
                        detail = "results.json not found"
                    else:
                        data = json.loads(rpath.read_text(encoding="utf-8"))
                        keys = set(data.keys())
                        landmark_keys = {"landmark_churn_rates", "corrected_churn_rates",
                                         "landmark_results", "corrected_loyal_churn_rate",
                                         "landmark_loyal_churn_rate"}
                        found_keys = keys & landmark_keys
                        passed = len(found_keys) > 0
                        detail = f"landmark keys found: {found_keys}, all keys: {list(keys)}"
                """),
            },
            {
                "id": "C3",
                "description": f"Corrected loyal churn rate >= {corrected_loyal_churn_min} (immortal bias reduced)",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import json, pathlib
                    rpath = pathlib.Path(workspace_dir) / "results.json"
                    if not rpath.exists():
                        passed = False
                        detail = "results.json not found"
                    else:
                        data = json.loads(rpath.read_text(encoding="utf-8"))
                        # Look for corrected/landmark loyal churn rate
                        candidate_keys = [
                            "landmark_loyal_churn_rate", "corrected_loyal_churn_rate",
                            "loyal_churn_rate_corrected", "landmark_churn_rate_loyal"
                        ]
                        rate = None
                        for k in candidate_keys:
                            if k in data:
                                rate = float(data[k])
                                break
                        # Also check nested dicts
                        if rate is None:
                            for k, v in data.items():
                                if isinstance(v, dict):
                                    for sk in candidate_keys:
                                        if sk in v:
                                            rate = float(v[sk])
                                            break
                                if rate is not None:
                                    break
                        if rate is None:
                            # Fall back: check if loyal_churn_rate increased from biased value
                            rate = float(data.get("loyal_churn_rate", 0.0))
                        passed = rate >= {corrected_loyal_churn_min}
                        detail = f"corrected loyal churn rate={{rate}} (need >= {corrected_loyal_churn_min})"
                """),
            },
            {
                "id": "C4",
                "description": "results.json contains 'n_at_landmark' or 'n_landmark' key",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    rpath = pathlib.Path(workspace_dir) / "results.json"
                    if not rpath.exists():
                        passed = False
                        detail = "results.json not found"
                    else:
                        data = json.loads(rpath.read_text(encoding="utf-8"))
                        landmark_n_keys = {"n_at_landmark", "n_landmark", "landmark_n",
                                           "n_landmark_cohort", "n_cohort"}
                        found = {k for k in data if any(lk in k.lower() for lk in
                                                         ["landmark", "cohort", "at_risk"])}
                        passed = len(found) > 0
                        detail = f"landmark N keys found: {found}"
                """),
            },
            {
                "id": "C5",
                "description": "report.md mentions immortal time bias or landmark analysis",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    rpath = pathlib.Path(workspace_dir) / "report.md"
                    if not rpath.exists():
                        passed = False
                        detail = "report.md not found"
                    else:
                        content = rpath.read_text(encoding="utf-8").lower()
                        keywords = ["immortal", "landmark", "survival", "bias",
                                    "guaranteed", "time bias", "survival analysis"]
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
        threshold = v["loyal_threshold"]
        loyal_label = v["loyal_label"]
        new_label = v["new_label"]
        bias_desc = v["bias_description"]
        fix_desc = v["fix_description"]
        biased_loyal = v["biased_loyal_churn"]
        biased_new = v["biased_new_churn"]
        corrected_min = v["corrected_loyal_churn_min"]

        return textwrap.dedent(f"""\
            # RDS18: Immortal Time Bias in Churn Analysis

            ## Overview

            The workspace contains `analysis.py`, a customer churn analysis on the
            Telco Churn dataset. It classifies customers as '{loyal_label}' or
            '{new_label}' and compares their churn rates.
            The script runs without errors and produces `results.json` and `report.md`.

            **However, the analysis contains immortal time bias** — the 'loyal' group
            classification criterion guarantees that these customers survived
            `tenure > {threshold}` months, creating an artificial immortal period
            that inflates the apparent loyalty effect.

            ## The Flaw

            ### Immortal Time Bias

            {bias_desc}

            ### Quantitative Impact

            | Group | Biased churn rate | Expected after fix |
            |---|---|---|
            | Loyal ({loyal_label}) | ~{biased_loyal:.0%} | >= {corrected_min:.0%} |
            | New ({new_label}) | ~{biased_new:.0%} | (similar) |

            The biased analysis overstates the difference between groups because the
            'loyal' group's low churn rate is partly a definitional artifact.

            ## Required Fix

            {fix_desc}

            ### Specific Changes to `analysis.py`

            1. **Apply landmark analysis**: filter the dataset to customers with
               `tenure >= {threshold}` to form the landmark cohort.
            2. **Compare churn rates** within this cohort (rather than comparing
               different-tenure groups).
            3. **Save** the landmark cohort size (`n_at_landmark`) and corrected
               churn rates (`landmark_churn_rates` or `corrected_loyal_churn_rate`)
               to `results.json`.
            4. **Update `report.md`** to acknowledge immortal time bias and explain
               the landmark analysis fix.

            ## Deliverables

            - Fixed `analysis.py` (landmark analysis applied)
            - `results.json` with `landmark_churn_rates` or `corrected_loyal_churn_rate`
              key, and `n_at_landmark` key
            - `report.md` that mentions immortal time bias

            ## Grading Rubric

            | Check | Description |
            |---|---|
            | C1 | Landmark or survival-aware method in `analysis.py` |
            | C2 | `results.json` contains `landmark_churn_rates` or `corrected_churn_rates` |
            | C3 | Corrected loyal churn rate >= {corrected_min:.0%} (bias reduced) |
            | C4 | `results.json` contains a landmark cohort size key |
            | C5 | `report.md` mentions immortal time bias or landmark analysis |
            | C6 | `analysis.py` runs without error |
        """)

    # ------------------------------------------------------------------
    # brief.md
    # ------------------------------------------------------------------

    def _make_brief(self, v: dict) -> str:
        return textwrap.dedent("""\
            # RDS18: Churn Analysis Review

            ## Task

            Review and validate the existing analysis in `analysis.py` for methodological issues.

            The script analyses the `telco_churn` dataset to compare churn rates between
            loyal and new customer segments. It currently runs without error and produces
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
