# Source - Python CLI

Python source for the `openspec-extended` binary.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | `__version__` only |
| `__main__.py` | Entry: `python -m source` |
| `cli.py` | Typer CLI (install/update/orchestrate + mounts `osx` subcommand) |
| `lib/osx.py` | Change-management library (10 domains). Pure functions, no CLI. |
| `osx_cli.py` | Typer app for the `openspec-extended osx` subcommand |
| `orchestrator/engine.py` | 7-phase autonomous workflow engine |

## Module Roles

- **`cli.py`** — User-facing CLI. Imports from `lib/osx.py`, `osx_cli.py`, and `orchestrator/engine.py`.
- **`lib/osx.py`** — Pure library. Exposes functions (e.g. `state_get`, `phase_advance`) that return dicts and raise `OSXError`. No CLI surface — importable without Typer.
- **`osx_cli.py`** — Typer wrappers around the library functions. Mounted as the `osx` subcommand of the main CLI in `cli.py`. This is what `openspec-extended osx …` runs.
- **`orchestrator/engine.py`** — Drives the PHASE0→PHASE6 state machine by spawning AI processes per phase. Calls `osx` library functions in-process.

## Conventions

- `__version__` in `source/__init__.py` is the **single source of truth** for the tool version. See root AGENTS.md "Versioning" section.
- The `osx` library is the in-process API. Callers (the orchestrator, tests) should `from source.lib import osx; osx.state_get(...)`. External callers use the binary: `openspec-extended osx <domain> <action> [args]`.

## See Also

- Root `AGENTS.md` — Code Style, Python Requirements, Versioning, Testing
- `source/lib/AGENTS.md` — `osx` library domains
- `source/orchestrator/AGENTS.md` — 7-phase workflow
