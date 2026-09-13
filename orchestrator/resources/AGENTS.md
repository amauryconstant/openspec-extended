# Resources (Orchestrator Side)

AI-assistant resources shipped inside the binary. Phase 4 split the
project's resource tree into two disjoint halves — the **orchestrator
side** (this directory) and the **skills side** at `skills/resources/`.
Within each side, the Claude tree is auto-generated from the OpenCode
tree.

## Layout

```
orchestrator/resources/
├── AGENTS.md                       # (you are here)
├── opencode/                       # OpenCode platform (canonical, single source)
│   ├── manifest.toml               # Per-side manifest (orchestrator scope)
│   ├── skills/osx-*/               # Workflow skills (osx-workflow etc.)
│   │   └── references/             # Skill-specific deeper references
│   ├── agents/osx-*.md             # Orchestrator-dispatched agents
│   └── commands/osx-*.md           # Slash commands (single-emit, flat)
```

Phase 2A: only `opencode/` is on disk. The per-adapter Claude/Codex/Kimi/etc.
layouts are rendered at deploy time by `orchestrator/source/cli.py:deploy_*`,
driven by `orchestrator/source/tools.py:ToolAdapter`. There is no
hand-maintained `claude/` mirror.

## Phase 4 / Phase 5 split rationale

Pre-Phase-4 the project had a single `resources/` root mixing two
concerns — autonomous workflow resources (skills that drive the
7-phase orchestrator) and utility/gap-filling skills (review, commit,
verify-tests). Phase 4 separated them so each side can version and
ship its own manifest independently. Phase 5 finished the split: each
side now owns a per-side manifest on disk and a per-side deploy loop.

## Naming, rendering, versioning

| Concern | Where the rules live |
|---|---|
| Naming (`osx-`/`osc-` prefixes) | `.opencode/rules/naming-conventions.md` |
| Per-adapter rendering (deploy-time token substitution + skill mirror) | `.opencode/rules/per-adapter-rendering.md` |
| Per-resource version bumps | `.opencode/rules/version-management.md` |

## Resource types

| Type    | Path pattern                  | Frontmatter                                                       | Example          |
| ------- | ----------------------------- | ----------------------------------------------------------------- | ---------------- |
| Skill   | `skills/<name>/SKILL.md`      | `name`, `description`, `license`                                  | `osx-workflow`   |
| Agent   | `agents/<name>.md`            | `description`, `hidden`, `mode`, `temperature`, `permission`       | `osx-analyzer`   |
| Command | `commands/<name>.md` (flat)   | `description` (OpenCode) + optional `agent:` (OpenCode-only)      | `osx-phase0`     |

Only skills, agents, and commands are deployed. State I/O is done by
calling the binary's `osx` subcommand directly — no scripts or lib
files are shipped.

## Manifest (`manifest.toml`)

Each side writes only its own resources; consumers that need both
sides (e.g. `validate_skills`) read and merge them.

| Tree                                         | Scope                                                                                |
| -------------------------------------------- | ------------------------------------------------------------------------------------ |
| `orchestrator/resources/opencode/manifest.toml` | Workflow skill, agents, phase commands, `osx-changelog`, `osx-maintain-docs`          |
| `skills/resources/opencode/manifest.toml`    | `osx-commit`, `osx-review-artifacts`, `osx-review-test-compliance`, `osx-review`, `osx-verify-tests` |

The two manifests are disjoint; their union is the canonical resource surface (locked by `tests/unit/test_resource_contract.py::TestManifestParity`).

Deployed manifest layout (per platform — `.opencode/` or `.claude/`):

| File                  | Owner            | Contents                                                                |
| --------------------- | ---------------- | ----------------------------------------------------------------------- |
| `manifest.toml`       | Orchestrator deploy | Orchestrator-side resources + core (`osc-*`) entries after `--with-core` |
| `skills-manifest.toml`| Skills deploy    | Skills-side resources only                                              |

Both deployed manifests are read by `validate_skills` and `validate_commands` to cross-check REQUIRED_SKILLS / phase commands against declared resources.

## Shared references (`skills/references/`)

Cross-cutting material that lives once and is reached by multiple skills.

| Reference                                                          | Used by                                                       |
| ------------------------------------------------------------------ | ------------------------------------------------------------- |
| `store-selection.md`                                              | osx-review-artifacts (skill) + osx-review (command)          |
| `schema-agnostic-contract.md`                                     | osx-review-artifacts                                          |
| `phase-protocol-common.md`                                        | osx-phase0..6 (commands)                                      |
| `blocker-semantics.md`                                            | osx-phase0..6 (commands)                                      |
| `osx-decision-logging.md`                                         | osx-phase0..6 (commands)                                      |
| `shell-argument-safety.md`                                        | osx-phase0..6 (commands)                                      |
| `scoring-rubric.md`                                               | osx-review-test-compliance                                    |
| `changelog-format.md`, `doc-structures.md`, `example-output.md`, `proposal-parsing-guide.md`, `update-examples.md`, `update-rules.md` | osx-review-artifacts, osx-changelog, osx-maintain-docs (consumed transitively) |

Shared references are excluded from `mise run version:check` (they don't map to a single manifest entry). The deploy copies each named reference into every consuming skill's own `references/` subdir at the target site, so each skill is self-sufficient.

A skill declares which shared references it consumes via the manifest's `references = [...]` list:

```toml
[resources.skills.osx-review-artifacts]
version = "0.3.3"
references = ["schema-agnostic-contract.md", "store-selection.md"]
```

## Phase commands

`commands/osx-phase0.md` … `commands/osx-phase6.md` correspond 1:1 with the orchestrator's PHASE0–PHASE6. Each phase command inherits the **Mandatory Start**, **Mandatory End**, and **blocker semantics** from `skills/references/phase-protocol-common.md` and `blocker-semantics.md`. State the phase-specific differences inline.

Phase commands are the **only** entry points the orchestrator uses; do not rename or remove them without updating `PHASE_COMMANDS` in `orchestrator/source/orchestrator/engine.py`.

## Conventions

- New resources get an `osx-` prefix; never collide with `osc-*` (core) names.
- One manifest entry per resource; CI fails on missing entries.
- Edit resources under `orchestrator/resources/opencode/` only; per-adapter
  rendering is driven by `ToolAdapter` fields at deploy time.
- Files under `orchestrator/core/` are not in this manifest — that tree is synced from upstream.
