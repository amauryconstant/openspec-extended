---
description: PHASE2 - Verification
agent: openspec-analyzer
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

# PHASE2: Verification

Change: $1

## MANDATORY START

1. Load context:
  !`.opencode/scripts/lib/osc-ctx "$1"`
2. Confirm `phase` is PHASE2
3. Review `history.iterations_recorded` for previous attempts
4. Load skill: `.opencode/skills/openspec-concepts/SKILL.md` (reference only)

## MANDATORY CHECKPOINT: CLI Output Logging

Before starting PHASE2:

1. Run: `openspec status --change "$1" --json`
2. Log via `osc-log` with `cli_status` field
3. Run: `openspec instructions apply --change "$1" --json`
4. Log via `osc-log` with `cli_instructions` field

## PURPOSE

Validate implementation matches artifacts - completeness, correctness, coherence.

## PROCESS

1. Load and use `openspec-verify-change` skill for change "$1"
2. Execute the skill's verification instructions exactly
3. Log the verification report via `osc-log` in `verification_report` field
4. Do NOT modify the skill's verification report format

The skill provides:
- Verification dimensions (completeness, correctness, coherence)
- Issue classification (CRITICAL, WARNING, SUGGESTION)
- Specific recommendations for each issue

## AFTER VERIFICATION

IF CRITICAL OR WARNING ISSUES FOUND:

1. Use `openspec-modify-artifacts` skill to fix artifacts
2. Log: "Artifacts modified, restarting implementation"
3. Next iteration will resume at PHASE1
4. DO NOT continue to PHASE3

IF NO CRITICAL OR WARNING ISSUES (SUGGESTIONS OK):

1. Log: "Verification passed, no CRITICAL or WARNING issues"
2. Log any SUGGESTION issues for future reference
3. Mark phase complete via `osc-state`
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

```bash
git add openspec/changes/$1/
git commit -m "Fix artifacts after verification for $1"
```

Record commit hash in decision log and iterations.json.

## STATE FILE UPDATES

Phase complete (verification passed):
```bash
.opencode/scripts/lib/osc-state "$1" complete
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
echo '{
  "phase": "REVIEW",
  "iteration": N,
  "summary": "Verification results summary",
  "verification_result": "passed|failed",
  "issues_found": {"critical": N, "warning": N, "suggestion": N},
  "verification_report_path": "openspec/changes/$1/verification-report.md",
  "artifacts_modified": false,
  "commit_hash": "<hash or null>",
  "next_steps": "Proceed to PHASE3 or restart PHASE1"
}' | .opencode/scripts/lib/osc-log "$1" append
```

## ITERATIONS.JSON

Append entry:
```bash
echo '{
  "iteration": N,
  "phase": "REVIEW",
  "verification_result": "passed|failed",
  "issues_found": {"critical": N, "warning": N, "suggestion": N},
  "artifacts_modified": false,
  "commit_hash": "<hash or null>",
  "notes": "Brief summary"
}' | .opencode/scripts/lib/osc-iterations "$1" append
```

## TRANSITION

- Verification passed → PHASE3 (MAINTAIN DOCS)
- Verification failed (artifacts modified) → PHASE1 (IMPLEMENTATION) restart
