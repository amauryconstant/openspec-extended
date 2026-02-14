---
description: Update AGENTS.md and CLAUDE.md after implementing an OpenSpec change
---

Update project documentation after implementing an OpenSpec change. Runs after `/opsx:sync` and before `/opsx:archive`.

**Input**: Optionally specify a change name. If omitted, infer from context or prompt for selection.

**Steps**

1. **Select the change** - Infer from context, auto-select if only one active, or prompt with **Ask tool**

2. **Read change artifacts** from `openspec/changes/<name>/`:
   - `proposal.md` - Intent, scope, new capabilities
   - `specs/` - New requirements, modified behaviors
   - `design.md` - Architectural decisions, new patterns
   - `tasks.md` - Checked items = what was built

3. **Read recent code changes** using git:
   ```bash
   git log --oneline -20
   git diff HEAD~5..HEAD --stat
   git diff HEAD~5..HEAD --name-only
   ```
   Cross-reference with artifacts to identify what was actually implemented.

4. **Detect or create documentation files**:
   ```bash
   test -f AGENTS.md && echo "AGENTS.md found"
   test -f CLAUDE.md && echo "CLAUDE.md found"
   ```
   If neither exists, create minimal docs with Quick Reference, Architecture, Conventions.

5. **Read current documentation** - Parse structure, note line counts (warn if >300, error if >500)

6. **Assess documentation needs** - For each implemented item, determine if docs need updating:
   - New CLI commands → Add to Quick Reference
   - New components → Add brief entry
   - New patterns → Add specific pattern
   - Architecture changes → Update overview
   - Internal/refactor → Usually skip

7. **Generate proposed updates** - Apply best practices:
   - Tables for lists
   - Specific commands (not vague instructions)
   - Progressive disclosure (reference, don't embed)
   - Cut generic advice

8. **Show proposal and confirm** with **Ask tool**

9. **Write updates** - Preserve structure, sync both platforms

**Output**

```
## Documentation Updated: <change-name>

**Files modified**:
- AGENTS.md: +5 lines (180 → 185)
- CLAUDE.md: +5 lines (165 → 170)

**Changes applied**:
- Added "Feature X" to Quick Reference
- Added pattern for Y

**Next step**: Ready to archive with `/opsx:archive`.
```

**Guardrails**

- Preserve existing structure
- Keep both platforms synchronized
- Don't document what AI can infer from code
- Files must stay <500 lines
- Confirm before writing

---

See `.claude/skills/openspec-maintain-ai-docs/SKILL.md` for:
- Core principles (conciseness, progressive disclosure)
- Best practices for documentation updates
- Anti-patterns to avoid
- Effectiveness indicators
