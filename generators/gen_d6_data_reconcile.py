"""
Parameterized generator for D6: Data Reconciliation.

TNI Pattern D (Source-of-Truth Designation):
  - Spec has: per-field source-of-truth rules (System A owns certain fields,
    System B owns others), conflict resolution rules (most-recent timestamp wins
    for shared fields, manual_override flag takes absolute priority), and the
    exact expected reconciled output format.
  - Brief says: "Two data systems have drifted out of sync. Reconcile the differences."
  - Without the Planner's field-ownership and conflict-resolution rules the
    Executor may merge naively (last-write-wins across all fields) and miss that
    System A is authoritative for identity fields while System B is authoritative
    for billing fields, and that manual_override supersedes timestamps.

Each seed produces:
  - Different domain (customers, employees, vendors, subscribers)
  - Different field ownership split between System A and System B
  - Different record counts (15-30 base records)
  - Conflict types: field-ownership conflicts, timestamp conflicts, manual-override
    records, records only in System A, records only in System B, agreement records
  - workspace/system_a.json   -- System A snapshot
  - workspace/system_b.json   -- System B snapshot
  - workspace/reconcile.py    -- skeleton with wrong merge logic
  - reports/expected.json     -- ground-truth for grading (never seen by agents)
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom, NamePool

# ── Domain definitions ──────────────────────────────────────────────────────

DOMAINS = {
    "customers": {
        "description": "Customer account records across CRM and billing systems",
        "id_field": "customer_id",
        "id_prefix": "CUST",
        "system_a_name": "CRM",
        "system_b_name": "Billing",
        "system_a_owns": ["name", "email", "phone", "account_type"],
        "system_b_owns": ["billing_address", "payment_method", "subscription_tier", "balance_cents"],
        "shared_fields": ["status", "region"],
        "field_types": {
            "name": "string",
            "email": "email",
            "phone": "phone",
            "account_type": "enum:standard,premium,enterprise",
            "billing_address": "string",
            "payment_method": "enum:credit_card,bank_transfer,invoice,paypal",
            "subscription_tier": "enum:basic,pro,business,unlimited",
            "balance_cents": "int",
            "status": "enum:active,inactive,suspended,pending",
            "region": "enum:NA,EU,APAC,LATAM",
        },
    },
    "employees": {
        "description": "Employee records across HR and payroll systems",
        "id_field": "employee_id",
        "id_prefix": "EMP",
        "system_a_name": "HR",
        "system_b_name": "Payroll",
        "system_a_owns": ["full_name", "email", "department", "job_title"],
        "system_b_owns": ["salary_cents", "pay_schedule", "tax_code", "bank_account_last4"],
        "shared_fields": ["employment_status", "office_location"],
        "field_types": {
            "full_name": "string",
            "email": "email",
            "department": "enum:engineering,sales,marketing,finance,operations,hr,legal",
            "job_title": "string",
            "salary_cents": "int",
            "pay_schedule": "enum:weekly,biweekly,monthly,semimonthly",
            "tax_code": "string",
            "bank_account_last4": "digits4",
            "employment_status": "enum:active,on_leave,terminated,probation",
            "office_location": "enum:NYC,LON,SFO,TYO,SYD,BER,TOR",
        },
    },
    "vendors": {
        "description": "Vendor records across procurement and accounts-payable systems",
        "id_field": "vendor_id",
        "id_prefix": "VND",
        "system_a_name": "Procurement",
        "system_b_name": "AccountsPayable",
        "system_a_owns": ["vendor_name", "contact_email", "category", "contract_type"],
        "system_b_owns": ["payment_terms_days", "currency", "tax_id", "preferred_bank"],
        "shared_fields": ["status", "country_code"],
        "field_types": {
            "vendor_name": "string",
            "contact_email": "email",
            "category": "enum:hardware,software,services,logistics,facilities,consulting",
            "contract_type": "enum:fixed,time_and_materials,retainer,milestone",
            "payment_terms_days": "enum:15,30,45,60,90",
            "currency": "enum:USD,EUR,GBP,JPY,CAD,AUD",
            "tax_id": "taxid",
            "preferred_bank": "string",
            "status": "enum:active,inactive,blacklisted,pending_review",
            "country_code": "enum:US,GB,DE,FR,JP,CA,AU,SG",
        },
    },
    "subscribers": {
        "description": "Subscriber records across identity and subscription-management systems",
        "id_field": "subscriber_id",
        "id_prefix": "SUB",
        "system_a_name": "Identity",
        "system_b_name": "SubscriptionMgr",
        "system_a_owns": ["username", "email", "display_name", "auth_provider"],
        "system_b_owns": ["plan_id", "renewal_date", "seats", "discount_pct"],
        "shared_fields": ["account_status", "timezone"],
        "field_types": {
            "username": "string",
            "email": "email",
            "display_name": "string",
            "auth_provider": "enum:google,github,saml,password,microsoft",
            "plan_id": "enum:free,starter,growth,enterprise,legacy",
            "renewal_date": "date",
            "seats": "int",
            "discount_pct": "int",
            "account_status": "enum:active,trial,expired,cancelled,paused",
            "timezone": "enum:UTC,US/Eastern,US/Pacific,Europe/London,Asia/Tokyo,Australia/Sydney",
        },
    },
}

# ── Value generators per field type ─────────────────────────────────────────

def _gen_value(rng: SeededRandom, names: NamePool, field: str, ftype: str, seed_salt: int) -> object:
    """Generate a realistic value for a given field type."""
    if ftype == "string":
        if "name" in field or "vendor_name" in field:
            return names.next()
        if "title" in field:
            titles = ["Engineer", "Manager", "Director", "Analyst", "Specialist",
                      "Coordinator", "Lead", "Architect", "Consultant", "Associate"]
            return rng.choice(titles)
        if "address" in field:
            streets = ["Main St", "Oak Ave", "Park Blvd", "Cedar Ln", "Elm Dr",
                       "Maple Rd", "Pine Way", "River Ct", "Lake Dr", "Hill St"]
            return f"{rng.randint(100, 9999)} {rng.choice(streets)}"
        if "bank" in field:
            banks = ["Chase", "BofA", "Wells Fargo", "Citibank", "HSBC",
                     "Barclays", "Deutsche Bank", "Mizuho", "TD Bank", "RBC"]
            return rng.choice(banks)
        return names.next()
    elif ftype == "email":
        name = names.next().lower()
        domains = ["example.com", "corp.io", "acme.org", "biztech.net", "enterprise.co"]
        return f"{name}@{rng.choice(domains)}"
    elif ftype == "phone":
        return f"+1-{rng.randint(200,999)}-{rng.randint(200,999)}-{rng.randint(1000,9999)}"
    elif ftype == "int":
        if "cents" in field or "salary" in field:
            return rng.randint(3000000, 25000000)  # $30k–$250k in cents
        if "seats" in field:
            return rng.randint(1, 500)
        if "discount" in field:
            return rng.randint(0, 40)
        return rng.randint(1, 9999)
    elif ftype == "digits4":
        return str(rng.randint(1000, 9999))
    elif ftype == "taxid":
        return f"{rng.randint(10,99)}-{rng.randint(1000000,9999999)}"
    elif ftype == "date":
        base = datetime(2025, 1, 1)
        delta = timedelta(days=rng.randint(1, 730))
        return (base + delta).strftime("%Y-%m-%d")
    elif ftype.startswith("enum:"):
        opts = ftype[5:].split(",")
        return rng.choice(opts)
    return "unknown"


def _make_ts(rng: SeededRandom, base_epoch: int, spread_hours: int = 720) -> str:
    """Generate a timestamp string offset from a base epoch."""
    offset = rng.randint(0, spread_hours * 3600)
    dt = datetime.utcfromtimestamp(base_epoch + offset)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Generator ────────────────────────────────────────────────────────────────

class Generator(TaskGenerator):
    task_id = "D6_data_reconcile"
    domain = "data"
    difficulty = "expert"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        names = NamePool(seed, count=120)

        # Pick domain
        domain_key = rng.choice(list(DOMAINS.keys()))
        dom = DOMAINS[domain_key]

        id_field = dom["id_field"]
        id_prefix = dom["id_prefix"]
        sys_a_name = dom["system_a_name"]
        sys_b_name = dom["system_b_name"]
        a_owns = dom["system_a_owns"]
        b_owns = dom["system_b_owns"]
        shared = dom["shared_fields"]
        ftypes = dom["field_types"]
        all_fields = a_owns + b_owns + shared

        # Record counts
        n_base = rng.randint(15, 28)
        n_only_a = rng.randint(2, 4)   # records only in System A (System B missing)
        n_only_b = rng.randint(2, 4)   # records only in System B (System A missing)
        n_conflict_ownership = rng.randint(3, 6)   # field-ownership conflicts
        n_conflict_timestamp = rng.randint(3, 6)   # shared-field timestamp conflicts
        n_manual_override = rng.randint(2, 4)      # manual_override=true records
        n_agree = n_base - n_conflict_ownership - n_conflict_timestamp - n_manual_override
        if n_agree < 2:
            n_agree = 2

        # Base epoch for timestamps (~6 months ago)
        base_epoch = 1720000000  # approx Jul 2024

        total_records = n_base + n_only_a + n_only_b

        # ── Build record IDs ─────────────────────────────────────────────
        all_ids = [f"{id_prefix}-{seed:02d}{i:04d}" for i in range(1, total_records + 1)]
        rng.shuffle(all_ids)

        base_ids = all_ids[:n_base]
        only_a_ids = all_ids[n_base:n_base + n_only_a]
        only_b_ids = all_ids[n_base + n_only_a:]

        # Partition base_ids into conflict categories
        rng.shuffle(base_ids)
        cat_ownership = base_ids[:n_conflict_ownership]
        cat_timestamp = base_ids[n_conflict_ownership:n_conflict_ownership + n_conflict_timestamp]
        cat_override = base_ids[n_conflict_ownership + n_conflict_timestamp:
                                n_conflict_ownership + n_conflict_timestamp + n_manual_override]
        cat_agree = base_ids[n_conflict_ownership + n_conflict_timestamp + n_manual_override:]

        # ── Generate canonical "truth" values for every record ───────────
        canonical: dict[str, dict] = {}
        for rid in base_ids + only_a_ids + only_b_ids:
            rec = {}
            for f in all_fields:
                rec[f] = _gen_value(rng, names, f, ftypes[f], seed)
            canonical[rid] = rec

        # ── Build System A and System B records ──────────────────────────
        system_a: dict[str, dict] = {}
        system_b: dict[str, dict] = {}

        # --- Records only in A ---
        for rid in only_a_ids:
            ts = _make_ts(rng, base_epoch)
            rec_a = {id_field: rid, "last_updated": ts}
            for f in a_owns + shared:
                rec_a[f] = canonical[rid][f]
            system_a[rid] = rec_a

        # --- Records only in B ---
        for rid in only_b_ids:
            ts = _make_ts(rng, base_epoch)
            rec_b = {id_field: rid, "last_updated": ts, "manual_override": False}
            for f in b_owns + shared:
                rec_b[f] = canonical[rid][f]
            system_b[rid] = rec_b

        # --- Agreement records: same values in both systems ---
        for rid in cat_agree:
            ts = _make_ts(rng, base_epoch)
            rec_a = {id_field: rid, "last_updated": ts}
            rec_b = {id_field: rid, "last_updated": ts, "manual_override": False}
            for f in a_owns:
                rec_a[f] = canonical[rid][f]
            for f in b_owns:
                rec_b[f] = canonical[rid][f]
            for f in shared:
                val = canonical[rid][f]
                rec_a[f] = val
                rec_b[f] = val
            system_a[rid] = rec_a
            system_b[rid] = rec_b

        # --- Ownership conflict records: System A values differ from System B
        #     for A-owned or B-owned fields (wrong system wrote to other's field).
        #     Correct reconciliation uses A's value for A-owned fields and
        #     B's value for B-owned fields, regardless of timestamps.
        ownership_conflict_details: dict[str, dict] = {}
        for rid in cat_ownership:
            ts = _make_ts(rng, base_epoch)
            rec_a = {id_field: rid, "last_updated": ts}
            rec_b = {id_field: rid, "last_updated": ts, "manual_override": False}

            for f in a_owns:
                a_val = canonical[rid][f]
                # System B has a stale/wrong value for this A-owned field
                b_val = _gen_value(rng, names, f, ftypes[f], seed + hash(rid + f))
                while b_val == a_val:
                    b_val = _gen_value(rng, names, f, ftypes[f], seed + hash(rid + f + "alt"))
                rec_a[f] = a_val
                rec_b[f] = b_val  # B has wrong value for A-owned field

            for f in b_owns:
                b_val = canonical[rid][f]
                # System A has a stale/wrong value for this B-owned field
                a_val = _gen_value(rng, names, f, ftypes[f], seed + hash(rid + f))
                while a_val == b_val:
                    a_val = _gen_value(rng, names, f, ftypes[f], seed + hash(rid + f + "alt"))
                rec_b[f] = b_val
                rec_a[f] = a_val  # A has wrong value for B-owned field

            for f in shared:
                val = canonical[rid][f]
                rec_a[f] = val
                rec_b[f] = val

            system_a[rid] = rec_a
            system_b[rid] = rec_b

            ownership_conflict_details[rid] = {
                "a_owned_correct": {f: rec_a[f] for f in a_owns},
                "b_owned_correct": {f: rec_b[f] for f in b_owns},
            }

        # --- Timestamp conflict records: shared fields differ, newer wins ---
        timestamp_conflict_details: dict[str, dict] = {}
        for rid in cat_timestamp:
            # A is newer for some shared fields, B is newer for others
            ts_a_epoch = base_epoch + rng.randint(0, 360 * 3600)
            ts_b_epoch = base_epoch + rng.randint(0, 360 * 3600)
            # Ensure they differ
            while ts_a_epoch == ts_b_epoch:
                ts_b_epoch = base_epoch + rng.randint(0, 360 * 3600)

            ts_a = datetime.utcfromtimestamp(ts_a_epoch).strftime("%Y-%m-%dT%H:%M:%SZ")
            ts_b = datetime.utcfromtimestamp(ts_b_epoch).strftime("%Y-%m-%dT%H:%M:%SZ")

            rec_a = {id_field: rid, "last_updated": ts_a}
            rec_b = {id_field: rid, "last_updated": ts_b, "manual_override": False}

            for f in a_owns:
                rec_a[f] = canonical[rid][f]
            for f in b_owns:
                rec_b[f] = canonical[rid][f]
                # A has a value too (might be wrong, but overridden by B ownership)
                rec_a[f] = canonical[rid][f]

            # Shared fields: generate different values for A and B
            shared_correct = {}
            for f in shared:
                a_val = canonical[rid][f]
                b_val = _gen_value(rng, names, f, ftypes[f], seed + hash(rid + f + "ts"))
                while b_val == a_val:
                    b_val = _gen_value(rng, names, f, ftypes[f], seed + hash(rid + f + "ts2"))
                rec_a[f] = a_val
                rec_b[f] = b_val
                # Newer timestamp wins for shared fields
                if ts_a_epoch >= ts_b_epoch:
                    shared_correct[f] = a_val
                else:
                    shared_correct[f] = b_val

            system_a[rid] = rec_a
            system_b[rid] = rec_b

            timestamp_conflict_details[rid] = {
                "ts_a": ts_a,
                "ts_b": ts_b,
                "a_newer": ts_a_epoch >= ts_b_epoch,
                "shared_correct": shared_correct,
            }

        # --- Manual override records: manual_override=True in System B,
        #     B's values win for ALL fields (including A-owned) ---
        override_details: dict[str, dict] = {}
        for rid in cat_override:
            ts = _make_ts(rng, base_epoch)
            rec_a = {id_field: rid, "last_updated": ts}
            rec_b = {id_field: rid, "last_updated": ts, "manual_override": True}

            # B has different values for A-owned fields — and wins because override
            b_override_vals = {}
            for f in a_owns:
                a_val = canonical[rid][f]
                b_val = _gen_value(rng, names, f, ftypes[f], seed + hash(rid + f + "ov"))
                while b_val == a_val:
                    b_val = _gen_value(rng, names, f, ftypes[f], seed + hash(rid + f + "ov2"))
                rec_a[f] = a_val
                rec_b[f] = b_val
                b_override_vals[f] = b_val

            for f in b_owns:
                val = canonical[rid][f]
                rec_b[f] = val
                rec_a[f] = val
                b_override_vals[f] = val

            for f in shared:
                val = canonical[rid][f]
                rec_a[f] = val
                rec_b[f] = val
                b_override_vals[f] = val

            system_a[rid] = rec_a
            system_b[rid] = rec_b
            override_details[rid] = {"b_wins_all": b_override_vals}

        # ── Compute expected reconciled output ───────────────────────────
        # Rules (in priority order):
        #   1. manual_override=True in B -> B wins ALL fields
        #   2. A-owned fields -> always take from A
        #   3. B-owned fields -> always take from B
        #   4. Shared fields with conflict -> newer last_updated wins
        #   5. Record only in A -> include, fill B fields as null
        #   6. Record only in B -> include, fill A fields as null

        reconciled: list[dict] = []
        expected_per_id: dict[str, dict] = {}

        all_reconcile_ids = sorted(
            set(system_a.keys()) | set(system_b.keys())
        )

        for rid in all_reconcile_ids:
            a_rec = system_a.get(rid)
            b_rec = system_b.get(rid)

            out = {id_field: rid}

            if a_rec is not None and b_rec is not None:
                # Both present — apply reconciliation rules
                if b_rec.get("manual_override") is True:
                    # Rule 1: B wins all fields
                    for f in a_owns:
                        out[f] = b_rec.get(f)
                    for f in b_owns:
                        out[f] = b_rec.get(f)
                    for f in shared:
                        out[f] = b_rec.get(f)
                    out["reconcile_source"] = "manual_override"
                else:
                    # Rule 2: A-owned -> from A
                    for f in a_owns:
                        out[f] = a_rec.get(f)
                    # Rule 3: B-owned -> from B
                    for f in b_owns:
                        out[f] = b_rec.get(f)
                    # Rule 4: Shared -> newer timestamp
                    ts_a = a_rec.get("last_updated", "")
                    ts_b = b_rec.get("last_updated", "")
                    a_newer = ts_a >= ts_b  # ISO strings compare correctly
                    for f in shared:
                        out[f] = a_rec.get(f) if a_newer else b_rec.get(f)
                    out["reconcile_source"] = "merged"

            elif a_rec is not None:
                # Only in A — Rule 5
                for f in a_owns:
                    out[f] = a_rec.get(f)
                for f in b_owns:
                    out[f] = None
                for f in shared:
                    out[f] = a_rec.get(f)
                out["reconcile_source"] = "system_a_only"

            else:
                # Only in B — Rule 6
                for f in a_owns:
                    out[f] = None
                for f in b_owns:
                    out[f] = b_rec.get(f)
                for f in shared:
                    out[f] = b_rec.get(f)
                out["reconcile_source"] = "system_b_only"

            reconciled.append(out)
            expected_per_id[rid] = out

        # Sort by id_field for deterministic output
        reconciled.sort(key=lambda r: r[id_field])

        # ── Build expected.json ──────────────────────────────────────────
        expected = {
            "domain": domain_key,
            "id_field": id_field,
            "system_a_name": sys_a_name,
            "system_b_name": sys_b_name,
            "a_owned_fields": a_owns,
            "b_owned_fields": b_owns,
            "shared_fields": shared,
            "all_output_fields": [id_field] + all_fields + ["reconcile_source"],
            "total_records": len(reconciled),
            "only_a_ids": only_a_ids,
            "only_b_ids": only_b_ids,
            "ownership_conflict_ids": list(cat_ownership),
            "timestamp_conflict_ids": list(cat_timestamp),
            "manual_override_ids": list(cat_override),
            "agree_ids": [r for r in cat_agree],
            "per_record": {
                rid: {
                    "expected_values": expected_per_id[rid],
                    "reconcile_source": expected_per_id[rid]["reconcile_source"],
                }
                for rid in expected_per_id
            },
        }

        # ── Generate workspace files ─────────────────────────────────────
        workspace_files = {
            "system_a.json": json.dumps(
                [v for v in system_a.values()],
                indent=2,
                ensure_ascii=False,
            ),
            "system_b.json": json.dumps(
                [v for v in system_b.values()],
                indent=2,
                ensure_ascii=False,
            ),
            "reconcile.py": self._generate_skeleton(
                id_field, a_owns, b_owns, shared, sys_a_name, sys_b_name
            ),
        }

        spec_md = self._generate_spec(
            domain_key, dom, id_field, a_owns, b_owns, shared,
            sys_a_name, sys_b_name, n_base + n_only_a + n_only_b,
        )
        brief_md = self._generate_brief(domain_key, sys_a_name, sys_b_name)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # ── Skeleton reconcile.py (wrong logic for agents to fix) ───────────────

    def _generate_skeleton(
        self,
        id_field: str,
        a_owns: list[str],
        b_owns: list[str],
        shared: list[str],
        sys_a_name: str,
        sys_b_name: str,
    ) -> str:
        a_owns_repr = repr(a_owns)
        b_owns_repr = repr(b_owns)
        shared_repr = repr(shared)

        return f'''"""
Data reconciliation script — merge System A ({sys_a_name}) and System B ({sys_b_name}).

TODO: Fix the reconciliation logic so it respects:
  1. manual_override=True in System B -> System B wins ALL fields for that record
  2. System A is authoritative for its owned fields
  3. System B is authoritative for its owned fields
  4. For shared fields with conflicting values: newer last_updated timestamp wins
  5. Records only in System A: include them, null-fill System B fields
  6. Records only in System B: include them, null-fill System A fields

Output: reconciled.json — list of merged records sorted by {id_field}.
"""
import json

ID_FIELD = "{id_field}"

# Field ownership — DO NOT CHANGE these assignments
A_OWNED_FIELDS = {a_owns_repr}
B_OWNED_FIELDS = {b_owns_repr}
SHARED_FIELDS  = {shared_repr}

ALL_OUTPUT_FIELDS = [ID_FIELD] + A_OWNED_FIELDS + B_OWNED_FIELDS + SHARED_FIELDS + ["reconcile_source"]


def load_system(path):
    with open(path, "r", encoding="utf-8") as f:
        records = json.load(f)
    return {{r[ID_FIELD]: r for r in records}}


def reconcile(a_records, b_records):
    all_ids = sorted(set(a_records) | set(b_records))
    result = []

    for rid in all_ids:
        a = a_records.get(rid)
        b = b_records.get(rid)
        out = {{ID_FIELD: rid}}

        if a is not None and b is not None:
            # BUG: naive last-write-wins on last_updated — ignores field ownership
            # and manual_override entirely.
            ts_a = a.get("last_updated", "")
            ts_b = b.get("last_updated", "")
            winner = a if ts_a >= ts_b else b
            for f in A_OWNED_FIELDS + B_OWNED_FIELDS + SHARED_FIELDS:
                out[f] = winner.get(f)
            out["reconcile_source"] = "merged"

        elif a is not None:
            # BUG: doesn't null-fill B-owned fields
            for f in A_OWNED_FIELDS + SHARED_FIELDS:
                out[f] = a.get(f)
            out["reconcile_source"] = "system_a_only"

        else:
            # BUG: doesn't null-fill A-owned fields
            for f in B_OWNED_FIELDS + SHARED_FIELDS:
                out[f] = b.get(f)
            out["reconcile_source"] = "system_b_only"

        result.append(out)

    return result


def main():
    a_records = load_system("system_a.json")
    b_records = load_system("system_b.json")

    reconciled = reconcile(a_records, b_records)

    with open("reconciled.json", "w", encoding="utf-8") as f:
        json.dump(reconciled, f, indent=2, ensure_ascii=False)

    print(f"Reconciled {{len(reconciled)}} records -> reconciled.json")


if __name__ == "__main__":
    main()
'''

    # ── Spec (full, for Planner/Verifier) ────────────────────────────────────

    def _generate_spec(
        self,
        domain_key: str,
        dom: dict,
        id_field: str,
        a_owns: list[str],
        b_owns: list[str],
        shared: list[str],
        sys_a_name: str,
        sys_b_name: str,
        total: int,
    ) -> str:
        a_owns_fmt = "\n".join(f"  - `{f}`" for f in a_owns)
        b_owns_fmt = "\n".join(f"  - `{f}`" for f in b_owns)
        shared_fmt = "\n".join(f"  - `{f}`" for f in shared)
        all_out = [id_field] + a_owns + b_owns + shared + ["reconcile_source"]
        cols_fmt = ", ".join(f"`{f}`" for f in all_out)

        return f"""# D6: Data Reconciliation — Full Specification

## Context
{dom['description']}.  Two system snapshots have drifted out of sync.
System A (`{sys_a_name}`) and System B (`{sys_b_name}`) each hold overlapping
records with approximately {total} distinct entities across both systems.

## Field Ownership (Source-of-Truth Designation)

### System A (`{sys_a_name}`) is authoritative for:
{a_owns_fmt}

### System B (`{sys_b_name}`) is authoritative for:
{b_owns_fmt}

### Shared fields (conflict resolved by timestamp):
{shared_fmt}

## Conflict Resolution Rules — in strict priority order

1. **Manual Override** (highest priority):
   If a System B record has `"manual_override": true`, System B's values win for
   **ALL** fields of that record — including fields normally owned by System A.
   `reconcile_source` must be set to `"manual_override"`.

2. **Field Ownership**:
   - A-owned fields: always take the value from System A, regardless of timestamps.
   - B-owned fields: always take the value from System B, regardless of timestamps.

3. **Shared Field Conflict Resolution**:
   For shared fields where System A and System B have different values:
   - Compare `last_updated` timestamps (ISO 8601 strings).
   - The record from the system with the **newer** (larger) timestamp wins for
     all shared fields of that record pair.
   - If timestamps are equal, System A takes precedence.

4. **Records only in System A**:
   Include the record. Fill all B-owned fields with `null`.
   `reconcile_source` = `"system_a_only"`.

5. **Records only in System B**:
   Include the record. Fill all A-owned fields with `null`.
   `reconcile_source` = `"system_b_only"`.

6. **Records present in both systems with no conflicts**:
   Merge normally following field-ownership rules.
   `reconcile_source` = `"merged"`.

## Output Format

### File: `reconciled.json`
A JSON array of objects, **sorted ascending by `{id_field}`**.

Each object must contain exactly these fields in order:
{cols_fmt}

- `reconcile_source` must be one of: `"merged"`, `"manual_override"`,
  `"system_a_only"`, `"system_b_only"`.
- Fields that have no source (null-filled) must appear as JSON `null`, not
  omitted and not the string `"null"`.
- No extra fields. No missing fields.

## Execution
```
python reconcile.py
```
Reads `system_a.json` and `system_b.json` from the current directory,
writes `reconciled.json` to the current directory.

## Deliverables
- Fixed `reconcile.py` in workspace.
- `reconciled.json` present and correct.
- Verifier attests all rules are satisfied.
"""

    # ── Brief (summary, for Executor) ────────────────────────────────────────

    def _generate_brief(self, domain_key: str, sys_a_name: str, sys_b_name: str) -> str:
        return f"""# D6: Data Reconciliation (Brief)

Two {domain_key} data systems — **{sys_a_name}** and **{sys_b_name}** — have
drifted out of sync.  Reconcile the differences and produce a single merged
dataset.

The Planner has the complete field-ownership rules and conflict-resolution spec.

**Run:** `python reconcile.py`
**Input:** `system_a.json`, `system_b.json`
**Output:** `reconciled.json`

Fix `reconcile.py` so it produces a correctly reconciled output file.
"""
