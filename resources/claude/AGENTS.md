# Claude Code Platform Resources

Resources for the Claude Code AI assistant. Mirrors the OpenCode tree, with two structural differences plus a **dual-emit** rule for commands.

## Layout

```
resources/claude/
├── manifest.toml
├── skills/                  # osx-* + osc-* skills (same structure as opencode)
└── commands/
    └── osx/                 # Note: all commands live under osx/ subdir
        └── <name>.md
```

## Platform Differences vs OpenCode

| Aspect | OpenCode | Claude Code |
|--------|----------|-------------|
| Commands directory | `commands/osx-*.md` (flat) | `commands/osx/<name>.md` (nested) |
| Command naming | `osx-phase0.md` | `phase0.md` (no `osx-` prefix in filename) |
| Command frontmatter | `description`, `agent` | `description`, `name: osx-<X>` |
| Skills directory | `skills/<name>/SKILL.md` | same |
| Skill frontmatter | `name`, `description`, `license` | `name`, `description`, full YAML with `metadata` |
| Agents | yes | n/a (Claude uses built-in agents) |

## Dual-emit for commands (Claude only)

Claude Code's "Custom commands have been merged into skills" (per
[the official docs](https://code.claude.com/docs/en/skills.md)). Both `.claude/commands/<name>.md`
and `.claude/skills/<name>/SKILL.md` register the same slash command `<name>`,
so every command in this tree is mirrored as:

- `.claude/commands/osx/<name>.md` — legacy form, kept for back-compat
- .claude/skills/osx-<name>/SKILL.md` — modern form (the canonical one going forward)

Upstream OpenSpec v1.7.0 follows the same dual-emit pattern. Mirroring it
keeps `osx-*` slash commands functional regardless of which Claude Code
surface resolves them, while putting us on the recommended path for future
Claude Code releases. The `name:` field on the mirrored skill is set to
`osx-<X>` (matching the slash-command identifier); the opencode-only
`agent:` frontmatter is dropped because Claude has no equivalent dispatch.

## Naming

Skills and command files use the `osx-` semantic prefix in their `name:` field, even when the filename omits it.

## See Also

- `resources/AGENTS.md` — Resource types, manifest format
- `resources/opencode/AGENTS.md` — Sibling platform (use as reference for shared content)
- `resources/claude/skills/AGENTS.md` — Skill directory layout
- `resources/claude/commands/AGENTS.md` — Command conventions
- `resources/claude/commands/osx/AGENTS.md` — Slash command files
- `research/claude-code-docs.md` — Claude Code capability reference
