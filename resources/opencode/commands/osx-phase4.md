---
description: PHASE4 - Sync Specs
agent: osx-maintainer
---

## Tools Available

| Tool | Usage |
|------|-------|
| `osc` | `.opencode/scripts/lib/osx <domain> <action> [args]` - unified OpenSpec tool |
| Domains: `ctx`, `state`, `iterations`, `log`, `complete`, `validate` |

# PHASE4: Sync Specs

Change: $1

## MANDATORY START

1. Load context:
  !`.opencode/scripts/lib/osx ctx get "$1"`
2. Confirm `phase` is PHASE4
3. Review `history.iterations_recorded` for previous attempts
4. Load skill: `.opencode/skills/osx-concepts/SKILL.md` (reference only)

## PURPOSE

Merge delta specs from the change to main specs.

## PROCESS

1. Check for delta specs:
   - Look in `openspec/changes/$1/specs/`
   - If no delta specs exist: Skip to transition with log note

2. Load skill: Use `osc-sync-specs` skill

3. Sync delta specs:
   - ADDED → Append to main spec
   - MODIFIED → Merge changes intelligently
   - REMOVED → Delete from main
   - RENAMED → Rename in main

4. Log sync summary:
   - Specs synced: <capability-list>
   - Changes: adds/modifications/removals/renames

## MANDATORY END

IF delta specs were synced, commit before transitioning:

```bash
git add openspec/specs/
git commit -m "Sync $1 specs to main"
```

Record commit hash in decision log and iterations.json.

## BLOCKER HANDLING

If you encounter an unrecoverable issue that prevents progress:

```bash
.opencode/scripts/lib/osx complete set "$1" BLOCKED --blocker-reason "[Describe the specific blocking issue]"
```

The orchestrator will detect this and halt the workflow.

**When to use:**
- Spec merge conflicts that cannot be resolved
- Main specs have been modified in ways incompatible with delta specs
- Sync would break existing functionality

## STATE FILE UPDATES

Phase complete:
```bash
.opencode/scripts/lib/osx state complete "$1"
```

## DECISION LOG

Append entry:
```bash
.opencode/scripts/lib/osx log append "$1" \
  --phase SYNC \
  --iteration N \
  --summary "Specs synced successfully" \
  --commit-hash "<hash or null>" \
  --next-steps "Proceeding to PHASE5 (ARCHIVE)" \
  --extra '{"delta_specs_found":["spec1.md","spec2.md"],"sync_operations":{"added":N,"modified":N,"removed":N,"renamed":N}}'
```

## ITERATIONS.JSON

Append entry:
```bash
.opencode/scripts/lib/osx iterations append "$1" \
  --phase SYNC \
  --iteration N \
  --commit-hash "<hash or null>" \
  --notes "Specs synced successfully" \
  --extra '{"specs_synced":["spec1.md","spec2.md"],"operations":{"added":N,"modified":N,"removed":N,"renamed":N}}'
```

## TRANSITION

IF delta specs exist and were synced:
1. Log: "Specs synced, proceeding to ARCHIVE"
2. Mark phase complete via `osx state`
3. Script will advance to PHASE5

IF no delta specs:
1. Log: "No delta specs, skipping SYNC"
2. Mark phase complete via `osx state`
3. Script will advance to PHASE5
