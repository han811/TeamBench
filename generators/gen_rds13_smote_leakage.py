"""
Generator for RDS13: SMOTE Leakage in Fraud Detection.

Archetype 4 — Adversarial Workspace.

The workspace contains a COMPLETE, RUNNING fraud detection pipeline that applies
SMOTE oversampling BEFORE the train/test split, causing test-set contamination
and inflating AUC to ~0.99. The script runs without error and looks correct.

Three seed variants using credit_card_fraud dataset:

  Seed 0: SMOTE applied before split, target column 'Class'.
          AUC inflated to ~0.99. Fix: split first, then SMOTE only on train.
          AUC should drop to ~0.95.

  Seed 1: RandomOverSampler (from imblearn) applied before split.
          Same contamination mechanism as seed 0 but different resampler.

  Seed 2: SMOTE + Tomek links applied before split.
          Uses SMOTETomek combined method, same contamination.

The spec tells the agent exactly what the flaw is and how to fix it.
The brief is vague: "Review and validate the existing analysis."

Rubric (6 checks):
  C1 — SMOTE/resample called AFTER train_test_split in analysis.py
  C2 — results.json exists with 'auc' key
  C3 — AUC in results.json <= 0.97 (contamination removed, realistic result)
  C4 — results.json contains 'n_train' and 'n_test' keys
  C5 — report.md mentions leakage / contamination / oversampling / SMOTE
  C6 — analysis.py runs without error
"""
from __future__ import annotations

import textwrap

from generators.base import GeneratedTask
from generators.real_data_base import AdversarialWorkspaceGenerator

_VARIANTS = [
    {
        "seed": 0,
        "resampler_name": "SMOTE",
        "resampler_import": "from imblearn.over_sampling import SMOTE",
        "resampler_init": "SMOTE(random_state=42)",
        "resampler_var": "smote",
        "inflated_auc": 0.999,
        "expected_auc_max": 0.97,
        "bias_description": (
            "The script calls SMOTE to oversample the minority class (fraud) BEFORE "
            "splitting into train and test sets. This means synthetic fraud samples "
            "derived from real test-set points appear in the training data. The model "
            "effectively memorises interpolations of its own test set, inflating AUC "
            "to ~0.999 — a result that will never replicate in production."
        ),
        "fix_description": (
            "Split the data FIRST using `train_test_split`, then apply SMOTE only to "
            "the training features and labels. The test set must contain only original "
            "(non-synthetic) samples. After the fix, AUC should drop to a realistic "
            "~0.95."
        ),
    },
    {
        "seed": 1,
        "resampler_name": "RandomOverSampler",
        "resampler_import": "from imblearn.over_sampling import RandomOverSampler",
        "resampler_init": "RandomOverSampler(random_state=42)",
        "resampler_var": "ros",
        "inflated_auc": 0.998,
        "expected_auc_max": 0.97,
        "bias_description": (
            "The script applies RandomOverSampler — which duplicates minority-class "
            "examples — BEFORE the train/test split. Exact duplicates of test-set "
            "fraud records end up in the training set. The model learns to perfectly "
            "recognise these duplicates, inflating AUC to ~0.998."
        ),
        "fix_description": (
            "Split the data FIRST with `train_test_split`, then apply RandomOverSampler "
            "only to the training portion. Never resample the test set. After the fix, "
            "AUC should drop to a realistic ~0.95."
        ),
    },
    {
        "seed": 2,
        "resampler_name": "SMOTETomek",
        "resampler_import": "from imblearn.combine import SMOTETomek",
        "resampler_init": "SMOTETomek(random_state=42)",
        "resampler_var": "smt",
        "inflated_auc": 0.999,
        "expected_auc_max": 0.97,
        "bias_description": (
            "The script uses SMOTETomek (combined SMOTE oversampling + Tomek link "
            "cleaning) applied BEFORE the train/test split. Synthetic minority samples "
            "are created from test-set points, and Tomek cleaning removes borderline "
            "majority samples that may include test examples. The model's AUC of ~0.999 "
            "is an artifact of this double contamination."
        ),
        "fix_description": (
            "Split the data FIRST with `train_test_split`. Apply SMOTETomek only to "
            "the training set. The test set must be a pristine holdout of original "
            "samples. After the fix, AUC should drop to a realistic ~0.95."
        ),
    },
]


class Generator(AdversarialWorkspaceGenerator):
    task_id = "RDS13_smote_leakage"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]
    dataset_name = "credit_card_fraud"
    dataset_license = "DbCL v1.0"
    dataset_source = "Kaggle / ULB"

    def generate(self, seed: int) -> GeneratedTask:
        v = _VARIANTS[seed % len(_VARIANTS)]

        analysis_py = self._make_analysis_py(v)
        check_py = self._make_check_solution(v)
        requirements_txt = (
            "pandas>=1.5\nnumpy>=1.23\nscikit-learn>=1.1\nimbalanced-learn>=0.10\n"
        )

        workspace_files = {
            "analysis.py": analysis_py,
            "requirements.txt": requirements_txt,
            "check_solution.py": check_py,
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._make_spec(v),
            brief_md=self._make_brief(v),
            expected={"resampler": v["resampler_name"], "seed": seed},
            workspace_files=workspace_files,
        )

    # ------------------------------------------------------------------
    # analysis.py — buggy pipeline (SMOTE before split)
    # ------------------------------------------------------------------

    def _make_analysis_py(self, v: dict) -> str:
        resampler_import = v["resampler_import"]
        resampler_init = v["resampler_init"]
        resampler_var = v["resampler_var"]
        resampler_name = v["resampler_name"]

        return textwrap.dedent(f"""\
            \"\"\"
            Credit card fraud detection pipeline.

            Loads the credit_card_fraud dataset, applies {resampler_name} to handle
            class imbalance, trains a Random Forest classifier, and evaluates on a
            held-out test set. Saves results to results.json and report.md.
            \"\"\"
            import json
            import pathlib
            import numpy as np
            import pandas as pd
            {resampler_import}
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.model_selection import train_test_split
            from sklearn.metrics import roc_auc_score, average_precision_score
            from sklearn.preprocessing import StandardScaler

            # ── Load data ────────────────────────────────────────────────────────────
            data_path = pathlib.Path(__file__).parent.parent / "datasets" / "credit_card_fraud.csv"
            df = pd.read_csv(data_path, comment="#")

            feature_cols = [c for c in df.columns if c not in ["Class"]]
            X = df[feature_cols].values
            y = df["Class"].values

            # ── Resample BEFORE split ─────────────────────────────────────────────
            # Apply {resampler_name} to handle class imbalance
            {resampler_var} = {resampler_init}
            X_res, y_res = {resampler_var}.fit_resample(X, y)

            # ── Train / test split ────────────────────────────────────────────────
            X_train, X_test, y_train, y_test = train_test_split(
                X_res, y_res, test_size=0.2, random_state=42, stratify=y_res
            )

            # ── Scale features ────────────────────────────────────────────────────
            scaler = StandardScaler()
            X_train = scaler.fit_transform(X_train)
            X_test = scaler.transform(X_test)

            # ── Model ─────────────────────────────────────────────────────────────
            clf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
            clf.fit(X_train, y_train)

            y_proba = clf.predict_proba(X_test)[:, 1]
            auc = roc_auc_score(y_test, y_proba)
            ap = average_precision_score(y_test, y_proba)

            # ── Save results ──────────────────────────────────────────────────────
            out_dir = pathlib.Path(__file__).parent
            results = {{
                "n_original": int(len(df)),
                "n_resampled": int(len(X_res)),
                "n_train": int(len(X_train)),
                "n_test": int(len(X_test)),
                "auc": round(float(auc), 4),
                "average_precision": round(float(ap), 4),
                "resampler": "{resampler_name}",
            }}
            (out_dir / "results.json").write_text(
                json.dumps(results, indent=2), encoding="utf-8"
            )

            # ── Save report ───────────────────────────────────────────────────────
            report = f\"\"\"# Fraud Detection Pipeline Report

            ## Dataset
            - Source: credit_card_fraud
            - Original rows: {{len(df)}}
            - After {resampler_name}: {{len(X_res)}}

            ## Model Performance
            - AUC-ROC: {{auc:.4f}}
            - Average Precision: {{ap:.4f}}

            ## Method
            Applied {resampler_name} to address class imbalance, then trained a
            Random Forest classifier.
            \"\"\"
            (out_dir / "report.md").write_text(report, encoding="utf-8")

            print(f"Original rows   : {{len(df)}}")
            print(f"After resample  : {{len(X_res)}}")
            print(f"Train size      : {{len(X_train)}}")
            print(f"Test size       : {{len(X_test)}}")
            print(f"AUC-ROC         : {{auc:.4f}}")
            print(f"Avg Precision   : {{ap:.4f}}")
            print("Saved results.json and report.md")
        """)

    # ------------------------------------------------------------------
    # check_solution.py
    # ------------------------------------------------------------------

    def _make_check_solution(self, v: dict) -> str:
        resampler_name = v["resampler_name"]
        resampler_var = v["resampler_var"]
        expected_auc_max = v["expected_auc_max"]

        checks = [
            {
                "id": "C1",
                "description": "Resampling called AFTER train_test_split in analysis.py",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import pathlib, re
                    src = (pathlib.Path(workspace_dir) / "analysis.py").read_text(encoding="utf-8")
                    lines = src.splitlines()
                    # Find line indices of train_test_split and fit_resample
                    split_idx = next((i for i, l in enumerate(lines) if "train_test_split" in l), None)
                    resample_idx = next((i for i, l in enumerate(lines) if "fit_resample" in l), None)
                    if split_idx is None:
                        passed = False
                        detail = "train_test_split not found in analysis.py"
                    elif resample_idx is None:
                        passed = False
                        detail = "fit_resample not found in analysis.py"
                    else:
                        # Resampling must come AFTER split (higher line index)
                        passed = resample_idx > split_idx
                        detail = f"split at line {{split_idx}}, resample at line {{resample_idx}}"
                """),
            },
            {
                "id": "C2",
                "description": "results.json exists with 'auc' key",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    rpath = pathlib.Path(workspace_dir) / "results.json"
                    if not rpath.exists():
                        passed = False
                        detail = "results.json not found"
                    else:
                        data = json.loads(rpath.read_text(encoding="utf-8"))
                        passed = "auc" in data
                        detail = f"keys present: {list(data.keys())}"
                """),
            },
            {
                "id": "C3",
                "description": f"AUC in results.json <= {expected_auc_max} (leakage removed, realistic result)",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import json, pathlib
                    rpath = pathlib.Path(workspace_dir) / "results.json"
                    if not rpath.exists():
                        passed = False
                        detail = "results.json not found"
                    else:
                        data = json.loads(rpath.read_text(encoding="utf-8"))
                        auc = data.get("auc", 1.0)
                        passed = float(auc) <= {expected_auc_max}
                        detail = f"auc={{auc}} (need <= {expected_auc_max})"
                """),
            },
            {
                "id": "C4",
                "description": "results.json contains 'n_train' and 'n_test' keys",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    rpath = pathlib.Path(workspace_dir) / "results.json"
                    if not rpath.exists():
                        passed = False
                        detail = "results.json not found"
                    else:
                        data = json.loads(rpath.read_text(encoding="utf-8"))
                        passed = "n_train" in data and "n_test" in data
                        detail = f"keys present: {list(data.keys())}"
                """),
            },
            {
                "id": "C5",
                "description": "report.md mentions leakage/contamination/oversampling order",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    rpath = pathlib.Path(workspace_dir) / "report.md"
                    if not rpath.exists():
                        passed = False
                        detail = "report.md not found"
                    else:
                        content = rpath.read_text(encoding="utf-8").lower()
                        keywords = ["leakage", "leak", "contamination", "before split",
                                    "after split", "train only", "training set only"]
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
                "timeout": 180,
            },
        ]

        return self.make_check_solution(checks)

    # ------------------------------------------------------------------
    # spec.md
    # ------------------------------------------------------------------

    def _make_spec(self, v: dict) -> str:
        resampler_name = v["resampler_name"]
        resampler_var = v["resampler_var"]
        bias_desc = v["bias_description"]
        fix_desc = v["fix_description"]
        inflated_auc = v["inflated_auc"]
        expected_auc_max = v["expected_auc_max"]

        return textwrap.dedent(f"""\
            # RDS13: SMOTE Data Leakage in Fraud Detection

            ## Overview

            The workspace contains `analysis.py`, a fraud detection pipeline using the
            `credit_card_fraud` dataset. The script trains a Random Forest classifier
            with {resampler_name} oversampling and reports AUC-ROC.
            It runs without errors and produces `results.json` and `report.md`.

            **However, the pipeline contains a data leakage flaw** — {resampler_name}
            is applied BEFORE the train/test split, causing the test set to be
            contaminated with synthetic samples derived from real test points.

            ## The Flaw

            ### {resampler_name} Applied Before Split

            {bias_desc}

            ### Quantitative Impact

            | Condition | AUC-ROC |
            |---|---|
            | Current (flawed — leakage) | ~{inflated_auc:.3f} |
            | After fix (correct) | ~0.95 |

            The inflated AUC of ~{inflated_auc:.3f} will never replicate in production,
            making the model appear far more capable than it actually is.

            ## Required Fix

            {fix_desc}

            ### Specific Changes to `analysis.py`

            1. **Move `train_test_split`** to occur BEFORE `{resampler_var}.fit_resample(...)`.
            2. **Apply resampling only to training data**:
               ```python
               X_train_res, y_train_res = {resampler_var}.fit_resample(X_train, y_train)
               ```
            3. **Train** on `X_train_res, y_train_res`.
            4. **Evaluate** on the original (unmodified) `X_test, y_test`.
            5. Re-run so `results.json` reflects the corrected AUC (should be ≤ {expected_auc_max}).
            6. Update `report.md` to acknowledge the leakage issue and explain the fix.

            ## Deliverables

            - Fixed `analysis.py` (resampling after split, only on train)
            - `results.json` with `auc` <= {expected_auc_max} and `n_train`/`n_test` keys
            - `report.md` that mentions data leakage and the correction

            ## Grading Rubric

            | Check | Description |
            |---|---|
            | C1 | `fit_resample` called after `train_test_split` in `analysis.py` |
            | C2 | `results.json` contains `auc` key |
            | C3 | AUC in `results.json` <= {expected_auc_max} |
            | C4 | `results.json` contains `n_train` and `n_test` keys |
            | C5 | `report.md` mentions data leakage |
            | C6 | `analysis.py` runs without error |
        """)

    # ------------------------------------------------------------------
    # brief.md
    # ------------------------------------------------------------------

    def _make_brief(self, v: dict) -> str:
        return textwrap.dedent("""\
            # RDS13: Fraud Detection Pipeline Review

            ## Task

            Review and validate the existing analysis in `analysis.py` for methodological issues.

            The script analyses the `credit_card_fraud` dataset to build a fraud
            detection classifier. It currently runs without error and produces
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
