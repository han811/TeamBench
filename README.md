# TeamBench: A Multi-Agent Teamwork Benchmark with OS-Enforced Role Separation

[![HF Dataset](https://img.shields.io/badge/%F0%9F%A4%97%20HuggingFace-ybkim95%2Fteambench-yellow)](https://huggingface.co/datasets/ybkim95/teambench)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

> Repository for the **TeamBench** benchmark and harness. The camera-ready manuscript and the supplementary checklist live under [`paper/submitted_version/`](paper/submitted_version).

---

## What this benchmark measures

Agent systems often decompose a task across multiple roles, but those roles are typically specified by **prompts** rather than enforced by access controls. Without enforcement, a team pass rate can mask whether agents actually coordinated, or whether one role effectively did another role's work.

**TeamBench** evaluates agent coordination under **operating-system-enforced role separation**. Planner, Executor, and Verifier roles operate in isolated containers with distinct filesystem mounts and tool allow-lists, so no role can read the full requirements, modify the workspace, and certify the final answer. The benchmark contains **851 task templates** that expand to **931 seeded evaluation instances**, each shipped with a deterministic shell-script grader and a parameterized generator that emits byte-identical workspaces from a fixed seed.

| Property | Value |
|---|---|
| Task templates | **851** |
| Seeded evaluation instances | **931** |
| Base categories | **19** (refined to 21 for the leaderboard) |
| Originally authored | 161 templates with hidden-spec coordination requirement |
| GitHub-derived | 650 templates from active OSS (Flask, Click, httpx, Requests, Pydantic, Django, pytest, FastAPI, SQLAlchemy, Celery, Werkzeug, NumPy, SciPy, Keras, spaCy, ...) |
| UCI data-science | 30 templates on canonical public datasets |
| Public post-mortems | 10 templates from real incident reports |
| Reference ablation pool | 155 tasks with complete 5-condition data |
| Leaderboard subset | 90 stratified tasks (TeamBench-90); TeamBench-Verified covers 57 of 90 |
| Ablation conditions | 5 (Solo / Restricted / Full / No Plan / No Eval) |
| Role-mixing configurations | 27 (3 roles x 3 providers) |
| Human pilot | 40 sessions, 21 tasks, 18 distinct participants |
| Enforcement mechanism | Docker bind mounts (OS-level) |

---

## Headline findings

1. **Verifier false-accept rate of 49%** on grader-failing runs in the role-mixing pool. Removing the Verifier improves mean partial score in the reference ablation by 5.5 points.
2. **Prompt-only and sandbox-enforced teams reach statistically indistinguishable pass rates**, but prompt-only runs produce **3.6x more cases** where the Verifier rewrites the Executor's code.
3. **Team value is conditional.** Teams help by +15.7 points in the lowest Solo-score quintile and hurt by 6.8 to 10.1 points in the higher quintiles. Mean team-vs-Solo uplift is +0.5 points across the 155-task reference pool.
4. **Human pilot.** Solo participants work through the task directly. Hybrid sessions often collapse into quick approval. Human teams spend more effort coordinating missing information across roles. MIT COUHES exempt determination.

---

## Role separation

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
```

| Role | Reads | Writes | Executes |
|---|---|---|---|
| **Planner** | `spec.md`, `brief.md`, messages | messages | No |
| **Executor** | `brief.md`, workspace, messages | workspace, messages | Yes |
| **Verifier** | `spec.md`, workspace (read-only), messages | `attestation.json` | No |

Boundaries are enforced by Docker bind mounts and per-role tool allow-lists, not by prompt instructions.

---

## Five conditions

| Condition | Roles | Purpose |
|---|---|---|
| `Solo` | Single agent, full access | Capability ceiling |
| `Restricted` | Single agent, executor-only access | Capability floor |
| `Full Team` | Planner + Executor + Verifier | Full team |
| `No Plan` | Executor + Verifier (Verifier holds the spec) | Isolates planner contribution |
| `No Eval` | Planner + Executor | Isolates verifier contribution |

Mean partial score on the 155-task reference ablation: Solo `0.549`, Restricted `0.542`, No Plan `0.523`, No Eval `0.601`, Full Team `0.546`.

---

## Teamwork Necessity Index (TNI)

```
TNI = (S_team - S_restricted) / max(epsilon, S_solo - S_restricted)   (epsilon = 0.05)
```

| Band | Rule | Interpretation |
|---|---|---|
| **HIGH-TNI** | TNI >= 0.5 and Team > Solo | Team substantially exceeds Solo |
| **TEAM-HELPS** | Team > Solo and TNI < 0.5 | Team helps modestly |
| **NEUTRAL** | abs(Team - Solo) <= 0.05 | No clear team effect |
| **TEAM-HURTS** | Team < Solo | Coordination overhead hurts |

Of the 155 reference-evaluated tasks: **15 HIGH-TNI**, **39 TEAM-HELPS**, **62 NEUTRAL**, **39 TEAM-HURTS**.

---

## Repository layout

```
TeamBench/
+-- paper/submitted_version/        Submitted manuscript + supplementary
|   +-- neurips_2026.tex            Main paper
|   +-- neurips_2026.sty            Style file
|   +-- references.bib              Bibliography
|   +-- checklist.tex               Reproducibility checklist
|   +-- croissant.json              Croissant 1.1 + RAI metadata
|   +-- dataset_README.md           Hugging Face dataset card
|   +-- imgs/                       Figures
|
+-- harness/                        Evaluation harness
|   +-- run_all.py                  Batch runner across tasks/seeds/models
|   +-- ablation.py                 5-condition ablation orchestrator
|   +-- agent_loop.py               Single-agent loop (Solo/Restricted)
|   +-- adapters/                   Provider adapters (Anthropic/OpenAI/Gemini/HF)
|   +-- compute_tni.py              Per-task TNI report
|   +-- paper_tables.py             LaTeX tables generation
|
+-- generators/                     Parameterized seeded generators
|   +-- registry.py                 Auto-discovery
|   +-- gen_<task_id>.py            Per-task generator
|
+-- tasks/<TASK_ID>/                851 task templates
|   +-- spec.md                     Full specification (Planner-only)
|   +-- brief.md                    User-facing symptom (Executor)
|   +-- workspace/                  Initial files
|   +-- grade.sh                    Deterministic grader
|
+-- scripts/                        Helper scripts
+-- experiments/                    Ablation runs and analyses
+-- shared/                         Generated artifacts
|   +-- teambench_dataset.json      Canonical 931-instance dataset listing
|   +-- paper/                      Paper artifacts (tables, figures, JSONs)
|       +-- lb90_full_aggregate.json    LB90 leaderboard source
|       +-- ablation_summary.json       155-task reference ablation source
|
+-- human_eval/                     Human-baseline web platform (Firebase backend)
+-- leaderboard/                    Leaderboard aggregation
+-- LICENSE                         MIT
```

---

## Quickstart

```bash
git clone https://github.com/ybkim95/TeamBench.git
cd TeamBench
pip install -e .
```

Set provider API keys in your shell or in `.env`:

```bash
export ANTHROPIC_API_KEY=...
export OPENAI_API_KEY=...
export GEMINI_API_KEY=...
```

### Run a single task under the 5-condition ablation

```bash
python -m harness.ablation \
    --task DIST1_queue_race \
    --model gemini-3-flash-preview \
    --seed 0 \
    --out shared/runs/example
```

### Run the full LB90 leaderboard sweep

```bash
bash scripts/run_all_opensource_100_ablation.sh
```

### Compute TNI and paper tables

```bash
python -m harness.compute_tni  --runs-dir shared/runs/example
python -m harness.paper_tables --out shared/paper/
```

---

## Reproducing the paper

[`paper/EXPERIMENT_FACTSHEET.md`](paper/EXPERIMENT_FACTSHEET.md) lists every authoritative result file referenced in the paper:

- **LB90 leaderboard** (Table tab:lb90-leaderboard): `shared/paper/lb90_full_aggregate.json`.
- **Reference ablation** (Section 5): `shared/paper/ablation_summary.json`, 155 tasks.
- **Role-mixing 27-config grid** (Table tab:rolemix-full): under `shared/role_ablation/`.
- **Role-enforcement ablation** (Section 5): `experiments/role_enforcement_ablation/runs/<model>/results_*.json`.
- **Human pilot** (Section 7): aggregates derived from the Firebase log; raw logs are anonymized and deferred to a follow-up release per IRB exempt determination.

Tables 3, 4, and the 27-configuration table are re-derived from these files via `harness/paper_tables.py`.

---

## Responsible-use note

Adversarial-trap (`TRAP*`) and security-vulnerability (`CRYPTO*`, `SEC*`) tasks contain **plausible-but-incorrect** security patterns by design (intentional nonce reuse, low PBKDF2 iterations, truncated authentication tags, etc.). These are synthetic evaluation cases and **must not be deployed**. Recommended use is in network-isolated containers, per the responsible-use note in the manuscript.

---

## License

Released under the **MIT License** (see [LICENSE](LICENSE)). Tasks adapted from public GitHub issue trackers and UCI datasets retain their respective upstream licenses; only the issue text and patch reference are used to construct deterministic graders.

## Links

- Hugging Face dataset: <https://huggingface.co/datasets/ybkim95/teambench>
- Croissant metadata: <https://huggingface.co/datasets/ybkim95/teambench/resolve/main/croissant.json>
- Project site: <https://teambench.github.io>
- Issue tracker: <https://github.com/ybkim95/TeamBench/issues>
