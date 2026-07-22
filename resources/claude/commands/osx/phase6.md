---
name: osx-phase6
description: PHASE6 - Archive Change
category: openspec-orchestrator
tags: [openspec-extended, autonomous, orchestrator]
license: MIT
---

## Tools Available

| Tool | Usage |
|------|-------|
| `osx` | `openspec-extended osx <domain> <action> [args]` - unified OpenSpec tool |
| Domains: `ctx`, `state`, `iterations`, `log`, `complete`, `validate` |

# PHASE6: Archive Change

Change: $1

## ATOMIC EXECUTION REQUIREMENT

⚠️ **CRITICAL**: All steps in this phase MUST complete in a SINGLE agent invocation.

- Do NOT stop after archiving files
- Do NOT stop after committing changes
- Do NOT stop until step 4 (commit archive) is finished
- Partial completion will trigger unnecessary re-execution of this phase

## MANDATORY START

1. Load context:
   !`openspec-extended osx ctx get "$1"`
2. Confirm `phase` is PHASE6
3. Review `history.iterations_recorded` for previous attempts
4. Load skills: `osx-concepts` and `osx-workflow` (both reference only)

## PURPOSE

Archive the completed change for historical reference.

## REQUIRED SEQUENCE (ALL STEPS)

Complete ALL of these steps in order, without stopping:

Transient state files (`state.json`, `complete.json`, `.openspec-baseline.json`, `.osx-orchestrate-<change>.log`) are removed by the orchestrator on success. Do not delete them from this phase — the orchestrator needs the auto-log to move it into the archive after the archive commit.

Note: PHASE6 does NOT call `osx state complete`. The orchestrator detects completion by archive directory existence, not by state.json.

### Step 1: Execute Archive

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

### Step 2: Update Decision Log

Append entry to decision log BEFORE committing:

```bash
openspec-extended osx log append "$1" \
  --phase ARCHIVE \
  --iteration N \
  --summary "Change successfully archived" \
  --next-steps "Archive complete. Workflow finished." \
  --extra '{"archive_path":"openspec/changes/archive/YYYY-MM-DD-$1/"}'
```

Note: Commit hash is captured in git history, not duplicated in logs.

### Step 3: Update Iterations Log

Append entry to iterations.json BEFORE committing:

```bash
openspec-extended osx iterations append "$1" \
  --phase ARCHIVE \
  --iteration N \
  --notes "Change archived and committed successfully" \
  --extra '{"archive_path":"openspec/changes/archive/YYYY-MM-DD-$1/"}'
```

Note: Commit hash is captured in git history, not duplicated in logs.

### Step 4: Commit Archive

1. Invoke osx-commit skill
2. Commit all archived files and log updates:

   ```bash
   git add openspec/changes/archive/
   git commit -m "Archive change $1"
   ```

Note: After archiving, the change directory moves to archive/. The osc-* functions automatically detect this and will continue to work.

## VERIFICATION CHECKLIST

Before finishing this invocation, verify ALL items are complete:

- [ ] Archive directory created at `openspec/changes/archive/YYYY-MM-DD-$1/`
- [ ] Decision log entry appended with archive path
- [ ] Iterations log entry appended with archive path
- [ ] Git commit created (includes all log updates in archive)
- [ ] Transient files (state.json, complete.json, .openspec-baseline.json, .osx-orchestrate-*.log) NOT deleted by this phase (the orchestrator handles cleanup)

**If ANY step is missing, the phase is incomplete and must be finished before stopping.**

## COMPLETION

After PHASE6 archive:
1. The change is now in `openspec/changes/archive/YYYY-MM-DD-$1/`
2. Historical files (iterations.json, decision-log.json, verification-report.md, reflections.md, test-compliance-report.md, suggestions.md) are preserved in archive
3. The orchestrator detects completion by archive directory existence
4. The orchestrator moves `.osx-orchestrate-<change>.log` into the archive and amends the archive commit on success
5. Transient state files (state.json, complete.json, .openspec-baseline.json) are removed by the orchestrator's success path

## BLOCKER HANDLING

If you encounter an unrecoverable issue that prevents progress:

```bash
openspec-extended osx complete set "$1" BLOCKED --blocker-reason "[Describe the specific blocking issue]"
```

The orchestrator will detect this and halt the workflow.

**When to use:**
- Archive operation fails and cannot be retried
- File permissions prevent moving change to archive
- Critical files missing from change directory


## SHELL ARGUMENT SAFETY

When passing free-text to `--summary`, `--next-steps`, or any other shell argument, **DO NOT use backticks** (`` `like this` ``) for inline code references. Backticks are interpreted as command substitution by bash/zsh — the shell will execute whatever is inside the backticks and substitute its output. In zsh, `` `local` `` dumps the entire shell environment (PATH, tokens, internal variables) into your string, which then gets stored verbatim in `decision-log.json`.

**Use instead:**

- Single quotes: `'local'`
- Double quotes: `"local"`
- Plain text: `local`
- Markdown `code` (which uses backticks in raw form, NOT shell backticks) — fine only when the argument is not passed through a shell

If `osx log append` returns `input_too_long` or `input_tainted`, remove the backticks from the offending argument and retry.
