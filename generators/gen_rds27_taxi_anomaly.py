"""
Generator for RDS27: NYC Taxi Demand Anomaly (Archetype 2 — Synthesis).

Dataset: nyc_taxi (VendorID, pickup/dropoff datetime, trip_distance, fare_amount, ...)

Task: Explain an anomalous demand spike on specific dates. Requires synthesizing
evidence from weather, events, and transit disruption data.

Corpus documents:
  - weather.csv           : Daily weather records showing heavy rain on anomaly dates
  - events.csv            : Major events schedule (concert/sports at MSG)
  - transit_disruptions.md: Subway line closure bulletin

Synthesis: Rain + major event + subway outage = perfect storm for taxi demand spike.

Rubric (8 checks):
  C1 — analysis.py runs without error
  C2 — Weather / rain factor identified
  C3 — Event factor identified (concert/sports/MSG)
  C4 — Transit disruption / subway closure identified
  C5 — results.json has demand_spike_factors key with >= 2 entries
  C6 — report.md quantifies at least one factor's contribution
  C7 — Data loaded correctly
  C8 — results.json valid JSON with required fields
"""
from __future__ import annotations

import textwrap

from generators.base import GeneratedTask
from generators.real_data_base import SynthesisGenerator
from generators.primitives import SeededRandom


_VARIANTS = [
    {
        "seed": 0,
        "anomaly_dates": ["2018-03-14", "2018-03-15"],
        "anomaly_label": "March 14–15, 2018",
        "weather_condition": "Heavy rain (2.8 inches over 2 days)",
        "event_name": "NBA Knicks vs. Boston Celtics (MSG)",
        "event_venue": "Madison Square Garden",
        "event_attendance": 19763,
        "subway_lines_closed": ["A", "C"],
        "closure_reason": "signal failure due to water intrusion",
        "demand_spike_pct": 34,
        "baseline_dates": ["2018-03-07", "2018-03-08"],
    },
    {
        "seed": 1,
        "anomaly_dates": ["2018-07-20", "2018-07-21"],
        "anomaly_label": "July 20–21, 2018",
        "weather_condition": "Thunderstorms (1.9 inches, wind gusts 40 mph)",
        "event_name": "Beyoncé / Jay-Z On The Run II Tour (CitiField)",
        "event_venue": "Citi Field",
        "event_attendance": 42000,
        "subway_lines_closed": ["7"],
        "closure_reason": "planned track maintenance combined with storm-related delays",
        "demand_spike_pct": 47,
        "baseline_dates": ["2018-07-13", "2018-07-14"],
    },
    {
        "seed": 2,
        "anomaly_dates": ["2019-01-19", "2019-01-20"],
        "anomaly_label": "January 19–20, 2019",
        "weather_condition": "Winter storm (4.1 inches snow, reduced visibility)",
        "event_name": "NHL Rangers vs. Pittsburgh Penguins + UFC 230 (MSG)",
        "event_venue": "Madison Square Garden",
        "event_attendance": 18006,
        "subway_lines_closed": ["B", "D", "F", "M"],
        "closure_reason": "winter storm emergency suspension of select lines",
        "demand_spike_pct": 51,
        "baseline_dates": ["2019-01-12", "2019-01-13"],
    },
]

_KEEP_COLUMNS = [
    "VendorID", "tpep_pickup_datetime", "tpep_dropoff_datetime",
    "passenger_count", "trip_distance", "RatecodeID",
    "PULocationID", "DOLocationID", "payment_type",
    "fare_amount", "tip_amount", "total_amount",
]


class Generator(SynthesisGenerator):
    task_id = "RDS27_taxi_anomaly"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]

    dataset_name = "nyc_taxi"
    dataset_license = "Public Domain"
    dataset_source = "NYC TLC"

    def generate(self, seed: int) -> GeneratedTask:
        v = _VARIANTS[seed % len(_VARIANTS)]
        rng = SeededRandom(seed + 270)

        rows = self.load_dataset()
        rows = self.subsample(rows, seed=seed + 270, frac=0.02)
        rows = self.select_columns(rows, _KEEP_COLUMNS)
        n_rows = len(rows)
        data_csv = self.rows_to_csv(rows, _KEEP_COLUMNS)

        corpus = {
            "weather.csv": self._gen_weather_csv(v, rng),
            "events.csv": self._gen_events_csv(v, rng),
            "transit_disruptions.md": self._gen_transit_md(v),
        }

        requirements_txt = "pandas>=1.5\nnumpy>=1.23\nscipy>=1.9\n"
        task_yaml = self.make_task_yaml()
        check_py = self._make_check_solution(v, n_rows)

        workspace_files = {
            "data/nyc_taxi.csv": data_csv,
            "requirements.txt": requirements_txt,
            "check_solution.py": check_py,
            "task.yaml": task_yaml,
        }

        expected = {
            "anomaly_dates": v["anomaly_dates"],
            "demand_spike_factors": ["weather", "major_event", "transit_disruption"],
            "n_rows": n_rows,
            "required_output_files": ["analysis.py", "results.json", "report.md"],
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=self._make_spec(v, n_rows),
            brief_md=self._make_brief(v),
            expected=expected,
            workspace_files=workspace_files,
            corpus_files=corpus,
        )

    # ── Corpus generators ─────────────────────────────────────────────────────

    def _gen_weather_csv(self, v: dict, rng: SeededRandom) -> str:
        lines = ["date,max_temp_f,min_temp_f,precipitation_in,wind_speed_mph,condition"]
        # Generate ~30 days of weather around anomaly dates
        # Derive a rough base date from the first anomaly date
        anom_month = v["anomaly_dates"][0][5:7]
        anom_day = int(v["anomaly_dates"][0][8:10])
        anom_year = v["anomaly_dates"][0][:4]

        # Generate surrounding dates (simplified: just use representative data)
        all_dates = []
        for d in range(anom_day - 10, anom_day + 10):
            if 1 <= d <= 28:
                date_str = f"{anom_year}-{anom_month}-{d:02d}"
                all_dates.append(date_str)

        for date_str in all_dates:
            is_anomaly = date_str in v["anomaly_dates"]
            if is_anomaly:
                precip = round(rng.uniform(1.2, 2.5), 2)
                wind = round(rng.uniform(25, 45), 1)
                cond = "Heavy Rain" if "rain" in v["weather_condition"].lower() or "thunder" in v["weather_condition"].lower() else "Snow"
                temp_max = 42 if "snow" in v["weather_condition"].lower() else 58
                temp_min = 34 if "snow" in v["weather_condition"].lower() else 51
            else:
                precip = round(rng.uniform(0.0, 0.2), 2)
                wind = round(rng.uniform(5, 15), 1)
                cond = "Partly Cloudy" if rng.uniform(0, 1) > 0.3 else "Clear"
                temp_max = round(rng.uniform(55, 72), 0)
                temp_min = round(rng.uniform(42, 58), 0)
            lines.append(f"{date_str},{temp_max},{temp_min},{precip},{wind},{cond}")

        return "\n".join(lines) + "\n"

    def _gen_events_csv(self, v: dict, rng: SeededRandom) -> str:
        lines = ["date,event_name,venue,expected_attendance,event_type,start_time"]
        # Anomaly event
        for date in v["anomaly_dates"]:
            lines.append(
                f"{date},{v['event_name']},{v['event_venue']},"
                f"{v['event_attendance']},Sports/Entertainment,19:30"
            )
        # Distractor events on other dates
        distractors = [
            ("Broadway Show - Hamilton", "Richard Rodgers Theatre", 1319, "Theater", "20:00"),
            ("NY Mets vs Yankees", "Yankee Stadium", 38000, "Baseball", "13:05"),
            ("NYC Marathon", "Central Park", 55000, "Running", "09:00"),
            ("Fashion Week Gala", "Lincoln Center", 2500, "Fashion", "18:00"),
            ("Film Festival Premiere", "AMC Lincoln Square", 800, "Film", "21:00"),
        ]
        anom_month = v["anomaly_dates"][0][5:7]
        anom_year = v["anomaly_dates"][0][:4]
        for i, (name, venue, att, etype, time) in enumerate(distractors):
            d = (i + 1) * 3
            if d <= 28:
                date_str = f"{anom_year}-{anom_month}-{d:02d}"
                lines.append(f"{date_str},{name},{venue},{att},{etype},{time}")
        return "\n".join(lines) + "\n"

    def _gen_transit_md(self, v: dict) -> str:
        lines_str = "/".join(v["subway_lines_closed"])
        return textwrap.dedent(f"""\
            # MTA Service Advisory
            **Date Issued**: {v['anomaly_dates'][0]}
            **Affected Dates**: {v['anomaly_label']}
            **Reference**: SVC-{v['anomaly_dates'][0].replace('-', '')}-001

            ## Service Disruption Notice

            **{lines_str} train service suspended** on the dates listed above due
            to {v['closure_reason']}.

            Affected routes:
            {chr(10).join(f"  - **{line} train**: Full line suspension, no service" for line in v['subway_lines_closed'])}

            Customers are advised to use:
            - Alternative subway lines where possible
            - MTA bus service on parallel routes
            - **For-hire vehicles** (taxis, rideshare) where transit alternatives
              are unavailable or significantly delayed

            ## Historical Context

            MTA records indicate that full-line suspensions of multiple lines
            during high-traffic event nights typically result in a 25–60%
            increase in for-hire vehicle demand in the affected corridors,
            based on prior incident analysis (see MTA FHV Impact Study 2017).

            ## Distractor: Planned Maintenance (Unrelated)

            Note: Separate weekend maintenance on the L train for track replacement
            is scheduled for the following month. This is unrelated to the
            current emergency suspension and affects a different corridor.

            ---
            *MTA New York City Transit — Customer Information Division*
        """)

    # ── Spec / brief ──────────────────────────────────────────────────────────

    def _make_spec(self, v: dict, n_rows: int) -> str:
        return textwrap.dedent(f"""\
            # RDS27: NYC Taxi Demand Anomaly Investigation

            ## Background

            NYC TLC yellow taxi trip data shows an anomalous demand spike on
            **{v['anomaly_label']}** — trip counts were approximately {v['demand_spike_pct']}%
            above the baseline for comparable days in the same period.

            Your task is to identify all factors that contributed to this spike
            by synthesizing evidence from the trip data and three external documents.

            ## Dataset

            - File: `data/nyc_taxi.csv`
            - Rows: {n_rows} (subsample)
            - Key columns: `tpep_pickup_datetime`, `tpep_dropoff_datetime`,
              `trip_distance`, `fare_amount`, `PULocationID`, `DOLocationID`

            ## Corpus Documents

            Reference documents in `corpus/`:

            | File | Description |
            |------|-------------|
            | `weather.csv` | Daily weather data (precipitation, temperature, conditions) |
            | `events.csv` | Major events schedule with venue and attendance |
            | `transit_disruptions.md` | MTA service advisory for affected dates |

            **All three factors contribute.** Identify each one and, where possible,
            quantify its contribution to the demand spike.

            ## Required Deliverables

            ### 1. `analysis.py`
            - Load and explore taxi trip data
            - Identify anomaly dates by computing trip volume vs baseline
            - Read corpus documents and correlate with anomaly timing
            - Quantify each factor's estimated contribution where data permits

            ### 2. `results.json`
            ```json
            {{
              "anomaly_dates": ["<date1>", ...],
              "baseline_trip_count": <float>,
              "anomaly_trip_count": <float>,
              "demand_spike_pct": <float>,
              "demand_spike_factors": ["<factor1>", "<factor2>", "<factor3>"],
              "primary_factor": "<string>"
            }}
            ```

            ### 3. `report.md`
            400–700 words covering:
            - Magnitude of the demand spike (quantified)
            - Each contributing factor with supporting evidence
            - Which factor had the greatest impact and why
            - Operational implications for taxi/rideshare dispatching

            ## Grading Criteria
            1. `analysis.py` runs without error
            2. Weather / precipitation factor identified
            3. Major event factor identified
            4. Transit disruption / subway closure identified
            5. `results.json` has `demand_spike_factors` with ≥ 2 entries
            6. `report.md` quantifies at least one factor's contribution
            7. Data loaded correctly
            8. `results.json` valid JSON with required fields
        """)

    def _make_brief(self, v: dict) -> str:
        return textwrap.dedent(f"""\
            # RDS27: NYC Taxi Demand Anomaly (Brief)

            NYC yellow taxi data shows anomalous demand on {v['anomaly_label']}.
            Identify the contributing factors by synthesizing trip data with
            corpus reference documents.

            **Dataset**: `data/nyc_taxi.csv`

            **Corpus docs** (in `corpus/`):
            - `weather.csv`
            - `events.csv`
            - `transit_disruptions.md`

            Produce:
            - `analysis.py` — investigation script
            - `results.json` — factors and demand metrics
            - `report.md` — narrative explanation
        """)

    # ── Grader ────────────────────────────────────────────────────────────────

    def _make_check_solution(self, v: dict, n_rows: int) -> str:
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
                "description": "Weather / rain / precipitation factor identified",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    passed = False
                    detail = ""
                    terms = ["weather", "rain", "precipitation", "storm", "snow",
                             "rainfall", "wet", "wind", "thunder", "inclement"]
                    for fname in ["analysis.py", "report.md"]:
                        p = pathlib.Path(workspace_dir) / fname
                        if p.exists():
                            content = p.read_text(encoding="utf-8").lower()
                            found = [t for t in terms if t in content]
                            if found:
                                passed = True
                                detail = f"found in {fname}: {found}"
                                break
                    if not passed:
                        detail = "weather/rain terms not found"
                """),
            },
            {
                "id": "C3",
                "description": "Major event factor identified (concert/sports/venue)",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    passed = False
                    detail = ""
                    terms = ["event", "concert", "game", "sports", "msg",
                             "madison square", "citi field", "stadium", "venue",
                             "attendance", "arena", "show", "performance"]
                    for fname in ["analysis.py", "report.md"]:
                        p = pathlib.Path(workspace_dir) / fname
                        if p.exists():
                            content = p.read_text(encoding="utf-8").lower()
                            found = [t for t in terms if t in content]
                            if found:
                                passed = True
                                detail = f"found in {fname}: {found}"
                                break
                    if not passed:
                        detail = "event/concert terms not found"
                """),
            },
            {
                "id": "C4",
                "description": "Transit disruption / subway closure identified",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    passed = False
                    detail = ""
                    terms = ["subway", "transit", "mta", "train", "service disruption",
                             "line closure", "suspension", "outage", "service advisory",
                             "rail", "metro"]
                    for fname in ["analysis.py", "report.md"]:
                        p = pathlib.Path(workspace_dir) / fname
                        if p.exists():
                            content = p.read_text(encoding="utf-8").lower()
                            found = [t for t in terms if t in content]
                            if found:
                                passed = True
                                detail = f"found in {fname}: {found}"
                                break
                    if not passed:
                        detail = "transit disruption terms not found"
                """),
            },
            {
                "id": "C5",
                "description": "results.json has demand_spike_factors with >= 2 entries",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    if p.exists():
                        try:
                            d = json.loads(p.read_text(encoding="utf-8"))
                            factors = d.get("demand_spike_factors", [])
                            passed = isinstance(factors, list) and len(factors) >= 2
                            detail = f"demand_spike_factors={factors}"
                        except Exception as e:
                            detail = str(e)
                    else:
                        detail = "results.json not found"
                """),
            },
            {
                "id": "C6",
                "description": "report.md quantifies at least one factor's contribution",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib, re
                    p = pathlib.Path(workspace_dir) / "report.md"
                    passed = False
                    detail = ""
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        # Look for numeric quantification (%, fold, x higher, etc.)
                        has_pct = bool(re.search(r'\\d+\\s*%', content))
                        has_fold = bool(re.search(r'\\d+\\.?\\d*\\s*x\\b', content))
                        has_times = "times higher" in content or "times more" in content
                        quant_terms = ["increase of", "increase by", "higher than",
                                       "above baseline", "spike of", "surge of",
                                       "contributed", "accounted for"]
                        has_quant = any(t in content for t in quant_terms)
                        passed = has_pct or has_fold or has_times or has_quant
                        detail = f"has_pct={has_pct}, has_fold={has_fold}, has_quant={has_quant}"
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
                        passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.02))
                        detail = f"actual={{actual}}, expected={{expected_rows}}"
                    else:
                        detail = "data/nyc_taxi.csv not found"
                """),
            },
            {
                "id": "C8",
                "description": "results.json valid JSON with required fields",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    required = ["demand_spike_factors", "demand_spike_pct", "primary_factor"]
                    if p.exists():
                        try:
                            d = json.loads(p.read_text(encoding="utf-8"))
                            missing = [f for f in required if f not in d]
                            passed = len(missing) == 0
                            detail = f"missing={missing}" if missing else "all fields present"
                        except json.JSONDecodeError as e:
                            detail = f"JSON error: {e}"
                    else:
                        detail = "results.json not found"
                """),
            },
        ]
        return self.make_check_solution(checks)
