# `source/lib/` - Change Management Library

The `osx` library: 10 command domains that read/write change state. The orchestrator and tests import these functions directly in-process.

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

### Typer CLI (debugging / ad-hoc)

`osx.py` also registers a Typer `app` invoked via `python -m source.lib.osx <domain> <action> [args]`. This is the same library code wrapped to print JSON to stdout and exit non-zero on error. Use it for debugging, scripts, and tests that want to exercise the CLI.

```bash
python -m source.lib.osx state get my-change
python -m source.lib.osx phase advance my-change
python -m source.lib.osx validate change-dir my-change
```

The `openspec-extended` CLI does **not** mount `osx` as a subcommand. It is internal.

## Contract

### Library
- **Returns**: dict on success
- **Errors**: raises `OSXError(code, message, **context)` — caller catches and handles
- **No side effects** beyond the requested action; idempotent where possible

### CLI
- **Output**: JSON to stdout
- **Errors**: stderr JSON `{"error": code, "message": msg, ...}`, exit code 1

## Command Domains (10)

| Domain | Library entry | CLI form |
|--------|---------------|----------|
| `baseline` | `baseline_record()`, `baseline_get()` | `osx baseline record\|get` |
| `ctx` | `ctx_get(change)` | `osx ctx get <change>` |
| `git` | `git_get(change)` | `osx git get <change>` |
| `phase` | `phase_current(change)`, `phase_next(change)`, `phase_advance(change)` | `osx phase current\|next\|advance <change>` |
| `state` | `state_get(change)`, `state_complete(change)`, `state_transition(change, target, reason, details)`, `state_clear_transition(change)`, `state_set_phase(change, phase, iteration)` | `osx state ...` |
| `iterations` | `iterations_get(change)`, `iterations_append(change, ...)` | `osx iterations ...` |
| `log` | `log_get(change)`, `log_append(change, ...)` | `osx log ...` |
| `complete` | `complete_check(change)`, `complete_get(change)`, `complete_set(change, status, blocker_reason)` | `osx complete ...` |
| `validate` | `validate_json(target)`, `validate_skills()`, `validate_commands()`, `validate_change_dir(target)`, `validate_archive(target)`, `validate_iterations(target)`, `validate_completion(target)` | `osx validate ...` |
| `instructions` | `instructions(artifact, change, json_output)` | `osx instructions ...` |

## Constants (top of `osx.py`)

| Constant | Value |
|----------|-------|
| `PHASES` | `["PHASE0" ... "PHASE6"]` |
| `VALID_TRANSITION_REASONS` | `implementation_incorrect`, `artifacts_modified`, `retry_requested` |
| `REQUIRED_SKILLS` | 5 `osx-*` skills installed for changes |
| `REQUIRED_CORE_SKILLS` | 4 `osc-*` core skills (apply, verify, sync, archive) |
| `OSXError` | Exception class raised by library functions |

## Conventions

- Library functions return dicts and raise `OSXError`. The Typer wrappers catch `OSXError` and call `osx_error` to print + exit.
- Low-level utilities (`find_change_dir`, `read_json`, `read_json_array`, `osx_error`) keep their CLI behavior (print + exit). Library callers use the `_`-prefixed variants (`_find_change_dir`, `_read_json`, `_read_json_array`).
- Domain commands read/write state under `.openspec/` (created on demand).
- Never call AI processes directly — `osx` is a state/IO tool. AI invocation is the orchestrator's job.

## See Also

- Root `AGENTS.md` — Code Style, Versioning
- `source/AGENTS.md` — Module roles
- `source/orchestrator/AGENTS.md` — Consumer of `osx` state
