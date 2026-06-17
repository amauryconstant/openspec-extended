# Test Lib (Python)

Shared Python test utilities for the parent `tests/` directory.

## Files

| File | Purpose |
|------|---------|
| `test_osx.py` | Helpers for exercising `osx` subcommand domains (JSON parsing, temp change dirs) |

## Conventions

- Importable from any pytest module under `tests/`; add it to `conftest.py` if widely needed.
- Functions return data structures, not exit codes — let tests assert on the values.
- Keep utilities I/O-only; no test logic (asserts, markers) lives here.

## See Also

- `tests/AGENTS.md` — Test layout
- `source/lib/AGENTS.md` — The `osx` subcommand contract being tested
