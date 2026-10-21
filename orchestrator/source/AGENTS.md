---
paths:
  - "orchestrator/source/**"
---

# `orchestrator/source/` - Python CLI

Python source for the `openspec-extended` binary. Lives under `orchestrator/source/` per Phase 4 (the binary lives at the project root; the orchestrator side owns the CLI/module path; the skills side owns nothing under `source/`).

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | `__version__` only |
| `__main__.py` | Entry: `python -m source` (still works from the new path) |
| `cli.py` | Typer CLI — top-level user commands (`install`, `update`, `orchestrate`, `init`, `validate`, `list`, `show`, `status`, `view`, `archive`, `context`, `doctor`, `schema`, `schemas`, `templates`, `instructions`, `store`, `feedback`, `completion`, `restore-core`, …) plus the resource deploy/purge machinery. Mounts the `osx` sub-app. |
| `osx_cli.py` | Typer app for the `openspec-extended osx` subcommand (12 domains) |
| `lib/osx/` | Change-management library. `__init__.py` holds the domain functions; `sides/` holds the side-tagged resource constants. |
| `lib/state_io.py` | Low-level state.json read/write helpers used by `lib/osx/` |
| `lib/osx/sides/` | Per-side resource constants: `orchestrator.py`, `skills.py`, `core.py` |
| `tools.py` | Per-tool adapter registry (`ToolAdapter` + `REGISTRY`) |
| `orchestrator/engine.py` | 7-phase autonomous workflow engine |
| `orchestrator/runner.py` | Per-tool CLI runner dispatch (OpenCode, Claude, generic print) |

## Module Roles

- **`cli.py`** — User-facing CLI. Imports from `lib/osx/`, `osx_cli.py`, `orchestrator/engine.py`, and `tools.py`.
- **`lib/osx/`** — Pure library. Exposes functions (e.g. `state_get`, `phase_advance`) that return dicts and raise `OSXError`. No CLI surface — importable without Typer. Resource constants live in `lib/osx/sides/` and are re-exported from `source.lib.osx`.
- **`osx_cli.py`** — Typer wrappers around the library functions. Mounted as the `osx` subcommand of the main CLI in `cli.py`. This is what `openspec-extended osx …` runs.
- **`orchestrator/engine.py`** — Drives the PHASE0→PHASE6 state machine by spawning AI processes per phase. Calls `osx` library functions in-process.

## Conventions

- `__version__` in `orchestrator/source/__init__.py` is the **single source of truth** for the tool version. See root AGENTS.md "Versioning" section.
- The `osx` library is the in-process API. Callers (the orchestrator, tests) should `from source.lib import osx; osx.state_get(...)`. External callers use the binary: `openspec-extended osx <domain> <action> [args]`.
- The Python **module name** is still `source` (no rename). All `from source.X` imports resolve because the project is installed editable — `.venv/.../_editable_impl_openspec_extended.pth` points at `orchestrator/`, which puts it on `sys.path`. PyInstaller's `pathex` in `openspec.spec` covers the frozen build.

`source.tools` is the single source of truth for everything that varies
between AI assistants (skills dir, command layout, slash prefix, runner
binary, agent-field transforms). Adding a new tool = one entry in
`REGISTRY`. The CLI / runner / engine / library layers read from
the registry — no per-tool edits there.

## Adding a new tool adapter

1. Add `REGISTRY[<tool_id>] = ToolAdapter(...)` in `source/tools.py`.
2. Pick a `commands_style` that matches the target's filesystem layout; add to the set of values `purge_managed_resources` recognises.
3. If the new `runner_kind` is not `opencode_run` or `claude_print`, add a branch in `source/orchestrator/runner.py:_runner_for`.
4. Add the tool id to `REGISTRY` first so `detect_platform` picks it up before existing tools.
5. Add a regression test in `tests/unit/test_runner_abstraction.py::TestDetectRunnerWalksRegistry`.
6. Populate the five Phase 1 surface fields on every adapter entry: `ask_tool` (non-empty), `install_hint` (non-empty, names `openspec-extended install <tool_id>`), and leave `cross_ref_prefix`, `runner_args`, `frontmatter_extras` at their defaults unless the adapter actually needs them. Locked by `tests/unit/test_tool_registry.py::TestAdapterFieldDefaults`.
7. If the adapter's body cross-references diverge from the canonical `/` form (e.g. Codex's `$`, Kimi's `/skill:`), set `cross_ref_prefix` explicitly so the `/opsx:<cmd>` rewrite in `source/cli.py:_rewrite_skill_body_refs` kicks in.
8. If the adapter's CLI shape differs from the standard `<tool> --print --dangerously-skip-permissions "<prompt>"` (Cursor / Qwen Code / Kiro), declare `runner_args` so `GenericPrintRunner` (`source/orchestrator/runner.py`) inserts the right flags between the binary name and `--print`.

## Library vs CLI vs subprocess

| Caller | Use |
|--------|-----|
| Orchestrator (`source/orchestrator/engine.py`) | Library function from `source.lib.osx` |
| Tests under `tests/unit/` | Library function from `source.lib.osx`, or `python -m source` when the CLI wiring is under test |
| Tests under `tests/integration/` | `python -m source <cmd>` subprocess (no CLI surface), or library function |
| External shell users | `openspec-extended osx <domain> <action>` binary |
| `mise run verify`, CI scripts | `openspec-extended` binary |

Rationale: the library is the only fast path (no subprocess, no JSON parse). The CLI is for users. Integration tests exercise the deploy path so they shell out; unit tests exercise logic so they call the library, except where the `__main__` entry or Typer wiring is the subject.

## See Also

- Root `AGENTS.md` — Code Style, Python Requirements, Versioning, Testing
- `orchestrator/source/lib/AGENTS.md` — `osx` library domains
- `orchestrator/source/orchestrator/AGENTS.md` — 7-phase workflow
