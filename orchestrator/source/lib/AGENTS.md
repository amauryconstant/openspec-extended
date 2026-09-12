# `source/lib/` - Change Management Library

The `osx` library: 11 command domains that read/write change state. The orchestrator and tests import these functions directly in-process. The module is a pure library — no Typer, no CLI surface.

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

The Typer app that exposes the library as `openspec-extended osx <domain> <action> [args]` lives in `source/osx_cli.py`. It is mounted as a subcommand of the main `openspec-extended` CLI in `source/cli.py`.

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

## Command Domains (11)

| Domain | Library entry | CLI form |
|--------|---------------|----------|
| `baseline` | `baseline_record()`, `baseline_get()` | `openspec-extended osx baseline record\|get` |
| `ctx` | `ctx_get(change)` | `openspec-extended osx ctx get <change>` |
| `git` | `git_get(change)` | `openspec-extended osx git get <change>` |
| `phase` | `phase_current(change)`, `phase_next(change)`, `phase_advance(change)` | `openspec-extended osx phase current\|next\|advance <change>` |
| `state` | `state_get(change)`, `state_complete(change)`, `state_transition(change, target, reason, details)`, `state_clear_transition(change)`, `state_set_phase(change, phase, iteration)` | `openspec-extended osx state ...` |
| `iterations` | `iterations_get(change)`, `iterations_append(change, ...)` | `openspec-extended osx iterations ...` |
| `log` | `log_get(change)`, `log_append(change, ...)` | `openspec-extended osx log ...` |
| `complete` | `complete_check(change)`, `complete_get(change)`, `complete_set(change, status, blocker_reason)` | `openspec-extended osx complete ...` |
| `validate` | `validate_json(target)`, `validate_skills(project_root=None)`, `validate_commands(project_root=None)`, `validate_change_dir(target)` (consults core's `isPlanningComplete` and falls back to a local file-existence check), `validate_archive(target)`, `validate_iterations(target)`, `validate_completion(target)`, `validate_change(change_id, *, store=None, strict=False)` (v1.8.0+ envelope), `validate_spec(spec_id, *, store=None, strict=False)`, `validate_all(*, store=None, strict=False, concurrency=None)`, `validate_changes_only(*, store=None, strict=False)`, `validate_specs_only(*, store=None, strict=False)`, `validate_archived(change_id=None, *, store=None, strict=False)` (v1.9.0+ scope) | `openspec-extended osx validate ...` |
| `instructions` | `fetch_instructions(operation, change_id, *, store=None)` (v1.7.0+ read-only mirror) | `openspec-extended osx instructions <operation> --change <change_id>` |
| `schema` | `schema_which`, `schema_validate`, `schema_fork`, `schema_init`, `schema_list`, `schema_fork_diff(source, target, *, force=False, project_root=None)` (v1.9.0+ YAML fidelity check) | `openspec-extended osx schema ...` |

## Constants (top of `osx.py`)

| Constant | Value |
|----------|-------|
| `PHASES` | `["PHASE0" ... "PHASE6"]` |
| `VALID_TRANSITION_REASONS` | `implementation_incorrect`, `artifacts_modified`, `retry_requested` |
| `REQUIRED_SKILLS` | 5 `osx-*` skills required for changes (default install). Excludes `osx-changelog` and `osx-maintain-docs` (slash commands with self-contained bodies, not skills) and `osx-workflow` (gated by `install --with-autonomous` and only required when the autonomous workflow is enabled). See `osx-concepts` §2.5 for the full taxonomy. |
| `REQUIRED_CORE_SKILLS` | All 12 `osc-*` core skills from upstream OpenSpec (current v1.13.0; floor v1.13.0): propose, explore, new-change, continue-change, apply-change, update-change, ff-change, verify-change, sync-specs, archive-change, bulk-archive-change, onboard. Bumped from 4 → 12 to track the full custom-profile set; see `source/lib/osx.py`. |
| `MIN_OPENSPEC_VERSION` | `(1, 13, 0)` — orchestrator refuses to start with older cores. The floor guarantees the v1.13.0 contract surface (`status --all`, `show --diff`, `validate --archived`, `init --language`, `isPlanningComplete`, `retire_capabilities`, `validate --report findings`, `missingPrerequisites`, `list --specs`, fenced-code preservation, retire_capabilities relaxations, etc.) is available. The `OPENSPEC_EXTENDED_NO_PLANNING_CORE=1` env var is the CI escape hatch that bypasses the core planning-status call in `validate_change_dir`; without it, falls back to a local file-existence check. Per-contract operational notes live in [`.opencode/rules/openspec-contract.md`](../../.opencode/rules/openspec-contract.md). | |
| `AUTONOMOUS_RESOURCE_NAMES` | 12 names (4 agents + 7 phase commands + `osx-workflow` skill) gated by `install --with-autonomous`. Mirror in `deploy_type` (`source/cli.py:236`). |
| `OSXError` | Exception class raised by library functions |

### Environment-variable propagation

`validate_all` (`source/lib/osx.py`) honours the `OPENSPEC_CONCURRENCY` env
var as a fallback for its `concurrency` arg. Resolution precedence:

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

## Platform / adapter helpers (registry-driven since Phase 1D)

The platform-aware path helpers used to embed hardcoded ``"opencode"`` /
``"claude"`` literals. Phase 1D rewrote them to read from
``source.tools.REGISTRY`` (the adapter registry landed in Phase 1A).
They are byte-identical for the two shipped adapters because the
registry reproduces the legacy constants exactly.

| Helper | Registry field(s) consumed | Pre-1D literal |
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
`detect_platform` defaults to the first registered tool id — pre-1D
behavior was a literal `return "opencode"`.

## See Also

- Root `AGENTS.md` — Code Style, Versioning
- `orchestrator/source/AGENTS.md` — Module roles
- `orchestrator/source/orchestrator/AGENTS.md` — Consumer of `osx` state
