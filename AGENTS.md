# OpenSpec-extended

Bridge AI coding assistants with OpenSpec — spec-driven development framework. Agree on WHAT to build before writing code. Artifacts live in the repository, not in tool-specific systems.

## Mental Map

| Side                | Role                                          | Source of truth                       |
| ------------------- | --------------------------------------------- | ------------------------------------- |
| **Orchestrator**    | Python CLI + 7-phase workflow engine          | `orchestrator/source/`                |
| **Resources (orch.)** | Workflow skills, agents, phase commands     | `orchestrator/resources/canonical/`   |
| **Resources (skills)** | Gap-filling skills (commit, review, tests) | `skills/resources/canonical/`         |
| **Core (vendored)** | Upstream OpenSpec workflows (read-only)       | `orchestrator/core/`                  |
| **Tests**           | pytest + bats suite                           | `tests/`                              |

OpenCode is canonical on disk. Every other tool adapter renders from the
OpenCode source at deploy time via `ToolAdapter`. Core is synced from
upstream. The two resource trees are disjoint (different `manifest.toml`
per side).

## Rules

- **NEVER** edit files in `orchestrator/core/` directly — use `mise run sync-core`.
- **NEVER** bump versions by hand — use `mise run release` (project) or `mise run version:update` (per-resource).
- **`mise run release` requires a populated `CHANGELOG.md` entry** for the upcoming version (either `## [Unreleased]` or `## [<X.Y.Z>]`). The gate runs before any file mutations; bypass with `--skip-changelog-check` for hotfixes. See `.opencode/rules/version-management.md`.
- Pre-commit hook `check-platform-hardcodes` fails the commit if any per-tool hardcode slips into `cli.py` / `runner.py` / `lib/osx.py`.
- **Naming** (`osx-`/`osc-` prefixes, regex, manifest ownership): `.opencode/rules/naming-conventions.md`
- **Versioning** (project release vs per-resource bumps): `.opencode/rules/version-management.md`
- **Per-adapter rendering** (deploy-time token substitution, skill mirror): `.opencode/rules/per-adapter-rendering.md`
- **Vendored subtree** (`orchestrator/core/**`): `.opencode/rules/vendored-subtree.md`

## Navigation

| If you are…                             | Read first                                                         |
| --------------------------------------- | ------------------------------------------------------------------ |
| Editing Python source                   | `orchestrator/source/AGENTS.md`                                    |
| Editing the workflow engine             | `orchestrator/source/orchestrator/AGENTS.md`                       |
| Adding/editing a workflow skill         | `orchestrator/resources/AGENTS.md`                                 |
| Adding/editing a gap-filling skill      | `skills/AGENTS.md`                                                 |
| Editing tests                           | `tests/AGENTS.md`                                                  |
| Adding a new AI tool adapter            | `orchestrator/source/tools.py` + `.opencode/rules/naming-conventions.md` |

## Adding a new AI tool adapter

1. Add `REGISTRY[<tool_id>] = ToolAdapter(...)` in `orchestrator/source/tools.py`. Register it before existing tools so `detect_platform` picks it up first.
2. Pick the `commands_style` that matches the target's filesystem layout; if the new `runner_kind` is not `opencode_run` / `claude_print`, add a branch in `orchestrator/source/orchestrator/runner.py:_runner_for`.
3. Every adapter must populate the five Phase 1 surface fields: `ask_tool` (non-empty), `install_hint` (non-empty, names `openspec-extended install <tool_id>`), and leave `cross_ref_prefix`, `runner_args`, `frontmatter_extras` at their defaults unless the adapter actually needs them. Locked by `tests/unit/test_tool_registry.py::TestAdapterFieldDefaults`.
4. If the adapter's body cross-references diverge from the canonical `/` form (Codex's `$`, Kimi's `/skill:`), set `cross_ref_prefix` explicitly so `orchestrator/source/cli.py:_rewrite_skill_body_refs` rewrites `/opsx:<cmd>` → `<cross_ref_prefix>openspec-<cmd>`.
5. If the adapter's CLI shape differs from `<tool> --print --dangerously-skip-permissions "<prompt>"` (Cursor / Qwen Code / Kiro), declare `runner_args` so `GenericPrintRunner` (`orchestrator/source/orchestrator/runner.py`) inserts the right flags between the binary name and `--print`.
6. CLI / runner / engine / library layers read from the registry — no per-tool edits required there.

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
- **Resources**: `<side>/resources/canonical/` canonical, hand-edited; per-adapter rendering happens at deploy time (no on-disk mirrors)
- **Skills**: `osx-` prefix for extended, `osc-` reserved for core (vendored) skills
- **Project structure** (Python source lives under `orchestrator/source/` because PyInstaller's `pathex` adds that to `sys.path`; the binary lives at project root)

## License

MIT — see LICENSE file.
