"""
Parameterized generator for RDS22: Stack Overflow Developer Survey Analysis
(Archetype 5 — Discovery).

Clean task: "Analyze developer satisfaction predictors."
The spec does NOT mention data quality issues. The executor must discover
and handle them during implementation.

Hidden issues injected per seed:
  Seed 0: JobSat satisfaction scale shift (some responses use 1-5, others 1-7),
           CompTotal has $1 and $10M+ outlier rows, YearsCode and YearsCodePro
           meaning conflated (some rows have YearsCodePro > YearsCode)
  Seed 1: Different satisfaction column scale issue (subset has 0-indexed vs 1-indexed),
           extreme salary outliers in different range, YearsCode contains "Less than 1 year"
           and "More than 50 years" as strings that need parsing
  Seed 2: Combined scale issue + salary outliers + coding years string parsing

Rubric checks (8):
  C1: analysis.py runs without error
  C2: Likert scale harmonized (scale difference handled)
  C3: Salary / compensation outliers handled
  C4: YearsCode / YearsCodePro relationship checked or string values parsed
  C5: Analysis identifies at least one predictor of satisfaction
  C6: results.json contains required fields
  C7: data loaded correctly
  C8: report.md discusses a data quality issue discovered
"""
from __future__ import annotations

import textwrap

from generators.base import GeneratedTask
from generators.primitives import SeededRandom
from generators.real_data_base import DiscoveryGenerator

_KEEP_COLUMNS = [
    "ResponseId",
    "Employment",
    "EdLevel",
    "YearsCode",
    "YearsCodePro",
    "DevType",
    "OrgSize",
    "CompTotal",
    "ConvertedCompYearly",
    "LanguageHaveWorkedWith",
    "JobSat",
]

_VARIANTS = [
    {
        "seed_offset": 0,
        "scale_issue": "5to7",  # subset uses 1-5 scale instead of 1-7
        "n_scale_affected": 80,
        "salary_outlier_low": 1,
        "salary_outlier_high": 15_000_000,
        "n_salary_outliers": 6,
        "years_issue": "logical_inconsistency",  # YearsCodePro > YearsCode
        "n_years_bad": 15,
        "description": "satisfaction scale shift (5-pt vs 7-pt), salary outliers, YearsCodePro > YearsCode",
    },
    {
        "seed_offset": 10,
        "scale_issue": "zero_indexed",  # subset uses 0-6 instead of 1-7
        "n_scale_affected": 60,
        "salary_outlier_low": 2,
        "salary_outlier_high": 8_000_000,
        "n_salary_outliers": 8,
        "years_issue": "string_values",  # "Less than 1 year", "More than 50 years"
        "n_years_bad": 20,
        "description": "0-indexed vs 1-indexed satisfaction, extreme salary outliers, string YearsCode",
    },
    {
        "seed_offset": 20,
        "scale_issue": "5to7",
        "n_scale_affected": 70,
        "salary_outlier_low": 1,
        "salary_outlier_high": 12_000_000,
        "n_salary_outliers": 7,
        "years_issue": "both",  # both logical inconsistency and string values
        "n_years_bad": 20,
        "description": "combined: scale shift, salary outliers, mixed YearsCode issues",
    },
]

_JOB_SAT_LABELS_7 = [
    "Very dissatisfied", "Dissatisfied", "Slightly dissatisfied",
    "Neither satisfied nor dissatisfied",
    "Slightly satisfied", "Satisfied", "Very satisfied",
]
_JOB_SAT_LABELS_5 = [
    "Very dissatisfied", "Dissatisfied",
    "Neither satisfied nor dissatisfied",
    "Satisfied", "Very satisfied",
]


class Generator(DiscoveryGenerator):
    task_id = "RDS22_survey_quality"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]

    dataset_name = "stackoverflow"
    dataset_license = "ODbL 1.0"
    dataset_source = "Stack Overflow Developer Survey"

    def generate(self, seed: int) -> GeneratedTask:
        variant = _VARIANTS[seed % len(_VARIANTS)]
        rng = SeededRandom(seed + variant["seed_offset"])

        rows = self.load_dataset()
        rows = self.subsample(rows, seed=seed + 400, frac=0.08)  # ~500 rows
        rows = self.select_columns(rows, _KEEP_COLUMNS)

        rows = self._inject_issues(rows, variant, rng)

        n_rows = len(rows)
        data_csv = self.rows_to_csv(rows, _KEEP_COLUMNS)

        check_py = self._make_check_solution(variant, n_rows)
        requirements_txt = (
            "pandas>=1.5\nnumpy>=1.23\nscikit-learn>=1.1\nscipy>=1.9\n"
        )
        task_yaml = self.make_task_yaml()

        workspace_files = {
            "data/survey_responses.csv": data_csv,
            "requirements.txt": requirements_txt,
            "check_solution.py": check_py,
            "task.yaml": task_yaml,
        }

        expected = {
            "issues": variant["description"],
            "n_rows": n_rows,
            "required_output_files": ["analysis.py", "results.json", "report.md"],
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._make_spec(n_rows),
            brief_md=self._make_brief(),
            expected=expected,
            workspace_files=workspace_files,
        )

    def _inject_issues(self, rows: list[dict], variant: dict, rng: SeededRandom) -> list[dict]:
        result = [dict(r) for r in rows]
        n = len(result)

        # Satisfaction scale issue
        scale_issue = variant["scale_issue"]
        n_affected = min(variant["n_scale_affected"], n // 4)
        scale_indices = rng.sample(range(n), n_affected)

        for i in scale_indices:
            current = result[i].get("JobSat", "")
            if scale_issue == "5to7":
                # Replace 7-point label with 5-point label
                if current in _JOB_SAT_LABELS_7:
                    idx = _JOB_SAT_LABELS_7.index(current)
                    # Map to 5-point scale (compress middle)
                    mapped_idx = min(idx * 4 // 6, 4)
                    result[i]["JobSat"] = _JOB_SAT_LABELS_5[mapped_idx]
            elif scale_issue == "zero_indexed":
                # Use numeric 0-6 instead of labels
                if current in _JOB_SAT_LABELS_7:
                    idx = _JOB_SAT_LABELS_7.index(current)
                    result[i]["JobSat"] = str(idx)  # 0-indexed

        # Salary outliers
        all_indices = list(range(n))
        rng.shuffle(all_indices)
        outlier_indices = all_indices[: variant["n_salary_outliers"]]
        low_val = str(variant["salary_outlier_low"])
        high_val = str(variant["salary_outlier_high"])
        for k, i in enumerate(outlier_indices):
            result[i]["CompTotal"] = low_val if k % 2 == 0 else high_val

        # YearsCode / YearsCodePro issues
        years_issue = variant["years_issue"]
        n_bad = min(variant["n_years_bad"], n // 15)
        years_indices = rng.sample(range(n), n_bad)

        for i in years_indices:
            if years_issue == "logical_inconsistency" or years_issue == "both":
                # Make YearsCodePro > YearsCode (logically impossible)
                try:
                    yc = int(float(result[i].get("YearsCode", "5") or "5"))
                    result[i]["YearsCodePro"] = str(yc + rng.randint(5, 15))
                except (ValueError, TypeError):
                    result[i]["YearsCodePro"] = "25"

            if years_issue == "string_values" or years_issue == "both":
                # Inject text strings that need special parsing
                choices = ["Less than 1 year", "More than 50 years"]
                result[i]["YearsCode"] = rng.choice(choices)

        return result

    def _make_spec(self, n_rows: int) -> str:
        return textwrap.dedent(f"""\
            # RDS22: Developer Satisfaction Predictors

            ## Task
            Analyze the Stack Overflow Developer Survey to identify key predictors
            of job satisfaction among software developers.

            ## Dataset
            - File: `data/survey_responses.csv`
            - Rows: {n_rows}
            - Target: `JobSat` — developer job satisfaction
            - Features include: employment type, education level, years of coding experience,
              developer type, organization size, compensation, programming languages used

            ## Your Task
            1. Load and explore `data/survey_responses.csv`
            2. Prepare the satisfaction target and features for analysis
            3. Identify the strongest predictors of job satisfaction
               (use regression, correlation analysis, or a classification model)
            4. Quantify the relationship between compensation and satisfaction
            5. Save results and a report

            ## Required Deliverables

            ### 1. `analysis.py`
            A Python script that:
            - Loads the survey data
            - Handles data types, encoding, and missing values
            - Identifies top predictors of job satisfaction
            - Saves `results.json` and `report.md`

            ### 2. `results.json`
            Must contain at minimum:
            ```json
            {{
              "top_predictors": [<str>, ...],
              "compensation_correlation": <float>,
              "n_valid_responses": <int>
            }}
            ```

            ### 3. `report.md`
            A brief (300–500 word) report covering:
            - Key predictors of developer satisfaction
            - Relationship between compensation and satisfaction
            - Any data quality issues discovered and how you handled them
            - Limitations

            ## Grading Criteria
            1. `analysis.py` runs without error
            2. JobSat scale is harmonized (consistent numeric scale)
            3. Extreme compensation outliers are handled
            4. YearsCode / YearsCodePro values are validated and parsed correctly
            5. At least one predictor of satisfaction is identified
            6. `results.json` contains required fields
            7. Data loaded correctly (expected row count)
            8. `report.md` discusses a data quality issue
        """)

    def _make_brief(self) -> str:
        return textwrap.dedent("""\
            # RDS22: Developer Satisfaction Predictors (Brief)

            Analyze developer job satisfaction using `data/survey_responses.csv`.

            Produce:
            - `analysis.py` — predictor analysis script
            - `results.json` — top predictors and compensation correlation
            - `report.md` — findings and data quality notes
        """)

    def _make_check_solution(self, variant: dict, n_rows: int) -> str:
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
                "description": "JobSat scale harmonized (consistent numeric encoding)",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    scale_terms = [
                        "jobsat", "satisfaction", "map", "replace", "encode",
                        "numeric", "ordinal", "scale", "harmonize", "normalize",
                        "convert", "label", "likert",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        has_jobsat = "jobsat" in content
                        found = [t for t in scale_terms if t in content]
                        passed = has_jobsat and len(found) >= 3
                        detail = f"jobsat mentioned={has_jobsat}, terms={found}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C3",
                "description": "Extreme compensation outliers handled",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    outlier_terms = [
                        "outlier", "clip", "quantile", "percentile", "cap",
                        "winsoriz", "compt", "salary", "compTotal", "log",
                        "iqr", "zscore", "z_score", "filter", "threshold",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        has_comp = "comptotal" in content or "comp" in content or "salary" in content
                        found = [t for t in outlier_terms if t in content]
                        passed = has_comp and len(found) >= 2
                        detail = f"comp mentioned={has_comp}, terms={found}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C4",
                "description": "YearsCode / YearsCodePro parsed correctly (strings handled, logical check)",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    years_terms = [
                        "yearscode", "years_code", "years_pro", "yrs",
                        "less than", "more than", "parse", "replace",
                        "extract", "numeric", "int(", "float(",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        has_yc = "yearscode" in content
                        found = [t for t in years_terms if t in content]
                        passed = has_yc and len(found) >= 2
                        detail = f"yearscode mentioned={has_yc}, terms={found}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C5",
                "description": "At least one predictor of satisfaction identified in results.json",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    if p.exists():
                        try:
                            d = json.loads(p.read_text(encoding="utf-8"))
                            preds = d.get("top_predictors", d.get("predictors", d.get("features", [])))
                            passed = isinstance(preds, list) and len(preds) >= 1
                            detail = f"top_predictors={preds}"
                        except Exception as e:
                            detail = str(e)
                    else:
                        detail = "results.json not found"
                """),
            },
            {
                "id": "C6",
                "description": "results.json contains required fields",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    required = ["top_predictors", "compensation_correlation", "n_valid_responses"]
                    alt_keys = {
                        "top_predictors": ["predictors", "features", "important_features"],
                        "compensation_correlation": ["comp_corr", "salary_correlation", "comp_correlation"],
                        "n_valid_responses": ["n_valid", "valid_n", "n_responses"],
                    }
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
                    p = pathlib.Path(workspace_dir) / "data" / "survey_responses.csv"
                    passed = False
                    detail = ""
                    expected_rows = {n_rows}
                    if p.exists():
                        with open(p, newline="", encoding="utf-8") as fh:
                            actual = sum(1 for _ in csv.reader(fh)) - 1
                        passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.01))
                        detail = f"actual={{actual}}, expected={{expected_rows}}"
                    else:
                        detail = "data/survey_responses.csv not found"
                """),
            },
            {
                "id": "C8",
                "description": "report.md discusses a data quality issue discovered",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "report.md"
                    passed = False
                    detail = ""
                    quality_terms = [
                        "outlier", "scale", "inconsisten", "missing", "clean",
                        "quality", "parse", "encoding", "salary", "compensation",
                        "yearscode", "satisfaction", "harmonize", "anomal",
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
