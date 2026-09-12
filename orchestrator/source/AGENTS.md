# `orchestrator/source/` - Python CLI

Python source for the `openspec-extended` binary. Lives under `orchestrator/source/` per Phase 4 (the binary lives at the project root; the orchestrator side owns the CLI/module path; the skills side owns nothing under `source/`).

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | `__version__` only |
| `__main__.py` | Entry: `python -m source` (still works from the new path) |
| `cli.py` | Typer CLI (install/update/orchestrate + mounts `osx` subcommand) |
| `lib/osx.py` | Change-management library (11 domains). Pure functions, no CLI. |
| `osx_cli.py` | Typer app for the `openspec-extended osx` subcommand |
| `tools.py` | Per-tool adapter registry (`ToolAdapter` + `REGISTRY`) |
| `orchestrator/engine.py` | 7-phase autonomous workflow engine |

## Module Roles

- **`cli.py`** — User-facing CLI. Imports from `lib/osx.py`, `osx_cli.py`, and `orchestrator/engine.py`.
- **`lib/osx.py`** — Pure library. Exposes functions (e.g. `state_get`, `phase_advance`) that return dicts and raise `OSXError`. No CLI surface — importable without Typer.
- **`osx_cli.py`** — Typer wrappers around the library functions. Mounted as the `osx` subcommand of the main CLI in `cli.py`. This is what `openspec-extended osx …` runs.
- **`orchestrator/engine.py`** — Drives the PHASE0→PHASE6 state machine by spawning AI processes per phase. Calls `osx` library functions in-process.

## Conventions

- `__version__` in `orchestrator/source/__init__.py` is the **single source of truth** for the tool version. See root AGENTS.md "Versioning" section.
- The `osx` library is the in-process API. Callers (the orchestrator, tests) should `from source.lib import osx; osx.state_get(...)`. External callers use the binary: `openspec-extended osx <domain> <action> [args]`.
- The Python **module name** is still `source` (no rename). All `from source.X` imports continue to resolve because `orchestrator/` is added to `sys.path` (PyInstaller `pathex` in `openspec.spec`) and because the test harness uses `uv run pytest` from the project root.

`source.tools` is the single source of truth for everything that varies
between AI assistants (skills dir, command layout, slash prefix, runner
binary, agent-field transforms). Adding a new tool = one entry in
`REGISTRY`. The CLI / runner / engine / library layers read from
the registry — no per-tool edits there.

## See Also

- Root `AGENTS.md` — Code Style, Python Requirements, Versioning, Testing
- `orchestrator/source/lib/AGENTS.md` — `osx` library domains
- `orchestrator/source/orchestrator/AGENTS.md` — 7-phase workflow
