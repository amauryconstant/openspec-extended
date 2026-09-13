---
paths:
  - "tests/integration/**"
---

# Integration Tests

Component-level tests under `@pytest.mark.integration`. May touch the filesystem and shell out, but do not invoke the AI.

## Conventions

- Use fixtures from `tests/fixtures/` for any OpenSpec change data.
- May shell out via `subprocess` to the source `cli.py` (not the built binary).
- Mark every test with `@pytest.mark.integration`.

## See Also

- `tests/AGENTS.md` — Marker semantics
- `tests/unit/AGENTS.md` — Narrower scope
- `tests/fixtures/AGENTS.md` — Available fixture data
