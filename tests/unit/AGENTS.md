---
paths:
  - "tests/unit/**"
---

# Unit Tests

Fast, isolated tests under `@pytest.mark.unit`. Mixed pytest and bats.

## Conventions

- One module per concern in this directory.
- No filesystem side effects outside `tmp_path` / bats `BATS_TEST_TMPDIR`.
- Exercise Python modules directly; do not invoke the built binary. A
  `python -m source` subprocess is acceptable when the `__main__` entry or
  the CLI wiring is the thing under test.
- Mark every test with `@pytest.mark.unit` — `mise run test:unit` selects on
  the marker, so an unmarked test never runs.
- `install.bats` and `test_changelog_gate.bats` cover `install.sh` and the
  release-time changelog gate. They read `tests/fixtures/install/` via
  `load '../helpers/test-helpers'`; `test_changelog_gate.bats` writes only
  inside its own tmpdir, never back into `tests/fixtures/`.
- `tests/lib/test_osx.py` is the one `@pytest.mark.unit` module living
  outside this directory. It covers `source.lib.osx` plus the `osx_cli`
  Typer surface. Keep it there or move it here — do not add a second one.

## See Also

- `tests/AGENTS.md` — Marker semantics, conftest gating
- `tests/integration/AGENTS.md` — Broader scope tests