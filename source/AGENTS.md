# Source - Python CLI

Python source for the `openspec-extended` binary.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | `__version__` only |
| `__main__.py` | Entry: `python -m source` |
| `cli.py` | Typer CLI (install/update/orchestrate) + `SCRIPT_VERSION` |
| `lib/osx.py` | Change-management library (10 domains) + Typer app |
| `orchestrator/engine.py` | 7-phase autonomous workflow engine |

## Module Roles

- **`cli.py`** — User-facing CLI. Imports from `lib/osx.py` and `orchestrator/engine.py`. Owns `SCRIPT_VERSION` (canonical version).
- **`lib/osx.py`** — Internal Python module. Exposes library functions (e.g. `state_get`, `phase_advance`) that return dicts and raise `OSXError`. Also exposes a Typer `app` invoked via `python -m source.lib.osx` for ad-hoc CLI use and for subprocess callers; the main `openspec-extended` CLI does **not** mount `osx` as a subcommand.
- **`orchestrator/engine.py`** — Drives the PHASE0→PHASE6 state machine by spawning AI processes per phase. Calls `osx` library functions in-process.

## Conventions

- `SCRIPT_VERSION` in `cli.py` is the **single source of truth** for the tool version. See root AGENTS.md "Versioning" section.
- The `osx` namespace is a library, not a public CLI subcommand. In-process callers (the orchestrator, tests) should `from source.lib import osx; osx.state_get(...)`. External CLI invocation is via `python -m source.lib.osx ...` and is reserved for debugging and ad-hoc use.

## See Also

- Root `AGENTS.md` — Code Style, Python Requirements, Versioning, Testing
- `source/lib/AGENTS.md` — `osx` library domains
- `source/orchestrator/AGENTS.md` — 7-phase workflow
