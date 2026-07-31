---
description: PHASE3 - Maintain Documentation
agent: osx-maintainer
---

# PHASE3: Maintain Documentation

Change: $1

> **Tools** — see `osx-workflow` §1.

## MANDATORY START

See `references/phase-protocol-common.md#mandatory-start`.

## PURPOSE

Update `AGENTS.md` and `CLAUDE.md` files to reflect ALL changes made during implementation. If a skill exists for this process, load it first.

**Scope — what to update:**

- Root `AGENTS.md` with new commands, patterns, or conventions
- Package-level `AGENTS.md` files (e.g., `internal/library/AGENTS.md`)
- `CLAUDE.md` if project supports both platforms
- Any other AI context documentation

**What to include:** new packages and purpose, new CLI commands and usage, new architectural patterns, updated command references, new capabilities.

**NOT in scope:** inline code comments (PHASE1), README files (PHASE1), test files (PHASE1).

## PROCESS

1. Load and use `osx-maintain-ai-docs` skill.
2. Read change artifacts: `proposal.md`, `specs/`, `design.md`, `tasks.md`.
3. Read recent git changes: `git log --oneline -10`.
4. Update project documentation: root `AGENTS.md`, package-level `AGENTS.md`, `CLAUDE.md`, other docs as needed.
5. Apply best practices: tables over prose, concrete commands, progressive disclosure, target <300 lines per file.

## AGENTS.md TASKS FROM TASKS.MD

If `tasks.md` contains AGENTS.md documentation tasks (e.g., "12.1 Update cmd/AGENTS.md"):

1. These were intentionally deferred from PHASE1.
2. Complete them now as part of this phase.
3. Mark them complete in `tasks.md` after updating.
4. Include in the single PHASE3 commit.

This consolidation ensures a single documentation commit for review, accurate representation of final codebase state, no duplicate documentation work.

## MANDATORY END

If documentation was updated during this phase: invoke `osx-commit` skill, commit changes, record commit hash in decision log and `iterations.json`.

See `references/phase-protocol-common.md#mandatory-end` for the standard end sequence.

## STATE FILE UPDATES

```bash
openspec-extended osx state complete "$1"
```

## LOGGING

```bash
# decision log
openspec-extended osx log append "$1" --phase MAINTAIN_DOCS --iteration N \
  --summary "..." --commit-hash "<hash or null>" --next-steps "Proceeding to PHASE4 (SYNC)" \
  --extra '{"docs_updated":["AGENTS.md","CLAUDE.md"],"changes_made":["..."]}'

# iterations log
openspec-extended osx iterations append "$1" --phase MAINTAIN_DOCS --iteration N \
  --commit-hash "<hash or null>" --notes "..." \
  --extra '{"docs_updated":["AGENTS.md","CLAUDE.md"]}'
```

Full schema in `references/osx-decision-logging.md`.

## BLOCKER HANDLING

See `references/blocker-semantics.md` for the canonical signal. Phase-specific reasons:

- Documentation conflicts that cannot be resolved
- `AGENTS.md` / `CLAUDE.md` structure fundamentally incompatible with changes

## TRANSITION

Log: "Documentation updated, proceeding to SYNC". Mark phase complete via `osx state`. Script advances to PHASE4.

## SHELL ARGUMENT SAFETY

See `references/shell-argument-safety.md`.

<!--
# AUTO-GENERATED from opencode via `mise run sync:mirrors` — do not edit by hand.
Source: resources/opencode/commands/osx-phase3.md
Regenerate: `mise run sync:mirrors`
-->
