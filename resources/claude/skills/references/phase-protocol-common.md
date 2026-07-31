# Phase Protocol — Common Patterns

Every phase command (`osx-phase0` … `osx-phase6`) shares the same operational spine. This reference captures what is common; each phase command documents only what is different.

## Mandatory start

Every phase command begins with these four steps before doing anything else:

1. Load context: `openspec-extended osx ctx get "$1"`.
2. Confirm `phase` field matches the current dispatch.
3. Review `history.iterations_recorded` for previous attempts.
4. Load reference skills `osx-concepts` and `osx-workflow` (do not edit them; read on demand).

## Mandatory end

Every phase command ends with:

1. Append to `osx log` (see `references/osx-decision-logging.md` for the schema).
2. Append to `osx iterations` (same reference).
3. Either mark phase complete (`osx state complete "$1"`) or signal a blocker (`osx complete set "$1" BLOCKED --blocker-reason "..."`).

PHASE6 is the exception: it does not call `osx state complete`. The orchestrator detects completion by the archive directory existing.

## State file updates

| Transition | Command |
|---|---|
| Phase complete, advance | `openspec-extended osx state complete "$1"` |
| Phase complete with routes pending (PHASE0 only) | `openspec-extended osx state set-routes "$1" --routes "/osx-modify,/opsx:update"` |
| Blocker (unrecoverable) | `openspec-extended osx complete set "$1" BLOCKED --blocker-reason "..."` |
| Explicit transition (PHASE2) | `openspec-extended osx state transition "$1" --target <PHASEN> --reason <reason> --details "..."` |

## Blocker vs fixable failure

A blocker is **unrecoverable** within the current phase. Fixable failures stay in the phase and re-iterate.

- Failing tests → fix in PHASE1, commit, re-iterate.
- Unclear specs → route via `osx-review-artifacts` (PHASE0) or signal a transition (`artifacts_modified`) so PHASE2 routes back to PHASE1 with fixed specs.
- Implementation bug → `osx state transition --target PHASE1 --reason implementation_incorrect`.
- Pre-commit hook failure → fix and re-stage. Never bypass with `--no-verify`.

## Iteration budget

`--max-phase-iterations` defaults to **10**. `-1` = unlimited. The orchestrator halts when the per-phase limit is reached and logs to `decision-log.json`; the user investigates.

## See also

- `references/osx-decision-logging.md` — the `osx log` / `osx iterations` schemas.
- `references/blocker-semantics.md` — when to halt vs continue.
- `references/osx-mode-conventions.md` — `OSX_AUTONOMOUS=1` handling.

<!--
# AUTO-GENERATED from opencode via `mise run sync:mirrors` — do not edit by hand.
Source: resources/opencode/skills/references/phase-protocol-common.md
Regenerate: `mise run sync:mirrors`
-->
