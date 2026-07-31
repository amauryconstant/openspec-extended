---
name: osx-maintain-ai-docs
description: Document only what AI cannot infer from code. Use between /opsx:apply and /opsx:archive to update CLAUDE.md after an OpenSpec change.
license: MIT
---

Update project documentation after implementing an OpenSpec change.

> **Mode** — see `references/osx-mode-conventions.md`. When `OSX_AUTONOMOUS=1` is set, skip interactive confirmation and proceed with reasonable defaults.

**Input**: optionally specify a change name. If omitted, infer from conversation context or prompt.

---

## Core Principles

| Principle | Application |
|-----------|-------------|
| **Infer** | Only document what AI can't infer from code |
| **Reference, don't embed** | Use progressive disclosure — point at detail, don't inline it |
| **Tables over prose** | Token efficiency: tables beat verbose lists |
| **Concrete** | Specific commands, not vague instructions |

**Target lengths**:
- Ideal: <300 lines (~1200 tokens)
- Warning: >300 lines (review needed)
- Maximum: >500 lines (must split)

---

## Steps

### 1. Select the change

If a name is provided, use it. Otherwise: infer from context, auto-select if only one active change exists, or run `openspec list --json` and prompt. Auto-select first candidate under `OSX_AUTONOMOUS=1`.

Always announce: "Using change: <name>" and how to override.

### 2. Read change artifacts

Read files from `openspec/changes/<name>/`:

- `proposal.md` — Intent, scope, new features/capabilities
- `specs/` — New requirements, modified behaviors
- `design.md` — Architectural decisions, new patterns, file changes
- `tasks.md` — Checked items = what was actually built

Extract: new commands, components, patterns, APIs/endpoints, architecture changes. Detail in `references/doc-structures.md`.

### 3. Read recent code changes

```bash
git log --oneline -20
git diff HEAD~5..HEAD --stat
git diff HEAD~5..HEAD --name-only
```

Cross-reference: match git changes to `tasks.md` checked items; identify implementation that differs from `design.md`; note additional work not in original artifacts.

### 4. Detect or create documentation file

```bash
test -f CLAUDE.md && echo "CLAUDE.md found"
```

If `CLAUDE.md` doesn't exist, create minimal documentation:

```markdown
# Project - Claude Code Reference

## Quick Reference

| Command | Purpose |
|---------|---------|
| `npm run dev` | Start development |
| `npm run build` | Production build |

## Architecture

[Brief overview based on codebase structure]

## Conventions

[Key patterns observed from git changes]
```

### 5. Read current documentation

Parse existing structure and sections. Note current line count.

**Warn if** `CLAUDE.md` > 300 lines. **Error if** > 500 lines (split required before adding content).

### 6. Assess documentation needs

For each implemented item, determine if docs need updating:

| Implementation Type | Action |
|---------------------|--------|
| New CLI commands/scripts | Add to Quick Reference |
| New components/modules | Add brief entry with purpose |
| New patterns/conventions | Add specific pattern |
| New APIs/endpoints | Add endpoint summary table |
| Architecture changes | Update overview section |
| Bug fixes/refactors | Usually no update needed |
| Internal changes | Skip unless affects conventions |

Filter out: generic patterns AI already knows, self-evident implementations, standard language conventions.

### 7. Generate proposed updates

Apply best practices — use tables, be specific, reference rather than embed, cut generic advice. See `references/update-rules.md` for the full list.

### 8. Show proposal and confirm

Present changes with impact:

```markdown
## Documentation Updates: <change-name>

**Current state**:
- CLAUDE.md: 180 lines (~720 tokens)

**Proposed changes**:
- Add "Feature X" to Quick Reference (table format)
- Add pattern: "Use `useX()` hook for X state"

**After update**: ~195 lines (within target)

Apply these updates?
```

Auto-accept under `OSX_AUTONOMOUS=1`. Otherwise, confirm before writing.

### 9. Write updates

For every row in step 6's table, either add the entry to its named section or record the skip in `osx log`. Preserve existing structure. Do not invent sections.

---

## Output

**On new docs created**:

```markdown
## Documentation Created: <change-name>

**File created**:
- CLAUDE.md (new, 45 lines)

**Initial content**:
- Quick Reference with detected commands
- Architecture overview from codebase
- Conventions from recent changes

**Next step**: Review and refine, then ready to archive with `/osc-archive-change`.
```

**On updates applied**:

```markdown
## Documentation Updated: <change-name>

**File modified**:
- CLAUDE.md: +5 lines (180 → 185)

**Changes applied**:
- Added "Theme System" to Quick Reference
- Added theme hook pattern
- Updated architecture overview

**Next step**: Ready to archive with `/osc-archive-change`.
```

**On no updates needed**:

```markdown
## Documentation Current

Implementation doesn't require documentation updates:
- All changes are internal/refactoring
- Existing documentation covers functionality
- Changes are inferable from code structure

Ready to archive with `/osc-archive-change`.
```

**On length warning**:

```markdown
## Documentation Warning

**CLAUDE.md**: 420 lines (exceeds 300 line target)

Recommendations:
1. Move detailed patterns to subdirectory CLAUDE.md files
2. Use progressive disclosure (reference, don't embed)
3. Convert verbose lists to tables

Proceed anyway, or address first?
```

---

## Anti-Patterns to Avoid

### Generic Advice

```markdown
# BAD
- Follow coding best practices
- Write clean, maintainable code
- Test thoroughly

# GOOD (or skip entirely if standard)
- Run `npm run typecheck` after TypeScript changes
- Use `set -euo pipefail` for shell scripts
```

### Verbose Descriptions

```markdown
# BAD
- ThemeContext: This component provides theme state management
  using React Context API. It integrates with localStorage for
  persistence and supports system preference detection...

# GOOD
- `useTheme()`: Returns `{ theme, setTheme }` - see `src/contexts/ThemeContext.tsx`
```

---

## References

- `references/doc-structures.md` — per-artifact extraction rules
- `references/update-rules.md` — full best-practice list
- `references/update-examples.md` — worked before/after diffs

<!--
# AUTO-GENERATED from opencode via `mise run sync:mirrors` — do not edit by hand.
Source: resources/opencode/skills/osx-maintain-ai-docs/SKILL.md
Regenerate: `mise run sync:mirrors`
-->
