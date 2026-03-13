---
description: PHASE3 - Maintain Documentation
agent: osx-maintainer
---

## Tools Available

| Tool | Usage |
|------|-------|
| `osc` | `.opencode/scripts/lib/osx <domain> <action> [args]` - unified OpenSpec tool |
| Domains: `ctx`, `state`, `iterations`, `log`, `complete`, `validate` |

# PHASE3: Maintain Documentation

Change: $1

## MANDATORY START

1. Load context:
  !`.opencode/scripts/lib/osx ctx get "$1"`
2. Confirm `phase` is PHASE3
3. Review `history.iterations_recorded` for previous attempts
4. Load skill: `.opencode/skills/osx-concepts/SKILL.md` (reference only)

## PURPOSE

Update AGENTS.md and CLAUDE.md files to reflect ALL changes made during implementation. If there is an available skill for that process, load it first.

**Scope - What to update:**
- Root AGENTS.md with new commands, patterns, or conventions
- Package-level AGENTS.md files (e.g., `internal/library/AGENTS.md`)
- CLAUDE.md if project supports both platforms
- Any other AI context documentation

**What to include:**
- New packages and their purpose
- New CLI commands and usage
- New architectural patterns
- Updated command references
- New capabilities added to the codebase

**NOT in scope:**
- Inline code comments (done in PHASE1)
- README files (done in PHASE1)
- Test files (done in PHASE1)

## PROCESS

1. Load and use `osx-maintain-ai-docs` skill
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

## AGENTS.md TASKS FROM TASKS.MD

If tasks.md contains AGENTS.md documentation tasks (e.g., "12.1 Update cmd/AGENTS.md"):

1. These tasks were intentionally deferred from PHASE1
2. Complete them now as part of this phase
3. Mark them complete in tasks.md after updating
4. Include in the single PHASE3 commit

This consolidation ensures:
- Single documentation commit for review
- Accurate representation of final codebase state
- No duplicate documentation work

## MANDATORY END

IF documentation was updated during this phase:

```bash
git add AGENTS.md CLAUDE.md
git commit -m "Update documentation for $1"
```

Record commit hash in decision log and iterations.json.

## BLOCKER HANDLING

If you encounter an unrecoverable issue that prevents progress:

```bash
.opencode/scripts/lib/osx complete set "$1" BLOCKED --blocker-reason "[Describe the specific blocking issue]"
```

The orchestrator will detect this and halt the workflow.

**When to use:**
- Documentation conflicts that cannot be resolved
- AGENTS.md/CLAUDE.md structure fundamentally incompatible with changes

## STATE FILE UPDATES

Phase complete:
```bash
.opencode/scripts/lib/osx state complete "$1"
```

## DECISION LOG

Append entry:
```bash
.opencode/scripts/lib/osx log append "$1" \
  --phase MAINTAIN_DOCS \
  --iteration N \
  --summary "Documentation updated successfully" \
  --commit-hash "<hash or null>" \
  --next-steps "Proceeding to PHASE4 (SYNC)" \
  --extra '{"docs_updated":["AGENTS.md","CLAUDE.md"],"changes_made":["Specific change 1","Specific change 2"]}'
```

## ITERATIONS.JSON

Append entry:
```bash
.opencode/scripts/lib/osx iterations append "$1" \
  --phase MAINTAIN_DOCS \
  --iteration N \
  --commit-hash "<hash or null>" \
  --notes "Documentation updated successfully" \
  --extra '{"docs_updated":["AGENTS.md","CLAUDE.md"]}'
```

## TRANSITION

1. Log: "Documentation updated, proceeding to SYNC"
2. Mark phase complete via `osx state`
3. Script will advance to PHASE4
