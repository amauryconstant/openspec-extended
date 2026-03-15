---
description: PHASE2 - Verification
agent: osx-analyzer
---

## Tools Available

| Tool | Type | Usage |
|------|------|-------|
| `openspec` | Upstream CLI | `openspec <command> [options]` - npm package |
| `osx` | Local script | `.opencode/scripts/lib/osx <domain> <action> [args]` - unified OpenSpec tool |
| Domains: `ctx`, `state`, `iterations`, `log`, `complete`, `validate` |

# PHASE2: Verification

Change: $1

## MANDATORY START

1. Load context:
  !`.opencode/scripts/lib/osx ctx get "$1"`
2. Confirm `phase` is PHASE2
3. Review `history.iterations_recorded` for previous attempts
4. Load skill: `.opencode/skills/osx-concepts/SKILL.md` (reference only)

## MANDATORY CHECKPOINT: CLI Output Logging

Before starting PHASE2:

1. Run: `openspec status --change "$1" --json`
2. Log via `osx log` with `cli_status` field
3. Run: `openspec instructions apply --change "$1" --json`
4. Log via `osx log` with `cli_instructions` field

## PURPOSE

Validate implementation matches artifacts - completeness, correctness, coherence.

## PROCESS

1. Load and use `osx-verify-change` skill for change "$1"
2. Execute the skill's verification instructions exactly
3. Log the verification report via `osx log` in `verification_report` field
4. Do NOT modify the skill's verification report format

The skill provides:
- Verification dimensions (completeness, correctness, coherence)
- Issue classification (CRITICAL, WARNING, SUGGESTION)
- Specific recommendations for each issue

## AFTER VERIFICATION

IF CRITICAL OR WARNING ISSUES FOUND:

First, determine the root cause:

**Case A: Artifacts are wrong (specs/design unclear or incomplete)**
1. Use `osx-modify-artifacts` skill to fix artifacts
2. Commit the artifact changes
3. Signal transition back to PHASE1:
   ```bash
   .opencode/scripts/lib/osx state transition "$1" PHASE1 artifacts_modified "Brief description of what was fixed"
   ```
4. Log: "Artifacts modified, transitioning to PHASE1 for re-implementation"

**Case B: Artifacts are correct, implementation is wrong**
1. DO NOT modify artifacts
2. Signal transition back to PHASE1:
   ```bash
   .opencode/scripts/lib/osx state transition "$1" PHASE1 implementation_incorrect "Brief description of what needs fixing"
   ```
3. Log: "Implementation incorrect, transitioning to PHASE1 for fixes"

**Case C: Same phase needs retry with different approach**
1. Signal retry:
   ```bash
   .opencode/scripts/lib/osx state transition "$1" PHASE2 retry_requested "Brief description of alternative approach"
   ```
2. Log: "Requesting retry with different approach"

IF NO CRITICAL OR WARNING ISSUES (SUGGESTIONS OK):

1. Log: "Verification passed, no CRITICAL or WARNING issues"
2. Log any SUGGESTION issues for future reference
3. Mark phase complete via `osx state`:
   ```bash
   .opencode/scripts/lib/osx state complete "$1"
   ```
4. Script will advance to PHASE3

## SUGGESTION TRACKING

IF SUGGESTION issues found (even if verification passed):

1. Create or append to suggestions.md:

```bash
cat >> "openspec/changes/$1/suggestions.md" <<EOF

## $(date -u +%Y-%m-%d) - PHASE2 Verification

- [ ] **[cosmetic]** Brief description
  - Location: file:line
  - Impact: Low
  - Notes: Optional context

EOF
```

2. Categories:
   - `[cosmetic]` - Typos, minor grammar, formatting
   - `[performance]` - Optimization opportunities
   - `[future]` - Future enhancement ideas
   - `[docs]` - Documentation improvements

3. Each suggestion is a checkbox for future follow-up

4. This file will be archived with the change for future reference

## MANDATORY END

IF artifacts were modified during this phase (CRITICAL/WARNING fixes):

1. Invoke osx-commit skill
2. Commit changes:

   ```bash
   git add openspec/changes/$1/
   git commit -m "Fix artifacts after verification for $1"
   ```

3. Record commit hash in decision log and iterations.json

## STATE FILE UPDATES

Phase complete (verification passed):
```bash
.opencode/scripts/lib/osx state complete "$1"
```

## DECISION LOG

Write verification report to file, then log:

```bash
# Write verification report (full markdown allowed)
cat > "openspec/changes/$1/verification-report.md" << 'EOF'
## Verification Report: $1

### Summary
| Dimension    | Status                        |
|--------------|-------------------------------|
| Completeness | X/X tasks, X/X reqs covered   |
| Correctness  | X/X reqs implemented          |
| Coherence    | Design followed               |

### CRITICAL Issues (Must fix before archive)
None.

### WARNING Issues (Should fix)
None.

### SUGGESTION Issues (Nice to fix)
None.

### Detailed Findings
[Full verification details here]

### Final Assessment
[PASS/FAIL with reasoning]
EOF

# Log with path reference (not inline content)
.opencode/scripts/lib/osx log append "$1" \
  --phase REVIEW \
  --iteration N \
  --summary "Verification results summary" \
  --commit-hash "<hash or null>" \
  --next-steps "Proceed to PHASE3 or restart PHASE1" \
  --extra '{"verification_result":"passed|failed","issues_found":{"critical":N,"warning":N,"suggestion":N},"verification_report_path":"openspec/changes/$1/verification-report.md","artifacts_modified":false}'
```

## ITERATIONS.JSON

Append entry:
```bash
.opencode/scripts/lib/osx iterations append "$1" \
  --phase REVIEW \
  --iteration N \
  --commit-hash "<hash or null>" \
  --notes "Brief summary" \
  --extra '{"verification_result":"passed|failed","issues_found":{"critical":N,"warning":N,"suggestion":N},"artifacts_modified":false}'
```

## TRANSITION

Use `osx state transition` for explicit phase control:

| Scenario | Command | Reason |
|----------|---------|--------|
| Artifacts fixed | `osx state transition "$1" PHASE1 artifacts_modified "..."` | Specs/design updated, re-implement |
| Implementation wrong | `osx state transition "$1" PHASE1 implementation_incorrect "..."` | Artifacts correct, code needs fix |
| Retry with new approach | `osx state transition "$1" PHASE2 retry_requested "..."` | Try different solution |
| Verification passed | `osx state complete "$1"` | Normal advance to PHASE3 |
