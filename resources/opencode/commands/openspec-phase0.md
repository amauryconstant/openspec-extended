---
description: PHASE0 - Artifact Review
agent: openspec-analyzer
---

## Tools Available

| Tool | Usage |
|------|-------|
| `osc-ctx` | `.opencode/scripts/lib/osc-ctx <change>` - load change context |
| `osc-state` | `.opencode/scripts/lib/osc-state <change> <action>` - manage state |
| `osc-log` | `.opencode/scripts/lib/osc-log <change> <action>` - decision log |
| `osc-iterations` | `.opencode/scripts/lib/osc-iterations <change> <action>` - iteration history |

# PHASE0: Artifact Review

Change: $1

## MANDATORY START

1. Load context:
  !`.opencode/scripts/lib/osc-ctx "$1"`
2. Confirm `phase` is PHASE0
3. Review `history.iterations_recorded` for previous attempts
4. Load skill: `.opencode/skills/openspec-concepts/SKILL.md` (reference only)

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
   **YOU MUST FIX THEM IMMEDIATELY IN THIS SAME INVOCATION - DO NOT WAIT FOR NEXT ITERATION**
   a. For each issue, use `openspec-modify-artifacts` skill to fix it NOW
   b. Track iteration via `osc-log` and `osc-iterations`
   c. After fixing all CRITICAL/WARNING issues, re-run review to verify fixes
   d. Only report "Recommendation: Fix issues" if you are UNABLE to fix them

5. IF CLEAN (no CRITICAL or WARNING issues):
   a. Log completion via `osc-log`
   b. Mark phase complete via `osc-state`
   c. Script will advance to PHASE1

6. IF MAX ITERATIONS (5) reached without clean review:
   a. Document all remaining CRITICAL issues via `osc-log`
   b. Create `complete.json` with CRITICAL BLOCKER status (workflow stops)

## MANDATORY END

Before transitioning to PHASE1, IF artifacts were modified during this phase:

```bash
git add openspec/changes/$1/
git commit -m "Review and iterate artifacts for $1"
```

Record commit hash in decision log.

## STATE FILE UPDATES

Phase complete (clean review):
```bash
.opencode/scripts/lib/osc-state "$1" complete
```

Critical blocker (cannot proceed):
```bash
echo '{
  "status": "COMPLETE",
  "with_blocker": true,
  "blocker_reason": "[Describe the blocking issue]",
  "timestamp": "'$(date -u +%Y-%m-%dT%H:%M:%SZ)'"
}' > openspec/changes/$1/complete.json
```

## DECISION LOG

Append entry:
```bash
echo '{
  "phase": "ARTIFACT_REVIEW",
  "iteration": N,
  "summary": "Brief summary of this iteration",
  "issues": {"critical": N, "warning": N, "suggestion": N},
  "issues_fixed": {"critical": N, "warning": N, "suggestion": N},
  "artifacts_modified": ["proposal.md", "specs/auth.md"],
  "commit_hash": "<hash or null>",
  "next_steps": "Proceed to PHASE1 or continue review"
}' | .opencode/scripts/lib/osc-log "$1" append
```

## ITERATIONS.JSON

Append entry:
```bash
echo '{
  "iteration": N,
  "phase": "ARTIFACT_REVIEW",
  "artifacts_reviewed": ["proposal", "specs", "design", "tasks"],
  "issues_found": {"critical": N, "warning": N, "suggestion": N},
  "issues_fixed": {"critical": N, "warning": N, "suggestion": N},
  "commit_hash": "<hash or null>",
  "notes": "Brief summary"
}' | .opencode/scripts/lib/osc-iterations "$1" append
```

## GUARDRAILS

- Must fix CRITICAL issues before proceeding
- Max 5 review iterations
- One commit at end of phase if artifacts were modified
- Early exit if first review returns clean
