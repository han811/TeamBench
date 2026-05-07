"""
Parameterized generator for RDS21: WHO Health Indicator Trends (Archetype 5 — Discovery).

Clean task: "Analyze health indicator trends across countries."
The spec does NOT mention data quality issues. The executor must discover
and handle them during implementation.

Hidden issues injected per seed:
  Seed 0: 30% values missing MNAR (poor countries — income_group="Low income" — have
           more missing values), country names inconsistent ("USA" vs "United States"),
           one indicator (life_expectancy) has values divided by 10 for year >= 2015
           (simulates scale change)
  Seed 1: Missing MCAR pattern (random 25% of numeric values), country name
           inconsistencies ("Russian Federation" vs "Russia"), infant_mortality
           scale inversion for a subset (values > 100 entered as rate per 1000 vs per 100)
  Seed 2: Missing MNAR + country name inconsistencies + year-specific scale change
           on under5_mortality (values multiplied by 10 for year < 2005)

Rubric checks (8):
  C1: analysis.py runs without error
  C2: missing data pattern documented or analyzed
  C3: country name inconsistencies addressed
  C4: scale change or outlier in indicators detected/handled
  C5: trend analysis produces output (at least one country/indicator visualized or tabulated)
  C6: results.json contains required fields
  C7: data loaded correctly
  C8: report.md discusses the missing data mechanism
"""
from __future__ import annotations

import textwrap

from generators.base import GeneratedTask
from generators.primitives import SeededRandom
from generators.real_data_base import DiscoveryGenerator

_KEEP_COLUMNS = [
    "country",
    "country_code",
    "year",
    "life_expectancy",
    "infant_mortality",
    "under5_mortality",
    "maternal_mortality",
    "physicians_per_1000",
    "health_expenditure_pct_gdp",
    "income_group",
]

# Country name inconsistencies to inject per variant
_COUNTRY_ALIASES = {
    0: [("United States of America", "USA"), ("United Kingdom", "UK"), ("Russian Federation", "Russia")],
    1: [("Russian Federation", "Russia"), ("Republic of Korea", "South Korea"), ("Democratic Republic of the Congo", "DR Congo")],
    2: [("United States of America", "USA"), ("Viet Nam", "Vietnam"), ("United Kingdom", "UK")],
}

_VARIANTS = [
    {
        "seed_offset": 0,
        "missing_mechanism": "MNAR",
        "missing_desc": "Low-income countries have disproportionately more missing values (MNAR pattern)",
        "scale_change_col": "life_expectancy",
        "scale_change_year": 2015,
        "scale_change_factor": 0.1,  # divided by 10 for year >= 2015
        "scale_change_desc": "life_expectancy values appear 10x smaller for year >= 2015",
        "aliases_key": 0,
    },
    {
        "seed_offset": 10,
        "missing_mechanism": "MCAR",
        "missing_desc": "25% of numeric values are missing at random (MCAR pattern)",
        "scale_change_col": "infant_mortality",
        "scale_change_year": None,
        "scale_change_threshold": 100.0,
        "scale_change_factor": 10.0,  # values > 100 are actually per-1000 (multiply by 10)
        "scale_change_desc": "Some infant_mortality values are anomalously large (> 100, inconsistent units)",
        "aliases_key": 1,
    },
    {
        "seed_offset": 20,
        "missing_mechanism": "MNAR",
        "missing_desc": "Low-income countries have disproportionately more missing values (MNAR pattern)",
        "scale_change_col": "under5_mortality",
        "scale_change_year": 2005,
        "scale_change_factor": 10.0,  # multiplied by 10 for year < 2005
        "scale_change_desc": "under5_mortality values are 10x larger for year < 2005 (unit inconsistency)",
        "aliases_key": 2,
    },
]


class Generator(DiscoveryGenerator):
    task_id = "RDS21_health_missing"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]

    dataset_name = "who_gho"
    dataset_license = "CC BY-NC-SA 3.0 IGO (WHO)"
    dataset_source = "WHO Global Health Observatory"

    def generate(self, seed: int) -> GeneratedTask:
        variant = _VARIANTS[seed % len(_VARIANTS)]
        rng = SeededRandom(seed + variant["seed_offset"])

        rows = self.load_dataset()
        rows = self.subsample(rows, seed=seed + 300, frac=0.35)
        rows = self.select_columns(rows, _KEEP_COLUMNS)

        rows = self._inject_issues(rows, variant, rng)

        n_rows = len(rows)
        data_csv = self.rows_to_csv(rows, _KEEP_COLUMNS)

        check_py = self._make_check_solution(variant, n_rows)
        requirements_txt = (
            "pandas>=1.5\nnumpy>=1.23\nscipy>=1.9\nmatplotlib>=3.5\n"
        )
        task_yaml = self.make_task_yaml()

        workspace_files = {
            "data/health_indicators.csv": data_csv,
            "requirements.txt": requirements_txt,
            "check_solution.py": check_py,
            "task.yaml": task_yaml,
        }

        expected = {
            "missing_mechanism": variant["missing_mechanism"],
            "scale_change_col": variant["scale_change_col"],
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

        numeric_cols = [
            "life_expectancy", "infant_mortality", "under5_mortality",
            "maternal_mortality", "physicians_per_1000", "health_expenditure_pct_gdp",
        ]

        # Inject missing values based on mechanism
        if variant["missing_mechanism"] == "MNAR":
            # Low-income countries get more missing values
            for i, row in enumerate(result):
                if row.get("income_group", "") in ("Low income", "Lower middle income"):
                    for col in numeric_cols:
                        if rng.random() < 0.45:
                            result[i][col] = ""
                else:
                    for col in numeric_cols:
                        if rng.random() < 0.08:
                            result[i][col] = ""
        else:  # MCAR
            for i in range(n):
                for col in numeric_cols:
                    if rng.random() < 0.25:
                        result[i][col] = ""

        # Inject country name aliases
        aliases = _COUNTRY_ALIASES[variant["aliases_key"]]
        for canonical, alias in aliases:
            for i, row in enumerate(result):
                if row.get("country", "") == canonical and rng.random() < 0.5:
                    result[i]["country"] = alias

        # Inject scale change
        scale_col = variant["scale_change_col"]
        scale_year = variant.get("scale_change_year")
        scale_factor = variant.get("scale_change_factor", 1.0)
        threshold = variant.get("scale_change_threshold")

        for i, row in enumerate(result):
            val_str = row.get(scale_col, "")
            if not val_str:
                continue
            try:
                val = float(val_str)
            except (ValueError, TypeError):
                continue

            if scale_year is not None:
                # Year-based scale change
                try:
                    yr = int(row.get("year", 0))
                except (ValueError, TypeError):
                    continue
                if variant["seed_offset"] == 20:  # year < 2005
                    if yr < scale_year:
                        result[i][scale_col] = str(round(val * scale_factor, 2))
                else:  # year >= 2015
                    if yr >= scale_year:
                        result[i][scale_col] = str(round(val * scale_factor, 2))
            elif threshold is not None:
                # Threshold-based: values > threshold are anomalous
                if val > threshold:
                    result[i][scale_col] = str(round(val * scale_factor, 2))

        return result

    def _make_spec(self, n_rows: int) -> str:
        return textwrap.dedent(f"""\
            # RDS21: WHO Health Indicator Trend Analysis

            ## Task
            Analyze health indicator trends across countries using WHO Global Health
            Observatory data, and summarize findings about global health progress.

            ## Dataset
            - File: `data/health_indicators.csv`
            - Rows: {n_rows}
            - Columns: country, country_code, year, life_expectancy, infant_mortality,
              under5_mortality, maternal_mortality, physicians_per_1000,
              health_expenditure_pct_gdp, income_group
            - Years covered: 2000–2020

            ## Your Task
            1. Load and explore `data/health_indicators.csv`
            2. Analyze trends over time for key indicators
            3. Compare patterns across income groups (Low / Middle / High income)
            4. Identify any countries with notable improvements or declines
            5. Save results and a report

            ## Required Deliverables

            ### 1. `analysis.py`
            A Python script that:
            - Loads the health indicators data
            - Handles missing values appropriately
            - Computes trends per indicator and income group
            - Saves `results.json` and `report.md`

            ### 2. `results.json`
            Must contain at minimum:
            ```json
            {{
              "n_countries": <int>,
              "years_covered": [<int>, ...],
              "missing_pct": <float>,
              "top_improvers": [<str>, ...]
            }}
            ```

            ### 3. `report.md`
            A brief (300–500 word) report covering:
            - Key trends observed across indicators and income groups
            - How missing data was handled and any patterns in missingness
            - Notable outliers or anomalies encountered
            - Limitations of the analysis

            ## Grading Criteria
            1. `analysis.py` runs without error
            2. Missing data pattern is analyzed or documented
            3. Country name inconsistencies are addressed
            4. Scale anomalies or outliers in indicators are detected/handled
            5. Trend analysis produces meaningful output
            6. `results.json` contains required fields
            7. Data loaded correctly (expected row count)
            8. `report.md` discusses missing data mechanism
        """)

    def _make_brief(self) -> str:
        return textwrap.dedent("""\
            # RDS21: WHO Health Indicator Analysis (Brief)

            Analyze global health trends using `data/health_indicators.csv`.

            Produce:
            - `analysis.py` — trend analysis script
            - `results.json` — summary statistics and top improvers
            - `report.md` — findings, data quality notes, limitations
        """)

    def _make_check_solution(self, variant: dict, n_rows: int) -> str:
        scale_col = variant["scale_change_col"]
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
                "description": "Missing data pattern analyzed or documented",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    missing_terms = [
                        "missing", "null", "nan", "isna", "isnull",
                        "fillna", "dropna", "impute", "missing_pct",
                        "missing_pattern", "mnar", "mcar", "mar",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in missing_terms if t in content]
                        passed = len(found) >= 2
                        detail = f"missing terms found: {found}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C3",
                "description": "Country name inconsistencies addressed",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    norm_terms = [
                        "replace", "map", "rename", "normalize", "standardize",
                        "country", "strip", "lower", "alias", "merge", "unify",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        has_country = "country" in content
                        found = [t for t in norm_terms if t in content]
                        passed = has_country and len(found) >= 2
                        detail = f"country mentioned={has_country}, norm terms={found}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C4",
                "description": f"Scale anomaly or outlier in {scale_col} detected/handled",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    scale_terms = [
                        "outlier", "scale", "anomal", "range", "quantile",
                        "clip", "filter", "inconsisten", "unit", "zscore",
                        "z_score", "iqr", "threshold", "plausible",
                    ]
                    col = "{scale_col}"
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        has_col = col.lower() in content
                        found = [t for t in scale_terms if t in content]
                        passed = has_col and len(found) >= 2
                        detail = f"col mentioned={{has_col}}, scale terms={{found}}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C5",
                "description": "Trend analysis produces meaningful output (country/indicator trends)",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    rj = pathlib.Path(workspace_dir) / "results.json"
                    rm = pathlib.Path(workspace_dir) / "report.md"
                    passed = False
                    detail = ""
                    if rj.exists() or rm.exists():
                        trend_terms = [
                            "trend", "increase", "decrease", "improve", "decline",
                            "progress", "change", "over time", "year",
                        ]
                        content = ""
                        if rj.exists():
                            content += rj.read_text(encoding="utf-8").lower()
                        if rm.exists():
                            content += rm.read_text(encoding="utf-8").lower()
                        found = [t for t in trend_terms if t in content]
                        passed = len(found) >= 2
                        detail = f"trend terms found: {found}"
                    else:
                        detail = "neither results.json nor report.md found"
                """),
            },
            {
                "id": "C6",
                "description": "results.json contains required fields (n_countries, missing_pct)",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    required = ["n_countries", "missing_pct"]
                    alt_keys = {
                        "missing_pct": ["missing_rate", "pct_missing", "missing_fraction"],
                        "n_countries": ["num_countries", "country_count"],
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
                    p = pathlib.Path(workspace_dir) / "data" / "health_indicators.csv"
                    passed = False
                    detail = ""
                    expected_rows = {n_rows}
                    if p.exists():
                        with open(p, newline="", encoding="utf-8") as fh:
                            actual = sum(1 for _ in csv.reader(fh)) - 1
                        passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.01))
                        detail = f"actual={{actual}}, expected={{expected_rows}}"
                    else:
                        detail = "data/health_indicators.csv not found"
                """),
            },
            {
                "id": "C8",
                "description": "report.md discusses missing data mechanism",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "report.md"
                    passed = False
                    detail = ""
                    missing_terms = [
                        "missing", "null", "nan", "incomplete", "not reported",
                        "mnar", "mcar", "mar", "imputation", "excluded",
                        "pattern", "mechanism", "bias",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in missing_terms if t in content]
                        passed = len(found) >= 2
                        detail = f"missing data terms found: {found}"
                    else:
                        detail = "report.md not found"
                """),
            },
        ]
        return self.make_check_solution(checks)
