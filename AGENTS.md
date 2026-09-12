# OpenSpec-extended

Bridge AI coding assistants with OpenSpec — spec-driven development framework. Agree on WHAT to build before writing code. Artifacts live in the repository, not in tool-specific systems.

## Mental Map

| Side                | Role                                          | Source of truth                       | Mirror                                |
| ------------------- | --------------------------------------------- | ------------------------------------- | ------------------------------------- |
| **Orchestrator**    | Python CLI + 7-phase workflow engine          | `orchestrator/source/`                | n/a                                   |
| **Resources (orch.)** | Workflow skills, agents, phase commands     | `orchestrator/resources/opencode/`    | `claude/` (auto-generated)            |
| **Resources (skills)** | Gap-filling skills (commit, review, tests) | `skills/resources/opencode/`          | `claude/` (auto-generated)            |
| **Core (vendored)** | Upstream OpenSpec workflows (read-only)       | `orchestrator/core/`                  | synced from upstream                  |
| **Tests**           | pytest + bats suite                           | `tests/`                              | n/a                                   |

OpenCode is canonical. Claude mirrors are auto-generated. Core is synced from upstream. The two resource trees are disjoint (different `manifest.toml` per side).

## Critical Rules

- **NEVER** edit files in `orchestrator/core/` directly — use `mise run sync-core`.
- **NEVER** edit files in `**/claude/` directly — edit the opencode sibling, then `mise run sync:mirrors`.
- **NEVER** bump versions by hand — use `mise run release` (project) or `mise run version:update` (per-resource).
- Pre-commit hook `sync-mirrors-check` fails the commit if any Claude mirror drifts.

## Navigation

| If you are…                             | Read first                                                         |
| --------------------------------------- | ------------------------------------------------------------------ |
| Editing Python source                   | `orchestrator/source/AGENTS.md`                                    |
| Editing the workflow engine             | `orchestrator/source/orchestrator/AGENTS.md`                       |
| Updating CLI/library domains (`osx`)    | `orchestrator/source/lib/AGENTS.md`                                |
| Adding/editing a workflow skill         | `orchestrator/resources/AGENTS.md`                                 |
| Adding/editing a gap-filling skill      | `skills/AGENTS.md`                                                 |
| Syncing core from upstream              | `orchestrator/core/AGENTS.md`                                      |
| Editing tests                           | `tests/AGENTS.md`                                                  |
| Updating platform docs                  | `research/AGENTS.md`                                               |
| Editing a Claude mirror file            | STOP — edit the opencode sibling, run `sync:mirrors`               |
| Editing vendored subtree                | STOP — use `sync-core`                                             |

## Cross-cutting Rules

- **Naming** (`osx-`/`osc-` prefixes, regex, manifest ownership): `.opencode/rules/naming-conventions.md`
- **Versioning** (project release vs per-resource bumps): `.opencode/rules/version-management.md`
- **Mirror generation** (Claude ↔ OpenCode, token substitution): `.opencode/rules/mirror-generation.md`
- **Vendored subtree** (`orchestrator/core/**`): `.opencode/rules/vendored-subtree.md`

## Commands

```bash
# Build / Test
mise run build                       # Build binary at dist/openspec-extended
mise run test                        # Default tests (unit + integration + mechanism + bats)
mise run verify                      # All checks
pytest -m unit|integration|mechanism
E2E_CONFIRM=1 mise run test:e2e      # Full e2e against built binary (slow)

# Sync / Mirror
mise run sync-core                   # Pull latest upstream OpenSpec into orchestrator/core/
mise run sync:mirrors                # Regenerate Claude mirrors from opencode source

# Version / Release
mise run release patch|minor|major   # Project release (bumps + tag)
mise run version:check               # Report pending framework bumps
mise run version:update              # Apply framework bumps
```

## Conventions

- **Python**: PEP 8 + ruff, Python 3.12+, typer + rich + toml
- **Testing**: pytest with `unit`/`integration`/`mechanism`/`e2e` markers; bats for install + e2e
- **Resources**: `<side>/resources/opencode/` canonical; `<side>/resources/claude/` is mirror
- **Skills**: `osx-` prefix for extended, `osc-` reserved for core (vendored) skills
- **Project structure** (Python source lives under `orchestrator/source/` because PyInstaller's `pathex` adds that to `sys.path`; the binary lives at project root)

## License

MIT — see LICENSE file.
