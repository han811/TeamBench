"""
Parameterized generator for PIPE1: ETL Schema Mapping Fix.

Each seed produces:
  - A different domain (e-commerce, healthcare, financial, logistics)
  - Different field renames (3-6 fields changed between old and new source schema)
  - Different type conversions (date formats, numeric precision, encodings)
  - Different nested-to-flat transformations
  - Different null/missing-value handling rules
  - Different enum value mappings

TNI Design:
  - Brief tells the executor: "ETL pipeline broke after source schema update; the Planner has mapping rules."
  - Spec (Planner-visible) has: old schema, new schema, target schema, and full mapping/edge-case rules.
  - Workspace has: etl.py (uses OLD field names), source_sample.json (NEW format), target_schema.json.
  - Executor can see the new field names in source_sample.json but NOT the full mapping/edge-case rules.
"""
from __future__ import annotations

import json
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# ── Domain definitions ────────────────────────────────────────────────────────
# Each domain specifies:
#   old_fields: field names the ETL currently uses (old source schema)
#   new_fields: field names now produced by the source (new source schema)
#   target_fields: fields the destination expects (unchanged)
#   field_map: new_source_field -> target_field (some are renames, some are identity after conversion)
#   type_conversions: field -> (old_type_desc, new_type_desc, conversion_hint)
#   nested_fields: fields that are now nested in the new schema (must be flattened)
#   enum_maps: field -> {old_value: new_value}
#   null_rules: field -> default_value_when_null

DOMAINS = [
    {
        "name": "ecommerce",
        "display": "E-Commerce Orders",
        "old_fields": [
            "order_id", "customer_name", "product_sku", "quantity",
            "unit_price", "order_date", "status", "discount_pct",
        ],
        "new_fields": [
            "id", "buyer_full_name", "sku_code", "qty",
            "price_usd", "placed_at", "order_status", "discount_percent",
            "shipping_address_city", "shipping_address_country",
        ],
        "target_fields": [
            "order_id", "customer_name", "product_sku", "quantity",
            "unit_price", "order_date", "status", "discount_pct",
            "city", "country",
        ],
        "field_map": {
            "id": "order_id",
            "buyer_full_name": "customer_name",
            "sku_code": "product_sku",
            "qty": "quantity",
            "price_usd": "unit_price",
            "placed_at": "order_date",
            "order_status": "status",
            "discount_percent": "discount_pct",
            "shipping_address_city": "city",
            "shipping_address_country": "country",
        },
        "type_conversions": {
            "placed_at": ("YYYY-MM-DD", "ISO-8601 datetime (YYYY-MM-DDTHH:MM:SSZ)", "extract date portion: value[:10]"),
            "price_usd": ("float", "string with currency prefix (e.g. 'USD 29.99')", "strip 'USD ' prefix and convert to float"),
            "discount_percent": ("integer 0-100", "decimal fraction 0.0-1.0", "multiply by 100 and round to int"),
        },
        "nested_fields": {
            "shipping_address_city": "shipping_address.city",
            "shipping_address_country": "shipping_address.country",
        },
        "enum_maps": {
            "order_status": {
                "PENDING": "pending",
                "SHIPPED": "shipped",
                "DELIVERED": "delivered",
                "CANCELLED": "cancelled",
            },
        },
        "null_rules": {
            "discount_pct": 0,
            "city": "unknown",
            "country": "unknown",
        },
    },
    {
        "name": "healthcare",
        "display": "Healthcare Patient Records",
        "old_fields": [
            "patient_id", "last_name", "first_name", "dob",
            "diagnosis_code", "visit_date", "provider_npi", "copay_amount",
        ],
        "new_fields": [
            "record_uid", "surname", "given_name", "birth_date",
            "icd10_code", "encounter_dt", "npi", "copay_cents",
            "insurance_plan_id", "insurance_plan_name",
        ],
        "target_fields": [
            "patient_id", "last_name", "first_name", "dob",
            "diagnosis_code", "visit_date", "provider_npi", "copay_amount",
            "plan_id", "plan_name",
        ],
        "field_map": {
            "record_uid": "patient_id",
            "surname": "last_name",
            "given_name": "first_name",
            "birth_date": "dob",
            "icd10_code": "diagnosis_code",
            "encounter_dt": "visit_date",
            "npi": "provider_npi",
            "copay_cents": "copay_amount",
            "insurance_plan_id": "plan_id",
            "insurance_plan_name": "plan_name",
        },
        "type_conversions": {
            "birth_date": ("MM/DD/YYYY", "YYYY-MM-DD", "reformat: datetime.strptime(v, '%Y-%m-%d').strftime('%m/%d/%Y')"),
            "encounter_dt": ("YYYY-MM-DD", "Unix timestamp (integer seconds)", "datetime.fromtimestamp(v).strftime('%Y-%m-%d')"),
            "copay_cents": ("float dollars (e.g. 25.00)", "integer cents (e.g. 2500)", "divide by 100 to get float dollars"),
        },
        "nested_fields": {
            "insurance_plan_id": "insurance.plan_id",
            "insurance_plan_name": "insurance.plan_name",
        },
        "enum_maps": {
            "icd10_code": {
                "J06.9": "J06.9",  # same but validates mapping exists
                "Z00.00": "Z00.00",
            },
        },
        "null_rules": {
            "copay_amount": 0.0,
            "plan_id": "SELF_PAY",
            "plan_name": "Self Pay",
        },
    },
    {
        "name": "financial",
        "display": "Financial Transactions",
        "old_fields": [
            "txn_id", "account_num", "merchant_name", "amount",
            "currency", "txn_date", "category", "is_flagged",
        ],
        "new_fields": [
            "transaction_reference", "acct_number", "payee",
            "debit_amount_minor", "currency_code", "posted_timestamp",
            "mcc_category", "fraud_flag",
            "card_last4", "card_network",
        ],
        "target_fields": [
            "txn_id", "account_num", "merchant_name", "amount",
            "currency", "txn_date", "category", "is_flagged",
            "card_last4", "card_network",
        ],
        "field_map": {
            "transaction_reference": "txn_id",
            "acct_number": "account_num",
            "payee": "merchant_name",
            "debit_amount_minor": "amount",
            "currency_code": "currency",
            "posted_timestamp": "txn_date",
            "mcc_category": "category",
            "fraud_flag": "is_flagged",
            "card_last4": "card_last4",
            "card_network": "card_network",
        },
        "type_conversions": {
            "debit_amount_minor": ("float dollars", "integer minor units (cents)", "divide by 100 to get float dollars"),
            "posted_timestamp": ("YYYY-MM-DD string", "Unix timestamp integer (ms)", "convert: datetime.fromtimestamp(v/1000).strftime('%Y-%m-%d')"),
            "fraud_flag": ("boolean True/False", "integer 0 or 1", "cast to bool: bool(int(v))"),
        },
        "nested_fields": {
            "card_last4": "card_info.last4",
            "card_network": "card_info.network",
        },
        "enum_maps": {
            "mcc_category": {
                "GROC": "groceries",
                "TRVL": "travel",
                "DINE": "dining",
                "UTIL": "utilities",
                "FUEL": "fuel",
                "HLTH": "healthcare",
                "ENTR": "entertainment",
                "OTHR": "other",
            },
        },
        "null_rules": {
            "card_last4": "0000",
            "card_network": "unknown",
            "is_flagged": False,
        },
    },
    {
        "name": "logistics",
        "display": "Logistics Shipments",
        "old_fields": [
            "shipment_id", "origin_city", "destination_city", "weight_kg",
            "carrier", "shipped_date", "estimated_days", "tracking_num",
        ],
        "new_fields": [
            "tracking_reference", "origin", "destination", "gross_weight_grams",
            "carrier_code", "dispatch_date", "transit_days_estimate", "tracking_number",
            "origin_country_code", "destination_country_code",
        ],
        "target_fields": [
            "shipment_id", "origin_city", "destination_city", "weight_kg",
            "carrier", "shipped_date", "estimated_days", "tracking_num",
            "origin_country", "destination_country",
        ],
        "field_map": {
            "tracking_reference": "shipment_id",
            "origin": "origin_city",
            "destination": "destination_city",
            "gross_weight_grams": "weight_kg",
            "carrier_code": "carrier",
            "dispatch_date": "shipped_date",
            "transit_days_estimate": "estimated_days",
            "tracking_number": "tracking_num",
            "origin_country_code": "origin_country",
            "destination_country_code": "destination_country",
        },
        "type_conversions": {
            "gross_weight_grams": ("float kilograms", "integer grams", "divide by 1000 to get kilograms, round to 3 decimal places"),
            "dispatch_date": ("YYYY-MM-DD", "DD/MM/YYYY", "reformat: datetime.strptime(v, '%d/%m/%Y').strftime('%Y-%m-%d')"),
            "transit_days_estimate": ("integer days", "string like '3d' or '5d'", "strip trailing 'd' and convert to int"),
        },
        "nested_fields": {
            "origin_country_code": "origin_location.country_code",
            "destination_country_code": "destination_location.country_code",
        },
        "enum_maps": {
            "carrier_code": {
                "UPS": "ups",
                "FEDEX": "fedex",
                "DHL": "dhl",
                "USPS": "usps",
                "AMAZON": "amazon_logistics",
            },
        },
        "null_rules": {
            "origin_country": "XX",
            "destination_country": "XX",
            "estimated_days": 0,
        },
    },
]


def _make_ecommerce_record(rng: SeededRandom, idx: int) -> dict:
    """Generate one e-commerce record in NEW source format."""
    cities = ["New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
              "Seattle", "Denver", "Boston", "Miami", "Austin"]
    countries = ["US", "CA", "GB", "AU", "DE", "FR", "JP", "MX"]
    skus = ["SKU-A1", "SKU-B2", "SKU-C3", "SKU-D4", "SKU-E5",
            "SKU-F6", "SKU-G7", "SKU-H8"]
    statuses = ["PENDING", "SHIPPED", "DELIVERED", "CANCELLED"]
    first_names = ["Alice", "Bob", "Carol", "David", "Emma",
                   "Frank", "Grace", "Henry", "Iris", "Jack"]
    last_names = ["Smith", "Jones", "Brown", "Davis", "Wilson",
                  "Taylor", "Anderson", "Thomas", "Jackson", "White"]

    discount_raw = rng.choice([0.0, 0.05, 0.10, 0.15, 0.20, 0.25])
    price_raw = round(rng.uniform(5.0, 299.99), 2)
    city = rng.choice(cities) if rng.random() > 0.1 else None
    country = rng.choice(countries) if city is not None else None

    rec = {
        "id": f"ORD-{10000 + idx}",
        "buyer_full_name": f"{rng.choice(first_names)} {rng.choice(last_names)}",
        "sku_code": rng.choice(skus),
        "qty": rng.randint(1, 10),
        "price_usd": f"USD {price_raw:.2f}",
        "placed_at": f"2024-{rng.randint(1,12):02d}-{rng.randint(1,28):02d}T{rng.randint(0,23):02d}:{rng.randint(0,59):02d}:00Z",
        "order_status": rng.choice(statuses),
        "discount_percent": discount_raw,
        "shipping_address": {
            "city": city,
            "country": country,
        },
    }
    return rec


def _make_healthcare_record(rng: SeededRandom, idx: int) -> dict:
    """Generate one healthcare record in NEW source format."""
    import datetime
    surnames = ["Johnson", "Williams", "Brown", "Davis", "Miller",
                "Wilson", "Moore", "Taylor", "Anderson", "Thomas"]
    given_names = ["James", "Mary", "John", "Patricia", "Robert",
                   "Jennifer", "Michael", "Linda", "William", "Barbara"]
    icd10_codes = ["J06.9", "Z00.00", "I10", "E11.9", "M54.5",
                   "J18.9", "N39.0", "K21.0", "F41.1", "G43.909"]
    npis = [f"1{rng.randint(100000000, 999999999)}" for _ in range(3)]

    # birth_date: new format is YYYY-MM-DD (old was MM/DD/YYYY)
    year = rng.randint(1940, 2005)
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    birth_date_new = f"{year}-{month:02d}-{day:02d}"

    # encounter_dt: new format is Unix timestamp
    base = datetime.datetime(2024, 1, 1)
    offset_days = rng.randint(0, 364)
    enc_dt = base + datetime.timedelta(days=offset_days)
    encounter_ts = int(enc_dt.timestamp())

    copay_dollars = rng.choice([0.0, 20.0, 35.0, 50.0, 75.0, 100.0])
    copay_cents = int(copay_dollars * 100)

    has_insurance = rng.random() > 0.15
    plan_id = f"PLN-{rng.randint(100, 999)}" if has_insurance else None
    plan_name = rng.choice(["BlueCross", "Aetna", "UnitedHealth", "Cigna", "Humana"]) if has_insurance else None

    rec = {
        "record_uid": f"PAT-{20000 + idx}",
        "surname": rng.choice(surnames),
        "given_name": rng.choice(given_names),
        "birth_date": birth_date_new,
        "icd10_code": rng.choice(icd10_codes),
        "encounter_dt": encounter_ts,
        "npi": rng.choice(npis) if npis else "1234567890",
        "copay_cents": copay_cents,
        "insurance": {
            "plan_id": plan_id,
            "plan_name": plan_name,
        },
    }
    return rec


def _make_financial_record(rng: SeededRandom, idx: int) -> dict:
    """Generate one financial transaction record in NEW source format."""
    import datetime
    merchants = ["Amazon", "Walmart", "Target", "Whole Foods", "Shell",
                 "Delta Airlines", "Netflix", "Spotify", "CVS", "Starbucks"]
    mcc_cats = ["GROC", "TRVL", "DINE", "UTIL", "FUEL", "HLTH", "ENTR", "OTHR"]
    currencies = ["USD", "EUR", "GBP", "CAD", "AUD"]
    networks = ["Visa", "Mastercard", "Amex", "Discover"]

    amount_minor = rng.randint(100, 50000)  # cents
    base = datetime.datetime(2024, 1, 1)
    offset_days = rng.randint(0, 364)
    txn_dt = base + datetime.timedelta(days=offset_days)
    posted_ts_ms = int(txn_dt.timestamp() * 1000)

    has_card = rng.random() > 0.1
    last4 = f"{rng.randint(1000, 9999)}" if has_card else None
    network = rng.choice(networks) if has_card else None

    rec = {
        "transaction_reference": f"TXN-{30000 + idx}",
        "acct_number": f"ACCT-{rng.randint(10000, 99999)}",
        "payee": rng.choice(merchants),
        "debit_amount_minor": amount_minor,
        "currency_code": rng.choice(currencies),
        "posted_timestamp": posted_ts_ms,
        "mcc_category": rng.choice(mcc_cats),
        "fraud_flag": rng.choice([0, 1, 0, 0, 0, 0, 0, 0]),  # mostly 0
        "card_info": {
            "last4": last4,
            "network": network,
        },
    }
    return rec


def _make_logistics_record(rng: SeededRandom, idx: int) -> dict:
    """Generate one logistics shipment record in NEW source format."""
    cities = ["New York", "Los Angeles", "Chicago", "Houston",
              "Toronto", "London", "Berlin", "Tokyo", "Sydney", "Paris"]
    country_codes = ["US", "CA", "GB", "DE", "JP", "AU", "FR", "MX", "CN", "BR"]
    carrier_codes = ["UPS", "FEDEX", "DHL", "USPS", "AMAZON"]

    weight_grams = rng.randint(100, 30000)
    day = rng.randint(1, 28)
    month = rng.randint(1, 12)
    dispatch_date_new = f"{day:02d}/{month:02d}/2024"  # DD/MM/YYYY

    transit_days = rng.randint(1, 14)
    transit_str = f"{transit_days}d"

    orig_country = rng.choice(country_codes)
    dest_country = rng.choice(country_codes)

    rec = {
        "tracking_reference": f"SHP-{40000 + idx}",
        "origin": rng.choice(cities),
        "destination": rng.choice(cities),
        "gross_weight_grams": weight_grams,
        "carrier_code": rng.choice(carrier_codes),
        "dispatch_date": dispatch_date_new,
        "transit_days_estimate": transit_str,
        "tracking_number": f"1Z{rng.randint(100000000, 999999999)}",
        "origin_location": {
            "country_code": orig_country if rng.random() > 0.1 else None,
        },
        "destination_location": {
            "country_code": dest_country if rng.random() > 0.1 else None,
        },
    }
    return rec


_RECORD_MAKERS = [
    _make_ecommerce_record,
    _make_healthcare_record,
    _make_financial_record,
    _make_logistics_record,
]


def _transform_record(domain: dict, raw: dict, rng: SeededRandom) -> dict:
    """Apply the full mapping from new-source record to target record."""
    import datetime

    domain_name = domain["name"]
    null_rules = domain["null_rules"]
    field_map = domain["field_map"]
    nested_fields = domain["nested_fields"]
    enum_maps = domain["enum_maps"]

    # Step 1: flatten nested fields into top-level
    flat = {}
    for k, v in raw.items():
        if isinstance(v, dict):
            for sub_k, sub_v in v.items():
                # The nested_fields dict maps flat_name -> nested_path
                # Reverse: find entries where nested_path ends with sub_k
                for flat_name, nested_path in nested_fields.items():
                    parts = nested_path.split(".")
                    if parts[0] == k and parts[1] == sub_k:
                        flat[flat_name] = sub_v
        else:
            flat[k] = v

    # Step 2: rename fields per field_map
    target = {}
    for new_name, target_name in field_map.items():
        val = flat.get(new_name)
        target[target_name] = val

    # Step 3: apply type conversions
    if domain_name == "ecommerce":
        # price_usd: "USD 29.99" -> float
        if target.get("unit_price") is not None:
            s = str(target["unit_price"])
            if s.startswith("USD "):
                target["unit_price"] = float(s[4:])
        # placed_at: ISO datetime -> date string
        if target.get("order_date") is not None:
            target["order_date"] = str(target["order_date"])[:10]
        # discount_percent: 0.0-1.0 -> int 0-100
        if target.get("discount_pct") is not None:
            target["discount_pct"] = int(round(float(target["discount_pct"]) * 100))
        # enum: order_status -> lowercase
        if target.get("status") is not None:
            em = enum_maps.get("order_status", {})
            target["status"] = em.get(str(target["status"]), str(target["status"]).lower())

    elif domain_name == "healthcare":
        # birth_date: YYYY-MM-DD -> MM/DD/YYYY
        if target.get("dob") is not None:
            try:
                dt = datetime.datetime.strptime(str(target["dob"]), "%Y-%m-%d")
                target["dob"] = dt.strftime("%m/%d/%Y")
            except ValueError:
                pass
        # encounter_dt: unix timestamp -> YYYY-MM-DD
        if target.get("visit_date") is not None:
            try:
                target["visit_date"] = datetime.datetime.fromtimestamp(
                    int(target["visit_date"])
                ).strftime("%Y-%m-%d")
            except (ValueError, TypeError, OSError):
                pass
        # copay_cents: int -> float dollars
        if target.get("copay_amount") is not None:
            try:
                target["copay_amount"] = int(target["copay_amount"]) / 100.0
            except (ValueError, TypeError):
                pass

    elif domain_name == "financial":
        # debit_amount_minor: int cents -> float dollars
        if target.get("amount") is not None:
            try:
                target["amount"] = int(target["amount"]) / 100.0
            except (ValueError, TypeError):
                pass
        # posted_timestamp (ms) -> YYYY-MM-DD
        if target.get("txn_date") is not None:
            try:
                target["txn_date"] = datetime.datetime.fromtimestamp(
                    int(target["txn_date"]) / 1000
                ).strftime("%Y-%m-%d")
            except (ValueError, TypeError, OSError):
                pass
        # fraud_flag: int 0/1 -> bool
        if target.get("is_flagged") is not None:
            target["is_flagged"] = bool(int(target["is_flagged"]))
        # mcc_category enum
        if target.get("category") is not None:
            em = enum_maps.get("mcc_category", {})
            target["category"] = em.get(str(target["category"]), str(target["category"]).lower())

    elif domain_name == "logistics":
        # gross_weight_grams: int grams -> float kg
        if target.get("weight_kg") is not None:
            try:
                target["weight_kg"] = round(int(target["weight_kg"]) / 1000.0, 3)
            except (ValueError, TypeError):
                pass
        # dispatch_date: DD/MM/YYYY -> YYYY-MM-DD
        if target.get("shipped_date") is not None:
            try:
                dt = datetime.datetime.strptime(str(target["shipped_date"]), "%d/%m/%Y")
                target["shipped_date"] = dt.strftime("%Y-%m-%d")
            except ValueError:
                pass
        # transit_days_estimate: "3d" -> int
        if target.get("estimated_days") is not None:
            try:
                s = str(target["estimated_days"])
                target["estimated_days"] = int(s.rstrip("d"))
            except (ValueError, AttributeError):
                pass
        # carrier_code enum
        if target.get("carrier") is not None:
            em = enum_maps.get("carrier_code", {})
            target["carrier"] = em.get(str(target["carrier"]), str(target["carrier"]).lower())

    # Step 4: apply null/default rules
    for field_name, default_val in null_rules.items():
        if target.get(field_name) is None:
            target[field_name] = default_val

    return target


class Generator(TaskGenerator):
    task_id = "PIPE1_etl_fix"
    domain = "pipeline"
    difficulty = "medium"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # Pick domain deterministically from seed
        domain = DOMAINS[seed % len(DOMAINS)]
        record_maker = _RECORD_MAKERS[seed % len(_RECORD_MAKERS)]

        # Generate 10 source records in NEW format
        raw_records = []
        for i in range(10):
            rec = record_maker(rng, i)
            raw_records.append(rec)

        # Compute expected transformed records
        expected_records = []
        for rec in raw_records:
            transformed = _transform_record(domain, rec, rng)
            expected_records.append(transformed)

        # Build expected dict for grader
        target_fields = domain["target_fields"]
        expected = {
            "domain": domain["name"],
            "record_count": len(expected_records),
            "target_fields": target_fields,
            "field_map": domain["field_map"],
            "null_rules": {k: str(v) for k, v in domain["null_rules"].items()},
            "records": expected_records,
        }

        # Build workspace files
        workspace_files = {}

        # source_sample.json — new format (executor can see new field names)
        workspace_files["source_sample.json"] = json.dumps(raw_records, indent=2)

        # target_schema.json — what the destination expects
        target_schema = {
            "description": f"Target schema for {domain['display']} pipeline",
            "fields": [
                {"name": f, "required": True}
                for f in target_fields
            ],
        }
        workspace_files["target_schema.json"] = json.dumps(target_schema, indent=2)

        # etl.py — broken: uses OLD field names, missing type conversions
        workspace_files["etl.py"] = self._generate_buggy_etl(domain)

        # run_etl.py — runner
        workspace_files["run_etl.py"] = self._generate_runner()

        # Spec and brief
        spec_md = self._generate_spec(domain)
        brief_md = self._generate_brief(domain)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _generate_buggy_etl(self, domain: dict) -> str:
        """Generate a broken etl.py that uses OLD field names and lacks conversions."""
        old_fields = domain["old_fields"]
        target_fields = domain["target_fields"]
        domain_name = domain["name"]

        # Build a naive pass-through that reads old field names (will KeyError on new data)
        field_assignments = "\n".join(
            f'        "{tf}": record.get("{of}", None),  # BUG: source field renamed'
            for of, tf in zip(old_fields, target_fields)
        )

        return f'''"""
ETL pipeline for {domain["display"]}.
Transform source records into the target schema.

STATUS: BROKEN — source system updated its schema. Field names, types, and
structure have changed. The transform() function still uses old field names.
"""
import json
import sys


def transform(record: dict) -> dict:
    """
    Transform a source record to the target schema.

    BUG: Uses old source field names. Source now uses different field names.
    BUG: Missing type conversions (dates, amounts, enums, nested fields).
    BUG: No null/default handling for optional fields.
    """
    return {{
{field_assignments}
    }}


def run(source_path: str, output_path: str) -> None:
    with open(source_path, "r", encoding="utf-8") as f:
        records = json.load(f)

    results = []
    for i, record in enumerate(records):
        try:
            results.append(transform(record))
        except Exception as e:
            print(f"ERROR transforming record {{i}}: {{e}}", file=sys.stderr)
            raise

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Transformed {{len(results)}} records -> {{output_path}}")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else "source_sample.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "output.json"
    run(src, out)
'''

    def _generate_runner(self) -> str:
        return '''"""
Runner: process source_sample.json through ETL, write output.json.
Run with: python run_etl.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from etl import run

if __name__ == "__main__":
    run("source_sample.json", "output.json")
    print("ETL complete. Output written to output.json")
'''

    def _generate_spec(self, domain: dict) -> str:
        """Full spec for Planner — contains all mapping rules and edge cases."""
        domain_name = domain["name"]
        domain_display = domain["display"]
        old_fields = domain["old_fields"]
        new_fields = domain["new_fields"]
        target_fields = domain["target_fields"]
        field_map = domain["field_map"]
        type_conversions = domain["type_conversions"]
        nested_fields = domain["nested_fields"]
        enum_maps = domain["enum_maps"]
        null_rules = domain["null_rules"]

        # Build mapping table
        mapping_rows = "\n".join(
            f"| `{nf}` | `{tf}` |"
            for nf, tf in field_map.items()
        )

        # Build type conversion table
        type_rows = "\n".join(
            f"| `{field}` | {old_t} | {new_t} | {hint} |"
            for field, (old_t, new_t, hint) in type_conversions.items()
        )

        # Build nested field table
        nested_rows = "\n".join(
            f"| `{nested_path}` | `{flat_name}` |"
            for flat_name, nested_path in nested_fields.items()
        )

        # Build enum map tables
        enum_sections = ""
        for field_name, mapping in enum_maps.items():
            rows = "\n".join(f"| `{k}` | `{v}` |" for k, v in mapping.items())
            enum_sections += f"""
### Enum Mapping: `{field_name}`
| Old Value | New Value |
|-----------|-----------|
{rows}
"""

        # Build null rules
        null_rows = "\n".join(
            f"| `{field}` | `{default}` |"
            for field, default in null_rules.items()
        )

        return f"""# PIPE1: ETL Schema Mapping Fix — Planner Specification

## Domain
{domain_display}

## Situation
The source system updated its data schema. The ETL pipeline (`etl.py`) still uses the
**old** field names and types. The Executor has the broken ETL code and sample data
in the new format. The Executor does NOT have the full field mapping or conversion rules.

Your job as Planner is to relay the complete mapping rules to the Executor so they
can fix `etl.py`.

---

## Schema Overview

### Old Source Schema (what ETL currently expects)
Fields: {", ".join(f"`{f}`" for f in old_fields)}

### New Source Schema (what source now produces)
Top-level fields: {", ".join(f"`{f}`" for f in new_fields)}
Note: some fields are now **nested** (see Nested Fields section).

### Target Schema (destination — unchanged)
Fields: {", ".join(f"`{f}`" for f in target_fields)}

---

## Field Renaming Map

The following new source fields must be mapped to target fields:

| New Source Field | Target Field |
|-----------------|--------------|
{mapping_rows}

---

## Nested Field Flattening

Some fields in the new source schema are nested inside sub-objects.
They must be extracted (flattened) before renaming:

| Nested Path in Source | Flat Target Field |
|-----------------------|------------------|
{nested_rows}

---

## Type Conversions

The following fields require type or format conversion during transform:

| Field (target name) | Old Format | New Source Format | Conversion Rule |
|--------------------|------------|-------------------|-----------------|
{type_rows}

---
{enum_sections}
---

## Null / Missing Value Handling

When a field is `null` or missing in the source, use these defaults:

| Target Field | Default Value |
|-------------|---------------|
{null_rows}

---

## Edge Cases

1. **Nested objects**: If a nested sub-object itself is `null`, all child fields must use their defaults.
2. **Type conversion failures**: If a type conversion fails (e.g., bad date format), log the error and use the field's default value.
3. **Extra fields**: The source may contain fields not in the target schema — they must be dropped.
4. **Field ordering**: Output records must contain exactly the target fields, in target schema order.

---

## Deliverables

The Executor must fix `etl.py` so that:
- `python run_etl.py` completes without errors
- `output.json` contains all {10} source records transformed correctly
- All field renames applied
- All nested fields flattened
- All type conversions applied
- All null defaults applied
- Output records contain only target schema fields in correct order
"""

    def _generate_brief(self, domain: dict) -> str:
        """Brief for Executor — describes the problem WITHOUT the mapping rules."""
        return f"""# PIPE1: ETL Schema Mapping Fix (Brief)

## Situation

The ETL pipeline for **{domain["display"]}** is broken. The source system recently
updated its data schema, and `etl.py` now fails when run against the new data.

**The Planner has the full schema mapping rules.** Coordinate with the Planner
to get the field renaming, type conversion, and null-handling rules you need.

## What You Have

- `etl.py` — the broken transform pipeline (uses old field names)
- `source_sample.json` — 10 sample records in the **new** source format
- `target_schema.json` — the target schema the destination expects (unchanged)
- `run_etl.py` — runner script

## What's Wrong

The `transform()` function in `etl.py` references old field names that no longer
exist in the source. The source data structure has also changed (new field names,
different types, nested objects). The ETL crashes immediately.

## What You Must Produce

Fix `etl.py` so that:
1. `python run_etl.py` completes without errors
2. `output.json` is written with all 10 records correctly transformed

**Do not modify `run_etl.py` or `source_sample.json`.**
Ask the Planner for the complete field mapping and conversion rules.
"""
