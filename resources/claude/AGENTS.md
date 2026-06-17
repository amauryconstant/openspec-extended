# Claude Code Platform Resources

Resources for the Claude Code AI assistant. Mirrors the OpenCode tree, with two structural differences.

## Layout

```
resources/claude/
├── manifest.toml
├── skills/                  # osx-* skills (same structure as opencode)
└── commands/
    └── osx/                 # Note: all commands live under osx/ subdir
        └── <name>.md
```

## Platform Differences vs OpenCode

| Aspect | OpenCode | Claude Code |
|--------|----------|-------------|
| Commands directory | `commands/osx-*.md` (flat) | `commands/osx/<name>.md` (nested) |
| Command naming | `osx-phase0.md` | `phase0.md` (no `osx-` prefix in filename) |
| Command frontmatter | `description` only | `name`, `description`, `category`, `tags` |
| Skills directory | `skills/<name>/SKILL.md` | same |
| Skill frontmatter | `name`, `description`, `license` | `name`, `description`, full YAML with `metadata` |
| Agents | yes | n/a (Claude uses built-in agents) |

## Naming

Skills and command files use the `osx-` semantic prefix in their `name:` field, even when the filename omits it.

## See Also

- `resources/AGENTS.md` — Resource types, manifest format
- `resources/opencode/AGENTS.md` — Sibling platform (use as reference for shared content)
- `resources/claude/skills/AGENTS.md` — Skill directory layout
- `resources/claude/commands/AGENTS.md` — Command conventions
- `resources/claude/commands/osx/AGENTS.md` — Slash command files
- `research/claude-code-docs.md` — Claude Code capability reference
