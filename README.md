# TeamBench: OS-Enforced Teamwork Benchmark for LLM Agents

> A multi-domain benchmark for evaluating whether LLM agents can collaborate effectively under OS-enforced role separation.

Unlike prior benchmarks that rely on prompt-based constraints, TeamBench uses **Docker containers with file-system mount policies** to enforce role boundaries. No single agent can simultaneously access the full specification, write to the workspace, and submit verification — forcing genuine teamwork.

## Key Features

- **22 tasks** across **8 domains** (software, ops, data, policy, IR, long-horizon, security, integration)
- **OS-level enforcement** via Docker bind mounts — not prompt-based honor system
- **Contamination-resistant** parameterized generation (infinite seed variants per task)
- **Model-agnostic** adapters for Gemini, GPT, Claude (and any OpenAI-compatible API)
- **5-condition ablation framework** with Teamwork Necessity Index (TNI)
- **336 automated tests** validating generators, graders, and pipeline integrity

## Why Teamwork Is Necessary

| Constraint | Mechanism | Bypass-proof? |
|---|---|---|
| **Information Partition** | Planner sees `spec.md`; Executor sees only `brief.md` | Yes — file not mounted |
| **Permission Partition** | Executor can write workspace; Planner/Verifier cannot | Yes — read-only mounts |
| **Verification Independence** | Only Verifier can write `attestation.json`; no attestation = auto-fail | Yes — mount policy |

### Teamwork Necessity Index (TNI)

```
TNI = (S_team - S_restricted) / max(epsilon, S_oracle - S_restricted)
```

| Score | Interpretation |
|-------|---------------|
| ~1.0 | Teamwork fully recovers the performance gap |
| ~0.5 | Teamwork substantially helps |
| ~0.0 | Teamwork provides no benefit |
| < 0 | Teamwork is harmful |

## Roles

| Role | Can Read | Can Write | Can Execute |
|---|---|---|---|
| **Planner** | `spec.md`, `brief.md`, messages | messages only | No |
| **Executor** | `brief.md`, workspace, reports, messages | workspace, reports | Yes |
| **Verifier** | `spec.md`, workspace (RO), reports (RO), messages | submission (`attestation.json`) | No |

## Task Overview (22 Tasks, 8 Domains)

| Domain | ID | Task | Difficulty | Languages |
|---|---|---|---|---|
| Software | S1 | Hidden Spec (edge cases in CLI app) | easy | Python |
| Software | S2 | Dependency Conflict (version resolution) | medium | Python |
| Ops | O1 | Service Health (fix broken server) | easy | Python, Bash |
| Ops | O2 | Incident Root Cause (diagnose from logs) | medium | Python, JSON |
| Data | D1 | Schema Drift (fix ETL pipeline) | easy | Python |
| Data | D2 | Data Quality (clean dirty dataset) | easy | Python |
| Policy | P1 | Policy-Driven Config (compliance rules) | easy | JSON |
| Policy | P2 | Spec Arbitration (conflicting requirements) | medium | JSON |
| IR | IR1 | Evidence QA (multi-doc retrieval) | easy | JSON |
| IR | IR2 | Misinformation Trap (adversarial docs) | medium | JSON |
| Long-Horizon | LH1 | Pipeline Workflow (10-15 step pipeline) | hard | Python, JSON |
| Long-Horizon | LH2 | Budgeted Workflow (resource constraints) | hard | Python, JSON |
| Security | SEC1 | Vulnerability Patch (OWASP fixes) | hard | Python |
| Testing | TEST1 | Spec-to-Tests (write tests from spec) | hard | Python |
| Integration | INT1 | Pipeline Repair (multi-component fix) | hard | Python, JSON |
| Integration | SYNTH1 | Distributed Debug (cross-service bugs) | expert | Python |
| Negotiation | NEG1 | Tradeoff Config (Pareto-optimal config) | expert | Python, JSON |
| Scale | SCALE1 | Codebase Migration (20+ file refactor) | expert | Python |
| Software | JS1 | API Migration (Express v4 to v5) | medium | JavaScript |
| Data | SQL1 | Query Repair (fix broken SQL queries) | medium | SQL |
| Software | GO1 | Concurrency Fix (race/deadlock bugs) | hard | Go |
| Integration | MULTI1 | Fullstack Fix (Python + JS + Bash bugs) | medium | Python, JS, Bash |

## Quick Start

### Prerequisites
- Python 3.10+
- Docker & Docker Compose (for container-based runs)

### Install

```bash
git clone https://github.com/ybkim95/TeamBench.git
cd TeamBench
python -m venv venv && source venv/bin/activate
pip install -e ".[dev]"
```

### Run with LLM Agent (API key required)

```bash
# Single task
teambench run --model gemini-2.5-flash --task P1_policy_config --seed 0

# All tasks
teambench run --model gpt-4o --task all --seeds 0 1 2

# Multi-model batch
teambench batch --models gemini-2.5-flash gpt-4o claude-3-5-sonnet --seeds 0 1 2

# Ablation study (5 conditions x all tasks)
teambench ablation --model gemini-2.5-flash --seeds 0 1 2
```

### Run with Docker (OS-enforced role separation)

```bash
docker compose build
python -m harness.run_task --task S1_hidden_spec --seed 0

# Interact with role containers
docker exec -it teambench_planner bash    # Read spec, plan strategy
docker exec -it teambench_executor bash   # Execute fixes
docker exec -it teambench_verifier bash   # Verify & create attestation

# Grade
python -m harness.grade_task --task S1_hidden_spec --run_dir shared/runs/<run_id>

docker compose down
```

### Validate Infrastructure (no API keys needed)

```bash
# Run all tests (generators, graders, pipeline)
pytest tests/ -v

# Validate all tasks
teambench validate --task all
```

## Model Adapters

TeamBench supports any LLM via the `ToolCallAdapter` interface:

```python
from harness.agent_interface import ToolCallAdapter, AdapterResponse

class MyAdapter(ToolCallAdapter):
    def generate_with_tools(self, messages, system_prompt, tools) -> AdapterResponse:
        # Call your LLM API, return text + tool_calls
        ...
    def get_usage(self) -> dict:
        return {"input_tokens": ..., "output_tokens": ..., "total_tokens": ...}
```

Built-in adapters (auto-selected by model name prefix):

| Prefix | Adapter | Environment Variable |
|---|---|---|
| `gemini-*` | GeminiAdapter | `GEMINI_API_KEY` |
| `gpt-*`, `o1*`, `o3*` | OpenAIAdapter | `OPENAI_API_KEY` |
| `claude-*` | AnthropicAdapter | `ANTHROPIC_API_KEY` |
| `mock-*` | MockAdapter | (none — for testing) |

## Contamination Resistance

Every task has a **parameterized generator** that produces unique instances per seed:

```python
from generators.registry import get_generator

gen = get_generator("P1_policy_config")

# Different seeds -> different data, different correct answers
r0 = gen.generate(seed=0)   # rate_limit=180, timeout=30, auth=jwt
r1 = gen.generate(seed=1)   # rate_limit=95, timeout=60, auth=saml
r42 = gen.generate(seed=42) # rate_limit=210, timeout=15, auth=oauth2

# Same seed -> deterministic
assert gen.generate(seed=0).expected == r0.expected
```

This makes data contamination through training data memorization ineffective.

## Ablation Framework

Five conditions to quantify the value of each architectural component:

| Condition | Description | What it measures |
|---|---|---|
| **Oracle** | Single agent, full access (spec + exec + verify) | Upper bound |
| **Restricted** | Single agent, executor-only (brief + exec) | Lower bound |
| **Team-NoPlan** | Executor + Verifier (no Planner) | Planning value |
| **Team-NoVerify** | Planner + Executor (no Verifier) | Verification value |
| **Full** | Planner + Executor + Verifier + remediation | Full team |

```bash
teambench ablation --model gpt-4o --seeds 0 1 2 --output shared/ablation_results.json
```

## Scoring

Each task produces `score.json`:

```json
{
  "pass": true,
  "primary": {"success": 1},
  "secondary": {"partial_score": 0.85},
  "failure_modes": []
}
```

**Hard rule**: Missing `attestation.json` = automatic FAIL (verifier must participate).

## Metrics

| Metric | Description |
|---|---|
| **Success Rate** | Binary pass/fail ratio |
| **Partial Score** | Fractional credit (0-1) for partial solutions |
| **Pass@k** | Stability: P(at least 1 pass in k seeded runs) |
| **TNI** | Teamwork Necessity Index (ablation-derived) |
| **Planning Value** | S_full - S_no_plan |
| **Verification Value** | S_full - S_no_verify |
| **Communication Cost** | Messages, tokens, rounds between agents |
| **Cross-Model Matrix** | C[planner_model, executor_model, verifier_model] |

## Failure Mode Taxonomy

| Code | Description |
|---|---|
| FM1 | Spec Omission — Executor missed requirements only in spec |
| FM2 | Overfit to Visible — Passed obvious checks, failed hidden ones |
| FM3 | Execution Loop — Agent retried without making progress |
| FM4 | Unsafe Change — Introduced security/policy violation |
| FM5 | Evidence Hallucination — Cited non-existent evidence |
| FM6 | Poor Repair — Failed remediation after verifier feedback |
| FM7 | Verification Failure — Verifier approved incorrect output |

## Repository Structure

```
TeamBench/
  harness/
    cli.py                  # Unified CLI: teambench run/grade/batch/ablation/validate
    run_agent.py             # Agent driver (model -> orchestrator -> grader)
    run_all.py               # Batch runner with setup_run/grade_run
    orchestrator.py          # 3-phase protocol: Plan -> Execute -> Verify
    agent_loop.py            # Single-agent tool-calling loop
    agent_interface.py       # ToolCallAdapter ABC, role configs, tools
    ablation.py              # 5-condition ablation framework + TNI
    statistics.py            # Bootstrap CIs, McNemar test, Pass@k
    analysis.py              # Post-hoc campaign analysis
    adapters/
      __init__.py            # create_adapter() factory
      openai_adapter.py      # GPT/O1/O3 adapter
      anthropic_adapter.py   # Claude adapter
      mock_adapter.py        # Deterministic mock for testing
    gemini_adapter.py        # Gemini adapter
  generators/
    base.py                  # TaskGenerator ABC, GeneratedTask dataclass
    primitives.py            # SeededRandom, NamePool, ValuePool
    registry.py              # Auto-discovery of gen_*.py generators
    gen_*.py                 # 22 parameterized generators (one per task)
  tasks/
    {TASK_ID}/
      task.yaml              # Metadata (domain, difficulty, languages, tags)
      spec.md                # Full specification (Planner + Verifier)
      brief.md               # Summary (Executor only)
      setup.sh               # Workspace preparation (legacy, generators preferred)
      grade.sh               # Deterministic grader -> score.json
      workspace/             # Initial (buggy) code/data
      corpus/                # Offline documents (IR/policy tasks)
  tests/
    test_contamination.py    # Cross-seed diversity + determinism
    test_task_structure.py   # Schema validation for all 22 tasks
    test_grader_correctness.py  # Graders don't false-positive
    test_e2e_pipeline.py     # Full pipeline integration test
  leaderboard/
    schema.json              # Submission format
    aggregate.py             # Aggregation with dimensional breakdowns
  docker-compose.yml         # 3-container sandbox (P/E/V)
  images/{planner,executor,verifier}/Dockerfile
  pyproject.toml             # Build config, CLI entry point
```

## Adding New Tasks

1. Create `generators/gen_my_task.py` implementing `TaskGenerator`
2. Create `tasks/MY_TASK/` with `task.yaml`, `spec.md`, `brief.md`, `setup.sh`, `grade.sh`, `workspace/`
3. Run `teambench validate --task MY_TASK` to verify
4. Run `pytest tests/test_contamination.py -v` to check cross-seed diversity

## Pre-registered Hypotheses

1. **Teamwork is necessary**: TNI > 0.5 across most tasks (restricted baseline significantly underperforms)
2. **Cross-family synergy**: Mixed teams (Gemini + Claude + GPT) outperform homogeneous teams
3. **Role specialization**: Some models excel as Planner vs. Executor vs. Verifier
4. **Verification value**: Removing the Verifier significantly reduces pass rate
5. **Difficulty calibration**: Expert tasks have < 20% pass rate; easy tasks have > 60%

## Citation

```bibtex
@article{teambench2025,
  title={TeamBench: A Benchmark for Evaluating OS-Enforced Teamwork Among Heterogeneous LLM Agents},
  author={...},
  year={2025},
  note={https://github.com/ybkim95/TeamBench}
}
```

## License

Apache 2.0
