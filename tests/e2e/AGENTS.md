---
paths:
  - "tests/e2e/**"
---

# End-to-End Tests

Tests run against the **built binary** at `dist/openspec-extended`. PyInstaller-freeze behavior cannot be reproduced from the source tree, so the binary is required.

## Files

| File | Type | Runs by default? | Requires `E2E_CONFIRM=1`? |
|------|------|------------------|---------------------------|
| `test_mechanism.py` | pytest, `@pytest.mark.mechanism` | yes | no |
| `mechanism.bats` | bats | yes | no |
| `full-workflow.bats` | bats (audit-clean fixture) | no | yes |
| `self-heal-workflow.bats` | bats (audit-dirty fixture; auto-fix regression sentinel) | no | yes |
| `helpers/e2e-helpers.bash` | shared bats helpers | n/a | n/a |

## Coverage

- `mechanism.bats` and `test_mechanism.py` cover the same CLI surface (commands, flags, exit codes) — pytest via subprocess, bats against the built binary. `test_mechanism.py` also pins the PHASE0 self-healing contract (auto-fixable vs halt-and-surface routes, slash-command name resolution, pre-check failure mode) via the `TestSlashCommandNameResolution`, `TestPhase0AutoFixVsHaltContract`, and `TestAutoFixAgentDispatchContract` classes.
- `full-workflow.bats` exercises the entire 7-phase orchestrator with AI calls on the audit-clean `add-hello-script` fixture. Slow, network-dependent, only run on confirmation.
- `self-heal-workflow.bats` exercises **PHASE0 only** (via `--to-phase=PHASE0`) on the audit-dirty `add-self-heal-script` fixture. Ships with deliberate PHASE0 findings on existing artifacts so the engine's auto-fix dispatch must reconcile them. ~3-5 min runtime vs ~20 min for the full 7-phase suite. The direct regression sentinel for the `library-state-status` bug is `phase0: no halt-for-routed-commands for autofixable route` — fails loudly with a clear message if the engine ever reverts to halting on `/osc-update-change`. The `to-phase: PHASE1 was not entered` test confirms the `--to-phase` short-circuit is itself honored (no IMPLEMENTATION iterations, completion banner present).

## Conventions

- Mechanism tests assert CLI behavior, not internal state.
- Build the binary first: `mise run build` — `test:mechanism:bats` and `test:e2e` mise tasks call `build` automatically.
- Never use the binary path as a constant; resolve it from `dist/openspec-extended` at test start.

## See Also

- Root `AGENTS.md` — E2E Test Strategy
- `tests/AGENTS.md` — Marker semantics, `E2E_CONFIRM` gating
