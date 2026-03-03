---
description: PHASE1 - Implementation
agent: openspec-builder
---

## Tools Available

| Tool | Type | Usage |
|------|------|-------|
| `openspec` | Upstream CLI | `openspec <command> [options]` - npm package |
| `osc-ctx` | Local script | `.opencode/scripts/lib/osc-ctx <change>` - load change context |
| `osc-state` | Local script | `.opencode/scripts/lib/osc-state <change> <action>` - manage state |
| `osc-log` | Local script | `.opencode/scripts/lib/osc-log <change> <action>` - decision log |
| `osc-iterations` | Local script | `.opencode/scripts/lib/osc-iterations <change> <action>` - iteration history |
| `osc-complete` | Local script | `.opencode/scripts/lib/osc-complete <change> <action>` - signal blocker status |

# PHASE1: Implementation

Change: $1

## MANDATORY START

1. Load context:
  !`.opencode/scripts/lib/osc-ctx "$1"`
2. Confirm `phase` is PHASE1
3. Review `history.iterations_recorded` for previous attempts
4. Load skill: `.opencode/skills/openspec-concepts/SKILL.md` (reference only)
5. Read context files: `openspec/changes/$1/proposal.md`, `openspec/changes/$1/specs/`, `openspec/changes/$1/design.md`, `openspec/changes/$1/tasks.md`
6. Determine which tasks to implement this iteration

## MANDATORY CHECKPOINT: CLI Output Logging

Before beginning implementation:

1. Run: `openspec status --change "$1" --json`
2. Log via `osc-log` with `cli_status` field
3. Run: `openspec instructions apply --change "$1" --json`
4. Log via `osc-log` with `cli_instructions` field

## PURPOSE

Implement tasks from the change, making logical milestone commits and validating test coverage.

## PROCESS

### 1. Load Implementation Skill

Load skill: Use `openspec-apply-change` skill for change "$1"

The skill provides the implementation workflow. Follow its task execution pattern.

### 2. Implement Tasks

Per the skill workflow:
- Read tasks.md to identify unchecked tasks
- Implement tasks sequentially
- Mark tasks complete: `- [ ]` → `- [x]`
- Continue until all tasks complete OR iteration limit reached

### 3. MANDATORY: Milestone Commits

**You MUST commit after completing logical work units.**

- Minimum 1 commit per iteration
- Maximum 5 commits per iteration
- Subject: imperative verb + brief description (40-72 chars)
- Review staged changes: `git diff --staged` before committing

**Commit message priority:**
1. Check for dedicated commit skills in `.opencode/skills/commit/SKILL.md`
2. Check project's AGENTS.md for commit conventions
3. Default: logical, atomic commits with clear, descriptive messages

**Pre-commit hook guardrails (ALWAYS apply):**
- NEVER use `--no-verify` to bypass pre-commit hooks
- If pre-commit hooks fail, fix the issues
- Re-run the commit after fixing - hooks must pass

**Persistent failures:** If fixes aren't possible within 3 attempts:
- Document the issue via `osc-log`
- Consider if artifacts need modification
- May need to signal COMPLETE with blocker_reason

**Documentation scope for PHASE1:**
- ✅ Inline code comments
- ✅ README updates for new features
- ✅ Package-level doc.go files
- ✅ CLI help text and usage strings
- ❌ AGENTS.md files → Deferred to PHASE3

**Why AGENTS.md is deferred:**
AGENTS.md files document the codebase structure for future AI sessions. They should be updated AFTER all implementation is complete to ensure accurate representation of the final state. PHASE3 handles this.

### 4. Validate Test Coverage

After implementation complete:
- Run `openspec-review-test-compliance` skill
- Analyze spec-to-test alignment
- IF gaps found: Implement missing tests, commit, re-run
- UNTIL: Clean or only suggestions remain

## ERROR HANDLING

- If git commit fails: Check staged files, verify working directory clean, retry once
- If tests fail repeatedly (>3 attempts): Use subagent to debug, check spec clarity
- If stuck in iteration loop (>3 iterations with no progress): Document blocker, signal COMPLETE
- If openspec CLI commands fail: Proceed without CLI output, document via `osc-log`

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
- Pre-commit hook failures that cannot be resolved after 3 attempts
- Implementation fundamentally blocked by unclear or contradictory specs
- External dependencies unavailable or broken
- Task cannot be completed due to missing information

## STATE FILE UPDATES

When all tasks are complete:
```bash
.opencode/scripts/lib/osc-state "$1" complete
```

## DECISION LOG

Append entry:
```bash
echo '{
  "phase": "IMPLEMENTATION",
  "iteration": N,
  "summary": "What was accomplished this iteration",
  "assumptions": ["Assumption with rationale"],
  "tasks_completed": ["1.1", "1.2"],
  "tasks_remaining": 0,
  "commits_made": N,
  "cli_status": {},
  "cli_instructions": {},
  "errors": [],
  "next_steps": "Continue implementation or transition to PHASE2"
}' | .opencode/scripts/lib/osc-log "$1" append
```

## ITERATIONS.JSON

Append entry:
```bash
echo '{
  "iteration": N,
  "phase": "IMPLEMENTATION",
  "tasks_completed": ["1.1", "1.2", "1.3"],
  "tasks_remaining": 0,
  "tasks_this_session": 3,
  "commits_made": N,
  "cli_status": {},
  "cli_instructions": {},
  "errors": [],
  "notes": "Brief summary"
}' | .opencode/scripts/lib/osc-iterations "$1" append
```

## TRANSITION

When all tasks in `tasks.md` are marked complete `[x]`:
- Log: "All tasks complete, transitioning to PHASE2 (REVIEW)"
- Mark phase complete via `osc-state`
- Script will advance to PHASE2

Note: AGENTS.md updates will occur in PHASE3 (MAINTAIN DOCS), not here. Even if tasks.md contains AGENTS.md tasks, they should be deferred to PHASE3.
