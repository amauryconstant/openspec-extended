# Tests

Dual pytest + bats suite. See root `AGENTS.md` "Testing" section for run commands and the "E2E Test Strategy" subsection for the why.

## Markers

| Marker | Purpose | Default run? |
|--------|---------|--------------|
| `unit` | Fast, isolated | yes |
| `integration` | Component interactions, may touch filesystem | yes |
| `mechanism` | CLI surface checks, no AI calls | yes |
| `e2e` | Full workflow against the built binary | no (requires `E2E_CONFIRM=1`) |

## Layout

```
tests/
├── conftest.py             # Pytest config: E2E_CONFIRM=1 gating
├── unit/                   # @pytest.mark.unit + install.bats
├── integration/            # @pytest.mark.integration
├── e2e/                    # @pytest.mark.mechanism + e2e bats
├── fixtures/               # Static test data (OpenSpec changes, install fixtures)
├── helpers/                # Shared bats helpers (test-helpers.bash)
├── lib/                    # Shared Python test utilities (test_osx.py)
└── e2e/helpers/            # E2E-specific bats helpers
```

## Gating Behavior

`tests/conftest.py` skips tests marked `e2e` unless `E2E_CONFIRM=1` is set. Tests marked `mechanism` are always collected — `mechanism` tests run by default and live in both pytest (`tests/e2e/test_mechanism.py`) and bats (`tests/e2e/mechanism.bats`).

## Conventions

- One pytest module per concern under each marker directory.
- bats tests source shared helpers via `load helpers/test-helpers.bash`.
- Fixtures are read-only — never mutate files in `tests/fixtures/`.
- Mechanism tests are the source of truth for CLI surface; full-workflow bats is the source of truth for end-to-end AI behavior.

## See Also

- Root `AGENTS.md` — Testing commands, E2E Test Strategy
- `tests/unit/AGENTS.md`, `tests/integration/AGENTS.md`, `tests/e2e/AGENTS.md` — per-marker scope
- `tests/fixtures/AGENTS.md` — fixture layout
