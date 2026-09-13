---
paths:
  - "tests/unit/**"
---

# Unit Tests

Fast, isolated tests under `@pytest.mark.unit`. Mixed pytest and bats.

## Conventions

- Tests live one-per-concern in this directory.
- No filesystem side effects outside `tmp_path` / bats `BATS_TEST_TMPDIR`.
- No subprocess calls to the built binary — exercise Python modules directly.
- Mark every test with `@pytest.mark.unit`; the marker is enforced by the default `pytest` run config.

## See Also

- `tests/AGENTS.md` — Marker semantics, conftest gating
- `tests/integration/AGENTS.md` — Broader scope tests
