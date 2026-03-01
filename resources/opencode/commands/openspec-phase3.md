---
description: PHASE3 - Maintain Documentation
agent: openspec-maintainer
---

## Tools Available

| Tool | Usage |
|------|-------|
| `osc-ctx` | `.opencode/scripts/lib/osc-ctx <change>` - load change context |
| `osc-state` | `.opencode/scripts/lib/osc-state <change> <action>` - manage state |
| `osc-log` | `.opencode/scripts/lib/osc-log <change> <action>` - decision log |
| `osc-iterations` | `.opencode/scripts/lib/osc-iterations <change> <action>` - iteration history |

# PHASE3: Maintain Documentation

Change: $1

## MANDATORY START

1. Load context:
  !`.opencode/scripts/lib/osc-ctx "$1"`
2. Confirm `phase` is PHASE3
3. Review `history.iterations_recorded` for previous attempts
4. Load skill: `.opencode/skills/openspec-concepts/SKILL.md` (reference only)

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
.opencode/scripts/lib/osc-state "$1" complete
```

## DECISION LOG

Append entry:
```bash
echo '{
  "phase": "MAINTAIN-DOCS",
  "iteration": N,
  "summary": "Documentation updated successfully",
  "docs_updated": ["AGENTS.md", "CLAUDE.md"],
  "changes_made": ["Specific change 1", "Specific change 2"],
  "next_steps": "Proceeding to PHASE4 (SYNC)"
}' | .opencode/scripts/lib/osc-log "$1" append
```

## ITERATIONS.JSON

Append entry:
```bash
echo '{
  "iteration": N,
  "phase": "MAINTAIN-DOCS",
  "docs_updated": ["AGENTS.md", "CLAUDE.md"],
  "notes": "Documentation updated successfully"
}' | .opencode/scripts/lib/osc-iterations "$1" append
```

## TRANSITION

1. Log: "Documentation updated, proceeding to SYNC"
2. Mark phase complete via `osc-state`
3. Script will advance to PHASE4
