"""
Parameterized generator for RDS23: Ames Housing Price Prediction (Archetype 5 — Discovery).

Clean task: "Build a price prediction model."
The spec does NOT mention data quality issues. The executor must discover
and handle them during implementation.

Hidden issues injected per seed:
  Seed 0: YearBuilt column injected with typo value 2207 (should be 2007),
           4 rows with LotArea > 100000 sqft (extreme outliers),
           Utilities column is constant (all "AllPub") — zero variance predictor
  Seed 1: YearRemodAdd has implausible values < YearBuilt,
           GrLivArea has 3 extreme outliers (> 5000 sqft),
           OverallQual has 2 rows with value 0 (invalid — scale is 1-10)
  Seed 2: Combined — YearBuilt typo, LotArea outliers, GrLivArea outliers

Note: ames_housing does NOT have GarageYrBlt column, so we use YearBuilt typo instead.

Rubric checks (8):
  C1: analysis.py runs without error
  C2: Year typo or implausible year corrected/handled
  C3: Area/size outliers addressed
  C4: Zero-variance or constant features removed
  C5: Model achieves reasonable RMSE (< $100k or < 50% of mean price)
  C6: results.json contains required fields
  C7: data loaded correctly
  C8: report.md discusses at least one data quality issue
"""
from __future__ import annotations

import textwrap

from generators.base import GeneratedTask
from generators.primitives import SeededRandom
from generators.real_data_base import DiscoveryGenerator

_KEEP_COLUMNS = [
    "Id",
    "LotArea",
    "Neighborhood",
    "BldgType",
    "HouseStyle",
    "OverallQual",
    "OverallCond",
    "YearBuilt",
    "YearRemodAdd",
    "TotalBsmtSF",
    "GrLivArea",
    "FullBath",
    "HalfBath",
    "BedroomAbvGr",
    "KitchenQual",
    "TotRmsAbvGrd",
    "GarageCars",
    "GarageArea",
    "Utilities",
    "SalePrice",
]

_VARIANTS = [
    {
        "seed_offset": 0,
        "year_col": "YearBuilt",
        "year_typo_value": "2207",   # should be 2007
        "year_typo_real": "2007",
        "n_year_typos": 2,
        "area_col": "LotArea",
        "n_area_outliers": 4,
        "area_outlier_range": (120000, 250000),
        "constant_col": "Utilities",   # already all "AllPub" in dataset
        "inject_constant": True,
        "invalid_qual": False,
        "area2_col": None,
        "description": "YearBuilt typo (2207→2007), LotArea outliers, Utilities constant",
    },
    {
        "seed_offset": 10,
        "year_col": "YearRemodAdd",
        "year_typo_value": None,
        "year_before_built": True,   # YearRemodAdd < YearBuilt
        "n_year_typos": 5,
        "area_col": "GrLivArea",
        "n_area_outliers": 3,
        "area_outlier_range": (5500, 8000),
        "constant_col": None,
        "inject_constant": False,
        "invalid_qual": True,   # OverallQual = 0
        "n_invalid_qual": 2,
        "area2_col": None,
        "description": "YearRemodAdd < YearBuilt, GrLivArea extreme outliers, OverallQual=0",
    },
    {
        "seed_offset": 20,
        "year_col": "YearBuilt",
        "year_typo_value": "2207",
        "year_typo_real": "2007",
        "n_year_typos": 2,
        "area_col": "LotArea",
        "n_area_outliers": 4,
        "area_outlier_range": (110000, 200000),
        "constant_col": None,
        "inject_constant": False,
        "invalid_qual": False,
        "area2_col": "GrLivArea",
        "n_area2_outliers": 3,
        "area2_outlier_range": (5000, 7000),
        "description": "YearBuilt typo (2207→2007), LotArea + GrLivArea outliers",
    },
]


class Generator(DiscoveryGenerator):
    task_id = "RDS23_housing_quality"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]

    dataset_name = "ames_housing"
    dataset_license = "Public Domain"
    dataset_source = "Ames Housing Dataset (De Cock, 2011)"

    def generate(self, seed: int) -> GeneratedTask:
        variant = _VARIANTS[seed % len(_VARIANTS)]
        rng = SeededRandom(seed + variant["seed_offset"])

        rows = self.load_dataset()
        rows = self.subsample(rows, seed=seed + 500, frac=0.5)  # ~700 rows
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
            "data/housing.csv": data_csv,
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

        # Year typo injection
        year_col = variant.get("year_col")
        typo_val = variant.get("year_typo_value")
        n_year = variant.get("n_year_typos", 0)

        if typo_val is not None and n_year > 0:
            indices = rng.sample(range(n), min(n_year, n // 50))
            for i in indices:
                result[i][year_col] = typo_val

        # YearRemodAdd < YearBuilt (implausible remodel before construction)
        if variant.get("year_before_built") and n_year > 0:
            indices = rng.sample(range(n), min(n_year, n // 40))
            for i in indices:
                try:
                    yb = int(result[i].get("YearBuilt", "1950") or "1950")
                    result[i]["YearRemodAdd"] = str(yb - rng.randint(5, 20))
                except (ValueError, TypeError):
                    result[i]["YearRemodAdd"] = "1930"

        # Area outliers (primary)
        area_col = variant.get("area_col")
        n_area = variant.get("n_area_outliers", 0)
        area_range = variant.get("area_outlier_range", (100000, 200000))
        if area_col and n_area > 0:
            indices = rng.sample(range(n), min(n_area, n // 50))
            for i in indices:
                result[i][area_col] = str(rng.randint(*area_range))

        # Area outliers (secondary, seed 2)
        area2_col = variant.get("area2_col")
        n_area2 = variant.get("n_area2_outliers", 0)
        area2_range = variant.get("area2_outlier_range", (5000, 7000))
        if area2_col and n_area2 > 0:
            indices = rng.sample(range(n), min(n_area2, n // 50))
            for i in indices:
                result[i][area2_col] = str(rng.randint(*area2_range))

        # Constant feature injection (make Utilities all "AllPub")
        if variant.get("inject_constant"):
            for row in result:
                row["Utilities"] = "AllPub"

        # Invalid OverallQual = 0 injection
        if variant.get("invalid_qual"):
            n_iq = variant.get("n_invalid_qual", 2)
            indices = rng.sample(range(n), min(n_iq, n // 80))
            for i in indices:
                result[i]["OverallQual"] = "0"

        return result

    def _make_spec(self, n_rows: int) -> str:
        return textwrap.dedent(f"""\
            # RDS23: Ames Housing Price Prediction

            ## Task
            Build a regression model to predict residential property sale prices using the
            Ames, Iowa housing dataset.

            ## Dataset
            - File: `data/housing.csv`
            - Rows: {n_rows}
            - Target column: `SalePrice` (USD)
            - Features include: lot area, neighborhood, building type, house style,
              overall quality/condition, year built, year remodeled, basement and living area,
              bathrooms, bedrooms, kitchen quality, garage capacity, utilities

            ## Your Task
            1. Load and explore `data/housing.csv`
            2. Perform feature engineering and data cleaning
            3. Select relevant features and handle categorical variables
            4. Train a regression model to predict `SalePrice`
            5. Evaluate using RMSE and R² on a held-out test set (20% split, random_state=42)
            6. Save results and a report

            ## Required Deliverables

            ### 1. `analysis.py`
            A Python script that:
            - Loads `data/housing.csv`
            - Cleans and engineers features
            - Trains a regression model and evaluates on a test split
            - Saves `results.json` and `report.md`

            ### 2. `results.json`
            Must contain at minimum:
            ```json
            {{
              "model": "<model name>",
              "rmse": <float>,
              "r2": <float>,
              "n_features": <int>,
              "n_train": <int>
            }}
            ```

            ### 3. `report.md`
            A brief (200–400 word) report covering:
            - Feature engineering decisions (which features were most useful)
            - Any data quality issues discovered and how you handled them
            - Model performance summary

            ## Grading Criteria
            1. `analysis.py` runs without error
            2. Implausible year values are corrected or handled
            3. Extreme area outliers (LotArea or GrLivArea) are addressed
            4. Zero-variance or near-constant features are removed from the model
            5. Model RMSE is reasonable (< $100,000 or < 50% of mean SalePrice)
            6. `results.json` contains required fields
            7. Data loaded correctly (expected row count)
            8. `report.md` discusses at least one data quality issue
        """)

    def _make_brief(self) -> str:
        return textwrap.dedent("""\
            # RDS23: Ames Housing Price Prediction (Brief)

            Build a home price prediction model using `data/housing.csv`.

            Produce:
            - `analysis.py` — feature engineering + model training + evaluation
            - `results.json` — RMSE and R² on held-out test set
            - `report.md` — feature decisions and data quality notes
        """)

    def _make_check_solution(self, variant: dict, n_rows: int) -> str:
        year_col = variant.get("year_col", "YearBuilt")
        area_col = variant.get("area_col", "LotArea")
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
                "description": f"Implausible {year_col} values addressed",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    year_terms = [
                        "yearbuilt", "yearremodadd", "year", "2207", "implausible",
                        "typo", "clip", "filter", "range", "valid", "before",
                        "< 1900", "<1900", "> 2023", ">2023", "remod",
                    ]
                    col = "{year_col}".lower()
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        has_col = col in content
                        found = [t for t in year_terms if t in content]
                        passed = has_col and len(found) >= 2
                        detail = f"col mentioned={{has_col}}, year terms={{found}}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C3",
                "description": f"Extreme {area_col} outliers addressed",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    area_terms = [
                        "outlier", "lotarea", "grlivarea", "area", "sqft",
                        "quantile", "percentile", "clip", "filter", "remove",
                        "iqr", "zscore", "z_score", "threshold", "large",
                    ]
                    col = "{area_col}".lower()
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        has_col = col in content
                        found = [t for t in area_terms if t in content]
                        passed = has_col and len(found) >= 2
                        detail = f"col mentioned={{has_col}}, area terms={{found}}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C4",
                "description": "Zero-variance or constant features removed",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    variance_terms = [
                        "variance", "constant", "nunique", "unique", "drop",
                        "utilities", "zero_var", "variancethreshold", "low_variance",
                        "single_value", "std()", ".std", "useless", "remove",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in variance_terms if t in content]
                        passed = len(found) >= 2
                        detail = f"variance terms found: {found}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C5",
                "description": "Model RMSE < $100,000 in results.json",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    if p.exists():
                        try:
                            d = json.loads(p.read_text(encoding="utf-8"))
                            rmse = d.get("rmse", d.get("test_rmse", None))
                            if rmse is not None:
                                passed = 0.0 < float(rmse) < 100_000.0
                                detail = f"rmse={rmse}"
                            else:
                                detail = "rmse key not found"
                        except Exception as e:
                            detail = str(e)
                    else:
                        detail = "results.json not found"
                """),
            },
            {
                "id": "C6",
                "description": "results.json contains required fields (model, rmse, r2)",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    required = ["model", "rmse", "r2"]
                    alt_keys = {
                        "rmse": ["test_rmse", "rmse_score", "root_mean_squared_error"],
                        "r2": ["r2_score", "r_squared", "r_2"],
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
                    p = pathlib.Path(workspace_dir) / "data" / "housing.csv"
                    passed = False
                    detail = ""
                    expected_rows = {n_rows}
                    if p.exists():
                        with open(p, newline="", encoding="utf-8") as fh:
                            actual = sum(1 for _ in csv.reader(fh)) - 1
                        passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.01))
                        detail = f"actual={{actual}}, expected={{expected_rows}}"
                    else:
                        detail = "data/housing.csv not found"
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
                        "outlier", "typo", "year", "area", "constant", "variance",
                        "quality", "clean", "anomal", "invalid", "implausible",
                        "missing", "remove", "filter", "drop",
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
