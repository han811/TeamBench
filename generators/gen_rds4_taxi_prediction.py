"""
Parameterized generator for RDS4: NYC Taxi Prediction (Archetype 3 — Open-Ended).

Uses the NYC TLC Yellow Taxi dataset. Three seed variants ask different prediction questions:
  Seed 0: What predicts tip amount? (time-of-day, distance, payment)
  Seed 1: What predicts trip duration?
  Seed 2: What drives fare amount? (distance vs time vs borough)

No scaffold code is provided. The agent receives the raw data and must build a
predictive model and produce structured output files.

Rubric checks (8):
  C1: analysis.py runs without error
  C2: Feature engineering present (time features or distance features)
  C3: Model performance reported with metric in results.json
  C4: Key predictors referenced in analysis.py
  C5: Model validation / cross-validation or train-test split present
  C6: Findings discussed in report.md with feature importance or coefficients
  C7: Data loaded correctly (row count check)
  C8: results.json is valid JSON with required fields
"""
from __future__ import annotations

import textwrap

from generators.base import GeneratedTask
from generators.real_data_base import OpenEndedGenerator

_VARIANTS = [
    {
        # Seed 0 — tip prediction
        "target": "tip_amount",
        "target_label": "tip amount (dollars)",
        "research_question": (
            "What features best predict tip amount for NYC yellow taxi trips? "
            "Specifically, how much do time-of-day, trip distance, and payment type "
            "contribute to tip size?"
        ),
        "key_features": ["trip_distance", "fare_amount", "payment_type", "passenger_count"],
        "feature_engineering": (
            "Extract hour-of-day and day-of-week from `tpep_pickup_datetime`. "
            "Note: `payment_type=1` is credit card (tips recorded), `payment_type=2` is cash "
            "(tips typically not recorded). Consider whether to include or filter cash trips."
        ),
        "hidden_feature_keywords": ["trip_distance", "payment_type"],
        "context": (
            "Tip amount is strongly influenced by fare amount (larger fares → larger tips). "
            "Credit card tips are systematically recorded while cash tips are not. "
            "Time-of-day matters: late-night and rush-hour trips may differ. "
            "A good model should handle the payment_type confound carefully."
        ),
        "metric": "RMSE",
        "metric_key": "rmse",
        "filter_hint": "Consider filtering to credit card trips (payment_type=1) for reliable tip data.",
    },
    {
        # Seed 1 — trip duration prediction
        "target": "trip_duration_minutes",
        "target_label": "trip duration (minutes)",
        "research_question": (
            "What features best predict NYC yellow taxi trip duration? "
            "How do distance, time-of-day, and pickup/dropoff location affect duration?"
        ),
        "key_features": ["trip_distance", "PULocationID", "DOLocationID", "passenger_count"],
        "feature_engineering": (
            "Compute trip duration in minutes from `tpep_pickup_datetime` and "
            "`tpep_dropoff_datetime`. Extract hour-of-day and day-of-week. "
            "Filter out trips with duration < 1 minute or > 180 minutes as outliers."
        ),
        "hidden_feature_keywords": ["trip_distance", "PULocationID"],
        "context": (
            "Trip duration depends heavily on distance but also on congestion. "
            "Pickup and dropoff location IDs encode geographic information. "
            "Rush hour (7-9am, 5-7pm weekdays) dramatically increases duration. "
            "The target must be computed from datetime columns — it is not directly in the data."
        ),
        "metric": "RMSE",
        "metric_key": "rmse",
        "filter_hint": "Filter out extreme outliers: trips < 1 min or > 3 hours, distance < 0.1 miles.",
    },
    {
        # Seed 2 — fare amount drivers
        "target": "fare_amount",
        "target_label": "fare amount (dollars)",
        "research_question": (
            "What drives NYC yellow taxi fare amount — trip distance, trip duration, "
            "or the pickup/dropoff borough combination?"
        ),
        "key_features": ["trip_distance", "PULocationID", "DOLocationID", "RatecodeID"],
        "feature_engineering": (
            "Compute trip duration in minutes from the datetime columns. "
            "Use `RatecodeID` (rate code: 1=standard, 2=JFK, 3=Newark, 4=Nassau, 5=negotiated). "
            "Group `PULocationID` and `DOLocationID` into broad borough categories if possible, "
            "or use them as categorical features directly."
        ),
        "hidden_feature_keywords": ["trip_distance", "RatecodeID"],
        "context": (
            "Fare amount follows a metered structure: $3 base + $0.70/0.2 mile. "
            "However RatecodeID creates special flat-rate zones (e.g. JFK flat $70). "
            "The interaction between distance and rate code matters. "
            "Decompose the variance explained by distance alone vs. additional location factors."
        ),
        "metric": "R2",
        "metric_key": "r2",
        "filter_hint": "Filter to standard rate (RatecodeID=1) and JFK (RatecodeID=2) trips for cleaner analysis.",
    },
]

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
    "tip_amount",
    "tolls_amount",
    "total_amount",
]


class Generator(OpenEndedGenerator):
    task_id = "RDS4_taxi_prediction"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]

    dataset_name = "nyc_taxi"
    dataset_license = "Public Domain"
    dataset_source = "NYC TLC"

    def generate(self, seed: int) -> GeneratedTask:
        variant = _VARIANTS[seed % len(_VARIANTS)]

        rows = self.load_dataset()
        rows = self.subsample(rows, seed=seed + 400, frac=0.015)  # ~1500 rows
        rows = self.select_columns(rows, _KEEP_COLUMNS)
        n_rows = len(rows)
        data_csv = self.rows_to_csv(rows, _KEEP_COLUMNS)

        check_py = self._make_check_solution(variant, n_rows)
        requirements_txt = self.make_requirements_txt(
            packages=[
                "pandas>=1.5",
                "numpy>=1.23",
                "scipy>=1.9",
                "scikit-learn>=1.1",
            ]
        )
        task_yaml = self.make_task_yaml()

        workspace_files = {
            "data/nyc_taxi.csv": data_csv,
            "requirements.txt": requirements_txt,
            "check_solution.py": check_py,
            "task.yaml": task_yaml,
        }

        expected = {
            "target": variant["target"],
            "research_question": variant["research_question"],
            "key_features": variant["key_features"],
            "hidden_feature_keywords": variant["hidden_feature_keywords"],
            "n_rows": n_rows,
            "columns": _KEEP_COLUMNS,
            "required_output_files": ["analysis.py", "results.json", "report.md"],
        }

        spec_md = self._make_spec(variant, n_rows)
        brief_md = self._make_brief(variant)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _make_spec(self, variant: dict, n_rows: int) -> str:
        feature_list = ", ".join(f"`{f}`" for f in variant["key_features"])
        return textwrap.dedent(f"""\
            # RDS4: NYC Taxi Prediction

            ## Research Question
            **{variant["research_question"]}**

            ## Dataset
            - File: `data/nyc_taxi.csv`
            - Rows: {n_rows} (subsample of NYC TLC Yellow Taxi data)
            - Columns: {", ".join(f"`{c}`" for c in _KEEP_COLUMNS)}
            - Target variable: `{variant["target_label"]}`

            ## Feature Engineering
            {variant["feature_engineering"]}

            ## Background
            {variant["context"]}

            ## Hint
            {variant["filter_hint"]}

            ## Your Task
            Build a predictive model for `{variant["target_label"]}`. You are free to choose
            any appropriate regression method (linear regression, random forest, gradient
            boosting, etc.). The key requirements are:

            1. Engineer relevant features (datetime decomposition, filtering outliers)
            2. Split data into train/test sets
            3. Report {variant["metric"]} on the held-out test set
            4. Identify the most important predictors
            5. Discuss findings and limitations

            ### Key Features to Include
            At minimum, use: {feature_list}

            ## Required Deliverables

            ### 1. `analysis.py`
            A Python script that:
            - Loads `data/nyc_taxi.csv`
            - Engineers features and filters outliers
            - Trains a regression model with train/test split
            - Reports {variant["metric"]} on the test set
            - Saves `results.json` and `report.md`

            ### 2. `results.json`
            Must contain at minimum:
            ```json
            {{
              "target": "{variant["target"]}",
              "{variant["metric_key"]}": <float>,
              "method": "<model name>",
              "n_train": <int>,
              "n_test": <int>,
              "top_features": [<feature names>]
            }}
            ```

            ### 3. `report.md`
            A brief (300–600 word) report covering:
            - Feature engineering decisions
            - Model choice and {variant["metric"]} on test set
            - Top predictors and their relative importance
            - **Limitations** (data quality, generalizability, etc.)

            ## Grading Criteria
            1. `analysis.py` runs without error
            2. Feature engineering present (datetime or distance features)
            3. Model performance metric ({variant["metric"]}) reported in `results.json`
            4. Key features ({feature_list}) referenced in analysis code
            5. Train/test split or cross-validation present
            6. `report.md` discusses feature importance and limitations
            7. Data loaded correctly (correct row count)
            8. `results.json` contains required fields and is valid JSON
        """)

    def _make_brief(self, variant: dict) -> str:
        return textwrap.dedent(f"""\
            # RDS4: NYC Taxi Prediction (Brief)

            Analyze the NYC Taxi dataset to build a predictive model.

            **Dataset**: `data/nyc_taxi.csv`

            **Question**: {variant["research_question"]}

            Produce:
            - `analysis.py` — prediction model script
            - `results.json` — model performance and top features
            - `report.md` — findings and limitations
        """)

    def _make_check_solution(self, variant: dict, n_rows: int) -> str:
        hidden_kw = variant["hidden_feature_keywords"]
        metric_key = variant["metric_key"]
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
                "description": "Feature engineering present in analysis.py (datetime/distance/duration features)",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    feature_terms = [
                        "hour", "day", "datetime", "duration", "distance",
                        "dt.", "strptime", "to_datetime", "timedelta",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in feature_terms if t in content]
                        passed = len(found) >= 1
                        detail = f"found feature engineering terms: {found}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C3",
                "description": f"Model performance metric ({variant['metric']}) reported in results.json",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    if p.exists():
                        try:
                            d = json.loads(p.read_text())
                            has_metric = "{metric_key}" in d
                            passed = has_metric
                            detail = f"{metric_key} present={{has_metric}}"
                        except Exception as e:
                            detail = str(e)
                    else:
                        detail = "results.json not found"
                """),
            },
            {
                "id": "C4",
                "description": f"Key features ({', '.join(hidden_kw)}) referenced in analysis.py",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    keywords = {hidden_kw!r}
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [kw for kw in keywords if kw.lower() in content]
                        passed = len(found) == len(keywords)
                        detail = f"found={{found}}, missing={{[kw for kw in keywords if kw.lower() not in content]}}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C5",
                "description": "Train/test split or cross-validation present in analysis.py",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    split_terms = [
                        "train_test_split", "cross_val", "kfold", "k_fold",
                        "test_size", "train_size", "split(", "validation",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in split_terms if t in content]
                        passed = len(found) >= 1
                        detail = f"found split terms: {found}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C6",
                "description": "report.md discusses feature importance and limitations",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "report.md"
                    passed = False
                    detail = ""
                    report_terms = ["feature", "important", "limitation", "predict",
                                    "model", "result", "finding"]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in report_terms if t in content]
                        passed = len(found) >= 3
                        detail = f"found report terms: {found}"
                    else:
                        detail = "report.md not found"
                """),
            },
            {
                "id": "C7",
                "description": f"Data loaded correctly (expected ~{n_rows} rows)",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import pathlib, csv
                    p = pathlib.Path(workspace_dir) / "data" / "nyc_taxi.csv"
                    passed = False
                    detail = ""
                    expected_rows = {n_rows}
                    if p.exists():
                        with open(p, newline="", encoding="utf-8") as fh:
                            actual = sum(1 for _ in csv.reader(fh)) - 1
                        passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.01))
                        detail = f"actual={{actual}}, expected={{expected_rows}}"
                    else:
                        detail = "data/nyc_taxi.csv not found"
                """),
            },
            {
                "id": "C8",
                "description": "results.json is valid JSON with required fields",
                "type": "custom_python",
                "code": textwrap.dedent(f"""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    required_fields = ["{metric_key}", "method", "top_features"]
                    if p.exists():
                        try:
                            d = json.loads(p.read_text(encoding="utf-8"))
                            missing = [f for f in required_fields if f not in d]
                            passed = len(missing) == 0
                            detail = f"missing fields: {{missing}}" if missing else "all required fields present"
                        except json.JSONDecodeError as e:
                            detail = f"JSON parse error: {{e}}"
                    else:
                        detail = "results.json not found"
                """),
            },
        ]
        return self.make_check_solution(checks)
