---
description: PHASE3 - Maintain Documentation
agent: openspec-maintainer
metadata:
   version: "0.1.0"
---

# PHASE3: Maintain Documentation

Change: $1

## MANDATORY START

1. Read `.opencode/skills/openspec-concepts/SKILL.md` (reference only)
2. Read `openspec/changes/$1/state.json` to confirm phase is PHASE3
3. Read `openspec/changes/$1/decision-log.md` (if exists) to understand previous work
4. Read `openspec/changes/$1/iterations.json` (if exists) to understand iteration history

## PURPOSE

Update project documentation to reflect changes made during implementation.

## PROCESS

1. Load and use `openspec-maintain-ai-docs` skill
2. Read change artifacts: `openspec/changes/$1/proposal.md`, `openspec/changes/$1/specs/`, `openspec/changes/$1/design.md`, `openspec/changes/$1/tasks.md`
3. Read recent git changes: `git log --oneline -10`
4. Update project documentation:
   - AGENTS.md - Update with new commands, patterns, or conventions
   - CLAUDE.md - Update if Claude-specific patterns changed (if applicable)
   - Other docs as needed based on the change

5. Apply best practices:
   - Use tables over verbose lists
   - Be specific (concrete commands, not vague descriptions)
   - Progressive disclosure (summary first, details later)
   - Target <300 lines per file

## STATE FILE UPDATES

Phase complete:
```bash
jq '.phase_complete = true' openspec/changes/$1/state.json > tmp && mv tmp openspec/changes/$1/state.json
```

## DECISION LOG FORMAT

Append to `openspec/changes/$1/decision-log.md`:

```markdown
## PHASE3 - MAINTAIN-DOCS

### Documentation Updated
- [x] AGENTS.md: [Summary of changes]
- [x] CLAUDE.md: [Summary of changes, if applicable]
- [x] Other: [List any other docs updated]

### Changes Made
- [Specific change 1]
- [Specific change 2]

### Session Summary
[What was accomplished]

### Next Steps
Proceeding to PHASE4 (SYNC).
```

## ITERATIONS.JSON FORMAT

Append to `openspec/changes/$1/iterations.json`:

```json
{
  "iteration": N,
  "phase": "MAINTAIN-DOCS",
  "docs_updated": ["AGENTS.md", "CLAUDE.md"],
  "notes": "Documentation updated successfully"
}
```

## TRANSITION

1. Log: "Documentation updated, proceeding to SYNC"
2. Update `state.json`: Set `"phase_complete": true`
3. Script will advance to PHASE4
