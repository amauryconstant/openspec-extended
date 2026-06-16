# CLI Reference for AI Agents

Complete reference for the three CLI surfaces in OpenSpec-extended. All shapes verified against `@fission-ai/openspec@1.4.1`, `openspec-extended@0.19.x` source, and the deployed `osx` script.

> **Quick rule**: use **`openspec`** to query workflow state, **`openspec-extended`** to drive the lifecycle, and **`osx`** to mutate change state.

---

## Table of contents

- [A. `openspec` (upstream npm)](#a-openspec-upstream-npm)
  - [status](#openspec-status)
  - [instructions](#openspec-instructions)
  - [list](#openspec-list)
  - [validate](#openspec-validate)
  - [schemas](#openspec-schemas)
  - [templates](#openspec-templates)
  - [show](#openspec-show)
  - [other commands](#openspec-other-commands)
- [B. `openspec-extended` (this project)](#b-openspec-extended-this-project)
  - [install](#openspec-extended-install)
  - [update](#openspec-extended-update)
  - [orchestrate](#openspec-extended-orchestrate)
- [C. `osx` (change state tool)](#c-osx-change-state-tool)
  - [ctx](#ctx)
  - [state](#state)
  - [phase](#phase)
  - [iterations](#iterations)
  - [log](#log)
  - [complete](#complete)
  - [baseline](#baseline)
  - [git](#git)
  - [validate](#osx-validate)
  - [instructions](#osx-instructions)
- [Common error patterns](#common-error-patterns)
- [Environment variables](#environment-variables)

---

## A. `openspec` (upstream npm)

The `openspec` binary is installed via `npm install -g @fission-ai/openspec`. It implements the spec-driven workflow: query state, get instructions for creating artifacts, validate, list changes, etc.

```bash
openspec --version    # 1.4.1
openspec <subcommand> [options]
```

### `openspec status`

Artifact completion state for a change. **Most commonly used command for agents.**

**Usage**:
```bash
openspec status --change <name> --json
```

**JSON output** (v1.4.1, verified):
```json
{
  "changeName": "add-dark-mode",
  "schemaName": "spec-driven",
  "planningHome": {
    "kind": "repo",
    "root": "/abs/path",
    "changesDir": "/abs/path/openspec/changes",
    "defaultSchema": "spec-driven"
  },
  "changeRoot": "/abs/path/openspec/changes/add-dark-mode",
  "artifactPaths": {
    "proposal": {"outputPath": "proposal.md", "resolvedOutputPath": "…", "existingOutputPaths": []},
    "specs":    {"outputPath": "specs/**/*.md", "resolvedOutputPath": "…", "existingOutputPaths": []},
    "design":   {"outputPath": "design.md", "resolvedOutputPath": "…", "existingOutputPaths": []},
    "tasks":    {"outputPath": "tasks.md", "resolvedOutputPath": "…", "existingOutputPaths": []}
  },
  "isComplete": false,
  "applyRequires": ["tasks"],
  "nextSteps": ["Run openspec instructions proposal --change \"add-dark-mode\" --json before writing that artifact."],
  "actionContext": {
    "mode": "repo-local",
    "sourceOfTruth": "repo",
    "planningArtifacts": ["proposal", "design", "specs", "tasks"],
    "linkedContext": [],
    "allowedEditRoots": ["/abs/path"],
    "requiresAffectedAreaSelection": false,
    "constraints": ["Repo-local change artifacts and implementation edits are scoped to this project."]
  },
  "artifacts": [
    {"id": "proposal", "outputPath": "proposal.md", "status": "ready"},
    {"id": "design",   "outputPath": "design.md",   "status": "blocked", "missingDeps": ["proposal"]},
    {"id": "specs",    "outputPath": "specs/**/*.md", "status": "blocked", "missingDeps": ["proposal"]},
    {"id": "tasks",    "outputPath": "tasks.md",    "status": "blocked", "missingDeps": ["design", "specs"]}
  ]
}
```

**Per-artifact `status` values**: `ready` (deps met) · `blocked` (deps missing, see `missingDeps`) · `done` (file exists).

**Agent usage**:
```bash
# Before any artifact work
openspec status --change "add-dark-mode" --json

# If isComplete: ready to apply or archive
# If nextSteps non-empty: read them; they tell you the next artifact to write
```

---

### `openspec instructions`

Get enriched instructions for creating an artifact or applying tasks.

**Usage**:
```bash
# Instructions for next ready artifact in a change
openspec instructions --change <name> --json

# Instructions for a specific artifact
openspec instructions <artifact> --change <name> --json

# Apply-mode instructions (for implementation)
openspec instructions apply --change <name> --json
```

**JSON output** (v1.4.1, verified — `proposal` example):
```json
{
  "changeName": "add-dark-mode",
  "artifactId": "proposal",
  "schemaName": "spec-driven",
  "changeDir": "/abs/path/openspec/changes/add-dark-mode",
  "outputPath": "proposal.md",
  "resolvedOutputPath": "/abs/path/openspec/changes/add-dark-mode/proposal.md",
  "existingOutputPaths": [],
  "description": "Initial proposal document outlining the change",
  "instruction": "Create the proposal document that establishes WHY this change is needed…",
  "template": "## Why\n\n…\n## What Changes\n…\n## Capabilities\n…\n## Impact\n…",
  "dependencies": [],
  "unlocks": ["design", "specs"]
}
```

**Apply-mode output** (v1.4.1, verified):
```json
{
  "changeName": "add-dark-mode",
  "changeDir": "…",
  "schemaName": "spec-driven",
  "contextFiles": {},
  "progress": {"total": 0, "complete": 0, "remaining": 0},
  "tasks": [],
  "state": "blocked",
  "missingArtifacts": ["tasks"],
  "instruction": "Cannot apply this change yet. Missing artifacts: tasks. Use the openspec-continue-change skill to create the missing artifacts first."
}
```

**Critical**: The `instruction` and `template` strings are guidance for you, the agent. **Do not copy `<context>`, `<rules>`, or `<project_context>` blocks into artifact files.** Read them, internalize, write your own content.

---

### `openspec list`

List changes or specs.

**Usage**:
```bash
openspec list --json              # active changes
openspec list --specs --json      # specs
openspec list --sort name --json  # by name
```

**JSON output** (v1.4.1, verified — changes):
```json
{
  "changes": [
    {
      "name": "add-dark-mode",
      "completedTasks": 0,
      "totalTasks": 0,
      "lastModified": "2026-06-16T10:48:33.731Z",
      "status": "no-tasks"
    }
  ]
}
```

`status` values: `no-tasks`, `in-progress`, `done` (when all tasks checked).

**JSON output** (specs):
```json
{"specs": []}
```

When `specs` is empty the project has no `openspec/specs/` yet.

---

### `openspec validate`

Validate changes and specs. **Always run before archiving.**

**Usage**:
```bash
openspec validate <change-name> --json   # one change
openspec validate --all --json          # all changes + specs
openspec validate --all --strict --json # warnings become errors
```

**JSON output** (v1.4.1, verified — empty project):
```json
{
  "items": [],
  "summary": {
    "totals": {"items": 0, "passed": 0, "failed": 0},
    "byType": {
      "change": {"items": 0, "passed": 0, "failed": 0},
      "spec":   {"items": 0, "passed": 0, "failed": 0}
    }
  },
  "version": "1.0"
}
```

When items are present, each has shape `{name, valid, errors[], warnings[]}` keyed under the `items` array (no `results.changes` / `results.specs` split).

---

### `openspec schemas`

List available workflow schemas.

**Usage**:
```bash
openspec schemas --json
```

**JSON output** (v1.4.1, verified — top-level array):
```json
[
  {
    "name": "spec-driven",
    "description": "Default OpenSpec workflow - proposal → specs → design → tasks",
    "artifacts": ["proposal", "specs", "design", "tasks"],
    "source": "package"
  },
  {
    "name": "workspace-planning",
    "description": "Workspace planning workflow for cross-area changes",
    "artifacts": ["proposal", "specs", "design", "tasks"],
    "source": "package"
  }
]
```

> The autonomous orchestrator (PHASE0–PHASE6) is built around the `spec-driven` schema only. Other schemas are not wired into the 7-phase loop.

---

### `openspec templates`

Show resolved template paths for a schema.

**Usage**:
```bash
openspec templates --schema spec-driven --json
```

**JSON output** (v1.4.1, verified):
```json
{
  "proposal": {"path": "/abs/path/to/schemas/spec-driven/templates/proposal.md", "source": "package"},
  "specs":    {"path": "/abs/path/to/schemas/spec-driven/templates/spec.md",     "source": "package"},
  "design":   {"path": "/abs/path/to/schemas/spec-driven/templates/design.md",   "source": "package"},
  "tasks":    {"path": "/abs/path/to/schemas/spec-driven/templates/tasks.md",    "source": "package"}
}
```

---

### `openspec show`

Display a change or spec. **Note: in v1.4.1 this is interactive-only and takes no positional `<item-name>`.** Running `openspec show <name>` returns `Unknown item '<name>'`.

**Usage**:
```bash
openspec show                                  # interactive picker
openspec change show                           # change selector
openspec spec show                             # spec selector
```

For programmatic change details, use `openspec status --change <name> --json` (gives artifact paths, deps, etc.) or `openspec list --json` (gives name + progress + last modified).

---

### `openspec` other commands

The upstream CLI has additional commands (`archive`, `init`, `update`, `view`, `change`, `spec`, `config`, `schema`, `workspace`, `context-store`, `initiative`, `feedback`, `completion`, `new`, `set`). For most agent flows you only need the seven above. The autonomous orchestrator handles archiving (via `osc-archive-change` skill) and lifecycle (via `openspec-extended orchestrate`).

---

## B. `openspec-extended` (this project)

The `openspec-extended` binary wraps the `osx` library and provides the lifecycle commands. It is the **entry point users run** to install resources or trigger the autonomous workflow.

```bash
openspec-extended --version    # 0.19.x
openspec-extended <subcommand> [options]
```

### `openspec-extended install`

Deploy extended resources to the target tool directory.

**Usage**:
```bash
openspec-extended install <tool> [--with-core]
```

| Argument / flag | Description |
|-----------------|-------------|
| `<tool>` | `opencode` or `claude` (required) |
| `--with-core` | Also deploy upstream `osc-*` skills via `openspec init --tools <tool> --force` |

**Behavior**:
- Copies skills, commands, agents, scripts, and `lib/osx` to `.opencode/` (or `.claude/`)
- Updates `.gitignore` to exclude `state.json`, `complete.json`, `iterations.json`, `decision-log.json`, `verification-report.md`, `reflections.md`, `test-compliance-report.md`, `suggestions.md`, `.openspec-baseline.json`, `.osx-orchestrate-*.log`
- Renames upstream `opsx-*` / `openspec-*` skills and commands to `osc-*` (replaces `/opsx-` and `/opsx:` with `/osc-` in command file content too)
- Validates that all manifest resources are deployed; warns on missing

### `openspec-extended update`

Same as `install` but **always overwrites** existing resources (regardless of version).

**Usage**:
```bash
openspec-extended update <tool> [--with-core]
```

### `openspec-extended orchestrate`

Run the 7-phase autonomous implementation workflow for a change.

**Usage**:
```bash
openspec-extended orchestrate <change> [options]
openspec-extended orchestrate --list
```

| Argument / flag | Default | Description |
|-----------------|---------|-------------|
| `<change>` | (required unless `--list`) | Change name; resolved to `openspec/changes/<change>/` or an archived folder ending in `-<change>` |
| `--from-phase PHASEN` | (auto-resume) | Start from this phase (e.g., `PHASE2`); skips pre-flight validation |
| `--max-phase-iterations N` | `10` | Per-phase retry budget; `-1` = unlimited |
| `--timeout N` | `1800` | Per-agent-subprocess timeout in seconds |
| `--model M` | (platform default) | AI model name |
| `--clean` / `-c` | off | Wipe `state.json` / `complete.json` / `iterations.json` / `.openspec-baseline.json` / auto log; re-run full pre-flight |
| `--force` / `-f` | off | Skip interactive prompts (dirty git, resume confirm) |
| `--list` | off | List available changes; do not orchestrate |
| `--dry-run` / `-d` | off | Show what would happen |
| `--verbose` / `-v` | off | Verbose output |
| `--no-color` / `-n` | off | Disable colored output |
| `--log-file F` | (auto, `.osx-orchestrate-<change>.log`) | Per-invocation log; on PHASE6 success, moved to archive and amended into the archive commit |

**Exit codes**:
- `0` — completed (either ran through, resumed to completion, or change was already archived)
- `1` — phase failure, blocker detected, archive validation failed, change not found
- `2` — missing required argument
- `124` — phase hit the per-subprocess timeout (raised as phase failure, exit `1`)
- `130` — interrupted (SIGINT/SIGTERM)

**State cleanup**:
- On success: `state.json`, `complete.json`, `.openspec-baseline.json`, and the auto log are deleted
- On failure or interrupt: state files are preserved for resumption
- On PHASE6 success: the auto log is moved to `<archive>/osx-orchestrate.log` and the archive commit is amended

---

## C. `osx` (change state tool)

The `osx` tool is the change-management library exposed as a CLI for agent use. It lives at `.opencode/scripts/lib/osx` (or `.claude/scripts/lib/osx`) after install, and is the same Python source as `source/lib/osx.py`.

```bash
osx <domain> <action> [args]
```

The `openspec-extended` binary does **not** mount `osx` as a subcommand. Call it directly via the deployed script.

**Conventions**:
- Output is JSON to stdout
- Errors are JSON to stderr with shape `{"error": "<code>", "message": "...", ...}` and exit code `1`
- Read actions: `get` (and `check` for `complete`, `current`/`next` for `phase`, the per-`validate` action names)
- Write actions: `append`, `complete`, `set-phase`, `transition`, `clear-transition`, `record`, `advance`, `set`

### `ctx`

| Action | Args | Purpose |
|--------|------|---------|
| `get` | `<change>` | Load aggregate context: state, git status, artifacts, history (decision-log + iterations counts) |

**Output** (key fields): `change`, `state: {phase, iteration, phase_complete}`, `git: {modified, added, untracked, clean, branch}`, `artifacts: {proposal, specs, design, tasks}` (each `{exists, count\|size}`), `history: {decision_log_entries, iterations_recorded}`.

### `state`

| Action | Args | Purpose |
|--------|------|---------|
| `get` | `<change>` | Read `state.json` |
| `complete` | `<change>` | Mark current phase as complete (sets `phase_complete: true`); orchestrator advances |
| `set-phase` | `<change> <PHASEN> [--iteration N]` | Force-set phase (use `--from-phase` on `orchestrate` when possible) |
| `transition` | `<change> <target> <reason> [details]` | Set pending transition; orchestrator routes to `<target>` next |
| `clear-transition` | `<change>` | Clear a pending transition |

**Transition reasons** (canonical, validated by the library):
- `implementation_incorrect` — code is wrong, do not modify artifacts
- `artifacts_modified` — specs/design updated, go to PHASE1 to re-implement
- `retry_requested` — same phase, different approach

### `phase`

| Action | Args | Purpose |
|--------|------|---------|
| `current` | `<change>` | Read current phase from state (creates PHASE0 state if missing) |
| `next` | `<change>` | Read next phase in sequence |
| `advance` | `<change>` | Force-advance to next phase (rare; prefer `state complete` or `state transition`) |

### `iterations`

| Action | Args | Purpose |
|--------|------|---------|
| `get` | `<change>` | List all iterations with `iteration` numbers |
| `append` | `<change> --phase P --iteration N [--summary S] [--commit-hash H] [--status S] [--notes N] [--issues JSON] [--artifacts-modified JSON] [--decisions JSON] [--errors JSON] [--extra JSON_OBJECT]` | Append an iteration record; `extra` is merged as a JSON object (not stringified) |

### `log`

| Action | Args | Purpose |
|--------|------|---------|
| `get` | `<change>` | List all decision-log entries |
| `append` | `<change> --phase P --iteration N [--summary S] [--commit-hash H] [--next-steps S] [--issues JSON] [--artifacts-modified JSON] [--decisions JSON] [--errors JSON] [--extra JSON_OBJECT]` | Append a decision-log entry; `extra` is merged as a JSON object |

**`log append` input validation:** `--summary` and `--next-steps` are validated before storage. The command rejects:

- Strings longer than 2,000 characters (`{"error":"input_too_long", ...}`)
- Strings containing zsh/bash env-dump fingerprints such as `integer 10 readonly`, `array readonly`, `tied zsh_eval_context` (`{"error":"input_tainted", ...}`)

These guards exist because LLMs sometimes use markdown backticks (e.g. `` `local` ``) inside shell-passed strings, and the shell interprets them as command substitution. The result is a 20KB+ shell environment dump landing in `decision-log.json`. If you see `input_too_long` or `input_tainted`, remove the backticks from the argument and retry. Use single quotes (`'like this'`), double quotes (`"like this"`), or plain text.

### `complete`

| Action | Args | Purpose |
|--------|------|---------|
| `check` | `<change>` | Returns `{exists: true|false}`; exit `0` if file exists, `1` if not |
| `get` | `<change>` | Returns `{status, with_blocker, blocker_reason?}` |
| `set` | `<change> [status] [--blocker-reason R]` | Write `complete.json`; `status=BLOCKED` requires `--blocker-reason` |

### `baseline`

| Action | Args | Purpose |
|--------|------|---------|
| `record` | (none) | Record current HEAD as the workflow baseline to `.openspec-baseline.json` |
| `get` | (none) | Read the baseline |

### `git`

| Action | Args | Purpose |
|--------|------|---------|
| `get` | `<change>` | Git status of the change dir: `{modified, added, untracked, clean, branch}` |

### `osx validate`

| Action | Args | Purpose |
|--------|------|---------|
| `json` | `<file>` | Validate JSON syntax |
| `skills` | (none) | All required `osx-*` and `osc-*` skills present |
| `commands` | (none) | All 7 phase commands present |
| `change-dir` | `<change>` | Change dir exists with `proposal.md`, `design.md`, `tasks.md`, non-empty `specs/` |
| `archive` | `<change>` | Archive exists at `openspec/changes/archive/...-<-change>` |
| `iterations` | `<change>` | `iterations.json` exists and is valid JSON |
| `completion` | `<change>` | `state.json` + `complete.json` + `iterations.json` + `decision-log.json` + archive all present |

Exit `0` if valid, `1` if invalid.

### `osx instructions`

Thin wrapper around `openspec instructions` for use from `osx` workflows.

| Args | Purpose |
|------|---------|
| `<artifact> [--change <name>] [--json]` | Proxy to `openspec instructions <artifact> --change <name> --json` |

---

## Common error patterns

| Error (shape) | Cause | Fix |
|---------------|-------|-----|
| `{"error":"change_not_found", "message":"...", "change":"X"}` | Change dir not in `openspec/changes/X/` or archive | Run `openspec-extended orchestrate --list` to see valid names |
| `{"error":"state_not_found", ...}` | `state.json` missing for the change | Use `openspec-extended orchestrate --clean` or run a phase to create it |
| `{"error":"invalid_target", "valid":["PHASE0",...,"PHASE6"]}` | Bad `state transition` target | Use one of the listed PHASEs |
| `{"error":"invalid_reason", "valid":["implementation_incorrect","artifacts_modified","retry_requested"]}` | Bad `state transition` reason | Use one of the three valid reasons |
| `{"error":"missing_field", ...}` | `iterations append` or `log append` missing `--phase` / `--iteration` | Pass both flags or pipe JSON via stdin |
| `{"error":"invalid_json", ...}` | Malformed JSON passed for `--issues` / `--decisions` / etc. | Pass valid JSON strings |
| `{"error":"input_too_long", ...}` | `log append` `--summary` or `--next-steps` exceeded 2,000 chars | Shorten the text; usually caused by backticks interpreted as command substitution |
| `{"error":"input_tainted", ...}` | `log append` `--summary` or `--next-steps` contains a zsh/bash env-dump fingerprint | Remove backticks from the argument; use single quotes, double quotes, or plain text for inline code references |
| `Unknown item 'X'` (from `openspec show`) | v1.4.1 `show` is interactive; no positional arg | Use `openspec status --change X --json` or `openspec list --json` instead |
| `openspec: command not found` | Upstream CLI not installed | `npm install -g @fission-ai/openspec` |
| `Not in a git repository` (from `orchestrate`) | Pre-flight requires git | `git init` first |

---

## Environment variables

| Variable | Default | Effect |
|----------|---------|--------|
| `OPENSPEC_CONCURRENCY` | `6` | Parallel validation threads |
| `NO_COLOR` | (unset) | Disable color in `openspec` output |
| `OPENSPEC_CONFIG` | `openspec/config.yaml` | Path to project config |

`openspec-extended` does not currently read any environment variables; behavior is fully flag-driven.

---

## See also

- Main skill: `../SKILL.md`
- `../osx-workflow/references/autonomous-workflow.md` — phase protocols and orchestrator state
- `references/artifact-formats.md` — artifact structure and templates
- `research/openspec-cli.md` — upstream CLI reference (project-level, may be older)
