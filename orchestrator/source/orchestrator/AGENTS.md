---
paths:
  - "orchestrator/source/orchestrator/**"
---

# `source/orchestrator/` - 7-Phase Workflow Engine

Drives a change through seven autonomous phases by spawning AI processes per phase and persisting state between iterations.

## 7-Phase State Machine

| Phase | Name | Command | Agent | Write? |
|-------|------|---------|-------|--------|
| PHASE0 | ARTIFACT REVIEW | `osx-phase0` | `osx-analyzer` | no (read-only) |
| PHASE1 | IMPLEMENTATION | `osx-phase1` | `osx-builder` | yes |
| PHASE2 | REVIEW | `osx-phase2` | `osx-reviewer` | yes (`verification-report.md`, commit) |
| PHASE3 | MAINTAIN DOCS | `osx-phase3` | `osx-maintainer` | yes |
| PHASE4 | SYNC | `osx-phase4` | `osx-maintainer` | yes |
| PHASE5 | SELF-REFLECTION | `osx-phase5` | `osx-reviewer` | yes (`reflections.md`, commit) |
| PHASE6 | ARCHIVE | `osx-phase6` | `osx-maintainer` | yes |

## Constants

| Constant | Value | Meaning |
|----------|-------|---------|
| `DEFAULT_TIMEOUT` | `1800` | Per-phase AI subprocess timeout (seconds) |
| `DEFAULT_MAX_PHASE_ITERATIONS` | `10` | Retry budget per phase before giving up |

## Phase Transitions

A phase advances when the AI process exits 0 and reports completion. The orchestrator detects completion by reading `state.json` (via `osx.state_get`) or by checking the archive directory for PHASE6. Failed phases transition backward using one of three reasons:

| Reason | Trigger |
|--------|---------|
| `implementation_incorrect` | Tests/build fail or code does not match proposal |
| `artifacts_modified` | Artifacts changed since the last iteration |
| `retry_requested` | Manual or self-reflection request |

Special-case short-circuits:

| Condition | Effect |
|-----------|--------|
| PHASE0 emits `retire_capabilities: true` in `.openspec.yaml` and planning is complete | Skip to PHASE6 |

Defined in `source/lib/osx/__init__.py:VALID_TRANSITION_REASONS`. Set on `state.json` by the AI agent and read by the orchestrator.

## Auto-fix routing

When PHASE0's read-only audit emits a route the engine can satisfy without
user judgment, the engine dispatches the reconciling slash command itself,
then re-enters the phase to verify.

| Constant | Value | Meaning |
|----------|-------|---------|
| `AUTO_FIXABLE_ROUTES` | `frozenset({"osc-update-change"})` | Routes the engine self-serves. Membership accepts both the `/osc-update-change` and `osc-update-change` spellings. |
| `AUTO_FIX_AGENTS` | `{"osc-update-change": "osx-editor"}` | Agent dispatched per route. Kept separate from `PHASE_AGENTS` because routes are slash commands, not phases. |

Routes needing user judgment (intent change, missing artifacts, archive
decision, ambiguous findings) are **not** in `AUTO_FIXABLE_ROUTES` and keep
the halt-and-surface behaviour. Covered by `TestPhase0RouteHaltFallback`
(`tests/integration/test_phase_workflow.py`) and
`TestAutoFixAgentDispatchContract` (`tests/e2e/test_mechanism.py`).

## Loop Shape

```
PHASE0 → PHASE1 → PHASE2 → PHASE3 → PHASE4 → PHASE5 → PHASE6
                ↖ (any phase can loop back on transition reason)
```

Each phase may iterate up to `DEFAULT_MAX_PHASE_ITERATIONS` times before the orchestrator halts and surfaces the failure.

The CLI exposes `--from-phase` (start at a specific phase) and
`--to-phase` (stop after a specific phase). Unknown `--to-phase` values are
rejected at startup with exit code 2 and a message naming the valid phases
(`PHASE0..PHASE6`).

## Conventions

- The orchestrator is a **driver**, not a decision-maker. It calls the AI CLI and reads dicts back from in-process `osx` library functions (`osx.state_get`, `osx.phase_advance`, etc.).
- State persists under the change directory (typically `openspec/changes/<id>/state.json`). Engine-specific wrappers (`read_state`, `write_state` and the helpers around them in `engine.py`) call `source.lib.state_io` directly rather than `osx.state_*`; all JSON writes are atomic. Read-only `json.loads` inspections in orchestration and display paths do not affect write atomicity. Cleanup deletes state files directly because file removal is atomic at the OS level.
- Cancellation is via SIGINT/SIGTERM: the orchestrator kills the AI child and records the partial state.
- After PHASE6, the orchestrator runs `archive_log_file()` to move the per-invocation log into the archive directory and amend the archive commit.
- **`log*` write to stdout AND `state.log_file`** (ANSI-stripped in the file). Mirrors the runner's agent-output streaming so `openspec-spec.log` and the archived `osx-orchestrate.log` stay plain-text greppable. The orchestrator's own banner, info/warn/error lines, and commit hashes all reach the file — not just agent subprocess output. Locked by `tests/unit/test_engine_logging.py`. `log_verbose` retains its asymmetric behavior: when `--verbose` is on it only prints to stdout; when off it only writes to the file.
- `RunRequest.extra_prompt` is a low-level extension point for the runner. PHASE1 and PHASE6 populate it with `operations.{apply|archive}.guidance` from `openspec/config.yaml`; other phases leave it empty. The OpenCode runner attaches it via `--file`; the Claude and generic-print runners prepend it to the slash-command prompt.
- Full per-contract operational notes for v1.8.0–v1.13.0 orchestrator consumption (`isPlanningComplete`, `retire_capabilities`, `operationGuidance`, `show --diff`, `validate --archived`, `validate --report findings`, `missingPrerequisites`, `list --specs`, fenced-code preservation, retire_capabilities relaxations) live in [`.agents/rules/openspec-contract.md`](../../../.agents/rules/openspec-contract.md).

## Entry Point

- `run_orchestrator(state)` — synchronous function in `engine.py`, exposed via `source.orchestrator.__init__`.
- Mounted under the main CLI as `openspec-extended orchestrate` (defined in `source/cli.py:orchestrate`).

Runner dispatch and the pre-flight binary probe both read
`source.tools.REGISTRY`; adding an adapter that uses a different
`runner_kind` only requires a `_runner_for` branch in
`source/orchestrator/runner.py`.

## See Also

- Root `AGENTS.md` — Code Style, Versioning
- `orchestrator/source/AGENTS.md` — Module roles
- `orchestrator/source/lib/AGENTS.md` — `osx` library contract (state I/O)
- `orchestrator/resources/AGENTS.md` — Phase command + agent definitions
