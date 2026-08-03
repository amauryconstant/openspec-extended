---
description: PHASE6 - Archive Change
agent: osx-maintainer
---

# PHASE6: Archive Change

Change: $1

> **Tools** — see `osx-workflow` §1.

## ATOMIC EXECUTION REQUIREMENT

⚠️ **CRITICAL**: All steps in this phase MUST complete in a SINGLE agent invocation.

- Do NOT stop after archiving files.
- Do NOT stop after committing changes.
- Do NOT stop until Step 4 (commit archive) is finished.
- Partial completion triggers unnecessary re-execution of this phase.

## MANDATORY START

See `references/phase-protocol-common.md#mandatory-start`. **PHASE6 exception**: this phase does NOT call `osx state complete`. The orchestrator detects completion by archive directory existence.

## PURPOSE

Archive the completed change for historical reference.

## REQUIRED SEQUENCE (ALL STEPS)

Complete ALL of these steps in order, without stopping. Transient state files (`state.json`, `complete.json`, `.openspec-baseline.json`, `.osx-orchestrate-<change>.log`) are removed by the orchestrator on success — do NOT delete them from this phase (the orchestrator needs the auto-log to move it into the archive after the archive commit).

### Step 1: Execute Archive

1. Load skill: `osc-archive-change` (originally `openspec-archive-change`).
2. Verify completion status: `tasks.md` all checked, delta spec sync state correct.
3. Verify files to archive: `iterations.json`, `decision-log.json`, `verification-report.md`, `reflections.md`, `test-compliance-report.md`, `suggestions.md`.
4. Perform archive: skill moves change to `openspec/changes/archive/YYYY-MM-DD-$1/`.

### Step 2: Update Decision Log

```bash
openspec-extended osx log append "$1" --phase ARCHIVE --iteration N \
  --summary "Change successfully archived" --next-steps "Archive complete. Workflow finished." \
  --extra '{"archive_path":"openspec/changes/archive/YYYY-MM-DD-$1/"}'
```

Commit hash captured in git history, not duplicated in logs.

### Step 3: Update Iterations Log

```bash
openspec-extended osx iterations append "$1" --phase ARCHIVE --iteration N \
  --notes "Change archived and committed successfully" \
  --extra '{"archive_path":"openspec/changes/archive/YYYY-MM-DD-$1/"}'
```

### Step 4: Commit Archive

Invoke `osx-commit` skill. Commit all archived files and log updates:

```bash
git add openspec/changes/archive/
git commit -m "Archive change $1"
```

After archiving, the change directory moves to `archive/`. The `osc-*` functions automatically detect this.

## VERIFICATION CHECKLIST

Before finishing this invocation, verify ALL items are complete:

- [ ] Archive directory created at `openspec/changes/archive/YYYY-MM-DD-$1/`
- [ ] Decision log entry appended with archive path
- [ ] Iterations log entry appended with archive path
- [ ] Git commit created (includes all log updates in archive)
- [ ] Transient files NOT deleted by this phase (orchestrator handles cleanup)

**If ANY step is missing, the phase is incomplete and must be finished before stopping.**

## COMPLETION

After PHASE6 archive: the change is in `openspec/changes/archive/YYYY-MM-DD-$1/`. Historical files are preserved. The orchestrator detects completion by archive directory existence, moves `.osx-orchestrate-<change>.log` into the archive and amends the archive commit on success. Transient state files are removed by the orchestrator's success path.

## BLOCKER HANDLING

See `references/blocker-semantics.md` for the canonical signal. Phase-specific reasons:

- Archive operation fails and cannot be retried
- File permissions prevent moving change to archive
- Critical files missing from change directory

## SHELL ARGUMENT SAFETY

See `references/shell-argument-safety.md`.
<!--
# AUTO-GENERATED from opencode via `mise run sync:mirrors` — do not edit by hand.
Source: resources/opencode/commands/osx-phase6.md
Regenerate: `mise run sync:mirrors`
-->
