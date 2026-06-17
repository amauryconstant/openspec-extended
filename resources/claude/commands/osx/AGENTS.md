# Claude Code Slash Commands

Concrete slash-command files. One file per command.

## File Naming

`<name>.md` (no `osx-` prefix in filename). The slash-command name is set via the `name:` frontmatter field, which **does** include the `osx-` prefix.

## Examples

| File | Frontmatter `name` | Invocation |
|------|--------------------|------------|
| `phase0.md` | `osx-phase0` | `/osx-phase0` |
| `phase1.md` | `osx-phase1` | `/osx-phase1` |
| `review.md` | `osx-review` | `/osx-review` |
| `modify.md` | `osx-modify` | `/osx-modify` |
| `verify-tests.md` | `osx-verify-tests` | `/osx-verify-tests` |

The full list is enumerated in `resources/claude/manifest.toml` under `[resources.commands.*]`.

## Conventions

- The frontmatter `name:` is the source of truth for the slash-command identifier — never rely on the filename alone.
- Phase command files must keep the `osx-phaseN` naming; the orchestrator's `PHASE_COMMANDS` table in `source/orchestrator/engine.py` references these names.

## See Also

- `resources/claude/commands/AGENTS.md` — Command directory conventions
- `resources/opencode/commands/AGENTS.md` — Sibling platform (treat as canonical)
- `source/orchestrator/AGENTS.md` — Phase dispatch
