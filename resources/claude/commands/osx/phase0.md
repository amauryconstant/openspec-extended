---
description: PHASE0 - Artifact Review (read-only audit + routing; do not edit here)
agent: osx-analyzer
---

# PHASE0: Artifact Review

Change: $1

> **Tools** — see `osx-workflow` §1 for the 4 tool layers.

## MANDATORY START

See `references/phase-protocol-common.md#mandatory-start`.

## PURPOSE

Ensure OpenSpec artifacts are excellent before implementation. Validate:

- Schema-driven format conformance (per `openspec instructions <id> --json`'s `template` and `rules`).
- Cross-artifact consistency across the `dependencies` / `unlocks` graph.
- Implementation readiness (dependencies, scope achievability, task specificity).

PHASE0 dispatches `osx-analyzer` (`edit: deny`). **Do not edit artifacts inside this phase** — emit a routing report; the user or another invocation performs the edits via `osx-modify-artifacts` or `/opsx:update`.

## PROCESS

1. Load and use `osx-review-artifacts` skill for change "$1".
2. Execute review instructions from the skill.
3. Review findings bucketed as Critical / Warning / Suggestion.

4. **Routing rule.** Produce a routing recommendation:

   | Finding pattern | Recommended route |
   |---|---|
   | All findings target a single artifact AND no coherence-level finding | `/osx-modify <name> <artifact-id>` |
   | Findings span ≥2 artifacts OR any coherence-level finding | `/opsx:update <name>` |
   | Missing artifacts | `/opsx:continue <name>` |
   | All clean | mark phase complete and hand off to PHASE1 |

5. **Do not fix in this phase.** Surface the routing; the user (or a follow-up slash command) performs the fixes.

6. Track iteration via `osx log` and `osx iterations` per §DECISION LOG / §ITERATIONS.JSON below. Do **not** include an `artifacts-modified` list unless the change's artifacts were modified by something other than this phase.

7. After the user has applied fixes via `/osx-modify` or `/opsx:update`, the next PHASE0 iteration runs review again. Repeat up to the iteration cap.

8. **Max iterations reached without clean review:**
   - Document all remaining Critical issues via `osx log`.
   - Create `complete.json` with BLOCKED status (workflow stops).

## MANDATORY END

See `references/phase-protocol-common.md#mandatory-end`. PHASE0 never commits artifacts (it never edits them); the user invokes `osx-commit` after running the routed editor. When `artifacts_modified` is later recorded by the transition, capture the commit hash in the decision log entry below.

## STATE FILE UPDATES

```bash
# Phase complete (clean review)
openspec-extended osx state complete "$1"

# Non-clean review (routes pending — engine halts until user runs them)
openspec-extended osx state set-routes "$1" --routes "/osx-modify,/opsx:update"

# Critical blocker
openspec-extended osx complete set "$1" BLOCKED --blocker-reason "[Describe the blocking issue]"
```

The engine reads `routes_pending` from `state.json` after the phase ends. If non-empty (and `phase_complete` is false), the orchestrator exits 0 with a "Halted for routed commands" message. After the user runs the routed commands, the next `orchestrate` run re-enters PHASE0 to verify the fix.

## LOGGING

```bash
# decision log (one entry per phase/sub-decision)
openspec-extended osx log append "$1" --phase ARTIFACT_REVIEW --iteration N \
  --summary "..." --commit-hash "<hash or null>" --next-steps "..." \
  --extra '{"routed_to":"...","issues_found":{"critical":N,"warning":N,"suggestion":N}}'

# iterations log (chronological record)
openspec-extended osx iterations append "$1" --phase ARTIFACT_REVIEW --iteration N \
  --commit-hash "<hash or null>" --notes "..." \
  --extra '{"artifacts_audited":["<id>"],"issues_found":{},"routed_to":"..."}'
```

Full schema in `references/osx-decision-logging.md`.

## BLOCKER HANDLING

See `references/blocker-semantics.md` for the canonical signal. Phase-specific reasons:

- Routing rules exhausted (no editor in `osx-review-artifacts` Step 7 matrix fits)
- Schema corruption that no editor can fix

## GUARDRAILS

- **Read-only.** Editor actions belong to `/osx-modify` (single artifact) or `/opsx:update` (multi-artifact / coherence drift).
- **Max 10 review iterations.**
- **Single source of artifact names**: `openspec status --change <name> --json` and `openspec instructions <id> --change <name> --json`. No hardcoded `proposal.md`/`specs/`/`design.md`/`tasks.md`.
- **Carry `--store <id>`** when the change is store-backed.
- **Early exit** if the first review returns clean.

## SHELL ARGUMENT SAFETY

See `references/shell-argument-safety.md`.
<!--
# AUTO-GENERATED from opencode via `mise run sync:mirrors` — do not edit by hand.
Source: resources/opencode/commands/osx-phase0.md
Regenerate: `mise run sync:mirrors`
-->
