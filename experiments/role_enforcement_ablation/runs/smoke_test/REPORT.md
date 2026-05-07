# Smoke Test Report — role_enforcement_ablation

**Purpose**: End-to-end verification of `VariableEnforcementOrchestrator` with a
real LLM before committing the experiment to pre-registered data collection.

**Scope**: 1 task (`P1_policy_config`) × 3 conditions × 1 seed × 1 model (Claude
Haiku 4.5 via OpenRouter, provider-pinned to `anthropic`).

This is **not** a pre-registered data point. Task selection is for engineering
validation only; statistical claims come from `scripts/03_run_all.sh`.

---

## Runs

### v1 — initial smoke (2026-04-24 17:29 UTC)

| Condition | Pass | Partial | Turns | Elapsed | Notes |
|---|---|---|---|---|---|
| `enforced` | ✅ | 1.0 | 32 | 127s | — |
| `enforced_shared_history` | ✅ | 1.0 | 30 | 136s | — |
| `prompt_only` | **❌** | 0.93 | 27 | 98s | Failed on `bad_attestation` |

### v2 — after bug fix (2026-04-24 17:41 UTC)

| Condition | Pass | Partial | Turns | Elapsed | Notes |
|---|---|---|---|---|---|
| `enforced` | ✅ | 1.0 | 29 | 127s | — |
| `enforced_shared_history` | ✅ | 1.0 | 33 | 147s | — |
| `prompt_only` | ✅ | 1.0 | 27 | 115s | Fix verified |

---

## Bug found and fixed during v1 investigation

**Symptom**: `prompt_only` verifier wrote `attestation.json` but grader reported
`bad_attestation`. Investigation found the file landed in `workspace/` instead
of `submission/`.

**Root cause** (in `harness/agent_interface.py::make_prompt_only_config`):

The shared-tools design used `WriteFileTool(..., base_dir=workspace_dir)` for
all three roles. This matches the enforced Executor's config but differs from
the enforced Verifier's config, which uses `base_dir=submission_dir`. In
enforced mode, `write(path='attestation.json')` resolves to
`submission/attestation.json` for the Verifier because of that base_dir shift.
In prompt_only with shared tools, the same call resolved to
`workspace/attestation.json` — wrong location — causing the grader's
attestation check to fail.

**Impact if unfixed**: prompt_only would have systematically failed the
`bad_attestation` check on every task that verifies attestation placement,
*regardless of actual agent behavior*. This would have confounded any
observed outcome gap between conditions with a path-resolution artifact. A
reviewer-2 flagrant.

**Fix**: Changed the `prompt_only` Verifier's system prompt to use the path_map
alias `/shared/submission/attestation.json` (which resolves via the already-
built path_map to the real submission directory). This:

1. Preserves the shared-tools design (tool configs still identical across roles).
2. Produces the correct on-disk location.
3. Is consistent with pre-registration: HYPOTHESIS.md §Implementation Guarantee 3
   allowed "only the workspace-access language differs" across conditions.
4. Does not change the enforced or enforced_shared_history prompts.

**Verification**: v2 smoke test (above) confirms all three conditions now pass
the attestation check with partial=1.0.

---

## Seed delivery evidence

`VariableEnforcementOrchestrator._seed_if_shared()` now writes the
seed content to `<run_dir>/logs/<role>/seed_context.json` whenever a seed is
applied. This gives post-hoc verifiable evidence of seed delivery.

v2 run artifacts:

| Condition | seed_context.json files | Matches expected |
|---|---|---|
| `enforced` (share_history=False) | 0 files | ✅ no seed expected, none written |
| `enforced_shared_history` | 2 files (executor, verifier_attempt_0) | ✅ |
| `prompt_only` | 2 files (executor, verifier_attempt_0) | ✅ |

Sample seed content (from
`enforced_shared_history/.../verifier_attempt_0/seed_context.json`):

```
# Prior conversation transcript (from earlier role phases)

## Phase: planning
Turn 0 — planner:
I'll start by reading the policy document to understand all the requirements,
then create a detailed plan for the Executor.
  tool_call: read({"path": "corpus/policy.txt"})
    exit_code=0
    stdout: CONFIGURATION POLICY DOCUMENT ...
```

This confirms the verifier in shared-history conditions actually receives the
prior planner+executor transcripts in its LLM context.

---

## What this does NOT show

This is N=1 on a single task. It does not speak to H1 or H2. All three
conditions passed — we cannot infer effect direction from this.

The pre-registered signal will come from `scripts/03_run_all.sh` (25 tasks × 3
conditions × 3 models × 2 seeds = 450 runs). Stopping rule and analysis plan
are in `HYPOTHESIS.md`.

---

## Files

- `v1 output`: `experiments/role_enforcement_ablation/logs/smoke_test_20260424T172849Z.log`
- `v2 output`: `experiments/role_enforcement_ablation/logs/smoke_test_v2_20260424T173900Z.log`
  (approximate timestamp; actual file in logs/)
- Per-run artifacts: `runs/smoke_test/<condition>/P1_policy_config/<timestamp>/`
- Aggregate: `runs/smoke_test/aggregate_summary.json`
