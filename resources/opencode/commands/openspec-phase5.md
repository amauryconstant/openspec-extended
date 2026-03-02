---
description: PHASE5 - Archive Change
agent: openspec-maintainer
---

## Tools Available

| Tool | Usage |
|------|-------|
| `osc-ctx` | `.opencode/scripts/lib/osc-ctx <change>` - load change context |
| `osc-state` | `.opencode/scripts/lib/osc-state <change> <action>` - manage state |
| `osc-log` | `.opencode/scripts/lib/osc-log <change> <action>` - decision log |
| `osc-iterations` | `.opencode/scripts/lib/osc-iterations <change> <action>` - iteration history |

# PHASE5: Archive Change

Change: $1

## MANDATORY START

1. Load context:
  !`.opencode/scripts/lib/osc-ctx "$1"`
2. Confirm `phase` is PHASE5
3. Review `history.iterations_recorded` for previous attempts
4. Load skill: `.opencode/skills/openspec-concepts/SKILL.md` (reference only)

## PURPOSE

Archive the completed change for historical reference.

## PROCESS

1. Load skill: Use `openspec-archive-change` skill

2. Verify completion status:
   - Check artifact completion in `openspec/changes/$1/tasks.md`
   - Verify delta spec sync state (if applicable)

3. Verify files to archive:
   - state.json (workflow state)
   - iterations.json (iteration history)
   - decision-log.json (decision log)
   - verification-report.md (from PHASE2, if exists)
   - reflections.md (from PHASE6, if exists)
   - test-compliance-report.md (from PHASE1, if exists)

4. Execute archive:
   - Skill will move change to: `openspec/changes/archive/YYYY-MM-DD-$1/`
   - Verify the move completed successfully

4. Log archive summary:
   - Archive location: <path>
   - Status: archived

## MANDATORY END

Commit the archive before transitioning:

```bash
git add openspec/changes/archive/
git commit -m "Archive change $1"
```

Record commit hash in decision log and iterations.json.

## STATE FILE UPDATES

Phase complete:
```bash
.opencode/scripts/lib/osc-state "$1" complete
```

Note: The state.json file will be in the archived location after this phase.

## DECISION LOG

Append entry:
```bash
echo '{
  "phase": "ARCHIVE",
  "iteration": N,
  "summary": "Change successfully archived",
  "archive_path": "openspec/changes/archive/YYYY-MM-DD-$1/",
  "commit_hash": "<hash>",
  "next_steps": "Proceeding to PHASE6 (SELF-REFLECTION)"
}' | .opencode/scripts/lib/osc-log "$1" append
```

## ITERATIONS.JSON

Append entry:
```bash
echo '{
  "iteration": N,
  "phase": "ARCHIVE",
  "archive_path": "openspec/changes/archive/YYYY-MM-DD-$1/",
  "commit_hash": "<hash>",
  "notes": "Change archived successfully"
}' | .opencode/scripts/lib/osc-iterations "$1" append
```

## TRANSITION

1. Log: "Change archived, proceeding to SELF-REFLECTION"
2. Mark phase complete via `osc-state`
3. Script will advance to PHASE6
