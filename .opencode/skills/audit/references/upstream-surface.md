# Upstream Surface Map Template (openspec-core)

Use this template to capture the upstream surface in Phase A. Fill every applicable section; mark sections N/A when the surface lacks the artifact. Cite `file:line` for every claim.

## Contents

- [Repository Metadata](#repository-metadata)
- [CLI Surface](#cli-surface)
- [Library / Core Module Surface](#library--core-module-surface)
- [AI Surface (slash commands + skills)](#ai-surface-slash-commands--skills)
- [Profile / Delivery / Store Models](#profile--delivery--store-models)
- [Change Lifecycle & State](#change-lifecycle--state)
- [Schema Definitions](#schema-definitions)
- [Documentation Conventions](#documentation-conventions)

## Repository Metadata

| Field | Value |
|-------|-------|
| Subtree path | `openspec-core/` |
| Head commit | `<hash>` |
| Date | `<YYYY-MM-DD>` |
| Version (from `package.json`) | `<X.Y.Z>` |
| Runtime | `<node ≥X.Y.Z>` |
| Build system | `<pnpm>` |
| Package manager | `<pnpm>` |
| File count (TS source) | `<number>` |
| Lines of code (TS source) | `<number>` |

## CLI Surface

Source: `openspec-core/source/src/cli/index.ts` and `openspec-core/source/src/commands/`.

| # | Command | Category | Mutates? | Key flags | Source file:line |
|---|---------|----------|-----------|-----------|------------------|
| 1 | `init [path]` | Setup | yes | `--tools`, `--force`, `--profile` | `cli/index.ts:140-178` |
| 2 | `update [path]` | Setup | yes | `--force` | `cli/index.ts:201-213` |
| 3 | `list` | Browsing | no | `--specs`, `--changes`, `--sort`, `--json`, `--store` | `cli/index.ts:215-249` |
| 4 | `show [item]` | Browsing | no | `--json`, `--type`, `--deltas-only`, `--requirements`, `--store` | `cli/index.ts:378-405` |
| 5 | `validate [item]` | Validation | no | `--all`, `--changes`, `--specs`, `--type`, `--strict`, `--json`, `--concurrency`, `--store` | `cli/index.ts:354-375` |
| 6 | `archive [name]` | Lifecycle | yes | `-y`, `--skip-specs`, `--no-validate`, `--json`, `--store` | `cli/index.ts:326-343` |
| 7 | `new change <name>` | Workflow | yes | `--description`, `--goal`, `--schema`, `--json`, `--store` | `cli/index.ts:557-579` |
| 8 | `status` | Workflow | no | `--change`, `--schema`, `--json`, `--store` | `cli/index.ts:487-502` |
| 9 | `instructions [artifact]` | Workflow | no | `--change`, `--schema`, `--json`, `--store` | `cli/index.ts:505-525` |
| 10 | `templates` | Workflow | no | `--schema`, `--json` | `cli/index.ts:528-540` |
| 11 | `schemas` | Workflow | no | `--json` | `cli/index.ts:543-554` |
| 12 | `doctor` | Health | no | `--store`, `--json` | `cli/index.ts:557+` |
| 13 | `context` | Working context | optional `--code-workspace` | `--store`, `--json`, `--force` | `cli/index.ts:557+` |
| 14 | `feedback <message>` | Utility | side-effect (opens GH issue) | `--body` | `cli/index.ts:408-420` |
| 15 | `completion …` | Utility | yes (`install`/`uninstall`) | shell arg, `-y`, `--verbose` | `cli/index.ts:427-466` |
| 16 | `config …` | Config | mostly no (`set`/`unset`/`reset`/`edit` mutate) | subcommand-specific | `commands/config.ts:208-643` |
| 17 | `schema …` | Schema | `init`/`fork` mutate | subcommand-specific | `commands/schema.ts:290-1005` |
| 18 | `store …` | Stores | `setup`/`register`/`unregister`/`remove` mutate | `--id`, `--yes`, `--path`, `--remote`, etc. | `commands/store.ts:661-799` |
| 19 | `workset …` | Worksets | `create`/`open`/`remove` mutate | `--member`, `--tool`, `--yes` | `commands/workset.ts:561-657` |

Deprecated noun forms (do not consume): `change show/list/validate`, `spec show/list/validate`.

Hidden options (deliberate rejection targets): `--store-path`, `--initiative`, `--areas`.

## Library / Core Module Surface

Source: `openspec-core/source/src/core/`.

| Module | Purpose | Public exports | file:line |
|--------|---------|----------------|-----------|
| `openspec-root.ts` | Path constants + nearest-ancestor resolution | `OPENSPEC_ROOT_DIR`, `findRepoPlanningRootSync`, etc. | `core/openspec-root.ts:11-22` |
| `root-selection.ts` | Multi-strategy root resolution (cwd / store / declared) | `resolveOpenSpecRoot`, `ResolvedOpenSpecRoot` | `core/root-selection.ts:349-405` |
| `artifact-graph/` | Schema-driven artifact lifecycle + completion detection | `state.ts`, `outputs.ts`, `instruction-loader.ts` | `core/artifact-graph/` |
| `schemas/` | Zod schemas for proposals, specs, requirements, scenarios | `base.schema.ts`, `spec.schema.ts`, `change.schema.ts` | `core/schemas/` |
| `change-metadata/` | `.openspec.yaml` parser/validator | `readChangeMetadata`, schema | `core/change-metadata/schema.ts:25-36` |
| `project-config.ts` | `openspec/config.yaml` parser | `ProjectConfigSchema` | `core/project-config.ts:19-54` |
| `references.ts` | Cross-store spec lookup index | `assembleReferenceIndex` | `core/references.ts` |
| `store/` | v1.5.0 stores (Beta) — registry, git backend, operations | `setupStore`, `registerStore`, `listStores`, `doctorStores` | `core/store/operations.ts:1229` |
| `validation/` | Validator pipeline + constants | `Validator`, `validateChangeDeltaSpecs` | `core/validation/validator.ts` |
| `global-config.ts` | XDG-aware global config | `getGlobalConfig`, `saveGlobalConfig` | `core/global-config.ts:1-172` |
| `profiles.ts` | `core` (6) / `custom` (12) workflow profiles | `CORE_WORKFLOWS`, `ALL_WORKFLOWS` | `core/profiles.ts:14-32` |
| `command-generation/` | 26 tool adapters (Claude, OpenCode, Cursor, …) | `ToolCommandAdapter` interface, adapter registry | `core/command-generation/adapters/` |
| `migration.ts` + `legacy-cleanup.ts` | Pre-v1.x artifact migration + legacy command cleanup | `migrateIfNeeded`, `LEGACY_SLASH_COMMAND_PATHS` | `core/migration.ts`, `core/legacy-cleanup.ts` |
| `working-set.ts` + `relationship-health.ts` | Doctor / context inputs | `assembleWorkingSet`, `inspectRelationships` | `core/working-set.ts`, `core/relationship-health.ts` |

## AI Surface (slash commands + skills)

| Layer | Path | Count | Naming convention |
|-------|------|-------|-------------------|
| Slash commands (OpenCode) | `openspec-core/.opencode/commands/` | 12 | `opsx-<verb>.md` |
| Slash commands (Claude) | `openspec-core/.claude/commands/opsx/` | 12 | `<verb>.md` under `opsx/` subdir; display `OPSX: <verb>` |
| Skills | `openspec-core/.opencode/skills/openspec-<verb>-change/` (and Claude mirror) | 12 | `openspec-<verb>` |

Workflows (12): `propose`, `explore`, `new`, `continue`, `apply`, `update`, `ff`, `sync`, `archive`, `bulk-archive`, `verify`, `onboard`.

`core` profile = 6 workflows: `propose, explore, apply, update, sync, archive`. `custom` profile = all 12.

Frontmatter on every skill: `name`, `description`, `license`, `allowed-tools: Bash(openspec:*)`, `compatibility`, `metadata.generatedBy`.

## Profile / Delivery / Store Models

- **Profile model** (`core/profiles.ts:14-32`): `core` (default, 6 workflows) vs `custom` (explicit list, 12 max). Set via `openspec config profile`.
- **Delivery model** (`core/global-config.ts:12`): `both | skills | commands`. Controls what `openspec init/update` materializes.
- **Store model** (`core/store/foundation.ts`): per-machine registry in `~/.config/openspec/config.json`; per-store metadata in `<store>/.openspec-store/store.yaml`. Backend: git only (`StoreGitBackendConfig`). Commands accepting `--store <id>`: `list`, `show`, `status`, `instructions`, `new change`, `validate`, `archive`, `doctor`, `context`.
- **`store register` flag is `--id`** (NOT `--name`). Cite `commands/store.ts:543-580`.

## Change Lifecycle & State

State is **derived from filesystem**, not stored explicitly.

```
openspec/changes/<id>/
├── .openspec.yaml                  # ChangeMetadata (schema, created, goal, affected_areas, initiative)
├── proposal.md                     # WHY + WHAT + Capabilities + Impact
├── design.md                       # Context / Goals / Decisions / Risks / Migration
├── tasks.md                        # `- [ ] X.Y …` numbered groups
└── specs/<cap>/spec.md             # ADDED / MODIFIED / REMOVED / RENAMED sections
```

Lifecycle: empty dir → `new change` creates skeleton → artifacts added → `archive` moves to `openspec/changes/archive/YYYY-MM-DD-<id>/` and applies deltas into main specs.

Artifact completion is computed: `detectCompleted(graph, changeDir)` checks `artifactOutputExists(changeDir, artifact.generates)` (`core/artifact-graph/state.ts:14-29`).

## Schema Definitions

| Schema | Location | Artifacts | file:line |
|--------|----------|-----------|-----------|
| `spec-driven` (default) | `openspec-core/source/schemas/spec-driven/schema.yaml` | `proposal`, `specs`, `design`, `tasks`, `apply` | `schemas/spec-driven/schema.yaml:153` |

Validation rules (`core/validation/constants.ts`):
- `MIN_WHY_SECTION_LENGTH = 50`, `MAX_WHY_SECTION_LENGTH = 1000`
- `MIN_PURPOSE_LENGTH = 50`
- `MAX_REQUIREMENT_TEXT_LENGTH = 500`
- `MAX_DELTAS_PER_CHANGE = 10`
- Requirement body MUST contain `SHALL` or `MUST`
- Scenarios use level-4 header `#### Scenario: <name>`
- Every requirement ≥ 1 scenario

Zod schemas: `core/schemas/base.schema.ts`, `core/schemas/spec.schema.ts`, `core/schemas/change.schema.ts`.

Change-name regex: `^[a-z][a-z0-9]*(-[a-z0-9]+)*$` (`utils/change-utils.ts:57-97`).

## Documentation Conventions

| Doc | Purpose | file:line |
|-----|---------|-----------|
| `README.md` | Public overview, install, stance, telemetry opt-out | `README.md` |
| `docs/cli.md` | CLI reference, exit codes, env vars | `docs/cli.md:1-1182` |
| `docs/commands.md` | Per-slash-command docs | `docs/commands.md` |
| `docs/workflows.md` | Workflow philosophy + decision tree | `docs/workflows.md` |
| `docs/opsx.md` | OPSX design reference | `docs/opsx.md:1-666` |
| `docs/agent-contract.md` | **Authoritative JSON contract** for every `--json` command | `docs/agent-contract.md` |
| `docs/concepts.md`, `docs/glossary.md` | Terminology | `docs/concepts.md`, `docs/glossary.md` |
| `docs/customization.md`, `docs/existing-projects.md`, `docs/team-workflow.md` | Adoption patterns | `docs/` |

Known inconsistencies in agent-contract.md (lines 128-137): snake_case (store) vs camelCase (workflow); four parallel envelope types; archive diagnostics never carry `target`; `schemas`/`templates` ignore `--store`.
