---
description: PHASE4 - Sync Specs
agent: osx-maintainer
---

# PHASE4: Sync Specs

Change: $1

> **Tools** — see `osx-workflow` §1.

## MANDATORY START

See `references/phase-protocol-common.md#mandatory-start`.

## PURPOSE

Merge delta specs from the change into main specs, completing the spec-sync step before archive.

## PROCESS

1. Load and use `osc-sync-specs` (originally `openspec-sync-specs`) skill for change "$1".
2. Execute the skill's sync instructions.
3. Log sync operations (delta specs merged, conflicts resolved) via `osx log` and `osx iterations`.

## MANDATORY END

If sync produced changes: invoke `osx-commit` skill, commit changes, record commit hash in decision log and `iterations.json`.

See `references/phase-protocol-common.md#mandatory-end` for the standard end sequence.

## STATE FILE UPDATES

```bash
openspec-extended osx state complete "$1"
```

## LOGGING

```bash
# decision log
openspec-extended osx log append "$1" --phase SYNC --iteration N \
  --summary "..." --commit-hash "<hash or null>" --next-steps "Proceeding to PHASE5 (SELF_REFLECTION)" \
  --extra '{"delta_specs_found":["..."],"sync_operations":["..."]}'

# iterations log
openspec-extended osx iterations append "$1" --phase SYNC --iteration N \
  --commit-hash "<hash or null>" --notes "..." \
  --extra '{"delta_specs_found":["..."],"sync_operations":["..."]}'
```

Full schema in `references/osx-decision-logging.md`.

## BLOCKER HANDLING

See `references/blocker-semantics.md` for the canonical signal. Phase-specific reasons:

- Sync conflicts between two changes touching the same spec (resolve via `osc-bulk-archive-change` first)
- Delta spec format invalid (route via `osx-review-artifacts`)

## TRANSITION

Log: "Sync complete, proceeding to SELF_REFLECTION". Mark phase complete via `osx state`. Script advances to PHASE5.

## SHELL ARGUMENT SAFETY

See `references/shell-argument-safety.md`.