# OpenSpec-extended

Bridge AI coding assistants with OpenSpec — spec-driven development framework. Agree on WHAT to build before writing code. Artifacts live in the repository, not in tool-specific systems.

## Mental Map

| Side                | Role                                          | Source of truth                       |
| ------------------- | --------------------------------------------- | ------------------------------------- |
| **Orchestrator**    | Python CLI + 7-phase workflow engine          | `orchestrator/source/`                |
| **Resources (orch.)** | Workflow skills, agents, phase commands     | `orchestrator/resources/opencode/`    |
| **Resources (skills)** | Gap-filling skills (commit, review, tests) | `skills/resources/opencode/`          |
| **Core (vendored)** | Upstream OpenSpec workflows (read-only)       | `orchestrator/core/`                  |
| **Tests**           | pytest + bats suite                           | `tests/`                              |

OpenCode is canonical on disk. Every other tool adapter renders from the
OpenCode source at deploy time via `ToolAdapter`. Core is synced from
upstream. The two resource trees are disjoint (different `manifest.toml`
per side).

## Critical Rules

- **NEVER** edit files in `orchestrator/core/` directly — use `mise run sync-core`.
- **NEVER** bump versions by hand — use `mise run release` (project) or `mise run version:update` (per-resource).
- Pre-commit hook `check-platform-hardcodes` fails the commit if any per-tool hardcode slips into `cli.py` / `runner.py` / `lib/osx.py`.

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
| Adding a new AI tool adapter            | `orchestrator/source/tools.py` + `.opencode/rules/naming-conventions.md` |
| Updating platform docs                  | Consult <https://github.com/Fission-AI/OpenSpec/tree/main/docs> + <https://opencode.ai/docs> for canonical upstream |
| Editing a per-adapter mirror file       | STOP — there is no on-disk per-adapter mirror. Edit the opencode source; deploy-time rendering produces the per-adapter layout |
| Editing vendored subtree                | STOP — use `sync-core`                                             |

## Cross-cutting Rules

- **Naming** (`osx-`/`osc-` prefixes, regex, manifest ownership): `.opencode/rules/naming-conventions.md`
- **Versioning** (project release vs per-resource bumps): `.opencode/rules/version-management.md`
- **Per-adapter rendering** (deploy-time token substitution, skill mirror): `.opencode/rules/per-adapter-rendering.md`
- **Vendored subtree** (`orchestrator/core/**`): `.opencode/rules/vendored-subtree.md`

## Commands

```bash
# Build / Test
mise run build                       # Build binary at dist/openspec-extended
mise run test                        # Default tests (unit + integration + mechanism + bats)
mise run verify                      # All checks
pytest -m unit|integration|mechanism
E2E_CONFIRM=1 mise run test:e2e      # Full e2e against built binary (slow)

# Sync
mise run sync-core                   # Pull latest upstream OpenSpec into orchestrator/core/

# Version / Release
mise run release patch|minor|major   # Project release (bumps + tag)
mise run version:check               # Report pending framework bumps
mise run version:update              # Apply framework bumps
```

## Conventions

- **Python**: PEP 8 + ruff, Python 3.12+, typer + rich + toml
- **Testing**: pytest with `unit`/`integration`/`mechanism`/`e2e` markers; bats for install + e2e
- **Resources**: `<side>/resources/opencode/` canonical, hand-edited; per-adapter rendering happens at deploy time (no on-disk mirrors)
- **Skills**: `osx-` prefix for extended, `osc-` reserved for core (vendored) skills
- **Project structure** (Python source lives under `orchestrator/source/` because PyInstaller's `pathex` adds that to `sys.path`; the binary lives at project root)

## License

MIT — see LICENSE file.
