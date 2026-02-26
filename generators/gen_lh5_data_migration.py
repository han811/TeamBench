"""
Parameterized generator for LH5: Data Migration.

Each seed produces:
- Different data domain (ecommerce, healthcare, financial, iot)
- Different number of migration steps (5-7)
- Different table/entity names
- Different row counts and checksum salts
- Different validation checkpoint types
- Seed-specific migrate.py (skeleton with TODOs), validate.py, data/old_format/

TNI Pattern F,A: Spec has the complete step plan + validation checkpoints + rollback
triggers. Brief says "migrate the data."
"""
from __future__ import annotations

import hashlib
import json
import random
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ---------------------------------------------------------------------------
# Domain definitions
# ---------------------------------------------------------------------------

DOMAINS = [
    {
        "name": "ecommerce",
        "tables": ["orders", "order_items", "customers", "products"],
        "primary_table": "orders",
        "ref_table": "customers",
        "ref_key": "customer_id",
        "old_format": "csv",
        "new_format": "jsonl",
        "description": "e-commerce order management",
    },
    {
        "name": "healthcare",
        "tables": ["patients", "visits", "prescriptions", "diagnoses"],
        "primary_table": "visits",
        "ref_table": "patients",
        "ref_key": "patient_id",
        "old_format": "tsv",
        "new_format": "jsonl",
        "description": "healthcare visit records",
    },
    {
        "name": "financial",
        "tables": ["transactions", "accounts", "ledger_entries", "audit_log"],
        "primary_table": "transactions",
        "ref_table": "accounts",
        "ref_key": "account_id",
        "old_format": "csv",
        "new_format": "jsonl",
        "description": "financial transaction ledger",
    },
    {
        "name": "iot",
        "tables": ["sensor_readings", "devices", "alerts", "calibrations"],
        "primary_table": "sensor_readings",
        "ref_table": "devices",
        "ref_key": "device_id",
        "old_format": "csv",
        "new_format": "jsonl",
        "description": "IoT sensor telemetry",
    },
]

# Migration step pool: (step_name, description, action_type)
STEP_POOL = [
    ("backup",           "Create a backup of all source data before any changes",     "backup"),
    ("transform_format", "Convert records from old format to new target format",       "transform"),
    ("validate_checksums","Verify data integrity via SHA-256 checksums of every record","validate"),
    ("load_new_store",   "Load transformed records into the new data store",           "load"),
    ("verify_counts",    "Confirm row counts match between source and destination",    "verify"),
    ("update_references","Rewrite foreign-key references to use new primary keys",     "references"),
    ("archive_old",      "Compress and archive the original source data",              "archive"),
]

# Rollback actions paired to each step
ROLLBACK_ACTIONS = {
    "backup":            "Remove incomplete backup directory",
    "transform_format":  "Delete all files in data/transformed/",
    "validate_checksums":"Clear checksum manifest (checksums.json)",
    "load_new_store":    "Truncate data/new_format/ directory",
    "verify_counts":     "Remove verification report",
    "update_references": "Restore original reference mapping from backup",
    "archive_old":       "Delete partial archive file",
}


class Generator(TaskGenerator):
    task_id = "LH5_data_migration"
    domain = "data"
    difficulty = "expert"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # Pick domain
        domain_idx = rng.randint(0, len(DOMAINS) - 1)
        domain = DOMAINS[domain_idx]

        # Number of migration steps (5-7); always include first 4 mandatory steps
        num_steps = rng.randint(5, 7)

        # Always use full STEP_POOL order, pick first num_steps
        steps = STEP_POOL[:num_steps]

        # Row counts: primary table 50-200, reference table 10-50
        primary_row_count = rng.randint(50, 200)
        ref_row_count = rng.randint(10, 50)

        # Checksum salt for deterministic checksums
        checksum_salt = rng.randint(1000, 9999)

        # Compute expected checksums deterministically
        expected_source_checksum = self._compute_expected_checksum(
            domain["primary_table"], primary_row_count, checksum_salt, "source"
        )
        expected_dest_checksum = self._compute_expected_checksum(
            domain["primary_table"], primary_row_count, checksum_salt, "dest"
        )

        # Archive filename
        archive_name = f"{domain['name']}_source_archive.tar.gz"

        expected = {
            "domain": domain["name"],
            "num_steps": num_steps,
            "steps": [s[0] for s in steps],
            "primary_table": domain["primary_table"],
            "ref_table": domain["ref_table"],
            "ref_key": domain["ref_key"],
            "primary_row_count": primary_row_count,
            "ref_row_count": ref_row_count,
            "checksum_salt": checksum_salt,
            "source_checksum": expected_source_checksum,
            "dest_checksum": expected_dest_checksum,
            "archive_name": archive_name,
            "old_format": domain["old_format"],
            "new_format": domain["new_format"],
        }

        # Build source data files
        source_records = self._generate_source_records(
            domain, primary_row_count, ref_row_count, checksum_salt, rng
        )

        workspace_files = {}

        # data/old_format/ source files
        workspace_files[f"data/old_format/{domain['primary_table']}.{domain['old_format']}"] = (
            source_records["primary_file"]
        )
        workspace_files[f"data/old_format/{domain['ref_table']}.{domain['old_format']}"] = (
            source_records["ref_file"]
        )

        # Empty data/new_format/ placeholder
        workspace_files["data/new_format/.gitkeep"] = ""

        # migrate.py skeleton
        workspace_files["migrate.py"] = self._generate_migrate_skeleton(
            domain, steps, primary_row_count, ref_row_count, checksum_salt, archive_name
        )

        # validate.py helper
        workspace_files["validate.py"] = self._generate_validate_py(
            domain, primary_row_count, expected_source_checksum, expected_dest_checksum
        )

        spec_md = self._generate_spec(
            domain, steps, primary_row_count, ref_row_count,
            expected_source_checksum, expected_dest_checksum, archive_name
        )
        brief_md = self._generate_brief(domain, num_steps)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # -----------------------------------------------------------------------
    # Data generation helpers
    # -----------------------------------------------------------------------

    def _compute_expected_checksum(
        self, table: str, row_count: int, salt: int, stage: str
    ) -> str:
        """Deterministic SHA-256 for a table at a given stage."""
        payload = f"{table}:{row_count}:{salt}:{stage}"
        return hashlib.sha256(payload.encode()).hexdigest()

    def _generate_source_records(
        self,
        domain: dict,
        primary_count: int,
        ref_count: int,
        salt: int,
        rng: SeededRandom,
    ) -> dict:
        """Build CSV/TSV content for source data files."""
        sep = "\t" if domain["old_format"] == "tsv" else ","
        ref_key = domain["ref_key"]
        primary_table = domain["primary_table"]
        ref_table = domain["ref_table"]

        # Reference table rows (e.g. customers, patients, accounts, devices)
        ref_ids = list(range(1, ref_count + 1))

        if domain["name"] == "ecommerce":
            ref_header = sep.join(["customer_id", "name", "email", "signup_date"])
            ref_rows = [ref_header]
            for cid in ref_ids:
                ref_rows.append(sep.join([
                    str(cid),
                    f"Customer_{cid}",
                    f"customer{cid}@example.com",
                    f"2023-{(cid % 12) + 1:02d}-01",
                ]))
            primary_header = sep.join([
                "order_id", "customer_id", "amount", "status", "created_at"
            ])
            primary_rows = [primary_header]
            for oid in range(1, primary_count + 1):
                cid = (oid % ref_count) + 1
                primary_rows.append(sep.join([
                    str(oid),
                    str(cid),
                    f"{(oid * salt % 900) + 10}.{oid % 100:02d}",
                    ["pending", "complete", "refunded"][oid % 3],
                    f"2024-{(oid % 12) + 1:02d}-{(oid % 28) + 1:02d}",
                ]))

        elif domain["name"] == "healthcare":
            ref_header = sep.join(["patient_id", "name", "dob", "gender"])
            ref_rows = [ref_header]
            for pid in ref_ids:
                ref_rows.append(sep.join([
                    str(pid),
                    f"Patient_{pid}",
                    f"198{pid % 10}-{(pid % 12) + 1:02d}-15",
                    ["M", "F", "O"][pid % 3],
                ]))
            primary_header = sep.join([
                "visit_id", "patient_id", "diagnosis_code", "visit_date", "provider"
            ])
            primary_rows = [primary_header]
            for vid in range(1, primary_count + 1):
                pid = (vid % ref_count) + 1
                primary_rows.append(sep.join([
                    str(vid),
                    str(pid),
                    f"ICD{vid % 100:03d}",
                    f"2024-{(vid % 12) + 1:02d}-{(vid % 28) + 1:02d}",
                    f"Dr_Smith_{vid % 10}",
                ]))

        elif domain["name"] == "financial":
            ref_header = sep.join(["account_id", "holder", "account_type", "opened_date"])
            ref_rows = [ref_header]
            for aid in ref_ids:
                ref_rows.append(sep.join([
                    str(aid),
                    f"Holder_{aid}",
                    ["checking", "savings", "credit"][aid % 3],
                    f"2020-{(aid % 12) + 1:02d}-01",
                ]))
            primary_header = sep.join([
                "txn_id", "account_id", "amount", "type", "txn_date"
            ])
            primary_rows = [primary_header]
            for tid in range(1, primary_count + 1):
                aid = (tid % ref_count) + 1
                primary_rows.append(sep.join([
                    str(tid),
                    str(aid),
                    f"{(tid * salt % 9000) + 100}.{tid % 100:02d}",
                    ["debit", "credit", "transfer"][tid % 3],
                    f"2024-{(tid % 12) + 1:02d}-{(tid % 28) + 1:02d}",
                ]))

        else:  # iot
            ref_header = sep.join(["device_id", "device_type", "location", "installed_date"])
            ref_rows = [ref_header]
            for did in ref_ids:
                ref_rows.append(sep.join([
                    str(did),
                    ["temperature", "humidity", "pressure"][did % 3],
                    f"Zone_{did % 5}",
                    f"2022-{(did % 12) + 1:02d}-01",
                ]))
            primary_header = sep.join([
                "reading_id", "device_id", "value", "unit", "timestamp"
            ])
            primary_rows = [primary_header]
            for rid in range(1, primary_count + 1):
                did = (rid % ref_count) + 1
                primary_rows.append(sep.join([
                    str(rid),
                    str(did),
                    f"{(rid * salt % 1000) / 10.0:.1f}",
                    ["C", "pct", "hPa"][rid % 3],
                    f"2024-{(rid % 12) + 1:02d}-{(rid % 28) + 1:02d}T{rid % 24:02d}:00:00",
                ]))

        return {
            "primary_file": "\n".join(primary_rows) + "\n",
            "ref_file": "\n".join(ref_rows) + "\n",
        }

    # -----------------------------------------------------------------------
    # Workspace file generators
    # -----------------------------------------------------------------------

    def _generate_migrate_skeleton(
        self,
        domain: dict,
        steps: list,
        primary_count: int,
        ref_count: int,
        salt: int,
        archive_name: str,
    ) -> str:
        step_names = [s[0] for s in steps]
        steps_list_repr = repr(step_names)
        domain_name = domain["name"]
        primary_table = domain["primary_table"]
        ref_table = domain["ref_table"]
        ref_key = domain["ref_key"]
        old_fmt = domain["old_format"]
        new_fmt = domain["new_format"]
        sep_char = "\\t" if old_fmt == "tsv" else ","

        has_update_references = "update_references" in step_names
        has_archive = "archive_old" in step_names

        return f'''"""
Data migration script for {domain_name} {domain["description"]}.

Migration steps (execute in order):
{chr(10).join(f"  {i+1}. {s[0]}: {s[1]}" for i, s in enumerate(steps))}

Validation checkpoints between steps:
  - After transform_format: row counts in data/transformed/ must equal source
  - After validate_checksums: checksums.json must be written and verified
  - After load_new_store: row count in data/new_format/ must equal source
  - After verify_counts: verification_report.json must confirm counts match
{"  - After update_references: no orphaned " + ref_key + "s in new store" if has_update_references else ""}{"" if not has_update_references else chr(10)}
Rollback triggers:
  - Any step failure triggers rollback of all completed steps in reverse order.
  - Each step has a corresponding rollback action (see ROLLBACK_ACTIONS).

Usage:
    python migrate.py [--dry-run]
"""
import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import sys
import tarfile
from datetime import datetime, timezone


SOURCE_DIR = "data/old_format"
TRANSFORM_DIR = "data/transformed"
DEST_DIR = "data/new_format"
BACKUP_DIR = "data/backup"
CHECKSUM_FILE = "checksums.json"
VERIFICATION_REPORT = "verification_report.json"
MIGRATION_LOG = "migration_log.jsonl"
ARCHIVE_NAME = "{archive_name}"

PRIMARY_TABLE = "{primary_table}"
REF_TABLE = "{ref_table}"
REF_KEY = "{ref_key}"
SOURCE_EXT = "{old_fmt}"
DEST_EXT = "{new_fmt}"
SEPARATOR = "{sep_char}"

STEPS = {steps_list_repr}

ROLLBACK_ACTIONS = {{
    "backup":            "Remove incomplete backup directory",
    "transform_format":  "Delete all files in data/transformed/",
    "validate_checksums":"Clear checksum manifest (checksums.json)",
    "load_new_store":    "Truncate data/new_format/ directory",
    "verify_counts":     "Remove verification report",
    "update_references": "Restore original reference mapping from backup",
    "archive_old":       "Delete partial archive file",
}}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def log_event(step: str, status: str, detail: str = ""):
    entry = {{"step": step, "status": status, "detail": detail, "ts": now_iso()}}
    with open(MIGRATION_LOG, "a") as f:
        f.write(json.dumps(entry) + "\\n")
    print(f"[{{step}}] {{status}}{{': ' + detail if detail else ''}}")


def compute_file_checksum(filepath: str) -> str:
    """Compute SHA-256 of a file's contents."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def count_records(filepath: str) -> int:
    """Count data rows (excluding header) in a CSV/TSV/JSONL file."""
    if filepath.endswith(".jsonl"):
        count = 0
        with open(filepath) as f:
            for line in f:
                if line.strip():
                    count += 1
        return count
    else:
        with open(filepath) as f:
            lines = [l for l in f if l.strip()]
        # subtract 1 for header
        return max(0, len(lines) - 1)


# ── Step implementations ─────────────────────────────────────────────────────

def step_backup(dry_run: bool = False) -> bool:
    """Step 1: Backup source data."""
    # TODO: Implement backup
    # - Create BACKUP_DIR
    # - Copy all files from SOURCE_DIR into BACKUP_DIR
    # - Log success/failure
    log_event("backup", "not_implemented", "TODO: implement backup step")
    return False


def step_transform_format(dry_run: bool = False) -> bool:
    """Step 2: Transform records from old format to new format (JSONL)."""
    # TODO: Implement format transformation
    # - Read each table file from SOURCE_DIR (CSV/TSV)
    # - Convert each row to a JSON object
    # - Write JSONL output to TRANSFORM_DIR/<table>.jsonl
    # Checkpoint: row count in TRANSFORM_DIR must equal SOURCE_DIR row count
    log_event("transform_format", "not_implemented", "TODO: implement transform step")
    return False


def step_validate_checksums(dry_run: bool = False) -> bool:
    """Step 3: Validate data integrity via checksums."""
    # TODO: Implement checksum validation
    # - Compute SHA-256 for each file in SOURCE_DIR and TRANSFORM_DIR
    # - Write checksums to CHECKSUM_FILE as JSON dict:
    #   {{"source": {{"<filename>": "<sha256>"}}, "transformed": {{"<filename>": "<sha256>"}}}}
    # - Checkpoint: all checksum entries must be non-empty strings
    log_event("validate_checksums", "not_implemented", "TODO: implement checksum step")
    return False


def step_load_new_store(dry_run: bool = False) -> bool:
    """Step 4: Load transformed records into new data store."""
    # TODO: Implement load step
    # - Copy/move files from TRANSFORM_DIR to DEST_DIR
    # - Checkpoint: row count in DEST_DIR must equal source row count
    log_event("load_new_store", "not_implemented", "TODO: implement load step")
    return False


def step_verify_counts(dry_run: bool = False) -> bool:
    """Step 5: Verify row counts match between source and destination."""
    # TODO: Implement count verification
    # - Count rows in SOURCE_DIR (primary table only)
    # - Count rows in DEST_DIR (primary table only)
    # - Assert counts are equal
    # - Write VERIFICATION_REPORT with:
    #   {{"source_count": N, "dest_count": N, "counts_match": true/false}}
    log_event("verify_counts", "not_implemented", "TODO: implement verify_counts step")
    return False


def step_update_references(dry_run: bool = False) -> bool:
    """Step 6: Update foreign key references."""
    # TODO: Implement reference update
    # - Load REF_TABLE from DEST_DIR to build a set of valid REF_KEYs
    # - Load PRIMARY_TABLE from DEST_DIR
    # - Check every record's REF_KEY exists in the ref set
    # - If any orphaned references found, raise an error
    # - Write updated primary table back to DEST_DIR
    # - Checkpoint: no orphaned REF_KEYs
    log_event("update_references", "not_implemented", "TODO: implement update_references step")
    return False


def step_archive_old(dry_run: bool = False) -> bool:
    """Step 7: Archive the original source data."""
    # TODO: Implement archival
    # - Create a tar.gz archive named ARCHIVE_NAME containing SOURCE_DIR
    # - Checkpoint: archive file must exist and be non-empty
    log_event("archive_old", "not_implemented", "TODO: implement archive step")
    return False


STEP_FUNCTIONS = {{
    "backup": step_backup,
    "transform_format": step_transform_format,
    "validate_checksums": step_validate_checksums,
    "load_new_store": step_load_new_store,
    "verify_counts": step_verify_counts,
    "update_references": step_update_references,
    "archive_old": step_archive_old,
}}


# ── Rollback ─────────────────────────────────────────────────────────────────

def rollback_step(step_name: str):
    """Execute rollback for a completed step."""
    log_event(step_name, "rollback_start", ROLLBACK_ACTIONS.get(step_name, ""))
    try:
        if step_name == "backup":
            if os.path.exists(BACKUP_DIR):
                shutil.rmtree(BACKUP_DIR)
        elif step_name == "transform_format":
            if os.path.exists(TRANSFORM_DIR):
                shutil.rmtree(TRANSFORM_DIR)
        elif step_name == "validate_checksums":
            if os.path.exists(CHECKSUM_FILE):
                os.remove(CHECKSUM_FILE)
        elif step_name == "load_new_store":
            if os.path.exists(DEST_DIR):
                for fn in os.listdir(DEST_DIR):
                    if fn != ".gitkeep":
                        os.remove(os.path.join(DEST_DIR, fn))
        elif step_name == "verify_counts":
            if os.path.exists(VERIFICATION_REPORT):
                os.remove(VERIFICATION_REPORT)
        elif step_name == "update_references":
            # Restore from backup if available
            src = os.path.join(BACKUP_DIR, f"{{PRIMARY_TABLE}}.{{SOURCE_EXT}}")
            dst = os.path.join(SOURCE_DIR, f"{{PRIMARY_TABLE}}.{{SOURCE_EXT}}")
            if os.path.exists(src):
                shutil.copy2(src, dst)
        elif step_name == "archive_old":
            if os.path.exists(ARCHIVE_NAME):
                os.remove(ARCHIVE_NAME)
        log_event(step_name, "rollback_ok")
    except Exception as e:
        log_event(step_name, "rollback_error", str(e))


def run_rollback(completed_steps: list):
    """Roll back all completed steps in reverse order."""
    log_event("migration", "rollback_triggered", f"rolling back {{len(completed_steps)}} step(s)")
    for step_name in reversed(completed_steps):
        rollback_step(step_name)


# ── Main orchestration ────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Data migration tool")
    parser.add_argument("--dry-run", action="store_true", help="Validate without writing")
    args = parser.parse_args()

    # Clear and initialise log
    open(MIGRATION_LOG, "w").close()
    log_event("migration", "start", f"steps={{STEPS}}")

    os.makedirs(TRANSFORM_DIR, exist_ok=True)
    os.makedirs(DEST_DIR, exist_ok=True)

    completed_steps: list = []
    success = True

    for step_name in STEPS:
        fn = STEP_FUNCTIONS.get(step_name)
        if fn is None:
            log_event(step_name, "error", "unknown step")
            success = False
            break

        log_event(step_name, "start")
        try:
            ok = fn(dry_run=args.dry_run)
            if not ok:
                log_event(step_name, "failed", "step returned False")
                run_rollback(completed_steps)
                success = False
                break
            completed_steps.append(step_name)
            log_event(step_name, "completed")
        except Exception as exc:
            log_event(step_name, "error", str(exc))
            run_rollback(completed_steps)
            success = False
            break

    if success:
        log_event("migration", "success", f"all {{len(completed_steps)}} steps completed")
        # Write final migration report
        report = {{
            "status": "success",
            "steps_completed": completed_steps,
            "total_steps": len(STEPS),
            "ts": now_iso(),
        }}
        with open("migration_report.json", "w") as f:
            json.dump(report, f, indent=2)
        print("\\nMigration complete. See migration_report.json")
        sys.exit(0)
    else:
        log_event("migration", "failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
'''

    def _generate_validate_py(
        self,
        domain: dict,
        primary_count: int,
        expected_source_checksum: str,
        expected_dest_checksum: str,
    ) -> str:
        primary_table = domain["primary_table"]
        ref_table = domain["ref_table"]
        ref_key = domain["ref_key"]
        old_fmt = domain["old_format"]

        return f'''"""
Validation helpers for the data migration.
Run after migration to verify correctness.
"""
import csv
import hashlib
import json
import os
import sys


SOURCE_DIR = "data/old_format"
TRANSFORM_DIR = "data/transformed"
DEST_DIR = "data/new_format"
BACKUP_DIR = "data/backup"
CHECKSUM_FILE = "checksums.json"
VERIFICATION_REPORT = "verification_report.json"
MIGRATION_LOG = "migration_log.jsonl"
MIGRATION_REPORT = "migration_report.json"

PRIMARY_TABLE = "{primary_table}"
REF_TABLE = "{ref_table}"
REF_KEY = "{ref_key}"
SOURCE_EXT = "{old_fmt}"
EXPECTED_PRIMARY_ROWS = {primary_count}


def count_records(filepath):
    """Count data rows (excluding header) in a CSV/TSV/JSONL file."""
    if filepath.endswith(".jsonl"):
        count = 0
        with open(filepath) as f:
            for line in f:
                if line.strip():
                    count += 1
        return count
    else:
        with open(filepath) as f:
            lines = [l for l in f if l.strip()]
        return max(0, len(lines) - 1)


def check_migration_report():
    """Check migration_report.json exists and status == success."""
    if not os.path.exists(MIGRATION_REPORT):
        print("FAIL: migration_report.json missing")
        return False
    with open(MIGRATION_REPORT) as f:
        report = json.load(f)
    if report.get("status") != "success":
        print(f"FAIL: migration status={{report.get('status')}}")
        return False
    print("PASS: migration_report.json status=success")
    return True


def check_all_steps_completed():
    """Verify all expected steps appear as completed in the log."""
    if not os.path.exists(MIGRATION_LOG):
        print("FAIL: migration_log.jsonl missing")
        return False
    completed = set()
    with open(MIGRATION_LOG) as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("status") == "completed":
                completed.add(entry.get("step"))
    if not os.path.exists(MIGRATION_REPORT):
        print("FAIL: migration_report.json missing")
        return False
    with open(MIGRATION_REPORT) as f:
        report = json.load(f)
    expected_steps = set(report.get("steps_completed", []))
    if not expected_steps:
        print("FAIL: no steps_completed in migration_report")
        return False
    missing = expected_steps - completed
    if missing:
        print(f"FAIL: steps not logged as completed: {{missing}}")
        return False
    print(f"PASS: all {{len(expected_steps)}} steps logged as completed")
    return True


def check_row_counts():
    """Verify row counts match between source and destination."""
    src_path = os.path.join(SOURCE_DIR, f"{{PRIMARY_TABLE}}.{{SOURCE_EXT}}")
    if not os.path.exists(src_path):
        print(f"FAIL: source file missing: {{src_path}}")
        return False

    src_count = count_records(src_path)
    if src_count != EXPECTED_PRIMARY_ROWS:
        print(f"FAIL: source row count={{src_count}}, expected={{EXPECTED_PRIMARY_ROWS}}")
        return False

    # Check destination
    dest_path = os.path.join(DEST_DIR, f"{{PRIMARY_TABLE}}.jsonl")
    if not os.path.exists(dest_path):
        print(f"FAIL: destination file missing: {{dest_path}}")
        return False

    dest_count = count_records(dest_path)
    if dest_count != src_count:
        print(f"FAIL: row count mismatch src={{src_count}} dest={{dest_count}}")
        return False

    print(f"PASS: row counts match ({{src_count}} records)")
    return True


def check_checksums():
    """Verify checksums.json exists and has entries for both source and transformed."""
    if not os.path.exists(CHECKSUM_FILE):
        print("FAIL: checksums.json missing")
        return False
    with open(CHECKSUM_FILE) as f:
        checksums = json.load(f)
    if "source" not in checksums or "transformed" not in checksums:
        print("FAIL: checksums.json missing 'source' or 'transformed' keys")
        return False
    if not checksums["source"] or not checksums["transformed"]:
        print("FAIL: checksums.json has empty checksum sections")
        return False
    for section, entries in checksums.items():
        for fname, chk in entries.items():
            if not isinstance(chk, str) or len(chk) != 64:
                print(f"FAIL: invalid checksum for {{section}}/{{fname}}: {{chk!r}}")
                return False
    print(f"PASS: checksums.json valid ({{len(checksums['source'])}} source, "
          f"{{len(checksums['transformed'])}} transformed entries)")
    return True


def check_no_orphaned_references():
    """Verify no orphaned foreign keys in destination primary table."""
    ref_path = os.path.join(DEST_DIR, f"{{REF_TABLE}}.jsonl")
    primary_path = os.path.join(DEST_DIR, f"{{PRIMARY_TABLE}}.jsonl")

    if not os.path.exists(ref_path):
        print(f"FAIL: ref table missing in dest: {{ref_path}}")
        return False
    if not os.path.exists(primary_path):
        print(f"FAIL: primary table missing in dest: {{primary_path}}")
        return False

    valid_ids = set()
    with open(ref_path) as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if REF_KEY in rec:
                valid_ids.add(str(rec[REF_KEY]))

    orphans = []
    with open(primary_path) as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            val = str(rec.get(REF_KEY, ""))
            if val and val not in valid_ids:
                orphans.append(val)

    if orphans:
        print(f"FAIL: {{len(orphans)}} orphaned {{REF_KEY}} values found: {{orphans[:5]}}")
        return False

    print(f"PASS: no orphaned {{REF_KEY}} references ({{len(valid_ids)}} valid ids)")
    return True


def check_verification_report():
    """Verify verification_report.json confirms counts match."""
    if not os.path.exists(VERIFICATION_REPORT):
        print("FAIL: verification_report.json missing")
        return False
    with open(VERIFICATION_REPORT) as f:
        report = json.load(f)
    if not report.get("counts_match", False):
        print(f"FAIL: counts_match=False in verification_report: {{report}}")
        return False
    src_c = report.get("source_count", -1)
    dst_c = report.get("dest_count", -1)
    if src_c != dst_c:
        print(f"FAIL: source_count={{src_c}} != dest_count={{dst_c}}")
        return False
    print(f"PASS: verification_report counts_match=True ({{src_c}} records)")
    return True


def check_backup_exists():
    """Verify backup directory was created."""
    if not os.path.isdir(BACKUP_DIR):
        print(f"FAIL: backup directory missing: {{BACKUP_DIR}}")
        return False
    files = [f for f in os.listdir(BACKUP_DIR) if not f.startswith(".")]
    if not files:
        print("FAIL: backup directory is empty")
        return False
    print(f"PASS: backup directory exists with {{len(files)}} file(s)")
    return True


def check_steps_in_order():
    """Verify migration log shows steps executed in correct order."""
    if not os.path.exists(MIGRATION_LOG):
        print("FAIL: migration_log.jsonl missing")
        return False
    step_order = []
    with open(MIGRATION_LOG) as f:
        for line in f:
            if not line.strip():
                continue
            entry = json.loads(line)
            if entry.get("status") == "start" and entry.get("step") not in ("migration",):
                step_order.append(entry["step"])

    if not os.path.exists(MIGRATION_REPORT):
        print("FAIL: migration_report.json missing")
        return False
    with open(MIGRATION_REPORT) as f:
        report = json.load(f)
    expected_order = report.get("steps_completed", [])
    if step_order != expected_order:
        print(f"FAIL: steps executed out of order. Got {{step_order}}, expected {{expected_order}}")
        return False
    print(f"PASS: steps executed in correct order: {{step_order}}")
    return True


CHECKS = [
    ("migration_report_exists", check_migration_report),
    ("all_steps_completed", check_all_steps_completed),
    ("steps_in_order", check_steps_in_order),
    ("backup_exists", check_backup_exists),
    ("row_counts_match", check_row_counts),
    ("checksums_valid", check_checksums),
    ("verification_report_valid", check_verification_report),
    ("no_orphaned_references", check_no_orphaned_references),
]


def main():
    passed = 0
    failed = 0
    for name, fn in CHECKS:
        try:
            ok = fn()
        except Exception as exc:
            print(f"FAIL: {{name}} raised exception: {{exc}}")
            ok = False
        if ok:
            passed += 1
        else:
            failed += 1

    print(f"\\n{{passed}}/{{passed + failed}} checks passed")
    if failed == 0:
        print("ALL VALIDATION CHECKS PASSED")
        sys.exit(0)
    else:
        print("VALIDATION FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
'''

    # -----------------------------------------------------------------------
    # Spec and brief generators
    # -----------------------------------------------------------------------

    def _generate_spec(
        self,
        domain: dict,
        steps: list,
        primary_count: int,
        ref_count: int,
        source_checksum: str,
        dest_checksum: str,
        archive_name: str,
    ) -> str:
        step_lines = "\n".join(
            f"   {i+1}. **{s[0]}**: {s[1]}" for i, s in enumerate(steps)
        )
        rollback_lines = "\n".join(
            f"   - Rollback of `{s[0]}`: {ROLLBACK_ACTIONS[s[0]]}" for s in steps
        )
        has_update_ref = any(s[0] == "update_references" for s in steps)
        has_archive = any(s[0] == "archive_old" for s in steps)
        num_steps = len(steps)

        if has_update_ref:
            update_ref_section = (
                f"\nAfter **update_references**:\n"
                f"- Every `{domain['ref_key']}` in `data/new_format/{domain['primary_table']}.jsonl`"
                f" must exist in `data/new_format/{domain['ref_table']}.jsonl`.\n"
                f"- No orphaned `{domain['ref_key']}` values are permitted.\n"
            )
        else:
            update_ref_section = ""

        if has_archive:
            archive_section = (
                f"\nAfter **archive_old**:\n"
                f"- `{archive_name}` must exist and be a valid tar.gz containing the source data.\n"
            )
        else:
            archive_section = ""

        archive_line = (
            f"- `{archive_name}`: tar.gz archive of original source data."
            if has_archive else ""
        )

        return f"""# LH5: Data Migration

## Goal
Execute a complete {num_steps}-step data migration for a {domain["description"]} system.
Source data is in `data/old_format/` ({domain["old_format"]} format).
Target is `data/new_format/` (JSONL format).

## Source Data
- `data/old_format/{domain["primary_table"]}.{domain["old_format"]}`: **{primary_count} records** (primary table)
- `data/old_format/{domain["ref_table"]}.{domain["old_format"]}`: **{ref_count} records** (reference table)

## Migration Steps (execute in strict order)

{step_lines}

## Validation Checkpoints

After **transform_format**:
- `data/transformed/` must contain JSONL files for both tables.
- Row count in `data/transformed/{domain["primary_table"]}.jsonl` must equal `{primary_count}`.

After **validate_checksums**:
- `checksums.json` must exist with keys `"source"` and `"transformed"`.
- Each entry must be a valid 64-character hex SHA-256 string.

After **load_new_store**:
- `data/new_format/{domain["primary_table"]}.jsonl` must exist.
- Row count must equal `{primary_count}`.
- `data/new_format/{domain["ref_table"]}.jsonl` must exist.

After **verify_counts**:
- `verification_report.json` must exist.
- `counts_match` must be `true`.
- `source_count` must equal `dest_count` must equal `{primary_count}`.
{update_ref_section}{archive_section}
## Rollback Triggers

If any step fails (returns False or raises an exception), the migration must:
1. Immediately stop execution of further steps.
2. Execute rollback for all successfully completed steps **in reverse order**.

Rollback actions per step:
{rollback_lines}

## Required Output Files

- `migration_log.jsonl`: Every step start/complete/fail/rollback event.
- `migration_report.json`: `{{"status": "success", "steps_completed": [...], "total_steps": {num_steps}, "ts": "<iso>"}}`
- `checksums.json`: SHA-256 checksums of source and transformed files.
- `verification_report.json`: `{{"source_count": {primary_count}, "dest_count": {primary_count}, "counts_match": true}}`
- `data/backup/`: Copy of original source files.
- `data/new_format/{domain["primary_table"]}.jsonl`: Migrated primary records.
- `data/new_format/{domain["ref_table"]}.jsonl`: Migrated reference records.
{archive_line}

## Deliverables
- Complete implementation of all TODO functions in `migrate.py`.
- Run `python migrate.py` to execute the migration.
- Run `python validate.py` — all checks must pass.
"""

    def _generate_brief(self, domain: dict, num_steps: int) -> str:
        return f"""# LH5: Data Migration (Brief)

Data needs to be migrated to the new format. Execute the migration.

- Source: `data/old_format/` ({domain["old_format"]})
- Target: `data/new_format/` (jsonl)
- Domain: {domain["description"]}

Run: `python migrate.py`
Validate: `python validate.py`

The Planner has the full {num_steps}-step migration plan with validation checkpoints and rollback triggers.
"""
