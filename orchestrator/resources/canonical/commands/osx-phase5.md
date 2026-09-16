---
name: osx-phase5
description: PHASE5 — autonomous reflection over the change's iteration history. Use when dispatched by the orchestrator after sync, or ad-hoc via the orchestrator to harvest improvement suggestions.
license: MIT
compatibility: Requires openspec CLI.
allowed-tools: Bash(openspec:*)
agent: osx-reviewer
metadata:
  audience: PHASE5 self-reflection (dispatched by orchestrator)
  workflow: post-implementation — reflection on iteration history
---

# PHASE5: Self-Reflection

Change: $1

> **Protocol spine** — see `references/phase-protocol-common.md`.
> **Tools** — see `osx-workflow` §1.
> **Store selection** — see `references/store-selection.md`.

**Input**: The orchestrator dispatches `<change-name>` as `$1` (e.g., `/osx-phase5 add-auth`). For ad-hoc invocations: if omitted, check if it can be inferred from conversation context; auto-select if only one active change exists; otherwise run `openspec list --json` and prompt via `{{ASK_TOOL}}`. PHASE5 also reads `iterations.json` and `decision-log.json` for the change's full history, plus `verification-report.md` and `test-compliance-report.md` from earlier phases.

## Steps

1. **Select the change**

   If a name is provided (the orchestrator dispatches `<change-name>` as `$1`), use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` and ask the user to select one

   Always announce: "Using change: <change-name>" and how to override (e.g., `/osx-phase5 <other>`).

2. Load context per protocol spine.
3. **Pull history** via `openspec-extended osx ctx get "$1"` — extract `history.iterations_recorded`, `decision_log`, and the latest `verification_report` and `test_compliance_report`.
4. **Optional pre-step — deep think.** If the iteration history is dense (3+ reroutes, multiple `implementation_incorrect` transitions, or recurring Critical findings across phases), invoke `/openspec-explore <name>` first to surface structural improvements through guided reasoning. Skip this step when history is short and the suggestions are obvious — the autonomous pass below covers the typical case.
5. **Reflect autonomously** — review workflow execution, identify recurring patterns (blockers, reroutes, milestone-commit cadence), and surface improvements as concrete suggestions.
6. Write `reflections.md` with: phase-by-phase iteration counts, dominant blocker categories, recurring routing decisions, and 1–5 actionable improvement suggestions for the orchestrator's future runs.
7. Commit `reflections.md` via `osx-commit`. Capture the commit hash in the decision-log entry.
8. **Mandatory end** — append `osx log` and `osx iterations` per protocol spine, then `osx state complete "$1"`. Script advances to PHASE6.

## Output

`reflections.md` with phase summary, dominant blocker categories, recurring routing decisions, and 1–5 actionable suggestions. Commit hash recorded in `decision-log.json` and `iterations.json`.

## Guardrails

- **Agent**: `osx-reviewer` (`edit: allow`).
- **Read-only on artifacts** — `reflections.md` is the only write target. Never modify planning or implementation artifacts here.
- **No tool-specific fallback** — there is no `osc-*` core skill for self-reflection; this phase runs autonomous reasoning over the change's iteration history.
- **Max 10 iterations** per phase. If exceeded, signal `BLOCKED` with `iteration_budget_exceeded`.
- **Failure modes**:
  - `iterations.json` corrupt or missing → log warning, write `reflections.md` with partial data, mark phase complete.
  - `decision-log.json` not parseable → fall back to `state.json.history` for the summary.
