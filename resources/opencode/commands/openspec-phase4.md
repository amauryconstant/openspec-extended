---
description: PHASE4 - Sync Specs
agent: openspec-maintainer
---

## Tools Available

| Tool | Usage |
|------|-------|
| `osc-ctx` | `.opencode/scripts/lib/osc-ctx <change>` - load change context |
| `osc-state` | `.opencode/scripts/lib/osc-state <change> <action>` - manage state |
| `osc-log` | `.opencode/scripts/lib/osc-log <change> <action>` - decision log |
| `osc-iterations` | `.opencode/scripts/lib/osc-iterations <change> <action>` - iteration history |
| `osc-complete` | `.opencode/scripts/lib/osc-complete <change> <action>` - signal blocker status |

# PHASE4: Sync Specs

Change: $1

## MANDATORY START

1. Load context:
  !`.opencode/scripts/lib/osc-ctx "$1"`
2. Confirm `phase` is PHASE4
3. Review `history.iterations_recorded` for previous attempts
4. Load skill: `.opencode/skills/openspec-concepts/SKILL.md` (reference only)

## PURPOSE

Merge delta specs from the change to main specs.

## PROCESS

1. Check for delta specs:
   - Look in `openspec/changes/$1/specs/`
   - If no delta specs exist: Skip to transition with log note

2. Load skill: Use `openspec-sync-specs` skill

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
echo '{
  "status": "COMPLETE",
  "with_blocker": true,
  "blocker_reason": "[Describe the specific blocking issue]",
  "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
}' > openspec/changes/$1/complete.json
```

The orchestrator will detect this and halt the workflow.

**When to use:**
- Spec merge conflicts that cannot be resolved
- Main specs have been modified in ways incompatible with delta specs
- Sync would break existing functionality

## STATE FILE UPDATES

Phase complete:
```bash
.opencode/scripts/lib/osc-state "$1" complete
```

## DECISION LOG

Append entry:
```bash
echo '{
  "phase": "SYNC",
  "iteration": N,
  "summary": "Specs synced successfully",
  "delta_specs_found": ["spec1.md", "spec2.md"],
  "sync_operations": {"added": N, "modified": N, "removed": N, "renamed": N},
  "commit_hash": "<hash or null>",
  "next_steps": "Proceeding to PHASE5 (ARCHIVE)"
}' | .opencode/scripts/lib/osc-log "$1" append
```

## ITERATIONS.JSON

Append entry:
```bash
echo '{
  "iteration": N,
  "phase": "SYNC",
  "specs_synced": ["spec1.md", "spec2.md"],
  "operations": {"added": N, "modified": N, "removed": N, "renamed": N},
  "commit_hash": "<hash or null>",
  "notes": "Specs synced successfully"
}' | .opencode/scripts/lib/osc-iterations "$1" append
```

## TRANSITION

IF delta specs exist and were synced:
1. Log: "Specs synced, proceeding to ARCHIVE"
2. Mark phase complete via `osc-state`
3. Script will advance to PHASE5

IF no delta specs:
1. Log: "No delta specs, skipping SYNC"
2. Mark phase complete via `osc-state`
3. Script will advance to PHASE5
