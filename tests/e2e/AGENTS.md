# End-to-End Tests

Tests run against the **built binary** at `dist/openspec-extended`. PyInstaller-freeze behavior cannot be reproduced from the source tree, so the binary is required.

## Files

| File | Type | Runs by default? | Requires `E2E_CONFIRM=1`? |
|------|------|------------------|---------------------------|
| `test_mechanism.py` | pytest, `@pytest.mark.mechanism` | yes | no |
| `mechanism.bats` | bats | yes | no |
| `full-workflow.bats` | bats | no | yes |
| `helpers/e2e-helpers.bash` | shared bats helpers | n/a | n/a |

## Coverage

- `mechanism.bats` and `test_mechanism.py` cover the same CLI surface (commands, flags, exit codes) — pytest via subprocess, bats against the built binary.
- `full-workflow.bats` exercises the entire 7-phase orchestrator with AI calls. Slow, network-dependent, only run on confirmation.

## Conventions

- Mechanism tests assert CLI behavior, not internal state.
- Build the binary first: `mise run build` — `test:mechanism:bats` and `test:e2e` mise tasks call `build` automatically.
- Never use the binary path as a constant; resolve it from `dist/openspec-extended` at test start.

## See Also

- Root `AGENTS.md` — E2E Test Strategy
- `tests/AGENTS.md` — Marker semantics, `E2E_CONFIRM` gating
- `tests/e2e/helpers/AGENTS.md` — Shared helpers
