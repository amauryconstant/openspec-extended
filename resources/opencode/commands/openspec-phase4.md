---
description: PHASE4 - Sync Specs
agent: openspec-maintainer
metadata:
   version: "0.1.0"
---

# PHASE4: Sync Specs

Change: $1

## MANDATORY START

1. Read `.opencode/skills/openspec-concepts/SKILL.md` (reference only)
2. Read `openspec/changes/$1/state.json` to confirm phase is PHASE4
3. Read `openspec/changes/$1/decision-log.md` (if exists) to understand previous work

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

4. Commit synced specs:
   ```bash
   git add openspec/specs/
   git commit -m "Sync $1 specs to main"
   ```

5. Log sync summary:
   - Specs synced: <capability-list>
   - Changes: adds/modifications/removals/renames
   - Commit hash: <hash>

## STATE FILE UPDATES

Phase complete:
```bash
jq '.phase_complete = true' openspec/changes/$1/state.json > tmp && mv tmp openspec/changes/$1/state.json
```

## DECISION LOG FORMAT

Append to `openspec/changes/$1/decision-log.md`:

```markdown
## PHASE4 - SYNC

### Delta Specs Found
- [list of delta specs or "None"]

### Sync Operations
- ADDED: [files]
- MODIFIED: [files]
- REMOVED: [files]
- RENAMED: [files]

### Commit
- Hash: <hash>
- Message: "Sync $1 specs to main"

### Session Summary
[What was accomplished]

### Next Steps
Proceeding to PHASE5 (ARCHIVE).
```

## ITERATIONS.JSON FORMAT

Append to `openspec/changes/$1/iterations.json`:

```json
{
  "iteration": N,
  "phase": "SYNC",
  "specs_synced": ["spec1.md", "spec2.md"],
  "operations": {"added": N, "modified": N, "removed": N, "renamed": N},
  "commit_hash": "<hash>",
  "notes": "Specs synced successfully"
}
```

## TRANSITION

IF delta specs exist and were synced:
1. Log: "Specs synced, proceeding to ARCHIVE"
2. Update `state.json`: Set `"phase_complete": true`
3. Script will advance to PHASE5

IF no delta specs:
1. Log: "No delta specs, skipping SYNC"
2. Update `state.json`: Set `"phase_complete": true`
3. Script will advance to PHASE5
