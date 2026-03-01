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

## STATE FILE UPDATES

Phase complete (verification passed):
```bash
.opencode/scripts/lib/osc-state "$1" complete
```

## DECISION LOG

Append entry:
```bash
echo '{
  "phase": "REVIEW",
  "iteration": N,
  "summary": "Verification results summary",
  "verification_result": "passed|failed",
  "issues_found": {"critical": N, "warning": N, "suggestion": N},
  "verification_report": "[Paste skill report here]",
  "artifacts_modified": false,
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
  "notes": "Brief summary"
}' | .opencode/scripts/lib/osc-iterations "$1" append
```

## TRANSITION

- Verification passed → PHASE3 (MAINTAIN-DOCS)
- Verification failed (artifacts modified) → PHASE1 (IMPLEMENTATION) restart
