---
description: PHASE2 - Verification
agent: openspec-analyzer
subtask: true
version: "0.1.0"
---

# PHASE2: Verification

Change: $1

## MANDATORY START

1. Read `.opencode/skills/openspec-concepts/SKILL.md` (reference only)
2. Read `openspec/changes/$1/state.json` to confirm phase is PHASE2
3. Read `openspec/changes/$1/decision-log.md` (if exists) to understand previous work
4. Read `openspec/changes/$1/iterations.json` (if exists) to understand iteration history

## MANDATORY CHECKPOINT: CLI Output Logging

Before starting PHASE2:

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

Validate implementation matches artifacts - completeness, correctness, coherence.

## PROCESS

1. Load and use `openspec-verify-change` skill for change "$1"
2. Execute the skill's verification instructions exactly
3. Append the skill's verification report to `openspec/changes/$1/decision-log.md` AS-IS
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
3. Update `state.json`: Set `"phase_complete": true`
4. Script will advance to PHASE3

## STATE FILE UPDATES

Phase complete (verification passed):
```bash
jq '.phase_complete = true' openspec/changes/$1/state.json > tmp && mv tmp openspec/changes/$1/state.json
```

## DECISION LOG FORMAT

Append to `openspec/changes/$1/decision-log.md`:

```markdown
## PHASE2 - VERIFICATION (Iteration N)

### CLI Output

## CLI Output: openspec status
```json
<paste exact output>
```

## CLI Output: openspec instructions apply
```json
<paste exact output>
```

### Verification Report
[Paste skill's verification report AS-IS]

### Issues Found
- CRITICAL: [description] (if any)
- WARNING: [description] (if any)
- SUGGESTION: [description] (if any)

### Action Taken
[Fix artifacts / Proceed to PHASE3]

### Session Summary
[Summary of verification results]

### Next Steps
[Transition to PHASE3 or restart PHASE1]
```

## ITERATIONS.JSON FORMAT

Append to `openspec/changes/$1/iterations.json`:

```json
{
  "iteration": N,
  "phase": "REVIEW",
  "verification_result": "passed|failed",
  "issues_found": {"critical": N, "warning": N, "suggestion": N},
  "artifacts_modified": true|false,
  "notes": "Brief summary"
}
```

## TRANSITION

- Verification passed → PHASE3 (MAINTAIN-DOCS)
- Verification failed (artifacts modified) → PHASE1 (IMPLEMENTATION) restart
