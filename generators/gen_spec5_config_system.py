"""
Parameterized generator for SPEC5: Configuration System from Requirements.

TNI Pattern A,C — The spec has the complete config schema (key names, types,
default values, validation rules like "port must be 1024-65535", "log_level
must be one of DEBUG/INFO/WARN/ERROR"), environment override rules, and cascade
priority (CLI args > env vars > config file > defaults). The brief says only
"implement the configuration management system."

Each seed varies:
  - Number of config keys (8-12)
  - Which validation rule types appear (int range, enum, bool, string pattern)
  - Which env var prefix is used
  - Default values
  - Port range, log levels, timeout values

Seed → domain mapping:
  0 mod 4 → web_service      (HTTP server config)
  1 mod 4 → database_client  (DB connection config)
  2 mod 4 → worker_service   (queue/job worker config)
  3 mod 4 → ml_pipeline      (ML training/inference config)

Grader: 12+ checks covering:
  - All config keys loadable
  - Defaults are correct
  - Validation rejects invalid values
  - Env var overrides work
  - Type coercion (string "8080" -> int 8080)
  - Priority cascade (file -> env -> cli)
  - Invalid values rejected with correct error types
  - Config schema accessible at runtime
"""
from __future__ import annotations

import json
import textwrap

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# ---------------------------------------------------------------------------
# Domain list
# ---------------------------------------------------------------------------

DOMAINS = [
    "web_service",
    "database_client",
    "worker_service",
    "ml_pipeline",
]


class Generator(TaskGenerator):
    task_id = "SPEC5_config_system"
    domain = "specification"
    difficulty = "hard"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        domain = DOMAINS[seed % len(DOMAINS)]

        if domain == "web_service":
            return self._gen_web_service(seed, rng)
        elif domain == "database_client":
            return self._gen_database_client(seed, rng)
        elif domain == "worker_service":
            return self._gen_worker_service(seed, rng)
        else:
            return self._gen_ml_pipeline(seed, rng)

    # -----------------------------------------------------------------------
    # Domain 0: Web Service Config
    # -----------------------------------------------------------------------

    def _gen_web_service(self, seed: int, rng: SeededRandom) -> GeneratedTask:
        port = rng.randint(3000, 9000)
        port_min = rng.choice([1024, 2048, 3000])
        port_max = rng.choice([49151, 65535, 32768])
        log_levels = ["DEBUG", "INFO", "WARN", "ERROR"]
        allowed_log_levels = rng.sample(log_levels, rng.randint(2, 4))
        allowed_log_levels = [l for l in log_levels if l in allowed_log_levels]
        default_log_level = rng.choice(["INFO", "WARN"])
        timeout = rng.choice([30, 60, 120, 300])
        max_connections = rng.randint(50, 500)
        max_conn_min = 1
        max_conn_max = rng.choice([1000, 2000, 5000])
        env_prefix = rng.choice(["APP", "WEB", "SVC", "SERVER"])
        num_keys = rng.randint(8, 12)

        # Fixed keys always present
        schema = {
            "host": {
                "type": "string",
                "default": "0.0.0.0",
                "env_var": f"{env_prefix}_HOST",
                "description": "Hostname or IP address to bind",
                "validation": "non-empty string",
            },
            "port": {
                "type": "int",
                "default": port,
                "env_var": f"{env_prefix}_PORT",
                "description": f"TCP port to listen on; must be {port_min}-{port_max}",
                "validation": f"int in range [{port_min}, {port_max}]",
                "min": port_min,
                "max": port_max,
            },
            "log_level": {
                "type": "enum",
                "default": default_log_level,
                "env_var": f"{env_prefix}_LOG_LEVEL",
                "description": f"Logging verbosity; one of {allowed_log_levels}",
                "validation": f"one of {allowed_log_levels}",
                "allowed": allowed_log_levels,
            },
            "request_timeout": {
                "type": "int",
                "default": timeout,
                "env_var": f"{env_prefix}_REQUEST_TIMEOUT",
                "description": f"Request timeout in seconds; must be 1-3600",
                "validation": "int in range [1, 3600]",
                "min": 1,
                "max": 3600,
            },
            "max_connections": {
                "type": "int",
                "default": max_connections,
                "env_var": f"{env_prefix}_MAX_CONNECTIONS",
                "description": f"Maximum concurrent connections; must be {max_conn_min}-{max_conn_max}",
                "validation": f"int in range [{max_conn_min}, {max_conn_max}]",
                "min": max_conn_min,
                "max": max_conn_max,
            },
            "debug_mode": {
                "type": "bool",
                "default": False,
                "env_var": f"{env_prefix}_DEBUG",
                "description": "Enable debug mode",
                "validation": "bool (true/false/1/0/yes/no)",
            },
            "static_dir": {
                "type": "string",
                "default": "./static",
                "env_var": f"{env_prefix}_STATIC_DIR",
                "description": "Path to static files directory",
                "validation": "non-empty string",
            },
            "cors_origins": {
                "type": "string",
                "default": "*",
                "env_var": f"{env_prefix}_CORS_ORIGINS",
                "description": "Allowed CORS origins, comma-separated",
                "validation": "string (any)",
            },
        }

        # Optionally add extra keys based on num_keys
        extra_keys = [
            ("ssl_enabled", {
                "type": "bool",
                "default": False,
                "env_var": f"{env_prefix}_SSL_ENABLED",
                "description": "Enable SSL/TLS",
                "validation": "bool",
            }),
            ("keep_alive_timeout", {
                "type": "int",
                "default": rng.choice([5, 10, 15, 30]),
                "env_var": f"{env_prefix}_KEEP_ALIVE_TIMEOUT",
                "description": "Keep-alive timeout seconds; must be 1-300",
                "validation": "int in range [1, 300]",
                "min": 1,
                "max": 300,
            }),
            ("worker_count", {
                "type": "int",
                "default": rng.choice([2, 4, 8]),
                "env_var": f"{env_prefix}_WORKER_COUNT",
                "description": "Number of worker processes; must be 1-64",
                "validation": "int in range [1, 64]",
                "min": 1,
                "max": 64,
            }),
            ("compress_responses", {
                "type": "bool",
                "default": True,
                "env_var": f"{env_prefix}_COMPRESS",
                "description": "Enable response compression",
                "validation": "bool",
            }),
        ]
        rng.shuffle(extra_keys)
        for key, spec in extra_keys[: max(0, num_keys - len(schema))]:
            schema[key] = spec

        expected = {
            "domain": "web_service",
            "env_prefix": env_prefix,
            "schema": schema,
            "port_min": port_min,
            "port_max": port_max,
            "default_port": port,
            "default_log_level": default_log_level,
            "allowed_log_levels": allowed_log_levels,
            "default_timeout": timeout,
            "default_max_connections": max_connections,
            "max_conn_max": max_conn_max,
        }

        return self._build_task(seed, "web_service", env_prefix, schema, expected)

    # -----------------------------------------------------------------------
    # Domain 1: Database Client Config
    # -----------------------------------------------------------------------

    def _gen_database_client(self, seed: int, rng: SeededRandom) -> GeneratedTask:
        db_port = rng.choice([5432, 3306, 1433, 27017, 6379])
        db_port_name = {5432: "PostgreSQL", 3306: "MySQL", 1433: "MSSQL",
                        27017: "MongoDB", 6379: "Redis"}[db_port]
        pool_min = rng.randint(1, 5)
        pool_max = rng.randint(10, 50)
        conn_timeout = rng.choice([5, 10, 15, 30])
        log_levels = ["DEBUG", "INFO", "WARN", "ERROR"]
        allowed_log_levels = rng.sample(log_levels, rng.randint(2, 4))
        allowed_log_levels = [l for l in log_levels if l in allowed_log_levels]
        default_log_level = rng.choice(["INFO", "WARN"])
        ssl_modes = ["disable", "require", "verify-full"]
        default_ssl_mode = rng.choice(ssl_modes[:2])
        env_prefix = rng.choice(["DB", "DATABASE", "PG", "MONGO"])
        num_keys = rng.randint(8, 12)

        schema = {
            "host": {
                "type": "string",
                "default": "localhost",
                "env_var": f"{env_prefix}_HOST",
                "description": "Database server hostname",
                "validation": "non-empty string",
            },
            "port": {
                "type": "int",
                "default": db_port,
                "env_var": f"{env_prefix}_PORT",
                "description": f"Database port; must be 1024-65535",
                "validation": "int in range [1024, 65535]",
                "min": 1024,
                "max": 65535,
            },
            "database": {
                "type": "string",
                "default": "mydb",
                "env_var": f"{env_prefix}_NAME",
                "description": "Database name to connect to",
                "validation": "non-empty string",
            },
            "username": {
                "type": "string",
                "default": "admin",
                "env_var": f"{env_prefix}_USER",
                "description": "Database username",
                "validation": "non-empty string",
            },
            "password": {
                "type": "string",
                "default": "",
                "env_var": f"{env_prefix}_PASSWORD",
                "description": "Database password (may be empty)",
                "validation": "string (any)",
            },
            "pool_min_size": {
                "type": "int",
                "default": pool_min,
                "env_var": f"{env_prefix}_POOL_MIN",
                "description": f"Min connection pool size; must be 1-{pool_max}",
                "validation": f"int in range [1, {pool_max}]",
                "min": 1,
                "max": pool_max,
            },
            "pool_max_size": {
                "type": "int",
                "default": pool_max,
                "env_var": f"{env_prefix}_POOL_MAX",
                "description": f"Max connection pool size; must be pool_min-100",
                "validation": "int in range [pool_min, 100]",
                "min": pool_min,
                "max": 100,
            },
            "connect_timeout": {
                "type": "int",
                "default": conn_timeout,
                "env_var": f"{env_prefix}_CONNECT_TIMEOUT",
                "description": "Connection timeout in seconds; must be 1-120",
                "validation": "int in range [1, 120]",
                "min": 1,
                "max": 120,
            },
            "ssl_mode": {
                "type": "enum",
                "default": default_ssl_mode,
                "env_var": f"{env_prefix}_SSL_MODE",
                "description": f"SSL mode; one of {ssl_modes}",
                "validation": f"one of {ssl_modes}",
                "allowed": ssl_modes,
            },
            "log_level": {
                "type": "enum",
                "default": default_log_level,
                "env_var": f"{env_prefix}_LOG_LEVEL",
                "description": f"Logging verbosity; one of {allowed_log_levels}",
                "validation": f"one of {allowed_log_levels}",
                "allowed": allowed_log_levels,
            },
        }

        extra_keys = [
            ("auto_reconnect", {
                "type": "bool",
                "default": True,
                "env_var": f"{env_prefix}_AUTO_RECONNECT",
                "description": "Automatically reconnect on connection loss",
                "validation": "bool",
            }),
            ("query_timeout", {
                "type": "int",
                "default": rng.choice([30, 60, 120]),
                "env_var": f"{env_prefix}_QUERY_TIMEOUT",
                "description": "Query timeout in seconds; must be 1-3600",
                "validation": "int in range [1, 3600]",
                "min": 1,
                "max": 3600,
            }),
        ]
        rng.shuffle(extra_keys)
        for key, spec in extra_keys[: max(0, num_keys - len(schema))]:
            schema[key] = spec

        expected = {
            "domain": "database_client",
            "env_prefix": env_prefix,
            "schema": schema,
            "db_port": db_port,
            "db_port_name": db_port_name,
            "pool_min": pool_min,
            "pool_max": pool_max,
            "conn_timeout": conn_timeout,
            "ssl_modes": ssl_modes,
            "default_ssl_mode": default_ssl_mode,
            "allowed_log_levels": allowed_log_levels,
            "default_log_level": default_log_level,
        }

        return self._build_task(seed, "database_client", env_prefix, schema, expected)

    # -----------------------------------------------------------------------
    # Domain 2: Worker Service Config
    # -----------------------------------------------------------------------

    def _gen_worker_service(self, seed: int, rng: SeededRandom) -> GeneratedTask:
        queue_url_default = rng.choice([
            "redis://localhost:6379/0",
            "amqp://localhost:5672",
            "kafka://localhost:9092",
        ])
        concurrency = rng.randint(2, 16)
        concurrency_max = rng.choice([32, 64, 128])
        retry_max = rng.randint(3, 10)
        retry_backoff = rng.choice([1, 2, 5])
        job_timeout = rng.choice([60, 120, 300, 600])
        log_levels = ["DEBUG", "INFO", "WARN", "ERROR"]
        allowed_log_levels = rng.sample(log_levels, rng.randint(2, 4))
        allowed_log_levels = [l for l in log_levels if l in allowed_log_levels]
        default_log_level = rng.choice(["INFO", "WARN"])
        env_prefix = rng.choice(["WORKER", "JOB", "QUEUE", "CELERY"])
        num_keys = rng.randint(8, 12)

        schema = {
            "queue_url": {
                "type": "string",
                "default": queue_url_default,
                "env_var": f"{env_prefix}_QUEUE_URL",
                "description": "URL of the message queue",
                "validation": "non-empty string",
            },
            "concurrency": {
                "type": "int",
                "default": concurrency,
                "env_var": f"{env_prefix}_CONCURRENCY",
                "description": f"Number of concurrent workers; must be 1-{concurrency_max}",
                "validation": f"int in range [1, {concurrency_max}]",
                "min": 1,
                "max": concurrency_max,
            },
            "max_retries": {
                "type": "int",
                "default": retry_max,
                "env_var": f"{env_prefix}_MAX_RETRIES",
                "description": "Maximum retry attempts per job; must be 0-20",
                "validation": "int in range [0, 20]",
                "min": 0,
                "max": 20,
            },
            "retry_backoff_seconds": {
                "type": "int",
                "default": retry_backoff,
                "env_var": f"{env_prefix}_RETRY_BACKOFF",
                "description": "Seconds to wait between retries; must be 1-300",
                "validation": "int in range [1, 300]",
                "min": 1,
                "max": 300,
            },
            "job_timeout": {
                "type": "int",
                "default": job_timeout,
                "env_var": f"{env_prefix}_JOB_TIMEOUT",
                "description": "Job execution timeout in seconds; must be 1-3600",
                "validation": "int in range [1, 3600]",
                "min": 1,
                "max": 3600,
            },
            "log_level": {
                "type": "enum",
                "default": default_log_level,
                "env_var": f"{env_prefix}_LOG_LEVEL",
                "description": f"Logging verbosity; one of {allowed_log_levels}",
                "validation": f"one of {allowed_log_levels}",
                "allowed": allowed_log_levels,
            },
            "dead_letter_queue": {
                "type": "bool",
                "default": True,
                "env_var": f"{env_prefix}_DEAD_LETTER",
                "description": "Route failed jobs to dead letter queue",
                "validation": "bool",
            },
            "heartbeat_interval": {
                "type": "int",
                "default": rng.choice([10, 30, 60]),
                "env_var": f"{env_prefix}_HEARTBEAT",
                "description": "Worker heartbeat interval seconds; must be 5-300",
                "validation": "int in range [5, 300]",
                "min": 5,
                "max": 300,
            },
        }

        extra_keys = [
            ("prefetch_count", {
                "type": "int",
                "default": rng.choice([1, 5, 10]),
                "env_var": f"{env_prefix}_PREFETCH",
                "description": "Number of messages to prefetch; must be 1-100",
                "validation": "int in range [1, 100]",
                "min": 1,
                "max": 100,
            }),
            ("ack_on_failure", {
                "type": "bool",
                "default": False,
                "env_var": f"{env_prefix}_ACK_ON_FAILURE",
                "description": "Acknowledge message even on job failure",
                "validation": "bool",
            }),
            ("metrics_enabled", {
                "type": "bool",
                "default": True,
                "env_var": f"{env_prefix}_METRICS",
                "description": "Enable Prometheus metrics",
                "validation": "bool",
            }),
            ("queue_poll_interval", {
                "type": "int",
                "default": rng.choice([1, 5, 10]),
                "env_var": f"{env_prefix}_POLL_INTERVAL",
                "description": "Queue polling interval seconds; must be 1-60",
                "validation": "int in range [1, 60]",
                "min": 1,
                "max": 60,
            }),
        ]
        rng.shuffle(extra_keys)
        for key, spec in extra_keys[: max(0, num_keys - len(schema))]:
            schema[key] = spec

        expected = {
            "domain": "worker_service",
            "env_prefix": env_prefix,
            "schema": schema,
            "concurrency": concurrency,
            "concurrency_max": concurrency_max,
            "retry_max": retry_max,
            "retry_backoff": retry_backoff,
            "job_timeout": job_timeout,
            "allowed_log_levels": allowed_log_levels,
            "default_log_level": default_log_level,
        }

        return self._build_task(seed, "worker_service", env_prefix, schema, expected)

    # -----------------------------------------------------------------------
    # Domain 3: ML Pipeline Config
    # -----------------------------------------------------------------------

    def _gen_ml_pipeline(self, seed: int, rng: SeededRandom) -> GeneratedTask:
        batch_size = rng.choice([16, 32, 64, 128, 256])
        batch_size_max = rng.choice([512, 1024, 2048])
        learning_rate_default = rng.choice([0.001, 0.0001, 0.01])
        epochs_default = rng.randint(10, 100)
        epochs_max = rng.choice([500, 1000, 2000])
        log_levels = ["DEBUG", "INFO", "WARN", "ERROR"]
        allowed_log_levels = rng.sample(log_levels, rng.randint(2, 4))
        allowed_log_levels = [l for l in log_levels if l in allowed_log_levels]
        default_log_level = rng.choice(["INFO", "WARN"])
        devices = ["cpu", "cuda", "mps"]
        default_device = "cpu"
        optimizers = ["adam", "sgd", "rmsprop", "adagrad"]
        allowed_optimizers = rng.sample(optimizers, rng.randint(2, 4))
        allowed_optimizers = [o for o in optimizers if o in allowed_optimizers]
        default_optimizer = rng.choice(["adam", "sgd"])
        if default_optimizer not in allowed_optimizers:
            default_optimizer = allowed_optimizers[0]
        env_prefix = rng.choice(["ML", "TRAIN", "MODEL", "PIPELINE"])
        num_keys = rng.randint(8, 12)

        schema = {
            "batch_size": {
                "type": "int",
                "default": batch_size,
                "env_var": f"{env_prefix}_BATCH_SIZE",
                "description": f"Training batch size; must be 1-{batch_size_max}",
                "validation": f"int in range [1, {batch_size_max}]",
                "min": 1,
                "max": batch_size_max,
            },
            "learning_rate": {
                "type": "float",
                "default": learning_rate_default,
                "env_var": f"{env_prefix}_LEARNING_RATE",
                "description": "Learning rate; must be 0.0 < lr <= 1.0",
                "validation": "float in range (0.0, 1.0]",
                "min_exclusive": 0.0,
                "max": 1.0,
            },
            "epochs": {
                "type": "int",
                "default": epochs_default,
                "env_var": f"{env_prefix}_EPOCHS",
                "description": f"Training epochs; must be 1-{epochs_max}",
                "validation": f"int in range [1, {epochs_max}]",
                "min": 1,
                "max": epochs_max,
            },
            "device": {
                "type": "enum",
                "default": default_device,
                "env_var": f"{env_prefix}_DEVICE",
                "description": f"Compute device; one of {devices}",
                "validation": f"one of {devices}",
                "allowed": devices,
            },
            "optimizer": {
                "type": "enum",
                "default": default_optimizer,
                "env_var": f"{env_prefix}_OPTIMIZER",
                "description": f"Optimizer algorithm; one of {allowed_optimizers}",
                "validation": f"one of {allowed_optimizers}",
                "allowed": allowed_optimizers,
            },
            "log_level": {
                "type": "enum",
                "default": default_log_level,
                "env_var": f"{env_prefix}_LOG_LEVEL",
                "description": f"Logging verbosity; one of {allowed_log_levels}",
                "validation": f"one of {allowed_log_levels}",
                "allowed": allowed_log_levels,
            },
            "checkpoint_dir": {
                "type": "string",
                "default": "./checkpoints",
                "env_var": f"{env_prefix}_CHECKPOINT_DIR",
                "description": "Directory for saving model checkpoints",
                "validation": "non-empty string",
            },
            "early_stopping": {
                "type": "bool",
                "default": True,
                "env_var": f"{env_prefix}_EARLY_STOPPING",
                "description": "Enable early stopping",
                "validation": "bool",
            },
        }

        extra_keys = [
            ("dropout_rate", {
                "type": "float",
                "default": rng.choice([0.1, 0.2, 0.5]),
                "env_var": f"{env_prefix}_DROPOUT",
                "description": "Dropout rate; must be 0.0-1.0",
                "validation": "float in range [0.0, 1.0]",
                "min": 0.0,
                "max": 1.0,
            }),
            ("seed_value", {
                "type": "int",
                "default": rng.randint(0, 9999),
                "env_var": f"{env_prefix}_SEED",
                "description": "Random seed for reproducibility; must be 0-2147483647",
                "validation": "int in range [0, 2147483647]",
                "min": 0,
                "max": 2147483647,
            }),
            ("gradient_clip", {
                "type": "float",
                "default": rng.choice([0.5, 1.0, 5.0]),
                "env_var": f"{env_prefix}_GRAD_CLIP",
                "description": "Gradient clipping max norm; must be 0.0-100.0",
                "validation": "float in range [0.0, 100.0]",
                "min": 0.0,
                "max": 100.0,
            }),
            ("num_workers", {
                "type": "int",
                "default": rng.choice([2, 4, 8]),
                "env_var": f"{env_prefix}_NUM_WORKERS",
                "description": "DataLoader worker count; must be 0-32",
                "validation": "int in range [0, 32]",
                "min": 0,
                "max": 32,
            }),
        ]
        rng.shuffle(extra_keys)
        for key, spec in extra_keys[: max(0, num_keys - len(schema))]:
            schema[key] = spec

        expected = {
            "domain": "ml_pipeline",
            "env_prefix": env_prefix,
            "schema": schema,
            "batch_size": batch_size,
            "batch_size_max": batch_size_max,
            "learning_rate": learning_rate_default,
            "epochs": epochs_default,
            "epochs_max": epochs_max,
            "devices": devices,
            "allowed_optimizers": allowed_optimizers,
            "default_optimizer": default_optimizer,
            "allowed_log_levels": allowed_log_levels,
            "default_log_level": default_log_level,
        }

        return self._build_task(seed, "ml_pipeline", env_prefix, schema, expected)

    # -----------------------------------------------------------------------
    # Shared builder: generates workspace files, spec.md, brief.md
    # -----------------------------------------------------------------------

    def _build_task(
        self,
        seed: int,
        domain: str,
        env_prefix: str,
        schema: dict,
        expected: dict,
    ) -> GeneratedTask:
        # Build spec.md
        spec_md = self._build_spec_md(domain, env_prefix, schema)

        # Build brief.md
        brief_md = self._build_brief_md(domain)

        # Build workspace files
        config_skeleton_py = self._build_config_skeleton(schema, env_prefix)
        config_schema_json = self._build_config_schema_json(schema, env_prefix, domain)

        workspace_files = {
            "config_skeleton.py": config_skeleton_py,
            "config_schema.json": config_schema_json,
        }

        return GeneratedTask(
            task_id="SPEC5_config_system",
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
            metadata={"domain": domain, "difficulty": "hard"},
        )

    def _build_spec_md(self, domain: str, env_prefix: str, schema: dict) -> str:
        domain_titles = {
            "web_service": "Web Service",
            "database_client": "Database Client",
            "worker_service": "Worker Service",
            "ml_pipeline": "ML Pipeline",
        }
        title = domain_titles.get(domain, domain)

        # Build schema table
        rows = []
        for key, spec in schema.items():
            typ = spec["type"]
            default = json.dumps(spec["default"])
            env_var = spec["env_var"]
            validation = spec["validation"]
            description = spec["description"]
            rows.append(f"| `{key}` | `{typ}` | {default} | `{env_var}` | {validation} | {description} |")

        schema_table = "\n".join(rows)

        # Build validation details
        validation_details = []
        for key, spec in schema.items():
            typ = spec["type"]
            if typ in ("int", "float") and "min" in spec:
                mn = spec["min"]
                mx = spec["max"]
                exclusive = spec.get("min_exclusive") is not None
                if exclusive:
                    validation_details.append(f"- `{key}`: must be > {mn} and <= {mx}")
                else:
                    validation_details.append(f"- `{key}`: must be in range [{mn}, {mx}] (inclusive)")
            elif typ == "enum":
                allowed = spec["allowed"]
                validation_details.append(f"- `{key}`: must be one of {allowed} (case-sensitive)")
            elif typ == "bool":
                validation_details.append(
                    f"- `{key}`: accepts true/false (case-insensitive), 1/0, yes/no, on/off as string inputs"
                )
            elif typ == "string" and spec.get("validation") == "non-empty string":
                validation_details.append(f"- `{key}`: must be a non-empty string")

        validation_section = "\n".join(validation_details)

        # Build env var table
        env_rows = []
        for key, spec in schema.items():
            env_rows.append(f"| `{spec['env_var']}` | `{key}` | `{spec['type']}` |")
        env_table = "\n".join(env_rows)

        return f"""# SPEC5: {title} Configuration System — Full Specification

## Overview

Implement a configuration management system for the {title} application.
The system must load configuration from multiple sources, validate all values
against the schema, apply correct defaults, and support type coercion.

## Configuration Schema

| Key | Type | Default | Env Var | Validation | Description |
|-----|------|---------|---------|------------|-------------|
{schema_table}

## Validation Rules (EXACT — must be implemented precisely)

{validation_section}

### Type Coercion

When loading from environment variables or config files, string values must be
coerced to the correct type:
- `int`: parse as integer; raise `ConfigValidationError` if not parseable
- `float`: parse as float; raise `ConfigValidationError` if not parseable
- `bool`: accept `true`/`false` (case-insensitive), `1`/`0`, `yes`/`no`, `on`/`off`;
  raise `ConfigValidationError` for any other string
- `enum`: validate the coerced string against `allowed` values
- `string`: use as-is

## Priority Cascade (EXACT order — highest priority first)

1. **CLI arguments** (passed programmatically as a dict to `load_config()`)
2. **Environment variables** (read from `os.environ`)
3. **Config file** (JSON file path passed to `load_config()`)
4. **Built-in defaults** (defined in the schema)

Later sources fill in keys not provided by higher-priority sources.
A key set to the string `""` in a lower-priority source is still overridden
by a non-None value from a higher-priority source.

## Error Handling

All validation failures must raise `ConfigValidationError` (a subclass of `ValueError`)
with a descriptive message. The error must include the key name and the invalid value.

## API Contract

```python
# config_system.py — you must implement this file

class ConfigValidationError(ValueError):
    \"\"\"Raised when a config value fails validation.\"\"\"
    pass

def load_config(
    config_file: str | None = None,
    env_vars: dict | None = None,   # defaults to os.environ if None
    cli_args: dict | None = None,
) -> dict:
    \"\"\"
    Load and validate configuration from all sources in priority order.

    Args:
        config_file: Path to a JSON config file (optional).
        env_vars: Dict of environment variables (defaults to os.environ).
        cli_args: Dict of CLI arguments — highest priority.

    Returns:
        A dict with all config keys populated, validated, and type-coerced.

    Raises:
        ConfigValidationError: If any value fails validation.
        FileNotFoundError: If config_file is specified but does not exist.
    \"\"\"
    ...

def get_schema() -> dict:
    \"\"\"Return the config schema as a dict (key -> spec dict).\"\"\"
    ...

def validate_value(key: str, value) -> object:
    \"\"\"
    Validate and coerce a single value against the schema for `key`.

    Returns the coerced value.
    Raises ConfigValidationError if invalid.
    \"\"\"
    ...
```

## Environment Variable Mapping

| Environment Variable | Config Key | Type |
|----------------------|------------|------|
{env_table}

## Config File Format

The config file is a JSON object with config keys as fields:
```json
{{
  "key_name": value,
  ...
}}
```
Unknown keys in the config file are ignored (not an error).

## Notes

- The schema is available at runtime via `get_schema()`; do not hard-code it
  separately from the implementation.
- The `config_schema.json` in the workspace contains a **partial** schema
  (only some keys). The full schema is defined above — use the spec, not the
  JSON file, as the authoritative source.
- All config keys defined in the schema must be present in the returned dict,
  even if no source provides a value (use the default).
"""

    def _build_brief_md(self, domain: str) -> str:
        domain_titles = {
            "web_service": "Web Service",
            "database_client": "Database Client",
            "worker_service": "Worker Service",
            "ml_pipeline": "ML Pipeline",
        }
        title = domain_titles.get(domain, domain)

        return f"""# SPEC5: {title} Configuration System (Executor Brief)

The application needs a configuration management system. Implement it.

## Workspace

- `config_skeleton.py` — skeleton with class/function stubs and TODOs
- `config_schema.json` — partial schema (incomplete — the Planner has the full spec)

## What to Implement

Create `config_system.py` that implements:

1. `ConfigValidationError` — exception class
2. `load_config(config_file, env_vars, cli_args)` — loads config from all sources
3. `get_schema()` — returns the full schema dict
4. `validate_value(key, value)` — validates and coerces a single value

The Planner has the full specification including:
- Complete config schema with all keys, types, defaults, and validation rules
- Priority cascade order (CLI > env vars > config file > defaults)
- Exact type coercion rules for booleans, ints, floats
- Exact error types and messages

## Testing

```bash
python3 -c "from config_system import load_config; cfg = load_config(); print(cfg)"
```
"""

    def _build_config_skeleton(self, schema: dict, env_prefix: str) -> str:
        # Show only the first 3 keys as examples in the skeleton, leave rest as TODO
        keys_list = list(schema.items())
        example_keys = keys_list[:3]

        example_lines = []
        for key, spec in example_keys:
            example_lines.append(f'        # "{key}": ... (type: {spec["type"]}, default: {json.dumps(spec["default"])})')

        example_block = "\n".join(example_lines)

        return f'''\
"""
Configuration system skeleton for the application.

TODO: Implement this as config_system.py (not this file).

This skeleton shows the required interface. The Planner has the full
specification with all config keys, types, validation rules, and defaults.
"""
import json
import os
from typing import Any


# TODO: Implement ConfigValidationError
class ConfigValidationError(ValueError):
    """Raised when a config value fails validation."""
    pass


# TODO: Define the full schema here
# The schema maps config key names to their specification.
# This is a PARTIAL example — see the full spec for all keys.
# Example structure:
{example_block}
# ... (see spec for remaining keys)
_SCHEMA: dict[str, dict] = {{
    # TODO: populate from spec
}}


def load_config(
    config_file: str | None = None,
    env_vars: dict | None = None,
    cli_args: dict | None = None,
) -> dict:
    """
    Load and validate configuration from all sources.

    Priority (highest first): cli_args > env_vars > config_file > defaults

    TODO: Implement priority cascade
    TODO: Apply type coercion for each key
    TODO: Validate all values against the schema
    TODO: Apply defaults for missing keys
    """
    pass


def get_schema() -> dict:
    """Return the config schema."""
    # TODO: return _SCHEMA
    pass


def validate_value(key: str, value: Any) -> Any:
    """
    Validate and coerce a single value for the given config key.

    TODO: Look up key in _SCHEMA
    TODO: Coerce type (int, float, bool, enum, string)
    TODO: Validate range/allowed values
    TODO: Raise ConfigValidationError on failure
    """
    pass
'''

    def _build_config_schema_json(self, schema: dict, env_prefix: str, domain: str) -> str:
        # Provide a partial schema — only some keys, missing validation details
        keys = list(schema.keys())
        # Keep roughly half the keys, and strip validation fields from those
        partial_count = max(3, len(keys) // 2)
        partial_keys = keys[:partial_count]

        partial_schema = {}
        for key in partial_keys:
            spec = schema[key]
            # Omit min/max/allowed (the critical validation details)
            partial_entry = {
                "type": spec["type"],
                "default": spec["default"],
                "env_var": spec["env_var"],
                "description": spec["description"],
            }
            partial_schema[key] = partial_entry

        doc = {
            "_comment": (
                "PARTIAL schema — this file is incomplete. "
                "The full schema with validation rules is in spec.md. "
                f"Domain: {domain}. Env prefix: {env_prefix}."
            ),
            "schema": partial_schema,
        }
        return json.dumps(doc, indent=2)
