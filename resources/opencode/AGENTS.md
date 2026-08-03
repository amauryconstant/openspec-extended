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

- Command files use the OpenCode frontmatter: `description` and (for autonomous
  phase commands) `agent: <sub-agent-name>`. The `agent:` field is OpenCode-only;
  the Claude mirror drops it.
- Commands are flat files named `osx-<command>.md` (no subdirectory).
- Skill directories follow `<name>/SKILL.md` with optional `references/` and `scripts/`.
- Agents use OpenCode-specific frontmatter including `mode`, `temperature`, and `permission` blocks.

## Naming

All extended resources use the `osx-` prefix. The 8 skills, 4 agents, and 12 commands are listed in `manifest.toml`.

## Claude Mirror Note

The Claude mirror at `resources/claude/` dual-emits every opencode command:
the legacy `.claude/commands/osx/<name>.md` form is preserved for back-compat,
and the modern `.claude/skills/osx-<name>/SKILL.md` form is also produced.
This mirrors upstream OpenSpec v1.7.0's own dual-emit on Claude (see
`resources/claude/AGENTS.md` for the rationale). OpenCode itself is
single-emit (commands only); the `syncing` between the two trees is handled
by `.mise/tasks/sync-mirrors`.

## See Also

- `resources/AGENTS.md` — Resource types, manifest format
- `resources/opencode/skills/AGENTS.md` — Skill directory layout
- `resources/opencode/agents/AGENTS.md` — Agent files
- `resources/opencode/commands/AGENTS.md` — Command files
- `resources/claude/AGENTS.md` — Sibling platform + dual-emit rationale
- `research/opencode-docs.md` — Platform capability reference
