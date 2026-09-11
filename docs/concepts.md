# OpenSpec-extended Concepts

Framework reference for OpenSpec-extended. Covers philosophy, repo layout,
artifacts, delta operations, resource taxonomy, and glossary.

> **Decision guidance** ("Use OpenSpec when...", "Update vs new change", etc.) lives in `osx-workflow` §3, not here.

---

## TL;DR — mental model in 30 seconds

**What OpenSpec-extended is**: a spec-driven development framework where you agree on **WHAT** to build before writing code. All artifacts live in the repository so humans and AI can collaborate.

**Skill split** (read both):
1. **This document (`docs/concepts.md`)** — framework, repo layout, 4 artifacts, delta specs, resource taxonomy, glossary
2. **`osx-workflow` skill** — 4 tool layers (`openspec`, `openspec-extended`, `osx` CLI, `osx` lib) and the 7-phase autonomous loop driven by `openspec-extended orchestrate`

---

## §1 Philosophy

Traditional workflows pretend work is linear (plan → implement → done). Real work isn't. **OpenSpec uses fluid actions, not rigid phases** — skills are things you can do anytime.

| Principle | Meaning |
|-----------|---------|
| **Fluid not rigid** | No phase gates — work happens iteratively |
| **Iterative not waterfall** | Learn as you build; refine as you go |
| **Easy not complex** | Minimal ceremony; get started in seconds |
| **Brownfield-first** | Works with existing code; most work modifies systems |

---

## §2 The Framework

### 2.1 Repository layout

```
openspec/
├── specs/                    # Source of truth (current behavior)
│   └── <domain>/<capability>/spec.md
└── changes/
    ├── <change-name>/        # Active change
    │   ├── proposal.md, design.md, tasks.md
    │   └── specs/            # Delta specs (ADDED/MODIFIED/REMOVED)
    └── archive/YYYY-MM-DD-<name>/   # Completed history
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

Query: `openspec status --change <name> --json` returns the full state per artifact. `status --json` carries the full dependency graph; older cores may omit `requires` — fall back to `instructions --json`.

### 2.5 Resource taxonomy

#### Extended skills (`osx-*` — 4 total)

The extended skill set lives across two trees per Phase 4 split:

- **Orchestrator side** (`orchestrator/resources/opencode/skills/`): 1 skill — `osx-workflow` (the orchestrator's reference doc)
- **Skills side** (`skills/resources/opencode/skills/`): 3 gap-filling skills

| Skill | Side | Default? | Purpose |
|-------|------|----------|---------|
| `osx-workflow` | orchestrator | opt-in (`--with-autonomous`) | 4 tool layers, 7-phase autonomous workflow (paired with this doc) |
| `osx-review-artifacts` | skills | yes | Pre-implementation schema-driven audit; routes findings to the right editor |
| `osx-review-test-compliance` | skills | yes | Spec-to-test alignment analysis (post-implementation) |
| `osx-commit` | skills | yes | Detect and apply project commit-message style |

The orchestrator pre-flight (`orchestrator/source/lib/osx.py:REQUIRED_SKILLS`) asserts all 3 default skills-side skills are installed at the start of every change. `--with-autonomous` additionally pulls `osx-workflow`, bringing the runtime requirement to 4 of 4.

> **Claude mirror**: every opencode command dual-emits to Claude as a modern skill (e.g. `commands/osx-review.md` → `skills/osx-review/SKILL.md`). See `orchestrator/resources/claude/AGENTS.md` §Dual-emit.

#### Agents (4 — orchestrator-dispatched)

`osx-analyzer` (PHASE0, read-only, 0.1) · `osx-builder` (PHASE1, full r/w, 0.4) · `osx-reviewer` (PHASE2/5, full r/w, 0.1) · `osx-maintainer` (PHASE3/4/6, full r/w, 0.3). All live in `orchestrator/resources/opencode/agents/`.

#### Commands (11)

- **Phase** (7) — `osx-phase0` … `osx-phase6`, dispatched by orchestrator only
- **Self-contained** (2) — `osx-changelog`, `osx-maintain-docs`; user-invoked ad-hoc, body lives in the command file
- **Skill wrapper** (2) — `osx-review`, `osx-verify-tests`; thin slash-form entry points that load a skill body

Orchestrator-side commands: `osx-phase0..6`, `osx-changelog`, `osx-maintain-docs` (lives at `orchestrator/resources/opencode/commands/`).
Skills-side commands: `osx-review`, `osx-verify-tests` (lives at `skills/resources/opencode/commands/`).

---

## §4 Glossary

| Term | Definition |
|------|------------|
| **Artifact** | Document within a change: `proposal.md`, `specs/`, `design.md`, `tasks.md` |
| **Archive** | Process of completing a change; merges deltas into main specs |
| **Change** | Proposed modification, packaged as a folder with artifacts |
| **Delta spec** | Spec describing changes (ADDED/MODIFIED/REMOVED/RENAMED) vs current specs |
| **Domain** | Logical grouping for specs (e.g., `auth/`, `payments/`) |
| **Requirement** | Specific behavior the system must have (SHALL/MUST/SHOULD) |
| **Scenario** | Concrete example in GIVEN/WHEN/THEN format |

---

## See Also

- `docs/audit.md` — audit procedure manual (design-time tooling; not shipped)
- `docs/cli-comparison.md` — upstream `openspec` vs `openspec-extended` vs `osx` subcommand
- `docs/orchestrator-state-machine.md` — 7-phase state machine
- `docs/review-modify-integration.md` — review/modify integration contract with core
- `docs/troubleshooting.md` — common issues
