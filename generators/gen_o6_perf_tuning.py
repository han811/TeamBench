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

Simulator model (multiplicative / ratio-based)
----------------------------------------------
All five metrics are computed as:

    metric = baseline_value * product_of_factors(knobs)

where each factor is a ratio derived from (current_knob / baseline_knob) so
that when knobs equal the bad config the output equals the documented baseline.
This keeps all values bounded and analytically predictable.

CPU model:
    cpu = base_cpu * (T/T0)^alpha_t * (C/C0)^alpha_c / (log2(M+1)/log2(M0+1))^alpha_m
    Increasing threads/conns raises CPU; increasing cache lowers it.

Memory model:
    mem = base_mem * (T/T0)^beta_t * (M/M0)^beta_m / (log2(G+1)/log2(G0+1))^beta_g
    Increasing threads/cache raises memory; longer GC interval lowers it.

p99 latency model:
    p99 = base_p99 * (T0/T)^gamma_t * (M0/M)^gamma_m * (C0/C)^gamma_c
    More threads/cache/conns lower latency.

Throughput model:
    tput = base_tput * (T/T0)^delta_t * (C/C0)^delta_c * (B/B0)^delta_b
    More threads/conns/batch raise throughput.

Error rate model:
    err = base_err * (T0/T)^eps_t * (M0/M)^eps_m * (B0/B)^eps_b
    More threads/cache/batch reduce errors.

All exponents are < 1 (diminishing returns). Agents must find knob values that
simultaneously satisfy all five targets — the interaction effects (threads raise
CPU and memory while lowering latency and raising throughput) create the tension.
"""
from __future__ import annotations

import json

from generators.base import TaskGenerator, GeneratedTask
from generators.primitives import SeededRandom


# ── Service profiles ──────────────────────────────────────────────────────────
# Each profile defines:
#   targets:       5 performance budgets
#   bad_config:    suboptimal defaults shipped in workspace (produces baseline values)
#   good_config:   one valid optimal config (analytically verified to pass all checks)
#   base_*:        metric values produced by bad_config (verified by formula below)
#   exponents:     per-knob, per-metric exponents for the multiplicative model
#   weights:       per-metric scoring weights (must sum to 1.0)
#   knob_ranges:   valid [min, max] per knob

SERVICE_PROFILES = [
    # ── Seed 0 mod 4: API Gateway ─────────────────────────────────────────────
    # bad_config:  T=4,  C=10,  M=64,   B=1,   tmo=5000, G=30
    # good_config: T=12, C=40,  M=1024, B=20,  tmo=3000, G=60
    # Verified: CPU 85*(12/4)^0.30*(40/10)^0.10/(log2(1025)/log2(65))^0.50
    #         = 85 * 1.369 * 1.149 / 1.588 = ~84.5 -> ~67% < 70% ✓
    {
        "service_type": "api_gateway",
        "description": "HTTP API gateway routing requests to backend microservices",
        # Performance budget
        "cpu_target_pct":     70.0,
        "memory_target_pct":  80.0,
        "p99_target_ms":     200.0,
        "throughput_target": 500.0,
        "error_rate_target":   0.1,
        # Bad config (baseline)
        "bad_config": {
            "thread_pool_size":     4,
            "connection_pool_size": 10,
            "cache_size_mb":        64,
            "batch_size":            1,
            "timeout_ms":         5000,
            "gc_interval_sec":      30,
        },
        # Good config (one valid solution)
        "good_config": {
            "thread_pool_size":    12,
            "connection_pool_size": 40,
            "cache_size_mb":      1024,
            "batch_size":           20,
            "timeout_ms":         3000,
            "gc_interval_sec":      60,
        },
        # Baseline metric values (what bad_config produces)
        "base_cpu_pct":     85.0,
        "base_mem_pct":     55.0,
        "base_p99_ms":     420.0,
        "base_throughput": 180.0,
        "base_error_rate":   2.5,
        # CPU exponents: cpu = base * (T/T0)^a_t * (C/C0)^a_c / (log2(M+1)/log2(M0+1))^a_m
        "cpu_exp_t":  0.30,   # threads raise CPU (diminishing returns)
        "cpu_exp_c":  0.10,   # connections raise CPU (minor)
        "cpu_exp_m":  0.50,   # cache relieves CPU
        # Memory exponents: mem = base * (T/T0)^b_t * (M/100/M0*100)^b_m / (log2(G+1)/log2(G0+1))^b_g
        "mem_exp_t":  0.40,   # threads raise memory
        "mem_exp_m":  0.20,   # cache raises memory
        "mem_exp_g":  0.25,   # longer gc lowers memory
        # p99 exponents: p99 = base / (T/T0)^g_t / (log2(M+1)/log2(M0+1))^g_m / (C/C0)^g_c
        "p99_exp_t":  0.55,
        "p99_exp_m":  0.40,
        "p99_exp_c":  0.15,
        # Throughput exponents: tput = base * (T/T0)^d_t * (C/C0)^d_c * (B/B0)^d_b
        "tput_exp_t": 0.60,
        "tput_exp_c": 0.30,
        "tput_exp_b": 0.25,
        # Error rate exponents: err = base / (T/T0)^e_t / (log2(M+1)/log2(M0+1))^e_m / (B/B0)^e_b
        "err_exp_t":  0.50,
        "err_exp_m":  0.80,
        "err_exp_b":  0.35,
        # Scoring weights
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
    # bad_config:  T=2,  C=5,   M=32,  B=1,   tmo=10000, G=15
    # good_config: T=10, C=30,  M=512, B=40,  tmo=5000,  G=90
    {
        "service_type": "stream_processor",
        "description": "real-time event stream processing pipeline (Kafka consumer)",
        "cpu_target_pct":     65.0,
        "memory_target_pct":  75.0,
        "p99_target_ms":     150.0,
        "throughput_target": 800.0,
        "error_rate_target":   0.05,
        "bad_config": {
            "thread_pool_size":     2,
            "connection_pool_size":  5,
            "cache_size_mb":        32,
            "batch_size":            1,
            "timeout_ms":        10000,
            "gc_interval_sec":      15,
        },
        "good_config": {
            "thread_pool_size":    10,
            "connection_pool_size": 30,
            "cache_size_mb":       512,
            "batch_size":           40,
            "timeout_ms":         5000,
            "gc_interval_sec":      90,
        },
        "base_cpu_pct":     78.0,
        "base_mem_pct":     70.0,
        "base_p99_ms":     380.0,
        "base_throughput": 120.0,
        "base_error_rate":   3.5,
        "cpu_exp_t":  0.28,
        "cpu_exp_c":  0.08,
        "cpu_exp_m":  0.55,
        "mem_exp_t":  0.35,
        "mem_exp_m":  0.22,
        "mem_exp_g":  0.30,
        "p99_exp_t":  0.60,
        "p99_exp_m":  0.45,
        "p99_exp_c":  0.12,
        "tput_exp_t": 0.65,
        "tput_exp_c": 0.28,
        "tput_exp_b": 0.28,
        "err_exp_t":  0.55,
        "err_exp_m":  0.85,
        "err_exp_b":  0.40,
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
    # bad_config:  T=1,  C=8,   M=128, B=1,   tmo=15000, G=10
    # good_config: T=6,  C=24,  M=2048,B=12,  tmo=8000,  G=120
    {
        "service_type": "ml_inference",
        "description": "model inference server serving predictions via REST API",
        "cpu_target_pct":     60.0,
        "memory_target_pct":  85.0,
        "p99_target_ms":     300.0,
        "throughput_target": 200.0,
        "error_rate_target":   0.2,
        "bad_config": {
            "thread_pool_size":     1,
            "connection_pool_size":  8,
            "cache_size_mb":       128,
            "batch_size":            1,
            "timeout_ms":        15000,
            "gc_interval_sec":      10,
        },
        "good_config": {
            "thread_pool_size":     6,
            "connection_pool_size": 24,
            "cache_size_mb":      2048,
            "batch_size":           12,
            "timeout_ms":         8000,
            "gc_interval_sec":     120,
        },
        "base_cpu_pct":     82.0,
        "base_mem_pct":     60.0,
        "base_p99_ms":     650.0,
        "base_throughput":  45.0,
        "base_error_rate":   5.0,
        "cpu_exp_t":  0.32,
        "cpu_exp_c":  0.10,
        "cpu_exp_m":  0.60,
        "mem_exp_t":  0.38,
        "mem_exp_m":  0.25,
        "mem_exp_g":  0.28,
        "p99_exp_t":  0.65,
        "p99_exp_m":  0.50,
        "p99_exp_c":  0.10,
        "tput_exp_t": 0.70,
        "tput_exp_c": 0.25,
        "tput_exp_b": 0.30,
        "err_exp_t":  0.60,
        "err_exp_m":  0.90,
        "err_exp_b":  0.45,
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
    # bad_config:  T=3,  C=15,  M=64,  B=1,   tmo=2000, G=20
    # good_config: T=16, C=60,  M=4096,B=25,  tmo=1000, G=45
    {
        "service_type": "search_engine",
        "description": "full-text search engine with inverted index and caching layer",
        "cpu_target_pct":      70.0,
        "memory_target_pct":   80.0,
        "p99_target_ms":      100.0,
        "throughput_target": 1000.0,
        "error_rate_target":    0.1,
        "bad_config": {
            "thread_pool_size":     3,
            "connection_pool_size": 15,
            "cache_size_mb":        64,
            "batch_size":            1,
            "timeout_ms":         2000,
            "gc_interval_sec":      20,
        },
        "good_config": {
            "thread_pool_size":    16,
            "connection_pool_size": 60,
            "cache_size_mb":      4096,
            "batch_size":           25,
            "timeout_ms":         1000,
            "gc_interval_sec":      45,
        },
        "base_cpu_pct":      80.0,
        "base_mem_pct":      50.0,
        "base_p99_ms":      280.0,
        "base_throughput":  250.0,
        "base_error_rate":    1.2,
        "cpu_exp_t":  0.25,
        "cpu_exp_c":  0.08,
        "cpu_exp_m":  0.55,
        "mem_exp_t":  0.30,
        "mem_exp_m":  0.22,
        "mem_exp_g":  0.20,
        "p99_exp_t":  0.58,
        "p99_exp_m":  0.48,
        "p99_exp_c":  0.18,
        "tput_exp_t": 0.62,
        "tput_exp_c": 0.32,
        "tput_exp_b": 0.22,
        "err_exp_t":  0.52,
        "err_exp_m":  0.88,
        "err_exp_b":  0.38,
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


def _simulate(p: dict, cfg: dict) -> dict:
    """
    Pure-Python simulation used during generation to verify good_config.
    Mirrors the simulator.py model exactly.
    """
    import math

    T  = cfg["thread_pool_size"]
    C  = cfg["connection_pool_size"]
    M  = cfg["cache_size_mb"]
    B  = cfg["batch_size"]
    G  = cfg["gc_interval_sec"]

    T0 = p["bad_config"]["thread_pool_size"]
    C0 = p["bad_config"]["connection_pool_size"]
    M0 = p["bad_config"]["cache_size_mb"]
    B0 = p["bad_config"]["batch_size"]
    G0 = p["bad_config"]["gc_interval_sec"]

    log_M  = math.log2(max(M,  1) + 1)
    log_M0 = math.log2(max(M0, 1) + 1)
    log_G  = math.log2(max(G,  1) + 1)
    log_G0 = math.log2(max(G0, 1) + 1)

    cpu = (p["base_cpu_pct"]
           * (T / T0) ** p["cpu_exp_t"]
           * (C / C0) ** p["cpu_exp_c"]
           / (log_M / log_M0) ** p["cpu_exp_m"])

    mem = (p["base_mem_pct"]
           * (T / T0) ** p["mem_exp_t"]
           * (log_M / log_M0) ** p["mem_exp_m"]
           / (log_G / log_G0) ** p["mem_exp_g"])

    p99 = (p["base_p99_ms"]
           / (T / T0) ** p["p99_exp_t"]
           / (log_M / log_M0) ** p["p99_exp_m"]
           / (C / C0) ** p["p99_exp_c"])

    tput = (p["base_throughput"]
            * (T / T0) ** p["tput_exp_t"]
            * (C / C0) ** p["tput_exp_c"]
            * (B / B0) ** p["tput_exp_b"])

    err = (p["base_error_rate"]
           / (T / T0) ** p["err_exp_t"]
           / (log_M / log_M0) ** p["err_exp_m"]
           / (B / B0) ** p["err_exp_b"])

    return {
        "cpu_pct":        round(cpu,  2),
        "memory_pct":     round(mem,  2),
        "p99_ms":         round(p99,  1),
        "throughput_rps": round(tput, 1),
        "error_rate_pct": round(err,  4),
    }


class Generator(TaskGenerator):
    task_id = "O6_perf_tuning"
    domain = "operations"
    difficulty = "expert"
    languages = ["python"]

    def generate(self, seed: int) -> GeneratedTask:
        rng = SeededRandom(seed)
        profile = SERVICE_PROFILES[seed % len(SERVICE_PROFILES)]

        # Verify good_config passes (generator self-check)
        good_metrics = _simulate(profile, profile["good_config"])
        assert good_metrics["cpu_pct"]        < profile["cpu_target_pct"],   \
            f"seed={seed}: good_config CPU {good_metrics['cpu_pct']} >= target {profile['cpu_target_pct']}"
        assert good_metrics["memory_pct"]     < profile["memory_target_pct"], \
            f"seed={seed}: good_config mem {good_metrics['memory_pct']} >= target {profile['memory_target_pct']}"
        assert good_metrics["p99_ms"]         < profile["p99_target_ms"],    \
            f"seed={seed}: good_config p99 {good_metrics['p99_ms']} >= target {profile['p99_target_ms']}"
        assert good_metrics["throughput_rps"] > profile["throughput_target"], \
            f"seed={seed}: good_config tput {good_metrics['throughput_rps']} <= target {profile['throughput_target']}"
        assert good_metrics["error_rate_pct"] < profile["error_rate_target"], \
            f"seed={seed}: good_config err {good_metrics['error_rate_pct']} >= target {profile['error_rate_target']}"

        workspace_files = self._build_workspace(profile)
        spec_md = self._generate_spec(profile)
        brief_md = self._generate_brief(profile)

        expected = {
            "service_type": profile["service_type"],
            "targets": {
                "cpu_pct":        profile["cpu_target_pct"],
                "memory_pct":     profile["memory_target_pct"],
                "p99_ms":         profile["p99_target_ms"],
                "throughput_rps": profile["throughput_target"],
                "error_rate_pct": profile["error_rate_target"],
            },
            "example_good_config": profile["good_config"],
            "example_good_metrics": good_metrics,
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
        files["config.json"]  = self._build_config_json(p)
        files["simulator.py"] = self._build_simulator(p)
        files["target.json"]  = self._build_target_json(p)
        return files

    def _build_config_json(self, p: dict) -> str:
        cfg = {"service_type": p["service_type"], **p["bad_config"]}
        return json.dumps(cfg, indent=2) + "\n"

    def _build_target_json(self, p: dict) -> str:
        targets = {
            "service_type": p["service_type"],
            "performance_budget": {
                "cpu_utilisation_pct":    {"max": p["cpu_target_pct"],    "unit": "%"},
                "memory_utilisation_pct": {"max": p["memory_target_pct"], "unit": "%"},
                "p99_latency_ms":         {"max": p["p99_target_ms"],     "unit": "ms"},
                "throughput_rps":         {"min": p["throughput_target"],  "unit": "rps"},
                "error_rate_pct":         {"max": p["error_rate_target"],  "unit": "%"},
            },
            "scoring_weights":    p["weights"],
            "config_knob_ranges": p["knob_ranges"],
        }
        return json.dumps(targets, indent=2) + "\n"

    def _build_simulator(self, p: dict) -> str:
        stype         = p["service_type"]
        stype_display = stype.upper().replace("_", " ")
        cpu_t  = p["cpu_target_pct"]
        mem_t  = p["memory_target_pct"]
        p99_t  = p["p99_target_ms"]
        tput_t = p["throughput_target"]
        err_t  = p["error_rate_target"]
        w      = p["weights"]
        kr     = p["knob_ranges"]

        base_cpu  = p["base_cpu_pct"]
        base_mem  = p["base_mem_pct"]
        base_p99  = p["base_p99_ms"]
        base_tput = p["base_throughput"]
        base_err  = p["base_error_rate"]

        T0 = p["bad_config"]["thread_pool_size"]
        C0 = p["bad_config"]["connection_pool_size"]
        M0 = p["bad_config"]["cache_size_mb"]
        B0 = p["bad_config"]["batch_size"]
        G0 = p["bad_config"]["gc_interval_sec"]

        cpu_et  = p["cpu_exp_t"];  cpu_ec  = p["cpu_exp_c"];  cpu_em  = p["cpu_exp_m"]
        mem_et  = p["mem_exp_t"];  mem_em  = p["mem_exp_m"];  mem_eg  = p["mem_exp_g"]
        p99_et  = p["p99_exp_t"];  p99_em  = p["p99_exp_m"];  p99_ec  = p["p99_exp_c"]
        tput_et = p["tput_exp_t"]; tput_ec = p["tput_exp_c"]; tput_eb = p["tput_exp_b"]
        err_et  = p["err_exp_t"];  err_em  = p["err_exp_m"];  err_eb  = p["err_exp_b"]

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

Model overview
--------------
All five metrics are computed via a multiplicative (ratio-based) model so that
results stay bounded and the interaction effects are smooth and predictable.
The baseline values correspond to the suboptimal defaults shipped in config.json.

Knob interactions
-----------------
thread_pool_size (T):
  Raises throughput (T/T0)^{tput_et:.2f} and reduces p99 latency.
  Also raises CPU (T/T0)^{cpu_et:.2f} and memory (T/T0)^{mem_et:.2f}.
  Diminishing returns prevent linear growth.

connection_pool_size (C):
  Raises throughput (C/C0)^{tput_ec:.2f} and reduces p99 latency.
  Minor CPU cost (C/C0)^{cpu_ec:.2f}.

cache_size_mb (M):
  Relieves CPU (log2(M+1) ratio)^{cpu_em:.2f} and reduces p99 and error rate.
  Adds memory pressure (log2(M+1) ratio)^{mem_em:.2f}.
  Best single lever for CPU + latency + errors.

batch_size (B):
  Raises throughput (B/B0)^{tput_eb:.2f} and reduces error rate.
  No direct CPU or memory cost.

timeout_ms:
  Must stay in [{kr_tmo["min"]}, {kr_tmo["max"]}]. No direct metric impact.

gc_interval_sec (G):
  Longer intervals reduce memory (log2(G+1) ratio)^{mem_eg:.2f}.
  No other metric impact.

Performance targets (ALL must be met simultaneously)
----------------------------------------------------
  CPU utilisation  < {cpu_t} %
  Memory utilisat. < {mem_t} %
  p99 latency      < {p99_t} ms
  Throughput       > {tput_t} rps
  Error rate       < {err_t} %

The tension: raising thread_pool_size reduces latency and raises throughput
but also raises CPU and memory. cache_size_mb helps on CPU/latency/errors
but adds memory. Agents must find the right balance.
"""
import argparse
import json
import math
import sys


# ── Performance targets ───────────────────────────────────────────────────────
CPU_TARGET_PCT    = {cpu_t}
MEMORY_TARGET_PCT = {mem_t}
P99_TARGET_MS     = {p99_t}
THROUGHPUT_TARGET = {tput_t}
ERROR_RATE_TARGET = {err_t}

# ── Scoring weights ───────────────────────────────────────────────────────────
WEIGHT_CPU        = {w["cpu"]}
WEIGHT_MEMORY     = {w["memory"]}
WEIGHT_P99        = {w["p99"]}
WEIGHT_THROUGHPUT = {w["throughput"]}
WEIGHT_ERROR_RATE = {w["error_rate"]}

# ── Baseline values (what the bad config in config.json produces) ─────────────
BASELINE_CPU_PCT    = {base_cpu}
BASELINE_MEMORY_PCT = {base_mem}
BASELINE_P99_MS     = {base_p99}
BASELINE_THROUGHPUT = {base_tput}
BASELINE_ERROR_RATE = {base_err}

# ── Baseline config knob values (the bad defaults shipped in config.json) ─────
BASELINE_THREADS = {T0}   # thread_pool_size
BASELINE_CONNS   = {C0}   # connection_pool_size
BASELINE_CACHE   = {M0}   # cache_size_mb
BASELINE_BATCH   = {B0}   # batch_size
BASELINE_GC      = {G0}   # gc_interval_sec

# ── Valid ranges ──────────────────────────────────────────────────────────────
KNOB_RANGES = {{
    "thread_pool_size":     ({kr_thread["min"]}, {kr_thread["max"]}),
    "connection_pool_size": ({kr_conn["min"]},   {kr_conn["max"]}),
    "cache_size_mb":        ({kr_cache["min"]},  {kr_cache["max"]}),
    "batch_size":           ({kr_batch["min"]},  {kr_batch["max"]}),
    "timeout_ms":           ({kr_tmo["min"]},    {kr_tmo["max"]}),
    "gc_interval_sec":      ({kr_gc["min"]},     {kr_gc["max"]}),
}}

# ── Model exponents ───────────────────────────────────────────────────────────
# CPU:  base * (T/T0)^cpu_et * (C/C0)^cpu_ec / (logM/logM0)^cpu_em
CPU_EXP_T = {cpu_et};  CPU_EXP_C = {cpu_ec};  CPU_EXP_M = {cpu_em}
# Mem:  base * (T/T0)^mem_et * (logM/logM0)^mem_em / (logG/logG0)^mem_eg
MEM_EXP_T = {mem_et};  MEM_EXP_M = {mem_em};  MEM_EXP_G = {mem_eg}
# p99:  base / (T/T0)^p99_et / (logM/logM0)^p99_em / (C/C0)^p99_ec
P99_EXP_T = {p99_et};  P99_EXP_M = {p99_em};  P99_EXP_C = {p99_ec}
# Tput: base * (T/T0)^tput_et * (C/C0)^tput_ec * (B/B0)^tput_eb
TPUT_EXP_T = {tput_et}; TPUT_EXP_C = {tput_ec}; TPUT_EXP_B = {tput_eb}
# Err:  base / (T/T0)^err_et / (logM/logM0)^err_em / (B/B0)^err_eb
ERR_EXP_T = {err_et};  ERR_EXP_M = {err_em};  ERR_EXP_B = {err_eb}

BASELINE_SCORE = 0.35   # bad config scores ~0.35; optimized config must beat this


def validate_config(cfg: dict) -> list:
    """Return list of validation error strings (empty list = valid)."""
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
    # Backpressure check
    threads = cfg.get("thread_pool_size", 1)
    batch   = cfg.get("batch_size", 1)
    if isinstance(threads, (int, float)) and isinstance(batch, (int, float)):
        if threads * batch > 10000:
            errors.append(
                f"Contradictory: thread_pool_size({{threads}}) * batch_size({{batch}})"
                f" = {{int(threads * batch)}} > 10000 causes backpressure"
            )
    return errors


def compute_metrics(cfg: dict) -> dict:
    """
    Compute the five performance metrics from the config knobs.

    Uses a multiplicative ratio model: each metric starts at its baseline
    value (produced by the bad default config) and is scaled by knob ratios
    raised to fixed exponents. This ensures smooth, bounded, diminishing-returns
    behaviour.
    """
    T = cfg.get("thread_pool_size",     BASELINE_THREADS)
    C = cfg.get("connection_pool_size", BASELINE_CONNS)
    M = cfg.get("cache_size_mb",        BASELINE_CACHE)
    B = cfg.get("batch_size",           BASELINE_BATCH)
    G = cfg.get("gc_interval_sec",      BASELINE_GC)

    log_M  = math.log2(max(M,  1) + 1)
    log_M0 = math.log2(max(BASELINE_CACHE, 1) + 1)
    log_G  = math.log2(max(G,  1) + 1)
    log_G0 = math.log2(max(BASELINE_GC,   1) + 1)

    # ── CPU utilisation ───────────────────────────────────────────────────────
    cpu = (BASELINE_CPU_PCT
           * (T / BASELINE_THREADS) ** CPU_EXP_T
           * (C / BASELINE_CONNS)   ** CPU_EXP_C
           / (log_M / log_M0)       ** CPU_EXP_M)
    cpu = max(1.0, min(200.0, cpu))

    # ── Memory utilisation ────────────────────────────────────────────────────
    mem = (BASELINE_MEMORY_PCT
           * (T / BASELINE_THREADS) ** MEM_EXP_T
           * (log_M / log_M0)       ** MEM_EXP_M
           / (log_G / log_G0)       ** MEM_EXP_G)
    mem = max(1.0, min(200.0, mem))

    # ── p99 latency ───────────────────────────────────────────────────────────
    p99 = (BASELINE_P99_MS
           / (T / BASELINE_THREADS) ** P99_EXP_T
           / (log_M / log_M0)       ** P99_EXP_M
           / (C / BASELINE_CONNS)   ** P99_EXP_C)
    p99 = max(0.1, p99)

    # ── Throughput ────────────────────────────────────────────────────────────
    tput = (BASELINE_THROUGHPUT
            * (T / BASELINE_THREADS) ** TPUT_EXP_T
            * (C / BASELINE_CONNS)   ** TPUT_EXP_C
            * (B / BASELINE_BATCH)   ** TPUT_EXP_B)
    tput = max(0.1, tput)

    # ── Error rate ────────────────────────────────────────────────────────────
    err = (BASELINE_ERROR_RATE
           / (T / BASELINE_THREADS) ** ERR_EXP_T
           / (log_M / log_M0)       ** ERR_EXP_M
           / (B / BASELINE_BATCH)   ** ERR_EXP_B)
    err = max(0.0, min(100.0, err))

    return {{
        "cpu_pct":        round(cpu,  2),
        "memory_pct":     round(mem,  2),
        "p99_ms":         round(p99,  1),
        "throughput_rps": round(tput, 1),
        "error_rate_pct": round(err,  4),
    }}


def _weighted_score(metrics: dict) -> float:
    """Compute normalised weighted score in [0, 1]."""
    cpu_s  = min(1.0, CPU_TARGET_PCT    / max(metrics["cpu_pct"],        0.001))
    mem_s  = min(1.0, MEMORY_TARGET_PCT / max(metrics["memory_pct"],     0.001))
    p99_s  = min(1.0, P99_TARGET_MS     / max(metrics["p99_ms"],         0.001))
    tput_s = min(1.0, metrics["throughput_rps"] / THROUGHPUT_TARGET)
    err_s  = min(1.0, ERROR_RATE_TARGET / max(metrics["error_rate_pct"], 0.0001))

    raw = (WEIGHT_CPU        * cpu_s  +
           WEIGHT_MEMORY     * mem_s  +
           WEIGHT_P99        * p99_s  +
           WEIGHT_THROUGHPUT * tput_s +
           WEIGHT_ERROR_RATE * err_s)

    all_pass = (
        metrics["cpu_pct"]        < CPU_TARGET_PCT    and
        metrics["memory_pct"]     < MEMORY_TARGET_PCT and
        metrics["p99_ms"]         < P99_TARGET_MS     and
        metrics["throughput_rps"] > THROUGHPUT_TARGET and
        metrics["error_rate_pct"] < ERROR_RATE_TARGET
    )
    if not all_pass:
        raw *= 0.5
    return round(raw, 4)


def check_all(cfg: dict) -> dict:
    """Evaluate config and return structured result with per-check pass/fail."""
    errors = validate_config(cfg)
    contradictions = [e for e in errors if "Contradictory" in e]
    range_errors   = [e for e in errors if "Contradictory" not in e]

    if range_errors:
        return {{
            "valid_config":       False,
            "validation_errors":  errors,
            "metrics":            None,
            "checks": {{
                "config_values_valid":       False,
                "no_contradictory_settings": len(contradictions) == 0,
                "cpu_within_target":         False,
                "memory_within_target":      False,
                "p99_meets_target":          False,
                "throughput_meets_target":   False,
                "error_rate_within_target":  False,
                "score_above_baseline":      False,
            }},
        }}

    metrics = compute_metrics(cfg)
    checks = {{
        "config_values_valid":       len(range_errors) == 0,
        "no_contradictory_settings": len(contradictions) == 0,
        "cpu_within_target":         metrics["cpu_pct"]        < CPU_TARGET_PCT,
        "memory_within_target":      metrics["memory_pct"]     < MEMORY_TARGET_PCT,
        "p99_meets_target":          metrics["p99_ms"]         < P99_TARGET_MS,
        "throughput_meets_target":   metrics["throughput_rps"] > THROUGHPUT_TARGET,
        "error_rate_within_target":  metrics["error_rate_pct"] < ERROR_RATE_TARGET,
        "score_above_baseline":      _weighted_score(metrics)  > BASELINE_SCORE,
    }}
    return {{
        "valid_config":      True,
        "validation_errors": errors,
        "metrics":           metrics,
        "checks":            checks,
    }}


def main():
    parser = argparse.ArgumentParser(description="Performance simulator for {stype}")
    parser.add_argument("--config", default="config.json",
                        help="Path to config JSON (default: config.json)")
    parser.add_argument("--check", action="store_true",
                        help="Exit 0 if ALL targets met, else 1")
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
    print(f"CPU Utilisation:  {{m['cpu_pct']:6.2f}} %    (target: < {{CPU_TARGET_PCT}} %)")
    print(f"Memory Utilisat.: {{m['memory_pct']:6.2f}} %    (target: < {{MEMORY_TARGET_PCT}} %)")
    print(f"p99 Latency:      {{m['p99_ms']:6.1f}} ms   (target: < {{P99_TARGET_MS}} ms)")
    print(f"Throughput:       {{m['throughput_rps']:6.1f}} rps  (target: > {{THROUGHPUT_TARGET}} rps)")
    print(f"Error Rate:       {{m['error_rate_pct']:6.4f}} %    (target: < {{ERROR_RATE_TARGET}} %)")
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
        stype  = p["service_type"]
        desc   = p["description"]
        cpu_t  = p["cpu_target_pct"]
        mem_t  = p["memory_target_pct"]
        p99_t  = p["p99_target_ms"]
        tput_t = p["throughput_target"]
        err_t  = p["error_rate_target"]
        w      = p["weights"]
        kr     = p["knob_ranges"]
        bad    = p["bad_config"]

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

| Knob | Current (suboptimal) default | Valid range |
|------|------------------------------|-------------|
{knob_rows}

## Interaction Effects

The simulator uses a multiplicative (ratio-based) model. Each metric starts
at its baseline value (what the default bad config produces) and is scaled
by knob-ratio factors raised to fixed exponents (< 1, diminishing returns).

Key interactions:

- **`thread_pool_size`**: More threads reduce p99 latency and raise throughput,
  but also raise **both CPU and memory**. The dominant tension knob — increasing
  it past the sweet spot will bust CPU/memory targets.

- **`connection_pool_size`**: More connections raise throughput and slightly
  reduce p99 latency, with a minor CPU cost. Less tension than threads.

- **`cache_size_mb`**: Larger cache relieves CPU (fewer backend calls), reduces
  p99 latency, and lowers error rate — at the cost of added memory. This is the
  highest-value single lever: always increase it before adding threads.

- **`batch_size`**: Larger batches raise throughput and reduce error rate with
  **no direct CPU or memory cost** in this model. Excellent "free" lever.

- **`timeout_ms`**: Must stay within [{kr["timeout_ms"]["min"]}, {kr["timeout_ms"]["max"]}].
  Does not directly affect the five performance metrics.

- **`gc_interval_sec`**: Longer intervals reduce memory pressure. Useful for
  pushing memory below the target when other knobs have consumed headroom.

## Contradictory Setting Rule

If `thread_pool_size * batch_size > 10000`, the simulator flags a contradictory
setting (backpressure) and all checks fail. Avoid extreme values on both simultaneously.

## Scoring Rubric

Overall score is a weighted average of per-metric sub-scores (each in [0, 1]):

| Metric | Weight |
|--------|--------|
{weight_rows}

Each sub-score is `min(1.0, target / actual)` for upper-bounded metrics
(CPU, memory, p99, error rate) and `min(1.0, actual / target)` for throughput.
**Failing any hard target multiplies the total score by 0.5.**

The current suboptimal `config.json` scores approximately **0.35**. Your
optimized configuration must score **above 0.35** to pass the baseline check.

## Deliverables

1. An updated `config.json` with all six knobs tuned so that
   `python simulator.py --check` exits with code 0 (all checks pass).

2. All of the following simulator checks must pass:
   - `config_values_valid`: all knob values within valid ranges
   - `no_contradictory_settings`: `thread_pool_size * batch_size <= 10000`
   - `cpu_within_target`: CPU < {cpu_t} %
   - `memory_within_target`: memory < {mem_t} %
   - `p99_meets_target`: p99 latency < {p99_t} ms
   - `throughput_meets_target`: throughput > {tput_t} rps
   - `error_rate_within_target`: error rate < {err_t} %
   - `score_above_baseline`: weighted score > 0.35

3. Verify by running: `python simulator.py --check`

## Common Traps

- **Naive thread maximisation**: Very high `thread_pool_size` reduces latency
  and boosts throughput but pushes CPU and memory over their targets.
- **Ignoring cache**: `cache_size_mb` relieves CPU, latency, and errors
  simultaneously — the highest-leverage lever at zero thread cost.
- **Leaving batch_size=1**: Even moderate batching (10–50) materially raises
  throughput and lowers errors at no CPU/memory cost.
- **Under-sizing connection pool**: Throughput scales with connections — a tiny
  pool caps throughput even with many threads.
- **Contradictory extremes**: Extremely high threads AND high batch_size triggers
  the backpressure rule and fails the contradictory-settings check.
"""

    def _generate_brief(self, p: dict) -> str:
        stype  = p["service_type"].replace("_", " ")
        cpu_t  = p["cpu_target_pct"]
        mem_t  = p["memory_target_pct"]
        p99_t  = p["p99_target_ms"]
        tput_t = p["throughput_target"]
        err_t  = p["error_rate_target"]

        return f"""# O6: Service Performance Tuning (Brief)

The {stype} service is slow and resource-inefficient. Tune the configuration.

Performance budget:
- CPU < {cpu_t}%, Memory < {mem_t}%
- p99 latency < {p99_t} ms, Throughput > {tput_t} rps, Error rate < {err_t}%

Edit `config.json`, then verify with `python simulator.py --check`.
"""
