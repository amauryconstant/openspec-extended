# Skills (Claude Code)

Claude Code skills. Mirror of orchestrator-side OpenCode skills —
same directory layout; bodies are generated from the OpenCode source.

## Layout

```
orchestrator/resources/claude/skills/
├── references/                  # Shared references (cross-cutting, no single owner)
├── osx-workflow/                # Mirror of orchestrator/resources/opencode/skills/osx-workflow
├── osx-phase0/ … osx-phase6/    # Dual-emit (modern form) of phase commands
└── osx-changelog/, osx-maintain-docs/  # Dual-emit (modern form) of orchestrator commands
```

## Frontmatter

Claude Code skills accept the full YAML frontmatter spec:

```yaml
---
name: osx-<skill-name>
description: <one-line purpose>
license: MIT
compatibility: <optional>
allowed-tools: <optional>
---
```

## Mirror generation

The Claude mirror is generated from the OpenCode source by `mise run sync:mirrors`. **Do not edit Claude skill files directly** — every generated file carries an `# AUTO-GENERATED` header. The pre-commit hook (`sync-mirrors-check`) fails the commit if the mirror drifts.

To change a skill:

1. Edit the file under `orchestrator/resources/opencode/skills/osx-<name>/SKILL.md`.
2. Run `mise run sync:mirrors` to regenerate the Claude mirror.
3. Commit both files.

For one-off Claude-only overrides, see `references/claude-only-overrides.md` (placeholder; reserved for future use). Today there are no overrides.

## Naming

Same rules as OpenCode (`osx-` prefix, lowercase-hyphenated, must match directory name). Skills mirror their OpenCode counterparts.

## Skill count on Claude

The orchestrator-side Claude mirror ships more skill directories than the
OpenCode source. The breakdown:

- **1** mirrors the OpenCode skill 1:1 (`osx-workflow`).
- **9** are dual-emits of orchestrator-side commands (`osx-phase0..6`,
  `osx-changelog`, `osx-maintain-docs`).
- **2 skills-side dual-emits** (`osx-review`, `osx-verify-tests`) live at
  `skills/resources/claude/skills/`, not here.
- **1** is the `references/` pool (cross-cutting shared references; see
  `orchestrator/resources/opencode/skills/AGENTS.md`).

## Authoring Workflow

1. Create or edit the skill under `orchestrator/resources/opencode/skills/osx-<name>/SKILL.md` first (orchestrator side) or `skills/resources/opencode/skills/osx-<name>/SKILL.md` (skills side).
2. Run `mise run sync:mirrors` to regenerate the corresponding Claude mirror.
3. Bump the version in the manifest (Phase 5 splits the manifest; today both sides share one).
4. Commit all four affected trees (opencode + claude × orchestrator + skills).

## Shared references

Same set as OpenCode — see `orchestrator/resources/opencode/skills/AGENTS.md` for the table. Each shared reference is auto-generated into the Claude mirror.

## Schema-Agnostic Contract for Review Skills

`osx-review-artifacts` adopts the same six rules as core's `openspec-update-change`. Every skill, command, and orchestrator phase that handles pre-implementation review must honor them. The full contract lives at:

- `references/schema-agnostic-contract.md`
- `references/store-selection.md` (v1.7.0 store-selection paragraph)

Add a one-line pointer at the top of any skill that needs either:

```markdown
> **Store selection** — see `references/store-selection.md`.
```

## See Also

- `orchestrator/resources/claude/AGENTS.md` — Platform differences
- `orchestrator/resources/opencode/skills/AGENTS.md` — Sibling layout (treat as canonical)
- `orchestrator/resources/AGENTS.md` — Manifest format
- Root `AGENTS.md` — Adding New Skills
