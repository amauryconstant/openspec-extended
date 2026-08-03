---
name: osx-workflow
description: 7-phase workflow reference. INVOKE when dispatched into PHASE0..PHASE6, when calling the osx state I/O tool, or when troubleshooting the loop. Pair with `osx-concepts` for framework concepts.
license: MIT
---

# OpenSpec-extended Autonomous Workflow

Operational reference for the 7-phase loop driven by `openspec-extended orchestrate`. `OSX_AUTONOMOUS=1` is set for skills invoked by that orchestrator, so interactive confirmation steps use their documented autonomous defaults. Covers the 4 tool layers, the phases, state files, the `osx` state I/O tool, and blocker/resume semantics.

---

## TL;DR

```
PHASE0 ARTIFACT_REVIEW → osx-analyzer   → osx-review-artifacts (audit + routing); /osx-modify or /opsx:update for fixes
PHASE1 IMPLEMENTATION  → osx-builder    → osc-apply-change, osx-review-test-compliance
PHASE2 REVIEW          → osx-reviewer   → osc-verify-change (writes verification-report.md, commits)
PHASE3 MAINTAIN_DOCS   → osx-maintainer → osx-maintain-ai-docs
PHASE4 SYNC            → osx-maintainer → osc-sync-specs
PHASE5 SELF_REFLECTION → osx-reviewer   → (writes reflections.md, commits)
PHASE6 ARCHIVE         → osx-maintainer → osc-archive-change / osc-bulk-archive-change
```

PHASE0 is read-only — it dispatches `osx-analyzer` (`edit: deny`) and emits a routing report. PHASE2 and PHASE5 dispatch `osx-reviewer` (`mode: subagent`, `edit: allow`) and write `verification-report.md` / `reflections.md` plus a commit.

**Tool**: every state mutation goes through `openspec-extended osx <domain> <action>`. Library lives at `source/lib/osx.py`.

---

## §1 Tool layers

### §1.1 The 4 layers

| # | Tool | Invocation | Used for |
|---|------|------------|----------|
| 1 | `openspec` (npm) | `openspec <sub>` | Query state, get instructions, validate |
| 2 | `openspec-extended` | `openspec-extended <sub>` | Install/update/orchestrate lifecycle |
| 3 | `osx` (CLI subcommand) | `openspec-extended osx …` | State I/O from agents (phase commands) |
| 4 | `osx` (library) | `from source.lib import osx` | In-process callers (orchestrator) |

> **Key**: orchestrator-dispatched agents use layer 3; user-invoked runs use layer 2. Layers 2 and 3 are the same binary. Layer 3's action vocabulary is in §4.

### §1.2 `openspec-extended` flags (orchestrate)

| Flag | Default | Effect |
|------|---------|--------|
| `--from-phase PHASEN` | (auto-resume) | Start from specific phase; skips pre-flight |
| `--max-phase-iterations N` | 10 | Per-phase retry budget; `-1` = unlimited |
| `--timeout N` | 1800 | Per-agent-subprocess timeout (seconds) |
| `--model M` | (platform default) | AI model name |
| `--clean` / `-c` | off | Wipe state files; re-run pre-flight |
| `--force` / `-f` | off | Skip interactive prompts |
| `--list` | off | List changes; do not orchestrate |
| `--dry-run` / `-d` | off | Show what would happen |
| `--verbose` / `-v` | off | Verbose output |
| `--log-file F` | (auto) | Per-invocation log; moved to archive on PHASE6 |

`install`/`update` accept `--with-core` to deploy upstream `osc-*` skills. **No `--max-total-iterations` flag exists.**

### §1.3 Decision: which layer for what

| If the agent needs to... | Use |
|--------------------------|-----|
| Know what artifacts exist for a change | Layer 1: `openspec status --change <name> --json` |
| Get instructions for creating an artifact | Layer 1: `openspec instructions <art> --change <name> --json` |
| Derive the full transitive required set | Layer 1: `openspec status --json` (v1.7.0+ `requires` array) |
| Mark the current phase complete | Layer 3: `osx state complete <change>` |
| Read state from inside Python | Layer 4: `osx.state_get(change)` |
| Trigger the autonomous workflow | Layer 2: `openspec-extended orchestrate <change>` |

For the full action set of layer 3, see §4.

---

## §2 The 7 phases

| Phase | Name in `state.json` | Agent | Key skills | Purpose |
|-------|----------------------|-------|------------|---------|
| PHASE0 | `ARTIFACT_REVIEW` | `osx-analyzer` | `osx-review-artifacts` + `osc-update-change` (default) or `osx-modify-artifacts` (surgical fallback) | Schema-driven audit; routing report (read-only) |
| PHASE1 | `IMPLEMENTATION` | `osx-builder` | `osc-apply-change`, `osx-review-test-compliance` | Implement `tasks.md`; milestone commits |
| PHASE2 | `REVIEW` | `osx-reviewer` | `osc-verify-change`; Case A → `osc-update-change` (default) or `osx-modify-artifacts` (isolated defect) | Verify implementation; writes `verification-report.md` |
| PHASE3 | `MAINTAIN_DOCS` | `osx-maintainer` | `osx-maintain-ai-docs` | Update `AGENTS.md` and `CLAUDE.md` |
| PHASE4 | `SYNC` | `osx-maintainer` | `osc-sync-specs` | Merge delta specs into main specs |
| PHASE5 | `SELF_REFLECTION` | `osx-reviewer` | (autonomous reasoning) | Evaluate the workflow; writes `reflections.md` |
| PHASE6 | `ARCHIVE` | `osx-maintainer` | `osc-archive-change` or `osc-bulk-archive-change` | Archive change; clean transient files |

> **Name disambiguation**: engine canonical is `REVIEW`; skill is `osc-verify-change`. Both refer to PHASE2.

---

## §3 State files

All live in `openspec/changes/<change>/` (or `openspec/changes/archive/YYYY-MM-DD-<change>/` after archive).

| File | Purpose | Lifecycle |
|------|---------|-----------|
| `state.json` | Current phase, iteration, `phase_complete` flag | Deleted on PHASE6 success |
| `complete.json` | Written only on `BLOCKED`; carries `blocker_reason` | Deleted by orchestrator on success |
| `iterations.json` | Chronological history of all phase iterations | Archived |
| `decision-log.json` | Agent decisions and reasoning per iteration | Archived |
| `.openspec-baseline.json` (project root) | Starting commit hash | Gitignored; deleted on success |

`state.json` shape:
```json
{
  "phase": "PHASE2",
  "phase_name": "REVIEW",
  "iteration": 3,
  "phase_complete": true,
  "phase_iterations": {"PHASE0": 2, "PHASE1": 4, "PHASE2": 3},
  "total_invocations": 9
}
```

---

## §4 The `osx` tool — domain/action reference

`openspec-extended osx <domain> <action>`. Output: JSON to stdout. Errors: JSON to stderr + exit `1`.

**Canonical verbs**: read = `get`; write = `append`, `complete`, `set-phase`, `transition`, `clear-transition`, `record`, `advance`, `set`, `set-routes`, `clear-routes`. There is **no** `show`, `list`, or `delete`.

> **Silent aliases** (since `lib.osx 0.1.4`): `show`/`list` → `get`; `set` → `set-phase`; `clear` → `clear-transition`. Prefer canonical forms.

| Domain | Read actions | Write / mutate actions |
|--------|--------------|------------------------|
| `ctx` | `get` | — |
| `git` | `get` | — |
| `baseline` | `get` | `record` |
| `state` | `get` | `complete`, `set-phase`, `transition`, `clear-transition`, `set-routes`, `clear-routes` |
| `phase` | `current`, `next` | `advance` |
| `iterations` | `get` | `append` |
| `log` | `get` | `append` |
| `complete` | `check`, `get` | `set` |
| `validate` | `json`, `skills`, `commands`, `change-dir`, `archive`, `iterations`, `completion` | — |
| `instructions` | `instructions <artifact> [--change <name>] [--json]` | — |

### `ctx` — aggregate context

`get <change>` → `{change, state: {phase, iteration, phase_complete}, git: {modified, added, untracked, clean, branch}, artifacts: {proposal, specs, design, tasks}, history: {decision_log_entries, iterations_recorded}}`. First thing every phase command runs.

### `state` — phase state machine

| Action | Args | Effect |
|--------|------|--------|
| `get` | `<change>` | Read `state.json` |
| `complete` | `<change>` | Set `phase_complete: true`; orchestrator advances |
| `set-phase` | `<change> <PHASEN> [--iteration N]` | Force-set phase (use `orchestrate --from-phase` instead when possible) |
| `transition` | `<change> --target <PHASEN> --reason <reason> [--details "..."]` | Set a pending transition; orchestrator routes to `<target>` next |
| `clear-transition` | `<change>` | Clear a pending transition |
| `set-routes` | `<change> --routes "<comma-separated slash commands>"` | PHASE0 only: queue slash commands the user should run |
| `clear-routes` | `<change>` | Clear pending routes |

**Transition reasons** (canonical): `implementation_incorrect` (code wrong, don't modify artifacts), `artifacts_modified` (specs/design updated via `/opsx:update`, fallback `/osx-modify` for isolated defects, go to PHASE1), `retry_requested` (same phase, different approach).

### `phase` — phase sequence

| Action | Args | Effect |
|--------|------|--------|
| `current` | `<change>` | Read current phase (creates PHASE0 state if missing) |
| `next` | `<change>` | Read next phase in sequence |
| `advance` | `<change>` | Force-advance (rare; prefer `state complete`) |

### `iterations` — chronological iteration history

`get <change>` → `{count, iterations[]}`. `append <change> --phase P --iteration N [--summary S] [--status S] [--notes N] [--commit-hash H] [--issues JSON] [--artifacts-modified JSON] [--decisions JSON] [--errors JSON] [--extra JSON_OBJECT]`.

> `--extra` is merged as a JSON **object**. Pass a flat object like `'{"tasks_completed":["1.1","1.2"]}'`. `--issues`, `--decisions`, `--errors` are merged as JSON arrays.

### `log` — decision log (different from iterations)

`get <change>` → `{count, entries[]}`. `append <change> --phase P --iteration N [--summary S] [--commit-hash H] [--next-steps S] [--issues JSON] [--artifacts-modified JSON] [--decisions JSON] [--errors JSON] [--extra JSON_OBJECT]`.

> **Distinction**: `log` is for one entry per phase (or sub-decision). `iterations` is for the chronological record of every iteration. Use both. Different schemas; do not mix.

### `complete` — completion / blocker

| Action | Args | Effect |
|--------|------|--------|
| `check` | `<change>` | `{exists: true\|false}`; exit 0/1 |
| `get` | `<change>` | `{status, with_blocker, blocker_reason?}` |
| `set` | `<change> [status] [--blocker-reason R]` | Write `complete.json`; `status=BLOCKED` requires `--blocker-reason` |

### `baseline` — starting commit

`record` (no args) → capture `HEAD` + branch + timestamp to `.openspec-baseline.json`. `get` (no args) → read the baseline.

### `git` — change-dir status

`get <change>` → `{modified, added, untracked, clean, branch}` for the change dir.

### `validate` — pre-flight checks

| Action | Args | Effect |
|--------|------|--------|
| `json` | `<file>` | Validate JSON syntax |
| `skills` | (none) | All required `osx-*` and `osc-*` skills present |
| `commands` | (none) | All 7 phase commands present |
| `change-dir` | `<change>` | Change dir exists with `proposal.md`, `design.md`, `tasks.md`, non-empty `specs/` |
| `archive` | `<change>` | Archive exists at `openspec/changes/archive/...-<change>` |
| `iterations` | `<change>` | `iterations.json` exists and is valid JSON |
| `completion` | `<change>` | `state.json` + `complete.json` + `iterations.json` + `decision-log.json` + archive all present |

Exit `0` if valid, `1` if invalid.

### `instructions` — proxy to upstream

`<artifact> [--change <name>] [--json]` → proxies to `openspec instructions <artifact> --change <name> --json`.

---

## §5 Invocation

```bash
openspec-extended orchestrate <change> [options]
```

**Exit codes**:
- `0` — completed, resumed to completion, or change was already archived
- `1` — phase failure, blocker detected, archive validation failed, change not found
- `2` — missing required argument
- `124` — phase hit per-subprocess timeout (raised as phase failure, exit `1`)
- `130` — interrupted (SIGINT/SIGTERM)

**State cleanup on success**: `state.json`, `complete.json`, `.openspec-baseline.json`, and the auto log are deleted. On failure or interrupt: state files are preserved. On PHASE6 success: the auto log moves to `<archive>/osx-orchestrate.log` and the archive commit is amended.

---

## §6 Iteration limits and timeouts

Default `--max-phase-iterations` is **10** (phase files historically referenced 5; trust the orchestrator). `-1` = unlimited. `--timeout` is **1800 seconds per agent subprocess** (per-subprocess, not per phase). No `--max-total-iterations` flag exists. When the per-phase limit is reached the orchestrator halts and logs to `decision-log.json`; user must investigate.

---

## §7 Blocker and resume semantics

### Blocker (unrecoverable)

When an issue is **unrecoverable** (third-party API down, missing required access, contradictory specs that block all paths), signal:

```bash
openspec-extended osx complete set <change> BLOCKED --blocker-reason "Specific reason"
```

The orchestrator detects `complete.json` and halts.

A blocker is **not**:
- Failing tests (fix in PHASE1, commit, re-iterate)
- Unclear specs (route via `osx-review-artifacts`, fix via `/osx-modify <name> <artifact-id>` or `/opsx:update <name>`)
- Missing dependency (add it)
- Implementation bug (transition `… implementation_incorrect` to PHASE1)

### Resume after a blocker

```bash
rm openspec/changes/<change>/complete.json
openspec-extended orchestrate <change>            # resumes from state.json
# or skip ahead:
openspec-extended orchestrate <change> --from-phase PHASE3
```

### Auto-resume

The orchestrator reads `state.json` at start. If it exists, it asks to resume that phase. `--force` auto-continues. A change in `openspec/changes/archive/` without `state.json` is complete; orchestrator exits `0` immediately.

### Explicit transitions (PHASE2)

PHASE2 (`osc-verify-change`) uses `state transition` to send the workflow back to PHASE1 or retry itself:

| Situation | Command |
|-----------|---------|
| Artifacts were fixed | `osx state transition <change> --target PHASE1 --reason artifacts_modified --details "..."` |
| Implementation is wrong | `osx state transition <change> --target PHASE1 --reason implementation_incorrect --details "..."` |
| Same phase retry | `osx state transition <change> --target PHASE2 --reason retry_requested --details "..."` |

> **Critical**: choose the correct reason. The wrong transition sends the workflow to the wrong place.

---

## §8 Pre-flight checklist

Before any phase action, verify:

- [ ] **Change directory exists**: `openspec/changes/<change>/` (or in archive)
- [ ] **Phase matches dispatch**: `osx state get <change>` → confirm `phase` field
- [ ] **Iteration budget**: `iteration` vs `--max-phase-iterations`; if close to limit, finish cleanly rather than re-iterate
- [ ] **Git state acceptable**: `osx git get <change>` (clean or `dirty` acknowledged with `--force`)
- [ ] **Required skills present**: `osx validate skills`

---

## §9 Edge cases (workflow)

1. **Archived change**: orchestrator exits 0 immediately if `state.json` is absent in the archive folder. Do not dispatch phase commands on archived changes.
2. **Dirty git**: pre-flight warns; pass `--force` to continue, or commit/stash first. **Never use `git commit --no-verify`** to bypass pre-commit hooks (PHASE1 rule).
3. **Missing `openspec` CLI**: `install --with-core` fails; orchestrator pre-flight fails. Install: `npm install -g @fission-ai/openspec`.
4. **State file corruption**: if `state.json` is invalid JSON, the orchestrator halts. Delete it (or use `--clean`) to start fresh.
5. **Two changes touching the same spec**: use `osc-bulk-archive-change`; it detects spec conflicts and applies chronologically.
6. **`osx log` vs `osx iterations`**: `log` is for high-level phase decisions (one entry per phase, with summary). `iterations` is chronological iteration history. Different schemas; do not mix.
7. **`--extra` flag**: pass a JSON **object** (e.g., `'{"tasks_completed":["1.1"]}'`), not a JSON string.
8. **Pre-commit hook failure in PHASE1**: never bypass. Fix the issue, re-stage, retry. After 3 attempts, document via `osx log` and consider signaling `BLOCKED`.

For framework-level edge cases, see `osx-concepts/SKILL.md`.

---

## §10 Workflow patterns

- **Quick feature (single-session)**: `osc-new-change` → `osc-ff-change` → `osc-apply-change` → `osc-verify-change` → `osc-archive-change`
- **Exploratory**: `osc-explore` → [investigation] → `osc-new-change` → `osc-continue-change` → ... → `osc-apply-change`
- **Parallel changes (no orchestrator)**: switch between changes with explicit names; archive one before resuming the paused one.
- **Enhanced manual**: `osc-new-change` → `osc-ff-change` → `/osx-review <name>` → `{/osx-modify | /opsx:update}` → `osc-apply-change` → `osx-review-test-compliance` → `osx-maintain-ai-docs` → `osc-archive-change` → `osx-generate-changelog`
- **Autonomous (full 7-phase loop)**: `openspec-extended orchestrate <change>`. PHASE0 is read-only — emits routing report; user invokes the routed slash command externally.

---

## §11 References

| File | Load when |
|------|-----------|
| `references/autonomous-workflow.md` | Per-phase protocol, transition logic, error recovery |

Anti-patterns catalog: see `osx-concepts/references/anti-patterns.md`.
<!--
# AUTO-GENERATED from opencode via `mise run sync:mirrors` — do not edit by hand.
Source: resources/opencode/skills/osx-workflow/SKILL.md
Regenerate: `mise run sync:mirrors`
-->
