"""
Parameterized generator for RDS20: NYC Taxi Fare Prediction (Archetype 5 — Discovery).

Clean task: "Analyze trip patterns and predict fare amount."
The spec does NOT mention data quality issues. The executor must discover
and handle them during implementation.

Hidden issues injected per seed:
  Seed 0: 20 trips with lat/lon coordinates swapped (pickup/dropoff in ocean),
           negative fare_amount rows (refunds), 50 trips with duration > 24 hours
  Seed 1: trips with fare_amount = 0, pickup == dropoff location (zero-distance trips),
           extreme trip_distance outliers (> 200 miles)
  Seed 2: combination — swapped coordinates, negative fares, zero-distance trips

Rubric checks (8):
  C1: analysis.py runs without error
  C2: geographic / invalid coordinate outliers addressed
  C3: negative or zero fare amounts handled
  C4: duration or distance outliers removed/flagged
  C5: model produces reasonable RMSE (< mean fare * 1.5)
  C6: results.json contains required fields
  C7: data loaded correctly
  C8: report.md discusses at least one data quality issue
"""
from __future__ import annotations

import textwrap

from generators.base import GeneratedTask
from generators.primitives import SeededRandom
from generators.real_data_base import DiscoveryGenerator

# NYC taxi columns available in the synthetic dataset
_KEEP_COLUMNS = [
    "VendorID",
    "tpep_pickup_datetime",
    "tpep_dropoff_datetime",
    "passenger_count",
    "trip_distance",
    "RatecodeID",
    "PULocationID",
    "DOLocationID",
    "payment_type",
    "fare_amount",
    "extra",
    "mta_tax",
    "tip_amount",
    "tolls_amount",
    "total_amount",
]

_VARIANTS = [
    {
        "seed_offset": 0,
        "description": "swapped location IDs, negative fares, extreme durations",
        "inject_swapped_locations": True,
        "inject_negative_fares": True,
        "inject_extreme_durations": True,
        "inject_zero_fares": False,
        "inject_zero_distance": False,
        "inject_distance_outliers": False,
        "n_swapped": 20,
        "n_negative": 8,
        "n_extreme_dur": 50,
    },
    {
        "seed_offset": 10,
        "description": "zero fares, zero-distance trips, extreme distance outliers",
        "inject_swapped_locations": False,
        "inject_negative_fares": False,
        "inject_extreme_durations": False,
        "inject_zero_fares": True,
        "inject_zero_distance": True,
        "inject_distance_outliers": True,
        "n_zero_fares": 12,
        "n_zero_distance": 15,
        "n_dist_outliers": 8,
    },
    {
        "seed_offset": 20,
        "description": "swapped locations, negative fares, zero-distance trips",
        "inject_swapped_locations": True,
        "inject_negative_fares": True,
        "inject_extreme_durations": False,
        "inject_zero_fares": False,
        "inject_zero_distance": True,
        "inject_distance_outliers": False,
        "n_swapped": 20,
        "n_negative": 8,
        "n_zero_distance": 15,
    },
]


class Generator(DiscoveryGenerator):
    task_id = "RDS20_taxi_quality"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]

    dataset_name = "nyc_taxi"
    dataset_license = "Public Domain (NYC TLC)"
    dataset_source = "NYC TLC Trip Record Data"

    def generate(self, seed: int) -> GeneratedTask:
        variant = _VARIANTS[seed % len(_VARIANTS)]
        rng = SeededRandom(seed + variant["seed_offset"])

        rows = self.load_dataset()
        rows = self.subsample(rows, seed=seed + 200, frac=0.06)  # ~600 rows
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
            "data/taxi_trips.csv": data_csv,
            "requirements.txt": requirements_txt,
            "check_solution.py": check_py,
            "task.yaml": task_yaml,
        }

        expected = {
            "issues": variant["description"],
            "n_rows": n_rows,
            "columns": _KEEP_COLUMNS,
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

        # Swapped PU/DO location IDs (simulates spatial anomaly)
        if variant.get("inject_swapped_locations"):
            indices = rng.sample(range(n), min(variant.get("n_swapped", 20), n // 20))
            for i in indices:
                # Swap pickup and dropoff location IDs to simulate invalid coordinates
                pu = result[i]["PULocationID"]
                result[i]["PULocationID"] = result[i]["DOLocationID"]
                result[i]["DOLocationID"] = pu
                # Set an obviously invalid location ID (> 265 is out of NYC TLC range)
                result[i]["PULocationID"] = str(rng.randint(300, 500))

        # Negative fare amounts (refunds / data entry errors)
        if variant.get("inject_negative_fares"):
            indices = rng.sample(range(n), min(variant.get("n_negative", 8), n // 40))
            for i in indices:
                try:
                    val = float(result[i]["fare_amount"])
                    result[i]["fare_amount"] = str(-abs(val))
                except (ValueError, TypeError):
                    result[i]["fare_amount"] = "-5.50"

        # Extreme duration outliers — set dropoff >> pickup (> 24h apart)
        if variant.get("inject_extreme_durations"):
            indices = rng.sample(range(n), min(variant.get("n_extreme_dur", 50), n // 8))
            for i in indices:
                # Replace dropoff datetime with one 30 hours later
                pickup = result[i].get("tpep_pickup_datetime", "2023-11-24 03:01:00")
                result[i]["tpep_dropoff_datetime"] = pickup[:10] + " 09:00:00"
                # Also set the pickup to 1 day earlier to make gap > 24h
                result[i]["tpep_pickup_datetime"] = pickup[:8] + str(
                    max(1, int(pickup[8:10]) - 1)
                ).zfill(2) + pickup[10:]

        # Zero fare amounts
        if variant.get("inject_zero_fares"):
            indices = rng.sample(range(n), min(variant.get("n_zero_fares", 12), n // 30))
            for i in indices:
                result[i]["fare_amount"] = "0.0"

        # Zero-distance trips (same PU and DO location)
        if variant.get("inject_zero_distance"):
            indices = rng.sample(range(n), min(variant.get("n_zero_distance", 15), n // 25))
            for i in indices:
                result[i]["trip_distance"] = "0.0"
                result[i]["DOLocationID"] = result[i]["PULocationID"]

        # Extreme distance outliers
        if variant.get("inject_distance_outliers"):
            indices = rng.sample(range(n), min(variant.get("n_dist_outliers", 8), n // 40))
            for i in indices:
                result[i]["trip_distance"] = str(rng.randint(250, 600))

        return result

    def _make_spec(self, n_rows: int) -> str:
        return textwrap.dedent(f"""\
            # RDS20: NYC Taxi Trip Analysis and Fare Prediction

            ## Task
            Analyze NYC yellow taxi trip patterns and build a regression model to predict
            fare amount from trip features.

            ## Dataset
            - File: `data/taxi_trips.csv`
            - Rows: {n_rows}
            - Target column: `fare_amount` (USD)
            - Features include: pickup/dropoff datetimes, trip distance, location IDs,
              passenger count, payment type, rate code

            ## Your Task
            1. Load and explore `data/taxi_trips.csv`
            2. Engineer useful features (e.g., trip duration, hour of day, day of week)
            3. Clean the data as needed
            4. Train a regression model to predict `fare_amount`
            5. Evaluate using RMSE and R² on a held-out test set (20% split, random_state=42)
            6. Save results and a brief report

            ## Required Deliverables

            ### 1. `analysis.py`
            A Python script that:
            - Loads `data/taxi_trips.csv`
            - Engineers features and cleans the data
            - Trains a regression model and evaluates on a test split
            - Saves `results.json` and `report.md`

            ### 2. `results.json`
            Must contain at minimum:
            ```json
            {{
              "model": "<model name>",
              "rmse": <float>,
              "r2": <float>,
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
            2. Invalid location IDs or geographic anomalies are addressed
            3. Negative or zero fare amounts are handled
            4. Duration or distance outliers are removed or flagged
            5. RMSE is reasonable (< mean fare × 1.5)
            6. `results.json` contains required fields
            7. Data loaded correctly (expected row count)
            8. `report.md` discusses at least one data quality issue
        """)

    def _make_brief(self) -> str:
        return textwrap.dedent("""\
            # RDS20: NYC Taxi Fare Prediction (Brief)

            Analyze trip patterns and predict fare amount using `data/taxi_trips.csv`.

            Produce:
            - `analysis.py` — feature engineering + model training + evaluation
            - `results.json` — RMSE and R² on held-out test set
            - `report.md` — data decisions and findings
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
                "description": "Geographic / invalid location anomalies addressed",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    geo_terms = [
                        "locationid", "location_id", "pulocationid", "dolocationid",
                        "outlier", "invalid", "filter", "valid", "range",
                        "265", "distance", "geographic", "spatial",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in geo_terms if t in content]
                        passed = len(found) >= 2
                        detail = f"geo terms found: {found}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C3",
                "description": "Negative or zero fare amounts handled",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    fare_terms = [
                        "fare", "negative", "< 0", "<= 0", "positive",
                        "filter", "drop", "remove", "clip", "abs",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        has_fare = "fare_amount" in content or "fare" in content
                        found = [t for t in fare_terms if t in content]
                        passed = has_fare and len(found) >= 2
                        detail = f"fare mentioned={has_fare}, terms={found}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C4",
                "description": "Duration or distance outliers addressed",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    outlier_terms = [
                        "outlier", "duration", "distance", "trip_distance",
                        "quantile", "percentile", "clip", "filter", "remove",
                        "iqr", "zscore", "z_score", "threshold", "24",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in outlier_terms if t in content]
                        passed = len(found) >= 3
                        detail = f"outlier terms found: {found}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C5",
                "description": "RMSE is reasonable (< mean fare * 1.5, reported in results.json)",
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
                                # NYC average fare ~$15; RMSE < $22.50 is reasonable
                                passed = 0.0 < float(rmse) < 200.0
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
                        "rmse": ["test_rmse", "rmse_score"],
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
                    p = pathlib.Path(workspace_dir) / "data" / "taxi_trips.csv"
                    passed = False
                    detail = ""
                    expected_rows = {n_rows}
                    if p.exists():
                        with open(p, newline="", encoding="utf-8") as fh:
                            actual = sum(1 for _ in csv.reader(fh)) - 1
                        passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.01))
                        detail = f"actual={{actual}}, expected={{expected_rows}}"
                    else:
                        detail = "data/taxi_trips.csv not found"
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
                        "outlier", "negative", "invalid", "clean", "filter",
                        "quality", "anomal", "zero", "missing", "remove",
                        "duration", "distance", "fare", "location",
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
