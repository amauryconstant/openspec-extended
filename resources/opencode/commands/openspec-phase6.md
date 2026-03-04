---
description: PHASE6 - Archive Change
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

# PHASE6: Archive Change

Change: $1

## ATOMIC EXECUTION REQUIREMENT

⚠️ **CRITICAL**: All steps in this phase MUST complete in a SINGLE agent invocation.

- Do NOT stop after archiving files
- Do NOT stop after committing changes
- Do NOT stop until step 5 (mark phase complete) is finished
- Partial completion will trigger unnecessary re-execution of this phase

## MANDATORY START

1. Load context:
   !`.opencode/scripts/lib/osc-ctx "$1"`
2. Confirm `phase` is PHASE6
3. Review `history.iterations_recorded` for previous attempts
4. Load skill: `.opencode/skills/openspec-concepts/SKILL.md` (reference only)

## PURPOSE

Archive the completed change for historical reference.

## REQUIRED SEQUENCE (ALL STEPS)

Complete ALL of these steps in order, without stopping:

### Step 1: Execute Archive

1. Load skill: Use `openspec-archive-change` skill

2. Verify completion status:
   - Check artifact completion in `openspec/changes/$1/tasks.md`
   - Verify delta spec sync state (if applicable)

3. Verify files to archive:
   - state.json (workflow state)
   - iterations.json (iteration history)
   - decision-log.json (decision log)
   - verification-report.md (from PHASE2, if exists)
   - reflections.md (from PHASE5, if exists)
   - test-compliance-report.md (from PHASE1, if exists)
   - suggestions.md (from any phase, if exists)

4. Perform archive:
   - Skill will move change to: `openspec/changes/archive/YYYY-MM-DD-$1/`
   - Verify the move completed successfully

### Step 2: Commit Archive

Commit the archive to git:

```bash
git add openspec/changes/archive/
git commit -m "Archive change $1"
```

Capture the commit hash for logging.

Note: After archiving, the change directory moves to archive/. The osc-* functions automatically detect this and will continue to work.

### Step 3: Mark Phase Complete

Mark this phase as complete in the state file:

```bash
.opencode/scripts/lib/osc-state "$1" complete
```

Note: The state.json file will be in the archived location after this phase. The osc-* functions will automatically find it.

### Step 4: Update Decision Log

Append entry to decision log:

```bash
echo '{
  "phase": "ARCHIVE",
  "iteration": N,
  "summary": "Change successfully archived with git commit",
  "archive_path": "openspec/changes/archive/YYYY-MM-DD-$1/",
  "commit_hash": "<hash>",
  "next_steps": "Archive complete. Workflow finished."
}' | .opencode/scripts/lib/osc-log "$1" append
```

### Step 5: Update Iterations Log

Append entry to iterations.json:

```bash
echo '{
  "iteration": N,
  "phase": "ARCHIVE",
  "archive_path": "openspec/changes/archive/YYYY-MM-DD-$1/",
  "commit_hash": "<hash>",
  "notes": "Change archived and committed successfully"
}' | .opencode/scripts/lib/osc-iterations "$1" append
```

## VERIFICATION CHECKLIST

Before finishing this invocation, verify ALL items are complete:

- [ ] Archive directory created at `openspec/changes/archive/YYYY-MM-DD-$1/`
- [ ] Git commit created with hash recorded in logs
- [ ] `osc-state "$1" complete` executed successfully
- [ ] Decision log entry appended with commit hash
- [ ] Iterations log entry appended with commit hash

**If ANY step is missing, the phase is incomplete and must be finished before stopping.**

## COMPLETION

After PHASE6 archive:
1. The change is now in `openspec/changes/archive/YYYY-MM-DD-$1/`
2. All state files (state.json, complete.json, iterations.json, decision-log.json) are archived
3. The script will detect completion and exit
4. State files will be cleaned up by the script

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
- Archive operation fails and cannot be retried
- File permissions prevent moving change to archive
- Critical files missing from change directory
