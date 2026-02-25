# TeamBench Human Baseline Protocol

## Overview

This protocol governs human developer participation in the TeamBench human baseline study. Human participants complete the same benchmark tasks as LLM multi-agent systems, operating under the same role constraints and time limits. The goal is to calibrate task difficulty, validate scoring rubrics, and produce a meaningful human reference point against which agent performance can be compared.

Participants act as a three-role team sequentially: first as the Planner, then as the Executor, then as the Verifier. Each role has restricted read access that mirrors the constraints imposed on LLM agents. The honor system, enforced by timestamped phase transitions logged automatically by the harness, ensures role discipline.

---

## Prerequisites

- Docker 24+ and Docker Compose v2 installed and running
- Python 3.10 or later
- Repository cloned: `git clone https://github.com/your-org/TeamBench && cd TeamBench`
- Dependencies installed: `pip install -e .`
- No LLM-based tools (GitHub Copilot, Cursor AI, ChatGPT, etc.) active during the session

---

## Starting a Session

```bash
python -m harness.human_baseline --task P1_policy_config --seed 42
```

Substitute the assigned task ID and seed values provided by the study coordinator. The script will:

1. Copy the task workspace into `shared/human_baselines/<participant_id>/<task>_<seed>/workspace/`
2. Run any task-specific setup
3. Print Phase 1 instructions and start the timer
4. Wait for your explicit confirmation before advancing to each subsequent phase

You will be prompted for a participant ID on first run. This ID is stored locally and reused for subsequent tasks. It is a random alphanumeric string — do not use your name or email.

---

## Role Constraints

You act as all three roles sequentially. Transitions are enforced by the script: files outside the permitted read set for each phase must not be consulted. This is an honor-system constraint; violations invalidate your run data.

### Phase 1 — Planner

**Permitted reads:** `tasks/<task_id>/spec.md` only.

**Required output:** A written plan saved at `workspace/plan.md`. The plan should describe:
- Your interpretation of the task goal
- The specific changes you intend to make in Phase 2
- Any risks or ambiguities you noticed

**Time budget:** Up to 10 minutes (counted against the 30-minute total).

When you have written `plan.md` and are ready to proceed, press Enter at the script prompt. The Phase 1 end timestamp is recorded automatically.

### Phase 2 — Executor

**Permitted reads:** `tasks/<task_id>/brief.md` and `workspace/plan.md` only. You may not re-read `spec.md`.

**Required output:** Fix the workspace files as described in your plan. All changes should be complete before you signal phase end.

**Time budget:** Up to 15 minutes.

You may use any tool available in your normal development environment: your IDE, terminal, web search, man pages, language documentation. LLM assistance (AI chat, AI code completion) is not permitted.

When you have finished editing the workspace, press Enter at the script prompt. The Phase 2 end timestamp is recorded.

### Phase 3 — Verifier

**Permitted reads:** `tasks/<task_id>/spec.md` and all files in `workspace/`. You may not modify workspace files during this phase.

**Required output:** An attestation file written by the script after your input. You will be asked:
- `verdict`: `pass` or `fail`
- `checklist`: for each criterion in spec.md, whether it is satisfied and a brief note

The script writes `workspace/submission/attestation.json` from your responses. The Phase 3 end timestamp is recorded when you confirm the attestation.

---

## Full Procedure

1. **Receive assignment.** The study coordinator provides you with a list of 5 task IDs and 5 seeds (one per task). Do not share these with other participants.

2. **Complete tasks one at a time.** Run the baseline script for each task in any order you choose. You may take breaks between tasks but not within a single task run.

3. **Time limit.** Each task is capped at 30 minutes of active working time. The script warns at 25 minutes and halts logging at 30 minutes (you may still submit but the overage is recorded). There is no benefit to rushing; accuracy is weighted more than speed in the study analysis.

4. **Permitted tools during execution:**
   - Your IDE or text editor
   - Terminal / shell
   - Web search for language documentation, library references, RFC specifications
   - Offline reference books or notes
   - Colleagues may not be consulted

5. **Prohibited during all phases:**
   - LLM-based chat assistants (ChatGPT, Claude, Gemini, Copilot Chat, etc.)
   - AI code completion plugins
   - Consulting other participants about task content

6. **Run the grader.** After the Verifier phase the script runs the official grader automatically and prints your score. Do not modify workspace files after the grader runs.

7. **Complete the self-report survey.** After the grader output the script prompts for:
   - Difficulty rating: 1 (trivial) to 5 (extremely hard)
   - Confidence rating: 1 (very unsure I passed) to 5 (certain I passed)
   - Free-text notes (optional, max 500 characters)

8. **Results are saved automatically** to `shared/human_baselines/<participant_id>/<task>_<seed>.json`.

---

## Data Collection

### Automatic (logged by the harness)

| Field | Description |
|---|---|
| `participant_id` | Anonymized random ID |
| `task_id` | Task name |
| `seed` | Random seed used |
| `phase1_duration_sec` | Seconds spent in Planner phase |
| `phase2_duration_sec` | Seconds spent in Executor phase |
| `phase3_duration_sec` | Seconds spent in Verifier phase |
| `total_duration_sec` | Wall-clock total |
| `grader_score` | Raw score dict from `grade_task` |
| `passed` | Boolean pass/fail |
| `overtime` | True if total exceeded 1800 s |

### Self-Reported

| Field | Description |
|---|---|
| `difficulty` | Integer 1–5 |
| `confidence` | Integer 1–5 |
| `notes` | Free-text string |

All data is written to a single JSON file. No data is transmitted automatically; the study coordinator will collect result files at the end of the session.

---

## Submission

After completing all 5 tasks, send the following to the study coordinator:

```
shared/human_baselines/<your_participant_id>/
```

The directory contains one JSON result file per task. Do not modify these files after the grader has run.

---

## IRB and Ethics Considerations

This is a developer performance study, not medical or psychological research. Key considerations:

- **Participants:** Professional software developers recruited voluntarily. Participation is compensated at the standard contractor rate for your region.
- **Data collected:** Task performance metrics and self-reported ratings. No personally identifiable information is collected; participant IDs are randomly generated.
- **Anonymization:** The mapping between participant IDs and real identities is stored only by the study coordinator and destroyed after the study concludes.
- **Data use:** Aggregated results will be published in the TeamBench paper. No individual-level results will be published.
- **Withdrawal:** You may withdraw at any time by informing the coordinator. Partial data will be deleted on request.
- **No deception:** The tasks, constraints, and grading criteria are exactly as described. There are no hidden conditions.

If you have questions about the study, contact the research lead listed in the participant information sheet provided at recruitment.

---

## Troubleshooting

**The script fails to find the task directory.**
Ensure you are running from the repository root (`TeamBench/`) and that the task ID is spelled exactly as shown (e.g. `P1_policy_config`, not `p1_policy_config`).

**The workspace setup step fails.**
Check that Docker is running (`docker info`). Some tasks require Docker for setup even in human baseline mode.

**I accidentally read a forbidden file.**
Stop the current phase immediately, note the violation in the free-text field, and continue. The study coordinator will decide whether to exclude the run.

**The grader reports an error.**
Do not modify workspace files. Note the error in the free-text field and contact the coordinator.
