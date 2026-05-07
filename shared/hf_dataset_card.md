---
dataset_info:
  features:
    - name: task_id
      dtype: string
    - name: title
      dtype: string
    - name: category
      dtype: string
    - name: difficulty
      dtype: string
    - name: has_generator
      dtype: bool
    - name: ablation_scores
      dtype: string
    - name: tni
      dtype: float32
    - name: classification
      dtype: string
  splits:
    - name: train
      num_examples: 153
    - name: test
      num_examples: 120
license: mit
task_categories:
  - text-generation
tags:
  - multi-agent
  - benchmark
  - software-engineering
  - teamwork
  - evaluation
  - llm-evaluation
pretty_name: TeamBench
---

# TeamBench: A Multi-Agent Teamwork Benchmark

## Overview

TeamBench is a rigorous benchmark for evaluating whether LLM-based agent *teams* outperform single oracle agents on realistic software engineering tasks. Each task is executed under five ablation conditions (oracle, restricted, full team, team without planning, team without verification), enabling fine-grained measurement of when and why teamwork helps. The core metric is the **Teamwork Necessity Index (TNI)**, which quantifies how much a task requires coordinated multi-agent effort beyond what a single capable agent can achieve alone.

TeamBench uses OS-enforced role separation — Planner, Executor, and Verifier agents operate in isolated sandboxes with distinct tool allow-lists — ensuring that role boundaries are structurally enforced rather than prompt-based. Tasks span 18 categories including security, data engineering, adversarial specification traps, distributed systems, and long-horizon planning, with 153 tasks totalling 459 parameterized instances (seeds 0–2).

---

## Task Categories

| Category | Tasks | Description |
|---|---|---|
| Software Eng. | 22 | Hidden specs, backward compatibility, refactoring |
| Security | 17 | Vulnerability patching, cryptographic correctness, audit triage |
| Operations | 16 | Incident root-cause, container debugging, monitoring |
| Data Engineering | 12 | Schema drift, ETL repair, query optimization |
| Testing | 11 | Spec-to-tests, mutation resistance, property-based testing |
| Incident Response | 11 | Cascade failure, memory leak, rollback planning |
| Information Retrieval | 8 | Evidence QA, misinformation traps, multi-source retrieval |
| Policy | 8 | Access control, data retention, license compliance |
| Distributed Systems | 7 | Race conditions, Raft consensus, idempotency |
| Adversarial | 7 | Spec conflicts, false bug reports, security theater |
| Code Review | 6 | API review, style enforcement, test coverage |
| Multi-language | 6 | Go concurrency, JavaScript XSS, polyglot debugging |
| Long-Horizon | 6 | Multi-step migrations, staged deployments, audit trails |
| Pipeline | 6 | ETL fix, API gateway, message queues |
| Cross-System Integration | 5 | API contract mismatches, schema evolution, auth federation |
| Specification | 3 | Feature implementation from RFC, config schema design |
| Integration | 1 | Pipeline repair, API versioning |
| Negotiation | 1 | Trade-off configuration under competing constraints |

**Difficulty breakdown:** 104 hard, 26 medium, 16 expert, 7 easy (78% hard or expert).

---

## Ablation Conditions

Each task is evaluated under five conditions:

| Condition | Description |
|---|---|
| `oracle` | Single powerful agent with full tool access and no role restrictions |
| `restricted` | Single agent with executor-only tool access (no planning/verification tools) |
| `team` | Full three-role team: Planner → Executor → Verifier |
| `team_no_plan` | Two-role team: Executor → Verifier (planning phase skipped) |
| `team_no_verify` | Two-role team: Planner → Executor (verification phase skipped) |

Scores are in [0, 1] and represent the fraction of grader checks passed.

---

## TNI Metric

The **Teamwork Necessity Index (TNI)** measures how much a task *requires* teamwork:

```
TNI = team_uplift / necessity_gap
    = (team - oracle) / (1 - restricted)
```

- `TNI > 0`: team outperforms oracle relative to the task's difficulty ceiling
- `TNI = 1.0`: team achieves the maximum possible improvement over oracle
- `TNI > 1.0`: team substantially exceeds oracle (rare; indicates strong synergy)
- `TNI < 0`: team underperforms oracle (teamwork overhead hurts)

**Classification thresholds:**
- `HIGH-TNI`: TNI ≥ 0.5 and team > oracle
- `TEAM-HELPS`: team > oracle but TNI < 0.5
- `NEUTRAL`: |team - oracle| ≤ 0.05
- `TEAM-HURTS`: team < oracle

Of the 153 tasks: TEAM-HELPS 53, NEUTRAL 51, TEAM-HURTS 28, HIGH-TNI 16.

---

## Usage

```python
import json

with open("teambench_dataset.json") as f:
    tasks = json.load(f)

# Filter to tasks where teamwork helps
team_helps = [t for t in tasks if t.get("classification") in ("TEAM-HELPS", "HIGH-TNI")]
print(f"Tasks where team > oracle: {len(team_helps)}")

# Get hard tasks with ablation scores
hard_with_scores = [
    t for t in tasks
    if t["difficulty"] in ("hard", "expert") and "ablation_scores" in t
]
print(f"Hard/expert tasks with ablation data: {len(hard_with_scores)}")

# Compute average team uplift
uplifts = [
    t["ablation_scores"]["team"] - t["ablation_scores"]["oracle"]
    for t in tasks
    if "ablation_scores" in t
]
print(f"Mean team uplift: {sum(uplifts)/len(uplifts):.3f}")
```

### Loading via HuggingFace datasets

```python
from datasets import load_dataset

ds = load_dataset("ybkim95/teambench", split="train")  # all 153 tasks
# ds = load_dataset("ybkim95/teambench", split="test")  # 120 hard/expert tasks only
print(ds[0])
```

---

## Benchmark Results

Cross-model evaluation across Gemini and OpenAI model families shows that:

- Team outperforms oracle on **43.9%** of tasks (68/155 with full ablation data)
- Average TNI: **0.744** across tasks with a measurable necessity gap
- Weaker models benefit *more* from teamwork (larger relative uplift)
- `team_no_verify` is often the strongest condition — verifier overhead can hurt on average
- The **Expertise-Asymmetry (EA)** variant (5 tasks) shows TNI > 1.0 with capable models, meaning specialized role knowledge pushes teams beyond what any single oracle achieves

Full results and leaderboard: [GitHub](https://github.com/ybkim95/TeamBench)

---

## Citation

```bibtex
@dataset{kim2026teambench,
  author    = {Yubin Kim},
  title     = {TeamBench: A Multi-Agent Teamwork Benchmark for LLM Evaluation},
  year      = {2026},
  url       = {https://huggingface.co/datasets/ybkim95/teambench},
  note      = {153 tasks across 18 categories with OS-enforced role separation}
}
```

---

## License

MIT License. See [LICENSE](https://github.com/ybkim95/TeamBench/blob/main/LICENSE) for details.
