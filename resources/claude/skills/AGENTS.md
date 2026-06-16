# Skills (Claude Code)

Claude Code skills. Same directory layout as the OpenCode side; frontmatter is richer.

## Layout

```
skills/
└── <skill-name>/
    ├── SKILL.md              # Required: skill body + frontmatter
    ├── references/           # Optional: deeper reference docs
    └── scripts/              # Optional: helper scripts
```

## Frontmatter

Claude Code skills accept the full YAML frontmatter spec, including a `metadata` block:

```yaml
---
name: osx-<skill-name>
description: <one-line purpose>
license: MIT
metadata:
  audience: <who this is for>
  workflow: <when to load>
---
```

## Naming

Same rules as OpenCode (`osx-` prefix, lowercase-hyphenated, must match directory name). The 8 skills mirror their OpenCode counterparts.

## Authoring Workflow

1. Create or edit the skill under `resources/opencode/skills/osx-<name>/SKILL.md` first.
2. Mirror the body under `resources/claude/skills/osx-<name>/SKILL.md`.
3. Adapt the frontmatter for Claude Code's richer schema.
4. Add entries to both `resources/opencode/manifest.toml` and `resources/claude/manifest.toml`.

## See Also

- `resources/claude/AGENTS.md` — Platform differences
- `resources/opencode/skills/AGENTS.md` — Sibling layout (treat as canonical)
- `resources/AGENTS.md` — Manifest format
- Root `AGENTS.md` — Adding New Skills
