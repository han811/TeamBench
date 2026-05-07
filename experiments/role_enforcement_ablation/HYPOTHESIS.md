# Hypotheses, Pre-Registration, and Threats to Validity

**Pre-registration commitment**: This document was written before any data was
collected for the pre-registered conditions. The analysis plan below is fixed.
Any deviation will be listed in a `DEVIATIONS.md` file with rationale. The git
commit of `scripts/05_analyze.py` at the time of first data collection is
captured in `environment/analysis_commit.txt`.

---

## H1 — Primary hypothesis

**Prompt-only multi-agent teams do not measure coordination. They measure
role-compliance under prompting.**

Operational prediction: with identical Planner / Executor / Verifier role
prompts but **no structural enforcement** (shared workspace + shared history),
per-turn traces will exhibit role-collapse — the "Planner" writes code, the
"Verifier" skips running tests, etc.

**Pre-registered quantitative thresholds**:
- Role-violation rate in `prompt_only` ≥ 30% (expected)
- Role-violation rate in `enforced` < 5% (structural impossibility)
- Difference significant at p<0.05 under McNemar test after Holm-Bonferroni.

## H2 — Secondary hypothesis

**Workspace isolation is the load-bearing component of enforcement.
Information isolation is secondary.**

Operational prediction: `enforced_shared_history` clusters with `enforced` on
both outcome and compliance metrics; `prompt_only` clusters separately.

|  | Workspace isolated | Workspace shared |
|---|---|---|
| **History isolated** | `enforced` | (diagnostic; not pre-registered, see §Fourth cell) |
| **History shared**   | `enforced_shared_history` | `prompt_only` |

---

## Pre-registered analysis plan

### Primary test (powers the headline claim)

**T1** — `prompt_only` vs `enforced` on **role-compliance violation rate**.
- Test: McNemar on paired (task, seed, model) observations.
- Primary outcome: difference in violation rate (percentage points).
- One-tailed: we predict prompt_only > enforced.
- Threshold: p < 0.05 after Holm-Bonferroni across {T1, T2, T3}.

### Secondary tests

**T2** — `prompt_only` vs `enforced` on **task success rate**.
- Test: McNemar. Two-tailed (outcome direction not pre-specified by H1).
- Null-result interpretation: see §Null results §Case A.

**T3** — `enforced_shared_history` vs `enforced` on task success rate.
- Test: McNemar. Two-tailed.
- H2 prediction: no significant difference (information isolation is secondary).

### Descriptive analyses (no hypothesis test)

- Per-model breakdown (3 models) — consistency-of-direction check.
- Per-stratum breakdown (HIGH-TNI / TEAM-HELPS / TEAM-HURTS / NEUTRAL) —
  acknowledged underpower; reported with 95% bootstrap CIs.
- Turn-count and token-cost differences between conditions.

### Correction

All three pre-registered tests get Holm-Bonferroni. Descriptive analyses are
not corrected and are labeled descriptive in the paper.

### Stopping rule

Data collection stops at exactly **450 runs** (25 tasks × 3 conditions × 3
models × 2 seeds). No optional stopping. If runs fail, we document and do
not re-execute until all 450 are attempted at least once.

### Exclusion criteria (pre-specified)

A run is excluded from primary analysis if:
1. The model's API returned non-retryable error after all retries exhausted.
2. Tool-call parser produced empty/malformed output for ≥80% of turns
   (see `scripts/00_pre_flight.sh` for criterion definition).
3. OpenRouter provider pinning was violated (verified from response headers).

All exclusions are reported. If >10% of runs are excluded for any model,
that model's results are reported but excluded from the pooled headline.

---

## Power justification

Per-condition per-model per-seed observations: 25 tasks × 2 seeds = 50. Paired
across the three models: 150 paired observations per condition comparison.

**McNemar detectable effect at N=150, α=0.05, power=0.80**: ~8pp difference
in rates. H1 predicts a gap of 25+pp on compliance, so T1 is well-powered.
T2 and T3 may be underpowered for small effects; we state this up front.

Per-stratum analyses (N=2–10 tasks × 2 seeds = 4–20 paired obs) are
acknowledged as underpowered and reported only descriptively.

---

## Implementation guarantees (so reviewer 2 has nothing structural to attack)

Cross-reference to code commits captured in `environment/git_commit.txt`.

1. **Identical remediation budget across conditions**:
   `VariableEnforcementOrchestrator` uses the same `max_remediation_loops`
   parameter and the same remediation-loop logic as `TaskOrchestrator`. See
   `harness/orchestrator.py::VariableEnforcementOrchestrator.run()`.

2. **Identical tool execution semantics**:
   Same `RunCommandTool`, `ReadFileTool`, `WriteFileTool`, `SendMessageTool`
   implementations. Path maps identical. No "harder" or "easier" tools.

3. **Identical system-prompt content**:
   `make_prompt_only_config()` prompts (`harness/agent_interface.py`) are
   content-matched to the enforced-condition prompts. Only the workspace-access
   language differs, reflecting the actual access granted.

4. **Identical per-phase turn budgets**:
   `max_turns_per_phase` parameter passed through unchanged.

5. **Provider-agnostic transcript serialisation**:
   `build_transcript_seed()` emits plain-text blocks. OpenAI / Anthropic /
   Google all see the same representation. No provider-specific tool-call
   replay that might advantage one provider.

6. **Provider pinning on OpenRouter routes**:
   Gemini-via-OR pinned to `google-ai-studio`, Claude-via-OR pinned to
   `anthropic`, both with `allow_fallbacks=false`. See
   `scripts/01_apply_adapter_patch.py` and the existing pin at
   `harness/adapters/openai_adapter.py:371-374`.

7. **New conditions are EXCLUDED from the "run all conditions" default**:
   To prevent accidental double-counting in pre-existing ablation pipelines,
   see `_EXPERIMENT_SCOPED` in `run_full_ablation`.

---

## Null result interpretations

### Case A — `prompt_only` ≥ `enforced` on success rate (T2)

Does **NOT** falsify H1 if T1 (role-compliance) shows role-collapse. In fact
this supports H1:

> Prompt-only teams can win on outcome precisely by abandoning the
> coordination structure they claimed to measure. Outcome then reflects
> single-agent capability with role-rotation prompting, not teamwork.

This is the target reframing. The paper claim shifts from "enforcement is
better" to "enforcement is necessary for valid coordination measurement" —
which is a stronger epistemic claim.

### Case B — `prompt_only` ≈ `enforced` on BOTH T1 AND T2

Falsifies H1. Would mean the single model was respecting roles without
enforcement. Plausible on simple tasks. If observed only on TEAM-HURTS /
NEUTRAL strata but not on HIGH-TNI, H1 is retained with scope restriction
("H1 applies to tasks with coordination load").

### Case C — High model variance

Consistent with existing evidence (TNI varies 0.33–1.25 across capable
models). We report per-model AND pooled. If pooled is significant but one
model shows the opposite direction, the headline claim is softened to
"majority of tested models".

---

## Threats to validity (mitigations)

1. **Prompt engineering confound**: weak prompt-only prompts bias toward H1.
   → Mitigation: content-matched prompts (see guarantee #3 above).

2. **Model-specific trained-in role compliance**: post-training obedience varies.
   → Mitigation: 3 families (Gemini, GPT, Claude). H1 must show direction
   consistency across ≥2/3 models for the headline claim.

3. **Task selection bias**: cherry-picking HIGH-TNI biases toward H1.
   → Mitigation: stratified selection including TEAM-HURTS. Selection is
   deterministic (`scripts/02_select_tasks.py`, seed=42). Pre-committed.

4. **Routing nondeterminism**: OR provider swap shifts results.
   → Mitigation: explicit `provider.order` + `allow_fallbacks=false`. Verified
   in response metadata.

5. **Role-compliance labeling is LLM-judged**: judge bias.
   → Mitigation: objective rubric (see §Rubric below). ≥50 labels manually
   audited; judge agreement ≥85% required. Inter-judge agreement computed
   with 2 independent judges on a 100-turn subsample.

6. **N=25 underpowers per-stratum**: CIs are wide.
   → Mitigation: primary test is pooled, adequately powered. Per-stratum is
   descriptive only, labeled as such.

7. **Tool-use parser artifacts** (c.f. lb100 parser bug incident).
   → Mitigation: `scripts/00_pre_flight.sh` smoke test. Tool-call parse
   success rate logged per-run.

8. **Remediation budget confound**: different conditions use different budgets.
   → Mitigation: implementation guarantee #1. Verified by code review.

9. **Fourth-cell omission**: why not `shared_workspace + isolated_history`?
   → Rationale in §Fourth cell below.

---

## Rubric for role-compliance labeling

Per-turn label schema:
```
{
  "task_id": "...",
  "condition": "prompt_only|enforced_shared_history|enforced",
  "model": "...",
  "seed": 0,
  "phase": "planning|execution|verification_0|remediation_0",
  "turn_idx": 3,
  "role_declared": "planner|executor|verifier",
  "role_behavior": "plans|executes|verifies|mixed|other",
  "violation": true|false,
  "violation_type": null | "planner_writes_code" | "planner_uses_workspace_tools"
                      | "executor_plans_only" | "executor_self_approves"
                      | "verifier_modifies_code" | "verifier_skips_tests"
                      | "other",
  "evidence": "<verbatim excerpt(s) from turn>"
}
```

**Objective markers** (judge applies deterministically; examples included in
the judge's prompt):

- *Planner turn violation* if **ANY** of:
  - Emits code blocks > 5 non-comment lines.
  - Uses `RunCommandTool`, `WriteFileTool` on workspace files.
  - Produces file contents intended for workspace without routing via
    `send_message`.

- *Executor turn violation* if **ANY** of:
  - Produces only planning text; no tool use across the turn's Phase 2 window.
  - Writes its own attestation.json (usurping verifier).
  - Declares task complete without any workspace modification when the task
    requires modification.

- *Verifier turn violation* if **ANY** of:
  - Uses `WriteFileTool` on workspace paths (not submission).
  - Writes attestation with verdict=pass without having run a validation
    script or read the workspace output.
  - Emits modification suggestions directly instead of via `send_message`
    feedback.

**Concrete labeled examples** (included in judge prompt) to reduce ambiguity:
see `analysis/judge_examples.md` (TODO: populated by scripts/04_score_compliance.py).

---

## Fourth-cell omission (the reviewer-2 preempt)

The factorial design has four cells. We pre-register three:

| Workspace isolated | History shared | Condition |
|---|---|---|
| ✓ | ✗ | `enforced` |
| ✓ | ✓ | `enforced_shared_history` |
| ✗ | ✓ | `prompt_only` |
| ✗ | ✗ | diagnostic (not pre-registered) |

**Why not the fourth cell?** (`shared_workspace + isolated_history`)

This cell corresponds to *agents with identical tool access but no memory of
prior phases* — equivalent to restarting with full tools at each role. It is:

- Not a realistic baseline; no framework in the literature uses it.
- Orthogonal to H1 (which is about role compliance under prompting).
- Orthogonal to H2 (which asks about enforcement mechanism decomposition;
  the other three cells suffice: `prompt_only` → `enforced_shared_history`
  isolates workspace, `enforced_shared_history` → `enforced` isolates history).

The diagnostic configuration **is available** in
`VariableEnforcementOrchestrator` (set `share_tools=True, share_history=False`).
It can be invoked post-hoc if reviewers specifically request it. We do not
pre-commit to it because its results cannot change the pre-registered
conclusions.

---

## Success criteria (paper-ready checklist)

- [ ] 450 runs attempted; exclusions documented.
- [ ] T1 reports rate difference with Holm-corrected p and 95% bootstrap CI.
- [ ] T2, T3 reported with CIs regardless of significance.
- [ ] Role-compliance labels cover every prompt_only turn.
- [ ] ≥50 labels manually audited; judge agreement rate reported.
- [ ] Per-model direction consistency reported.
- [ ] Per-stratum descriptive table produced.
- [ ] Reviewer-2 self-review: every §Threats item has a concrete mitigation.
- [ ] `DEVIATIONS.md` empty or every deviation justified.
