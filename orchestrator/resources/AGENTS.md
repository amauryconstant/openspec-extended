---
paths:
  - "orchestrator/resources/**"
---

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
├── canonical/                      # Canonical source (single, tool-neutral)
│   ├── manifest.toml               # Per-side manifest (orchestrator scope)
│   ├── skills/osx-*/               # Workflow skills (osx-workflow etc.)
│   │   └── references/             # Skill-specific deeper references
│   ├── agents/osx-*.md             # Orchestrator-dispatched agents
│   └── commands/osx-*.md           # Slash commands (single-emit, flat)
```

Phase 2A: only `canonical/` is on disk. The per-adapter Claude/Codex/Kimi/etc.
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

Cross-cutting rules live in [`.agents/rules/`](../../.agents/rules/) (linked from root `AGENTS.md`).

## Resource types

| Type    | Path pattern                  | Frontmatter                                                       | Example          |
| ------- | ----------------------------- | ----------------------------------------------------------------- | ---------------- |
| Skill   | `skills/<name>/SKILL.md`      | `name`, `description`, `license`                                  | `osx-workflow`   |
| Agent   | `agents/<name>.md`            | `name`, `description`, `license`, `compatibility`, `allowed-tools`, `hidden: true`, `temperature`, `permission`. `mode:` must stay unset. | `osx-analyzer`   |
| Command | `commands/<name>.md` (flat)   | `description` (OpenCode) + optional `agent:` (OpenCode-only)      | `osx-phase0`     |

A skill directory is copied whole by `deploy_skills`, so `references/` and
`scripts/` subdirectories ship alongside `SKILL.md`. State I/O is done by
calling the binary's `osx` subcommand directly — no top-level `scripts/` or
`lib/` tree is shipped (locked by `tests/unit/test_architecture.py`).

## Manifest (`manifest.toml`)

Each side writes only its own resources; consumers that need both
sides (e.g. `validate_skills`) read and merge them.

| Tree                                         | Scope                                                                                |
| -------------------------------------------- | ------------------------------------------------------------------------------------ |
| `orchestrator/resources/canonical/manifest.toml` | Workflow skill, agents, phase commands, `osx-changelog`, `osx-maintain-docs`          |
| `skills/resources/canonical/manifest.toml`    | 3 skills (`osx-commit`, `osx-review-artifacts`, `osx-verify-tests`) and 2 slash commands (`osx-review`, `osx-verify-tests`) |

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
| `osx-mode-conventions.md`                                         | osx-maintain-docs, osx-phase3; transitively via the two refs above |
| `changelog-format.md`, `doc-structures.md`, `example-output.md`, `proposal-parsing-guide.md`, `update-examples.md`, `update-rules.md` | osx-changelog, osx-maintain-docs, osx-phase3 (consumed transitively) |

The shared pool formerly included `scoring-rubric.md` (consumed by `osx-verify-tests`); the rubric content has been inlined into the skill body per the alignment with `openspec-verify-change`'s self-contained posture and the reference is removed.

Shared references are excluded from `mise run version:check` (they don't map to a single manifest entry). The deploy copies each named reference into every consuming skill's own `references/` subdir at the target site, so each skill is self-sufficient.

**Two discovery paths**, because the two resource types work differently:

- **Skills** declare what they consume in the manifest's `references = [...]` list.
- **Commands** declare nothing. `_referenced_skill_refs` (`source/cli.py`) scrapes `references/<file>.md` mentions out of the command body at deploy time, so a command "consumes" a reference simply by naming it in prose. This is why several live references (`osx-mode-conventions.md` among them) appear in no manifest.

A skill entry looks like:

```toml
[resources.skills.osx-review-artifacts]
version = "0.5.0"
references = ["schema-agnostic-contract.md", "store-selection.md"]
```

## Phase commands

`commands/osx-phase0.md` … `commands/osx-phase6.md` correspond 1:1 with the orchestrator's PHASE0–PHASE6. Each phase command inherits the **Mandatory Start**, **Mandatory End**, and **blocker semantics** from `skills/references/phase-protocol-common.md` and `blocker-semantics.md`. State the phase-specific differences inline.

Phase commands are the **only** entry points the orchestrator uses; do not rename or remove them without updating `PHASE_COMMANDS` in `orchestrator/source/lib/osx/sides/orchestrator.py` (which `engine.py` imports).

## Adding a new slash command

1. Create `orchestrator/resources/canonical/commands/osx-<name>.md` with required frontmatter (`description` + optional `agent:`).
2. Add an entry to `orchestrator/resources/canonical/manifest.toml` under `[resources.commands]`.
3. Bump the version: `mise run version:update`.
4. If the command runs as part of the orchestrator workflow, add it to `PHASE_COMMANDS` in `source/lib/osx/sides/orchestrator.py`.
5. Add a unit test in `tests/unit/test_command_refs.py::TestFullCommandNames::test_expected_full_forms_present` if it introduces new full-form slash-command references.
6. If the body points at a shared reference, name it as `references/<file>.md` in prose — the deploy picks it up automatically.

## Conventions

- New resources get an `osx-` prefix; never collide with `osc-*` (core) names.
- One manifest entry per resource; CI fails on missing entries.
- Edit resources under `orchestrator/resources/canonical/` only; per-adapter
  rendering is driven by `ToolAdapter` fields at deploy time.
- Files under `orchestrator/core/` are not in this manifest — that tree is synced from upstream.

## See also

- [`.agents/rules/resource-separation.md`](../../.agents/rules/resource-separation.md) — Phase 5 disjoint-manifest invariant + shared-references pool ownership.
