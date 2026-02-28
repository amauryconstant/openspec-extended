---
description: PHASE1 - Implementation
agent: openspec-builder
metadata:
   version: "0.1.0"
---

# PHASE1: Implementation

Change: $1

## MANDATORY START

1. Read `.opencode/skills/openspec-concepts/SKILL.md` (reference only)
2. Read `openspec/changes/$1/state.json` to confirm phase is PHASE1
3. Read `openspec/changes/$1/decision-log.md` (if exists) to understand previous work
4. Read `openspec/changes/$1/iterations.json` (if exists) to understand iteration history
5. Read context files: `openspec/changes/$1/proposal.md`, `openspec/changes/$1/specs/`, `openspec/changes/$1/design.md`, `openspec/changes/$1/tasks.md`
6. Determine which tasks to implement this iteration

## MANDATORY CHECKPOINT: CLI Output Logging

Before beginning implementation:

1. Run: `openspec status --change "$1" --json`
2. Append to `openspec/changes/$1/decision-log.md`:
   ```
   ## CLI Output: openspec status (Iteration N)
   ```json
   <paste exact CLI output here>
   ```
   ```

3. Run: `openspec instructions apply --change "$1" --json`
4. Append to `openspec/changes/$1/decision-log.md`:
   ```
   ## CLI Output: openspec instructions apply (Iteration N)
   ```json
   <paste exact CLI output here>
   ```
   ```

## PURPOSE

Implement tasks from the change, making logical milestone commits and validating test coverage.

## PROCESS

1. Load skill: Use `openspec-apply-change` skill for change "$1"
2. Execute skill instructions exactly - do NOT deviate from the skill's workflow
3. Implement tasks:
   - Read tasks.md to identify unchecked tasks
   - Implement tasks sequentially
   - Mark tasks complete: `- [ ]` → `- [x]`
   - Continue until all tasks complete OR iteration limit reached

4. Make milestone commits:
   - Commit after completing logical work units
   - Subject: imperative verb + brief description (40-72 chars)
   - Use `git diff --staged` to review before committing
   - Minimum 1 commit per iteration
   - Maximum 5 commits per iteration

5. After implementation complete:
   - Run `openspec-review-test-compliance` skill
   - Analyze spec-to-test alignment
   - IF gaps found: Implement missing tests, commit, re-run
   - UNTIL: Clean or only suggestions remain

## COMMIT PROTOCOL

When making commits, follow this priority order:

1. Check for dedicated commit skills in `.opencode/skills/commit/SKILL.md`
2. Check project's AGENTS.md for commit conventions
3. Default workflow:
   - Make logical, atomic commits after completing coherent work units
   - Review staged changes: `git diff --staged`
   - Commit with clear, descriptive messages

4. Pre-commit hook guardrails (ALWAYS apply):
   - NEVER use `--no-verify` to bypass pre-commit hooks
   - If pre-commit hooks fail, fix the issues
   - Re-run the commit after fixing - hooks must pass

5. Persistent failures: If fixes aren't possible within 3 attempts:
   - Document the issue in decision-log.md
   - Consider if artifacts need modification
   - May need to signal COMPLETE with blocker_reason

## ERROR HANDLING

- If git commit fails: Check staged files, verify working directory clean, retry once
- If tests fail repeatedly (>3 attempts): Use subagent to debug, check spec clarity
- If stuck in iteration loop (>3 iterations with no progress): Document blocker, signal COMPLETE
- If openspec CLI commands fail: Proceed without CLI output, document in decision-log.md

## STATE FILE UPDATES

When all tasks are complete:
```bash
jq '.phase_complete = true' openspec/changes/$1/state.json > tmp && mv tmp openspec/changes/$1/state.json
```

## DECISION LOG FORMAT

Append to `openspec/changes/$1/decision-log.md`:

```markdown
## Iteration N

### Date
YYYY-MM-DD

### Phase
IMPLEMENTATION

### CLI Output (MANDATORY)

## CLI Output: openspec status
```json
<paste exact output>
```

## CLI Output: openspec instructions apply
```json
<paste exact output>
```

### Work Done

#### Assumptions Made (Iteration-Level)
- [Assumption 1]: Brief description with rationale
  - Justification: Why this is reasonable
  - Files affected: path/to/file:line-range

#### Tasks Completed:
- [x] Task ID: Description
  - Decision: What you decided
  - Why: Rationale
  - Files affected: path/to/file:line-range

### Session Summary
[Summary of what was accomplished this iteration]

### Next Steps
[What you plan to do next iteration]
```

## ITERATIONS.JSON FORMAT

Append to `openspec/changes/$1/iterations.json`:

```json
{
  "iteration": N,
  "phase": "IMPLEMENTATION",
  "tasks_completed": ["1.1", "1.2", "1.3"],
  "tasks_remaining": 0,
  "tasks_this_session": 3,
  "cli_status": {},
  "cli_instructions": {},
  "errors": [],
  "notes": "Brief summary"
}
```

## TRANSITION

When all tasks in `tasks.md` are marked complete `[x]`:
- Log: "All tasks complete, transitioning to PHASE2 (REVIEW)"
- Update `state.json`: Set `"phase_complete": true`
- Script will advance to PHASE2
