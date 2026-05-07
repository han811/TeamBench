"""
Generator for RDS16: P-Hacking via Multiple Comparisons in Retail Data.

Archetype 4 — Adversarial Workspace.

The workspace contains a COMPLETE, RUNNING analysis that tests 15 customer
segments for a conversion difference, reports 3 "significant" results (p<0.05)
without multiple comparison correction. Expected false positives by chance:
15 × 0.05 = 0.75.

Three seed variants using online_retail dataset:

  Seed 0: Tests 15 country segments for revenue-per-order difference vs baseline.
          Reports segments with p<0.05. Fix: Bonferroni correction (threshold 0.05/15).
          After correction, 0 or 1 segments significant.

  Seed 1: Tests 15 product categories for quantity-per-order difference.
          Same multiple-testing issue. Fix: Benjamini-Hochberg correction.

  Seed 2: Tests 15 hour-of-day bins for repeat-purchase rate difference.
          Same issue. Fix: Bonferroni or BH correction.

The spec tells the agent exactly what the flaw is and how to fix it.
The brief is vague: "Review and validate the existing analysis."

Rubric (6 checks):
  C1 — Correction applied: 'bonferroni' or 'fdr_bh' or adjusted p-values in analysis.py
  C2 — results.json exists with 'significant_segments' key
  C3 — n_significant in results.json <= 3 after correction (0 or 1 vs uncorrected 3)
  C4 — results.json contains 'n_tests' key with value 15
  C5 — report.md mentions multiple comparison / correction / Bonferroni / false positive
  C6 — analysis.py runs without error
"""
from __future__ import annotations

import textwrap

from generators.base import GeneratedTask
from generators.real_data_base import AdversarialWorkspaceGenerator

_VARIANTS = [
    {
        "seed": 0,
        "segment_col": "Country",
        "metric": "revenue per order",
        "metric_col": "UnitPrice",
        "agg_fn": "mean",
        "n_segments": 15,
        "bias_description": (
            "The analysis tests 15 country segments for a difference in mean revenue "
            "per order vs the overall baseline using t-tests, and reports any segment "
            "with p < 0.05 as 'significantly different'. With 15 independent tests at "
            "alpha=0.05, we expect 15 × 0.05 = 0.75 false positives by chance alone. "
            "Finding 3 'significant' segments without correction is well within the "
            "expected false-positive count."
        ),
        "fix_description": (
            "Apply Bonferroni correction: use alpha_corrected = 0.05 / 15 = 0.0033 "
            "as the significance threshold, OR use `statsmodels.stats.multitest.multipletests` "
            "with method='bonferroni' (or 'fdr_bh'). Report only segments that survive "
            "the corrected threshold."
        ),
        "correction_method": "bonferroni",
    },
    {
        "seed": 1,
        "segment_col": "Description",
        "metric": "quantity per order",
        "metric_col": "Quantity",
        "agg_fn": "mean",
        "n_segments": 15,
        "bias_description": (
            "The analysis tests 15 product categories for a difference in mean quantity "
            "per order vs the overall mean using t-tests, reporting p < 0.05 as "
            "significant. With 15 tests, 0.75 false positives are expected by chance. "
            "The 3 'significant' categories almost certainly include false discoveries."
        ),
        "fix_description": (
            "Apply Benjamini-Hochberg FDR correction using "
            "`statsmodels.stats.multitest.multipletests` with method='fdr_bh'. "
            "Report only categories with corrected p-values (q-values) < 0.05."
        ),
        "correction_method": "fdr_bh",
    },
    {
        "seed": 2,
        "segment_col": "Country",
        "metric": "unit price",
        "metric_col": "UnitPrice",
        "agg_fn": "median",
        "n_segments": 15,
        "bias_description": (
            "The analysis tests 15 country segments for a difference in median unit "
            "price using Mann-Whitney U tests, reporting p < 0.05 as significant. "
            "With 15 tests, the family-wise error rate without correction is "
            "1 - (1-0.05)^15 = 54% — i.e., over half the time at least one false "
            "positive appears by chance."
        ),
        "fix_description": (
            "Apply Bonferroni correction: adjusted threshold = 0.05 / 15 = 0.0033. "
            "Alternatively use `multipletests` with method='bonferroni'. Report only "
            "segments with corrected p < 0.05."
        ),
        "correction_method": "bonferroni",
    },
]


class Generator(AdversarialWorkspaceGenerator):
    task_id = "RDS16_retail_phacking"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]
    dataset_name = "online_retail"
    dataset_license = "CC BY 4.0"
    dataset_source = "UCI ML Repository"

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
            expected={"n_tests": v["n_segments"], "seed": seed},
            workspace_files=workspace_files,
        )

    # ------------------------------------------------------------------
    # analysis.py — buggy: no multiple-comparison correction
    # ------------------------------------------------------------------

    def _make_analysis_py(self, v: dict) -> str:
        segment_col = v["segment_col"]
        metric_col = v["metric_col"]
        agg_fn = v["agg_fn"]
        metric = v["metric"]
        n_segments = v["n_segments"]

        return textwrap.dedent(f"""\
            \"\"\"
            Online retail segment analysis: {metric} by {segment_col}.

            Tests {n_segments} {segment_col} segments for differences in {metric}
            and reports significant segments (p < 0.05).
            Saves results to results.json and report.md.
            \"\"\"
            import json
            import pathlib
            import numpy as np
            import pandas as pd
            from scipy import stats

            # ── Load data ────────────────────────────────────────────────────────────
            data_path = pathlib.Path(__file__).parent.parent / "datasets" / "online_retail.csv"
            df = pd.read_csv(data_path, comment="#", encoding="latin-1")

            # Clean up
            df = df.dropna(subset=["{segment_col}", "{metric_col}"])
            df = df[df["{metric_col}"] > 0].copy()

            # ── Select top segments by volume ─────────────────────────────────────
            top_segments = (
                df["{segment_col}"].value_counts().head({n_segments}).index.tolist()
            )
            df_top = df[df["{segment_col}"].isin(top_segments)].copy()

            # ── Overall baseline ──────────────────────────────────────────────────
            overall = df_top["{metric_col}"].values

            # ── Test each segment vs overall ──────────────────────────────────────
            # No multiple-comparison correction applied
            alpha = 0.05
            results_list = []
            for seg in top_segments:
                seg_vals = df_top[df_top["{segment_col}"] == seg]["{metric_col}"].values
                if len(seg_vals) < 10:
                    continue
                stat, pval = stats.ttest_ind(seg_vals, overall, equal_var=False)
                seg_mean = float(np.{agg_fn}(seg_vals))
                results_list.append({{
                    "segment": str(seg),
                    "n": int(len(seg_vals)),
                    "{agg_fn}_{metric_col}": round(seg_mean, 4),
                    "t_stat": round(float(stat), 4),
                    "p_value": round(float(pval), 6),
                    "significant": bool(pval < alpha),
                }})

            significant = [r for r in results_list if r["significant"]]
            n_significant = len(significant)

            # ── Save results ──────────────────────────────────────────────────────
            out_dir = pathlib.Path(__file__).parent
            results = {{
                "n_tests": len(results_list),
                "alpha": alpha,
                "n_significant": n_significant,
                "significant_segments": [r["segment"] for r in significant],
                "all_results": results_list,
            }}
            (out_dir / "results.json").write_text(
                json.dumps(results, indent=2), encoding="utf-8"
            )

            # ── Save report ───────────────────────────────────────────────────────
            report = f\"\"\"# Retail Segment Analysis Report

            ## Dataset
            - Source: online_retail
            - Segments tested: {{len(results_list)}}

            ## Significant Segments (p < {{alpha}})
            Found {{n_significant}} significant segments out of {{len(results_list)}} tested:
            {{', '.join(r['segment'] for r in significant) if significant else 'None'}}

            ## Method
            Two-sample t-test (Welch) for each segment vs overall baseline.
            Alpha = {{alpha}} (uncorrected).
            \"\"\"
            (out_dir / "report.md").write_text(report, encoding="utf-8")

            print(f"Segments tested  : {{len(results_list)}}")
            print(f"Significant (raw): {{n_significant}}")
            print("Saved results.json and report.md")
        """)

    # ------------------------------------------------------------------
    # check_solution.py
    # ------------------------------------------------------------------

    def _make_check_solution(self, v: dict) -> str:
        n_segments = v["n_segments"]

        checks = [
            {
                "id": "C1",
                "description": "Multiple comparison correction applied in analysis.py",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    src = (pathlib.Path(workspace_dir) / "analysis.py").read_text(encoding="utf-8")
                    src_lower = src.lower()
                    correction_terms = [
                        "bonferroni", "fdr_bh", "multipletests", "p_adjust",
                        "adjusted", "correction", "fdr", "holm", "bh"
                    ]
                    found = [t for t in correction_terms if t in src_lower]
                    passed = len(found) >= 1
                    detail = f"correction terms found: {found}"
                """),
            },
            {
                "id": "C2",
                "description": "results.json exists with 'significant_segments' key",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    rpath = pathlib.Path(workspace_dir) / "results.json"
                    if not rpath.exists():
                        passed = False
                        detail = "results.json not found"
                    else:
                        data = json.loads(rpath.read_text(encoding="utf-8"))
                        passed = "significant_segments" in data
                        detail = f"keys present: {list(data.keys())}"
                """),
            },
            {
                "id": "C3",
                "description": "n_significant in results.json <= 3 after correction (vs uncorrected 3+)",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    rpath = pathlib.Path(workspace_dir) / "results.json"
                    if not rpath.exists():
                        passed = False
                        detail = "results.json not found"
                    else:
                        data = json.loads(rpath.read_text(encoding="utf-8"))
                        n = data.get("n_significant", 999)
                        # After correction, expect 0-2 significant; accept up to 3
                        passed = int(n) <= 3
                        detail = f"n_significant={n} (need <= 3)"
                """),
            },
            {
                "id": "C4",
                "description": f"results.json contains 'n_tests' key with value {n_segments}",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import json, pathlib
                    rpath = pathlib.Path(workspace_dir) / "results.json"
                    if not rpath.exists():
                        passed = False
                        detail = "results.json not found"
                    else:
                        data = json.loads(rpath.read_text(encoding="utf-8"))
                        n = data.get("n_tests", 0)
                        passed = int(n) >= {n_segments - 2}  # allow a few dropped for small N
                        detail = f"n_tests={{n}} (need >= {n_segments - 2})"
                """),
            },
            {
                "id": "C5",
                "description": "report.md mentions multiple comparison correction or false positives",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    rpath = pathlib.Path(workspace_dir) / "report.md"
                    if not rpath.exists():
                        passed = False
                        detail = "report.md not found"
                    else:
                        content = rpath.read_text(encoding="utf-8").lower()
                        keywords = ["multiple", "bonferroni", "correction", "false positive",
                                    "family-wise", "fdr", "adjusted", "p-hack"]
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
        segment_col = v["segment_col"]
        metric = v["metric"]
        n_segments = v["n_segments"]
        bias_desc = v["bias_description"]
        fix_desc = v["fix_description"]
        correction_method = v["correction_method"]
        expected_fp = n_segments * 0.05

        return textwrap.dedent(f"""\
            # RDS16: P-Hacking via Multiple Comparisons in Retail Analysis

            ## Overview

            The workspace contains `analysis.py`, an analysis of the Online Retail
            dataset that tests {n_segments} `{segment_col}` segments for differences
            in `{metric}`. The script reports "significant" segments using p < 0.05.
            It runs without errors and produces `results.json` and `report.md`.

            **However, the analysis performs multiple comparisons without correction**,
            inflating the false-positive rate and producing spurious "significant" results.

            ## The Flaw

            ### No Multiple-Comparison Correction

            {bias_desc}

            ### Statistical Impact

            | | Value |
            |---|---|
            | Number of tests | {n_segments} |
            | Uncorrected alpha | 0.05 |
            | Expected false positives by chance | {expected_fp:.2f} |
            | Family-wise error rate (no correction) | {1 - (1-0.05)**n_segments:.1%} |
            | "Significant" results found | ~3 |

            With a {1 - (1-0.05)**n_segments:.0%} chance of at least one false positive,
            the "significant" segments are likely noise.

            ## Required Fix

            {fix_desc}

            ### Specific Changes to `analysis.py`

            1. **Import** `from statsmodels.stats.multitest import multipletests`
            2. **Collect all p-values** from the per-segment tests into a list.
            3. **Apply correction**:
               ```python
               reject, p_adjusted, _, _ = multipletests(p_values, alpha=0.05, method='{correction_method}')
               ```
            4. **Report only segments** where `reject[i]` is True.
            5. Update `results.json` with the corrected `n_significant` and
               `significant_segments`.
            6. Update `report.md` to acknowledge the multiple-comparison issue.

            ## Deliverables

            - Fixed `analysis.py` (correction applied)
            - `results.json` with corrected `n_significant` (expected 0-2) and `n_tests`={n_segments}
            - `report.md` that mentions multiple comparison correction

            ## Grading Rubric

            | Check | Description |
            |---|---|
            | C1 | Multiple comparison correction applied in `analysis.py` |
            | C2 | `results.json` contains `significant_segments` key |
            | C3 | `n_significant` in `results.json` <= 3 after correction |
            | C4 | `results.json` contains `n_tests` key with value ~{n_segments} |
            | C5 | `report.md` mentions multiple comparison correction |
            | C6 | `analysis.py` runs without error |
        """)

    # ------------------------------------------------------------------
    # brief.md
    # ------------------------------------------------------------------

    def _make_brief(self, v: dict) -> str:
        return textwrap.dedent("""\
            # RDS16: Retail Segment Analysis Review

            ## Task

            Review and validate the existing analysis in `analysis.py` for methodological issues.

            The script analyses the `online_retail` dataset to identify customer segments
            with significantly different purchasing behaviour. It currently runs without
            error and produces `results.json` and `report.md`.

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
