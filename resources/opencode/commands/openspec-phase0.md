---
description: PHASE0 - Artifact Review
agent: openspec-analyzer
metadata:
   version: "0.1.0"
---

# PHASE0: Artifact Review

Change: $1

## MANDATORY START

1. Read `.opencode/skills/openspec-concepts/SKILL.md` (reference only)
2. Read `openspec/changes/$1/state.json` to confirm phase is PHASE0
3. Read `openspec/changes/$1/decision-log.md` (if exists) to understand previous work
4. Read `openspec/changes/$1/iterations.json` (if exists) to understand iteration history

## PURPOSE

Ensure OpenSpec artifacts are excellent before implementation. Validate:
- Format (required sections, correct headers, checkbox syntax)
- Content quality (specificity, SHALL/MUST usage, clarity)
- Implementation readiness (dependencies, scope achievability, task specificity)
- Cross-artifact consistency (proposal→specs, specs→design, design→tasks)

## PROCESS

1. Load and use `openspec-review-artifacts` skill for change "$1"
2. Execute review instructions from the skill
3. Review findings:
   - **CRITICAL**: Must fix before implementation (blocks progress)
   - **WARNING**: Should fix, may cause issues during implementation
   - **SUGGESTION**: Nice to have, non-blocking

4. IF CRITICAL or WARNING issues found:
   a. For each issue, use `openspec-modify-artifacts` skill to fix it
   b. Track iteration count in `iterations.json`
   c. After fixing all CRITICAL/WARNING issues, re-run review
   d. Repeat until clean or max iterations (5) reached

5. IF CLEAN (no CRITICAL or WARNING issues):
   a. Log: "Artifact review complete - artifacts are excellent"
   b. IF artifacts were modified during this phase:
      - Make commit: "Review and iterate artifacts for $1"
   c. Update `state.json`: Set `"phase_complete": true`
   d. Script will advance to PHASE1

6. IF MAX ITERATIONS (5) reached without clean review:
   a. Log: "Artifact review failed - cannot resolve CRITICAL issues"
   b. Document all remaining CRITICAL issues in `decision-log.md`
   c. Create `complete.json` with CRITICAL BLOCKER status (workflow stops)

## STATE FILE UPDATES

Phase complete (clean review):
```bash
jq '.phase_complete = true' openspec/changes/$1/state.json > tmp && mv tmp openspec/changes/$1/state.json
```

Critical blocker (cannot proceed):
```bash
cat > openspec/changes/$1/complete.json << 'EOF'
{
  "status": "COMPLETE",
  "with_blocker": true,
  "blocker_reason": "[Describe the blocking issue]",
  "timestamp": "[current timestamp]"
}
EOF
```

## DECISION LOG FORMAT

Append to `openspec/changes/$1/decision-log.md`:

```markdown
## PHASE0 - ARTIFACT REVIEW (Iteration N)

### Issues Found
- CRITICAL: [Issue description]
  - Fix action taken: [description]
- WARNING: [Issue description]
  - Fix action taken: [description]

### Modified Artifacts
- [x] proposal.md: [Summary of changes]
- [x] specs/auth.md: [Summary of changes]

### Session Summary
[Summary of this iteration]

### Next Steps
[Plan for next iteration or transition to PHASE1]
```

## ITERATIONS.JSON FORMAT

Append to `openspec/changes/$1/iterations.json`:

```json
{
  "iteration": N,
  "phase": "ARTIFACT_REVIEW",
  "artifacts_reviewed": ["proposal", "specs", "design", "tasks"],
  "issues_found": {"critical": N, "warning": N, "suggestion": N},
  "issues_fixed": {"critical": N, "warning": N, "suggestion": N},
  "notes": "Brief summary"
}
```

## GUARDRAILS

- Must fix CRITICAL issues before proceeding
- Max 5 review iterations
- One commit at end of phase, not per fix
- Early exit if first review returns clean
