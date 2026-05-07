# Verification Suite

Pre-execution checks on the role_enforcement_ablation implementation. No API calls.

## Run

```bash
# Canonical — explicit pass/fail per claim with context
python experiments/role_enforcement_ablation/tests/verify_implementation.py
```

Exit code 0 = all claims hold. Exit code 1 = at least one claim fails; specific failure printed with context.

## What this verifies

`verify_implementation.py` runs 18 checks grouped into 9 claims mapped directly to assertions in `../HYPOTHESIS.md`:

| Claim | Purpose |
|---|---|
| 1 | `AblationCondition` enum wiring + `_EXPERIMENT_SCOPED` guard |
| 2 | Tool symmetry (prompt_only) / asymmetry (enforced) — H1 operationalisation |
| 3 | prompt_only prompts cover same instructional topics (no prompt-engineering confound) |
| 4 | `build_transcript_seed` format, empty-input handling, truncation |
| 5 | **Orchestrator parity**: `VEO(enforced)` uses identical configs + budgets as `TaskOrchestrator` |
| 6 | `seed_context` gating (only applied when `share_history=True`) |
| 7 | `AgentLoop.run()` accepts `seed_context` with None default (no regression for existing callers) |
| 8 | `run_ablation_condition` dispatch routes all three new conditions through VEO |
| 9 | Scoring is grade.sh-authoritative, not attestation-only (defends against cheat-write critique) |

## When to re-run

- After any edit to `harness/agent_interface.py`, `harness/agent_loop.py`, `harness/orchestrator.py`, or `harness/ablation.py`
- As the first step of `scripts/99_replicate_from_scratch.sh`

## What this does NOT verify

- End-to-end LLM behavior (requires API calls — covered by `scripts/00_pre_flight.sh`)
- Provider pinning actually engages on OpenRouter (verified by log inspection post-run)
- Grader correctness (covered by existing `tests/test_grader_correctness.py`)

## Pre-existing failure (NOT caused by this experiment)

`tests/test_contamination.py::test_generator_cross_seed_produces_different_data` fails on the `fix/tokenizer-mismatch` branch due to uncommitted changes in `generators/gen_cross1_api_contract.py`. This is outside the role_enforcement_ablation surface area.
