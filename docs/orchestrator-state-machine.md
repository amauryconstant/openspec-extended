# Orchestrator State Machine

How `openspec-extended orchestrate` drives a change through seven phases, when phases advance, when they loop back, and what state survives each iteration.

The orchestrator is a **driver**, not a decision-maker. It spawns an AI process per phase, reads the resulting `state.json` and `decision-log.json` back, and decides whether to advance or loop.

## State Machine Diagram

```
                                          (any phase can loop back)
                                                          |
                                                          v
+-------------+    +-------------+    +-------------+    +--------+
|   PHASE0    |    |   PHASE1    |    |   PHASE2    |    |  ...   |
| Artifact    |--->| Implement   |--->| Review      |--->|        |
| Review      |    |             |    |             |    |        |
+-------------+    +-------------+    +-------------+    +--------+
| osx-phase0  |    | osx-phase1  |    | osx-phase2  |    |        |
| osx-analyzer|    | osx-builder |    | osx-analyzer|    |        |
+-------------+    +-------------+    +-------------+    +--------+
                                                          |
                                                          v
                                            +-------------+    +--------+
                                            |   PHASE6    |    |COMPLETE|
                                            | Archive     |--->|        |
                                            |             |    |        |
                                            +-------------+    +--------+
                                            | osx-phase6  |
                                            | osx-maintainer|
                                            +-------------+
```

The full sequence is `PHASE0 -> PHASE1 -> PHASE2 -> PHASE3 -> PHASE4 -> PHASE5 -> PHASE6 -> COMPLETE`. Each phase has a fixed command and agent pair defined in `source/orchestrator/engine.py:41-59`.

## Phase Reference

| Phase | Name | Command | Agent | Library function |
|-------|------|---------|-------|------------------|
| PHASE0 | ARTIFACT REVIEW | `osx-phase0` | `osx-analyzer` | `validate_change_dir` |
| PHASE1 | IMPLEMENTATION | `osx-phase1` | `osx-builder` | -- |
| PHASE2 | REVIEW | `osx-phase2` | `osx-analyzer` | -- |
| PHASE3 | MAINTAIN DOCS | `osx-phase3` | `osx-maintainer` | -- |
| PHASE4 | SYNC | `osx-phase4` | `osx-maintainer` | -- |
| PHASE5 | SELF-REFLECTION | `osx-phase5` | `osx-analyzer` | -- |
| PHASE6 | ARCHIVE | `osx-phase6` | `osx-maintainer` | `validate_archive` |

The main loop is `source/orchestrator/engine.py:1009-1102`. PHASE0 and PHASE6 have library validation hooks; the intermediate phases delegate entirely to the AI command.

## Transition Reasons

A phase only loops back if the AI process writes a `transition` block to `state.json` with a valid reason. Defined at `source/lib/osx.py:VALID_TRANSITION_REASONS`:

| Reason | Trigger | Typical effect |
|--------|---------|----------------|
| `implementation_incorrect` | Tests or build fail, or code does not match proposal | Loop to PHASE1 to re-implement |
| `artifacts_modified` | Artifacts changed since the last iteration | Loop to PHASE0 to re-review |
| `retry_requested` | Manual or self-reflection request | Loop to whatever phase the target specifies |

The orchestrator reads the transition with `check_transition`, `get_transition_reason`, and `get_transition_details` (`engine.py:437-453`), clears it with `clear_transition` (`engine.py:460`), and overwrites `current_phase` accordingly (`engine.py:1083-1098`).

If no transition is set, `advance_phase` (`engine.py:485`) moves to the next phase in the fixed sequence.

## Retry Budget

Each phase may iterate up to `DEFAULT_MAX_PHASE_ITERATIONS` times before the orchestrator halts with a non-zero exit. The default is `10` (`source/orchestrator/engine.py:62`). Override with `--max-phase-iterations N` on the `orchestrate` command, or pass `-1` for unlimited.

The budget counts both forward and backward iterations. A change that flips between PHASE1 and PHASE2 ten times under `implementation_incorrect` will exhaust the budget on either phase.

## Resume Semantics

When invoked against a change that already has a `state.json`, the orchestrator resumes from the recorded phase rather than restarting from PHASE0. The read happens at `engine.py:982-988`.

- Without `--force` and on a TTY, the user is prompted: `Continue? [Y/n]`. Default is yes.
- With `--force` or non-interactive (no TTY), auto-continue is logged.
- With `--from-phase PHASEx`, the recorded state is ignored and the run starts at `PHASEx`. Pre-flight validation is skipped in this case (`engine.py:978-979`).

## Schema Resolution

Pre-flight resolves the active workflow schema exactly once and stores it on `state.schema_name` and `state.schema_source` (`engine.py:292-293`). No subsequent phase re-resolves or clears these fields. The full path is asserted in `tests/integration/test_schema_name_propagation.py`.

Resolution precedence (4 levels, `source/lib/osx.py:1490-1547`):

1. Explicit `--schema` flag on `orchestrate` (sources as `explicit`).
2. Change-level metadata (`openspec/changes/<id>/.openspec.yaml`, sources as `change-metadata`).
3. Project config (`openspec/config.yaml` or `config.yml`, sources as `project-config`).
4. Default `spec-driven` (sources as `default`).

When `--schema` overrides a project config that declares a different schema, the orchestrator logs a warning and proceeds (`engine.py:297-302`).

## Cache: `_PATHS_CACHE`

`resolve_change_paths` (`source/lib/osx.py:164-219`) caches resolved change paths in `_PATHS_CACHE` (defined at `source/lib/osx.py:130`). The cache key is `(change, store)` — schema is intentionally not a key, because `resolve_change_paths` does not consult the schema when computing paths. This is a documented audit decision (Tier 4) and is locked by `tests/unit/test_architecture.py::TestSchemaSupport::test_resolve_change_paths_ignores_schema_for_paths`.

If you change `openspec/config.yaml` to a new schema mid-session and call `resolve_change_paths` again, the cache will serve the previously resolved paths. That is correct: schema does not affect path layout. Only `validate_change_dir` and `validate_change` consult the schema, and they re-resolve on every call.

## Pre-Flight Order

The orchestrator runs these checks in this order before the first phase (`engine.py:971-975`):

1. `validate_skills` — five `osx-*` skills plus four `osc-*` core skills are installed.
2. `validate_commands` — seven `osx-phase*.md` command files are installed.
3. `validate_git` — repository is initialized; dirty working tree warns or aborts.
4. `validate_change_dir` — `openspec/changes/<id>/` exists and contains the required artifacts for the resolved schema.
5. `validate_schema` — schema is resolved and cached on state.

After the checks pass, `record_baseline` captures the current commit hash so the orchestrator can later diff against it.

## Cancellation

SIGINT and SIGTERM kill the AI child process and record partial state via `cleanup` (`engine.py` cleanup section). The next invocation reads the partial `state.json` and prompts to resume from the recorded phase.

## See Also

- [CLI comparison](./cli-comparison.md) — `openspec` vs `openspec-extended` vs `osx`
- [Troubleshooting](./troubleshooting.md) — common errors and fixes
- `source/orchestrator/AGENTS.md` — phase model summary
- `source/orchestrator/engine.py` — full implementation