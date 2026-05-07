# TeamBench Leaderboard Protocol

## Overview

TeamBench maintains two evaluation tracks to balance openness with anti-gaming guarantees:

| Track | Seeds | Who runs it | Published |
|-------|-------|-------------|-----------|
| **Public** | 0, 1, 2 | Anyone (self-reported) | Yes — raw results welcome |
| **Hidden** | 3–9 | Benchmark maintainers only | Scores only, no content |

The hidden track is the authoritative leaderboard source. Public track results are useful for development and self-assessment but are not ranked officially because seeds 0–2 are visible in the repo.

---

## Public Track

Anyone can evaluate a system and self-report results.

**How to run:**

```bash
# Single task, seed 0, oracle condition
python -m harness.ablation --task D1_schema_drift --seed 0 --condition oracle --model gpt-5-mini

# Full ablation, seeds 0-2, all conditions
python scripts/run_leaderboard.py --model gpt-5-mini --seeds 0 1 2
```

**Reporting format** (`shared/leaderboard_submissions/public/{team_name}.json`):

```json
{
  "team": "MyTeam",
  "model": "gpt-5-mini",
  "date": "2026-04-01",
  "seeds": [0, 1, 2],
  "conditions": ["oracle", "full"],
  "results": { ... }
}
```

Self-reported results are accepted without verification. They appear in the community leaderboard with a "self-reported" badge.

---

## Hidden Track

Hidden seeds (3–9) are stored in `tasks_hidden/` which is git-ignored and never published. Evaluation is run by benchmark maintainers on behalf of submitters.

### Submission Format

Submit one of the following:

**Option A — Docker image** (preferred for reproducibility):

```
docker pull ghcr.io/your-org/your-agent:latest
```

The image must implement the `TeamBenchFrameworkAdapter` interface (see `harness/framework_adapter.py`). It receives a workspace directory mount and role-specific tool access:

```
/workspace/      <- task workspace (read/write)
/messages/       <- inter-agent messages
/submission/     <- write attestation.json here
/task/spec.md    <- Planner and Oracle only
/task/brief.md   <- Executor and Oracle
```

**Option B — Python script**:

Implement `TeamBenchFrameworkAdapter` from `harness/framework_adapter.py`:

```python
from harness.framework_adapter import TeamBenchFrameworkAdapter

class MyAdapter(TeamBenchFrameworkAdapter):
    def run_planner(self, spec: str, tools) -> str: ...
    def run_executor(self, brief: str, tools) -> str: ...
    def run_verifier(self, spec: str, tools) -> str: ...
```

Then run:

```bash
python scripts/run_with_framework.py --adapter path/to/my_adapter.py \
    --model my-model --seeds 3 4 5 --condition full
```

### What We Run

For each submission we run the **full** and **oracle** conditions on a stratified sample of hidden instances:

- 50 tasks × 3 seeds (seeds 3, 4, 5 by default) = 150 instances per condition
- Both `oracle` and `full` conditions are scored
- TNI is computed per task; mean TNI and team uplift are reported

### What We Publish

Results file (`shared/hidden_results/{model}_seeds345.json`) contains:

- Task IDs and categories
- Pass/fail per condition per seed
- Partial scores
- TNI and uplift summary statistics

Hidden seed **content** (workspace files, expected.json, spec.md) is never published.

### Submission Checklist

- [ ] Agent implements `TeamBenchFrameworkAdapter` or is packaged as a Docker image
- [ ] System runs end-to-end on public seeds 0–2 without errors (self-verify first)
- [ ] Submission email includes: team name, model name, Docker image or script path, contact email
- [ ] Results for public seeds attached (for cross-referencing)

Submit to: **teambench-submit@[maintainer-domain]** or open a GitHub issue tagged `leaderboard-submission`.

---

## Evaluation Cadence

| Activity | Schedule |
|----------|----------|
| Leaderboard updated | Monthly (first Monday) |
| Hidden seeds rotated | Quarterly |
| Old seeds published | On rotation (seeds become public after retirement) |

### Anti-Gaming Policy

1. **Seed rotation**: Seeds 3–9 are active for one quarter. On rotation, those seeds are published and a new set (10–16, etc.) replaces them. Systems cannot be tuned to hidden seeds because they change.

2. **Content embargo**: Hidden seed workspace files and expected.json are never included in any public artifact. Only scores and task IDs are reported.

3. **Generator audit**: If a submitted system shows >15% higher score on hidden seeds than public seeds for the same tasks, maintainers will audit the submission for data leakage or prompt injection.

4. **One submission per team per month**: To prevent iterative tuning against hidden-track feedback.

---

## Rotating Hidden Seeds

When a quarterly rotation is due:

```bash
# 1. Publish the retiring seeds (make them public)
python scripts/generate_hidden_seeds.py --seeds 3 4 5 6 7 8 9 --out-dir tasks_retired_Q1_2026

# 2. Generate new hidden seeds
python scripts/generate_hidden_seeds.py --seeds 10 11 12 13 14 15 16 --out-dir tasks_hidden

# 3. Validate new instances
python scripts/generate_hidden_seeds.py --validate-only --seeds 10 11 12 13 14 15 16

# 4. Update HIDDEN_SEEDS in scripts/evaluate_hidden.py
# 5. Announce rotation in the leaderboard changelog
```

Retired seed instances are committed to a separate `tasks_public_archive/` directory so the community can reproduce historical evaluations.

---

## Framework Adapter Interface

Any agent framework can participate by implementing `TeamBenchFrameworkAdapter`. See `harness/framework_adapter.py` for the full interface. Existing adapters:

| Framework | Adapter |
|-----------|---------|
| Direct API (OpenAI) | `harness/adapters/openai_adapter.py` |
| Direct API (Gemini) | `harness/gemini_adapter.py` |
| AutoGen | `harness/frameworks/autogen_adapter.py` |
| CrewAI | `harness/frameworks/crewai_adapter.py` |
| LangGraph | `harness/frameworks/langgraph_adapter.py` |

To add a new framework, subclass `TeamBenchFrameworkAdapter` and register it:

```python
from harness.framework_adapter import register_adapter
register_adapter("my_framework", MyAdapter)
```

---

## Leaderboard Display Fields

Each entry in the official leaderboard shows:

| Field | Description |
|-------|-------------|
| Team | Submitter name |
| Model | Base model identifier |
| Full Score | Pass rate under `full` condition (hidden seeds) |
| Oracle Score | Pass rate under `oracle` condition (hidden seeds) |
| TNI | Mean Team Necessity Index across tasks |
| Uplift | `full` − `oracle` (positive = team helps) |
| Track | `hidden` or `public (self-reported)` |
| Date | Evaluation date |
| Seeds | Seed range used |
