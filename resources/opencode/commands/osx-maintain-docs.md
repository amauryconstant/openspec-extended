---
description: Update AGENTS.md and CLAUDE.md after implementing an OpenSpec change
license: MIT
---

Update project documentation after implementing an OpenSpec change. Runs after `/osc-sync-specs` and before `/osc-archive-change`.

**Input**: optionally specify a change name. If omitted, infer from context or prompt for selection.

## Steps

Load the skill body — read `{{PLATFORM_DIR}}/skills/osx-maintain-ai-docs/SKILL.md` and follow the `## Steps` section. This command wraps that skill; do not duplicate steps here.

## Output

```
## Documentation Updated: <change-name>

**Files modified**:
- {{DOCS_FILE}}: +N lines (X → Y)

**Changes applied**:
- ...

**Next step**: Ready to archive with `/osc-archive-change`.
```

## Guardrails

- Preserve existing structure.
- Keep both platforms synchronized (`AGENTS.md` ↔ `CLAUDE.md`).
- Document only what AI cannot infer from code.
- Files must stay <500 lines (warn at 300).
- Confirm before writing.

See `{{PLATFORM_DIR}}/skills/osx-maintain-ai-docs/SKILL.md` for the full contract, core principles, and anti-patterns.