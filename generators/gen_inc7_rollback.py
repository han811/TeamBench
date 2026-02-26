"""
Parameterized generator for INC7: Safe Deployment Rollback.

Each seed produces:
  - Different deployment type (web_app, api_service, data_pipeline, ml_model)
  - Different number of rollback steps (5-7)
  - Different data preservation rules (what data written during the failed deploy
    must be retained vs. discarded)
  - Different config files (old vs. new with seed-specific values)
  - Different database migration state (schema changed or not)
  - Seed-specific deploy_state.json, rollback.py skeleton, config/old_config.json,
    config/new_config.json, database/migrations.json, expected.json

TNI driver (F,C pattern):
  - Spec contains an ordered rollback checklist (step 1: pause traffic,
    step 2: revert app code, step 3: rollback database if schema changed,
    step 4: restore config, step 5: resume traffic, step 6: verify health),
    plus data preservation constraints (some records written during the failed
    deploy MUST be preserved — e.g. user-submitted forms, payment events).
  - Brief says only "The latest deployment failed. Execute a safe rollback."
  - Without the Planner's checklist, the Executor may skip the DB rollback,
    restore config before reverting code, or discard data that must be kept.

The grader checks (10+ checks):
  1. rollback.py runs without error (exit 0)
  2. deploy_state.json shows status=rolled_back after script runs
  3. Traffic paused before code revert (step order: pause_traffic first)
  4. App code reverted to previous version
  5. DB rolled back only if schema_changed=true in deploy state
  6. Config restored to old values (seed-specific key check)
  7. Traffic resumed after config restored
  8. Health check passes (health_status=ok in output)
  9. Preserved data records are present in preserved_data.json
  10. Discarded data is absent from preserved_data.json
  11. rollback_log.json has all 6 steps recorded in correct order
  12. attestation.json with verdict=pass
"""
from __future__ import annotations

import json

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# ---------------------------------------------------------------------------
# Pools
# ---------------------------------------------------------------------------

DEPLOYMENT_TYPES = [
    "web_app",
    "api_service",
    "data_pipeline",
    "ml_model",
    "message_broker",
    "cache_service",
]

# (service_name, old_version, new_version)
SERVICE_VERSIONS = [
    ("frontend", "2.4.1", "2.5.0"),
    ("auth_api", "1.8.3", "1.9.0"),
    ("payment_service", "3.1.2", "3.2.0"),
    ("recommendation_engine", "0.9.1", "1.0.0"),
    ("notification_service", "2.0.4", "2.1.0"),
    ("search_service", "4.2.0", "4.3.0"),
    ("analytics_pipeline", "1.3.7", "1.4.0"),
    ("user_profile_api", "2.7.1", "2.8.0"),
]

# Config key/value pairs: (key, old_value, new_broken_value, description)
CONFIG_VARIANTS = [
    ("max_connections", 100, 500, "database connection pool size"),
    ("request_timeout_ms", 5000, 50, "upstream request timeout in milliseconds"),
    ("cache_ttl_seconds", 300, 0, "cache entry time-to-live"),
    ("worker_threads", 8, 128, "number of worker threads"),
    ("rate_limit_rps", 1000, 10, "requests per second rate limit"),
    ("retry_attempts", 3, 0, "number of retry attempts on failure"),
    ("session_timeout_sec", 3600, 1, "session timeout in seconds"),
    ("batch_size", 50, 5000, "batch processing size"),
]

# Database migration scenarios: (schema_changed, migration_id, migration_desc, rollback_sql)
DB_MIGRATIONS = [
    (
        True,
        "m_20240615_001",
        "Added nullable column user_tier to accounts table",
        "ALTER TABLE accounts DROP COLUMN IF EXISTS user_tier;",
    ),
    (
        False,
        None,
        "No schema changes — data-only migration (seed records)",
        None,
    ),
    (
        True,
        "m_20240616_002",
        "Created new index on orders(created_at, status)",
        "DROP INDEX IF EXISTS idx_orders_created_status;",
    ),
    (
        True,
        "m_20240617_003",
        "Added foreign key constraint payments(user_id) -> users(id)",
        "ALTER TABLE payments DROP CONSTRAINT IF EXISTS fk_payments_user;",
    ),
    (
        False,
        None,
        "No schema changes — config table values updated only",
        None,
    ),
    (
        True,
        "m_20240618_004",
        "Renamed column event_ts to event_timestamp in audit_log",
        "ALTER TABLE audit_log RENAME COLUMN event_timestamp TO event_ts;",
    ),
]

# Data preservation rules: records that must be kept even after rollback
# (preserve_category, preserve_reason, discard_category)
DATA_RULES = [
    (
        "payment_events",
        "Payment events recorded during the failed deploy are financial records "
        "and MUST be preserved for audit compliance. They must appear in "
        "preserved_data.json after rollback.",
        "failed_sessions",
    ),
    (
        "user_registrations",
        "New user account registrations that occurred during the failed deploy "
        "window must be preserved so users are not locked out. They must appear "
        "in preserved_data.json after rollback.",
        "temp_cache_entries",
    ),
    (
        "order_submissions",
        "Customer orders submitted during the failed deploy window are binding "
        "contracts and must be preserved. They must appear in preserved_data.json.",
        "incomplete_sessions",
    ),
    (
        "audit_log_entries",
        "Security audit log entries from the failed deploy window cannot be "
        "discarded (regulatory requirement). They must appear in preserved_data.json.",
        "draft_records",
    ),
    (
        "form_submissions",
        "User-submitted forms recorded during the failed window must be preserved "
        "to avoid data loss. They must appear in preserved_data.json.",
        "prefetch_cache",
    ),
    (
        "webhook_events",
        "Inbound webhook events recorded during the failed deploy are idempotency "
        "keys for third-party systems and must be preserved. They must appear in "
        "preserved_data.json.",
        "stale_locks",
    ),
]

# Health check endpoint / success indicator pairs
HEALTH_CONFIGS = [
    ("http://localhost:8080/health", "healthy"),
    ("http://localhost:9000/status", "ok"),
    ("http://localhost:3000/ping", "pong"),
    ("http://localhost:8000/ready", "ready"),
    ("http://localhost:5000/healthz", "alive"),
]


class Generator(TaskGenerator):
    task_id = "INC7_rollback"
    domain = "incident"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # Deterministic selection with different strides for contamination resistance
        deploy_type = DEPLOYMENT_TYPES[seed % len(DEPLOYMENT_TYPES)]
        svc_name, old_ver, new_ver = SERVICE_VERSIONS[(seed * 3 + 1) % len(SERVICE_VERSIONS)]
        cfg_key, cfg_old, cfg_broken, cfg_desc = CONFIG_VARIANTS[
            (seed * 5 + 2) % len(CONFIG_VARIANTS)
        ]
        schema_changed, migration_id, migration_desc, rollback_sql = DB_MIGRATIONS[
            (seed * 7 + 3) % len(DB_MIGRATIONS)
        ]
        preserve_cat, preserve_reason, discard_cat = DATA_RULES[
            (seed * 11 + 4) % len(DATA_RULES)
        ]
        health_endpoint, health_indicator = HEALTH_CONFIGS[
            (seed * 13 + 5) % len(HEALTH_CONFIGS)
        ]

        # Port derived from health endpoint
        port = int(health_endpoint.split(":")[2].split("/")[0])

        # Generate seed-specific record IDs for preserved/discarded data
        preserve_ids = [f"rec_{seed * 100 + i:05d}" for i in range(1, 4)]
        discard_ids = [f"tmp_{seed * 100 + i:05d}" for i in range(1, 3)]

        # Number of config keys (always includes the broken one + 2-3 stable ones)
        stable_configs = {
            "log_level": "info",
            "environment": "production",
            "region": rng.choice(["us-east-1", "eu-west-1", "ap-southeast-1"]),
        }

        expected = {
            "deploy_type": deploy_type,
            "service_name": svc_name,
            "old_version": old_ver,
            "new_version": new_ver,
            "config_key": cfg_key,
            "config_old_value": cfg_old,
            "config_broken_value": cfg_broken,
            "schema_changed": schema_changed,
            "migration_id": migration_id,
            "rollback_sql": rollback_sql,
            "preserve_category": preserve_cat,
            "discard_category": discard_cat,
            "preserve_ids": preserve_ids,
            "discard_ids": discard_ids,
            "health_endpoint": health_endpoint,
            "health_indicator": health_indicator,
            "port": port,
            "rollback_steps_ordered": [
                "pause_traffic",
                "revert_app_code",
                "rollback_database",
                "restore_config",
                "resume_traffic",
                "verify_health",
            ],
        }

        workspace_files = self._build_workspace(
            deploy_type=deploy_type,
            svc_name=svc_name,
            old_ver=old_ver,
            new_ver=new_ver,
            cfg_key=cfg_key,
            cfg_old=cfg_old,
            cfg_broken=cfg_broken,
            cfg_desc=cfg_desc,
            schema_changed=schema_changed,
            migration_id=migration_id,
            migration_desc=migration_desc,
            rollback_sql=rollback_sql,
            preserve_cat=preserve_cat,
            discard_cat=discard_cat,
            preserve_ids=preserve_ids,
            discard_ids=discard_ids,
            health_endpoint=health_endpoint,
            health_indicator=health_indicator,
            port=port,
            stable_configs=stable_configs,
        )

        spec_md = self._generate_spec(
            deploy_type=deploy_type,
            svc_name=svc_name,
            old_ver=old_ver,
            new_ver=new_ver,
            cfg_key=cfg_key,
            cfg_old=cfg_old,
            cfg_broken=cfg_broken,
            cfg_desc=cfg_desc,
            schema_changed=schema_changed,
            migration_id=migration_id,
            migration_desc=migration_desc,
            rollback_sql=rollback_sql,
            preserve_cat=preserve_cat,
            preserve_reason=preserve_reason,
            discard_cat=discard_cat,
            preserve_ids=preserve_ids,
            discard_ids=discard_ids,
            health_endpoint=health_endpoint,
            health_indicator=health_indicator,
        )
        brief_md = self._generate_brief(svc_name=svc_name, new_ver=new_ver)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # ------------------------------------------------------------------
    def _build_workspace(
        self,
        deploy_type: str,
        svc_name: str,
        old_ver: str,
        new_ver: str,
        cfg_key: str,
        cfg_old,
        cfg_broken,
        cfg_desc: str,
        schema_changed: bool,
        migration_id,
        migration_desc: str,
        rollback_sql,
        preserve_cat: str,
        discard_cat: str,
        preserve_ids: list,
        discard_ids: list,
        health_endpoint: str,
        health_indicator: str,
        port: int,
        stable_configs: dict,
    ) -> dict[str, str]:

        old_config = {cfg_key: cfg_old, **stable_configs}
        new_config = {cfg_key: cfg_broken, **stable_configs}

        # deploy_state.json — current broken state
        deploy_state = {
            "status": "failed",
            "service": svc_name,
            "deploy_type": deploy_type,
            "previous_version": old_ver,
            "current_version": new_ver,
            "schema_changed": schema_changed,
            "migration_id": migration_id,
            "traffic_paused": False,
            "deploy_timestamp": "2024-06-15T03:00:00Z",
            "failure_timestamp": "2024-06-15T03:12:47Z",
            "failure_reason": (
                f"Health check failed after deploy: {health_endpoint} "
                f"returned 503 instead of '{health_indicator}'"
            ),
        }

        # database/migrations.json — tracks applied migrations
        migrations_data = {
            "applied": (
                [
                    {
                        "id": migration_id,
                        "description": migration_desc,
                        "applied_at": "2024-06-15T03:05:12Z",
                        "status": "applied",
                        "rollback_sql": rollback_sql,
                    }
                ]
                if schema_changed
                else []
            ),
            "pending": [],
        }

        # database/preserved_records.json — records written during failed deploy
        # that must be preserved
        preserved_records = {
            preserve_cat: [
                {
                    "id": rec_id,
                    "recorded_at": "2024-06-15T03:08:00Z",
                    "status": "committed",
                    "source": "failed_deploy_window",
                }
                for rec_id in preserve_ids
            ],
            discard_cat: [
                {
                    "id": rec_id,
                    "recorded_at": "2024-06-15T03:09:00Z",
                    "status": "uncommitted",
                    "source": "failed_deploy_window",
                }
                for rec_id in discard_ids
            ],
        }

        # rollback.py skeleton — agent must implement this
        rollback_skeleton = _rollback_skeleton(
            svc_name=svc_name,
            old_ver=old_ver,
            new_ver=new_ver,
            cfg_key=cfg_key,
            schema_changed=schema_changed,
            migration_id=migration_id,
            preserve_cat=preserve_cat,
            discard_cat=discard_cat,
            preserve_ids=preserve_ids,
            discard_ids=discard_ids,
            health_endpoint=health_endpoint,
            health_indicator=health_indicator,
        )

        return {
            "deploy_state.json": json.dumps(deploy_state, indent=2),
            "rollback.py": rollback_skeleton,
            "config/old_config.json": json.dumps(old_config, indent=2),
            "config/new_config.json": json.dumps(new_config, indent=2),
            "database/migrations.json": json.dumps(migrations_data, indent=2),
            "database/preserved_records.json": json.dumps(preserved_records, indent=2),
            "deploy.log": _deploy_log(
                svc_name=svc_name,
                old_ver=old_ver,
                new_ver=new_ver,
                cfg_key=cfg_key,
                cfg_broken=cfg_broken,
                migration_id=migration_id,
                schema_changed=schema_changed,
                health_endpoint=health_endpoint,
                health_indicator=health_indicator,
            ),
        }

    # ------------------------------------------------------------------
    def _generate_spec(
        self,
        deploy_type: str,
        svc_name: str,
        old_ver: str,
        new_ver: str,
        cfg_key: str,
        cfg_old,
        cfg_broken,
        cfg_desc: str,
        schema_changed: bool,
        migration_id,
        migration_desc: str,
        rollback_sql,
        preserve_cat: str,
        preserve_reason: str,
        discard_cat: str,
        preserve_ids: list,
        discard_ids: list,
        health_endpoint: str,
        health_indicator: str,
    ) -> str:
        db_step_detail = (
            f"Migration `{migration_id}` was applied ({migration_desc}). "
            f"You MUST roll it back by executing:\n  `{rollback_sql}`\n"
            f"  Write the rollback result to `database/migrations.json` "
            f"(set status to `rolled_back` for this migration)."
            if schema_changed
            else "No schema migration was applied. Skip the database rollback sub-step "
            "(do not modify `database/migrations.json`). Only data-only changes "
            "were made; those are handled by the data preservation step."
        )

        preserve_ids_str = ", ".join(f'"{r}"' for r in preserve_ids)
        discard_ids_str = ", ".join(f'"{r}"' for r in discard_ids)

        return f"""# INC7: Safe Deployment Rollback

## Incident Summary

**Incident ID**: INC-2024-0615-007
**Severity**: P1
**Deployment Type**: {deploy_type}
**Service**: `{svc_name}`
**Failed Version**: `{new_ver}` (must be rolled back to `{old_ver}`)

The deployment of `{svc_name}` v{new_ver} failed during roll-out.
The health check at `{health_endpoint}` did not return `{health_indicator}`.
Traffic is currently being served by the broken version.

Review `deploy.log` for the failure timeline and `deploy_state.json`
for the current system state.

---

## Rollback Checklist (ORDERED — execute in this exact sequence)

**CRITICAL**: Steps must be executed in the order listed. Skipping or
reordering steps causes data loss or extended downtime.

### Step 1: Pause Traffic
- Set `traffic_paused: true` in `deploy_state.json`.
- Log `{{"step": "pause_traffic", "status": "done"}}` to `rollback_log.json`.
- Rationale: prevents new requests from hitting the broken version while
  code is in a transitional state.

### Step 2: Revert App Code
- Update `deploy_state.json`: set `current_version` back to `{old_ver}`.
- Log `{{"step": "revert_app_code", "status": "done"}}` to `rollback_log.json`.
- Rationale: must happen AFTER traffic is paused to avoid split-brain (some
  requests hitting old code, some hitting new code mid-switch).

### Step 3: Rollback Database (conditional)
{db_step_detail}
- Log `{{"step": "rollback_database", "status": "done"}}` to `rollback_log.json`
  regardless (record whether it was a no-op or executed).
- Rationale: schema rollback must happen AFTER code revert so that the reverted
  code and the schema are compatible before traffic resumes.

### Step 4: Restore Config
- Copy `config/old_config.json` over `config/active_config.json`
  (create `config/active_config.json` with the old config contents).
- Verify that `{cfg_key}` is restored to `{cfg_old}` (the broken deploy set it to
  `{cfg_broken}`, which caused {cfg_desc} issues).
- Log `{{"step": "restore_config", "status": "done"}}` to `rollback_log.json`.
- Rationale: config must be restored after code revert to ensure the old code
  sees the config values it was designed for.

### Step 5: Resume Traffic
- Set `traffic_paused: false` in `deploy_state.json`.
- Log `{{"step": "resume_traffic", "status": "done"}}` to `rollback_log.json`.
- Rationale: only re-enable traffic after all code + config + DB changes are consistent.

### Step 6: Verify Health
- Simulate a health check: write `{{"health_status": "ok", "endpoint": "{health_endpoint}",
  "service": "{svc_name}", "version": "{old_ver}"}}` to `health_check_result.json`.
- Set `deploy_state.json` `status` to `rolled_back`.
- Log `{{"step": "verify_health", "status": "done"}}` to `rollback_log.json`.

---

## Data Preservation Constraints

**These constraints take effect regardless of step order.**

### Must Preserve — `{preserve_cat}`
{preserve_reason}
- Record IDs to preserve: {preserve_ids_str}
- Action: write these records (from `database/preserved_records.json`) to
  `preserved_data.json` under the key `"{preserve_cat}"`.

### Must Discard — `{discard_cat}`
Records in the `{discard_cat}` category were created by the broken deploy
and are invalid / uncommitted. Do NOT include them in `preserved_data.json`.
- Record IDs to discard: {discard_ids_str}

---

## Deliverables

After rollback completes, the following files must exist in the workspace:

| File | Contents |
|------|----------|
| `deploy_state.json` | `status: rolled_back`, `current_version: {old_ver}`, `traffic_paused: false` |
| `config/active_config.json` | Identical to `config/old_config.json` |
| `rollback_log.json` | Array of 6 step records in correct order |
| `preserved_data.json` | `{preserve_cat}` records only (no `{discard_cat}`) |
| `health_check_result.json` | `health_status: ok` |
| `attestation.json` | `{{"verdict": "pass", "service": "{svc_name}", "rolled_back_to": "{old_ver}"}}` |

---

## Scoring Rubric

- **Step ordering** (steps 1-6 in correct sequence): 2 pts
- **Database rollback correct** (executed iff schema_changed=true): 2 pts
- **Config restored** ({cfg_key} = {cfg_old}): 2 pts
- **Data preserved** ({preserve_cat} present, {discard_cat} absent): 2 pts
- **Health check passes**: 1 pt
- **Attestation valid**: 1 pt
"""

    def _generate_brief(self, svc_name: str, new_ver: str) -> str:
        return f"""# INC7: Safe Deployment Rollback (Brief)

The latest deployment of `{svc_name}` v{new_ver} has failed.
Health checks are returning errors. Traffic is currently hitting the broken version.

**Goal**: Execute a safe rollback.

Implement `rollback.py` to perform the rollback. When complete, the workspace
must contain `deploy_state.json` with `status=rolled_back`, a `rollback_log.json`,
`preserved_data.json`, `config/active_config.json`, `health_check_result.json`,
and `attestation.json` with `verdict=pass`.

The Planner has a full incident report with the ordered rollback checklist,
database migration details, and data preservation requirements.
Coordinate with the Planner before implementing.

Run: `python rollback.py`
"""


# ---------------------------------------------------------------------------
# Module-level code-generation helpers
# ---------------------------------------------------------------------------

def _rollback_skeleton(
    svc_name: str,
    old_ver: str,
    new_ver: str,
    cfg_key: str,
    schema_changed: bool,
    migration_id,
    preserve_cat: str,
    discard_cat: str,
    preserve_ids: list,
    discard_ids: list,
    health_endpoint: str,
    health_indicator: str,
) -> str:
    schema_comment = (
        f"    # SCHEMA CHANGED: migration {migration_id} must be rolled back"
        if schema_changed
        else "    # No schema migration applied — this step is a no-op"
    )
    preserve_comment = (
        f"    # Preserve category '{preserve_cat}' records: {preserve_ids}\n"
        f"    # Discard category '{discard_cat}' records: {discard_ids}"
    )
    return f'''\
"""
rollback.py — Execute safe rollback of failed deployment.

Service: {svc_name}
Failed version: {new_ver}
Target version: {old_ver}

IMPORTANT: Steps must be executed in this exact order:
  1. pause_traffic
  2. revert_app_code
  3. rollback_database  (conditional: only if schema_changed=True)
  4. restore_config
  5. resume_traffic
  6. verify_health

Read the full spec for data preservation constraints before implementing.
"""
import json
import os
import shutil


WORKSPACE = os.path.dirname(os.path.abspath(__file__))


def load_json(path):
    with open(os.path.join(WORKSPACE, path)) as f:
        return json.load(f)


def save_json(path, data):
    abs_path = os.path.join(WORKSPACE, path)
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, "w") as f:
        json.dump(data, f, indent=2)


def append_log(step, status="done"):
    log_path = os.path.join(WORKSPACE, "rollback_log.json")
    if os.path.exists(log_path):
        log = json.load(open(log_path))
    else:
        log = []
    log.append({{"step": step, "status": status}})
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)


def step1_pause_traffic(state):
    """Step 1: Pause traffic before any changes."""
    # TODO: set traffic_paused=True in state and save deploy_state.json
    raise NotImplementedError("step1_pause_traffic not implemented")


def step2_revert_app_code(state):
    """Step 2: Revert application code to previous version."""
    # TODO: update current_version in state to the old version and save
    raise NotImplementedError("step2_revert_app_code not implemented")


def step3_rollback_database(state):
    """Step 3: Roll back database migration if schema was changed."""
{schema_comment}
    # TODO: check state["schema_changed"]; if True, update database/migrations.json
    #       to mark the migration as rolled_back.
    raise NotImplementedError("step3_rollback_database not implemented")


def step4_restore_config():
    """Step 4: Restore configuration to pre-deploy values."""
    # TODO: copy config/old_config.json to config/active_config.json
    raise NotImplementedError("step4_restore_config not implemented")


def step5_resume_traffic(state):
    """Step 5: Resume traffic after all changes are consistent."""
    # TODO: set traffic_paused=False in state and save deploy_state.json
    raise NotImplementedError("step5_resume_traffic not implemented")


def step6_verify_health(state):
    """Step 6: Verify service health and finalize rollback."""
    # TODO: write health_check_result.json and set state status=rolled_back
    raise NotImplementedError("step6_verify_health not implemented")


def preserve_data():
    """Preserve required records from the failed deploy window."""
{preserve_comment}
    # TODO: read database/preserved_records.json and write preserved_data.json
    #       Include only the records that must be preserved (not discarded).
    raise NotImplementedError("preserve_data not implemented")


def write_attestation(state):
    """Write attestation.json confirming rollback success."""
    # TODO: write attestation.json with verdict=pass
    raise NotImplementedError("write_attestation not implemented")


def main():
    state = load_json("deploy_state.json")

    step1_pause_traffic(state)
    step2_revert_app_code(state)
    step3_rollback_database(state)
    step4_restore_config()
    step5_resume_traffic(state)
    step6_verify_health(state)
    preserve_data()
    write_attestation(state)

    print("Rollback complete.")


if __name__ == "__main__":
    main()
'''


def _deploy_log(
    svc_name: str,
    old_ver: str,
    new_ver: str,
    cfg_key: str,
    cfg_broken,
    migration_id,
    schema_changed: bool,
    health_endpoint: str,
    health_indicator: str,
) -> str:
    migration_lines = (
        f"2024-06-15T03:05:12Z  INFO  [deploy] Running database migration {migration_id}\n"
        f"2024-06-15T03:05:18Z  INFO  [deploy] Migration {migration_id} applied successfully\n"
        if schema_changed
        else "2024-06-15T03:05:12Z  INFO  [deploy] No schema migrations to run\n"
    )
    return (
        f"2024-06-15T03:00:00Z  INFO  [deploy] Starting deployment of {svc_name} "
        f"v{new_ver} (previous: v{old_ver})\n"
        f"2024-06-15T03:00:05Z  INFO  [deploy] Draining traffic from old instances\n"
        f"2024-06-15T03:00:30Z  INFO  [deploy] Traffic drained — old instances stopped\n"
        f"2024-06-15T03:01:00Z  INFO  [deploy] Starting new instances with v{new_ver}\n"
        f"2024-06-15T03:01:15Z  INFO  [deploy] Applying config: {cfg_key}={cfg_broken}\n"
        + migration_lines
        + f"2024-06-15T03:10:00Z  INFO  [deploy] New instances started — "
        f"running health checks\n"
        f"2024-06-15T03:10:05Z  WARN  [deploy] Health check attempt 1/3 failed: "
        f"{health_endpoint} returned 503\n"
        f"2024-06-15T03:10:35Z  WARN  [deploy] Health check attempt 2/3 failed: "
        f"{health_endpoint} returned 503\n"
        f"2024-06-15T03:11:05Z  WARN  [deploy] Health check attempt 3/3 failed: "
        f"{health_endpoint} returned 503 (expected: {health_indicator!r})\n"
        f"2024-06-15T03:11:06Z  ERROR [deploy] Deployment FAILED — "
        f"health check threshold exceeded\n"
        f"2024-06-15T03:12:47Z  ERROR [deploy] Service {svc_name} v{new_ver} "
        f"is unhealthy — manual rollback required\n"
        f"2024-06-15T03:12:48Z  ALERT [on-call] Incident INC-2024-0615-007 opened. "
        f"Severity: P1. Service: {svc_name}\n"
    )
