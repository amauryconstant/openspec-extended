---
paths:
  - "tests/e2e/**"
---

# End-to-End Tests

Split surface: the **pytest** half (`test_mechanism.py`) runs against the
source tree via `python -m source`; the **bats** half runs against the built
binary. Both cover the same CLI surface.

## Files

| File | Type | Runner | Runs by default? | Requires `E2E_CONFIRM=1`? |
|------|------|--------|------------------|---------------------------|
| `test_mechanism.py` | pytest, `@pytest.mark.mechanism` | `python -m source` | yes | no |
| `mechanism.bats` | bats | built binary | yes | no |
| `store-and-config-passthrough.bats` | bats | built binary | yes | no |
| `full-workflow.bats` | bats (audit-clean fixture) | built binary | no | yes |
| `helpers/e2e-helpers.bash` | shared bats helpers + `E2E_CONFIRM` gate | n/a | n/a | n/a |

## Coverage

- `mechanism.bats`, `store-and-config-passthrough.bats` and `test_mechanism.py`
  cover the CLI surface (commands, flags, exit codes) without AI calls.
  `store-and-config-passthrough.bats` asserts that every top-level passthrough
  and subcommand group is advertised on `--help`. `test_mechanism.py` also pins
  the PHASE0 self-healing contract (auto-fixable vs halt-and-surface routes,
  slash-command name resolution, pre-check failure mode) via the
  `TestSlashCommandNameResolution`, `TestPhase0AutoFixVsHaltContract`, and
  `TestAutoFixAgentDispatchContract` classes.
- `full-workflow.bats` exercises the entire 7-phase orchestrator with AI calls
  on the audit-clean `add-hello-script` fixture. Slow, network-dependent,
  gated on `E2E_CONFIRM=1` (`E2E_TIMEOUT=12000`).
- PHASE0 auto-fix routing is covered without e2e cost by
  `TestPhase0RouteHaltFallback` (`tests/integration/test_phase_workflow.py`)
  and `TestDispatchSharedTail` (`tests/unit/test_runner_pid_callback.py`).

## Conventions

- Mechanism tests assert CLI behavior, not internal state.
- Build the binary first: `mise run build` — `test:mechanism:bats` and
  `test:e2e` depend on it.
- Never hardcode a binary path. `helpers/e2e-helpers.bash` resolves it,
  preferring `dist/openspec-extended-onedir/openspec-extended-onedir` over
  `dist/openspec-extended` for the ~2x faster cold start, and falls back to
  the single-file bundle when only that is built.

## See Also

- Root `AGENTS.md` — E2E Test Strategy
- `tests/AGENTS.md` — Marker semantics, `E2E_CONFIRM` gating
- `tests/fixtures/AGENTS.md` — the `add-hello-script` fixture