---
name: osx-concepts
description: OpenSpec-extended reference. INVOKE when learning the framework, when a phase command says "load osx-concepts", or when deciding whether/how to use OpenSpec. Pair with `osx-workflow` for tool-layer and 7-phase mechanics.
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

Query: `openspec status --change <name> --json` returns the full state per artifact (see `references/cli-reference.md` for the canonical JSON shape). `status --json` carries the full dependency graph; older cores may omit `requires` — fall back to `instructions --json`.

### 2.5 Resource taxonomy

#### Extended skills (`osx-*` — 6 total)

The extended skill set lives under `resources/opencode/skills/` and mirrors 1:1
to `resources/claude/skills/`. Use this table as the canonical inventory.

| Skill | Default? | Purpose |
|-------|----------|---------|
| `osx-concepts` | yes | **This skill** — framework, repo layout, artifacts, decision guidance |
| `osx-workflow` | opt-in (`--with-autonomous`) | 4 tool layers, 7-phase autonomous workflow (paired skill) |
| `osx-review-artifacts` | yes | Pre-implementation schema-driven audit; routes findings to the right editor |
| `osx-modify-artifacts` | yes | Single-artifact surgical editor (forward-only); chains with `/osc-update` for multi-artifact cases |
| `osx-review-test-compliance` | yes | Spec-to-test alignment analysis (post-implementation) |
| `osx-commit` | yes | Create commits matching project style |

The orchestrator pre-flight (`source/lib/osx.py:REQUIRED_SKILLS`) asserts all 5
default skills are installed at the start of every change. `--with-autonomous`
additionally pulls `osx-workflow`, bringing the runtime requirement to 6 of 6.

> **Claude mirror**: every opencode command dual-emits to Claude as a modern
> skill (e.g. `commands/osx-modify.md` → `skills/osx-modify/SKILL.md`). See
> `resources/claude/AGENTS.md` §Dual-emit.

#### Agents (4 — orchestrator-dispatched)

`osx-analyzer` (PHASE0, read-only, 0.1) · `osx-builder` (PHASE1, full r/w, 0.4) · `osx-reviewer` (PHASE2/5, full r/w, 0.1) · `osx-maintainer` (PHASE3/4/6, full r/w, 0.3).

#### Commands (12)

- **Phase** (7) — `osx-phase0` … `osx-phase6`, dispatched by orchestrator only
- **Workflow** (5) — `osx-modify`, `osx-review`, `osx-verify-tests`, `osx-changelog`, `osx-maintain-docs`; user/agent ad-hoc

`osx-changelog` and `osx-maintain-docs` are **self-contained** slash commands
(the body lives in the command file itself, with referenced material in the
shared `references/` pool). The other three workflow commands
(`osx-modify`, `osx-review`, `osx-verify-tests`) are thin pointers that load a
skill body. On Claude, every workflow command dual-emits as a modern skill.

---

## §3 Decision guidance

**Use OpenSpec when**: multi-step (3+ tasks), refactors, architectural changes, unclear requirements, work spanning multiple sessions.

**Skip OpenSpec when**: single obvious fixes (1-2 lines), emergency hotfixes, pure debugging.

**Update vs new change**: update if same intent with >50% scope overlap; start new if intent fundamentally changed.

**Continue vs fast-forward**: `osc-ff-change` when requirements are clear; `osc-continue-change` when exploring.

Detailed guidance (parallel changes, bulk archive, naming): `references/change-guidance.md`.

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

## §5 References

| File | Load when |
|------|-----------|
| `../osx-workflow/SKILL.md` | Running the 7-phase autonomous workflow (paired skill) |
| `../osx-workflow/references/autonomous-workflow.md` | Per-phase protocol, transition logic, error recovery |
| `references/artifact-formats.md` | Creating or modifying any artifact |
| `references/cli-reference.md` | Need JSON output schema for any CLI command |
| `references/change-guidance.md` | Deciding update vs new, parallel work, bulk archive |
| `references/anti-patterns.md` | Made a mistake; need full catalog of what to avoid |