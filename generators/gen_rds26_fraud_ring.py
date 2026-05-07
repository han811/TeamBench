"""
Generator for RDS26: Fraud Ring Investigation (Archetype 2 — Synthesis).

Dataset: credit_card_fraud (Time, V1-V28 PCA features, Amount, Class)

Task: An unusual fraud pattern has appeared in recent transactions. The agent
must synthesize evidence from three corpus documents to identify the organized
fraud ring and explain the attack pattern.

Corpus documents:
  - mcc_codes.csv       : Merchant category codes reference table
  - holiday_calendar.csv: Holiday and long-weekend dates
  - fraud_intelligence.md: Intelligence report mentioning organized ring targeting
                           electronics MCCs on holiday weekends

Synthesis: Fraud cluster = organized ring targeting electronics MCCs on holiday
weekends. Amount profile (high-value transactions) confirms organized behavior.

Rubric (8 checks):
  C1 — analysis.py runs without error
  C2 — MCC / merchant category pattern identified
  C3 — Holiday / weekend temporal pattern identified
  C4 — Organized ring / coordinated fraud hypothesis in report
  C5 — results.json has fraud_pattern key describing the cluster
  C6 — report.md proposes targeted detection rule or monitoring
  C7 — Data loaded correctly
  C8 — results.json is valid JSON with required fields
"""
from __future__ import annotations

import textwrap

from generators.base import GeneratedTask
from generators.real_data_base import SynthesisGenerator
from generators.primitives import SeededRandom


_VARIANTS = [
    {
        "seed": 0,
        "target_mcc_group": "electronics",
        "target_mcc_codes": ["5065", "5734", "5732", "5045"],
        "target_mcc_desc": "electronic parts stores (5065), computer and software stores (5734/5732), and computers/peripherals wholesale (5045)",
        "holiday_name": "Black Friday / Cyber Monday weekend",
        "holiday_dates": ["2018-11-23", "2018-11-25", "2018-11-26"],
        "ring_name": "Ring-7",
        "avg_fraud_amount": 487.50,
        "ring_size": 23,
    },
    {
        "seed": 1,
        "target_mcc_group": "electronics and jewelry",
        "target_mcc_codes": ["5065", "5094", "5944", "5734"],
        "target_mcc_desc": "electronic parts (5065), jewelry/watches wholesale (5094), jewelry stores (5944), and computer stores (5734)",
        "holiday_name": "Memorial Day weekend",
        "holiday_dates": ["2019-05-25", "2019-05-26", "2019-05-27"],
        "ring_name": "Ring-12",
        "avg_fraud_amount": 612.00,
        "ring_size": 17,
    },
    {
        "seed": 2,
        "target_mcc_group": "electronics and department stores",
        "target_mcc_codes": ["5065", "5311", "5734", "5411"],
        "target_mcc_desc": "electronic parts (5065), department stores (5311), computer stores (5734), and grocery stores during gift card purchases (5411)",
        "holiday_name": "Labor Day weekend",
        "holiday_dates": ["2019-08-31", "2019-09-01", "2019-09-02"],
        "ring_name": "Ring-19",
        "avg_fraud_amount": 398.75,
        "ring_size": 31,
    },
]

_KEEP_COLUMNS = [
    "Time", "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8",
    "V10", "V12", "V14", "V17", "V21", "V24", "V26", "Amount", "Class",
]


class Generator(SynthesisGenerator):
    task_id = "RDS26_fraud_ring"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]

    dataset_name = "credit_card_fraud"
    dataset_license = "CC0"
    dataset_source = "Kaggle / ULB"

    def generate(self, seed: int) -> GeneratedTask:
        v = _VARIANTS[seed % len(_VARIANTS)]
        rng = SeededRandom(seed + 260)

        rows = self.load_dataset()
        rows = self.subsample(rows, seed=seed + 260, frac=0.05)
        rows = self.select_columns(rows, _KEEP_COLUMNS)
        n_rows = len(rows)
        data_csv = self.rows_to_csv(rows, _KEEP_COLUMNS)

        corpus = {
            "mcc_codes.csv": self._gen_mcc_csv(v, rng),
            "holiday_calendar.csv": self._gen_holiday_csv(v, rng),
            "fraud_intelligence.md": self._gen_intel_md(v),
        }

        requirements_txt = "pandas>=1.5\nnumpy>=1.23\nscipy>=1.9\nscikit-learn>=1.1\n"
        task_yaml = self.make_task_yaml()
        check_py = self._make_check_solution(v, n_rows)

        workspace_files = {
            "data/credit_card_fraud.csv": data_csv,
            "requirements.txt": requirements_txt,
            "check_solution.py": check_py,
            "task.yaml": task_yaml,
        }

        expected = {
            "fraud_ring": v["ring_name"],
            "target_mcc_group": v["target_mcc_group"],
            "holiday_pattern": v["holiday_name"],
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

    def _gen_mcc_csv(self, v: dict, rng: SeededRandom) -> str:
        lines = ["mcc_code,category,description,fraud_risk_tier"]
        entries = [
            ("5065", "Electronics", "Electronic parts and equipment", "HIGH"),
            ("5734", "Electronics", "Computer and software stores", "HIGH"),
            ("5732", "Electronics", "Electronics stores", "HIGH"),
            ("5045", "Electronics", "Computers and peripherals wholesale", "HIGH"),
            ("5094", "Jewelry", "Jewelry, watches, and silverware wholesale", "HIGH"),
            ("5944", "Jewelry", "Jewelry stores", "HIGH"),
            ("5311", "Retail", "Department stores", "MEDIUM"),
            ("5411", "Grocery", "Grocery stores and supermarkets", "LOW"),
            ("5912", "Health", "Drug stores and pharmacies", "LOW"),
            ("5812", "Food", "Eating places and restaurants", "LOW"),
            ("5411", "Grocery", "Grocery stores", "LOW"),
            ("5999", "Misc", "Miscellaneous retail stores", "MEDIUM"),
            ("5533", "Auto", "Automotive parts and accessories", "MEDIUM"),
            ("7011", "Travel", "Hotels and lodging", "MEDIUM"),
            ("4111", "Transit", "Transportation and transit", "LOW"),
        ]
        for code, cat, desc, risk in entries:
            lines.append(f"{code},{cat},{desc},{risk}")
        # Add distractor: crypto/gift card codes (not relevant to this ring)
        lines.append("6051,Quasi-Cash,Non-financial institutions quasi-cash,HIGH")
        lines.append("6010,Financial,Financial institutions cash disbursements,HIGH")
        return "\n".join(lines) + "\n"

    def _gen_holiday_csv(self, v: dict, rng: SeededRandom) -> str:
        lines = ["date,holiday_name,is_long_weekend,year"]
        holiday_data = [
            ("2018-01-01", "New Year's Day", "N", 2018),
            ("2018-05-28", "Memorial Day", "Y", 2018),
            ("2018-07-04", "Independence Day", "N", 2018),
            ("2018-09-03", "Labor Day", "Y", 2018),
            ("2018-11-22", "Thanksgiving", "Y", 2018),
            ("2018-11-23", "Black Friday", "Y", 2018),
            ("2018-11-26", "Cyber Monday", "Y", 2018),
            ("2018-12-25", "Christmas Day", "N", 2018),
            ("2019-01-01", "New Year's Day", "N", 2019),
            ("2019-05-27", "Memorial Day", "Y", 2019),
            ("2019-07-04", "Independence Day", "Y", 2019),
            ("2019-09-02", "Labor Day", "Y", 2019),
            ("2019-11-28", "Thanksgiving", "Y", 2019),
            ("2019-11-29", "Black Friday", "Y", 2019),
            ("2019-12-25", "Christmas Day", "N", 2019),
        ]
        for date, name, lw, yr in holiday_data:
            lines.append(f"{date},{name},{lw},{yr}")
        return "\n".join(lines) + "\n"

    def _gen_intel_md(self, v: dict) -> str:
        return textwrap.dedent(f"""\
            # Fraud Intelligence Report
            **Classification**: INTERNAL — Fraud Risk Management
            **Date**: 2019-10-15
            **Reference**: FIR-2019-047

            ## Executive Summary

            Intelligence gathered from partner networks and law enforcement
            liaisons indicates an increase in coordinated card-not-present (CNP)
            fraud targeting {v['target_mcc_group']} merchants during high-traffic
            shopping periods.

            ## Observed Pattern

            **{v['ring_name']}** (provisional designation) is believed to be an
            organized fraud ring operating across multiple metropolitan areas.
            Key characteristics:

            - **Target merchants**: Primarily {v['target_mcc_desc']}
            - **Timing**: Operations concentrated during {v['holiday_name']}
              and similar high-volume shopping events when transaction monitoring
              thresholds are elevated to reduce false positive declines
            - **Transaction profile**: High-value transactions (avg ~${v['avg_fraud_amount']:.2f})
              consistent with resale-oriented theft rather than personal use
            - **Estimated ring size**: Approximately {v['ring_size']} compromised
              accounts per cell, with multiple cells operating simultaneously

            ## Technical Indicators

            Compromised cards used by this ring tend to show:
            - Rapid sequential transactions at same or nearby MCCs
            - Transactions initiated in geographic clusters
            - Velocity inconsistent with cardholders' historical behavior

            ## Distractor: Unrelated Schemes

            Note: Separate intelligence (FIR-2019-031) relates to a phishing
            campaign targeting retail bank customers. This is believed to be
            unrelated to {v['ring_name']} and involves a different actor group
            focused on account takeover rather than CNP fraud.

            ## Recommendations

            Fraud teams should examine transaction clusters on
            {', '.join(v['holiday_dates'])} for MCC codes associated with
            {v['target_mcc_group']} merchants, applying enhanced velocity checks
            and consortium data correlation.

            ---
            *For internal fraud risk management use only.*
        """)

    # ── Spec / brief ──────────────────────────────────────────────────────────

    def _make_spec(self, v: dict, n_rows: int) -> str:
        return textwrap.dedent(f"""\
            # RDS26: Fraud Ring Investigation

            ## Background

            The fraud operations team has flagged an unusual cluster of fraudulent
            transactions in the credit card dataset. Standard anomaly detection
            models flagged elevated fraud rates, but the pattern is not explained
            by the usual individual-cardholder indicators alone.

            Your task is to identify the fraud ring's operational signature by
            synthesizing evidence from the transaction data and three reference
            documents.

            ## Dataset

            - File: `data/credit_card_fraud.csv`
            - Rows: {n_rows} (subsample)
            - Columns: Time (seconds from first transaction), V1–V28 (PCA-transformed
              features), Amount (transaction amount), Class (1=fraud, 0=legitimate)

            ## Corpus Documents

            Reference documents in `corpus/`:

            | File | Description |
            |------|-------------|
            | `mcc_codes.csv` | Merchant category codes, descriptions, and fraud risk tiers |
            | `holiday_calendar.csv` | Holiday and long-weekend dates with is_long_weekend flag |
            | `fraud_intelligence.md` | Internal fraud intelligence report |

            **No single document reveals the full pattern.** You must cross-reference
            the intelligence report's claims against the calendar and MCC reference data,
            then verify against the transaction data.

            ## Required Deliverables

            ### 1. `analysis.py`
            - Load transaction data and compute basic fraud statistics
            - Read all three corpus documents
            - Identify the MCC category and temporal pattern consistent with the
              intelligence report
            - Quantify how the fraud rate varies by identified dimensions

            ### 2. `results.json`
            ```json
            {{
              "overall_fraud_rate": <float>,
              "fraud_pattern": "<description of the cluster>",
              "target_merchant_category": "<mcc group>",
              "temporal_pattern": "<holiday/weekend/timing>",
              "ring_hypothesis": "<string>",
              "detection_rule": "<proposed rule>"
            }}
            ```

            ### 3. `report.md`
            400–600 words covering:
            - Statistical evidence for the anomalous cluster
            - MCC and temporal signature
            - Hypothesis about organized ring activity
            - Proposed targeted detection rule or real-time monitoring approach

            ## Grading Criteria
            1. `analysis.py` runs without error
            2. MCC / merchant category pattern identified
            3. Holiday / weekend temporal pattern identified
            4. Organized ring hypothesis stated
            5. `results.json` has `fraud_pattern` key
            6. `report.md` proposes detection rule or monitoring
            7. Data loaded correctly
            8. `results.json` valid JSON with required fields
        """)

    def _make_brief(self, v: dict) -> str:
        return textwrap.dedent(f"""\
            # RDS26: Fraud Ring Investigation (Brief)

            Investigate an unusual fraud cluster in credit card transaction data.
            Synthesize transaction patterns with corpus reference documents to
            identify the fraud ring's signature.

            **Dataset**: `data/credit_card_fraud.csv`

            **Corpus docs** (in `corpus/`):
            - `mcc_codes.csv`
            - `holiday_calendar.csv`
            - `fraud_intelligence.md`

            Produce:
            - `analysis.py` — investigation script
            - `results.json` — fraud pattern summary
            - `report.md` — findings and detection recommendations
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
                "description": "MCC / merchant category pattern identified in analysis or report",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    passed = False
                    detail = ""
                    terms = ["mcc", "merchant category", "merchant_category",
                             "electronics", "mcc_code", "category code",
                             "merchant type", "5065", "5734"]
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
                        detail = "MCC/merchant category terms not found"
                """),
            },
            {
                "id": "C3",
                "description": "Holiday / weekend temporal pattern identified",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    passed = False
                    detail = ""
                    terms = ["holiday", "weekend", "long weekend", "black friday",
                             "memorial day", "labor day", "thanksgiving",
                             "cyber monday", "shopping", "seasonal"]
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
                        detail = "holiday/weekend pattern terms not found"
                """),
            },
            {
                "id": "C4",
                "description": "Organized ring / coordinated fraud hypothesis in report",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "report.md"
                    passed = False
                    detail = ""
                    terms = ["ring", "organized", "coordinated", "group",
                             "syndicate", "network", "scheme", "actor",
                             "systematic", "deliberate"]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in terms if t in content]
                        passed = len(found) >= 2
                        detail = f"found: {found}"
                    else:
                        detail = "report.md not found"
                """),
            },
            {
                "id": "C5",
                "description": "results.json has fraud_pattern key",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    if p.exists():
                        try:
                            d = json.loads(p.read_text(encoding="utf-8"))
                            passed = "fraud_pattern" in d and bool(d["fraud_pattern"])
                            detail = f"fraud_pattern={d.get('fraud_pattern', 'MISSING')}"
                        except Exception as e:
                            detail = str(e)
                    else:
                        detail = "results.json not found"
                """),
            },
            {
                "id": "C6",
                "description": "report.md proposes detection rule or monitoring",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "report.md"
                    passed = False
                    detail = ""
                    terms = ["rule", "detect", "monitor", "alert", "threshold",
                             "flag", "block", "velocity", "real-time", "screening"]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        found = [t for t in terms if t in content]
                        passed = len(found) >= 2
                        detail = f"found: {found}"
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
                    p = pathlib.Path(workspace_dir) / "data" / "credit_card_fraud.csv"
                    passed = False
                    detail = ""
                    expected_rows = {n_rows}
                    if p.exists():
                        with open(p, newline="", encoding="utf-8") as fh:
                            actual = sum(1 for _ in csv.reader(fh)) - 1
                        passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.02))
                        detail = f"actual={{actual}}, expected={{expected_rows}}"
                    else:
                        detail = "data/credit_card_fraud.csv not found"
                """),
            },
            {
                "id": "C8",
                "description": "results.json is valid JSON with required fields",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    required = ["overall_fraud_rate", "fraud_pattern", "ring_hypothesis"]
                    if p.exists():
                        try:
                            d = json.loads(p.read_text(encoding="utf-8"))
                            missing = [f for f in required if f not in d]
                            passed = len(missing) == 0
                            detail = f"missing={missing}" if missing else "all required fields present"
                        except json.JSONDecodeError as e:
                            detail = f"JSON error: {e}"
                    else:
                        detail = "results.json not found"
                """),
            },
        ]
        return self.make_check_solution(checks)
