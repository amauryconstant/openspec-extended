# OpenCode Platform Resources

Resources for the OpenCode AI coding assistant.

## Layout

```
resources/opencode/
├── manifest.toml
├── skills/                  # osx-* skills, one directory per skill
├── agents/                  # osx-*.md agent files
└── commands/                # osx-*.md slash command files
```

## Platform Conventions

- Command files use the OpenCode frontmatter: `description` only.
- Commands are flat files named `osx-<command>.md` (no subdirectory).
- Skill directories follow `<name>/SKILL.md` with optional `references/` and `scripts/`.
- Agents use OpenCode-specific frontmatter including `mode`, `temperature`, and `permission` blocks.

## Naming

All extended resources use the `osx-` prefix. The 8 skills, 3 agents, and 12 commands are listed in `manifest.toml`.

## See Also

- `resources/AGENTS.md` — Resource types, manifest format
- `resources/opencode/skills/AGENTS.md` — Skill directory layout
- `resources/opencode/agents/AGENTS.md` — Agent files
- `resources/opencode/commands/AGENTS.md` — Command files
- `research/opencode-docs.md` — Platform capability reference
