---
name: osx-maintain-docs
description: Document only what AI cannot infer from code. Use between apply and archive to update project docs after an OpenSpec change.
license: MIT
disable-model-invocation: true
compatibility: Requires openspec CLI.
allowed-tools: Bash(openspec:*)
metadata:
  audience: user-invoked /osx-maintain-docs invocation; PHASE3 internal dispatch
  workflow: post-implementation — docs sync
---

Update project documentation after implementing an OpenSpec change.

Runs after `/osc-sync-specs` and before `/osc-archive-change`.

> **Mode** — see `references/osx-mode-conventions.md`. When `OSX_AUTONOMOUS=1` is set, skip interactive confirmation and proceed with reasonable defaults.

**Input**: Optionally specify `[<change-name>]` as `$1` (e.g., `/osx-maintain-docs add-auth`). For ad-hoc invocations: if omitted, check if it can be inferred from conversation context; auto-select if only one active change exists; otherwise run `openspec list --json` and prompt via `{{ASK_TOOL}}`. PHASE3 dispatches the change name automatically; this command is also user-invocable directly with `$1` set.

---

## Steps

1. **Select the change**

   If a name is provided (as `$1`), use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` and ask the user to select one

   Always announce: "Using change: <change-name>" and how to override (e.g., `/osx-maintain-docs <other>`).

2. Apply the **Core Principles** below as you draft.

3. Read change artifacts from `openspec/changes/<name>/`:

   - `proposal.md` — Intent, scope, new features/capabilities
   - `specs/` — New requirements, modified behaviors
   - `design.md` — Architectural decisions, new patterns, file changes
   - `tasks.md` — Checked items = what was actually built

   Extract: new commands, components, patterns, APIs/endpoints, architecture changes. Detail in `references/doc-structures.md`.

4. Read recent code changes:

   ```bash
   git log --oneline -20
   git diff HEAD~5..HEAD --stat
   git diff HEAD~5..HEAD --name-only
   ```

   Cross-reference: match git changes to `tasks.md` checked items; identify implementation that differs from `design.md`; note additional work not in original artifacts.

5. Detect or create the documentation file:

   ```bash
   test -f {{DOCS_FILE}} && echo "{{DOCS_FILE}} found"
   ```

   If `{{DOCS_FILE}}` doesn't exist, create minimal documentation per the template in **Output → On new docs created** below.

6. Read current documentation. Parse existing structure and sections; note current line count.

   **Warn if** `{{DOCS_FILE}}` > 300 lines. **Error if** > 500 lines (split required before adding content).

7. Assess documentation needs:

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

8. Generate proposed updates. Apply best practices — use tables, be specific, reference rather than embed, cut generic advice. See `references/update-rules.md` for the full list. Worked before/after examples in `references/update-examples.md`.

9. Show proposal and confirm. Present changes with impact (see **Output → On updates applied** below). Auto-accept under `OSX_AUTONOMOUS=1`. Otherwise, confirm before writing.

10. Write updates. For every row in step 7's table, either add the entry to its named section or record the skip in `osx log`. Preserve existing structure. Do not invent sections.

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

## Output

**On new docs created**:

```markdown
## Documentation Created: <change-name>

**File created**:
- {{DOCS_FILE}} (new, 45 lines)

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
- {{DOCS_FILE}}: +5 lines (180 → 185)

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

**{{DOCS_FILE}}**: 420 lines (exceeds 300 line target)

Recommendations:
1. Move detailed patterns to subdirectory {{DOCS_FILE}} files
2. Use progressive disclosure (reference, don't embed)
3. Convert verbose lists to tables

Proceed anyway, or address first?
```

---

## Guardrails

- Preserve existing structure.
- Keep both platforms synchronized (`AGENTS.md` ↔ `CLAUDE.md`).
- Document only what AI cannot infer from code.
- Files must stay <500 lines (warn at 300).
- Confirm before writing.

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
