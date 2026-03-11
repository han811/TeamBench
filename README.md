# TeamBench: Evaluating Structured LLM Teamwork via OS-Enforced Role Separation

A multi-domain benchmark that evaluates whether LLM agent teams can collaborate effectively under hard, OS-level role constraints -- not prompt-based honor systems.

---

## Overview

Most multi-agent benchmarks rely on prompt instructions to separate agent roles. TeamBench removes that loophole: roles are enforced by **Docker bind mounts and file-system permissions**. No single agent can simultaneously read the full specification, write to the workspace, and submit verification. Genuine coordination is structurally required.

**Key stats**

| Property | Value |
|---|---|
| Tasks | 155 |
| Categories | 19 |
| Seeded instances | 465 (seeds 0, 1, 2) |
| Ablation conditions | 5 |
| Supported model families | OpenAI, Anthropic, Google, HuggingFace |
| Enforcement mechanism | Docker bind mounts (OS-level) |

---

## Role Separation

Three roles operate in isolated containers. Each container has a strictly scoped filesystem view:

```
+------------------+       +------------------+       +------------------+
|     PLANNER      |       |     EXECUTOR     |       |    VERIFIER      |
|                  |  -->  |                  |  -->  |                  |
| Reads: spec.md   |  msg  | Reads: brief.md  |  msg  | Reads: spec.md   |
|        brief.md  |       |        workspace |       |        workspace |
| Writes: messages |       |        messages  |       |        (read-only)|
| Executes: No     |       | Writes: workspace|       | Writes:          |
|                  |       |         messages |       |  attestation.json|
|                  |       | Executes: Yes    |       | Executes: No     |
+------------------+       +------------------+       +------------------+
       |                          |                          |
       |    Docker bind mounts enforce every boundary        |
       +---------------------------------------------------->+
```

| Role | Reads | Writes | Executes |
|---|---|---|---|
| Planner | spec.md, brief.md, messages | messages | No |
| Executor | brief.md, workspace, messages | workspace, messages | Yes |
| Verifier | spec.md, workspace (read-only), messages | attestation.json | No |

A missing `attestation.json` is an automatic failure. The Verifier must participate -- it cannot be bypassed.

---

## Teamwork Necessity Index (TNI)

Five ablation conditions quantify the value of each architectural component:

| Condition | Description | Purpose |
|---|---|---|
| Oracle | Single agent, full access | Upper bound |
| Restricted | Single agent, executor-only access | Lower bound |
| Team-NoPlan | Executor + Verifier only | Measures planning value |
| Team-NoVerify | Planner + Executor only | Measures verification value |
| Full | Planner + Executor + Verifier | Full team |

TNI is derived from these conditions:

```
TNI = (S_team - S_restricted) / max(epsilon, S_oracle - S_restricted)
```

| TNI | Interpretation |
|---|---|
| ~1.0 | Teamwork fully recovers the oracle-restricted gap |
| ~0.5 | Teamwork substantially helps |
| ~0.0 | Teamwork provides no benefit over restricted access |
| < 0 | Teamwork is harmful |

Across 155 tasks, the average TNI is **0.744**. Team outperforms Oracle on **43.9% of tasks**.

---

## Task Distribution

19 categories spanning security, data engineering, incident response, distributed systems, and more:

| Category | Tasks | Difficulty |
|---|---|---|
| Security (SEC) | 15 | medium -- expert |
| Data Engineering (DATA) | 11 | medium -- expert |
| Incident Response (INC) | 11 | medium -- expert |
| Software Engineering (SWE) | 11 | medium -- expert |
| Long-Horizon (LH) | 9 | hard -- expert |
| Multi-language (MULTI) | 9 | hard |
| Operations (OPS) | 9 | medium -- hard |
| Pipeline/Integration (PIPE) | 9 | medium -- hard |
| Testing (TEST) | 9 | medium -- hard |
| Adversarial (TRAP) | 8 | hard -- expert |
| Policy/Compliance (POL) | 8 | medium -- hard |
| Cross-Codebase (CROSS) | 7 | hard -- expert |
| Information Retrieval (IR) | 7 | easy -- hard |
| Specification (SPEC) | 7 | medium -- hard |
| Code Review (CR) | 6 | easy -- hard |
| Distributed Systems (DIST) | 6 | hard -- expert |
| Expertise Asymmetry (EA) | 5 | hard |
| Negotiation (NEG) | 5 | hard |
| Cryptographic Correctness (CRYPTO) | 5 | hard -- expert |

**Difficulty distribution**: 103 hard, 26 medium, 16 expert, 7 easy (155 tasks total).

---

## Installation

```bash
pip install teambench
```

Backend SDKs are optional extras -- install only what you need:

```bash
pip install "teambench[openai]"      # OpenAI / GPT / o-series
pip install "teambench[anthropic]"   # Anthropic / Claude
pip install "teambench[gemini]"      # Google / Gemini
pip install "teambench[all]"         # All three backends
```

Docker is required for OS-enforced role separation:

```bash
# Install Docker from https://docs.docker.com/get-docker/
docker compose build
```

---

## Quick Start

### Run a single task

```bash
export OPENAI_API_KEY=sk-...

# Run one task, seed 0, full-team condition
teambench run --model gpt-4o --tasks S1_hidden_spec --seeds 0 --conditions full

# Grade the result
teambench grade --task S1_hidden_spec --run-dir shared/runs/S1_hidden_spec/latest
```

### Run the full benchmark

```bash
export GEMINI_API_KEY=...

teambench run --model gemini-3-flash-preview
```

This runs all 155 tasks across seeds 0, 1, 2 and all 5 ablation conditions. Results are written to `shared/leaderboard/`.

### Explore tasks

```bash
# List all tasks
teambench list-tasks

# Filter by category and difficulty
teambench list-tasks --category SEC --difficulty hard

# Show metadata for one task
teambench info --task CRYPTO1_nonce_reuse

# Validate generator determinism and cross-seed uniqueness
teambench validate --task S1_hidden_spec --seeds 0 1 2
```

### Generate a task instance

```bash
teambench generate --task D1_schema_drift --seed 2 --output-dir /tmp/d1_seed2
```

### Submit results to the leaderboard

```bash
# Validate your result file
teambench submit shared/leaderboard/leaderboard_gpt-4o.json
```

Follow the printed instructions to open a pull request. Scores are server-side verified -- not self-reported.

---

## Supported Models

TeamBench selects a backend adapter automatically based on the model name prefix:

| Model family | Prefix | Environment variable | Install extra |
|---|---|---|---|
| OpenAI GPT / o-series | `gpt-*`, `o1`, `o3`, `o4` | `OPENAI_API_KEY` | `teambench[openai]` |
| Anthropic Claude | `claude-*` | `ANTHROPIC_API_KEY` | `teambench[anthropic]` |
| Google Gemini | `gemini-*` | `GEMINI_API_KEY` | `teambench[gemini]` |
| HuggingFace / OpenAI-compatible | any | `OPENAI_API_KEY` + `--base-url` | `teambench[openai]` |
| Mock (local testing) | `mock*` | (none) | (built-in) |

Any OpenAI-compatible endpoint (vLLM, Ollama, Together AI, etc.) works via the OpenAI adapter with a custom base URL.

Bring your own model by implementing the `ToolCallAdapter` interface:

```python
from harness.agent_interface import ToolCallAdapter, AdapterResponse

class MyAdapter(ToolCallAdapter):
    def generate_with_tools(self, messages, system_prompt, tools) -> AdapterResponse:
        # Call your model, return text + tool_calls
        ...
    def get_usage(self) -> dict:
        return {"input_tokens": ..., "output_tokens": ..., "total_tokens": ...}
```

---

## Contamination Resistance

Every task has a parameterized generator. Different seeds produce distinct workspace files and correct answers; the same seed always reproduces identically:

```python
from generators.registry import get_generator

gen = get_generator("P1_policy_config")

# Seed 0: rate_limit=180, timeout=30, auth=jwt
r0 = gen.generate(seed=0)

# Seed 1: rate_limit=95, timeout=60, auth=saml -- different correct answer
r1 = gen.generate(seed=1)

# Deterministic: same seed, same output
assert gen.generate(seed=0).expected == r0.expected
```

155 generators produce 465 instances across seeds [0, 1, 2]. Arbitrary additional seeds are supported for holdout evaluation.

---

## Repository Structure

```
TeamBench/
  harness/
    cli.py               # teambench CLI entry point
    run_agent.py         # Single-run driver
    run_all.py           # Batch runner
    orchestrator.py      # 3-phase protocol: Plan -> Execute -> Verify
    agent_loop.py        # Tool-calling loop with stuck detection
    agent_interface.py   # ToolCallAdapter ABC, role configs, tools
    ablation.py          # 5-condition ablation framework
    compute_tni.py       # TNI computation and reporting
    paper_tables.py      # LaTeX table generation
    benchmark_stats.py   # Task distribution analysis
    adapters/
      __init__.py        # create_adapter() factory
      openai_adapter.py  # GPT / o-series adapter
      anthropic_adapter.py  # Claude adapter
      mock_adapter.py    # Deterministic mock for testing
    gemini_adapter.py    # Gemini adapter
  generators/
    base.py              # TaskGenerator ABC, GeneratedTask dataclass
    primitives.py        # SeededRandom, NamePool, ValuePool
    registry.py          # Auto-discovery of gen_*.py generators
    gen_*.py             # 155 parameterized generators (one per task)
  tasks/
    {TASK_ID}/
      task.yaml          # Metadata (domain, difficulty, languages, tags)
      spec.md            # Full specification (Planner + Verifier access)
      brief.md           # Summary (Executor access only)
      setup.sh           # Workspace preparation
      grade.sh           # Deterministic grader -> score.json
      workspace/         # Initial (buggy) code and data
      corpus/            # Offline documents (IR and policy tasks)
  leaderboard/
    schema.json          # Submission format specification
    aggregate.py         # Aggregation with dimensional breakdowns
  docker-compose.yml     # 3-container sandbox (Planner / Executor / Verifier)
  images/
    planner/Dockerfile
    executor/Dockerfile
    verifier/Dockerfile
```

---

## Leaderboard

Results are publicly tracked at:

**https://huggingface.co/spaces/ybkim95/teambench-leaderboard**

Submissions are server-side graded using held-out seeds. To submit:

1. Run the benchmark: `teambench run --model <your-model>`
2. Validate the result file: `teambench submit shared/leaderboard/leaderboard_<model>.json`
3. Open a pull request placing the file at `shared/submissions/<model>.json`
4. CI runs the grader on held-out seeds and updates the leaderboard automatically.

Scores on the public leaderboard are not self-reported. All submissions are re-evaluated server-side.

---

## Citation

```bibtex
@article{kim2026teambench,
  title     = {TeamBench: Evaluating Structured LLM Teamwork via OS-Enforced Role Separation},
  author    = {Kim, Yubin},
  year      = {2026},
  url       = {https://github.com/ybkim95/TeamBench},
  note      = {https://huggingface.co/spaces/ybkim95/teambench-leaderboard}
}
```

---

## License

MIT License. See [LICENSE](LICENSE) for details.
