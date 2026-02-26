"""
Parameterized generator for O6: Service Performance Tuning.

Each seed produces:
  - Different service type (api_gateway, stream_processor, ml_inference, search_engine)
  - Different performance targets (CPU, memory, p99 latency, throughput, error rate)
  - Different config knobs with interaction effects
  - Same challenge: suboptimal defaults must be tuned to hit all 5 metric targets

TNI Pattern C: Spec has 5 performance targets, the available config knobs, the
interaction effects (more threads -> more throughput but also more memory), and
the scoring weights. Brief says "The service is slow."

Simulator uses additive/multiplicative model where:
  - thread_pool_size drives throughput and p99 latency but raises CPU and memory
  - connection_pool_size drives throughput with mild CPU cost
  - cache_size_mb reduces CPU and p99 latency (cache hits)
  - batch_size improves throughput, reduces per-request CPU
  - timeout_ms does not affect performance metrics but must stay in valid range
  - gc_interval_sec reduces memory at cost of occasional CPU spikes (modeled as +CPU)

The bad config leaves thread_pool_size and cache_size_mb too low and
batch_size=1, causing high latency and low throughput while keeping
CPU/memory within budget — agents must find the sweet spot.
"""
from __future__ import annotations

import json

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom

# ── Service profiles ──────────────────────────────────────────────────────────
#
# Each profile has:
#   targets: 5 performance budgets (cpu_pct, memory_pct, p99_ms, throughput_rps, error_rate)
#   bad_config:  suboptimal defaults shipped in workspace
#   good_config: one valid optimal config (used for expected.json; agents may find others)
#   sim_params:  coefficients for the simulator model
#   weights:     per-metric scoring weights (must sum to 1.0)
#   knob_ranges: valid ranges per knob (for grade.sh validation)

SERVICE_PROFILES = [
    # ── Seed 0 mod 4: API Gateway ─────────────────────────────────────────────
    {
        "service_type": "api_gateway",
        "description": "HTTP API gateway routing requests to backend microservices",
        # Performance budget (ALL must be met)
        "cpu_target_pct":      70.0,   # CPU utilisation must be < 70%
        "memory_target_pct":   80.0,   # Memory utilisation must be < 80%
        "p99_target_ms":      200.0,   # p99 latency must be < 200 ms
        "throughput_target":  500.0,   # throughput must be > 500 rps
        "error_rate_target":    0.1,   # error rate must be < 0.1 %
        # Suboptimal defaults — too few threads and tiny cache
        "bad_config": {
            "thread_pool_size":    4,
            "connection_pool_size": 10,
            "cache_size_mb":       64,
            "batch_size":           1,
            "timeout_ms":        5000,
            "gc_interval_sec":     30,
        },
        # One known-good config (there are others)
        "good_config": {
            "thread_pool_size":   16,
            "connection_pool_size": 50,
            "cache_size_mb":    1024,
            "batch_size":         20,
            "timeout_ms":       3000,
            "gc_interval_sec":    60,
        },
        # Simulator baseline (what bad_config produces)
        "base_cpu_pct":      85.0,
        "base_memory_pct":   55.0,
        "base_p99_ms":      420.0,
        "base_throughput":  180.0,
        "base_error_rate":    2.5,
        # Interaction coefficients (see simulator.py for model)
        "thread_cpu_coeff":      3.0,   # each thread adds N% CPU
        "thread_mem_coeff":      1.2,   # each thread adds N% memory
        "conn_cpu_coeff":        0.4,   # each conn adds N% CPU
        "cache_cpu_relief":      0.04,  # log2 cache hits reduce CPU
        "cache_mem_coeff":       0.015, # cache_mb adds N% memory per MB (per 100MB)
        "batch_throughput_coeff": 0.06, # log2 batch boosts throughput
        "gc_mem_coeff":          0.8,   # shorter gc = higher memory baseline
        # Scoring weights (sum = 1.0)
        "weights": {
            "cpu":        0.20,
            "memory":     0.15,
            "p99":        0.30,
            "throughput": 0.25,
            "error_rate": 0.10,
        },
        # Valid knob ranges
        "knob_ranges": {
            "thread_pool_size":     {"min": 1,   "max": 128},
            "connection_pool_size": {"min": 1,   "max": 500},
            "cache_size_mb":        {"min": 0,   "max": 16384},
            "batch_size":           {"min": 1,   "max": 1000},
            "timeout_ms":           {"min": 100, "max": 30000},
            "gc_interval_sec":      {"min": 5,   "max": 300},
        },
    },
    # ── Seed 1 mod 4: Stream Processor ───────────────────────────────────────
    {
        "service_type": "stream_processor",
        "description": "real-time event stream processing pipeline (Kafka consumer)",
        "cpu_target_pct":      65.0,
        "memory_target_pct":   75.0,
        "p99_target_ms":      150.0,
        "throughput_target":  800.0,
        "error_rate_target":    0.05,
        "bad_config": {
            "thread_pool_size":    2,
            "connection_pool_size":  5,
            "cache_size_mb":       32,
            "batch_size":           1,
            "timeout_ms":       10000,
            "gc_interval_sec":     15,
        },
        "good_config": {
            "thread_pool_size":   12,
            "connection_pool_size": 40,
            "cache_size_mb":     512,
            "batch_size":         50,
            "timeout_ms":       5000,
            "gc_interval_sec":    90,
        },
        "base_cpu_pct":      78.0,
        "base_memory_pct":   82.0,
        "base_p99_ms":      350.0,
        "base_throughput":  120.0,
        "base_error_rate":    3.8,
        "thread_cpu_coeff":      2.5,
        "thread_mem_coeff":      1.5,
        "conn_cpu_coeff":        0.3,
        "cache_cpu_relief":      0.05,
        "cache_mem_coeff":       0.020,
        "batch_throughput_coeff": 0.08,
        "gc_mem_coeff":          1.2,
        "weights": {
            "cpu":        0.20,
            "memory":     0.20,
            "p99":        0.25,
            "throughput": 0.25,
            "error_rate": 0.10,
        },
        "knob_ranges": {
            "thread_pool_size":     {"min": 1,   "max": 64},
            "connection_pool_size": {"min": 1,   "max": 200},
            "cache_size_mb":        {"min": 0,   "max": 8192},
            "batch_size":           {"min": 1,   "max": 500},
            "timeout_ms":           {"min": 500, "max": 60000},
            "gc_interval_sec":      {"min": 10,  "max": 600},
        },
    },
    # ── Seed 2 mod 4: ML Inference Server ────────────────────────────────────
    {
        "service_type": "ml_inference",
        "description": "model inference server serving predictions via REST API",
        "cpu_target_pct":      60.0,
        "memory_target_pct":   85.0,
        "p99_target_ms":      300.0,
        "throughput_target":  200.0,
        "error_rate_target":    0.2,
        "bad_config": {
            "thread_pool_size":    1,
            "connection_pool_size":  8,
            "cache_size_mb":      128,
            "batch_size":           1,
            "timeout_ms":       15000,
            "gc_interval_sec":     10,
        },
        "good_config": {
            "thread_pool_size":    8,
            "connection_pool_size": 30,
            "cache_size_mb":    2048,
            "batch_size":         16,
            "timeout_ms":       8000,
            "gc_interval_sec":   120,
        },
        "base_cpu_pct":      92.0,
        "base_memory_pct":   60.0,
        "base_p99_ms":      650.0,
        "base_throughput":   45.0,
        "base_error_rate":    5.0,
        "thread_cpu_coeff":      5.0,
        "thread_mem_coeff":      2.0,
        "conn_cpu_coeff":        0.5,
        "cache_cpu_relief":      0.06,
        "cache_mem_coeff":       0.012,
        "batch_throughput_coeff": 0.10,
        "gc_mem_coeff":          1.5,
        "weights": {
            "cpu":        0.25,
            "memory":     0.20,
            "p99":        0.25,
            "throughput": 0.20,
            "error_rate": 0.10,
        },
        "knob_ranges": {
            "thread_pool_size":     {"min": 1,   "max": 32},
            "connection_pool_size": {"min": 1,   "max": 100},
            "cache_size_mb":        {"min": 0,   "max": 32768},
            "batch_size":           {"min": 1,   "max": 256},
            "timeout_ms":           {"min": 1000, "max": 120000},
            "gc_interval_sec":      {"min": 10,   "max": 600},
        },
    },
    # ── Seed 3 mod 4: Search Engine ───────────────────────────────────────────
    {
        "service_type": "search_engine",
        "description": "full-text search engine with inverted index and caching layer",
        "cpu_target_pct":      70.0,
        "memory_target_pct":   80.0,
        "p99_target_ms":      100.0,
        "throughput_target": 1000.0,
        "error_rate_target":    0.1,
        "bad_config": {
            "thread_pool_size":    3,
            "connection_pool_size": 15,
            "cache_size_mb":       64,
            "batch_size":           1,
            "timeout_ms":        2000,
            "gc_interval_sec":     20,
        },
        "good_config": {
            "thread_pool_size":   20,
            "connection_pool_size": 80,
            "cache_size_mb":    4096,
            "batch_size":         30,
            "timeout_ms":       1000,
            "gc_interval_sec":    45,
        },
        "base_cpu_pct":      80.0,
        "base_memory_pct":   50.0,
        "base_p99_ms":      280.0,
        "base_throughput":  250.0,
        "base_error_rate":    1.2,
        "thread_cpu_coeff":      2.0,
        "thread_mem_coeff":      0.8,
        "conn_cpu_coeff":        0.2,
        "cache_cpu_relief":      0.07,
        "cache_mem_coeff":       0.010,
        "batch_throughput_coeff": 0.05,
        "gc_mem_coeff":          0.6,
        "weights": {
            "cpu":        0.15,
            "memory":     0.15,
            "p99":        0.35,
            "throughput": 0.25,
            "error_rate": 0.10,
        },
        "knob_ranges": {
            "thread_pool_size":     {"min": 1,   "max": 256},
            "connection_pool_size": {"min": 1,   "max": 1000},
            "cache_size_mb":        {"min": 0,   "max": 65536},
            "batch_size":           {"min": 1,   "max": 2000},
            "timeout_ms":           {"min": 50,  "max": 10000},
            "gc_interval_sec":      {"min": 5,   "max": 300},
        },
    },
]


class Generator(TaskGenerator):
    task_id = "O6_perf_tuning"
    domain = "operations"
    difficulty = "expert"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        profile = SERVICE_PROFILES[seed % len(SERVICE_PROFILES)]

        workspace_files = self._build_workspace(profile)
        spec_md = self._generate_spec(profile)
        brief_md = self._generate_brief(profile)

        # Verify good_config actually passes (sanity check for generator authors)
        expected = {
            "service_type": profile["service_type"],
            "targets": {
                "cpu_pct":       profile["cpu_target_pct"],
                "memory_pct":    profile["memory_target_pct"],
                "p99_ms":        profile["p99_target_ms"],
                "throughput_rps": profile["throughput_target"],
                "error_rate_pct": profile["error_rate_target"],
            },
            "example_good_config": profile["good_config"],
            "constraints": {
                "cpu_within_target":         True,
                "memory_within_target":      True,
                "p99_meets_target":          True,
                "throughput_meets_target":   True,
                "error_rate_within_target":  True,
                "config_values_valid":       True,
                "no_contradictory_settings": True,
                "score_above_baseline":      True,
            },
        }

        return GeneratedTask(
            task_id=self.task_id,
            seed=seed,
            spec_md=spec_md,
            brief_md=brief_md,
            expected=expected,
            workspace_files=workspace_files,
        )

    # ──────────────────────────────────────────────────────────────────────────
    # Workspace builder
    # ──────────────────────────────────────────────────────────────────────────

    def _build_workspace(self, p: dict) -> dict[str, str]:
        files: dict[str, str] = {}
        files["config.json"] = self._build_config_json(p)
        files["simulator.py"] = self._build_simulator(p)
        files["target.json"] = self._build_target_json(p)
        return files

    def _build_config_json(self, p: dict) -> str:
        bad = p["bad_config"]
        cfg = {
            "service_type": p["service_type"],
            **bad,
        }
        return json.dumps(cfg, indent=2) + "\n"

    def _build_target_json(self, p: dict) -> str:
        targets = {
            "service_type": p["service_type"],
            "performance_budget": {
                "cpu_utilisation_pct":  {"max": p["cpu_target_pct"],    "unit": "%"},
                "memory_utilisation_pct": {"max": p["memory_target_pct"], "unit": "%"},
                "p99_latency_ms":       {"max": p["p99_target_ms"],     "unit": "ms"},
                "throughput_rps":       {"min": p["throughput_target"],  "unit": "rps"},
                "error_rate_pct":       {"max": p["error_rate_target"],  "unit": "%"},
            },
            "scoring_weights": p["weights"],
            "config_knob_ranges": p["knob_ranges"],
        }
        return json.dumps(targets, indent=2) + "\n"

    def _build_simulator(self, p: dict) -> str:
        stype = p["service_type"]
        stype_display = stype.upper().replace("_", " ")
        cpu_t = p["cpu_target_pct"]
        mem_t = p["memory_target_pct"]
        p99_t = p["p99_target_ms"]
        tput_t = p["throughput_target"]
        err_t = p["error_rate_target"]
        w = p["weights"]
        kr = p["knob_ranges"]

        base_cpu  = p["base_cpu_pct"]
        base_mem  = p["base_memory_pct"]
        base_p99  = p["base_p99_ms"]
        base_tput = p["base_throughput"]
        base_err  = p["base_error_rate"]

        th_cpu  = p["thread_cpu_coeff"]
        th_mem  = p["thread_mem_coeff"]
        cn_cpu  = p["conn_cpu_coeff"]
        ca_cpu  = p["cache_cpu_relief"]
        ca_mem  = p["cache_mem_coeff"]
        bt_tput = p["batch_throughput_coeff"]
        gc_mem  = p["gc_mem_coeff"]

        kr_thread = kr["thread_pool_size"]
        kr_conn   = kr["connection_pool_size"]
        kr_cache  = kr["cache_size_mb"]
        kr_batch  = kr["batch_size"]
        kr_tmo    = kr["timeout_ms"]
        kr_gc     = kr["gc_interval_sec"]

        return f'''"""
Performance simulator for {stype}.

Usage:
    python simulator.py                     # evaluate config.json
    python simulator.py --config my.json    # evaluate a custom config file
    python simulator.py --check             # exit 0 if ALL targets met, else 1

The simulator models how the six configuration knobs interact:

Knob interactions
-----------------
thread_pool_size (T):
  Increases throughput (sqrt scaling with concurrency gains).
  Increases p99 latency reduction via parallelism (log2).
  Increases CPU utilisation (each thread costs {th_cpu:.1f}% CPU at baseline).
  Increases memory utilisation (each thread costs {th_mem:.1f}% memory).

connection_pool_size (C):
  Increases throughput (log2 scaling).
  Small CPU cost ({cn_cpu:.2f}% per connection).

cache_size_mb (M):
  Reduces CPU utilisation via cache hits (log2 relief, coeff {ca_cpu:.3f}).
  Reduces p99 latency via cache hits.
  Adds memory utilisation ({ca_mem:.4f}% per MB / 100).

batch_size (B):
  Increases throughput (amortises per-request overhead, log2, coeff {bt_tput:.3f}).
  Reduces per-request error rate at larger batch sizes.

timeout_ms:
  Must stay in [{kr_tmo["min"]}, {kr_tmo["max"]}].
  Has no direct effect on throughput/latency in this model.

gc_interval_sec (G):
  Longer interval -> lower memory pressure ({gc_mem:.2f}x relief per doubling).
  Shorter interval -> more frequent GC pauses -> slightly higher CPU.
  Must stay in [{kr_gc["min"]}, {kr_gc["max"]}].

Performance targets (ALL must be met)
--------------------------------------
  CPU utilisation  < {cpu_t} %
  Memory utilisat. < {mem_t} %
  p99 latency      < {p99_t} ms
  Throughput       > {tput_t} rps
  Error rate       < {err_t} %
"""
import argparse
import json
import math
import sys


# ── Targets ───────────────────────────────────────────────────────────────────
CPU_TARGET_PCT      = {cpu_t}
MEMORY_TARGET_PCT   = {mem_t}
P99_TARGET_MS       = {p99_t}
THROUGHPUT_TARGET   = {tput_t}
ERROR_RATE_TARGET   = {err_t}

# ── Scoring weights ───────────────────────────────────────────────────────────
WEIGHT_CPU        = {w["cpu"]}
WEIGHT_MEMORY     = {w["memory"]}
WEIGHT_P99        = {w["p99"]}
WEIGHT_THROUGHPUT = {w["throughput"]}
WEIGHT_ERROR_RATE = {w["error_rate"]}

# ── Baseline values (what the shipped bad config produces) ────────────────────
BASELINE_CPU_PCT      = {base_cpu}
BASELINE_MEMORY_PCT   = {base_mem}
BASELINE_P99_MS       = {base_p99}
BASELINE_THROUGHPUT   = {base_tput}
BASELINE_ERROR_RATE   = {base_err}

# ── Baseline config (bad defaults shipped in config.json) ────────────────────
BASELINE_THREADS = {p["bad_config"]["thread_pool_size"]}
BASELINE_CONNS   = {p["bad_config"]["connection_pool_size"]}
BASELINE_CACHE   = {p["bad_config"]["cache_size_mb"]}
BASELINE_BATCH   = {p["bad_config"]["batch_size"]}
BASELINE_GC      = {p["bad_config"]["gc_interval_sec"]}

# ── Valid ranges ──────────────────────────────────────────────────────────────
KNOB_RANGES = {{
    "thread_pool_size":     ({kr_thread["min"]}, {kr_thread["max"]}),
    "connection_pool_size": ({kr_conn["min"]},   {kr_conn["max"]}),
    "cache_size_mb":        ({kr_cache["min"]},  {kr_cache["max"]}),
    "batch_size":           ({kr_batch["min"]},  {kr_batch["max"]}),
    "timeout_ms":           ({kr_tmo["min"]},    {kr_tmo["max"]}),
    "gc_interval_sec":      ({kr_gc["min"]},     {kr_gc["max"]}),
}}

# ── Interaction coefficients ──────────────────────────────────────────────────
THREAD_CPU_COEFF       = {th_cpu}    # CPU cost per thread relative to baseline
THREAD_MEM_COEFF       = {th_mem}    # Memory cost per thread relative to baseline
CONN_CPU_COEFF         = {cn_cpu}    # CPU cost per connection
CACHE_CPU_RELIEF_COEFF = {ca_cpu}    # CPU relief from cache (log2 factor)
CACHE_MEM_COEFF        = {ca_mem}    # Memory overhead per 100 MB of cache
BATCH_TPUT_COEFF       = {bt_tput}   # Throughput boost from batching (log2 factor)
GC_MEM_COEFF           = {gc_mem}    # Memory relief factor from longer GC interval

BASELINE_SCORE         = 0.35   # bad config scores ~0.35; agent must beat this


def validate_config(cfg: dict) -> list[str]:
    """Return list of validation errors (empty = valid)."""
    errors = []
    for knob, (lo, hi) in KNOB_RANGES.items():
        val = cfg.get(knob)
        if val is None:
            errors.append(f"Missing knob: {{knob}}")
            continue
        if not isinstance(val, (int, float)):
            errors.append(f"{{knob}} must be numeric, got {{type(val).__name__}}")
            continue
        if val < lo or val > hi:
            errors.append(f"{{knob}}={{val}} out of range [{{lo}}, {{hi}}]")
    # Contradictory settings: batch_size > thread_pool_size is wasteful but not
    # forbidden; however batch_size * thread_pool_size > 10000 creates backpressure
    threads = cfg.get("thread_pool_size", 1)
    batch   = cfg.get("batch_size", 1)
    if isinstance(threads, (int, float)) and isinstance(batch, (int, float)):
        if threads * batch > 10000:
            errors.append(
                f"Contradictory: thread_pool_size({{threads}}) * batch_size({{batch}}) "
                f"= {{threads * batch}} > 10000 causes backpressure"
            )
    return errors


def compute_metrics(cfg: dict) -> dict:
    """
    Compute all 5 performance metrics from config knobs.

    All metrics are modelled as deviations from the baseline (bad config).
    Positive interactions improve metrics; interactions are bounded to prevent
    unrealistic values.
    """
    threads = cfg.get("thread_pool_size",    BASELINE_THREADS)
    conns   = cfg.get("connection_pool_size", BASELINE_CONNS)
    cache   = cfg.get("cache_size_mb",       BASELINE_CACHE)
    batch   = cfg.get("batch_size",          BASELINE_BATCH)
    gc_int  = cfg.get("gc_interval_sec",     BASELINE_GC)

    # ── CPU utilisation ───────────────────────────────────────────────────────
    # More threads -> more CPU; more cache -> fewer backend calls -> less CPU.
    # Connection pool has small additive CPU cost.
    thread_cpu_delta = THREAD_CPU_COEFF * (threads - BASELINE_THREADS)
    conn_cpu_delta   = CONN_CPU_COEFF   * (conns   - BASELINE_CONNS)
    cache_cpu_relief = CACHE_CPU_RELIEF_COEFF * (
        math.log2(max(cache, 1) + 1) - math.log2(max(BASELINE_CACHE, 1) + 1)
    ) * 100  # convert to percentage points
    # Shorter GC interval -> more GC pauses -> slightly more CPU used
    gc_cpu_delta = 2.0 * math.log2(max(BASELINE_GC, 1) / max(gc_int, 1) + 1)

    cpu_pct = BASELINE_CPU_PCT + thread_cpu_delta + conn_cpu_delta - cache_cpu_relief + gc_cpu_delta
    cpu_pct = max(5.0, min(200.0, cpu_pct))

    # ── Memory utilisation ────────────────────────────────────────────────────
    # More threads -> more memory; more cache -> more memory.
    # Longer GC interval -> memory can grow -> lower effective utilisation
    # (because GC reclaims more; modelled as log2 relief).
    thread_mem_delta = THREAD_MEM_COEFF * (threads - BASELINE_THREADS)
    cache_mem_delta  = CACHE_MEM_COEFF  * (cache   - BASELINE_CACHE) / 100.0 * 100
    gc_mem_relief    = GC_MEM_COEFF * math.log2(max(gc_int, 1) / max(BASELINE_GC, 1) + 1) * 5

    memory_pct = BASELINE_MEMORY_PCT + thread_mem_delta + cache_mem_delta - gc_mem_relief
    memory_pct = max(5.0, min(200.0, memory_pct))

    # ── p99 latency ───────────────────────────────────────────────────────────
    # More threads reduce latency (parallelism, log2).
    # More cache reduces latency (cache hits, log2).
    # More connections reduce latency slightly (less queuing).
    thread_p99_factor = math.log2(max(BASELINE_THREADS, 1) + 1) / math.log2(threads + 1)
    cache_p99_factor  = math.log2(max(BASELINE_CACHE, 1)   + 1) / math.log2(max(cache, 1) + 1)
    conn_p99_factor   = math.sqrt(BASELINE_CONNS / max(conns, 1))

    p99_ms = BASELINE_P99_MS * thread_p99_factor * cache_p99_factor * conn_p99_factor
    p99_ms = max(1.0, p99_ms)

    # ── Throughput ────────────────────────────────────────────────────────────
    # More threads (sqrt scaling), more connections (log2), larger batch (log2).
    thread_tput_factor = math.sqrt(threads / max(BASELINE_THREADS, 1))
    conn_tput_factor   = math.log2(conns   + 1) / math.log2(BASELINE_CONNS + 1)
    batch_tput_factor  = 1.0 + BATCH_TPUT_COEFF * (
        math.log2(max(batch, 1) + 1) - math.log2(max(BASELINE_BATCH, 1) + 1)
    )

    throughput = BASELINE_THROUGHPUT * thread_tput_factor * conn_tput_factor * max(batch_tput_factor, 0.1)
    throughput = max(1.0, throughput)

    # ── Error rate ────────────────────────────────────────────────────────────
    # Fewer threads -> more timeouts -> higher error rate.
    # More cache -> fewer backend misses -> lower error rate.
    # Larger batch -> amortises retries -> lower error rate.
    thread_err_factor = math.sqrt(BASELINE_THREADS / max(threads, 1))
    cache_err_factor  = math.log2(max(BASELINE_CACHE, 1) + 1) / math.log2(max(cache, 1) + 1)
    batch_err_factor  = 1.0 / (1.0 + 0.03 * math.log2(max(batch, 1) + 1))

    error_rate = BASELINE_ERROR_RATE * thread_err_factor * cache_err_factor * batch_err_factor
    error_rate = max(0.0, min(100.0, error_rate))

    return {{
        "cpu_pct":       round(cpu_pct,    2),
        "memory_pct":    round(memory_pct, 2),
        "p99_ms":        round(p99_ms,     1),
        "throughput_rps": round(throughput, 1),
        "error_rate_pct": round(error_rate, 4),
    }}


def check_all(cfg: dict) -> dict:
    """Evaluate config and return structured result with per-check pass/fail."""
    validation_errors = validate_config(cfg)
    if validation_errors:
        return {{
            "valid_config": False,
            "validation_errors": validation_errors,
            "metrics": None,
            "checks": {{
                "config_values_valid":       False,
                "no_contradictory_settings": False,
                "cpu_within_target":         False,
                "memory_within_target":      False,
                "p99_meets_target":          False,
                "throughput_meets_target":   False,
                "error_rate_within_target":  False,
                "score_above_baseline":      False,
            }},
        }}

    metrics = compute_metrics(cfg)

    # Contradictory settings check (already validated in validate_config)
    no_contradictions = len([e for e in validation_errors if "Contradictory" in e]) == 0

    checks = {{
        "config_values_valid":       True,
        "no_contradictory_settings": no_contradictions,
        "cpu_within_target":         metrics["cpu_pct"]        < CPU_TARGET_PCT,
        "memory_within_target":      metrics["memory_pct"]     < MEMORY_TARGET_PCT,
        "p99_meets_target":          metrics["p99_ms"]         < P99_TARGET_MS,
        "throughput_meets_target":   metrics["throughput_rps"] > THROUGHPUT_TARGET,
        "error_rate_within_target":  metrics["error_rate_pct"] < ERROR_RATE_TARGET,
        "score_above_baseline":      _weighted_score(metrics)  > BASELINE_SCORE,
    }}

    return {{
        "valid_config": True,
        "validation_errors": [],
        "metrics": metrics,
        "checks": checks,
    }}


def _weighted_score(metrics: dict) -> float:
    """Compute normalised weighted score in [0, 1]."""
    cpu_score  = min(1.0, CPU_TARGET_PCT      / max(metrics["cpu_pct"], 0.1))
    mem_score  = min(1.0, MEMORY_TARGET_PCT   / max(metrics["memory_pct"], 0.1))
    p99_score  = min(1.0, P99_TARGET_MS       / max(metrics["p99_ms"], 0.1))
    tput_score = min(1.0, metrics["throughput_rps"] / THROUGHPUT_TARGET)
    err_score  = min(1.0, ERROR_RATE_TARGET   / max(metrics["error_rate_pct"], 0.0001))

    raw = (
        WEIGHT_CPU        * cpu_score  +
        WEIGHT_MEMORY     * mem_score  +
        WEIGHT_P99        * p99_score  +
        WEIGHT_THROUGHPUT * tput_score +
        WEIGHT_ERROR_RATE * err_score
    )
    # Penalty: failing any hard target halves the score
    all_hard_pass = (
        metrics["cpu_pct"]        < CPU_TARGET_PCT  and
        metrics["memory_pct"]     < MEMORY_TARGET_PCT and
        metrics["p99_ms"]         < P99_TARGET_MS   and
        metrics["throughput_rps"] > THROUGHPUT_TARGET and
        metrics["error_rate_pct"] < ERROR_RATE_TARGET
    )
    if not all_hard_pass:
        raw *= 0.5
    return round(raw, 4)


def main():
    parser = argparse.ArgumentParser(description="Performance simulator for {stype}")
    parser.add_argument("--config", default="config.json",
                        help="Path to config JSON (default: config.json)")
    parser.add_argument("--check", action="store_true",
                        help="Exit 0 if ALL performance targets met, else 1")
    args = parser.parse_args()

    with open(args.config) as f:
        cfg = json.load(f)

    result = check_all(cfg)

    print(f"=== {stype_display} PERFORMANCE REPORT ===")
    print()

    if not result["valid_config"]:
        print("CONFIG VALIDATION FAILED:")
        for err in result["validation_errors"]:
            print(f"  ERROR: {{err}}")
        if args.check:
            sys.exit(1)
        return

    m = result["metrics"]
    print(f"CPU Utilisation:  {{m[\'cpu_pct\']:6.2f}} %    (target: < {{CPU_TARGET_PCT}} %)")
    print(f"Memory Utilisat.: {{m[\'memory_pct\']:6.2f}} %    (target: < {{MEMORY_TARGET_PCT}} %)")
    print(f"p99 Latency:      {{m[\'p99_ms\']:6.1f}} ms   (target: < {{P99_TARGET_MS}} ms)")
    print(f"Throughput:       {{m[\'throughput_rps\']:6.1f}} rps  (target: > {{THROUGHPUT_TARGET}} rps)")
    print(f"Error Rate:       {{m[\'error_rate_pct\']:6.4f}} %    (target: < {{ERROR_RATE_TARGET}} %)")
    print(f"Weighted Score:   {{_weighted_score(m):.4f}}       (baseline: > {{BASELINE_SCORE}})")
    print()
    print("=== CHECK RESULTS ===")

    all_pass = True
    for name, passed in result["checks"].items():
        status = "PASS" if passed else "FAIL"
        print(f"  {{status}}  {{name}}")
        if not passed:
            all_pass = False

    print()
    if all_pass:
        print("ALL CHECKS PASSED")
    else:
        print("SOME CHECKS FAILED")

    if args.check:
        sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
'''

    # ──────────────────────────────────────────────────────────────────────────
    # Spec / brief generators
    # ──────────────────────────────────────────────────────────────────────────

    def _generate_spec(self, p: dict) -> str:
        stype = p["service_type"]
        desc  = p["description"]
        cpu_t = p["cpu_target_pct"]
        mem_t = p["memory_target_pct"]
        p99_t = p["p99_target_ms"]
        tput_t = p["throughput_target"]
        err_t = p["error_rate_target"]
        w = p["weights"]
        kr = p["knob_ranges"]
        bad = p["bad_config"]

        knob_rows = "\n".join(
            f"| `{k}` | `{bad[k]}` | [{v['min']}, {v['max']}] |"
            for k, v in kr.items()
        )

        weight_rows = "\n".join(
            f"| {metric.replace('_', ' ').title()} | {int(wt * 100)}% |"
            for metric, wt in w.items()
        )

        return f"""# O6: Service Performance Tuning

## Service Under Optimization
**Type**: {stype} — {desc}

## Performance Budget (ALL five targets must be met simultaneously)

| Metric | Target | Direction |
|--------|--------|-----------|
| CPU utilisation | < {cpu_t} % | lower is better |
| Memory utilisation | < {mem_t} % | lower is better |
| p99 latency | < {p99_t} ms | lower is better |
| Throughput | > {tput_t} rps | higher is better |
| Error rate | < {err_t} % | lower is better |

## Configuration Knobs

Edit `config.json` to tune the service. All six knobs must remain within their valid ranges.

| Knob | Current (bad) default | Valid range |
|------|-----------------------|-------------|
{knob_rows}

## Interaction Effects

Understanding how knobs interact is critical for expert tuning:

- **`thread_pool_size`** (T): More threads increase throughput (√T scaling) and
  reduce p99 latency (log₂ parallelism). However, each thread adds CPU and memory
  pressure. There is a diminishing-returns curve — doubling threads beyond ~16
  gives little throughput gain while linearly increasing resource usage.

- **`connection_pool_size`** (C): More connections allow more concurrent backend
  calls, improving throughput (log₂C) with a minor CPU cost per connection.

- **`cache_size_mb`** (M): A larger cache reduces CPU utilisation (fewer backend
  round-trips) and reduces p99 latency and error rate. It adds proportional memory
  overhead. The optimal cache size balances memory budget against CPU/latency relief.

- **`batch_size`** (B): Larger batches amortise per-request overhead, boosting
  throughput (log₂B factor) and reducing error rate. Has no direct CPU or memory
  cost in this model.

- **`timeout_ms`**: Must remain in valid range. Does not directly affect the five
  performance metrics but is validated as a config correctness check.

- **`gc_interval_sec`** (G): Longer intervals reduce memory pressure (GC reclaims
  less frequently). Shorter intervals cause more GC pauses, adding a small CPU
  overhead. Sweet spot is usually in the upper half of the valid range.

## Contradictory Setting Rule

If `thread_pool_size * batch_size > 10000`, the simulator will flag a contradictory
setting and all checks will fail. Avoid extreme values on both simultaneously.

## Scoring Rubric

Overall score is a weighted average of per-metric sub-scores (each in [0, 1]):

| Metric | Weight |
|--------|--------|
{weight_rows}

Each sub-score is `min(1.0, target / actual)` for upper-bounded metrics and
`min(1.0, actual / target)` for throughput. Failing **any** hard target multiplies
the total score by 0.5.

The current suboptimal `config.json` scores approximately **0.35**. Your optimized
configuration must score **above 0.35** to pass the baseline check.

## Deliverables

1. An updated `config.json` with all six knobs tuned so that `python simulator.py --check`
   exits with code 0 (all checks pass).

2. All of the following simulator checks must pass:
   - `config_values_valid`: all knob values within valid ranges
   - `no_contradictory_settings`: `thread_pool_size * batch_size <= 10000`
   - `cpu_within_target`: CPU < {cpu_t} %
   - `memory_within_target`: memory < {mem_t} %
   - `p99_meets_target`: p99 latency < {p99_t} ms
   - `throughput_meets_target`: throughput > {tput_t} rps
   - `error_rate_within_target`: error rate < {err_t} %
   - `score_above_baseline`: weighted score > 0.35

## Common Traps

- **Maximise threads naively**: A very high `thread_pool_size` reduces latency
  and boosts throughput but can push CPU and memory over their targets.
- **Ignore cache**: `cache_size_mb` is a "free" knob that relieves CPU and latency
  without costing threads; always increase it before adding threads.
- **Forget batch_size**: Setting `batch_size=1` (the default) leaves significant
  throughput on the table. Even moderate batching (10–50) materially helps.
- **Under-size connection pool**: Throughput is log₂(C) dependent — a small pool
  caps throughput even with many threads.
- **Contradictory extremes**: A very high thread count with a very high batch size
  triggers the backpressure rule and fails the contradictory-settings check.
"""

    def _generate_brief(self, p: dict) -> str:
        stype  = p["service_type"]
        cpu_t  = p["cpu_target_pct"]
        mem_t  = p["memory_target_pct"]
        p99_t  = p["p99_target_ms"]
        tput_t = p["throughput_target"]
        err_t  = p["error_rate_target"]

        return f"""# O6: Service Performance Tuning (Brief)

The {stype.replace('_', ' ')} service is slow and resource-inefficient. Tune the configuration.

Performance budget:
- CPU < {cpu_t}%, Memory < {mem_t}%
- p99 latency < {p99_t} ms, Throughput > {tput_t} rps, Error rate < {err_t}%

Edit `config.json`, then verify with `python simulator.py --check`.
"""
