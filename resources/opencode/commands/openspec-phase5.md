---
description: PHASE5 - Archive Change
agent: openspec-maintainer
metadata:
   version: "0.1.0"
---

# PHASE5: Archive Change

Change: $1

## MANDATORY START

1. Read `.opencode/skills/openspec-concepts/SKILL.md` (reference only)
2. Read `openspec/changes/$1/state.json` to confirm phase is PHASE5
3. Read `openspec/changes/$1/decision-log.md` (if exists) to understand previous work

## PURPOSE

Archive the completed change for historical reference.

## PROCESS

1. Load skill: Use `openspec-archive-change` skill

2. Verify completion status:
   - Check artifact completion in `openspec/changes/$1/tasks.md`
   - Verify delta spec sync state (if applicable)

3. Execute archive:
   - Skill will move change to: `openspec/changes/archive/YYYY-MM-DD-$1/`
   - Verify the move completed successfully

4. Commit the archive:
   ```bash
   git add openspec/changes/archive/
   git commit -m "Archive change $1"
   ```

5. Log archive summary:
   - Archive location: <path>
   - Commit hash: <hash>
   - Status: archived

## STATE FILE UPDATES

Phase complete:
```bash
jq '.phase_complete = true' openspec/changes/$1/state.json > tmp && mv tmp openspec/changes/$1/state.json
```

Note: The state.json file will be in the archived location after this phase.

## DECISION LOG FORMAT

Append to `openspec/changes/$1/decision-log.md`:

```markdown
## PHASE5 - ARCHIVE

### Archive Location
- Path: openspec/changes/archive/YYYY-MM-DD-$1/

### Commit
- Hash: <hash>
- Message: "Archive change $1"

### Session Summary
Change successfully archived.

### Next Steps
Proceeding to PHASE6 (SELF-REFLECTION).
```

## ITERATIONS.JSON FORMAT

Append to `openspec/changes/$1/iterations.json`:

```json
{
  "iteration": N,
  "phase": "ARCHIVE",
  "archive_path": "openspec/changes/archive/YYYY-MM-DD-$1/",
  "commit_hash": "<hash>",
  "notes": "Change archived successfully"
}
```

## TRANSITION

1. Log: "Change archived, proceeding to SELF-REFLECTION"
2. Update `state.json`: Set `"phase_complete": true`
3. Script will advance to PHASE6
