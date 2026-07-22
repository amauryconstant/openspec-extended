---
name: osx-concepts
description: Foundational knowledge for OpenSpec-extended. INVOKE when learning the framework or whenever a phase command says "load osx-concepts". Covers the framework (repo layout, artifacts, resource taxonomy, glossary) and decision guidance. For tool-layer choice and the 7-phase workflow, see `osx-workflow`.
license: MIT
---

# OpenSpec-extended for AI Agents

Framework reference for OpenSpec-extended. Covers the framework (repo layout, artifacts, resource taxonomy, glossary) and decision guidance.

---

## TL;DR — mental model in 30 seconds

**What OpenSpec-extended is**: a spec-driven development framework where you agree on **WHAT** to build before writing code. All artifacts live in the repository so humans and AI can collaborate.

**Skill split** (read both):
1. **This skill (`osx-concepts`)** — framework, repo layout, 4 artifacts, delta specs, resource taxonomy, decision guidance, glossary
2. **`osx-workflow`** — 4 tool layers (`openspec`, `openspec-extended`, `osx` CLI, `osx` lib) and the 7-phase autonomous loop driven by `openspec-extended orchestrate`

**Skip OpenSpec when**: 1-2 line fix, emergency hotfix, pure debugging.

---

## §1 Philosophy

Traditional workflows pretend work is linear (plan → implement → done). Real work isn't: you implement, realize the design is wrong, update specs, continue. **OpenSpec uses fluid actions, not rigid phases** — skills are things you can do anytime.

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
│   └── <domain>/
│       └── <capability>/
│           └── spec.md
└── changes/                  # In-progress proposals
    ├── <change-name>/        # Active change
    │   ├── proposal.md
    │   ├── design.md
    │   ├── tasks.md
    │   └── specs/            # Delta specs (ADDED/MODIFIED/REMOVED)
    └── archive/              # Completed history (date-prefixed)
        └── YYYY-MM-DD-<change-name>/
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

Query: `openspec status --change <name> --json` returns the full state per artifact (see `references/cli-reference.md` for the canonical JSON shape). From v1.5.0, the same status call accepts `--store <id>` when the change lives in a registered store.

### 2.5 Resource taxonomy

#### Core skills (`osc-*` — 12, renamed from upstream `openspec-*` by installer)

| Skill | Purpose |
|-------|---------|
| `osc-propose` | Create change + all artifacts in one step |
| `osc-explore` | Think through ideas without committing |
| `osc-new-change` | Create change folder |
| `osc-continue-change` | Create next artifact incrementally |
| `osc-update-change` | Revise existing artifacts; multi-artifact bidirectional reconciliation (v1.6.0) |
| `osc-ff-change` | Create all artifacts at once |
| `osc-apply-change` | Implement tasks from `tasks.md` |
| `osc-verify-change` | Verify implementation matches artifacts |
| `osc-sync-specs` | Merge delta specs into main specs |
| `osc-archive-change` | Complete a single change |
| `osc-bulk-archive-change` | Complete multiple changes with conflict detection |
| `osc-onboard` | Guided tutorial for first-time users |

#### Extended skills (`osx-*` — 8, local enhancements)

| Skill | Purpose |
|-------|---------|
| `osx-concepts` | **This skill** — framework, repo layout, artifacts, decision guidance |
| `osx-workflow` | 4 tool layers, 7-phase autonomous workflow (paired with this skill) |
| `osx-review-artifacts` | **Pre-implementation schema-driven audit** — validates each artifact against its schema `template` + `rules`, walks the dependency graph for cross-artifact consistency, and routes findings to the right editor |
| `osx-modify-artifacts` | **Single-artifact surgical editor (forward-only)** — small, targeted fixes; chains with `/opsx:update` for multi-artifact cases |
| `osx-review-test-compliance` | Spec-to-test alignment analysis (post-implementation) |
| `osx-maintain-ai-docs` | Update `AGENTS.md` and `CLAUDE.md` |
| `osx-generate-changelog` | Generate `CHANGELOG.md` from archive |
| `osx-commit` | Create commits matching project style |

> The pre-implementation `review`/`modify`/`update` trio replaces the older hardcoded `proposal`/`specs`/`design`/`tasks` model. Use `osx-review-artifacts` for an audit, `/opsx:update` for multi-artifact reconciliation, and `osx-modify-artifacts` for a single-artifact surgical edit.

> After this skill: 8 extended skills total. The taxonomy above lists all of them.

#### Agents (4 — orchestrator-dispatched)

| Agent | Phases | Permissions | Temp |
|-------|--------|-------------|------|
| `osx-analyzer` | PHASE0 | read-only (`edit: deny`) | 0.1 |
| `osx-builder` | PHASE1 | full read/write | 0.4 |
| `osx-reviewer` | PHASE2, PHASE5 | full read/write | 0.1 |
| `osx-maintainer` | PHASE3, PHASE4, PHASE6 | full read/write | 0.3 |

#### Commands (12)

| Type | Command | Dispatched by |
|------|---------|---------------|
| Phase | `osx-phase0` … `osx-phase6` | Orchestrator only |
| Workflow | `osx-modify`, `osx-review`, `osx-verify-tests`, `osx-changelog`, `osx-maintain-docs` | User/agent ad-hoc |

---

## §3 Decision guidance

**Use OpenSpec when**: multi-step (3+ tasks), refactors, architectural changes, unclear requirements, work spanning multiple sessions.

**Skip OpenSpec when**: single obvious fixes (1-2 lines), emergency hotfixes, pure debugging.

**Update vs new change**:
- Update existing if: same intent, refined execution; >50% scope overlap; original can't finish without these changes
- Start new if: intent fundamentally changed; <50% overlap; original is done standalone

**Continue vs fast-forward**:
- `osc-ff-change` (fast-forward) when requirements are clear, ready to build
- `osc-continue-change` (incremental) when exploring or wanting step-by-step control

**For detailed guidance** (including parallel changes, bulk archive, naming): `references/change-guidance.md`.

---

## §4 Glossary

| Term | Definition |
|------|------------|
| **Artifact** | A document within a change: `proposal.md`, `specs/`, `design.md`, `tasks.md` |
| **Archive** | Process of completing a change and merging its deltas into main specs |
| **Change** | A proposed modification, packaged as a folder with artifacts |
| **Delta spec** | Spec describing changes (ADDED/MODIFIED/REMOVED/RENAMED) relative to current specs |
| **Domain** | A logical grouping for specs (e.g., `auth/`, `payments/`) |
| **Requirement** | A specific behavior the system must have (SHALL/MUST/SHOULD) |
| **Scenario** | A concrete example in GIVEN/WHEN/THEN format |
| **Source of truth** | The `openspec/specs/` directory with current behavior |

---

## §5 References

| File | Load when |
|------|-----------|
| `../osx-workflow/SKILL.md` | Running the 7-phase autonomous workflow (paired skill) |
| `../osx-workflow/references/autonomous-workflow.md` | Per-phase protocol, transition logic, error recovery |
| `references/artifact-formats.md` | Creating or modifying any artifact |
| `references/cli-reference.md` | Need JSON output schema for any CLI command |
| `references/change-guidance.md` | Deciding update vs new, parallel work, bulk archive |
| `references/anti-patterns.md` | Made a mistake; need full catalog of what to avoid |
