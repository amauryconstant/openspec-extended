---
description: PHASE5 - Self-Reflection
agent: osx-reviewer
---

# PHASE5: Self-Reflection

Change: $1

> **Tools** — see `osx-workflow` §1.

## MANDATORY START

See `references/phase-protocol-common.md#mandatory-start`.

## PURPOSE

Evaluate the workflow retrospectively. Identify what worked, what didn't, and what to change. Capture in `reflections.md`.

## PROCESS

1. Load recent state: `openspec-extended osx ctx get "$1"`. Review `iterations.json` for total iterations across phases; review `decision-log.json` for high-level decisions; review `verification-report.md` (from PHASE2) and `test-compliance-report.md` (from PHASE1) for outcomes.

2. Synthesise the reflection:

   - **What worked** — patterns that delivered clean reviews / quick transitions
   - **What didn't** — repeated failures, blocked phases, excessive iterations
   - **What to change** — concrete recommendations for skill body, agent prompts, or phase protocol

3. Write `openspec/changes/$1/reflections.md`. Markdown body, free-form. Include total_phases and total_iterations in the frontmatter.

## MANDATORY END

Invoke `osx-commit` skill, commit `reflections.md`, record commit hash in decision log and `iterations.json`.

See `references/phase-protocol-common.md#mandatory-end` for the standard end sequence.

## STATE FILE UPDATES

```bash
openspec-extended osx state complete "$1"
```

## LOGGING

```bash
# decision log
openspec-extended osx log append "$1" --phase SELF_REFLECTION --iteration N \
  --summary "..." --commit-hash "<hash or null>" --next-steps "Proceeding to PHASE6 (ARCHIVE)" \
  --extra '{"reflections_path":"openspec/changes/$1/reflections.md","total_phases":N,"total_iterations":N}'

# iterations log
openspec-extended osx iterations append "$1" --phase SELF_REFLECTION --iteration N \
  --commit-hash "<hash or null>" --notes "..." \
  --extra '{"reflections_path":"...","total_phases":N,"total_iterations":N}'
```

Full schema in `references/osx-decision-logging.md`.

## BLOCKER HANDLING

See `references/blocker-semantics.md` for the canonical signal. Phase-specific reasons:

- Unable to read `iterations.json` or `decision-log.json` (state corruption)
- Reflection synthesis impossible without phase history

## TRANSITION

Log: "Reflection complete, proceeding to ARCHIVE". Mark phase complete via `osx state`. Script advances to PHASE6.

## SHELL ARGUMENT SAFETY

See `references/shell-argument-safety.md`.
<!--
# AUTO-GENERATED from opencode via `mise run sync:mirrors` — do not edit by hand.
Source: resources/opencode/commands/osx-phase5.md
Regenerate: `mise run sync:mirrors`
-->
