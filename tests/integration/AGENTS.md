---
paths:
  - "tests/integration/**"
---

# Integration Tests

Component-level tests under `@pytest.mark.integration`. May touch the
filesystem and shell out, but do not invoke the AI.

## Conventions

- For OpenSpec change data, prefer a fixture from `tests/fixtures/changes/`
  over inlining artifact text in the test. Most integration tests build
  their throwaway change under `tmp_path` instead — do not read from
  `tests/fixtures/` at test time unless the test is asserting on fixture
  content.
- May shell out via `subprocess` to the source `cli.py` (not the built
  binary) — `sys.executable -m source …`.
- Mark every test with `@pytest.mark.integration`.
- Add `@pytest.mark.upstream` to any test that needs an installed upstream
  `openspec` CLI; `mise run test:integration` filters those out by default.
- `test_install_flow.py` holds the session-scoped installed-tree fixture.
  Reuse it rather than re-running `install` in a new fixture.

## See Also

- `tests/AGENTS.md` — Marker semantics
- `tests/unit/AGENTS.md` — Narrower scope
- `tests/fixtures/AGENTS.md` — Fixture layout and which suites consume it