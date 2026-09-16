---
name: osx-phase3
description: PHASE3 — sync project docs (`AGENTS.md` / `CLAUDE.md`) with what implementation changed. Use when dispatched by the orchestrator after verification, or ad-hoc via `/osx-maintain-docs`.
license: MIT
compatibility: Requires openspec CLI.
allowed-tools: Bash(openspec:*)
agent: osx-maintainer
metadata:
  audience: PHASE3 documentation maintenance (dispatched by orchestrator)
  workflow: post-implementation — docs sync
---

# PHASE3: Maintain Documentation

Change: $1

> **Protocol spine** — see `references/phase-protocol-common.md`. **Blocker semantics** — `references/blocker-semantics.md`. **Decision-log schema** — `references/osx-decision-logging.md`. **Shell-arg safety** — `references/shell-argument-safety.md`. **Tools** — `osx-workflow` §1. **Store selection** — `references/store-selection.md`.

**Input**: The orchestrator dispatches `<change-name>` as `$1` (e.g., `/osx-phase3 add-auth`). For ad-hoc invocations: if omitted, check if it can be inferred from conversation context; auto-select if only one active change exists; otherwise run `openspec list --json` and prompt via `{{ASK_TOOL}}`. PHASE3 also reads `tasks.md` for any `{{DOCS_FILE}}` task items the implementer deferred from PHASE1.

## Mandatory start / end

```bash
# Start
openspec-extended osx ctx get "$1"
# End
openspec-extended osx log append "$1" --phase MAINTAIN_DOCS --iteration N \
  --summary "..." --commit-hash "<hash or null>" --next-steps "..." \
  --extra '{"docs_file":"...","lines_added":N,"commit_style":"..."}'
openspec-extended osx iterations append "$1" --phase MAINTAIN_DOCS --iteration N \
  --commit-hash "<hash or null>" --notes "..."
# Phase end
openspec-extended osx state complete "$1"
```

## Steps

1. **Select the change**

   If a name is provided (the orchestrator dispatches `<change-name>` as `$1`), use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` and ask the user to select one

   Always announce: "Using change: <change-name>" and how to override (e.g., `/osx-phase3 <other>`).

2. Load context per protocol spine.
3. Load and use `osx-maintain-docs` skill. Follow the doc-update rules in `references/update-rules.md` and worked diffs in `references/update-examples.md`. Edit `{{DOCS_FILE}}` (project-specific docs file) only — never inline comments. Cross-reference `references/doc-structures.md` for AGENTS.md/CLAUDE.md parse/write rules and the `osx-maintain-docs` command body for the canonical protocol; `references/osx-mode-conventions.md` clarifies how `OSX_AUTONOMOUS=1` resolves interactive confirmation steps.
4. **Structure guide** — see `references/doc-structures.md` for AGENTS.md / CLAUDE.md parsing/writing strategies and validation rules.
5. **Mode** — `OSX_AUTONOMOUS=1` is set by the orchestrator. Interactive confirmation steps use their documented autonomous defaults (see `references/osx-mode-conventions.md`).
6. Commit via `osx-commit`. Capture the commit hash in the decision-log entry.
7. **Mandatory end** — append `osx log` and `osx iterations` per protocol spine, then `osx state complete "$1"`.

## Output

`{{DOCS_FILE}}` updated to reflect what the implementation actually changed (not what was planned). No section reordering; no inline-comment substitution; no doc cruft. Commit hash recorded in `decision-log.json` and `iterations.json`.

## Guardrails

- **Agent**: `osx-maintainer` (`edit: allow`).
- **Document only what AI cannot infer from code** — code is the source of truth for behaviour; docs describe intent, trade-offs, and operational guidance.
- **Never bypass** `osx-commit`'s detection heuristic; commit style must match the project standard.
- **Warn if** `{{DOCS_FILE}}` > 300 lines. **Error if** > 500 lines (split required before adding content).
- **Max 10 iterations** per phase. If exceeded, signal `BLOCKED` with `iteration_budget_exceeded`.
- **Failure modes**:
  - Doc structure invalid → fix and re-iterate.
  - Commit style ambiguous → `osx-commit` falls back to Conventional Commits; record the chosen style in the log.
