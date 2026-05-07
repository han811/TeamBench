"""
Parameterized generator for RDS19: Lending Club Default Prediction (Archetype 5 — Discovery).

Clean task: "Build a default prediction model using the loan dataset."
The spec does NOT mention data quality issues. The executor must discover
and handle them during implementation.

Hidden issues injected per seed:
  Seed 0: emp_length as messy strings ("10+ years"), 3 outlier annual_inc rows (9999999),
           "debt_consoldation" typo in purpose column
  Seed 1: different emp_length noise pattern ("n/a" entries), extreme dti outliers,
           "other" / "Other" capitalization inconsistency in purpose
  Seed 2: mix of seed-0 and seed-1 patterns with added loan_status leakage risk
           (total_pymnt highly correlated with default_ind — executor should flag or exclude)

Rubric checks (8):
  C1: analysis.py runs without error
  C2: emp_length numeric conversion handled (no raw string in model features)
  C3: outliers in annual_inc addressed (documented or removed)
  C4: purpose column cleaned / duplicates merged
  C5: model produces a valid AUC score (> 0.5)
  C6: results.json exists with required fields
  C7: data loaded correctly (row count check)
  C8: report.md discusses at least one data quality issue discovered
"""
from __future__ import annotations

import csv
import io
import textwrap

from generators.base import GeneratedTask
from generators.primitives import SeededRandom
from generators.real_data_base import DiscoveryGenerator

# Columns relevant to default prediction (drop leaky payment-history cols for seed 0/1)
_KEEP_COLUMNS = [
    "loan_amnt",
    "term",
    "int_rate",
    "installment",
    "grade",
    "emp_length",
    "home_ownership",
    "annual_inc",
    "verification_status",
    "purpose",
    "dti",
    "delinq_2yrs",
    "fico_range_low",
    "fico_range_high",
    "open_acc",
    "revol_util",
    "default_ind",
]

_EMP_LENGTH_VALUES = [
    "< 1 year", "1 year", "2 years", "3 years", "4 years",
    "5 years", "6 years", "7 years", "8 years", "9 years", "10+ years",
]

_PURPOSES = [
    "debt_consolidation", "credit_card", "home_improvement",
    "other", "major_purchase", "medical", "small_business",
    "car", "vacation", "moving", "house",
]

_VARIANTS = [
    {
        "seed_offset": 0,
        "issues": [
            "emp_length contains mixed formats including '10+ years' as a string",
            "3 rows have annual_inc = 9999999 (sentinel outlier value)",
            "purpose column contains 'debt_consoldation' (misspelling of debt_consolidation)",
        ],
        "emp_noise": "ten_plus_string",   # "10+ years" needs parsing
        "inc_outlier_sentinel": 9999999,
        "purpose_typo": "debt_consoldation",
        "leakage_cols": [],
    },
    {
        "seed_offset": 10,
        "issues": [
            "emp_length contains 'n/a' entries that must be handled",
            "dti has 4 extreme outlier rows (> 200)",
            "purpose column has capitalisation inconsistency ('Other' vs 'other')",
        ],
        "emp_noise": "na_entries",
        "inc_outlier_sentinel": None,
        "purpose_typo": None,
        "leakage_cols": [],
    },
    {
        "seed_offset": 20,
        "issues": [
            "emp_length mixes '10+ years' strings and 'n/a' entries",
            "annual_inc has sentinel outlier value 9999999",
            "purpose column has both typo ('debt_consoldation') and case inconsistency",
        ],
        "emp_noise": "both",
        "inc_outlier_sentinel": 9999999,
        "purpose_typo": "debt_consoldation",
        "leakage_cols": [],
    },
]


class Generator(DiscoveryGenerator):
    task_id = "RDS19_lending_quality"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]

    dataset_name = "lending_club"
    dataset_license = "CC BY 4.0 (synthetic placeholder)"
    dataset_source = "Kaggle / Lending Club"

    def generate(self, seed: int) -> GeneratedTask:
        variant = _VARIANTS[seed % len(_VARIANTS)]
        rng = SeededRandom(seed + variant["seed_offset"])

        rows = self.load_dataset()
        rows = self.subsample(rows, seed=seed + 100, frac=0.04)  # ~400 rows
        rows = self.select_columns(rows, _KEEP_COLUMNS)

        # Inject hidden quality issues
        rows = self._inject_issues(rows, variant, rng)

        n_rows = len(rows)
        data_csv = self.rows_to_csv(rows, _KEEP_COLUMNS)

        check_py = self._make_check_solution(variant, n_rows)
        requirements_txt = self._make_requirements()
        task_yaml = self.make_task_yaml()

        workspace_files = {
            "data/loans.csv": data_csv,
            "requirements.txt": requirements_txt,
            "check_solution.py": check_py,
            "task.yaml": task_yaml,
        }

        expected = {
            "issues": variant["issues"],
            "n_rows": n_rows,
            "columns": _KEEP_COLUMNS,
            "required_output_files": ["analysis.py", "results.json", "report.md"],
        }

        spec_md = self._make_spec(n_rows)
        brief_md = self._make_brief()

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _inject_issues(self, rows: list[dict], variant: dict, rng: SeededRandom) -> list[dict]:
        result = [dict(r) for r in rows]
        n = len(result)

        emp_noise = variant["emp_noise"]
        purpose_typo = variant["purpose_typo"]
        inc_sentinel = variant["inc_outlier_sentinel"]

        # Inject emp_length noise
        noisy_indices = rng.sample(range(n), min(15, n // 20))
        for i in noisy_indices:
            if emp_noise in ("ten_plus_string", "both"):
                result[i]["emp_length"] = "10+ years"
            elif emp_noise == "na_entries":
                result[i]["emp_length"] = "n/a"

        if emp_noise == "both":
            na_indices = rng.sample(range(n), min(10, n // 25))
            for i in na_indices:
                result[i]["emp_length"] = "n/a"

        # Inject annual_inc outlier sentinel
        if inc_sentinel is not None:
            outlier_indices = rng.sample(range(n), 3)
            for i in outlier_indices:
                result[i]["annual_inc"] = str(inc_sentinel)

        # Inject dti outliers for seed 1
        if emp_noise == "na_entries":
            dti_indices = rng.sample(range(n), 4)
            for i in dti_indices:
                result[i]["dti"] = str(rng.randint(250, 400))

        # Inject purpose typo / casing issue
        if purpose_typo is not None:
            typo_indices = rng.sample(range(n), min(8, n // 30))
            for i in typo_indices:
                result[i]["purpose"] = purpose_typo

        if emp_noise in ("na_entries", "both"):
            # Capitalisation inconsistency
            cap_indices = rng.sample(range(n), min(6, n // 40))
            for i in cap_indices:
                if result[i]["purpose"] == "other":
                    result[i]["purpose"] = "Other"

        return result

    def _make_requirements(self) -> str:
        return (
            "pandas>=1.5\n"
            "numpy>=1.23\n"
            "scikit-learn>=1.1\n"
            "scipy>=1.9\n"
        )

    def _make_spec(self, n_rows: int) -> str:
        return textwrap.dedent(f"""\
            # RDS19: Lending Default Prediction

            ## Task
            Build a binary classification model to predict loan default using the provided
            Lending Club loan dataset.

            ## Dataset
            - File: `data/loans.csv`
            - Rows: {n_rows}
            - Target column: `default_ind` (1 = defaulted, 0 = fully paid)
            - Features include: loan amount, term, interest rate, grade, employment length,
              annual income, purpose, debt-to-income ratio, FICO scores, and delinquency history

            ## Your Task
            1. Load and explore `data/loans.csv`
            2. Prepare features for modelling (handle types, missing values, encoding)
            3. Train a classification model (logistic regression, random forest, or gradient boosting)
            4. Evaluate using AUC-ROC on a held-out test set (20% split, random_state=42)
            5. Save results and a brief report

            ## Required Deliverables

            ### 1. `analysis.py`
            A Python script that:
            - Loads `data/loans.csv`
            - Prepares features (handle types, missing values, categorical encoding)
            - Trains a classifier and evaluates on a test split
            - Saves `results.json` and `report.md`

            ### 2. `results.json`
            Must contain at minimum:
            ```json
            {{
              "model": "<model name>",
              "auc_roc": <float>,
              "accuracy": <float>,
              "n_train": <int>,
              "n_test": <int>
            }}
            ```

            ### 3. `report.md`
            A brief (200–400 word) report covering:
            - Feature engineering decisions
            - Any data quality issues discovered and how you handled them
            - Model performance summary

            ## Grading Criteria
            1. `analysis.py` runs without error
            2. `emp_length` column is converted to numeric (not used as raw string)
            3. Outliers in `annual_inc` are addressed
            4. `purpose` column is cleaned (consistent values)
            5. Model achieves AUC > 0.5 on the test set
            6. `results.json` contains required fields
            7. Data is loaded correctly (expected row count)
            8. `report.md` discusses at least one data quality issue
        """)

    def _make_brief(self) -> str:
        return textwrap.dedent("""\
            # RDS19: Lending Default Prediction (Brief)

            Build a default prediction model using `data/loans.csv`.

            Produce:
            - `analysis.py` — data prep + model training + evaluation script
            - `results.json` — AUC and accuracy on held-out test set
            - `report.md` — feature engineering decisions and findings
        """)

    def _make_check_solution(self, variant: dict, n_rows: int) -> str:
        checks = [
            {
                "id": "C1",
                "description": "analysis.py runs without error",
                "type": "script_runs",
                "path": "analysis.py",
                "timeout": 180,
            },
            {
                "id": "C2",
                "description": "emp_length converted to numeric (not used as raw string in model)",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib, re
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    numeric_terms = [
                        "int(", "float(", "replace", "extract", "str.replace",
                        "to_numeric", "astype", "parse", "map", "apply",
                        "strip", "split", "years", "numeric",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        # check emp_length is mentioned AND some numeric conversion nearby
                        has_emp = "emp_length" in content
                        has_conv = any(t in content for t in numeric_terms)
                        passed = has_emp and has_conv
                        detail = f"emp_length mentioned={has_emp}, conversion term found={has_conv}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C3",
                "description": "Outliers in annual_inc addressed (clipping, removal, or log transform)",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    outlier_terms = [
                        "clip", "outlier", "quantile", "percentile", "log",
                        "9999999", "cap", "winsoriz", "iqr", "zscore", "z_score",
                        "annual_inc",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        has_inc = "annual_inc" in content
                        found_terms = [t for t in outlier_terms if t in content]
                        passed = has_inc and len(found_terms) >= 2
                        detail = f"annual_inc mentioned={has_inc}, terms={found_terms}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C4",
                "description": "purpose column cleaned (consistent values, typo/case handled)",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    clean_terms = [
                        "lower", "strip", "replace", "map", "str.", "clean",
                        "purpose", "consolidat", "normalize", "standardize",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        has_purpose = "purpose" in content
                        found = [t for t in clean_terms if t in content]
                        passed = has_purpose and len(found) >= 2
                        detail = f"purpose mentioned={has_purpose}, clean terms={found}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C5",
                "description": "Model AUC > 0.5 reported in results.json",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    if p.exists():
                        try:
                            d = json.loads(p.read_text(encoding="utf-8"))
                            auc = d.get("auc_roc", d.get("auc", d.get("roc_auc", None)))
                            if auc is not None:
                                passed = float(auc) > 0.5
                                detail = f"auc_roc={auc}"
                            else:
                                detail = "auc_roc key not found in results.json"
                        except Exception as e:
                            detail = str(e)
                    else:
                        detail = "results.json not found"
                """),
            },
            {
                "id": "C6",
                "description": "results.json contains required fields (model, auc_roc, accuracy)",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    required = ["model", "auc_roc", "accuracy"]
                    alt_keys = {"auc_roc": ["auc", "roc_auc", "auc_score"]}
                    if p.exists():
                        try:
                            d = json.loads(p.read_text(encoding="utf-8"))
                            missing = []
                            for f in required:
                                alts = alt_keys.get(f, [])
                                if f not in d and not any(a in d for a in alts):
                                    missing.append(f)
                            passed = len(missing) == 0
                            detail = f"missing={missing}" if missing else "all fields present"
                        except Exception as e:
                            detail = str(e)
                    else:
                        detail = "results.json not found"
                """),
            },
            {
                "id": "C7",
                "description": f"Data loaded correctly (expected ~{n_rows} rows)",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import pathlib, csv
                    p = pathlib.Path(workspace_dir) / "data" / "loans.csv"
                    passed = False
                    detail = ""
                    expected_rows = {n_rows}
                    if p.exists():
                        with open(p, newline="", encoding="utf-8") as fh:
                            actual = sum(1 for _ in csv.reader(fh)) - 1
                        passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.01))
                        detail = f"actual={{actual}}, expected={{expected_rows}}"
                    else:
                        detail = "data/loans.csv not found"
                """),
            },
            {
                "id": "C8",
                "description": "report.md discusses at least one data quality issue",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "report.md"
                    passed = False
                    detail = ""
                    quality_terms = [
                        "missing", "outlier", "null", "nan", "inconsistent",
                        "clean", "quality", "typo", "encoding", "parsing",
                        "emp_length", "annual_inc", "purpose", "duplicate",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in quality_terms if t in content]
                        passed = len(found) >= 2
                        detail = f"quality terms found: {found}"
                    else:
                        detail = "report.md not found"
                """),
            },
        ]
        return self.make_check_solution(checks)
