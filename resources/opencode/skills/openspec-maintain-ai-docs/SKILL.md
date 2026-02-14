---
name: openspec-maintain-ai-docs
description: Update AGENTS.md after implementing an OpenSpec change. Use between sync and archive to document what was built for future OpenCode sessions.
license: MIT
metadata:
  author: openspec-extended
  version: "0.2.0"
---

Update project documentation after implementing an OpenSpec change.

**Input**: Optionally specify a change name. If omitted, check if it can be inferred from conversation context. If vague or ambiguous you MUST prompt for available changes.

---

## Core Principles

| Principle | Application |
|-----------|-------------|
| **Ruthless conciseness** | Only document what AI can't infer from code |
| **Progressive disclosure** | Reference details, don't embed them |
| **Token efficiency** | Tables over verbose lists, front-load essentials |
| **Specificity** | Concrete commands, not vague instructions |

**Target lengths**:
- Ideal: <300 lines (~1200 tokens)
- Warning: >300 lines (review needed)
- Maximum: >500 lines (must split)

---

## Steps

1. **Select the change**

   If a name is provided, use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` to get available changes and use the **AskUserQuestion tool** to let the user select

   Always announce: "Using change: <name>" and how to override.

2. **Read change artifacts**

   Read files from `openspec/changes/<name>/`:
   
   | File | Extract |
   |------|---------|
   | `proposal.md` | Intent, scope, new features/capabilities |
   | `specs/` | New requirements, modified behaviors |
   | `design.md` | Architectural decisions, new patterns, file changes |
   | `tasks.md` | Checked items = what was actually built |

   **Key extraction**:
   - New commands/CLI tools added
   - New components/modules created
   - New patterns or conventions established
   - New APIs/endpoints exposed
   - Architectural changes

3. **Read recent code changes**

   Use git to identify what code was actually modified:

   ```bash
   # Get recent commits related to the change
   git log --oneline -20

   # See what files changed in recent commits
   git diff HEAD~5..HEAD --stat

   # View actual diff content for context
   git diff HEAD~5..HEAD --name-only
   ```

   **What to look for**:
   - New files created (indicate new components/modules)
   - Modified files (indicate pattern changes or extensions)
   - Deleted files (indicate removed functionality)
   - Commit messages (provide context on what was built)

   **Cross-reference with artifacts**:
   - Match git changes to tasks.md checked items
   - Identify any implementation that differs from design.md
   - Note any additional work not in original artifacts

4. **Detect or create documentation file**

   ```bash
   test -f AGENTS.md && echo "AGENTS.md found"
   ```

   **If AGENTS.md doesn't exist**, create minimal documentation:

   ```markdown
   # Project - OpenCode Reference

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

5. **Read current documentation**

   - Parse existing structure and sections
   - Note current line count
   - Identify sections to preserve

   **Warn if**:
   - AGENTS.md > 300 lines

   **Error if**:
   - AGENTS.md > 500 lines (split required before adding content)

6. **Assess documentation needs**

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

   **Filter out**:
   - Generic patterns AI already knows
   - Self-evident implementations
   - Standard language conventions

7. **Generate proposed updates**

   Apply best practices:
   
   **Use tables for lists**:
   ```markdown
   | Command | Purpose |
   |---------|---------|
   | `npm run dev` | Start dev server |
   | `npm run build` | Production build |
   ```

   **Be specific**:
   ```markdown
   ✅ "Run `npm run typecheck` after TypeScript changes"
   ❌ "Run the typechecker"
   ```

   **Progressive disclosure**:
   ```markdown
   ✅ "See `src/auth/AGENTS.md` for auth patterns"
   ❌ [500 lines of auth documentation embedded]
   ```

   **Cut generic advice**:
   ```markdown
   ❌ "Follow coding best practices"
   ❌ "Write clean code"
   ❌ "Test thoroughly"
   ```

8. **Show proposal and confirm**

   Present changes with impact:

   ```markdown
   ## Documentation Updates: <change-name>

   **Current state**:
   - AGENTS.md: 180 lines (~720 tokens)

   **Proposed changes**:
   - Add "Feature X" to Quick Reference (table format)
   - Add pattern: "Use `useX()` hook for X state"

   **After update**: ~195 lines (within target)

   Apply these updates?
   ```

   Use **AskUserQuestion tool** to confirm before writing.

9. **Write updates**

   - Preserve existing structure
   - Add new content in appropriate sections

---

## Output

**On new docs created**:

```markdown
## Documentation Created: <change-name>

**File created**:
- AGENTS.md (new, 45 lines)

**Initial content**:
- Quick Reference with detected commands
- Architecture overview from codebase
- Conventions from recent changes

**Next step**: Review and refine, then ready to archive with `/opsx-archive`.
```

**On updates applied**:

```markdown
## Documentation Updated: <change-name>

**File modified**:
- AGENTS.md: +5 lines (180 → 185)

**Changes applied**:
- Added "Theme System" to Quick Reference
- Added theme hook pattern
- Updated architecture overview

**Next step**: Ready to archive with `/opsx-archive`.
```

**On no updates needed**:

```markdown
## Documentation Current

Implementation doesn't require documentation updates:
- All changes are internal/refactoring
- Existing documentation covers functionality
- Changes are inferable from code structure

Ready to archive with `/opsx-archive`.
```

**On length warning**:

```markdown
## Documentation Warning

**AGENTS.md**: 420 lines (exceeds 300 line target)

Recommendations:
1. Move detailed patterns to subdirectory AGENTS.md files
2. Use progressive disclosure (reference, don't embed)
3. Convert verbose lists to tables

Proceed anyway, or address first?
```

---

## Guardrails

- **DO**: Preserve existing structure and sections
- **DO**: Use tables for command/reference lists
- **DO**: Confirm with user before writing changes
- **DON'T**: Document standard patterns AI already knows
- **DON'T**: Add verbose file-by-file descriptions
- **DON'T**: Include tutorials, history, or generic advice
- **DON'T**: Let files exceed 500 lines

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

## Effectiveness Indicators

### Positive Signs

- AI follows new patterns without asking
- File stays under 300 lines
- No outdated or orphaned sections

### Negative Signs (Fix Needed)

- AI asks about documented items → improve clarity
- File >300 lines → review and condense
- File >500 lines → split immediately
