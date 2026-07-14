# Unit Tests

Fast, isolated tests under `@pytest.mark.unit`. Mixed pytest and bats.

## Files

| File | Covers |
|------|--------|
| `test_architecture.py` | CLI/library split invariants: `lib/osx.py` has no Typer surface, `osx_cli.py` owns the Typer app, `cli.py` mounts the `osx` subcommand |
| `test_cli_passthrough.py` | Top-level passthrough commands (`status`, `templates`, `schemas`, `validate`, etc.) forwarded to upstream `openspec` |
| `test_openspec_extended.py` | Top-level CLI: install, update, orchestrate entry points |
| `test_osx_orchestrate.py` | `osx` subcommand domains, JSON contract |
| `test_path_resolution.py` | `resolve_change_paths`, `_find_change_dir`, `_run_openspec_json` (v1.5.0 store behavior) |
| `test_platform_detection.py` | `detect_platform` / `skills_dir` / `commands_dir` (opencode vs claude layout) and platform-aware `validate_skills` / `validate_commands` |
| `test_runner_abstraction.py` | `RunResult`, `RunRequest`, runner dispatch, PID propagation |
| `test_schema_resolution.py` | `resolve_schema()` 4-level precedence chain |
| `test_schema_subcommands.py` | Subprocess wrappers for `openspec schema *` |
| `test_schema_validation.py` | Manifest and resource schema validation |
| `test_store_domain.py` | `store_list`, `store_doctor`, `store_register`, `store_unregister` |
| `test_validate_subcommands.py` | `osx validate` subcommands via Typer CliRunner |
| `test_validation_translator.py` | `validate_*` library functions and `_translate_validate_payload` |
| `install.bats` | `install.sh` (hermetic via local HTTP server) |

## Conventions

- No filesystem side effects outside `tmp_path` / bats `BATS_TEST_TMPDIR`.
- No subprocess calls to the built binary — exercise Python modules directly.
- Mark every test with `@pytest.mark.unit`; markers are enforced by the default `pytest` run config.

## See Also

- `tests/AGENTS.md` — Marker semantics, conftest gating
- `tests/integration/AGENTS.md` — Broader scope tests
