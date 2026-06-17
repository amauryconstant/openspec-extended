# Commands (Claude Code)

Claude Code slash commands live one level deeper than OpenCode: under an `osx/` subdirectory.

## Layout

```
commands/
└── osx/
    └── <name>.md             # Filename is the slash-command tail
```

The full set of command files lives at `resources/claude/commands/osx/`.

## Frontmatter

Claude Code commands use a richer frontmatter than OpenCode:

```yaml
---
name: osx-<command>            # Slash-command name (includes osx- prefix)
description: <one-line purpose> # Required
category: <grouping>            # Optional
tags: [<tag>, ...]              # Optional
---
```

## Filename vs Name

| Filename | Frontmatter `name` | Slash invocation |
|----------|--------------------|------------------|
| `phase0.md` | `osx-phase0` | `/osx-phase0` |
| `review.md` | `osx-review` | `/osx-review` |

The filename omits the `osx-` prefix; the frontmatter `name:` field carries it.

## Conventions

- Mirror OpenCode commands: every `resources/opencode/commands/osx-<x>.md` should have a `resources/claude/commands/osx/<x>.md` counterpart.
- Phase commands (`phase0` … `phase6`) are the only entry points the orchestrator uses; the dispatch table is the same.

## See Also

- `resources/claude/AGENTS.md` — Platform differences
- `resources/claude/commands/osx/AGENTS.md` — The command file directory
- `resources/opencode/commands/AGENTS.md` — Sibling layout (treat as canonical)
- `source/orchestrator/AGENTS.md` — Phase dispatch
