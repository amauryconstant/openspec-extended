---
name: osx-phase5
description: PHASE5 - Self-Reflection
category: openspec-orchestrator
tags: [openspec-extended, autonomous, orchestrator]
license: MIT
---

## Tools Available

| Tool | Usage |
|------|-------|
| `osx` | `openspec-extended osx <domain> <action> [args]` - unified OpenSpec tool |
| Domains: `ctx`, `state`, `iterations`, `log`, `complete`, `validate` |

# PHASE5: Self-Reflection

Change: $1

## MANDATORY START

1. Load context:
  !`openspec-extended osx ctx get "$1"`
2. Confirm `phase` is PHASE5
3. Review full history via `osx log get "$1"` to understand entire workflow
4. Review `history.iterations_recorded` for iteration counts per phase
5. Load skills: `osx-concepts` and `osx-workflow` (both reference only)

## PURPOSE

Critically evaluate the autonomous development process and identify improvements.

## REFLECTION QUESTIONS

Answer each with 2-4 sentences minimum, including specific examples:

**1. How well did the artifact review process work?**
   - Were CRITICAL issues identified accurately?
   - Did the iteration limit (10) constrain fixing important issues?
   - Should any issues have been raised earlier or later?

**2. How effective was the implementation phase?**
   - Were tasks clear and achievable?
   - Did milestone commits make sense?
   - Was test compliance review useful?

**3. How did verification perform?**
   - Did it catch important issues?
   - Were issues actionable?
   - Should any CRITICAL/WARNING issues have been caught earlier?

**4. What assumptions had to be made?**
   - List all significant assumptions from decision-log.json
   - Which caused issues later?
   - Which worked well?

**5. How did completion phases work?**
   - Were phase transitions smooth?
   - Did MAINTAIN DOCS provide value?
   - Did SYNC complete successfully?

**6. How was commit behavior?**
   - Were milestone commits made appropriately?
   - Did commit timing make sense?

**7. What would improve the workflow?**
   - Missing skills or tools?
   - Process bottlenecks?
   - Documentation improvements?

**8. What would improve for future changes?**
   - Review suggestions.md for any quick wins
   - Were any suggestions actually blockers in disguise?
   - Should any suggestions become new OpenSpec changes?
   - Artifact quality improvements?
   - Missing checkpoints?
   - Better progress tracking?

## DECISION LOG

Write reflections to file, then log:

```bash
# Write reflections (full markdown allowed)
cat > "openspec/changes/$1/reflections.md" << 'EOF'
# Self-Reflection: $1

## 1. How well did the artifact review process work?
[Answer with specific examples - 2-4 sentences]

## 2. How effective was the implementation phase?
[Answer with specific examples - 2-4 sentences]

## 3. How did verification perform?
[Answer with specific examples - 2-4 sentences]

## 4. What assumptions had to be made?
[Answer with specific examples - 2-4 sentences]

## 5. How did completion phases work?
[Answer with specific examples - 2-4 sentences]

## 6. How was commit behavior?
[Answer with specific examples - 2-4 sentences]

## 7. What would improve the workflow?
[Answer with specific examples - 2-4 sentences]

## 8. What would improve for future changes?
[Answer with specific examples - 2-4 sentences]
EOF

# Log with path reference (not inline content)
openspec-extended osx log append "$1" \
  --phase SELF_REFLECTION \
  --iteration N \
  --summary "Self-reflection completed. Workflow evaluation finished." \
  --commit-hash "<hash or null>" \
  --next-steps "Self-reflection complete. Proceeding to PHASE6 (ARCHIVE)." \
  --extra '{"reflections_path":"openspec/changes/$1/reflections.md","total_phases":7,"total_iterations":N}'
```

## ITERATIONS.JSON

Append entry:
```bash
openspec-extended osx iterations append "$1" \
  --phase SELF_REFLECTION \
  --iteration N \
  --commit-hash "<hash or null>" \
  --notes "Self-reflection completed" \
  --extra '{"total_phases":7,"total_iterations":N,"reflection_completed":true}'
```

## MANDATORY END

1. Invoke osx-commit skill
2. Commit changes:

   ```bash
   git add openspec/changes/$1/reflections.md
   git commit -m "Complete self-reflection for $1"
   ```

3. Record commit hash in decision log and iterations.json

## BLOCKER HANDLING

If you encounter an unrecoverable issue that prevents progress:

```bash
openspec-extended osx complete set "$1" BLOCKED --blocker-reason "[Describe the specific blocking issue]"
```

The orchestrator will detect this and halt the workflow.

**When to use:**
- Reflection reveals a critical issue that requires human intervention
- Workflow cannot proceed to archive due to unresolved problems

## TRANSITION

1. Log: "Self-reflection complete, proceeding to ARCHIVE"
2. Mark phase complete via `osx state`
3. Script will advance to PHASE6 (ARCHIVE)


## SHELL ARGUMENT SAFETY

When passing free-text to `--summary`, `--next-steps`, or any other shell argument, **DO NOT use backticks** (`` `like this` ``) for inline code references. Backticks are interpreted as command substitution by bash/zsh — the shell will execute whatever is inside the backticks and substitute its output. In zsh, `` `local` `` dumps the entire shell environment (PATH, tokens, internal variables) into your string, which then gets stored verbatim in `decision-log.json`.

**Use instead:**

- Single quotes: `'local'`
- Double quotes: `"local"`
- Plain text: `local`
- Markdown `code` (which uses backticks in raw form, NOT shell backticks) — fine only when the argument is not passed through a shell

If `osx log append` returns `input_too_long` or `input_tainted`, remove the backticks from the offending argument and retry.
