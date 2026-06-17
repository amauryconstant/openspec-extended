# E2E Test Helpers (bats)

Bats helpers specific to the e2e suite.

## Files

| File | Purpose |
|------|---------|
| `e2e-helpers.bash` | Binary path resolution, isolated HOME setup, change-dir scaffolding |

## Conventions

- Source via `load helpers/e2e-helpers.bash`.
- All helpers assume the built binary is at `dist/openspec-extended` — call `mise run build` first.
- Helpers must clean up any state they create in `BATS_TEST_TMPDIR` and the isolated `HOME`.

## See Also

- `tests/AGENTS.md` — Test layout
- `tests/e2e/AGENTS.md` — E2E suite and binary requirement
- `tests/helpers/AGENTS.md` — Cross-suite shared helpers
