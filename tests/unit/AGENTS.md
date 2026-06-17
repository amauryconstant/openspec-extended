# Unit Tests

Fast, isolated tests under `@pytest.mark.unit`. Mixed pytest and bats.

## Files

| File | Covers |
|------|--------|
| `test_openspec_extended.py` | Top-level CLI: install, update, orchestrate entry points |
| `test_osx_orchestrate.py` | `osx` subcommand domains, JSON contract |
| `test_schema_validation.py` | Manifest and resource schema validation |
| `install.bats` | `install.sh` (hermetic via local HTTP server) |

## Conventions

- No filesystem side effects outside `tmp_path` / bats `BATS_TEST_TMPDIR`.
- No subprocess calls to the built binary — exercise Python modules directly.
- Mark every test with `@pytest.mark.unit`; markers are enforced by the default `pytest` run config.

## See Also

- `tests/AGENTS.md` — Marker semantics, conftest gating
- `tests/integration/AGENTS.md` — Broader scope tests
