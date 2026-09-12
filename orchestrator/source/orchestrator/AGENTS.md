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

| Reason | Trigger |
|--------|---------|
| Retirement (PHASE0 detects marker + planning complete) | Skip to PHASE6 | `retire_capabilities: true` in `.openspec.yaml` |

Defined in `source/lib/osx.py:VALID_TRANSITION_REASONS`. Set on `state.json` by the AI agent and read by the orchestrator.

## Loop Shape

```
PHASE0 → PHASE1 → PHASE2 → PHASE3 → PHASE4 → PHASE5 → PHASE6
                ↖ (any phase can loop back on transition reason)
```

Each phase may iterate up to `DEFAULT_MAX_PHASE_ITERATIONS` times before the orchestrator halts and surfaces the failure.

## Conventions

- The orchestrator is a **driver**, not a decision-maker. It calls the AI CLI and reads dicts back from in-process `osx` library functions (`osx.state_get`, `osx.phase_advance`, etc.).
- State persists under the change directory (typically `openspec/changes/<id>/state.json`). Engine-specific wrappers (`read_state`, `write_state`, and related helpers at `engine.py:307+`) call `source.lib.state_io` directly rather than `osx.state_*`; all JSON writes are atomic. Read-only `json.loads` inspections in orchestration and display paths do not affect write atomicity. Cleanup deletes state files directly because file removal is atomic at the OS level.
- Cancellation is via SIGINT/SIGTERM: the orchestrator kills the AI child and records the partial state.
- After PHASE6, the orchestrator runs `archive_log_file()` to move the per-invocation log into the archive directory and amend the archive commit.
- `RunRequest.extra_prompt` (A.4) is a low-level extension point for the runner. PHASE1 and PHASE6 populate it with `operations.{apply|archive}.guidance` from `openspec/config.yaml`; other phases leave it empty. The OpenCode runner attaches it via `--file`; the Claude runner prepends it to the slash-command prompt.
- Full per-contract operational notes for v1.8.0–v1.13.0 orchestrator consumption (`isPlanningComplete`, `retire_capabilities`, `operationGuidance`, `show --diff`, `validate --archived`, `validate --report findings`, `missingPrerequisites`, `list --specs`, fenced-code preservation, retire_capabilities relaxations) live in [`.opencode/rules/openspec-contract.md`](../../.opencode/rules/openspec-contract.md).

## Entry Point

- `run_orchestrator(state)` — synchronous function in `engine.py`, exposed via `source.orchestrator.__init__`.
- Mounted under the main CLI as `openspec-extended orchestrate` (defined in `source/cli.py:orchestrate`).

Phase 1C wired the runner dispatch and pre-flight binary probe through
`source.tools.REGISTRY`; adding a new adapter that uses a different
`runner_kind` only requires a `_runner_for` branch in
`source/orchestrator/runner.py`.

## See Also

- Root `AGENTS.md` — Code Style, Versioning
- `orchestrator/source/AGENTS.md` — Module roles
- `orchestrator/source/lib/AGENTS.md` — `osx` library contract (state I/O)
- `orchestrator/resources/AGENTS.md` — Phase command + agent definitions
