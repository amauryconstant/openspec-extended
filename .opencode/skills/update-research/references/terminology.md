# Terminology Reference

## Claude Code Terms (use consistently)

- **Subagents** (not "agents" or "sub-agents" except in official doc URLs)
- **Permission modes**: `default`, `acceptEdits`, `dontAsk`, `bypassPermissions`, `plan`
- **Tools**: PascalCase (`Bash`, `Read`, `Edit`, `Write`, `Grep`, `Glob`)
- **Model IDs**: Use aliases (`sonnet`, `opus`, `haiku`) or full names
- **Memory files**: `CLAUDE.md`, `.claude/CLAUDE.md`, `.claude/rules/*.md`

## OpenCode Terms (use consistently)

- **Agents** (not "subagents")
- **Permissions**: Object with tool-specific config, values: `allow`, `ask`, `deny`
- **Tools**: Lowercase (`bash`, `read`, `edit`, `write`, `grep`, `glob`)
- **Model IDs**: `provider/model-id` format
- **Skill names**: `^[a-z0-9]+(-[a-z0-9]+)*$` regex

## Cross-Platform Concepts (describe separately)

| Concept           | Claude Code           | OpenCode                      |
| ----------------- | --------------------- | ----------------------------- |
| Primary AI entity | Subagents             | Agents                        |
| Permission system | Enum (permissionMode) | Object with patterns          |
| Memory system     | Native CLAUDE.md      | Via AGENTS.md/CLAUDE.md rules |
