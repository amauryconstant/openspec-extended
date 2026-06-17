# Integration Tests

Component-level tests under `@pytest.mark.integration`. May touch the filesystem and shell out, but do not invoke the AI.

## Files

| File | Covers |
|------|--------|
| `test_change_lifecycle.py` | OpenSpec change directory creation, validation, archive flow |
| `test_completion_workflow.py` | Completion status, decision log, iteration history |
| `test_git_integration.py` | Git status, baseline tracking, commit/branch handling |
| `test_install_flow.py` | End-to-end install path against local fixtures |
| `test_orchestration_logging.py` | Orchestrator state persistence and log output |
| `test_phase_workflow.py` | PHASE0→PHASE6 transitions, retry budget, transition reasons |

## Conventions

- Use fixtures from `tests/fixtures/` for any OpenSpec change data.
- May shell out via `subprocess` to the source `cli.py` (not the built binary).
- Mark every test with `@pytest.mark.integration`.

## See Also

- `tests/AGENTS.md` — Marker semantics
- `tests/unit/AGENTS.md` — Narrower scope
- `tests/fixtures/AGENTS.md` — Available fixture data
