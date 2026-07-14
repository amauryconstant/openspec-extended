# Troubleshooting

Common failures you may hit while running `openspec-extended`, the underlying error code, and how to recover.

Errors come from `source/lib/osx.py:OSXError` (raised by library functions and converted to stderr JSON by `source/osx_cli.py:osx_error`) and from `source/orchestrator/engine.py` (printed to stderr by the orchestrator).

## State Issues

### `state.json` is stuck on an old phase

**Symptom**: Re-running `orchestrate` keeps resuming from the same phase even after you fixed the underlying problem.

**Cause**: `state.json` records the last completed phase. The orchestrator resumes from that phase (`source/orchestrator/engine.py:982-988`) rather than restarting from PHASE0.

**Fix**: Re-run with `--from-phase PHASE0` to force a restart from the beginning, or delete `openspec/changes/<id>/state.json` and let the orchestrator re-derive the phase from the artifacts.

### `phase_complete` never flips to true

**Symptom**: The orchestrator loops on a phase forever, never advancing.

**Cause**: The AI subprocess did not call `openspec-extended osx state complete <change>` before exiting. Without that, the orchestrator sees no completion signal.

**Fix**: Run the phase command manually:

```bash
openspec-extended osx phase <name>
```

to see what state currently looks like, then re-run:

```bash
openspec-extended osx state complete <change>
```

If the AI is failing to call this on its own, raise `--max-phase-iterations` to give it more retries, or inspect `decision-log.json` for the last reported blocker.

### `decision-log.json` is malformed or missing

**Symptom**: `validate completion` reports `decision-log.json not found`.

**Cause**: A previous orchestrator run was killed before it could flush the decision log. Common after `SIGKILL` (not `SIGINT`/`SIGTERM`).

**Fix**: The orchestrator writes the decision log on every iteration append. To recover:

```bash
rm openspec/changes/<id>/decision-log.json
openspec-extended orchestrate <id> --from-phase PHASE0
```

The first iteration of PHASE0 will recreate the file.

### `state.json` contains invalid JSON

**Symptom**: `OSXError("invalid_json", "Invalid JSON in state.json")`.

**Cause**: A partial write (process killed mid-write) or hand-edited corruption. `write_json` uses a temp-file-and-replace pattern (`source/lib/osx.py:259-266`) so this should be rare.

**Fix**: Inspect the file with `cat openspec/changes/<id>/state.json | jq`. If it really is corrupt, restore from git:

```bash
git checkout HEAD -- openspec/changes/<id>/state.json
```

If the change is uncommitted, the safest path is to remove the file and let the orchestrator rebuild it via `--from-phase PHASE0`.

## Git Issues

### `Aborted due to dirty git state`

**Symptom**: Pre-flight aborts with `Aborted due to dirty git state`.

**Cause**: `validate_git` (`source/orchestrator/engine.py:224-258`) detected unstaged or staged changes that were not committed before pre-flight.

**Fix**: Either commit/stash the changes, or pass `--force` to skip the prompt (only recommended for ephemeral test runs):

```bash
git add -A && git commit -m "WIP"
openspec-extended orchestrate <change>
```

Non-interactive shells (`CI`, `mise run`, scripts) auto-continue with a warning.

### `Not in a git repository`

**Symptom**: Pre-flight exits with `Not in a git repository`.

**Cause**: `openspec-extended orchestrate` requires a git repo for baseline tracking and baseline diff.

**Fix**: `git init` in the project root, or run the orchestrator from a parent directory that contains a git repo.

### Baseline not found

**Symptom**: `OSXError("baseline_not_found", ".openspec-baseline.json does not exist")`.

**Cause**: A subsequent run is reading baseline info without having recorded one. This usually means the orchestrator was invoked with `--from-phase` after a baseline was cleared, or after a manual archive.

**Fix**: Re-run with `--from-phase PHASE0` (or omit `--from-phase`) so `record_baseline` runs and writes `.openspec-baseline.json`.

## Missing CLI Tools

### `openspec-extended: command not found`

**Symptom**: Shell reports the binary is missing.

**Fix**: Re-run the installer:

```bash
curl -fsSL https://raw.githubusercontent.com/.../install.sh | bash
```

For local development use `mise run install` or activate the venv directly.

### `Required tool not found: openspec`

**Symptom**: Pre-flight aborts with `Required tool not found: openspec` (`engine.py:960-963`).

**Cause**: The orchestrator shells out to the upstream `openspec` CLI for schema validation. It must be on `PATH`.

**Fix**: Install upstream OpenSpec first (see [README](../README.md) install section), or prepend its location:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

### `Required tool not found: jq`

**Symptom**: Pre-flight aborts with `Required tool not found: jq`.

**Cause**: `jq` is required for the installer and some tests, but the orchestrator itself does not shell out to `jq`. This error usually appears during `install.sh` or `mise run verify`.

**Fix**: Install `jq` via your package manager (`apt install jq`, `brew install jq`, etc.).

### `Required skills validation failed` / `Required commands validation failed`

**Symptom**: Pre-flight aborts with `Run: openspec-extended install opencode`.

**Fix**: This is the auto-suggested fix — run it. The install command copies the missing `osx-*` skills and `osx-phase*.md` commands into the target platform's resource directory.

```bash
openspec-extended install opencode
```

If you only need Claude Code resources, substitute `claude`.

## Schema Resolution Failures

### `Schema: <name> (source: project-config)` is not what you expected

**Symptom**: Pre-flight logs a schema name that does not match your intent.

**Cause**: Resolution precedence (`source/lib/osx.py:1490-1547`) checks (in order) `--schema`, change-level `.openspec.yaml`, project `openspec/config.yaml`, then default `spec-driven`. The first match wins.

**Fix**: Use `--schema <name>` on the `orchestrate` command to force the value:

```bash
openspec-extended orchestrate <change> --schema workspace-planning
```

Or remove the offending layer (e.g., delete `openspec/config.yaml` if you want the change-level metadata to win).

### `defaultSchema` vs `schema` mismatch

**Symptom**: `openspec schema init --default` writes `defaultSchema:` to `config.yaml`, but `resolve_schema` reads `schema:`. They never match.

**Cause**: Upstream OpenSpec uses `defaultSchema` as the YAML key, but our resolver (matching earlier upstream versions) reads `schema`. Documented in `research/roadmap.md` Tier 4 — MEDIUM severity latent issue.

**Fix**: Edit `openspec/config.yaml` to use `schema:` instead of `defaultSchema:`, or wrap the file with our own template that aliases the keys. The cleanest workaround today is to hand-edit:

```yaml
schema: spec-driven
```

instead of relying on `openspec schema init --default`.

## Orchestrator Errors

### `Critical blocker detected` on a previously passing change

**Symptom**: `complete.json` reports `with_blocker: true` and the orchestrator exits 1.

**Cause**: A previous AI run wrote a blocker to `decision-log.json`. The orchestrator reads `complete.json` at PHASE6 (`engine.py:1028-1047`) and surfaces the blocker instead of archiving.

**Fix**: Inspect the blocker:

```bash
cat openspec/changes/<id>/decision-log.json | jq '.[] | select(.blocker)'
```

Resolve the underlying issue, then either remove `complete.json` (the orchestrator will recreate it on success) or run:

```bash
openspec-extended osx complete set <change> ok
```

to clear the blocker.

### Archive validation failed after PHASE6

**Symptom**: The orchestrator exits 1 with `Archive validation failed`.

**Cause**: `validate_archive` (`engine.py:308-312`) did not find exactly one archive directory matching `YYYY-MM-DD-<change>`.

**Fix**: This is rare and usually means PHASE6 ran but the archive step did not complete (e.g., permissions). Inspect:

```bash
ls openspec/changes/archive/
```

If the archive directory exists but has the wrong name, rename it. If it does not exist, re-run:

```bash
openspec-extended orchestrate <change> --from-phase PHASE6
```

## Installation Issues

### `install.sh: openspec-extended binary download failed`

**Symptom**: The bash installer exits with a curl/wget error.

**Fix**: Check your network connection and that `VERSION` (or `latest`) resolves to a published release. For local development, set `VERSION=main` to install from the latest CI artifact.

### `mise run verify` fails on a single rule

**Symptom**: `ruff` or `pytest` reports one failure.

**Fix**: Run the failing tool directly to see the full diff:

```bash
ruff check source/ tests/
pytest tests/unit tests/integration -v
```

Most ruff failures auto-fix with `ruff check --fix`.

## See Also

- [CLI comparison](./cli-comparison.md) — what each command does
- [Orchestrator state machine](./orchestrator-state-machine.md) — phase model and transitions
- `source/lib/osx.py` — full list of `OSXError` codes
- `source/orchestrator/engine.py` — orchestrator error reporting