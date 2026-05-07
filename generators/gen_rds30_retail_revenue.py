"""
Generator for RDS30: Retail Revenue Drop Diagnosis (Archetype 2 — Synthesis).

Dataset: online_retail (InvoiceNo, StockCode, Description, Quantity, InvoiceDate,
                        UnitPrice, CustomerID, Country)

Task: Diagnose the revenue drop in Q4. The key insight (counter-intuitive) is that
a marketing campaign was running during the drop — so the decline is NOT from lack
of demand, but from a stockout of the top 5 products during peak campaign traffic.

Corpus documents:
  - marketing_campaigns.csv : Campaign schedule showing campaign was active during drop
  - inventory_levels.csv    : Stock levels showing stockout of top 5 products
  - customer_complaints.md  : Customer complaints about out-of-stock items

Synthesis: Revenue drop = stockout during campaign. Campaign drove demand but
inventory couldn't meet it. This is counter-intuitive (campaign + revenue drop).

Rubric (8 checks):
  C1 — analysis.py runs without error
  C2 — Stockout / inventory depletion identified
  C3 — Marketing campaign overlap with revenue drop identified
  C4 — Counter-intuitive diagnosis: campaign running during drop (not demand failure)
  C5 — results.json has root_cause key indicating stockout/inventory
  C6 — report.md quantifies lost revenue from stockout
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
        "drop_period": "Q4 2011 (Oct–Dec)",
        "drop_year": 2011,
        "drop_quarter": "Q4",
        "drop_months": ["2011-10", "2011-11", "2011-12"],
        "top_skus": ["85123A", "22423", "85099B", "47566", "20725"],
        "campaign_name": "Holiday Season Promotional Drive",
        "campaign_start": "2011-10-01",
        "campaign_end": "2011-12-31",
        "stockout_date": "2011-10-18",
        "revenue_drop_pct": 28,
        "lost_revenue_est": 142000,
        "complaint_theme": "customers unable to complete holiday orders due to out-of-stock status on featured items",
    },
    {
        "seed": 1,
        "drop_period": "Q4 2010 (Oct–Dec)",
        "drop_year": 2010,
        "drop_quarter": "Q4",
        "drop_months": ["2010-10", "2010-11", "2010-12"],
        "top_skus": ["22423", "84879", "21232", "22720", "85123A"],
        "campaign_name": "Black Friday Email Blast + Cyber Week",
        "campaign_start": "2010-11-01",
        "campaign_end": "2010-12-15",
        "stockout_date": "2010-11-12",
        "revenue_drop_pct": 31,
        "lost_revenue_est": 198000,
        "complaint_theme": "high volume of complaints from customers who clicked email promotions but found items out of stock at checkout",
    },
    {
        "seed": 2,
        "drop_period": "Q3 2011 (Jul–Sep)",
        "drop_year": 2011,
        "drop_quarter": "Q3",
        "drop_months": ["2011-07", "2011-08", "2011-09"],
        "top_skus": ["POST", "22423", "85099B", "20727", "22386"],
        "campaign_name": "Summer Clearance + Back-to-School Push",
        "campaign_start": "2011-07-15",
        "campaign_end": "2011-09-15",
        "stockout_date": "2011-07-22",
        "revenue_drop_pct": 19,
        "lost_revenue_est": 87000,
        "complaint_theme": "back-to-school promotional items sold out within days of campaign launch; repeat customers expressed frustration via support tickets",
    },
]

_KEEP_COLUMNS = [
    "InvoiceNo", "StockCode", "Description", "Quantity",
    "InvoiceDate", "UnitPrice", "CustomerID", "Country",
]


class Generator(SynthesisGenerator):
    task_id = "RDS30_retail_revenue"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]

    dataset_name = "online_retail"
    dataset_license = "CC-BY 4.0"
    dataset_source = "UCI ML Repository"

    def generate(self, seed: int) -> GeneratedTask:
        v = _VARIANTS[seed % len(_VARIANTS)]
        rng = SeededRandom(seed + 300)

        rows = self.load_dataset()
        rows = self.subsample(rows, seed=seed + 300, frac=0.01)   # ~5000 rows
        rows = self.select_columns(rows, _KEEP_COLUMNS)
        n_rows = len(rows)
        data_csv = self.rows_to_csv(rows, _KEEP_COLUMNS)

        corpus = {
            "marketing_campaigns.csv": self._gen_campaigns_csv(v, rng),
            "inventory_levels.csv": self._gen_inventory_csv(v, rng),
            "customer_complaints.md": self._gen_complaints_md(v),
        }

        requirements_txt = "pandas>=1.5\nnumpy>=1.23\nscipy>=1.9\n"
        task_yaml = self.make_task_yaml()
        check_py = self._make_check_solution(v, n_rows)

        workspace_files = {
            "data/online_retail.csv": data_csv,
            "requirements.txt": requirements_txt,
            "check_solution.py": check_py,
            "task.yaml": task_yaml,
        }

        expected = {
            "drop_period": v["drop_period"],
            "root_cause": "stockout_during_campaign",
            "top_skus_stockout": v["top_skus"],
            "campaign_name": v["campaign_name"],
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

    def _gen_campaigns_csv(self, v: dict, rng: SeededRandom) -> str:
        lines = ["campaign_name,start_date,end_date,channel,budget_gbp,target_segment,expected_uplift_pct"]
        # Main campaign running during the drop
        lines.append(
            f"{v['campaign_name']},{v['campaign_start']},{v['campaign_end']},"
            f"Email+Display,{round(rng.uniform(15000, 25000))},All customers,{round(rng.uniform(20, 35))}"
        )
        # Earlier campaigns (not overlapping — distractors)
        earlier = [
            ("Spring Newsletter", "2011-03-01", "2011-03-31", "Email", 5000, "Existing", 12),
            ("Summer Preview", "2011-05-15", "2011-06-30", "Display", 8000, "New", 18),
            ("Flash Sale Jan", "2011-01-10", "2011-01-15", "Email", 3000, "Lapsed", 25),
        ]
        for name, start, end, chan, budget, seg, uplift in earlier:
            # Adjust years for seed 1 which uses 2010
            start_adj = start.replace("2011", str(v["drop_year"] - 1 if v["drop_quarter"] == "Q4" else v["drop_year"]))
            end_adj = end.replace("2011", str(v["drop_year"] - 1 if v["drop_quarter"] == "Q4" else v["drop_year"]))
            lines.append(f"{name},{start_adj},{end_adj},{chan},{budget},{seg},{uplift}")
        return "\n".join(lines) + "\n"

    def _gen_inventory_csv(self, v: dict, rng: SeededRandom) -> str:
        lines = ["sku,description,date,units_in_stock,reorder_point,days_until_restock,status"]
        skus_desc = {
            "85123A": "WHITE HANGING HEART T-LIGHT HOLDER",
            "22423": "REGENCY CAKESTAND 3 TIER",
            "85099B": "JUMBO BAG RED RETROSPOT",
            "47566": "PARTY BUNTING",
            "20725": "LUNCH BAG RED RETROSPOT",
            "84879": "ASSORTED COLOUR BIRD ORNAMENT",
            "21232": "STRAWBERRY CERAMIC TRINKET BOX",
            "22720": "SET OF 3 CAKE TINS PANTRY DESIGN",
            "POST": "POSTAGE",
            "20727": "LUNCH BAG BLACK SKULL",
            "22386": "JUMBO BAG WOODLAND ANIMALS",
        }
        # Pre-stockout: normal levels
        for sku in v["top_skus"]:
            desc = skus_desc.get(sku, f"PRODUCT {sku}")
            lines.append(f"{sku},{desc},{v['campaign_start'][:7]}-01,{round(rng.uniform(200, 500))},50,0,IN_STOCK")

        # At stockout date
        for sku in v["top_skus"]:
            desc = skus_desc.get(sku, f"PRODUCT {sku}")
            lines.append(f"{sku},{desc},{v['stockout_date']},0,50,{round(rng.uniform(14, 28))},OUT_OF_STOCK")

        # Other skus (still in stock — distractors)
        other_skus = [s for s in skus_desc if s not in v["top_skus"]][:4]
        for sku in other_skus:
            desc = skus_desc.get(sku, f"PRODUCT {sku}")
            lines.append(f"{sku},{desc},{v['stockout_date']},{round(rng.uniform(80, 300))},30,0,IN_STOCK")

        return "\n".join(lines) + "\n"

    def _gen_complaints_md(self, v: dict) -> str:
        return textwrap.dedent(f"""\
            # Customer Complaints Summary Report
            **Period**: {v['drop_period']}
            **Source**: Customer Support Ticket System
            **Reference**: CS-REPORT-{v['drop_year']}-Q{v['drop_quarter'][1]}

            ## Executive Summary

            Customer support received a **{round(v['revenue_drop_pct'] * 3.2):,}% increase**
            in complaints during {v['drop_period']} compared to the same period
            in the prior year. The dominant theme: {v['complaint_theme']}.

            ## Complaint Categories

            | Category | Count | % of Total |
            |----------|-------|-----------|
            | Out-of-stock at checkout | 847 | 61% |
            | Order cancellation (no substitute available) | 312 | 22% |
            | Delayed shipment (backorder) | 143 | 10% |
            | Pricing complaints | 48 | 3% |
            | Other | 56 | 4% |

            ## Representative Customer Comments

            > "I received the promotional email for the {v['campaign_name']} and
            > clicked through immediately, but the featured items were already
            > out of stock. Very disappointing."

            > "I've been a loyal customer for 3 years. When I tried to reorder
            > my usual products during the sale, they were unavailable. I ended up
            > purchasing from a competitor."

            > "Your campaign said 'limited time offer' but the items were gone
            > within days. Please improve your inventory management before running
            > promotions."

            ## Inventory-Related Revenue Impact

            Based on abandoned cart analysis, an estimated **£{v['lost_revenue_est']:,}**
            in potential revenue was lost to stockout-related cart abandonment and
            order cancellations during the campaign period.

            ## Distractor: Pricing Complaints (Unrelated)

            A small number of complaints (3%) relate to pricing on non-featured items.
            These are consistent with historical complaint rates and are not considered
            related to the revenue decline under investigation.

            ---
            *Customer Experience Team — Internal Report*
        """)

    # ── Spec / brief ──────────────────────────────────────────────────────────

    def _make_spec(self, v: dict, n_rows: int) -> str:
        skus_str = ", ".join(v["top_skus"])
        return textwrap.dedent(f"""\
            # RDS30: Retail Revenue Drop Diagnosis

            ## Background

            Online retail transaction data shows a **{v['revenue_drop_pct']}% revenue
            decline** during **{v['drop_period']}** relative to the prior year's
            comparable period. The business stakeholders are puzzled because a major
            marketing campaign was running at the time.

            Your task is to diagnose the true root cause of the revenue drop.

            ## Dataset

            - File: `data/online_retail.csv`
            - Rows: {n_rows} (subsample)
            - Columns: `InvoiceNo`, `StockCode`, `Description`, `Quantity`,
              `InvoiceDate`, `UnitPrice`, `CustomerID`, `Country`
            - Revenue = `Quantity × UnitPrice` per line item

            ## Corpus Documents

            Reference documents in `corpus/`:

            | File | Description |
            |------|-------------|
            | `marketing_campaigns.csv` | Campaign schedule with dates, channels, and budgets |
            | `inventory_levels.csv` | Stock levels by SKU and date, including stockout events |
            | `customer_complaints.md` | Customer support complaint summary report |

            **The diagnosis is counter-intuitive**: a marketing campaign was actively
            running during the revenue drop. Do not assume the campaign failed.
            Synthesize all three documents to identify the actual root cause.

            ## Required Deliverables

            ### 1. `analysis.py`
            - Compute monthly/weekly revenue from transaction data
            - Identify the revenue drop period and magnitude
            - Read all three corpus documents
            - Identify the top revenue-generating SKUs and check their inventory status
            - Quantify the campaign-period overlap with the stockout event

            ### 2. `results.json`
            ```json
            {{
              "drop_period": "<period>",
              "revenue_drop_pct": <float>,
              "root_cause": "<string>",
              "stockout_skus": ["<sku1>", ...],
              "campaign_was_running": <bool>,
              "estimated_lost_revenue": <float>,
              "recommendation": "<string>"
            }}
            ```

            ### 3. `report.md`
            400–700 words covering:
            - Revenue decline magnitude and timing
            - Why demand was NOT the issue (campaign was running, driving traffic)
            - The stockout evidence and its timeline relative to the campaign
            - Customer complaint evidence corroborating the diagnosis
            - Estimated lost revenue and recommendation to prevent recurrence

            ## Grading Criteria
            1. `analysis.py` runs without error
            2. Stockout / inventory depletion identified
            3. Marketing campaign overlap with revenue drop identified
            4. Counter-intuitive diagnosis: campaign + stockout, not demand failure
            5. `results.json` has `root_cause` indicating stockout/inventory
            6. `report.md` quantifies or estimates lost revenue
            7. Data loaded correctly
            8. `results.json` valid JSON with required fields
        """)

    def _make_brief(self, v: dict) -> str:
        return textwrap.dedent(f"""\
            # RDS30: Retail Revenue Drop Diagnosis (Brief)

            Online retail data shows a {v['revenue_drop_pct']}% revenue drop in
            {v['drop_period']}. Diagnose the root cause — the answer may not be
            what you expect.

            **Dataset**: `data/online_retail.csv`

            **Corpus docs** (in `corpus/`):
            - `marketing_campaigns.csv`
            - `inventory_levels.csv`
            - `customer_complaints.md`

            Produce:
            - `analysis.py` — investigation script
            - `results.json` — root cause and revenue impact
            - `report.md` — narrative diagnosis and recommendations
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
                "description": "Stockout / inventory depletion identified",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    passed = False
                    detail = ""
                    terms = ["stockout", "stock out", "out of stock", "out_of_stock",
                             "inventory", "depleted", "zero stock", "backorder",
                             "unavailable", "sold out", "no stock"]
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
                        detail = "stockout/inventory terms not found"
                """),
            },
            {
                "id": "C3",
                "description": "Marketing campaign overlap with revenue drop identified",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    passed = False
                    detail = ""
                    terms = ["campaign", "marketing", "promotion", "promotional",
                             "email", "advertisement", "advertis", "marketing_campaign",
                             "campaign running", "campaign was"]
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
                        detail = "campaign/marketing terms not found"
                """),
            },
            {
                "id": "C4",
                "description": "Counter-intuitive diagnosis: campaign + stockout (not demand failure)",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    passed = False
                    detail = ""
                    # Must connect campaign to stockout as the mechanism
                    combined_terms = [
                        "campaign drove", "campaign increased", "campaign generated",
                        "demand was", "not demand", "sufficient demand", "demand existed",
                        "campaign during", "running during", "despite campaign",
                        "stockout during", "during the campaign", "campaign period",
                        "inventory could not", "supply could not", "unable to fulfill",
                        "inventory shortage", "fulfill demand",
                    ]
                    for fname in ["analysis.py", "report.md"]:
                        p = pathlib.Path(workspace_dir) / fname
                        if p.exists():
                            content = p.read_text(encoding="utf-8").lower()
                            found = [t for t in combined_terms if t in content]
                            if len(found) >= 1:
                                passed = True
                                detail = f"found in {fname}: {found}"
                                break
                    if not passed:
                        detail = "counter-intuitive diagnosis terms not found"
                """),
            },
            {
                "id": "C5",
                "description": "results.json has root_cause key indicating stockout/inventory",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    if p.exists():
                        try:
                            d = json.loads(p.read_text(encoding="utf-8"))
                            root_cause = str(d.get("root_cause", "")).lower()
                            stockout_terms = ["stockout", "stock", "inventory", "out_of_stock",
                                              "supply", "backorder", "depletion"]
                            found = [t for t in stockout_terms if t in root_cause]
                            passed = len(found) > 0
                            detail = f"root_cause='{root_cause}', matched={found}"
                        except Exception as e:
                            detail = str(e)
                    else:
                        detail = "results.json not found"
                """),
            },
            {
                "id": "C6",
                "description": "report.md quantifies or estimates lost revenue",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib, re
                    p = pathlib.Path(workspace_dir) / "report.md"
                    passed = False
                    detail = ""
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        # Look for currency amounts or percentage loss
                        has_currency = bool(re.search(r'[£$€]\\s*\\d', content))
                        has_pct = bool(re.search(r'\\d+\\s*%', content))
                        has_revenue_est = any(t in content for t in [
                            "lost revenue", "revenue loss", "estimated loss",
                            "lost sales", "foregone revenue", "missed revenue",
                            "revenue impact", "lost £", "lost $"
                        ])
                        passed = has_currency or has_revenue_est or has_pct
                        detail = f"currency={has_currency}, pct={has_pct}, revenue_est={has_revenue_est}"
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
                    p = pathlib.Path(workspace_dir) / "data" / "online_retail.csv"
                    passed = False
                    detail = ""
                    expected_rows = {n_rows}
                    if p.exists():
                        with open(p, newline="", encoding="utf-8") as fh:
                            actual = sum(1 for _ in csv.reader(fh)) - 1
                        passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.02))
                        detail = f"actual={{actual}}, expected={{expected_rows}}"
                    else:
                        detail = "data/online_retail.csv not found"
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
                    required = ["root_cause", "campaign_was_running", "recommendation"]
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
