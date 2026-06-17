# Resources

AI-assistant resources shipped inside the binary. Two parallel platform trees, one shared manifest per platform.

## Layout

```
resources/
├── opencode/                # OpenCode platform resources
│   ├── manifest.toml        # Per-resource version manifest
│   ├── skills/osx-*/        # Skills
│   ├── agents/osx-*.md      # Agents
│   └── commands/osx-*.md    # Slash commands
└── claude/                  # Claude Code platform resources
    ├── manifest.toml
    ├── skills/osx-*/
    └── commands/osx/        # Note: commands live under an osx/ subdir
```

## Naming Convention

| Resource | Core (upstream) | Extended (local) |
|----------|-----------------|------------------|
| CLI | `openspec` | `openspec-extended` |
| Slash commands | `/osc-*` | `/osx-*` |
| Skills | `osc-*` | `osx-*` |
| Agents | n/a | `osx-*` |
| Lib scripts | n/a | `osx` |

Core skills (the upstream OpenSpec workflows) live in `openspec-core/` and are not modified locally.

## Resource Types

| Type | Path pattern | Frontmatter | Example |
|------|--------------|-------------|---------|
| Skill | `skills/<name>/SKILL.md` | `name`, `description`, `license` | `osx-concepts` |
| Agent | `agents/<name>.md` | `description`, `hidden`, `mode`, `temperature`, `permission` | `osx-analyzer` |
| Command | `commands/<name>.md` | `description` (OpenCode) | `osx-phase0` |
| Script | `scripts/<name>.py` | n/a | `osx-orchestrate` |
| Lib | `lib/<name>.py` | n/a | `osx` |

## Manifest (`manifest.toml`)

Each platform has its own manifest tracking the version of every resource:

```toml
[resources.skills.osx-commit]
version = "0.1.0"

[resources.agents.osx-analyzer]
version = "0.2.1"
```

Versions are bumped **per resource** (not per release) by `mise run version:update` — see root AGENTS.md "Version Bumping" section.

## Conventions

- New resources get an `osx-` prefix; never collide with `osc-*` (core) names.
- One manifest entry per resource; CI fails on missing entries.
- Files under `openspec-core/` are not in this manifest — that tree is synced from upstream.

## See Also

- Root `AGENTS.md` — Adding New Skills, Version Bumping
- `resources/opencode/AGENTS.md`, `resources/claude/AGENTS.md` — Platform-specific
