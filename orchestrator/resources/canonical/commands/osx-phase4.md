---
name: osx-phase4
description: PHASE4 — merge delta specs from the change into main specs. Use when dispatched by the orchestrator after docs sync, or ad-hoc via `/osc-sync-specs` to surface conflicts early.
license: MIT
compatibility: Requires openspec CLI.
allowed-tools: Bash(openspec:*)
agent: osx-maintainer
metadata:
  audience: PHASE4 spec sync (dispatched by orchestrator)
  workflow: post-implementation — sync delta specs into main specs
---

# PHASE4: Sync Specs

Change: $1

> **Protocol spine** — see `references/phase-protocol-common.md`. **Blocker semantics** — `references/blocker-semantics.md`. **Decision-log schema** — `references/osx-decision-logging.md`. **Shell-arg safety** — `references/shell-argument-safety.md`. **Tools** — `osx-workflow` §1. **Store selection** — `references/store-selection.md`.

**Input**: The orchestrator dispatches `<change-name>` as `$1` (e.g., `/osx-phase4 add-auth`). For ad-hoc invocations: if omitted, check if it can be inferred from conversation context; auto-select if only one active change with delta specs exists; otherwise run `openspec list --json` (filtered to changes with delta specs, i.e. where a `specs/` directory exists) and prompt via `{{ASK_TOOL}}`. When the change is store-backed, carry `--store <id>` on every `openspec …` command.

## Mandatory start / end

```bash
# Start
openspec-extended osx ctx get "$1"
# End
openspec-extended osx log append "$1" --phase SYNC --iteration N \
  --summary "..." --commit-hash "<hash or null>" --next-steps "..." \
  --extra '{"delta_specs_found":["..."],"sync_operations":["..."]}'
openspec-extended osx iterations append "$1" --phase SYNC --iteration N \
  --commit-hash "<hash or null>" --notes "..."
# Phase end
openspec-extended osx state complete "$1"
```

## Steps

1. **Select the change**

   If a name is provided (the orchestrator dispatches `<change-name>` as `$1`), use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change with delta specs exists
   - If ambiguous, run `openspec list --json` (filtered to changes with delta specs, i.e. where a `specs/` directory exists) and ask the user to select one

   Always announce: "Using change: <change-name>" and how to override (e.g., `/osx-phase4 <other>`).

2. Load context per protocol spine.
3. Load and use `osc-sync-specs` skill for change `<change-name>`. Execute the skill's sync instructions.
4. **Conflict resolution** — if two changes touch the same spec, resolve via `osc-bulk-archive-change` first (archive the older change to free its delta specs) then re-run sync.
5. **Malformed delta specs** — if the delta in `openspec/changes/<name>/specs/` is malformed (invalid section headers, missing `## REMOVED Requirements` shape, broken `### Requirement:` blocks), never hand-edit the delta. Fix the *source* artifact that produced it via `/osc-update-change <name>` (reconciling proposal/specs/design/tasks against the dependency graph), then re-run sync. The delta is a render of upstream artifacts; the fix belongs upstream.
5. Log sync operations (delta specs merged, conflicts resolved) via `osx log` and `osx iterations`. Include `delta_specs_found` and `sync_operations` in `--extra`.
6. Commit via `osx-commit`. Capture the commit hash in the decision-log entry.
7. **Mandatory end** — append `osx log` and `osx iterations` per protocol spine, then `osx state complete "$1"`. Script advances to PHASE5.

## Output

Delta specs merged into main specs at `openspec/specs/<cap>/spec.md`. Sync operations logged. Commit hash recorded.

## Guardrails

- **Agent**: `osx-maintainer` (`edit: allow`).
- **Run sync inline** — do not delegate to a background task. The archive step (PHASE6) moves the change out from under an async sync.
- **Max 10 iterations** per phase. If exceeded, signal `BLOCKED` with `iteration_budget_exceeded`.
- **Failure modes**:
  - Sync conflicts between two changes touching the same spec → resolve via `osc-bulk-archive-change` first.
  - Delta spec format invalid → route via `osx-review-artifacts` and signal `BLOCKED`.
- **Pre-commit hook failure** → fix and re-stage. Never bypass with `--no-verify`.
