"""
Parameterized generator for RDS24: Online Retail Customer Segmentation
(Archetype 5 — Discovery).

Clean task: "Segment customers by purchase behavior."
The spec does NOT mention data quality issues. The executor must discover
and handle them during implementation.

Hidden issues injected per seed:
  Seed 0: InvoiceNo starting with 'C' are cancellations (must be excluded from RFM),
           25% rows have NaN CustomerID (cannot be assigned to any customer),
           some UnitPrice = 0.00 (free/promotional items or data errors)
  Seed 1: Cancellations plus negative Quantity rows, missing CustomerIDs,
           Description column has "POSTAGE" / "BANK CHARGES" / "MANUAL" entries
           (non-product transactions that inflate customer value)
  Seed 2: Cancellations, missing CustomerIDs, zero prices,
           plus some rows with Quantity < 0 and no matching invoice (unmatched returns)

Rubric checks (8):
  C1: analysis.py runs without error
  C2: Cancellations (InvoiceNo starting with 'C') handled
  C3: Missing CustomerID rows excluded from segmentation
  C4: Zero or negative prices / quantities addressed
  C5: At least 2 customer segments produced
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
    "InvoiceNo",
    "StockCode",
    "Description",
    "Quantity",
    "InvoiceDate",
    "UnitPrice",
    "CustomerID",
    "Country",
]

_NON_PRODUCT_DESCRIPTIONS = [
    "POSTAGE",
    "BANK CHARGES",
    "MANUAL",
    "AMAZON FEE",
    "CRUK COMMISSION",
    "CARRIAGE",
    "DOTCOM POSTAGE",
]

_VARIANTS = [
    {
        "seed_offset": 0,
        "cancellation_frac": 0.08,     # 8% of invoices are cancellations
        "missing_customer_frac": 0.25,  # 25% rows have no CustomerID
        "zero_price_frac": 0.04,        # 4% have UnitPrice = 0
        "negative_qty": False,
        "non_product_rows": False,
        "unmatched_returns": False,
        "description": "cancellation invoices (C-prefix), missing CustomerIDs, zero UnitPrice",
    },
    {
        "seed_offset": 10,
        "cancellation_frac": 0.06,
        "missing_customer_frac": 0.20,
        "zero_price_frac": 0.0,
        "negative_qty": True,           # negative quantities without C-invoices
        "n_neg_qty": 20,
        "non_product_rows": True,       # POSTAGE / BANK CHARGES
        "n_non_product": 30,
        "unmatched_returns": False,
        "description": "cancellations, missing CustomerIDs, negative quantities, non-product rows",
    },
    {
        "seed_offset": 20,
        "cancellation_frac": 0.07,
        "missing_customer_frac": 0.25,
        "zero_price_frac": 0.03,
        "negative_qty": True,
        "n_neg_qty": 15,
        "non_product_rows": False,
        "unmatched_returns": True,      # negative qty rows with no matching invoice
        "n_unmatched": 10,
        "description": "cancellations, missing CustomerIDs, zero prices, unmatched returns",
    },
]


class Generator(DiscoveryGenerator):
    task_id = "RDS24_retail_quality"
    domain = "data_science"
    difficulty = "hard"
    languages = ["python"]

    dataset_name = "online_retail"
    dataset_license = "CC BY 4.0"
    dataset_source = "UCI ML Repository / Online Retail Dataset"

    def generate(self, seed: int) -> GeneratedTask:
        variant = _VARIANTS[seed % len(_VARIANTS)]
        rng = SeededRandom(seed + variant["seed_offset"])

        rows = self.load_dataset()
        rows = self.subsample(rows, seed=seed + 600, frac=0.06)  # ~600 rows
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
            "data/transactions.csv": data_csv,
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

        # Inject cancellation invoices (C-prefix)
        cancel_n = max(1, int(n * variant["cancellation_frac"]))
        cancel_indices = rng.sample(range(n), min(cancel_n, n // 10))
        for i in cancel_indices:
            inv = result[i].get("InvoiceNo", "500000")
            result[i]["InvoiceNo"] = "C" + str(inv)
            # Cancellations typically have negative quantities
            try:
                qty = int(float(result[i].get("Quantity", "1") or "1"))
                result[i]["Quantity"] = str(-abs(qty))
            except (ValueError, TypeError):
                result[i]["Quantity"] = "-1"

        # Inject missing CustomerIDs
        missing_n = max(1, int(n * variant["missing_customer_frac"]))
        missing_indices = rng.sample(range(n), min(missing_n, n // 3))
        for i in missing_indices:
            result[i]["CustomerID"] = ""

        # Inject zero UnitPrice rows
        zero_price_frac = variant.get("zero_price_frac", 0.0)
        if zero_price_frac > 0:
            zero_n = max(1, int(n * zero_price_frac))
            zero_indices = rng.sample(range(n), min(zero_n, n // 20))
            for i in zero_indices:
                result[i]["UnitPrice"] = "0.0"

        # Inject negative quantity rows (not cancellations — no C-prefix)
        if variant.get("negative_qty"):
            neg_n = min(variant.get("n_neg_qty", 20), n // 20)
            neg_indices = rng.sample(range(n), neg_n)
            for i in neg_indices:
                try:
                    qty = int(float(result[i].get("Quantity", "1") or "1"))
                    result[i]["Quantity"] = str(-abs(qty))
                except (ValueError, TypeError):
                    result[i]["Quantity"] = "-2"

        # Inject non-product rows
        if variant.get("non_product_rows"):
            non_n = min(variant.get("n_non_product", 30), n // 15)
            non_indices = rng.sample(range(n), non_n)
            for i in non_indices:
                desc = rng.choice(_NON_PRODUCT_DESCRIPTIONS)
                result[i]["Description"] = desc
                result[i]["StockCode"] = "POST" if desc == "POSTAGE" else "M"
                result[i]["UnitPrice"] = str(round(rng.random() * 5, 2))

        # Inject unmatched returns
        if variant.get("unmatched_returns"):
            unm_n = min(variant.get("n_unmatched", 10), n // 40)
            unm_indices = rng.sample(range(n), unm_n)
            for i in unm_indices:
                # New invoice number not present elsewhere
                result[i]["InvoiceNo"] = "R" + str(rng.randint(900000, 999999))
                result[i]["Quantity"] = str(-rng.randint(1, 5))

        return result

    def _make_spec(self, n_rows: int) -> str:
        return textwrap.dedent(f"""\
            # RDS24: Customer Segmentation from Retail Transactions

            ## Task
            Segment customers by their purchase behavior using RFM (Recency, Frequency,
            Monetary) analysis on the provided online retail transaction dataset.

            ## Dataset
            - File: `data/transactions.csv`
            - Rows: {n_rows}
            - Columns: InvoiceNo, StockCode, Description, Quantity, InvoiceDate,
              UnitPrice, CustomerID, Country
            - Each row represents a line item in a retail transaction

            ## Your Task
            1. Load and explore `data/transactions.csv`
            2. Compute RFM metrics per customer:
               - **Recency**: days since last purchase
               - **Frequency**: number of unique invoices
               - **Monetary**: total spend
            3. Clean and filter the data as needed before computing RFM
            4. Segment customers into at least 2 groups (e.g., using K-means or
               quantile-based scoring)
            5. Save results and a report

            ## Required Deliverables

            ### 1. `analysis.py`
            A Python script that:
            - Loads `data/transactions.csv`
            - Cleans the data and computes RFM metrics per customer
            - Segments customers and saves `results.json` and `report.md`

            ### 2. `results.json`
            Must contain at minimum:
            ```json
            {{
              "n_customers": <int>,
              "n_segments": <int>,
              "segment_sizes": {{<str>: <int>, ...}},
              "rfm_stats": {{
                "mean_recency": <float>,
                "mean_frequency": <float>,
                "mean_monetary": <float>
              }}
            }}
            ```

            ### 3. `report.md`
            A brief (300–500 word) report covering:
            - Data cleaning decisions made before computing RFM
            - Description of each customer segment
            - Business recommendations for at least one segment
            - Limitations

            ## Grading Criteria
            1. `analysis.py` runs without error
            2. Cancellation invoices (InvoiceNo starting with 'C') are excluded
            3. Rows with missing CustomerID are excluded from segmentation
            4. Zero or negative prices / quantities are handled
            5. At least 2 customer segments are produced
            6. `results.json` contains required fields
            7. Data loaded correctly (expected row count)
            8. `report.md` discusses at least one data quality issue
        """)

    def _make_brief(self) -> str:
        return textwrap.dedent("""\
            # RDS24: Customer Segmentation (Brief)

            Segment customers by purchase behavior using `data/transactions.csv`.

            Compute RFM (Recency, Frequency, Monetary) metrics and produce clusters.

            Produce:
            - `analysis.py` — data cleaning + RFM computation + segmentation
            - `results.json` — segment counts and RFM summary stats
            - `report.md` — segment descriptions and data quality notes
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
                "description": "Cancellation invoices (InvoiceNo starting with 'C') handled",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    cancel_terms = [
                        "startswith", "str.startswith", "\"c\"", "'c'",
                        "cancel", "invoiceno", "invoice_no", "c-",
                        "exclude", "filter", "drop", "remove",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        has_inv = "invoiceno" in content or "invoice" in content
                        found = [t for t in cancel_terms if t in content]
                        passed = has_inv and len(found) >= 2
                        detail = f"invoice mentioned={has_inv}, cancel terms={found}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C3",
                "description": "Missing CustomerID rows excluded from segmentation",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    cust_terms = [
                        "customerid", "customer_id", "dropna", "isna",
                        "isnull", "notna", "notnull", "missing",
                        "exclude", "filter", "drop", "nan",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        has_cust = "customerid" in content
                        found = [t for t in cust_terms if t in content]
                        passed = has_cust and len(found) >= 2
                        detail = f"customerid mentioned={has_cust}, terms={found}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C4",
                "description": "Zero or negative prices / quantities addressed",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import pathlib
                    p = pathlib.Path(workspace_dir) / "analysis.py"
                    passed = False
                    detail = ""
                    qty_price_terms = [
                        "quantity", "unitprice", "price", "> 0", ">0",
                        "< 0", "<0", "positive", "negative", "filter",
                        "zero", "0.0", "exclude", "drop",
                    ]
                    if p.exists():
                        content = p.read_text(encoding="utf-8").lower()
                        has_qty = "quantity" in content
                        has_price = "unitprice" in content or "price" in content
                        found = [t for t in qty_price_terms if t in content]
                        passed = (has_qty or has_price) and len(found) >= 3
                        detail = f"qty={has_qty}, price={has_price}, terms={found}"
                    else:
                        detail = "analysis.py not found"
                """),
            },
            {
                "id": "C5",
                "description": "At least 2 customer segments produced in results.json",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    if p.exists():
                        try:
                            d = json.loads(p.read_text(encoding="utf-8"))
                            n_seg = d.get("n_segments", 0)
                            seg_sizes = d.get("segment_sizes", {})
                            if isinstance(n_seg, (int, float)):
                                passed = int(n_seg) >= 2
                            elif seg_sizes:
                                passed = len(seg_sizes) >= 2
                            detail = f"n_segments={n_seg}, segment_sizes keys={list(seg_sizes.keys())}"
                        except Exception as e:
                            detail = str(e)
                    else:
                        detail = "results.json not found"
                """),
            },
            {
                "id": "C6",
                "description": "results.json contains required fields (n_customers, n_segments, rfm_stats)",
                "type": "custom_python",
                "code": textwrap.dedent("""\
                    import json, pathlib
                    p = pathlib.Path(workspace_dir) / "results.json"
                    passed = False
                    detail = ""
                    required = ["n_customers", "n_segments"]
                    alt_keys = {
                        "n_customers": ["num_customers", "customer_count", "n_unique_customers"],
                        "n_segments": ["num_segments", "num_clusters", "n_clusters"],
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
                    p = pathlib.Path(workspace_dir) / "data" / "transactions.csv"
                    passed = False
                    detail = ""
                    expected_rows = {n_rows}
                    if p.exists():
                        with open(p, newline="", encoding="utf-8") as fh:
                            actual = sum(1 for _ in csv.reader(fh)) - 1
                        passed = abs(actual - expected_rows) <= max(5, int(expected_rows * 0.01))
                        detail = f"actual={{actual}}, expected={{expected_rows}}"
                    else:
                        detail = "data/transactions.csv not found"
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
                        "cancel", "missing", "null", "nan", "clean",
                        "quality", "outlier", "invalid", "filter",
                        "customerid", "invoice", "zero", "negative",
                        "exclude", "postage", "non-product",
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
