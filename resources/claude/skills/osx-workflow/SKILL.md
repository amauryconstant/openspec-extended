---
name: osx-workflow
description: Reference for the 7-phase OpenSpec-extended autonomous workflow. INVOKE when dispatched by the orchestrator, executing any osx-phaseN command, calling the osx state I/O tool, or troubleshooting the 7-phase loop. Covers the 4 tool layers, the phases, state files, the osx state I/O tool, and blocker/resume semantics.
license: MIT
---

# OpenSpec-extended Autonomous Workflow

Operational reference for the 7-phase loop driven by `openspec-extended orchestrate`. Covers the 4 tool layers, the phases, state files, the `osx` state I/O tool, and blocker/resume semantics.

---

## TL;DR

```
PHASE0 ARTIFACT_REVIEW → osx-analyzer  → osx-review-artifacts, osx-modify-artifacts
PHASE1 IMPLEMENTATION  → osx-builder   → osc-apply-change, osx-review-test-compliance
PHASE2 REVIEW          → osx-analyzer  → osc-verify-change
PHASE3 MAINTAIN_DOCS   → osx-maintainer→ osx-maintain-ai-docs
PHASE4 SYNC            → osx-maintainer→ osc-sync-specs
PHASE5 SELF_REFLECTION → osx-analyzer  → (autonomous reasoning)
PHASE6 ARCHIVE         → osx-maintainer→ osc-archive-change / osc-bulk-archive-change
```

**Tool**: every state mutation goes through the `osx` script at `.opencode/scripts/lib/osx` (one surface; same Python as `source/lib/osx.py`).

For the 4 tool layers (`openspec` / `openspec-extended` / `osx` CLI / `osx` lib), see §1 below.

---

## §1 Tool layers and CLIs

### §1.1 The 4 layer table

| # | Tool | Invocation | Used for |
|---|------|------------|----------|
| 1 | `openspec` (npm) | `openspec <sub>` | Query state, get instructions, validate, list, show |
| 2 | `openspec-extended` | `openspec-extended <sub>` | Install/update/orchestrate lifecycle |
| 3 | `osx` (deployed) | `.opencode/scripts/lib/osx` | State I/O from agents (what phase commands use) |
| 4 | `osx` (library) | `from source.lib import osx` | In-process callers (the orchestrator) |

> **Why this lives in `osx-workflow`**: the 4 CLI surfaces and the `openspec-extended` subcommands are workflow concerns because the agent running the orchestrator encounters them at runtime.

> **Key**: When the orchestrator dispatches you, you use **layer 3** (the deployed `osx` script). When the user runs a binary, that's **layer 2** (`openspec-extended`). The two share the same Python source.
>
> **The `osx` action vocabulary** (which `<dom> <act>` pairs are valid) lives in §4 of this skill — that's the protocol-layer concern. This section covers the layer concept; §4 covers what to actually call.

### §1.2 `openspec-extended` subcommands

| Subcommand | Purpose |
|------------|---------|
| `install <tool>` | Deploy extended resources; `<tool>` is `opencode` or `claude` |
| `update <tool>` | Force reinstall (overwrite existing) |
| `orchestrate <change>` | Run 7-phase autonomous workflow |
| `--version` | Print version |

Flags for `install` / `update`:

| Flag | Effect |
|------|--------|
| `--with-core` | Also deploy upstream `osc-*` skills (calls `openspec init --tools <tool> --force`) |

Flags for `orchestrate` (full semantics in §5 below):

| Flag | Default | Effect |
|------|---------|--------|
| `--from-phase PHASEN` | (auto-resume) | Start from specific phase; skips pre-flight |
| `--max-phase-iterations N` | 10 | Per-phase retry budget; `-1` = unlimited |
| `--timeout N` | 1800 | Per-agent-subprocess timeout in seconds |
| `--model M` | (platform default) | AI model to use |
| `--clean` / `-c` | off | Wipe state files and re-run pre-flight |
| `--force` / `-f` | off | Skip interactive prompts (dirty git, resume confirm) |
| `--list` | off | List available changes; do not orchestrate |
| `--dry-run` / `-d` | off | Show what would happen |
| `--verbose` / `-v` | off | Verbose output |
| `--no-color` / `-n` | off | Disable colored output |
| `--log-file F` | (auto) | Per-invocation log; moved to archive on PHASE6 |

> **No `--max-total-iterations` flag exists.** Only `--max-phase-iterations`.

### §1.3 Decision: which layer for what

| If the agent needs to... | Use |
|--------------------------|-----|
| Know what artifacts exist for a change | Layer 1: `openspec status --change <name> --json` |
| Get instructions for creating an artifact | Layer 1: `openspec instructions <art> --change <name> --json` |
| Mark the current phase complete | Layer 3: `osx state complete <change>` (full action set in §4) |
| Read state from inside Python | Layer 4: `osx.state_get(change)` (full action set in §4) |
| Trigger the autonomous workflow | Layer 2: `openspec-extended orchestrate <change>` |
| Install/update resources in a project | Layer 2: `openspec-extended install <tool>` |

For the full action set of layer 3 (`osx`), see §4 below.

---

## §2 The 7 phases

| Phase | Name in `state.json` | Agent | Key skills loaded | Purpose |
|-------|----------------------|-------|-------------------|---------|
| PHASE0 | `ARTIFACT_REVIEW` | `osx-analyzer` | `osx-review-artifacts`, `osx-modify-artifacts` | Validate artifacts; fix CRITICAL issues immediately |
| PHASE1 | `IMPLEMENTATION` | `osx-builder` | `osc-apply-change`, `osx-review-test-compliance` | Implement `tasks.md`; milestone commits |
| PHASE2 | `REVIEW` | `osx-analyzer` | `osc-verify-change` | Verify implementation matches artifacts |
| PHASE3 | `MAINTAIN_DOCS` | `osx-maintainer` | `osx-maintain-ai-docs` | Update `AGENTS.md` and `CLAUDE.md` |
| PHASE4 | `SYNC` | `osx-maintainer` | `osc-sync-specs` | Merge delta specs into main specs |
| PHASE5 | `SELF_REFLECTION` | `osx-analyzer` | (autonomous reasoning) | Evaluate the workflow; write `reflections.md` |
| PHASE6 | `ARCHIVE` | `osx-maintainer` | `osc-archive-change` or `osc-bulk-archive-change` | Archive change; clean transient files |

> **PHASE2 name disambiguation**: the engine's canonical phase name is `REVIEW`. The skill it loads is `osc-verify-change` ("Verification"). Both refer to the same phase. When you see `--phase REVIEW` in `decision-log.json`, that's PHASE2. The same is true for other phases: e.g., PHASE0 = `ARTIFACT_REVIEW` (engine) = `osx-review-artifacts` (skill).

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

`state.json` shape (written by the engine):
```json
{
  "phase": "PHASE2",
  "phase_name": "REVIEW",
  "iteration": 3,
  "phase_complete": true,
  "phase_iterations": {"PHASE0": 2, "PHASE1": 4, "PHASE2": 3},
  "total_invocations": 9,
  "started_at": "…",
  "last_updated": "…"
}
```

---

## §4 The `osx` tool — full domain/action reference

The `osx` script is at `.opencode/scripts/lib/osx`. Same Python source as `source/lib/osx.py` (the orchestrator calls it in-process; agents call it via the deployed script).

```bash
osx <domain> <action> [args]
```

Output: JSON to stdout. Errors: JSON to stderr `{"error":"<code>","message":"…",…}` + exit `1`.

**Canonical verbs**: the only read verb is `get`. The only write verbs are `append`, `complete`, `set-phase`, `transition`, `clear-transition`, `record`, `advance`, and `set` (for `complete`). There is **no** `show`, `list`, or `delete`.

> **Silent aliases accepted by the deployed `osx` CLI** (since `lib.osx 0.1.4`): `show` and `list` are routed to `get`; `set` is routed to `set-phase`; `clear` is routed to `clear-transition`. Error responses still list only the canonical verbs. Prefer canonical forms in scripts and docs.

| Domain | Read actions | Write / mutate actions |
|--------|--------------|------------------------|
| `ctx` | `get` | — |
| `git` | `get` | — |
| `baseline` | `get` | `record` |
| `state` | `get` | `complete`, `set-phase`, `transition`, `clear-transition` |
| `phase` | `current`, `next` | `advance` |
| `iterations` | `get` | `append` |
| `log` | `get` | `append` |
| `complete` | `check`, `get` | `set` |
| `validate` | `json`, `skills`, `commands`, `change-dir`, `archive`, `iterations`, `completion` | — |
| `instructions` | `instructions <artifact> [--change <name>] [--json]` | — |

### `ctx` — aggregate context

| Action | Args | Returns |
|--------|------|---------|
| `get` | `<change>` | `{change, state: {phase, iteration, phase_complete}, git: {modified, added, untracked, clean, branch}, artifacts: {proposal, specs, design, tasks}, history: {decision_log_entries, iterations_recorded}}` |

The first thing every phase command does: `osx ctx get "$1"`.

### `state` — phase state machine

| Action | Args | Effect |
|--------|------|--------|
| `get` | `<change>` | Read `state.json` |
| `complete` | `<change>` | Set `phase_complete: true`; orchestrator advances to next phase |
| `set-phase` | `<change> <PHASEN> [--iteration N]` | Force-set phase (use `orchestrate --from-phase` instead when possible) |
| `transition` | `<change> <target> <reason> [details]` | Set a pending transition; orchestrator routes to `<target>` next |
| `clear-transition` | `<change>` | Clear a pending transition |

**Transition reasons** (canonical, validated by the library):
- `implementation_incorrect` — code is wrong, do not modify artifacts
- `artifacts_modified` — specs/design updated, go to PHASE1 to re-implement
- `retry_requested` — same phase, different approach

### `phase` — phase sequence

| Action | Args | Effect |
|--------|------|--------|
| `current` | `<change>` | Read current phase (creates PHASE0 state if missing) |
| `next` | `<change>` | Read next phase in sequence |
| `advance` | `<change>` | Force-advance to next phase (rare; prefer `state complete`) |

### `iterations` — chronological iteration history

| Action | Args |
|--------|------|
| `get` | `<change>` → `{count, iterations[]}` |
| `append` | `<change> --phase P --iteration N [--summary S] [--status S] [--notes N] [--commit-hash H] [--issues JSON] [--artifacts-modified JSON] [--decisions JSON] [--errors JSON] [--extra JSON_OBJECT]` |

> `--extra` is merged as a JSON **object** (not stringified). Pass a flat object like `'{"tasks_completed":["1.1","1.2"]}'`. `--issues`, `--decisions`, `--errors` are merged as JSON arrays.

### `log` — decision log (different from iterations)

| Action | Args |
|--------|------|
| `get` | `<change>` → `{count, entries[]}` |
| `append` | `<change> --phase P --iteration N [--summary S] [--commit-hash H] [--next-steps S] [--issues JSON] [--artifacts-modified JSON] [--decisions JSON] [--errors JSON] [--extra JSON_OBJECT]` |

> **Distinction**: `log` is for one entry per phase (or sub-decision within a phase). `iterations` is for the chronological record of every iteration. Use both. They have different schemas; do not mix.

### `complete` — completion / blocker

| Action | Args | Effect |
|--------|------|--------|
| `check` | `<change>` | `{exists: true\|false}`; exit `0` if file exists, `1` if not |
| `get` | `<change>` | `{status, with_blocker, blocker_reason?}` |
| `set` | `<change> [status] [--blocker-reason R]` | Write `complete.json`; `status=BLOCKED` requires `--blocker-reason` |

### `baseline` — starting commit

| Action | Args | Effect |
|--------|------|--------|
| `record` | (none) | Capture `HEAD` + branch + timestamp to `.openspec-baseline.json` |
| `get` | (none) | Read the baseline |

### `git` — change-dir status

| Action | Args | Returns |
|--------|------|---------|
| `get` | `<change>` | `{modified, added, untracked, clean, branch}` for the change dir |

### `validate` — pre-flight checks

| Action | Args | Effect |
|--------|------|--------|
| `json` | `<file>` | Validate JSON syntax |
| `skills` | (none) | All required `osx-*` and `osc-*` skills present |
| `commands` | (none) | All 7 phase commands present |
| `change-dir` | `<change>` | Change dir exists with `proposal.md`, `design.md`, `tasks.md`, non-empty `specs/` |
| `archive` | `<change>` | Archive exists at `openspec/changes/archive/...-<-change>` |
| `iterations` | `<change>` | `iterations.json` exists and is valid JSON |
| `completion` | `<change>` | `state.json` + `complete.json` + `iterations.json` + `decision-log.json` + archive all present |

Exit `0` if valid, `1` if invalid.

### `instructions` — proxy to upstream

| Args | Effect |
|------|--------|
| `<artifact> [--change <name>] [--json]` | Proxy to `openspec instructions <artifact> --change <name> --json` |

---

## §5 Invocation

```bash
# Primary entry point
openspec-extended orchestrate <change> [options]

# Wrapper (deployed copy of engine.py)
.opencode/scripts/osx-orchestrate <change>
```

**Flags** (full reference in `osx-concepts/references/cli-reference.md` §B):

| Flag | Default | Effect |
|------|---------|--------|
| `--from-phase PHASEN` | (auto-resume) | Start from this phase; skips pre-flight |
| `--max-phase-iterations N` | `10` | Per-phase retry budget; `-1` = unlimited |
| `--timeout N` | `1800` | Per-agent-subprocess timeout in seconds |
| `--model M` | (platform default) | AI model name |
| `--clean` / `-c` | off | Wipe state files; re-run full pre-flight |
| `--force` / `-f` | off | Skip interactive prompts |
| `--list` | off | List available changes; do not orchestrate |
| `--dry-run` / `-d` | off | Show what would happen |
| `--verbose` / `-v` | off | Verbose output |
| `--no-color` / `-n` | off | Disable colored output |
| `--log-file F` | (auto, `.osx-orchestrate-<change>.log`) | Per-invocation log; on PHASE6 success, moved to archive and amended into the archive commit |

**Exit codes**:
- `0` — completed (ran through, resumed to completion, or change was already archived)
- `1` — phase failure, blocker detected, archive validation failed, change not found
- `2` — missing required argument
- `124` — phase hit per-subprocess timeout (raised as phase failure, exit `1`)
- `130` — interrupted (SIGINT/SIGTERM)

**State cleanup on success**: `state.json`, `complete.json`, `.openspec-baseline.json`, and the auto log are deleted. On failure or interrupt: state files are preserved for resumption. On PHASE6 success: the auto log moves to `<archive>/osx-orchestrate.log` and the archive commit is amended.

---

## §6 Iteration limits and timeouts

- **Default `--max-phase-iterations`**: **10**. Not 5 — the phase command files (osx-phase0..6) historically referenced `5`; trust the orchestrator, not the phase files.
- **`-1`** = unlimited.
- **`--timeout`**: **1800 seconds per agent subprocess** (the orchestrator spawns a fresh AI process per iteration; this is per-subprocess, not per phase).
- **No `--max-total-iterations` flag exists.** If you see it referenced, it's stale.

When the per-phase limit is reached the orchestrator halts and logs to `decision-log.json`; user must investigate.

---

## §7 Blocker and resume semantics

### Blocker (unrecoverable)

When an issue is **unrecoverable** (third-party API down, missing required access, contradictory specs that block all paths), signal:

```bash
osx complete set <change> BLOCKED --blocker-reason "Specific reason"
```

The orchestrator detects `complete.json` and halts.

A blocker is **not**:
- Failing tests (fix in PHASE1, commit, re-iterate)
- Unclear specs (use `osx-modify-artifacts`, then `state transition … artifacts_modified`)
- Missing dependency (add it)
- Implementation bug (transition `… implementation_incorrect` to PHASE1)

### Resume after a blocker

```bash
# Fix the underlying issue first, then:
rm openspec/changes/<change>/complete.json
openspec-extended orchestrate <change>            # resumes from state.json
# or skip ahead:
openspec-extended orchestrate <change> --from-phase PHASE3
```

### Auto-resume

The orchestrator reads `state.json` at start. If it exists, it asks to resume that phase. `--force` auto-continues without prompting. A change in `openspec/changes/archive/` without `state.json` is considered complete; the orchestrator exits `0` immediately.

### Explicit transitions (PHASE2)

PHASE2 (`osc-verify-change`) uses `state transition` to send the workflow back to PHASE1 or retry itself:

| Situation | Command |
|-----------|---------|
| Artifacts were fixed | `osx state transition <change> PHASE1 artifacts_modified "Fixed unclear specs in design.md"` |
| Implementation is wrong | `osx state transition <change> PHASE1 implementation_incorrect "Missing validation in API handler"` |
| Same phase retry | `osx state transition <change> PHASE2 retry_requested "Alternative verification strategy"` |

> **Critical**: choose the correct reason. The wrong transition sends the workflow to the wrong place.

---

## §8 Pre-flight checklist

Before any phase action, verify:

- [ ] **Change directory exists**: `openspec/changes/<change>/` (or in archive)
- [ ] **Phase matches dispatch**: `osx state get <change>` → confirm `phase` field
- [ ] **Iteration budget**: check `iteration` vs `--max-phase-iterations`; if close to limit, finish cleanly and mark complete rather than re-iterate
- [ ] **Git state acceptable**: `osx git get <change>` (clean or `dirty` acknowledged with `--force` upstream)
- [ ] **Required skills present**: `osx validate skills` (the orchestrator's pre-flight already ran this on `--clean` starts; re-check after manual skill changes)

---

## §9 Edge cases (workflow)

1. **Archived change**: orchestrator exits 0 immediately if `state.json` is absent in the archive folder. Do not dispatch phase commands on archived changes.
2. **Dirty git**: pre-flight warns; pass `--force` upstream to continue, or commit/stash first. **Never use `git commit --no-verify`** to bypass pre-commit hooks (PHASE1 rule).
3. **Missing `openspec` CLI**: `install --with-core` fails; orchestrator pre-flight fails. Install: `npm install -g @fission-ai/openspec`.
4. **State file corruption**: if `state.json` is invalid JSON, the orchestrator halts. Delete it (or use `--clean`) to start fresh.
5. **Two changes touching the same spec**: use `osc-bulk-archive-change`; it detects spec conflicts and applies chronologically.
6. **`osx log` vs `osx iterations`**: `log` is for high-level phase decisions (one entry per phase, with `phase` + `iteration` + summary). `iterations` is chronological iteration history. They have different schemas; do not mix.
7. **`log --extra` / `iterations --extra`**: pass a JSON **object** (e.g., `'{"tasks_completed":["1.1"]}'`), not a JSON string. The library merges the object into the entry.
8. **Pre-commit hook failure in PHASE1**: never bypass. Fix the issue, re-stage, retry. After 3 attempts, document via `osx log` and consider signaling `BLOCKED`.

For framework-level edge cases (missing CLI on the user's machine, choosing the right CLI layer, etc.), see `osx-concepts/SKILL.md`.

---

## §10 Workflow patterns

- **Quick feature (single-session, no orchestrator)**: `osc-new-change` → `osc-ff-change` → `osc-apply-change` → `osc-verify-change` → `osc-archive-change`
- **Exploratory**: `osc-explore` → [investigation] → `osc-new-change` → `osc-continue-change` → ... → `osc-apply-change`
- **Parallel changes (no orchestrator)**: switch between changes with explicit names: `osc-new-change <other>`, work it, archive, then resume the paused one. Avoids orchestrator state.
- **Enhanced manual (with `osx-*` skills)**: `osc-new-change` → `osc-ff-change` → `osx-review-artifacts` → `osc-apply-change` → `osx-review-test-compliance` → `osx-maintain-ai-docs` → `osc-archive-change` → `osx-generate-changelog`
- **Autonomous (full 7-phase loop)**: `openspec-extended orchestrate <change>`. The orchestrator dispatches per phase; each phase loads the relevant skills.

---

## §11 References

| File | Load when |
|------|-----------|
| `references/autonomous-workflow.md` | Per-phase protocol, transition logic, error recovery, phase failure modes |

**Top workflow anti-patterns**:
1. Marking tasks `[x]` before code is written and tested
2. Skipping `osx log` / `osx iterations` append after a phase action
3. Using `git commit --no-verify` to bypass pre-commit hooks
4. Calling `osx state complete` for PHASE6 (PHASE6 detects completion via archive dir, not state)
5. Setting `complete.json` for issues that are actually fixable in the current phase |
