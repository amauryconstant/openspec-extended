# OpenSpec-extended Concepts

**Audience**: OpenSpec-extended **maintainers**. This is the framework-level
reference for the project itself — its repo layout, design philosophy,
the OpenSpec framework it builds on, and resource taxonomy. It is **not**
a runtime document; for that, see the `osx-workflow` skill, which is
what an AI agent reads while executing the 7-phase loop in a deployed
project.

**For agents in a deployed project**: read the `osx-workflow` skill (in
your `.opencode/skills/osx-workflow/` or `.claude/skills/osx-workflow/`
after install). That skill covers the 4 tool layers, the 7 phases, the
`osx` state I/O tool, blocker and resume semantics, and decision guidance.

**For OpenSpec-extended maintainers**: read on. This document and
`osx-workflow` are scoped so they don't duplicate each other.

---

## §1 Philosophy

Traditional workflows pretend work is linear (plan → implement → done).
Real work isn't. **OpenSpec uses fluid actions, not rigid phases** —
skills are things you can do anytime.

| Principle | Meaning |
|-----------|---------|
| **Fluid not rigid** | No phase gates — work happens iteratively |
| **Iterative not waterfall** | Learn as you build; refine as you go |
| **Easy not complex** | Minimal ceremony; get started in seconds |
| **Brownfield-first** | Works with existing code; most work modifies systems |

---

## §2 The OpenSpec framework (built on)

The framework OpenSpec-extended extends. OpenSpec is upstream; we
vendored its core under `orchestrator/core/` and add an autonomous
workflow on top. The framework concepts below are OpenSpec's, not ours.

### 2.1 Project repo layout (deployed project, not this repo)

```
openspec/                          # Per-project
├── specs/                         # Source of truth (current behavior)
│   └── <domain>/<capability>/spec.md
└── changes/
    ├── <change-name>/             # Active change
    │   ├── proposal.md, design.md, tasks.md
    │   └── specs/                 # Delta specs (ADDED/MODIFIED/REMOVED)
    └── archive/YYYY-MM-DD-<name>/ # Completed history
```

### 2.2 Artifacts

| Artifact | Purpose |
|----------|---------|
| `proposal.md` | Why & what — intent, scope, capabilities, impact |
| `specs/` (delta) | Requirements as `## ADDED` / `## MODIFIED` / `## REMOVED` / `## RENAMED` sections |
| `design.md` | How — context, decisions, tradeoffs |
| `tasks.md` | Checklist — `- [ ]` (todo) / `- [x]` (done) |

### 2.3 Delta operations

| Section | On archive |
|---------|-----------|
| `## ADDED Requirements` | Append to main spec |
| `## MODIFIED Requirements` | Replace existing requirement |
| `## REMOVED Requirements` | Delete from main spec |
| `## RENAMED Requirements` | Rename in main spec |

### 2.4 Artifact state machine

| State | Symbol | Meaning |
|-------|--------|---------|
| `BLOCKED` | ○ | Dependencies not met |
| `READY` | ◆ | Can create now |
| `DONE` | ✓ | File exists |

Query: `openspec status --change <name> --json` returns the full state
per artifact. `status --json` carries the full dependency graph; older
cores may omit `requires` — fall back to `instructions --json`.

---

## §3 This repo's layout

```
openspec-extended/
├── install.sh                  # Bash installer (no Python dep)
├── openspec.spec               # PyInstaller spec
├── pyproject.toml              # Project metadata + entry point
├── orchestrator/               # Orchestrator side (workflow resources + Python engine + vendored core)
│   ├── source/                 # Python CLI engine
│   ├── core/                   # Vendored OpenSpec subtree (synced from upstream; read-only)
│   └── resources/              # Skills, agents, commands (opencode canonical + claude mirror)
├── skills/                     # Skills side (gap-filling utilities)
│   └── resources/              # Skills + wrapper commands (opencode canonical + claude mirror)
├── tests/                      # pytest + bats suite
├── docs/                       # User-facing documentation (you are here)
├── .mise/tasks/                # sync-core, release, sync-mirrors, version/* (bash)
└── research/                   # Platform documentation
```

Phase 4 split `resources/` into `orchestrator/resources/` (workflow side)
and `skills/resources/` (gap-filling side). Phase 5 split each side's
manifest into a per-side file. See `orchestrator/resources/AGENTS.md` for
the per-side manifest layout.

---

## §4 Resource taxonomy

The 19 extended resources are split across two parallel trees per
Phase 4 + Phase 5. The orchestrator side owns the workflow surface;
the skills side owns the gap-filling utilities. The two manifests are
disjoint; their union is the canonical resource set.

| Resource | Tree | Manifest side | Install default? |
|---|---|---|---|
| `osx-workflow` skill | orchestrator | `orchestrator/resources/<tool>/manifest.toml` | opt-in (`--with-autonomous`) |
| `osx-changelog`, `osx-maintain-docs` commands | orchestrator | orchestrator | yes |
| `osx-phase0..6` commands | orchestrator | orchestrator | opt-in (`--with-autonomous`) |
| `osx-analyzer`, `osx-builder`, `osx-maintainer`, `osx-reviewer` agents | orchestrator | orchestrator | opt-in (`--with-autonomous`) |
| `osx-commit` skill | skills | `skills/resources/<tool>/manifest.toml` | yes |
| `osx-review-artifacts` skill | skills | skills | yes |
| `osx-review-test-compliance` skill | skills | skills | yes |
| `osx-review`, `osx-verify-tests` commands | skills | skills | yes |

Each side's manifest is mirrored to Claude via `mise run sync-mirrors`.
On Claude, every opencode command dual-emits as both the legacy
`.claude/commands/osx/<name>.md` and the modern
`.claude/skills/osx-<name>/SKILL.md` form (mirrors upstream OpenSpec's
dual-emit, current as of v1.13.0).

When a resource is installed at the target site, each side writes its
own manifest at the target:
- `<target>/manifest.toml` — orchestrator side (legacy position)
- `<target>/skills-manifest.toml` — skills side

Consumers (`validate_skills`, `validate_commands`, `validate_deployment`)
read both manifests and merge the resources to cross-check the
REQUIRED_SKILLS / phase commands.

---

## §5 Glossary

| Term | Definition |
|------|------------|
| **Artifact** | Document within a change: `proposal.md`, `specs/`, `design.md`, `tasks.md` |
| **Archive** | Process of completing a change; merges deltas into main specs |
| **Change** | Proposed modification, packaged as a folder with artifacts |
| **Delta spec** | Spec describing changes (ADDED/MODIFIED/REMOVED/RENAMED) vs current specs |
| **Domain** | Logical grouping for specs (e.g., `auth/`, `payments/`) |
| **Requirement** | Specific behavior the system must have (SHALL/MUST/SHOULD) |
| **Scenario** | Concrete example in GIVEN/WHEN/THEN format |
| **Per-side manifest** | The Phase 5 split: each side's manifest declares only its own resources. Source-tree side manifests mirror cleanly; target-tree side manifests land at `<target>/manifest.toml` (orchestrator) and `<target>/skills-manifest.toml` (skills). |
| **Dual-emit** | Claude Code's command-as-skill mirror: every opencode command emits both the legacy `.claude/commands/osx/<name>.md` and the modern `.claude/skills/osx-<name>/SKILL.md`. Mirrors upstream OpenSpec v1.7.0 strategy. |
| **Store** | A standalone OpenSpec repo registered on a machine; consulted by the orchestrator when a change is requested with `--store <id>` (v1.5.0+). |

---

## See Also

- `osx-workflow` skill — runtime reference for AI agents in deployed projects
- `docs/audit.md` — audit procedure manual (design-time tooling; not shipped)
- `docs/cli-comparison.md` — upstream `openspec` vs `openspec-extended` vs `osx` subcommand
- `docs/orchestrator-state-machine.md` — 7-phase state machine
- `docs/review-modify-integration.md` — review/modify integration contract with core
- `docs/troubleshooting.md` — common issues
- `orchestrator/resources/AGENTS.md` — per-side manifest layout, resource types
