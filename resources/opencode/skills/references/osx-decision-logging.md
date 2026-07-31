# Decision & Iterations Logging

Two parallel JSON logs live under `openspec/changes/<change>/`:

- `decision-log.json` — one entry per phase (or sub-decision). High-level reasoning.
- `iterations.json` — chronological record of every iteration. Mechanical history.

They have different schemas. Do not mix.

## `osx log append` — decision log

```bash
openspec-extended osx log append "$1" \
    --phase <PHASENAME> \
    --iteration N \
    --summary "What was decided" \
    --commit-hash "<hash or null>" \
    --next-steps "What comes next" \
    [--issues JSON] [--decisions JSON] [--errors JSON] [--extra JSON_OBJECT]
```

| Flag | Type | Notes |
|---|---|---|
| `--phase` | string | One of `ARTIFACT_REVIEW`, `IMPLEMENTATION`, `REVIEW`, `MAINTAIN_DOCS`, `SYNC`, `SELF_REFLECTION`, `ARCHIVE` |
| `--iteration` | int | Per-phase iteration count |
| `--summary` | string | One-line summary of the decision |
| `--commit-hash` | string | `null` if no commit this iteration |
| `--next-steps` | string | Where the workflow goes from here |
| `--issues`, `--decisions`, `--errors` | JSON array | Merged into the entry |
| `--extra` | JSON object | Merged as an object — see warning below |

## `osx iterations append` — iteration history

```bash
openspec-extended osx iterations append "$1" \
    --phase <PHASENAME> \
    --iteration N \
    --commit-hash "<hash or null>" \
    [--summary S] [--status S] [--notes N] \
    [--issues JSON] [--artifacts-modified JSON] [--decisions JSON] [--errors JSON] \
    [--extra JSON_OBJECT]
```

Same flags as `osx log append`, plus `--status` and `--notes`.

## `--extra` is an object, not a string

```bash
# Correct
--extra '{"tasks_completed":["1.1","1.2"],"commits_made":3}'

# Wrong — stringifies as a string, breaks downstream parsing
--extra 'tasks_completed: 1.1, 1.2'
```

Pass a flat JSON **object** like `'{"tasks_completed":["1.1","1.2"]}'`. The library merges it.

## Phase-specific extra keys

Each phase uses `--extra` to record phase-specific metadata. Common keys:

| Phase | Common `--extra` keys |
|---|---|
| PHASE0 | `routed_to`, `artifacts_audited`, `issues_found` |
| PHASE1 | `tasks_completed`, `tasks_remaining`, `commits_made`, `cli_status`, `cli_instructions` |
| PHASE2 | `verification_result`, `issues_found`, `verification_report_path`, `artifacts_modified` |
| PHASE3 | `docs_updated`, `changes_made` |
| PHASE4 | `delta_specs_found`, `sync_operations` |
| PHASE5 | `reflections_path`, `total_phases`, `total_iterations` |
| PHASE6 | `archive_path` |

## See also

- `references/shell-argument-safety.md` — backticks in `--summary`/`--next-steps` corrupt the log.
- `references/phase-protocol-common.md` — when to append vs when to mark complete.