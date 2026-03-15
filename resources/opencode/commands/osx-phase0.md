---
description: PHASE0 - Artifact Review
agent: osx-analyzer
---

## Tools Available

| Tool | Usage |
|------|-------|
| `osx` | `.opencode/scripts/lib/osx <domain> <action> [args]` - unified OpenSpec tool |
| Domains: `ctx`, `state`, `iterations`, `log`, `complete`, `validate` |

# PHASE0: Artifact Review

Change: $1

## MANDATORY START

1. Load context:
  !`.opencode/scripts/lib/osx ctx get "$1"`
2. Confirm `phase` is PHASE0
3. Review `history.iterations_recorded` for previous attempts
4. Load skill: `.opencode/skills/osx-concepts/SKILL.md` (reference only)

## PURPOSE

Ensure OpenSpec artifacts are excellent before implementation. Validate:
- Format (required sections, correct headers, checkbox syntax)
- Content quality (specificity, SHALL/MUST usage, clarity)
- Implementation readiness (dependencies, scope achievability, task specificity)
- Cross-artifact consistency (proposal→specs, specs→design, design→tasks)

## PROCESS

1. Load and use `osx-review-artifacts` skill for change "$1"
2. Execute review instructions from the skill
3. Review findings:
   - **CRITICAL**: Must fix before implementation (blocks progress)
   - **WARNING**: Should fix, may cause issues during implementation
   - **SUGGESTION**: Nice to have, non-blocking

4. IF CRITICAL or WARNING issues found:
    **YOU MUST FIX THEM IMMEDIATELY IN THIS SAME INVOCATION - DO NOT WAIT FOR NEXT ITERATION**
    a. For each issue, use `osx-modify-artifacts` skill to fix it NOW
    b. Track iteration via `osx log` and `osx iterations`
    c. After fixing all CRITICAL/WARNING issues, re-run review to verify fixes
    d. Only report "Recommendation: Fix issues" if you are UNABLE to fix them

5. IF CLEAN (no CRITICAL or WARNING issues):
    a. Log completion via `osx log`
    b. Mark phase complete via `osx state`
    c. Script will advance to PHASE1

6. IF MAX ITERATIONS (5) reached without clean review:
    a. Document all remaining CRITICAL issues via `osx log`
   b. Create `complete.json` with CRITICAL BLOCKER status (workflow stops)

## MANDATORY END

IF artifacts were modified during this phase:

1. Invoke osx-commit skill
2. Commit changes:

   ```bash
   git add openspec/changes/$1/
   git commit -m "Review and iterate artifacts for $1"
   ```

3. Record commit hash in decision log

## STATE FILE UPDATES

Phase complete (clean review):
```bash
.opencode/scripts/lib/osx state complete "$1"
```

Critical blocker (cannot proceed):
```bash
.opencode/scripts/lib/osx complete set "$1" BLOCKED --blocker-reason "[Describe the blocking issue]"
```

## DECISION LOG

Append entry:
```bash
.opencode/scripts/lib/osx log append "$1" \
  --phase ARTIFACT_REVIEW \
  --iteration N \
  --summary "Brief summary of this iteration" \
  --commit-hash "<hash or null>" \
  --next-steps "Proceed to PHASE1 or continue review" \
  --issues '{"critical":N,"warning":N,"suggestion":N}' \
  --artifacts-modified '["proposal.md","specs/auth.md"]' \
  --extra '{"issues_fixed":{"critical":N,"warning":N,"suggestion":N}}'
```

## ITERATIONS.JSON

Append entry:
```bash
.opencode/scripts/lib/osx iterations append "$1" \
  --phase ARTIFACT_REVIEW \
  --iteration N \
  --commit-hash "<hash or null>" \
  --notes "Brief summary" \
  --extra '{"artifacts_reviewed":["proposal","specs","design","tasks"],"issues_found":{"critical":N,"warning":N,"suggestion":N},"issues_fixed":{"critical":N,"warning":N,"suggestion":N}}'
```

## GUARDRAILS

- Must fix CRITICAL issues before proceeding
- Max 5 review iterations
- One commit at end of phase if artifacts were modified
- Early exit if first review returns clean
