---
paths:
  - "orchestrator/source/lib/**"
---

# `source/lib/` - Change Management Library

The `osx` library: 12 command domains that read/write change state. The
orchestrator and tests import these functions directly in-process. The
module is a pure library — no Typer, no CLI surface.

## Package Layout

```
source/lib/
├── state_io.py    # Low-level atomic state.json read/write helpers
└── osx/           # The osx library (a package, not a single module)
    ├── __init__.py  # Domain functions + OSXError + VALID_TRANSITION_REASONS + MIN_OPENSPEC_VERSION
    └── sides/       # Side-tagged resource constants
        ├── orchestrator.py  # PHASES, PHASE_NAMES, PHASE_COMMANDS, AUTONOMOUS_RESOURCE_NAMES
        ├── skills.py        # REQUIRED_SKILLS
        └── core.py          # REQUIRED_CORE_SKILLS
```

`sides/` exists so each resource constant belongs to exactly one side of the
resource split. Everything is re-exported from `source.lib.osx`, so
`from source.lib.osx import REQUIRED_SKILLS` keeps working — import from
`source.lib.osx`, not from `sides/`, in new call sites.

## Two Surfaces

### Library API (in-process, recommended)

Each domain exposes a public Python function (e.g. `state_get(change)`, `phase_advance(change)`, `baseline_record()`) that:

- Returns a `dict` on success
- Raises `OSXError(code, message, **context)` on failure

The orchestrator calls these directly to avoid the subprocess + JSON-parsing cost.

```python
from source.lib import osx

result = osx.state_get("my-change")  # {"phase": "PHASE1", ...}
osx.state_complete("my-change")      # sets phase_complete=True on state.json
osx.iterations_append("my-change", iteration=1, phase="PHASE1", ...)
```

### CLI surface (`source/osx_cli.py`)

The Typer app that exposes the library as `openspec-extended osx <domain> <action> [args]` lives in `source/osx_cli.py`. It is mounted as a subcommand of the main `openspec-extended` CLI in `source/cli.py`. The 12 domains are `baseline`, `ctx`, `git`, `phase`, `state`, `iterations`, `log`, `complete`, `validate`, `instructions`, `store`, `schema`.

```bash
openspec-extended osx state get my-change
openspec-extended osx phase advance my-change
openspec-extended osx validate change-dir my-change
```

Keep the library and the CLI module separate so the library can be imported in-process (orchestrator, tests) without pulling in Typer.

## Contract

### Library
- **Returns**: dict on success
- **Errors**: raises `OSXError(code, message, **context)` — caller catches and handles
- **No side effects** beyond the requested action; idempotent where possible

### CLI (`source/osx_cli.py`)
- **Output**: JSON to stdout
- **Errors**: stderr JSON `{"error": code, "message": msg, ...}`, exit code 1

## Constants

Resource-name constants live in `source/lib/osx/sides/`; the rest are at the
top of `source/lib/osx/__init__.py`.

| Constant | Location | Value |
|----------|----------|-------|
| `PHASES` | `sides/orchestrator.py` | `["PHASE0" ... "PHASE6"]` |
| `PHASE_NAMES` | `sides/orchestrator.py` | Phase display names (e.g. `PHASE0` → `ARTIFACT REVIEW`) |
| `PHASE_COMMANDS` | `sides/orchestrator.py` | `PHASE0..PHASE6` → `osx-phase0..osx-phase6` |
| `VALID_TRANSITION_REASONS` | `osx/__init__.py` | `implementation_incorrect`, `artifacts_modified`, `retry_requested` |
| `REQUIRED_SKILLS` | `sides/skills.py` | 3 `osx-*` skills required for changes (default install): `osx-commit`, `osx-review-artifacts`, `osx-verify-tests`. Excludes `osx-changelog` and `osx-maintain-docs` (slash commands with self-contained bodies, not skills) and `osx-workflow` (gated by `install --with-autonomous` and only required when the autonomous workflow is enabled). See `osx-concepts` §2.5 for the full taxonomy. |
| `REQUIRED_CORE_SKILLS` | `sides/core.py` | All 12 `osc-*` core skills from upstream OpenSpec: propose, explore, new-change, continue-change, apply-change, update-change, ff-change, verify-change, sync-specs, archive-change, bulk-archive-change, onboard. Mirrors `[resources.skills.osc-*]`; never declared in a source manifest. |
| `AUTONOMOUS_RESOURCE_NAMES` | `sides/orchestrator.py` | 13 names (5 agents + 7 phase commands + `osx-workflow` skill) gated by `install --with-autonomous`. Aliased to `ORCHESTRATION_RESOURCE_NAMES`. Mirrored in `deploy_type` (`source/cli.py`). |
| `MIN_OPENSPEC_VERSION` | `osx/__init__.py` | `(1, 13, 0)` — orchestrator refuses to start with older cores. The vendored core under `orchestrator/core/` is currently **v1.14.3**; the floor is deliberately lower, to pin the contract surface rather than the vendored version. `OPENSPEC_EXTENDED_NO_PLANNING_CORE=1` is the CI escape hatch that bypasses the core planning-status call in `validate_change_dir`. Per-contract operational notes live in [`.agents/rules/openspec-contract.md`](../../../.agents/rules/openspec-contract.md). |
| `OSXError` | `osx/__init__.py` | Exception class raised by library functions |

### Environment-variable propagation

`validate_all` (`source/lib/osx/__init__.py`) honours the `OPENSPEC_CONCURRENCY`
env var as a fallback for its `concurrency` arg. Resolution precedence:

1. Explicit `concurrency` kwarg
2. `OPENSPEC_CONCURRENCY` env var (must parse as an int and be > 0)
3. Default `6` (matches upstream `openspec validate --all` default)

Invalid env values (non-int, ≤ 0, empty) fall back to `6` silently. The same
fallback applies via the top-level `openspec-extended validate --all`
passthrough and the `osx validate all` subcommand — see
`source/cli.py:validate_cmd` and `source/osx_cli.py:validate_cmd`.

The helper `_resolve_concurrency(explicit)` centralises the resolution logic
so each callsite reads identically.

`OPENSPEC_LANGUAGE` is read by `openspec-extended init` and
`openspec-extended install --with-core` (CLI layer in `source/cli.py` — not
the `osx` library). Resolution helper: `_resolve_language(arg)` next to
`run_openspec`. Same precedence as `OPENSPEC_CONCURRENCY`: explicit
`--language` flag > env var > unset; empty string is treated as unset.

## Conventions

- Library functions return dicts and raise `OSXError`. The Typer wrappers in `source/osx_cli.py` catch `OSXError` and call `osx_error` to print + exit.
- Low-level utilities (`_find_change_dir`, `_read_json`, `_read_json_array`, `_read_stdin`) raise `OSXError`. There are no CLI-exit variants in the library.
- Domain commands read/write state under `.openspec/` (created on demand).
- Never call AI processes directly — `osx` is a state/IO tool. AI invocation is the orchestrator's job.

## Platform / adapter helpers (registry-driven)

The platform-aware path helpers read from ``source.tools.REGISTRY`` rather
than embedding `"opencode"` / `"claude"` literals. The two shipped adapters
reproduce the legacy constants exactly, so behaviour is unchanged.

| Helper | Registry field(s) consumed | Pre-registry literal |
|---|---|---|
| `detect_platform(project_root)` | `REGISTRY[*].detect_paths` | `.opencode`, `.claude` |
| `skills_dir(project_root)` | `REGISTRY[platform].skills_dir` | `.opencode`, `.claude` |
| `commands_dir(project_root)` | `REGISTRY[platform].skills_dir`, `commands_dir` | `.opencode/commands`, `.claude/commands/osx` |
| `_load_manifest(project_root)` | `REGISTRY[platform].skills_dir` | `.opencode`, `.claude` |
| `_command_resolved_for_phase(root, platform, cmd_name)` | `commands_style`, `skills_dir` | dual-emit check hardcoded to `.claude` |
| `validate_commands(project_root)` (agent check) | `has_agents_dir`, `skills_dir` | `if platform == "opencode"` |

`detect_platform` walks `REGISTRY` in registration order; the first
adapter whose `detect_paths` include an existing directory at
`project_root` wins. Opencode wins ties because it's registered first
(locked by `tests/unit/test_tool_registry.py`). With no markers present
`detect_platform` defaults to the first registered tool id.

## Adding a new `osx` library domain

1. Add the public function(s) in `source/lib/osx/__init__.py`. Pure-Python: returns `dict`, raises `OSXError`.
2. Add the Typer wrapper in `source/osx_cli.py` under the matching sub-app. Catch `OSXError` and call `osx_error` for the JSON-shaped error.
3. Mount the sub-app under the main `osx` Typer app if it's a new top-level domain.
4. Add the domain to the module docstring's `## Command Domains` table at the top of `source/lib/osx/__init__.py`.
5. Add a unit test in `tests/unit/test_<domain>.py` and an integration test if it touches state I/O.

## See Also

- Root `AGENTS.md` — Code Style, Versioning
- `orchestrator/source/AGENTS.md` — Module roles
- `orchestrator/source/orchestrator/AGENTS.md` — Consumer of `osx` state
