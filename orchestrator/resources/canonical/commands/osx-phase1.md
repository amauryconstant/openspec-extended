---
name: osx-phase1
description: PHASE1 — implement the change's tasks with milestone commits. Use when dispatched by the orchestrator after artifact review passes, or ad-hoc to apply tasks from a change's `tasks.md`.
license: MIT
compatibility: Requires openspec CLI.
allowed-tools: Bash(openspec:*)
agent: osx-builder
metadata:
  audience: PHASE1 implementation (dispatched by orchestrator)
  workflow: implementation
---

# PHASE1: Implementation

Change: $1

> **Protocol spine** — see `references/phase-protocol-common.md`. **Blocker semantics** — `references/blocker-semantics.md`. **Decision-log schema** — `references/osx-decision-logging.md`. **Shell-arg safety** — `references/shell-argument-safety.md`. **Tools** — `osx-workflow` §1. **Store selection** — `references/store-selection.md`.

**Input**: The orchestrator dispatches `<change-name>` as `$1` (e.g., `/osx-phase1 add-auth`). For ad-hoc invocations: if omitted, check if it can be inferred from conversation context; auto-select if only one active change exists; otherwise run `openspec list --json` and prompt via `{{ASK_TOOL}}`. When the change is store-backed, carry `--store <id>` on every `openspec …` command.

## Mandatory start / end

```bash
# Start
openspec-extended osx ctx get "$1"
# Apply prerequisites (v1.13.0+ envelope includes missingPrerequisites)
openspec-extended osx fetch_apply_prerequisites "$1"
# End — log missing prerequisites when present
openspec-extended osx log append "$1" --phase IMPLEMENTATION --iteration N \
  --summary "..." --commit-hash "<hash or null>" --next-steps "..." \
  --extra '{"missing_prerequisites":[...],"milestone_commits":[...]}'
openspec-extended osx iterations append "$1" --phase IMPLEMENTATION --iteration N \
  --commit-hash "<hash or null>" --notes "..."
# Phase end
openspec-extended osx state complete "$1"
```

**Advisory project guidance** (optional): if `openspec-extended` injects guidance at the top of this prompt via `RunRequest.extra_prompt` (surfaced from `operations.apply.guidance` in `openspec/config.yaml`), treat it as authoritative project context.

## Steps

1. **Select the change**

   If a name is provided (the orchestrator dispatches `<change-name>` as `$1`), use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` and ask the user to select one

   Always announce: "Using change: <change-name>" and how to override (e.g., `/osx-phase1 <other>`).

2. Load context per protocol spine.
3. **Load apply prerequisites** via `osx fetch_apply_prerequisites "$1"` — reads `instructions apply --json` and surfaces `missingArtifacts`, `missingPrerequisites`, `tasks`, `contextFiles`, `operationGuidance`. Address missing prerequisites via PHASE0 routing before continuing.
4. Load and use `osc-apply-change` skill for change `<change-name>`. Follow its task execution pattern.
5. Implement tasks in order. Dispatched via `osx-builder` (`edit: allow`).
6. **Milestone commits** — 1–5 commits per iteration, invoked via `osx-commit`. Each commit advances `state.json.current_commit` and is logged in `decision-log.json` and `iterations.json`. Cap at the iteration budget.
7. **End-of-iteration coverage check** — invoke `osx-review-test-compliance` skill. If a `Critical` or unresolved `Warning` finding appears, fix it (re-iterate) or transition (`implementation_incorrect` → PHASE1 with new details). Slash-command equivalent for ad-hoc runs: `/osx-verify-tests <change-name>` — same skill body.
8. **Validation** — `openspec validate --change "$1" --type all --strict --json`. If invalid, fix and re-iterate.
9. **Mandatory end** — append `osx log` and `osx iterations` per protocol spine, then `osx state complete "$1"`.

## Output

Completed implementation with `openspec validate --strict` passing, end-of-iteration `test-compliance-report.md` free of Critical findings, milestone commits recorded in `iterations.json`, and `state.json.phase = PHASE1_COMPLETE`.

## Guardrails

- **Agent**: `osx-builder` (`edit: allow`).
- **Pause-and-route on scope/design drift** — if implementation reveals the spec or design is wrong (not just the code), stop work in PHASE1, route via `/osc-update-change <name>`, then resume. If the intent changed entirely, follow the `Update vs Start Fresh` heuristic (`osc-update-change` §Guardrails) and route to `/osc-new-change <fresh-name>` instead of retrofitting the current change.
- **Never edits OpenSpec planning artifacts** in PHASE1 (`openspec/changes/<name>/{proposal,design,specs,tasks}.md`); those belong to `/osc-update-change` (called by the user outside the dispatched phase).
- **Never invokes `osx log` or `osx iterations` with backticks in arg values** — shell interprets backticks as command substitution. See `references/shell-argument-safety.md`.
- **Max 10 iterations** per phase; if exceeded, signal `BLOCKED` with `iteration_budget_exceeded` and let the user investigate.
- **Failure modes**:
  - Apply instructions report `state: "blocked"` (missing artifacts) → route back to PHASE0 via `state transition --target PHASE0 --reason artifacts_missing`.
  - `state: "all_done"` → skip to PHASE2.
  - `openspec validate` fails → fix and re-iterate within PHASE1 (not a blocker).
- **Pre-commit hook failure** → fix and re-stage. Never bypass with `--no-verify`.
