---
description: PHASE6 - Archive Change
agent: osx-maintainer
---

## Tools Available

| Tool | Usage |
|------|-------|
| `osx` | `.opencode/scripts/lib/osx <domain> <action> [args]` - unified OpenSpec tool |
| Domains: `ctx`, `state`, `iterations`, `log`, `complete`, `validate` |

# PHASE6: Archive Change

Change: $1

## ATOMIC EXECUTION REQUIREMENT

⚠️ **CRITICAL**: All steps in this phase MUST complete in a SINGLE agent invocation.

- Do NOT stop after archiving files
- Do NOT stop after committing changes
- Do NOT stop until step 5 (commit archive) is finished
- Partial completion will trigger unnecessary re-execution of this phase

## MANDATORY START

1. Load context:
   !`.opencode/scripts/lib/osx ctx get "$1"`
2. Confirm `phase` is PHASE6
3. Review `history.iterations_recorded` for previous attempts
4. Load skill: `.opencode/skills/osx-concepts/SKILL.md` (reference only)

## PURPOSE

Archive the completed change for historical reference.

## REQUIRED SEQUENCE (ALL STEPS)

Complete ALL of these steps in order, without stopping:

### Step 1: Clean Transient Files

Before archiving, remove transient state files that should not be preserved:

```bash
rm -f openspec/changes/$1/state.json
rm -f openspec/changes/$1/complete.json
rm -f .openspec-baseline.json
```

These files are runtime artifacts that should not be archived.

Note: PHASE6 does NOT call `osx state complete`. The orchestrator detects completion by archive directory existence, not by state.json.

### Step 2: Execute Archive

1. Load skill: Use `osc-archive-change` (originally `openspec-archive-change`) skill

2. Verify completion status:
   - Check artifact completion in `openspec/changes/$1/tasks.md`
   - Verify delta spec sync state (if applicable)

3. Verify files to archive:
   - iterations.json (iteration history)
   - decision-log.json (decision log)
   - verification-report.md (from PHASE2, if exists)
   - reflections.md (from PHASE5, if exists)
   - test-compliance-report.md (from PHASE1, if exists)
   - suggestions.md (from any phase, if exists)

4. Perform archive:
   - Skill will move change to: `openspec/changes/archive/YYYY-MM-DD-$1/`
   - Verify the move completed successfully

### Step 3: Update Decision Log

Append entry to decision log BEFORE committing:

```bash
.opencode/scripts/lib/osx log append "$1" \
  --phase ARCHIVE \
  --iteration N \
  --summary "Change successfully archived" \
  --next-steps "Archive complete. Workflow finished." \
  --extra '{"archive_path":"openspec/changes/archive/YYYY-MM-DD-$1/"}'
```

Note: Commit hash is captured in git history, not duplicated in logs.

### Step 4: Update Iterations Log

Append entry to iterations.json BEFORE committing:

```bash
.opencode/scripts/lib/osx iterations append "$1" \
  --phase ARCHIVE \
  --iteration N \
  --notes "Change archived and committed successfully" \
  --extra '{"archive_path":"openspec/changes/archive/YYYY-MM-DD-$1/"}'
```

Note: Commit hash is captured in git history, not duplicated in logs.

### Step 5: Commit Archive

1. Invoke osx-commit skill
2. Commit all archived files and log updates:

   ```bash
   git add openspec/changes/archive/
   git commit -m "Archive change $1"
   ```

Note: After archiving, the change directory moves to archive/. The osc-* functions automatically detect this and will continue to work.

## VERIFICATION CHECKLIST

Before finishing this invocation, verify ALL items are complete:

- [ ] Transient files deleted (state.json, complete.json, .openspec-baseline.json)
- [ ] Archive directory created at `openspec/changes/archive/YYYY-MM-DD-$1/`
- [ ] Decision log entry appended with archive path
- [ ] Iterations log entry appended with archive path
- [ ] Git commit created (includes all log updates in archive)

**If ANY step is missing, the phase is incomplete and must be finished before stopping.**

## COMPLETION

After PHASE6 archive:
1. The change is now in `openspec/changes/archive/YYYY-MM-DD-$1/`
2. Transient files (state.json, complete.json, baseline) were deleted before archiving
3. Historical files (iterations.json, decision-log.json) are preserved in archive
4. The orchestrator detects completion by archive directory existence
5. No cleanup needed after this phase (already clean)

## BLOCKER HANDLING

If you encounter an unrecoverable issue that prevents progress:

```bash
.opencode/scripts/lib/osx complete set "$1" BLOCKED --blocker-reason "[Describe the specific blocking issue]"
```

The orchestrator will detect this and halt the workflow.

**When to use:**
- Archive operation fails and cannot be retried
- File permissions prevent moving change to archive
- Critical files missing from change directory
