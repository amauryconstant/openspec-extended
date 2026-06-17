# Test Helpers (bats)

Shared bats helpers for the parent `tests/` directory.

## Files

| File | Purpose |
|------|---------|
| `test-helpers.bash` | Common assertion and setup functions |

## Conventions

- Source via `load helpers/test-helpers.bash` at the top of any bats file that needs them.
- Helpers must be idempotent and side-effect-free outside `BATS_TEST_TMPDIR`.
- Keep this directory for **shared** helpers only — bats files that are specific to one suite live next to the suite.

## See Also

- `tests/AGENTS.md` — Test layout
- `tests/e2e/helpers/AGENTS.md` — E2E-specific helpers
