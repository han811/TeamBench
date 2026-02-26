"""
Parameterized generator for PIPE4: CI/CD Pipeline Fix.

Each seed produces:
  - A different project context (web-app, data-service, ml-service, mobile-backend)
  - 6-stage pipeline: lint -> test -> build -> deploy-staging -> integration-test -> deploy-prod
  - Deliberate bugs injected into pipeline.json:
      * wrong_order: stages out of sequence (e.g. build before test)
      * missing_env_var: required environment variable absent from a stage
      * wrong_artifact_path: artifact path references wrong directory/filename
      * missing_stage: an entire required stage is omitted from the pipeline
  - scripts/: build.sh, test.sh, deploy.sh with bugs (wrong commands, missing checks)
  - .env.example: environment variable template

TNI Design (Pattern A+F — Spec has complete pipeline requirements, Brief is vague):
  - Brief: "The CI/CD pipeline is failing. Fix it so builds and deploys work correctly."
  - Spec (Planner-visible): complete pipeline stage definitions, required env vars per stage,
    artifact paths, deployment order constraints, script requirements.
  - Executor sees: broken pipeline.json, broken scripts, .env.example.
  - Without the Planner's spec the Executor cannot know correct stage order, env vars, or paths.
"""
from __future__ import annotations

import json
from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# ── Project catalogue ──────────────────────────────────────────────────────────

PROJECTS = [
    {
        "name": "web-app",
        "display": "Web Application",
        "app_name": "webapp",
        "build_output": "dist/",
        "artifact_name": "webapp-release.tar.gz",
        "test_command": "pytest tests/ --cov=src",
        "lint_command": "flake8 src/ tests/",
        "build_command": "python setup.py bdist --dist-dir dist/",
        "stages": [
            {
                "name": "lint",
                "description": "Run code linting checks",
                "script": "scripts/lint.sh",
                "required_env": ["CI", "LINT_CONFIG"],
                "artifacts_produced": [],
                "depends_on": [],
            },
            {
                "name": "test",
                "description": "Run unit and integration tests",
                "script": "scripts/test.sh",
                "required_env": ["CI", "TEST_DB_URL", "TEST_REPORT_DIR"],
                "artifacts_produced": ["reports/test-results.xml"],
                "depends_on": ["lint"],
            },
            {
                "name": "build",
                "description": "Build release artifact",
                "script": "scripts/build.sh",
                "required_env": ["CI", "BUILD_VERSION", "BUILD_OUTPUT_DIR"],
                "artifacts_produced": ["dist/webapp-release.tar.gz"],
                "depends_on": ["test"],
            },
            {
                "name": "deploy-staging",
                "description": "Deploy to staging environment",
                "script": "scripts/deploy.sh",
                "required_env": ["CI", "DEPLOY_ENV", "STAGING_HOST", "DEPLOY_KEY", "ARTIFACT_PATH"],
                "artifacts_produced": [],
                "depends_on": ["build"],
            },
            {
                "name": "integration-test",
                "description": "Run integration tests against staging",
                "script": "scripts/integration_test.sh",
                "required_env": ["CI", "STAGING_HOST", "INTEGRATION_TEST_TIMEOUT"],
                "artifacts_produced": ["reports/integration-results.xml"],
                "depends_on": ["deploy-staging"],
            },
            {
                "name": "deploy-prod",
                "description": "Deploy to production environment",
                "script": "scripts/deploy.sh",
                "required_env": ["CI", "DEPLOY_ENV", "PROD_HOST", "DEPLOY_KEY", "ARTIFACT_PATH", "PROD_APPROVAL_TOKEN"],
                "artifacts_produced": [],
                "depends_on": ["integration-test"],
            },
        ],
        "env_defaults": {
            "CI": "true",
            "LINT_CONFIG": ".flake8",
            "TEST_DB_URL": "postgresql://localhost:5432/test_db",
            "TEST_REPORT_DIR": "reports/",
            "BUILD_VERSION": "1.0.0",
            "BUILD_OUTPUT_DIR": "dist/",
            "DEPLOY_ENV": "staging",
            "STAGING_HOST": "staging.webapp.internal",
            "PROD_HOST": "prod.webapp.internal",
            "DEPLOY_KEY": "${DEPLOY_SSH_KEY}",
            "ARTIFACT_PATH": "dist/webapp-release.tar.gz",
            "INTEGRATION_TEST_TIMEOUT": "300",
            "PROD_APPROVAL_TOKEN": "${APPROVAL_TOKEN}",
        },
    },
    {
        "name": "data-service",
        "display": "Data Processing Service",
        "app_name": "dataservice",
        "build_output": "build/",
        "artifact_name": "dataservice-bundle.zip",
        "test_command": "pytest tests/ -m unit",
        "lint_command": "pylint src/",
        "build_command": "python -m build --outdir build/",
        "stages": [
            {
                "name": "lint",
                "description": "Static analysis and style checks",
                "script": "scripts/lint.sh",
                "required_env": ["CI", "PYLINT_THRESHOLD"],
                "artifacts_produced": [],
                "depends_on": [],
            },
            {
                "name": "test",
                "description": "Unit tests with coverage enforcement",
                "script": "scripts/test.sh",
                "required_env": ["CI", "TEST_DB_URL", "COVERAGE_THRESHOLD"],
                "artifacts_produced": ["reports/coverage.xml", "reports/test-results.xml"],
                "depends_on": ["lint"],
            },
            {
                "name": "build",
                "description": "Package service artifacts",
                "script": "scripts/build.sh",
                "required_env": ["CI", "BUILD_VERSION", "BUILD_OUTPUT_DIR", "REGISTRY_URL"],
                "artifacts_produced": ["build/dataservice-bundle.zip"],
                "depends_on": ["test"],
            },
            {
                "name": "deploy-staging",
                "description": "Deploy bundle to staging cluster",
                "script": "scripts/deploy.sh",
                "required_env": ["CI", "DEPLOY_ENV", "STAGING_CLUSTER", "DEPLOY_TOKEN", "ARTIFACT_PATH"],
                "artifacts_produced": [],
                "depends_on": ["build"],
            },
            {
                "name": "integration-test",
                "description": "End-to-end pipeline validation on staging",
                "script": "scripts/integration_test.sh",
                "required_env": ["CI", "STAGING_CLUSTER", "E2E_DATASET_PATH", "INTEGRATION_TEST_TIMEOUT"],
                "artifacts_produced": ["reports/e2e-results.xml"],
                "depends_on": ["deploy-staging"],
            },
            {
                "name": "deploy-prod",
                "description": "Promote artifact to production cluster",
                "script": "scripts/deploy.sh",
                "required_env": ["CI", "DEPLOY_ENV", "PROD_CLUSTER", "DEPLOY_TOKEN", "ARTIFACT_PATH", "PROD_APPROVAL_TOKEN"],
                "artifacts_produced": [],
                "depends_on": ["integration-test"],
            },
        ],
        "env_defaults": {
            "CI": "true",
            "PYLINT_THRESHOLD": "8.0",
            "TEST_DB_URL": "postgresql://localhost:5432/data_test",
            "COVERAGE_THRESHOLD": "80",
            "BUILD_VERSION": "2.1.0",
            "BUILD_OUTPUT_DIR": "build/",
            "REGISTRY_URL": "registry.data.internal",
            "DEPLOY_ENV": "staging",
            "STAGING_CLUSTER": "k8s-staging.data.internal",
            "PROD_CLUSTER": "k8s-prod.data.internal",
            "DEPLOY_TOKEN": "${K8S_DEPLOY_TOKEN}",
            "ARTIFACT_PATH": "build/dataservice-bundle.zip",
            "E2E_DATASET_PATH": "testdata/e2e-fixtures/",
            "INTEGRATION_TEST_TIMEOUT": "600",
            "PROD_APPROVAL_TOKEN": "${APPROVAL_TOKEN}",
        },
    },
    {
        "name": "ml-service",
        "display": "ML Model Service",
        "app_name": "mlservice",
        "build_output": "artifacts/",
        "artifact_name": "model-package.tar.gz",
        "test_command": "pytest tests/ --tb=short",
        "lint_command": "black --check src/ && isort --check src/",
        "build_command": "python scripts/package_model.py --output artifacts/",
        "stages": [
            {
                "name": "lint",
                "description": "Format and import order checks",
                "script": "scripts/lint.sh",
                "required_env": ["CI", "PYTHON_VERSION"],
                "artifacts_produced": [],
                "depends_on": [],
            },
            {
                "name": "test",
                "description": "Model unit tests and regression checks",
                "script": "scripts/test.sh",
                "required_env": ["CI", "MODEL_TEST_DATA", "GPU_ENABLED", "TEST_REPORT_DIR"],
                "artifacts_produced": ["reports/test-results.xml", "reports/model-metrics.json"],
                "depends_on": ["lint"],
            },
            {
                "name": "build",
                "description": "Package model and dependencies",
                "script": "scripts/build.sh",
                "required_env": ["CI", "MODEL_VERSION", "BUILD_OUTPUT_DIR", "MODEL_REGISTRY_URL"],
                "artifacts_produced": ["artifacts/model-package.tar.gz"],
                "depends_on": ["test"],
            },
            {
                "name": "deploy-staging",
                "description": "Deploy model to staging inference endpoint",
                "script": "scripts/deploy.sh",
                "required_env": ["CI", "DEPLOY_ENV", "STAGING_ENDPOINT", "DEPLOY_API_KEY", "ARTIFACT_PATH"],
                "artifacts_produced": [],
                "depends_on": ["build"],
            },
            {
                "name": "integration-test",
                "description": "Inference validation on staging endpoint",
                "script": "scripts/integration_test.sh",
                "required_env": ["CI", "STAGING_ENDPOINT", "VALIDATION_DATASET", "ACCURACY_THRESHOLD"],
                "artifacts_produced": ["reports/validation-results.json"],
                "depends_on": ["deploy-staging"],
            },
            {
                "name": "deploy-prod",
                "description": "Promote model to production inference endpoint",
                "script": "scripts/deploy.sh",
                "required_env": ["CI", "DEPLOY_ENV", "PROD_ENDPOINT", "DEPLOY_API_KEY", "ARTIFACT_PATH", "PROD_APPROVAL_TOKEN"],
                "artifacts_produced": [],
                "depends_on": ["integration-test"],
            },
        ],
        "env_defaults": {
            "CI": "true",
            "PYTHON_VERSION": "3.11",
            "MODEL_TEST_DATA": "testdata/fixtures/",
            "GPU_ENABLED": "false",
            "TEST_REPORT_DIR": "reports/",
            "MODEL_VERSION": "v3.2.1",
            "BUILD_OUTPUT_DIR": "artifacts/",
            "MODEL_REGISTRY_URL": "registry.ml.internal",
            "DEPLOY_ENV": "staging",
            "STAGING_ENDPOINT": "https://staging-inference.ml.internal",
            "PROD_ENDPOINT": "https://inference.ml.internal",
            "DEPLOY_API_KEY": "${ML_DEPLOY_KEY}",
            "ARTIFACT_PATH": "artifacts/model-package.tar.gz",
            "VALIDATION_DATASET": "testdata/validation/",
            "ACCURACY_THRESHOLD": "0.95",
            "PROD_APPROVAL_TOKEN": "${APPROVAL_TOKEN}",
        },
    },
    {
        "name": "mobile-backend",
        "display": "Mobile API Backend",
        "app_name": "mobileapi",
        "build_output": "target/",
        "artifact_name": "mobileapi-server.jar",
        "test_command": "mvn test",
        "lint_command": "checkstyle -c checkstyle.xml src/",
        "build_command": "mvn package -DskipTests --batch-mode",
        "stages": [
            {
                "name": "lint",
                "description": "Checkstyle and static analysis",
                "script": "scripts/lint.sh",
                "required_env": ["CI", "JAVA_VERSION", "CHECKSTYLE_CONFIG"],
                "artifacts_produced": [],
                "depends_on": [],
            },
            {
                "name": "test",
                "description": "JUnit tests and coverage report",
                "script": "scripts/test.sh",
                "required_env": ["CI", "JAVA_VERSION", "TEST_DB_URL", "REDIS_URL"],
                "artifacts_produced": ["target/surefire-reports/", "target/site/jacoco/"],
                "depends_on": ["lint"],
            },
            {
                "name": "build",
                "description": "Maven package build",
                "script": "scripts/build.sh",
                "required_env": ["CI", "JAVA_VERSION", "BUILD_VERSION", "MAVEN_OPTS"],
                "artifacts_produced": ["target/mobileapi-server.jar"],
                "depends_on": ["test"],
            },
            {
                "name": "deploy-staging",
                "description": "Deploy JAR to staging app server",
                "script": "scripts/deploy.sh",
                "required_env": ["CI", "DEPLOY_ENV", "STAGING_HOST", "STAGING_PORT", "DEPLOY_USER", "ARTIFACT_PATH"],
                "artifacts_produced": [],
                "depends_on": ["build"],
            },
            {
                "name": "integration-test",
                "description": "API smoke tests against staging",
                "script": "scripts/integration_test.sh",
                "required_env": ["CI", "STAGING_HOST", "STAGING_PORT", "API_TEST_SUITE", "INTEGRATION_TEST_TIMEOUT"],
                "artifacts_produced": ["reports/api-test-results.xml"],
                "depends_on": ["deploy-staging"],
            },
            {
                "name": "deploy-prod",
                "description": "Blue-green deploy to production",
                "script": "scripts/deploy.sh",
                "required_env": ["CI", "DEPLOY_ENV", "PROD_HOST", "STAGING_PORT", "DEPLOY_USER", "ARTIFACT_PATH", "PROD_APPROVAL_TOKEN"],
                "artifacts_produced": [],
                "depends_on": ["integration-test"],
            },
        ],
        "env_defaults": {
            "CI": "true",
            "JAVA_VERSION": "17",
            "CHECKSTYLE_CONFIG": "checkstyle.xml",
            "TEST_DB_URL": "jdbc:postgresql://localhost:5432/test",
            "REDIS_URL": "redis://localhost:6379",
            "BUILD_VERSION": "4.0.2",
            "MAVEN_OPTS": "-Xmx2g",
            "DEPLOY_ENV": "staging",
            "STAGING_HOST": "staging.mobileapi.internal",
            "PROD_HOST": "prod.mobileapi.internal",
            "STAGING_PORT": "8080",
            "DEPLOY_USER": "deploy",
            "ARTIFACT_PATH": "target/mobileapi-server.jar",
            "API_TEST_SUITE": "tests/api/smoke_suite.yaml",
            "INTEGRATION_TEST_TIMEOUT": "180",
            "PROD_APPROVAL_TOKEN": "${APPROVAL_TOKEN}",
        },
    },
]

# ── Bug definitions ────────────────────────────────────────────────────────────

BUG_TYPES = [
    "wrong_order",       # stages shuffled / wrong sequence
    "missing_env_var",   # required env var absent from a stage
    "wrong_artifact_path",  # artifact path references wrong file/directory
    "missing_stage",     # entire stage omitted from pipeline
]

# ── Script templates ───────────────────────────────────────────────────────────

def _make_lint_sh(project: dict, broken: bool = False) -> str:
    app_name = project["app_name"]
    lint_cmd = project["lint_command"]
    if broken:
        # BUG: uses wrong config path and exits without proper error code handling
        return f'''#!/usr/bin/env bash
# lint.sh — Run linting checks for {project["display"]}
# STATUS: BROKEN — wrong config path, missing error propagation
set -e

echo "[lint] Starting linting for {app_name}..."

# BUG: LINT_CONFIG env var not checked
# BUG: wrong config file path
{lint_cmd.replace("$LINT_CONFIG", ".config/linting-wrong.cfg").replace("checkstyle.xml", "wrong-checkstyle.xml")}

echo "[lint] Done."
'''
    else:
        return f'''#!/usr/bin/env bash
# lint.sh — Run linting checks for {project["display"]}
set -euo pipefail

echo "[lint] Starting linting for {app_name}..."

if [ -z "${{LINT_CONFIG:-}}" ] && [ -z "${{CHECKSTYLE_CONFIG:-}}" ] && [ -z "${{PYTHON_VERSION:-}}" ]; then
    echo "ERROR: No lint configuration env var set" >&2
    exit 1
fi

{lint_cmd}

echo "[lint] Linting passed."
'''


def _make_test_sh(project: dict, broken: bool = False) -> str:
    app_name = project["app_name"]
    test_cmd = project["test_command"]
    if broken:
        # BUG: skips test execution, writes to wrong report dir, ignores TEST_DB_URL
        return f'''#!/usr/bin/env bash
# test.sh — Run tests for {project["display"]}
# STATUS: BROKEN — skips actual tests, writes reports to wrong path
set -e

echo "[test] Starting tests for {app_name}..."

# BUG: TEST_DB_URL not exported, tests will use wrong database
# BUG: reports written to wrong directory
mkdir -p test-output/  # wrong: should be $TEST_REPORT_DIR or reports/

# BUG: --skip-slow flag causes many tests to be skipped
{test_cmd} --co -q  # only collects, does not run

echo "[test] Done."
'''
    else:
        return f'''#!/usr/bin/env bash
# test.sh — Run tests for {project["display"]}
set -euo pipefail

echo "[test] Starting tests for {app_name}..."

REPORT_DIR="${{TEST_REPORT_DIR:-reports/}}"
mkdir -p "$REPORT_DIR"

export TEST_DB_URL="${{TEST_DB_URL}}"

{test_cmd}

echo "[test] All tests passed. Reports in $REPORT_DIR"
'''


def _make_build_sh(project: dict, broken: bool = False) -> str:
    app_name = project["app_name"]
    build_cmd = project["build_command"]
    artifact = project["artifact_name"]
    build_output = project["build_output"]
    if broken:
        # BUG: output directory wrong, version not stamped, artifact path incorrect
        return f'''#!/usr/bin/env bash
# build.sh — Build {project["display"]} artifact
# STATUS: BROKEN — wrong output directory, missing version stamp
set -e

echo "[build] Building {app_name}..."

# BUG: BUILD_OUTPUT_DIR ignored, hardcoded to wrong dir
mkdir -p output/  # wrong: should be ${{BUILD_OUTPUT_DIR}}

# BUG: build_version not injected
{build_cmd.replace("--outdir build/", "--outdir output/").replace("--dist-dir dist/", "--dist-dir output/").replace("--output artifacts/", "--output output/")}

# BUG: artifact ends up in wrong path
echo "[build] Build complete. Artifact: output/{artifact}"
'''
    else:
        return f'''#!/usr/bin/env bash
# build.sh — Build {project["display"]} artifact
set -euo pipefail

echo "[build] Building {app_name} version ${{BUILD_VERSION}}..."

OUTPUT_DIR="${{BUILD_OUTPUT_DIR:-{build_output}}}"
mkdir -p "$OUTPUT_DIR"

{build_cmd}

if [ ! -f "${{ARTIFACT_PATH:-$OUTPUT_DIR{artifact}}}" ]; then
    echo "ERROR: Artifact not found after build" >&2
    exit 1
fi

echo "[build] Build complete. Artifact: ${{BUILD_OUTPUT_DIR}}{artifact}"
'''


def _make_deploy_sh(project: dict, broken: bool = False) -> str:
    app_name = project["app_name"]
    if broken:
        # BUG: DEPLOY_ENV check missing, artifact path hardcoded wrong, no staging/prod distinction
        return f'''#!/usr/bin/env bash
# deploy.sh — Deploy {project["display"]}
# STATUS: BROKEN — missing DEPLOY_ENV check, wrong artifact path, no prod safeguards
set -e

echo "[deploy] Deploying {app_name}..."

# BUG: DEPLOY_ENV not validated
# BUG: ARTIFACT_PATH not used — hardcoded wrong path
ARTIFACT="artifacts/wrong-package.zip"  # wrong path

if [ ! -f "$ARTIFACT" ]; then
    echo "WARNING: artifact not found, deploying anyway"  # BUG: should be fatal
fi

# BUG: PROD_APPROVAL_TOKEN never checked for production deploys
echo "[deploy] Deployed to ${{DEPLOY_ENV:-unknown}}."
'''
    else:
        return f'''#!/usr/bin/env bash
# deploy.sh — Deploy {project["display"]}
set -euo pipefail

echo "[deploy] Deploying {app_name} to ${{DEPLOY_ENV}}..."

# Validate artifact exists
if [ ! -f "${{ARTIFACT_PATH}}" ]; then
    echo "ERROR: Artifact not found at ${{ARTIFACT_PATH}}" >&2
    exit 1
fi

# Production gate: require approval token
if [ "${{DEPLOY_ENV}}" = "prod" ]; then
    if [ -z "${{PROD_APPROVAL_TOKEN:-}}" ]; then
        echo "ERROR: PROD_APPROVAL_TOKEN required for production deploy" >&2
        exit 1
    fi
fi

echo "[deploy] Artifact: ${{ARTIFACT_PATH}}"
echo "[deploy] Deploy environment: ${{DEPLOY_ENV}}"
echo "[deploy] Deploy complete."
'''


def _make_integration_test_sh(project: dict, broken: bool = False) -> str:
    app_name = project["app_name"]
    if broken:
        # BUG: timeout not respected, wrong host used, results dir wrong
        return f'''#!/usr/bin/env bash
# integration_test.sh — Integration tests for {project["display"]}
# STATUS: BROKEN — ignores timeout, uses wrong host, results in wrong dir
set -e

echo "[integration-test] Running integration tests for {app_name}..."

# BUG: STAGING_HOST / STAGING_ENDPOINT / STAGING_CLUSTER not used
TARGET="localhost:8080"  # hardcoded wrong

# BUG: INTEGRATION_TEST_TIMEOUT ignored
# BUG: results written to wrong directory
mkdir -p test-output/

echo "[integration-test] Tests passed (fake)."
'''
    else:
        return f'''#!/usr/bin/env bash
# integration_test.sh — Integration tests for {project["display"]}
set -euo pipefail

echo "[integration-test] Running integration tests for {app_name}..."

TIMEOUT="${{INTEGRATION_TEST_TIMEOUT:-300}}"
REPORT_DIR="reports/"
mkdir -p "$REPORT_DIR"

# Use whichever host variable is set (varies by project type)
TARGET="${{STAGING_ENDPOINT:-${{STAGING_HOST:-${{STAGING_CLUSTER:-localhost}}}}}}"
echo "[integration-test] Target: $TARGET (timeout: ${{TIMEOUT}}s)"

# Run with timeout
timeout "$TIMEOUT" bash -c "
    echo 'Running integration tests against $TARGET...'
    echo 'All integration checks passed.'
"

echo "[integration-test] Integration tests passed. Results in $REPORT_DIR"
'''


class Generator(TaskGenerator):
    task_id = "PIPE4_ci_cd"
    domain = "pipeline"
    difficulty = "medium"
    languages = ["bash", "python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)

        # Select project deterministically from seed
        project = PROJECTS[seed % len(PROJECTS)]
        stages = project["stages"]
        env_defaults = project["env_defaults"]

        # ── Decide which bugs to inject ──────────────────────────────────────
        # Always inject 2-3 bug types from the 4 available, deterministically
        num_bugs = rng.randint(2, 3)
        bug_types_to_inject = rng.sample(BUG_TYPES, num_bugs)
        bug_manifest = {}

        # Build correct pipeline config (before bugs)
        correct_pipeline = {
            "version": "1.0",
            "project": project["name"],
            "stages": [
                {
                    "name": s["name"],
                    "description": s["description"],
                    "script": s["script"],
                    "env": {k: env_defaults[k] for k in s["required_env"] if k in env_defaults},
                    "artifacts": s["artifacts_produced"],
                    "depends_on": s["depends_on"],
                }
                for s in stages
            ],
        }

        # ── Apply bugs to produce broken pipeline ────────────────────────────
        broken_stages = [
            {
                "name": s["name"],
                "description": s["description"],
                "script": s["script"],
                "env": {k: env_defaults[k] for k in s["required_env"] if k in env_defaults},
                "artifacts": s["artifacts_produced"],
                "depends_on": s["depends_on"],
            }
            for s in stages
        ]

        if "wrong_order" in bug_types_to_inject:
            # Swap two middle stages to break pipeline order
            # Swap test and build (indices 1 and 2)
            broken_stages[1], broken_stages[2] = broken_stages[2], broken_stages[1]
            bug_manifest["wrong_order"] = {
                "description": "Stages 'test' and 'build' are swapped — build runs before test",
                "correct_order": [s["name"] for s in stages],
                "injected_order": [s["name"] for s in broken_stages],
            }

        if "missing_env_var" in bug_types_to_inject:
            # Remove a critical env var from the build stage
            build_stage_idx = next(i for i, s in enumerate(broken_stages) if s["name"] == "build")
            build_stage = broken_stages[build_stage_idx]
            # Find a required env var that is present and remove it
            removable = [k for k in build_stage["env"].keys() if k != "CI"]
            if removable:
                removed_key = rng.choice(removable)
                del build_stage["env"][removed_key]
                bug_manifest["missing_env_var"] = {
                    "stage": "build",
                    "missing_key": removed_key,
                    "correct_value": env_defaults.get(removed_key, ""),
                    "description": f"Required env var '{removed_key}' is missing from the 'build' stage",
                }

        if "wrong_artifact_path" in bug_types_to_inject:
            # Inject wrong artifact path into deploy-staging stage env
            deploy_staging_idx = next(
                (i for i, s in enumerate(broken_stages) if s["name"] == "deploy-staging"), None
            )
            if deploy_staging_idx is not None:
                correct_path = env_defaults.get("ARTIFACT_PATH", "dist/artifact.tar.gz")
                wrong_path = correct_path.replace(project["build_output"], "output/wrong/")
                broken_stages[deploy_staging_idx]["env"]["ARTIFACT_PATH"] = wrong_path
                bug_manifest["wrong_artifact_path"] = {
                    "stage": "deploy-staging",
                    "field": "ARTIFACT_PATH",
                    "correct": correct_path,
                    "injected": wrong_path,
                    "description": f"ARTIFACT_PATH points to wrong location '{wrong_path}' instead of '{correct_path}'",
                }

        if "missing_stage" in bug_types_to_inject:
            # Remove the integration-test stage entirely
            integration_idx = next(
                (i for i, s in enumerate(broken_stages) if s["name"] == "integration-test"), None
            )
            if integration_idx is not None:
                removed_stage = broken_stages.pop(integration_idx)
                bug_manifest["missing_stage"] = {
                    "missing_stage_name": "integration-test",
                    "description": "The 'integration-test' stage is entirely missing from the pipeline",
                    "correct_stage": removed_stage,
                }

        broken_pipeline = {
            "version": "1.0",
            "project": project["name"],
            "stages": broken_stages,
        }

        # ── Build expected dict for grader ───────────────────────────────────
        expected = {
            "project": project["name"],
            "correct_stage_order": [s["name"] for s in stages],
            "correct_pipeline": correct_pipeline,
            "bug_manifest": bug_manifest,
            "required_stages": [s["name"] for s in stages],
            "stage_env_requirements": {
                s["name"]: s["required_env"] for s in stages
            },
            "stage_artifacts": {
                s["name"]: s["artifacts_produced"] for s in stages
            },
            "artifact_path": env_defaults.get("ARTIFACT_PATH", ""),
        }

        # ── Build workspace files ────────────────────────────────────────────
        workspace_files: dict[str, str] = {}

        # pipeline.json — intentionally broken
        workspace_files["pipeline.json"] = json.dumps(broken_pipeline, indent=2)

        # scripts/ — all scripts, some broken
        scripts_broken = {
            "lint": "missing_env_var" not in bug_types_to_inject,  # lint.sh only broken when env bug elsewhere
            "test": "wrong_order" in bug_types_to_inject,          # test.sh broken when order bug
            "build": "missing_env_var" in bug_types_to_inject or "wrong_artifact_path" in bug_types_to_inject,
            "deploy": "wrong_artifact_path" in bug_types_to_inject,
            "integration_test": "missing_stage" in bug_types_to_inject,
        }

        workspace_files["scripts/lint.sh"] = _make_lint_sh(project, broken=False)
        workspace_files["scripts/test.sh"] = _make_test_sh(project, broken=scripts_broken["test"])
        workspace_files["scripts/build.sh"] = _make_build_sh(project, broken=scripts_broken["build"])
        workspace_files["scripts/deploy.sh"] = _make_deploy_sh(project, broken=scripts_broken["deploy"])
        workspace_files["scripts/integration_test.sh"] = _make_integration_test_sh(
            project, broken=scripts_broken["integration_test"]
        )

        # .env.example — complete env var reference
        workspace_files[".env.example"] = self._generate_env_example(project, env_defaults)

        # pipeline_runner.py — reads pipeline.json and validates/executes stages
        workspace_files["pipeline_runner.py"] = self._generate_runner(project)

        # validate_pipeline.py — standalone validator
        workspace_files["validate_pipeline.py"] = self._generate_validator()

        # spec and brief
        spec_md = self._generate_spec(project, stages, env_defaults, bug_manifest)
        brief_md = self._generate_brief(project)

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # ── File generators ────────────────────────────────────────────────────────

    def _generate_env_example(self, project: dict, env_defaults: dict) -> str:
        lines = [
            f"# Environment variables for {project['display']} CI/CD pipeline",
            f"# Copy to .env and fill in real values before running.",
            "",
        ]
        for key, val in env_defaults.items():
            lines.append(f"{key}={val}")
        return "\n".join(lines) + "\n"

    def _generate_runner(self, project: dict) -> str:
        return f'''\
"""
Pipeline runner for {project["display"]}.

Reads pipeline.json and executes each stage in order, validating:
- Stage order matches depends_on constraints
- All required env vars are set before each stage script runs
- Artifacts are present after stages that produce them

Fix pipeline.json (and scripts/) so this runner completes successfully.
Do NOT modify this file.
"""
import json
import os
import subprocess
import sys


PIPELINE_FILE = os.path.join(os.path.dirname(__file__), "pipeline.json")


def load_pipeline(path: str = PIPELINE_FILE) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_stage_order(stages: list[dict]) -> list[str]:
    """Return list of order violation errors."""
    errors = []
    seen = set()
    for stage in stages:
        for dep in stage.get("depends_on", []):
            if dep not in seen:
                errors.append(
                    f"Stage '{{stage['name']}}' depends on '{{dep}}' "
                    f"but '{{dep}}' has not run yet (check stage order)"
                )
        seen.add(stage["name"])
    return errors


def validate_env(stage: dict) -> list[str]:
    """Return list of missing env var errors for a stage."""
    errors = []
    for key, val in stage.get("env", {{}}).items():
        if val.startswith("${{") and val.endswith("}}"):
            # Template variable — skip (injected at runtime)
            continue
        os.environ.setdefault(key, val)
    return errors


def run_stage(stage: dict, dry_run: bool = False) -> bool:
    """Run a stage script. Returns True on success."""
    script = stage["script"]
    env = {{**os.environ}}
    for key, val in stage.get("env", {{}}).items():
        if not (val.startswith("${{") and val.endswith("}}")):
            env[key] = val

    print(f"[runner] Stage: {{stage['name']}} -> {{script}}")
    if dry_run:
        print(f"[runner] DRY RUN: would execute {{script}}")
        return True

    if not os.path.isfile(script):
        print(f"[runner] ERROR: script not found: {{script}}", file=sys.stderr)
        return False

    result = subprocess.run(
        ["bash", script],
        env=env,
        capture_output=False,
    )
    return result.returncode == 0


def run_pipeline(dry_run: bool = False) -> int:
    pipeline = load_pipeline()
    stages = pipeline.get("stages", [])

    print(f"[runner] Pipeline: {{pipeline.get('project', 'unknown')}}")
    print(f"[runner] Stages: {{[s['name'] for s in stages]}}")

    # Validate order
    order_errors = validate_stage_order(stages)
    if order_errors:
        for err in order_errors:
            print(f"[runner] ORDER ERROR: {{err}}", file=sys.stderr)
        return 1

    # Execute stages
    for stage in stages:
        validate_env(stage)
        ok = run_stage(stage, dry_run=dry_run)
        if not ok:
            print(f"[runner] FAILED at stage: {{stage['name']}}", file=sys.stderr)
            return 1

    print("[runner] Pipeline completed successfully.")
    return 0


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv
    sys.exit(run_pipeline(dry_run=dry_run))
'''

    def _generate_validator(self) -> str:
        return '''\
"""
Standalone pipeline validator.

Checks pipeline.json for structural correctness:
- All required stages present in correct order
- All stage env vars set
- Artifact paths are consistent
- No circular dependencies

Run with: python validate_pipeline.py
Fix pipeline.json until this validator reports no errors.
"""
import json
import os
import sys

REQUIRED_STAGES = [
    "lint",
    "test",
    "build",
    "deploy-staging",
    "integration-test",
    "deploy-prod",
]

REQUIRED_ORDER = {
    "test": "lint",
    "build": "test",
    "deploy-staging": "build",
    "integration-test": "deploy-staging",
    "deploy-prod": "integration-test",
}


def validate(pipeline_path: str = "pipeline.json") -> list[str]:
    errors = []

    try:
        with open(pipeline_path, "r", encoding="utf-8") as f:
            pipeline = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        return [f"Cannot load pipeline.json: {e}"]

    stages = pipeline.get("stages", [])
    stage_names = [s["name"] for s in stages]

    # Check all required stages present
    for req in REQUIRED_STAGES:
        if req not in stage_names:
            errors.append(f"Missing required stage: '{req}'")

    # Check stage order
    for stage, must_follow in REQUIRED_ORDER.items():
        if stage in stage_names and must_follow in stage_names:
            idx_stage = stage_names.index(stage)
            idx_dep = stage_names.index(must_follow)
            if idx_stage <= idx_dep:
                errors.append(
                    f"Stage '{stage}' must come after '{must_follow}' "
                    f"(currently: {must_follow}=#{idx_dep+1}, {stage}=#{idx_stage+1})"
                )

    # Check each stage has non-empty env
    for stage in stages:
        if not stage.get("env"):
            errors.append(f"Stage '{stage['name']}' has no env vars configured")
        if not stage.get("script"):
            errors.append(f"Stage '{stage['name']}' has no script configured")

    # Check ARTIFACT_PATH consistency
    artifact_paths = set()
    for stage in stages:
        ap = stage.get("env", {}).get("ARTIFACT_PATH")
        if ap:
            artifact_paths.add(ap)
    if len(artifact_paths) > 1:
        errors.append(
            f"Inconsistent ARTIFACT_PATH across stages: {sorted(artifact_paths)}"
        )

    return errors


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "pipeline.json"
    errors = validate(path)
    if errors:
        print(f"Pipeline validation FAILED ({len(errors)} error(s)):")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)
    else:
        print("Pipeline validation PASSED.")
        sys.exit(0)
'''

    def _generate_spec(
        self,
        project: dict,
        stages: list[dict],
        env_defaults: dict,
        bug_manifest: dict,
    ) -> str:
        """Full spec for Planner — contains complete pipeline requirements."""

        # Stage table
        stage_rows = "\n".join(
            f"| `{s['name']}` | {s['description']} | `{s['script']}` | "
            f"{', '.join(f'`{d}`' for d in s['depends_on']) or '—'} |"
            for s in stages
        )

        # Env vars per stage
        env_sections = ""
        for s in stages:
            env_rows = "\n".join(
                f"| `{k}` | `{env_defaults.get(k, '')}` |"
                for k in s["required_env"]
            )
            artifacts_str = (
                ", ".join(f"`{a}`" for a in s["artifacts_produced"])
                if s["artifacts_produced"] else "_(none)_"
            )
            env_sections += f"""
### Stage: `{s['name']}`

**Description**: {s['description']}
**Script**: `{s['script']}`
**Depends on**: {', '.join(f'`{d}`' for d in s['depends_on']) or '_(none — first stage)_'}
**Artifacts produced**: {artifacts_str}

**Required environment variables**:
| Variable | Required Value / Description |
|---|---|
{env_rows}
"""

        # Bug summary
        bug_lines = []
        for bug_type, info in bug_manifest.items():
            bug_lines.append(f"- **{bug_type}**: {info['description']}")
        bug_section = "\n".join(bug_lines) if bug_lines else "_(none)_"

        # Order constraint summary
        order_desc = "\n".join(
            f"{i+1}. `{s['name']}`"
            for i, s in enumerate(stages)
        )

        return f"""# PIPE4: CI/CD Pipeline Fix — Planner Specification

## Project
**{project['display']}** (`{project['name']}`)

## Situation

The CI/CD pipeline configuration (`pipeline.json`) and associated scripts contain
deliberate errors. The Executor can see the broken files but does NOT know the
correct stage order, required environment variables, or artifact paths.

Your job as Planner is to relay the complete correct pipeline specification
so the Executor can fix `pipeline.json` and the scripts in `scripts/`.

---

## Required Pipeline Stage Order

The pipeline MUST execute stages in exactly this order:

{order_desc}

This order is mandatory — each stage depends on the previous completing successfully.

---

## Stage Definitions

| Stage | Description | Script | Depends On |
|---|---|---|---|
{stage_rows}

---

## Full Stage Specifications (with Environment Variables)
{env_sections}
---

## Artifact Path

The build artifact is produced by the `build` stage and must be referenced
consistently in all downstream stages:

**Artifact path**: `{env_defaults.get('ARTIFACT_PATH', 'dist/artifact.tar.gz')}`

This exact path must appear in `ARTIFACT_PATH` for both `deploy-staging` and
`deploy-prod` stages.

---

## Script Requirements

Each script in `scripts/` must:

1. **lint.sh**: Run the linter using the `LINT_CONFIG` (or equivalent) env var.
   Must exit non-zero on lint failure.
2. **test.sh**: Export `TEST_DB_URL`, run the full test suite (not `--collect-only`).
   Write results to `$TEST_REPORT_DIR`. Must exit non-zero on test failure.
3. **build.sh**: Use `$BUILD_OUTPUT_DIR` as output directory (not a hardcoded path).
   Verify artifact exists after build. Must exit non-zero if artifact missing.
4. **deploy.sh**: Read artifact from `$ARTIFACT_PATH` (must exist).
   For `DEPLOY_ENV=prod`, require `$PROD_APPROVAL_TOKEN` to be non-empty.
   Must exit non-zero if artifact missing or token absent for prod.
5. **integration_test.sh**: Use the staging host env var (project-specific).
   Respect `$INTEGRATION_TEST_TIMEOUT`. Write results to `reports/`.

---

## Bugs Injected

The following errors are present in `pipeline.json` and/or `scripts/` and must be corrected:

{bug_section}

---

## Deliverables

The Executor must fix `pipeline.json` (and any broken `scripts/`) so that:

1. All 6 required stages are present: lint, test, build, deploy-staging, integration-test, deploy-prod
2. Stages appear in the correct order with correct `depends_on` values
3. Each stage has all required env vars set with correct values
4. `ARTIFACT_PATH` is consistent and correct in all stages that reference it
5. `python validate_pipeline.py` reports no errors
6. `python pipeline_runner.py --dry-run` completes without errors
7. Each script in `scripts/` correctly implements its stage requirements

**Do not modify `pipeline_runner.py` or `validate_pipeline.py`.**
"""

    def _generate_brief(self, project: dict) -> str:
        """Brief for Executor — vague description without the full spec."""
        return f"""# PIPE4: CI/CD Pipeline Fix (Brief)

## Situation

The CI/CD pipeline for **{project['display']}** is failing. Builds aren't completing
successfully and deployments are not reaching production.

**The Planner has the complete pipeline specification.** Coordinate with the Planner
to understand the correct stage order, required environment variables, artifact paths,
and script requirements.

## What You Have

- `pipeline.json` — the pipeline configuration (has errors)
- `scripts/` — pipeline stage scripts (some may have bugs):
  - `scripts/lint.sh`
  - `scripts/test.sh`
  - `scripts/build.sh`
  - `scripts/deploy.sh`
  - `scripts/integration_test.sh`
- `.env.example` — environment variable reference
- `pipeline_runner.py` — pipeline executor (do NOT modify)
- `validate_pipeline.py` — pipeline validator (do NOT modify)

## What's Wrong

The pipeline has one or more of these issues:
- Stages may be in the wrong order
- Required environment variables may be missing from some stages
- Artifact paths may reference the wrong location
- A required stage may be entirely missing

## What You Must Produce

Fix `pipeline.json` and any broken scripts so that:
1. `python validate_pipeline.py` reports no errors
2. `python pipeline_runner.py --dry-run` completes without errors
3. All 6 pipeline stages are present and in the correct order
4. All stages have the correct environment variables
5. The artifact path is consistent and correct

**Do not modify `pipeline_runner.py` or `validate_pipeline.py`.**
Ask the Planner for the complete pipeline specification.
"""
