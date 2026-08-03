---
description: PHASE1 - Implementation
name: osx-phase1
---

# PHASE1: Implementation

Change: $1

> **Tools** — see `osx-workflow` §1 for the 4 tool layers.

## MANDATORY START

See `references/phase-protocol-common.md#mandatory-start`. PHASE1 also reads the change artifacts (`proposal.md`, `specs/`, `design.md`, `tasks.md`) and determines which tasks to implement this iteration.

## MANDATORY CHECKPOINT: CLI Output Logging

Before implementation:

1. `openspec status --change "$1" --json` → log via `osx log` with `cli_status` field
2. `openspec instructions apply --change "$1" --json` → log via `osx log` with `cli_instructions` field

## PURPOSE

Implement tasks from the change, making logical milestone commits and validating test coverage.

## PROCESS

### 1. Load Implementation Skill

Load `osc-apply-change` (originally `openspec-apply-change`) skill for change "$1". Follow its task execution pattern.

### 2. Implement Tasks

- Read `tasks.md` to identify unchecked tasks.
- Implement sequentially.
- Mark complete: `- [ ]` → `- [x]`.
- Continue until all tasks complete OR iteration limit reached.

### 3. Milestone Commits

**You MUST commit after completing logical work units.** Min 1 / max 5 commits per iteration. Subject: imperative verb + brief description (40–72 chars). For each commit: invoke `osx-commit` skill, stage, commit.

**Pre-commit hook guardrails (always apply):**

- NEVER use `--no-verify` to bypass pre-commit hooks.
- If pre-commit hooks fail, fix the issues. Re-run commit.
- After 3 failed attempts, document via `osx log` and consider signaling `BLOCKED`.

**Documentation scope for PHASE1:**

- ✅ Inline code comments, README updates for new features, package-level doc files, CLI help text.
- ❌ `AGENTS.md` files → deferred to PHASE3 (PHASE3 handles `AGENTS.md` after implementation is final).

### 4. Validate Test Coverage

After implementation: run `osx-review-test-compliance` skill. If gaps: implement missing tests, commit, re-run. Until: clean or only suggestions remain.

## ERROR HANDLING

- Git commit fails: check staged files, verify clean working directory, retry once.
- Tests fail repeatedly (>3 attempts): subagent to debug, check spec clarity.
- Iteration loop stuck (>3 with no progress): document blocker, signal COMPLETE.
- `openspec` CLI fails: proceed without CLI output, document via `osx log`.

## MANDATORY END

See `references/phase-protocol-common.md#mandatory-end`. AGENTS.md updates happen in PHASE3 even if `tasks.md` lists them.

## STATE FILE UPDATES

When all tasks complete:

```bash
openspec-extended osx state complete "$1"
```

## LOGGING

```bash
# decision log
openspec-extended osx log append "$1" --phase IMPLEMENTATION --iteration N \
  --summary "..." --next-steps "..." --errors '[]' \
  --extra '{"tasks_completed":["1.1","1.2"],"tasks_remaining":0,"commits_made":N,"cli_status":{},"cli_instructions":{}}'

# iterations log
openspec-extended osx iterations append "$1" --phase IMPLEMENTATION --iteration N \
  --notes "..." --errors '[]' \
  --extra '{"tasks_completed":["1.1","1.2","1.3"],"tasks_remaining":0,"tasks_this_session":3,"commits_made":N,"cli_status":{},"cli_instructions":{}}'
```

Full schema in `references/osx-decision-logging.md`.

## BLOCKER HANDLING

See `references/blocker-semantics.md` for the canonical signal. Phase-specific reasons:

- Pre-commit hook failures that cannot be resolved after 3 attempts
- Implementation fundamentally blocked by unclear or contradictory specs
- External dependencies unavailable or broken
- Task cannot be completed due to missing information

## TRANSITION

When all tasks in `tasks.md` are marked `[x]`: log "All tasks complete, transitioning to PHASE2 (REVIEW)", mark phase complete via `osx state`. Script advances to PHASE2.

## SHELL ARGUMENT SAFETY

See `references/shell-argument-safety.md`.

<!--
# AUTO-GENERATED from opencode via `mise run sync:mirrors` — do not edit by hand.
Source: resources/opencode/commands/osx-phase1.md
Regenerate: `mise run sync:mirrors`
-->
