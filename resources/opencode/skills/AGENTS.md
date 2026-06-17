# Skills (OpenCode)

OpenCode skills: one directory per skill, `SKILL.md` as the entry point.

## Layout

```
skills/
└── <skill-name>/
    ├── SKILL.md              # Required: skill body + frontmatter
    ├── references/           # Optional: deeper reference docs
    └── scripts/              # Optional: helper scripts the skill may invoke
```

Example: `osx-concepts/SKILL.md` plus `osx-concepts/references/`.

## Frontmatter

```yaml
---
name: osx-<skill-name>          # Required, must match directory name
description: <one-line purpose> # Required
license: MIT                   # Required
---
```

## Naming Rules

| Rule | Constraint |
|------|------------|
| Length | 1–64 chars |
| Charset | `^[a-z0-9]+(-[a-z0-9]+)*$` |
| Prefix | `osx-` for extended skills; `osc-` reserved for core |
| Match | Directory name must equal the `name` field |

## Authoring Workflow

See root `AGENTS.md` "Adding New Skills" section for the full procedure. Briefly:

1. Create `resources/opencode/skills/osx-<name>/SKILL.md`.
2. Add the entry to `resources/opencode/manifest.toml`.
3. Mirror the skill under `resources/claude/skills/osx-<name>/` if Claude Code support is needed.
4. Bump the version in the manifest.

## See Also

- Root `AGENTS.md` — Adding New Skills
- `resources/AGENTS.md` — Manifest format, resource types
- `resources/opencode/AGENTS.md` — Platform overview
- `research/opencode-docs.md` — OpenCode skill spec
