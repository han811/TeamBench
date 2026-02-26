"""
Parameterized generator for LH4: Staged Deployment with Gates.

Each seed produces:
- Different number of stages (4-6)
- Different gate conditions (error rate threshold, latency threshold, health check count)
- Different deployment targets (canary %, services list, regions)
- Different validation thresholds
- Different rollback trigger conditions
- Seed-specific deploy.py (skeleton with stages but missing implementation),
  config/ (deployment configs), pre_deploy/ (migration script skeleton),
  validate.py (validation checks skeleton)

TNI Pattern F:
- Spec (seen by Planner/Verifier): complete deployment pipeline with all gate conditions,
  thresholds, and required outputs
- Brief (seen by Executor): "Deploy the new release to production."
"""
from __future__ import annotations

import json
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom, PROJECT_NAMES, CODENAMES


# Pool of service names for deployment targets
SERVICE_NAME_POOL = [
    "auth-service", "api-gateway", "user-service", "payment-service",
    "notification-service", "analytics-service", "search-service",
    "inventory-service", "order-service", "catalog-service",
    "session-service", "recommendation-service", "billing-service",
    "reporting-service", "cache-service",
]

# Pool of region names
REGION_POOL = [
    "us-east-1", "us-west-2", "eu-west-1", "eu-central-1",
    "ap-southeast-1", "ap-northeast-1", "ca-central-1", "sa-east-1",
]

# Pool of schema migration types
MIGRATION_TYPES = [
    ("add_column", "users", "last_login_at TIMESTAMP DEFAULT NULL"),
    ("add_index", "orders", "idx_orders_status ON orders(status)"),
    ("add_column", "sessions", "device_fingerprint VARCHAR(64) DEFAULT NULL"),
    ("add_index", "products", "idx_products_category ON products(category_id)"),
    ("add_column", "events", "processed_at TIMESTAMP DEFAULT NULL"),
    ("add_index", "audit_logs", "idx_audit_logs_user ON audit_logs(user_id)"),
    ("add_column", "payments", "retry_count INT DEFAULT 0"),
    ("add_index", "notifications", "idx_notif_read ON notifications(is_read, user_id)"),
]

# Pool of config keys that change between versions
CONFIG_CHANGE_POOL = [
    ("feature_flags.new_checkout", False, True),
    ("feature_flags.enhanced_search", False, True),
    ("rate_limits.api_requests_per_min", 1000, 1500),
    ("rate_limits.auth_requests_per_min", 500, 750),
    ("cache_ttl_seconds", 300, 600),
    ("max_connection_pool_size", 20, 30),
    ("request_timeout_ms", 5000, 3000),
    ("retry_max_attempts", 3, 5),
]

# Canary traffic percentages (step 2 options)
CANARY_PERCENTAGES = [5, 10, 15, 20, 25]

# Error rate thresholds (as percentages, e.g. 0.5 means <0.5%)
ERROR_RATE_THRESHOLDS = [0.5, 1.0, 1.5, 2.0]

# Latency thresholds in ms
LATENCY_THRESHOLDS = [150, 200, 250, 300]

# Health check minimum counts (number of passing health checks required)
HEALTH_CHECK_COUNTS = [3, 5, 7, 10]

# Post-deploy notification channels
NOTIFY_CHANNELS = [
    ("slack", "#deployments"),
    ("pagerduty", "deployment-team"),
    ("email", "ops@company.com"),
    ("teams", "DevOps channel"),
]

# Monitoring dashboards to update
MONITORING_DASHBOARDS = [
    "service-latency", "error-rates", "throughput", "cache-hit-rate",
    "db-connections", "memory-usage", "cpu-utilization", "request-volume",
]

# Release version patterns
RELEASE_VERSIONS = [
    ("1.4.2", "1.4.1"),
    ("2.1.0", "2.0.9"),
    ("3.0.1", "3.0.0"),
    ("1.8.5", "1.8.4"),
    ("2.5.0", "2.4.7"),
    ("4.2.1", "4.2.0"),
]


class Generator(TaskGenerator):
    task_id = "LH4_staged_deploy"
    domain = "operations"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # Vary number of stages (4-6)
        num_stages = rng.randint(4, 6)

        # Pick release version
        ver_idx = rng.randint(0, len(RELEASE_VERSIONS) - 1)
        new_version, old_version = RELEASE_VERSIONS[ver_idx]

        # Pick codename for this release
        codename = rng.choice(CODENAMES)

        # Pick services (3-5 services)
        num_services = rng.randint(3, 5)
        services = rng.sample(SERVICE_NAME_POOL, num_services)

        # Pick regions (2-3)
        num_regions = rng.randint(2, 3)
        regions = rng.sample(REGION_POOL, num_regions)

        # Canary percentage
        canary_pct = rng.choice(CANARY_PERCENTAGES)

        # Gate thresholds
        error_rate_threshold = rng.choice(ERROR_RATE_THRESHOLDS)
        latency_threshold_ms = rng.choice(LATENCY_THRESHOLDS)
        health_check_count = rng.choice(HEALTH_CHECK_COUNTS)

        # Schema migration
        mig_idx = rng.randint(0, len(MIGRATION_TYPES) - 1)
        mig_type, mig_table, mig_sql = MIGRATION_TYPES[mig_idx]

        # Config change
        cfg_idx = rng.randint(0, len(CONFIG_CHANGE_POOL) - 1)
        cfg_key, cfg_old_val, cfg_new_val = CONFIG_CHANGE_POOL[cfg_idx]

        # Notification channel
        notif_idx = rng.randint(0, len(NOTIFY_CHANNELS) - 1)
        notif_channel, notif_target = NOTIFY_CHANNELS[notif_idx]

        # Monitoring dashboards (pick 2-3)
        num_dashboards = rng.randint(2, 3)
        dashboards = rng.sample(MONITORING_DASHBOARDS, num_dashboards)

        # Rollback threshold = 2x the error rate threshold
        rollback_error_threshold = round(error_rate_threshold * 2, 1)

        # Build stage definitions based on num_stages
        stages = self._build_stages(
            num_stages, canary_pct, error_rate_threshold,
            latency_threshold_ms, health_check_count,
            notif_channel, notif_target, dashboards,
            services, regions,
        )

        # Expected output values (ground truth for grading)
        expected = {
            "new_version": new_version,
            "old_version": old_version,
            "codename": codename,
            "num_stages": num_stages,
            "stages": [s["name"] for s in stages],
            "canary_pct": canary_pct,
            "error_rate_threshold": error_rate_threshold,
            "latency_threshold_ms": latency_threshold_ms,
            "health_check_count": health_check_count,
            "migration_type": mig_type,
            "migration_table": mig_table,
            "migration_sql": mig_sql,
            "config_key": cfg_key,
            "config_old_val": cfg_old_val,
            "config_new_val": cfg_new_val,
            "notify_channel": notif_channel,
            "notify_target": notif_target,
            "dashboards": dashboards,
            "services": services,
            "regions": regions,
            "rollback_error_threshold": rollback_error_threshold,
        }

        # Generate workspace files
        workspace_files = {}

        # deploy.py - skeleton with TODO stubs
        workspace_files["deploy.py"] = self._generate_deploy_py(
            stages, new_version, old_version, codename,
            error_rate_threshold, latency_threshold_ms,
            health_check_count, rollback_error_threshold,
            services, regions, canary_pct,
        )

        # validate.py - validation checks skeleton
        workspace_files["validate.py"] = self._generate_validate_py(
            error_rate_threshold, latency_threshold_ms, health_check_count,
        )

        # config/deployment.json
        workspace_files["config/deployment.json"] = json.dumps({
            "release": {
                "version": new_version,
                "codename": codename,
                "previous_version": old_version,
            },
            "targets": {
                "services": services,
                "regions": regions,
            },
            "canary": {
                "traffic_percentage": None,   # TODO: fill in
                "duration_minutes": 10,
            },
            "gates": {
                "error_rate_max_pct": None,   # TODO: fill in
                "latency_p99_max_ms": None,   # TODO: fill in
                "health_checks_required": None,  # TODO: fill in
            },
            "rollback": {
                "auto_rollback_on_error_pct": None,  # TODO: fill in
                "preserve_migration": False,
            },
            "notifications": {
                "channel": notif_channel,
                "target": notif_target,
            },
        }, indent=2)

        # config/monitoring.json
        workspace_files["config/monitoring.json"] = json.dumps({
            "dashboards_to_update": [],   # TODO: fill in
            "alert_thresholds": {
                "error_rate_pct": None,   # TODO: fill in
                "latency_p99_ms": None,   # TODO: fill in
            },
        }, indent=2)

        # pre_deploy/migrate.py - schema migration skeleton
        workspace_files["pre_deploy/migrate.py"] = self._generate_migrate_py(
            mig_type, mig_table, mig_sql,
        )

        # pre_deploy/update_config.py - config update skeleton
        workspace_files["pre_deploy/update_config.py"] = self._generate_update_config_py(
            cfg_key, cfg_old_val, cfg_new_val,
        )

        spec_md = self._generate_spec(
            num_stages, stages, new_version, old_version, codename,
            services, regions, canary_pct,
            error_rate_threshold, latency_threshold_ms, health_check_count,
            rollback_error_threshold, mig_type, mig_table, mig_sql,
            cfg_key, cfg_old_val, cfg_new_val,
            notif_channel, notif_target, dashboards,
        )
        brief_md = self._generate_brief(new_version, codename)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    def _build_stages(
        self, num_stages, canary_pct, error_rate_threshold,
        latency_threshold_ms, health_check_count,
        notif_channel, notif_target, dashboards,
        services, regions,
    ) -> list:
        # Core 4 stages always present
        base_stages = [
            {
                "name": "pre_deploy",
                "label": "Stage 1: Pre-Deploy Checks",
                "gate": "Schema migration applied successfully AND config updated",
                "actions": [
                    "Run schema migration (pre_deploy/migrate.py)",
                    "Update application config (pre_deploy/update_config.py)",
                    "Verify migration applied: check migration_status.json exists and status == 'applied'",
                    "Verify config updated: check config_update_status.json exists and status == 'applied'",
                ],
                "outputs": ["output/migration_status.json", "output/config_update_status.json"],
            },
            {
                "name": "canary",
                "label": "Stage 2: Canary Deployment",
                "gate": f"Canary deployed to {canary_pct}% traffic AND health checks passing",
                "actions": [
                    f"Deploy new version to {canary_pct}% of traffic",
                    f"Run health checks against {health_check_count} endpoints",
                    "Write output/canary_status.json with fields: traffic_pct, healthy_endpoints, status",
                ],
                "outputs": ["output/canary_status.json"],
            },
            {
                "name": "validate",
                "label": "Stage 3: Validation",
                "gate": f"Error rate < {error_rate_threshold}% AND p99 latency < {latency_threshold_ms}ms",
                "actions": [
                    "Run python validate.py to check error rate and latency",
                    f"Assert error_rate < {error_rate_threshold} (percent)",
                    f"Assert latency_p99_ms < {latency_threshold_ms}",
                    "Write output/validation_report.json",
                ],
                "outputs": ["output/validation_report.json"],
            },
            {
                "name": "full_rollout",
                "label": "Stage 4: Full Rollout",
                "gate": "All services deployed to all regions AND 100% traffic shifted",
                "actions": [
                    f"Deploy to all services: {', '.join(services)}",
                    f"Deploy to all regions: {', '.join(regions)}",
                    "Shift traffic to 100% new version",
                    "Write output/rollout_status.json with fields: services_deployed, regions_deployed, traffic_pct",
                ],
                "outputs": ["output/rollout_status.json"],
            },
        ]

        if num_stages == 5:
            # Insert a smoke-test stage between validate and full_rollout
            smoke_stage = {
                "name": "smoke_test",
                "label": "Stage 5: Smoke Test",
                "gate": f"All {health_check_count} smoke test endpoints return HTTP 200",
                "actions": [
                    f"Run smoke tests against {health_check_count} endpoints",
                    "Assert all endpoints return status 200",
                    "Write output/smoke_test_results.json with fields: endpoints_tested, passed, failed",
                ],
                "outputs": ["output/smoke_test_results.json"],
            }
            base_stages.insert(3, smoke_stage)  # before full_rollout

        elif num_stages == 6:
            # Insert smoke-test AND a post-deploy monitoring stage
            smoke_stage = {
                "name": "smoke_test",
                "label": "Stage 5: Smoke Test",
                "gate": f"All {health_check_count} smoke test endpoints return HTTP 200",
                "actions": [
                    f"Run smoke tests against {health_check_count} endpoints",
                    "Assert all endpoints return status 200",
                    "Write output/smoke_test_results.json with fields: endpoints_tested, passed, failed",
                ],
                "outputs": ["output/smoke_test_results.json"],
            }
            post_stage = {
                "name": "post_deploy",
                "label": "Stage 6: Post-Deploy",
                "gate": "Monitoring updated AND notification sent",
                "actions": [
                    f"Update monitoring dashboards: {', '.join(dashboards)}",
                    f"Send notification via {notif_channel} to {notif_target}",
                    "Write output/post_deploy_status.json with fields: dashboards_updated, notification_sent, channel",
                ],
                "outputs": ["output/post_deploy_status.json"],
            }
            base_stages.insert(3, smoke_stage)  # before full_rollout
            base_stages.append(post_stage)      # after full_rollout

        # For 4-stage: append post-deploy as part of full_rollout actions
        if num_stages == 4:
            base_stages[3]["actions"] += [
                f"Update monitoring dashboards: {', '.join(dashboards)}",
                f"Send notification via {notif_channel} to {notif_target}",
            ]
            base_stages[3]["outputs"].append("output/post_deploy_status.json")

        return base_stages[:num_stages]

    def _generate_deploy_py(
        self, stages, new_version, old_version, codename,
        error_rate_threshold, latency_threshold_ms, health_check_count,
        rollback_error_threshold, services, regions, canary_pct,
    ) -> str:
        stage_names = [s["name"] for s in stages]
        services_repr = repr(services)
        regions_repr = repr(regions)
        dashboards_note = "# Update monitoring dashboards and send notification"

        return f'''"""
Staged deployment script for release {new_version} ({codename}).
Previous version: {old_version}

Implements a {len(stages)}-stage deployment pipeline with gate conditions.
Each stage must pass its gate before proceeding to the next.
Rollback is triggered automatically if error rate exceeds {rollback_error_threshold}%.

Usage:
    python deploy.py

Outputs written to output/ directory.
"""
import json
import os
import subprocess
import sys
from datetime import datetime, timezone


NEW_VERSION = "{new_version}"
OLD_VERSION = "{old_version}"
CODENAME = "{codename}"
CANARY_TRAFFIC_PCT = {canary_pct}          # TODO: read from config/deployment.json
ERROR_RATE_THRESHOLD = {error_rate_threshold}  # TODO: read from config/deployment.json
LATENCY_THRESHOLD_MS = {latency_threshold_ms}  # TODO: read from config/deployment.json
HEALTH_CHECKS_REQUIRED = {health_check_count}  # TODO: read from config/deployment.json
ROLLBACK_ERROR_THRESHOLD = {rollback_error_threshold}  # TODO: read from config/deployment.json
SERVICES = {services_repr}
REGIONS = {regions_repr}

STAGES = {repr(stage_names)}


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  Wrote {{path}}")


def load_config():
    """Load deployment config and populate gate thresholds."""
    with open("config/deployment.json") as f:
        return json.load(f)


def check_gate(stage_name, result):
    """
    Validate gate conditions for a stage.
    Returns True if gate passes, False if it fails.
    Raises RuntimeError if gate conditions indicate rollback is needed.
    """
    # TODO: implement gate checks per stage
    raise NotImplementedError(f"check_gate not implemented for stage: {{stage_name}}")


def rollback(reason):
    """
    Execute rollback to previous version.
    Writes output/rollback_status.json.
    """
    # TODO: implement rollback
    raise NotImplementedError("rollback() not implemented")


def stage_pre_deploy():
    """
    Stage 1: Pre-Deploy Checks.
    Gate: Schema migration applied AND config updated.
    """
    print("\\n[Stage 1] Pre-Deploy Checks")
    # TODO: run pre_deploy/migrate.py
    # TODO: run pre_deploy/update_config.py
    # TODO: verify both produce status == 'applied'
    # TODO: write output/migration_status.json and output/config_update_status.json
    raise NotImplementedError("stage_pre_deploy() not implemented")


def stage_canary():
    """
    Stage 2: Canary Deployment.
    Gate: {canary_pct}% traffic routed AND {health_check_count} health checks pass.
    """
    print("\\n[Stage 2] Canary Deployment")
    # TODO: deploy to canary ({canary_pct}% traffic)
    # TODO: run {health_check_count} health checks
    # TODO: write output/canary_status.json
    raise NotImplementedError("stage_canary() not implemented")


def stage_validate():
    """
    Stage 3: Validation.
    Gate: error_rate < {error_rate_threshold}% AND p99 latency < {latency_threshold_ms}ms.
    """
    print("\\n[Stage 3] Validation")
    # TODO: run python validate.py
    # TODO: assert error_rate < {error_rate_threshold}
    # TODO: assert latency_p99_ms < {latency_threshold_ms}
    # TODO: write output/validation_report.json
    # TODO: trigger rollback if error_rate >= {rollback_error_threshold}
    raise NotImplementedError("stage_validate() not implemented")


def stage_smoke_test():
    """
    Stage N: Smoke Test.
    Gate: All {health_check_count} smoke test endpoints return HTTP 200.
    """
    print("\\n[Stage: Smoke Test]")
    # TODO: run {health_check_count} smoke test requests
    # TODO: assert all return status 200
    # TODO: write output/smoke_test_results.json
    raise NotImplementedError("stage_smoke_test() not implemented")


def stage_full_rollout():
    """
    Stage N: Full Rollout.
    Gate: All services deployed to all regions AND 100% traffic shifted.
    Services: {services}
    Regions: {regions}
    """
    print("\\n[Stage: Full Rollout]")
    # TODO: deploy to all services: {services}
    # TODO: deploy to all regions: {regions}
    # TODO: shift traffic to 100%
    # TODO: write output/rollout_status.json
    {dashboards_note}
    raise NotImplementedError("stage_full_rollout() not implemented")


def stage_post_deploy():
    """
    Stage N: Post-Deploy.
    Gate: Monitoring updated AND notification sent.
    """
    print("\\n[Stage: Post-Deploy]")
    # TODO: update monitoring dashboards (from config/monitoring.json)
    # TODO: send deployment notification
    # TODO: write output/post_deploy_status.json
    raise NotImplementedError("stage_post_deploy() not implemented")


_STAGE_FNS = {{
    "pre_deploy": stage_pre_deploy,
    "canary": stage_canary,
    "validate": stage_validate,
    "smoke_test": stage_smoke_test,
    "full_rollout": stage_full_rollout,
    "post_deploy": stage_post_deploy,
}}


def main():
    print(f"=== Staged Deploy: {{NEW_VERSION}} ({{CODENAME}}) ===")
    print(f"Stages: {{STAGES}}")

    os.makedirs("output", exist_ok=True)

    deploy_log = []

    for stage_name in STAGES:
        fn = _STAGE_FNS.get(stage_name)
        if fn is None:
            print(f"ERROR: Unknown stage: {{stage_name}}")
            sys.exit(1)

        try:
            result = fn()
            deploy_log.append({{"stage": stage_name, "status": "pass", "ts": now_iso()}})
            print(f"  [PASS] {{stage_name}}")
        except NotImplementedError as e:
            print(f"  [FAIL] {{stage_name}}: {{e}}")
            deploy_log.append({{"stage": stage_name, "status": "not_implemented", "ts": now_iso()}})
            sys.exit(1)
        except RuntimeError as e:
            msg = str(e)
            deploy_log.append({{"stage": stage_name, "status": "fail", "error": msg, "ts": now_iso()}})
            print(f"  [FAIL] {{stage_name}}: {{msg}}")
            if "ROLLBACK" in msg:
                rollback(msg)
            sys.exit(1)

    # Write deploy log
    write_json("output/deploy_log.json", {{
        "version": NEW_VERSION,
        "codename": CODENAME,
        "stages_completed": [s["stage"] for s in deploy_log if s["status"] == "pass"],
        "total_stages": len(STAGES),
        "log": deploy_log,
        "completed_at": now_iso(),
    }})

    print(f"\\n=== Deployment complete: {{NEW_VERSION}} ===")


if __name__ == "__main__":
    main()
'''

    def _generate_validate_py(
        self, error_rate_threshold, latency_threshold_ms, health_check_count,
    ) -> str:
        return f'''"""
Validation script for staged deployment.
Checks error rate and latency against gate thresholds.
Writes output/validation_report.json.

Gate conditions:
  - error_rate < {error_rate_threshold}%
  - p99_latency_ms < {latency_threshold_ms}ms
"""
import json
import os
import sys
from datetime import datetime, timezone


ERROR_RATE_THRESHOLD = {error_rate_threshold}   # percent
LATENCY_P99_THRESHOLD = {latency_threshold_ms}  # milliseconds


def collect_metrics():
    """
    Collect error rate and latency metrics from the canary deployment.
    Returns dict with: error_rate (float, percent), latency_p99_ms (float).

    In a real deployment this would query monitoring APIs.
    For this task, simulate by reading output/canary_status.json if present,
    or use a synthetic healthy signal.
    """
    # TODO: implement metric collection
    # The implementation must:
    # 1. Read actual metrics (simulate from canary_status.json or monitoring)
    # 2. Return {{"error_rate": <float>, "latency_p99_ms": <float>}}
    raise NotImplementedError("collect_metrics() not implemented")


def check_thresholds(metrics):
    """
    Validate metrics against gate thresholds.
    Returns (passed: bool, failures: list[str]).
    """
    failures = []
    # TODO: implement threshold checks
    # Check: metrics["error_rate"] < ERROR_RATE_THRESHOLD
    # Check: metrics["latency_p99_ms"] < LATENCY_P99_THRESHOLD
    raise NotImplementedError("check_thresholds() not implemented")


def main():
    os.makedirs("output", exist_ok=True)

    metrics = collect_metrics()
    passed, failures = check_thresholds(metrics)

    report = {{
        "error_rate": metrics.get("error_rate"),
        "latency_p99_ms": metrics.get("latency_p99_ms"),
        "error_rate_threshold": ERROR_RATE_THRESHOLD,
        "latency_threshold_ms": LATENCY_P99_THRESHOLD,
        "passed": passed,
        "failures": failures,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }}

    with open("output/validation_report.json", "w") as f:
        json.dump(report, f, indent=2)

    print(f"Validation: passed={{passed}}, error_rate={{metrics.get('error_rate')}}%, "
          f"latency_p99={{metrics.get('latency_p99_ms')}}ms")

    if not passed:
        print(f"GATE FAIL: {{failures}}")
        sys.exit(1)

    print("Gate conditions met.")
    sys.exit(0)


if __name__ == "__main__":
    main()
'''

    def _generate_migrate_py(self, mig_type, mig_table, mig_sql) -> str:
        return f'''"""
Pre-deploy schema migration.
Migration type: {mig_type}
Target table: {mig_table}
SQL: {mig_sql}

Writes output/migration_status.json.
"""
import json
import os
from datetime import datetime, timezone


MIGRATION_TYPE = "{mig_type}"
MIGRATION_TABLE = "{mig_table}"
MIGRATION_SQL = "{mig_sql}"


def apply_migration():
    """
    Apply the schema migration.
    In this simulation, write a record of the applied migration.

    Returns dict with migration result.
    """
    # TODO: implement migration
    # Must:
    # 1. Record that migration was applied (simulate DB operation)
    # 2. Return {{"status": "applied", "migration_type": MIGRATION_TYPE,
    #             "table": MIGRATION_TABLE, "sql": MIGRATION_SQL, "applied_at": <iso_ts>}}
    raise NotImplementedError("apply_migration() not implemented")


def main():
    os.makedirs("output", exist_ok=True)
    result = apply_migration()

    with open("output/migration_status.json", "w") as f:
        json.dump(result, f, indent=2)

    print(f"Migration status: {{result['status']}}")
    if result["status"] != "applied":
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()
'''

    def _generate_update_config_py(self, cfg_key, cfg_old_val, cfg_new_val) -> str:
        return f'''"""
Pre-deploy config update.
Updates application configuration for the new release.

Config change:
  key:       {cfg_key}
  old value: {json.dumps(cfg_old_val)}
  new value: {json.dumps(cfg_new_val)}

Writes output/config_update_status.json.
"""
import json
import os
from datetime import datetime, timezone


CONFIG_KEY = "{cfg_key}"
CONFIG_OLD_VALUE = {json.dumps(cfg_old_val)}
CONFIG_NEW_VALUE = {json.dumps(cfg_new_val)}


def apply_config_update():
    """
    Apply the configuration update.
    Returns dict with update result.

    Must:
    1. Record the config change (key, old_value, new_value)
    2. Return {{"status": "applied", "key": CONFIG_KEY,
                "old_value": CONFIG_OLD_VALUE, "new_value": CONFIG_NEW_VALUE,
                "applied_at": <iso_ts>}}
    """
    # TODO: implement config update
    raise NotImplementedError("apply_config_update() not implemented")


def main():
    os.makedirs("output", exist_ok=True)
    result = apply_config_update()

    with open("output/config_update_status.json", "w") as f:
        json.dump(result, f, indent=2)

    print(f"Config update status: {{result['status']}}")
    if result["status"] != "applied":
        import sys
        sys.exit(1)


if __name__ == "__main__":
    main()
'''

    def _generate_spec(
        self, num_stages, stages, new_version, old_version, codename,
        services, regions, canary_pct,
        error_rate_threshold, latency_threshold_ms, health_check_count,
        rollback_error_threshold, mig_type, mig_table, mig_sql,
        cfg_key, cfg_old_val, cfg_new_val,
        notif_channel, notif_target, dashboards,
    ) -> str:
        stages_text = ""
        for i, stage in enumerate(stages, start=1):
            stages_text += f"\n### {stage['label']}\n"
            stages_text += f"**Gate**: {stage['gate']}\n\n"
            stages_text += "**Actions**:\n"
            for action in stage["actions"]:
                stages_text += f"- {action}\n"
            stages_text += "\n**Required outputs**: " + ", ".join(f"`{o}`" for o in stage["outputs"]) + "\n"

        services_list = ", ".join(f"`{s}`" for s in services)
        regions_list = ", ".join(f"`{r}`" for r in regions)
        dashboards_list = ", ".join(f"`{d}`" for d in dashboards)

        return f"""# LH4: Staged Deployment with Gates

## Overview

Deploy release **{new_version}** (codename: **{codename}**) using a {num_stages}-stage pipeline.
Previous version: `{old_version}`.
Each stage has gate conditions that must pass before proceeding to the next stage.
Rollback is triggered automatically if error rate exceeds **{rollback_error_threshold}%**.

## Release Details

| Field | Value |
|-------|-------|
| New version | `{new_version}` |
| Previous version | `{old_version}` |
| Codename | `{codename}` |
| Target services | {services_list} |
| Target regions | {regions_list} |
| Canary traffic | `{canary_pct}%` |

## Gate Thresholds

| Gate | Threshold |
|------|-----------|
| Error rate (validation gate) | < `{error_rate_threshold}%` |
| p99 Latency (validation gate) | < `{latency_threshold_ms}ms` |
| Health checks required (canary/smoke) | `{health_check_count}` endpoints |
| Auto-rollback trigger | error rate >= `{rollback_error_threshold}%` |

## Pre-Deploy Changes

### Schema Migration
- **Type**: `{mig_type}`
- **Table**: `{mig_table}`
- **SQL**: `{mig_sql}`
- **Script**: `pre_deploy/migrate.py`
- **Output**: `output/migration_status.json` with `status == "applied"`

### Config Update
- **Key**: `{cfg_key}`
- **Old value**: `{json.dumps(cfg_old_val)}`
- **New value**: `{json.dumps(cfg_new_val)}`
- **Script**: `pre_deploy/update_config.py`
- **Output**: `output/config_update_status.json` with `status == "applied"`

## Deployment Stages
{stages_text}
## Post-Deploy Requirements

- Update monitoring dashboards: {dashboards_list}
- Send deployment notification via `{notif_channel}` to `{notif_target}`
- Output: `output/post_deploy_status.json` with fields `dashboards_updated`, `notification_sent`, `channel`

## Config Files

### `config/deployment.json`
Must be completed with correct values before running:
- `canary.traffic_percentage` = `{canary_pct}`
- `gates.error_rate_max_pct` = `{error_rate_threshold}`
- `gates.latency_p99_max_ms` = `{latency_threshold_ms}`
- `gates.health_checks_required` = `{health_check_count}`
- `rollback.auto_rollback_on_error_pct` = `{rollback_error_threshold}`

### `config/monitoring.json`
Must be completed:
- `dashboards_to_update` = `{json.dumps(dashboards)}`
- `alert_thresholds.error_rate_pct` = `{error_rate_threshold}`
- `alert_thresholds.latency_p99_ms` = `{latency_threshold_ms}`

## Rollback Requirements

- `rollback()` function in `deploy.py` must write `output/rollback_status.json`
- Fields: `triggered_at`, `reason`, `rolled_back_to` (= `"{old_version}"`), `status` (= `"completed"`)
- Rollback is triggered when `error_rate >= {rollback_error_threshold}%` during validation

## Final Deliverables

1. All {num_stages} stages implemented in `deploy.py`
2. `pre_deploy/migrate.py` fully implemented
3. `pre_deploy/update_config.py` fully implemented
4. `validate.py` fully implemented
5. `config/deployment.json` values filled in
6. `config/monitoring.json` values filled in
7. `python deploy.py` runs end-to-end without errors
8. All `output/` JSON files present with correct fields

## Execution

```bash
python deploy.py
```
"""

    def _generate_brief(self, new_version, codename) -> str:
        return f"""# LH4: Staged Deployment (Brief)

Deploy release **{new_version}** ({codename}) to production.

Run: `python deploy.py`

The deployment must complete all stages in order.
Each stage has gate conditions that must pass before proceeding.
See the Planner's spec for stage details and thresholds.
"""
