# Commands (OpenCode)

OpenCode slash commands, one file per command.

## Layout

Flat directory: `commands/osx-<command>.md`. No subdirectories.

## Categories

| Category | Files |
|----------|-------|
| Phase commands | `osx-phase0.md` through `osx-phase6.md` (one per phase) |
| Workflow | `osx-modify.md`, `osx-review.md`, `osx-verify-tests.md`, `osx-changelog.md`, `osx-maintain-docs.md` |

The full list lives in `manifest.toml` under `[resources.commands.*]`.

## Frontmatter

OpenCode commands use minimal frontmatter:

```yaml
---
description: <one-line purpose> # Required
---
```

## Phase Command Contract

`osx-phase0.md` … `osx-phase6.md` correspond 1:1 with the orchestrator's PHASE0–PHASE6. The orchestrator dispatches the matching command at the start of each phase. See `source/orchestrator/AGENTS.md` for the dispatch table.

## Conventions

- Filename `osx-<command>.md` must match the slash-command name `/osx-<command>`.
- Phase commands are the **only** entry points the orchestrator uses; do not rename or remove them without updating `PHASE_COMMANDS` in `source/orchestrator/engine.py`.

## See Also

- `resources/AGENTS.md` — Manifest format
- `source/orchestrator/AGENTS.md` — Phase dispatch
- `resources/opencode/AGENTS.md` — Platform overview
