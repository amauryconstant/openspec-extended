---
paths:
  - "tests/**"
---

# Tests

Dual pytest + bats suite. Run commands live in `.mise/config.toml`:
`mise run test` (the default gate) and `mise run test:e2e`
(sets `E2E_CONFIRM=1`).

## Markers

Registered in `pyproject.toml` under `[tool.pytest.ini_options] markers`.

| Marker | Purpose | Default run? |
|--------|---------|--------------|
| `unit` | Fast, isolated | yes (`test:unit`) |
| `integration` | Component interactions, may touch filesystem | yes (`test:integration`) |
| `mechanism` | CLI surface checks, no AI calls | yes (`test:mechanism`) |
| `contract` | Envelope shapes against a live `openspec` CLI | no (`pytest -m contract`) |
| `upstream` | Needs an installed upstream `openspec` CLI | no — filtered out of `test:integration` |

`e2e` is registered but **no pytest test carries it**. End-to-end is a
bats-only surface gated by `E2E_CONFIRM`; see `tests/e2e/AGENTS.md`.

## Layout

```
tests/
├── conftest.py             # Pytest collection hook (see Gating Behavior)
├── contract/               # @pytest.mark.contract (live openspec envelopes)
├── unit/                   # @pytest.mark.unit + install.bats, test_changelog_gate.bats
├── integration/            # @pytest.mark.integration
├── e2e/                    # @pytest.mark.mechanism + mechanism.bats,
│                           #   store-and-config-passthrough.bats, full-workflow.bats
├── fixtures/               # Static test data (OpenSpec changes, install fixtures)
├── helpers/                # Shared bats helpers for tests/unit (test-helpers.bash)
├── lib/                    # @pytest.mark.unit module for source.lib.osx + osx_cli
└── e2e/helpers/            # E2E-specific bats helpers (e2e-helpers.bash)
```

## Gating Behavior

The only live `E2E_CONFIRM` gate is
`tests/e2e/helpers/e2e-helpers.bash::require_e2e_confirm`, called from
`full-workflow.bats`'s `setup_file()`. `tests/conftest.py`'s
`pytest_collection_modifyitems` skips `e2e`-marked tests unless
`E2E_CONFIRM=1`, but no test uses that marker, so the hook is currently a
no-op. `mechanism` tests are collected and run either way.

`tests/contract/` skips itself when `openspec` is not on `PATH`.

## Conventions

- One pytest module per concern under each marker directory. The exception is
  `tests/lib/`, which holds the `source.lib.osx` + `osx_cli` unit module —
  it is a test module, not a shared helper; nothing imports it.
- bats files load helpers by relative path: `load '../helpers/test-helpers'`
  from `tests/unit/`, `load 'helpers/e2e-helpers'` from `tests/e2e/`.
- Fixtures are read-only — never mutate files in `tests/fixtures/`.
- Mechanism tests are the source of truth for CLI surface; full-workflow bats
  is the source of truth for end-to-end AI behavior.
- Subprocess is allowed in every scope. Prefer in-process calls (`from
  source.lib import osx`, Typer's `CliRunner`); shell out via
  `python -m source` only when the deploy path or the `__main__` entry is
  what you are testing.

## Adding a new test

- Pick the marker that matches the test scope: `unit` for pure logic,
  `integration` for filesystem/subprocess, `mechanism` for CLI surface,
  `contract` for live-upstream envelope checks.
- Place the file under `tests/<marker>/` and mark with `@pytest.mark.<marker>`.
- If you are asserting on a deployed tree, reuse the session-scoped fixture
  in `tests/integration/test_install_flow.py` instead of building your own.
- For CLI surface, prefer Typer's `CliRunner` over `subprocess.run`.
- See the per-marker AGENTS.md (`tests/unit/AGENTS.md`,
  `tests/integration/AGENTS.md`, `tests/e2e/AGENTS.md`) for the conventions
  specific to that scope.

## See Also

- Root `AGENTS.md` — Testing commands, E2E Test Strategy
- `tests/unit/AGENTS.md`, `tests/integration/AGENTS.md`, `tests/e2e/AGENTS.md` — per-marker scope
- `tests/fixtures/AGENTS.md` — fixture layout