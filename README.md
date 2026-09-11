# OpenSpec-extended

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg?style=flat-square)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-v1.8.0-orange.svg?style=flat-square)](https://github.com/amauryconstant/openspec-extended)

An **extension pack** for [OpenSpec](https://github.com/Fission-AI/OpenSpec) that adds autonomous implementation capabilities and utility skills for AI coding assistants.

## Why use this?

| Feature                   | OpenSpec Core | OpenSpec-extended     |
| ------------------------- | ------------- | --------------------- |
| Manual change workflows   | ✓ 12 commands | ✓ (via `--with-core`) |
| Autonomous implementation | ✗             | ✓ 7-phase loop (opt-in via `--with-autonomous`) |
| Specialized agents        | ✗             | ✓ 4 agents (with `--with-autonomous`) |
| Utility skills            | ✗             | ✓ 3 skills (default)   |
| Unified CLI surface       | ✓             | ✓ (passthrough + ext) |

## Requirements

- [OpenSpec](https://github.com/Fission-AI/OpenSpec) v1.13.0+ (required)
- Python 3.12 or higher (only for building from source)
- No Python needed when installing the prebuilt binary

## Install

### Quick install (binary)

```bash
curl -sSL https://raw.githubusercontent.com/amauryconstant/openspec-extended/main/install.sh | bash
```

```bash
# Specific version
VERSION=v1.8.0 curl -sSL https://raw.githubusercontent.com/amauryconstant/openspec-extended/main/install.sh | bash
```

```bash
# System-wide
PREFIX=/usr/local curl -sSL https://raw.githubusercontent.com/amauryconstant/openspec-extended/main/install.sh | bash
```

### From source

```bash
git clone https://github.com/amauryconstant/openspec-extended.git
cd openspec-extended
uv tool install .
# or: pip install .
```

The entry point `openspec-extended` is registered automatically.

```bash
openspec-extended --version
```

## Setup in your project

```bash
cd your-project

# Default: 3 utility skills + 2 commands
openspec-extended install opencode

# Add the autonomous workflow (7 phase commands, 4 agents, workflow skill)
openspec-extended install opencode --with-autonomous

# Include upstream OpenSpec workflows (12 osc-* commands)
openspec-extended install opencode --with-core
```

Verify the install:

```bash
ls .opencode/{skills,agents,commands}/
```

## Install flags

| Flag                       | Default | Effect |
|---------------------------|---------|--------|
| `--with-autonomous`       | off     | Deploy 7 phase commands, 4 agents, workflow skill (opt-in autonomous workflow) |
| `--with-core`             | off     | Deploy all 12 upstream OpenSpec workflows as `osc-*` |
| `--force`                 | off     | Required to overwrite an existing core deployment; saves a baseline snapshot first |
| `--language <lang>`       | unset   | Language for new-project artifacts (v1.10.0+). Precedence: `--language` > `OPENSPEC_LANGUAGE` > unset |
| `--strict-archived`       | off     | Fail on warnings from the post-install `openspec validate --archived` sweep |

## Commands

### Lifecycle (extended)

| Command                                              | Description                                   |
| ---------------------------------------------------- | --------------------------------------------- |
| `openspec-extended install opencode`                 | Deploy utility skills + commands (default)    |
| `openspec-extended install opencode --with-autonomous` | Also deploy 7 phase commands, 4 agents, workflow skill |
| `openspec-extended install claude`                   | Same for Claude Code                          |
| `openspec-extended update opencode`                  | Refresh utility resources (overwrite existing)|
| `openspec-extended update opencode --with-autonomous`| Refresh autonomous resources too              |
| `openspec-extended update-core [path]`               | Refresh upstream OpenSpec instruction files   |
| `openspec-extended restore-core`                     | Restore the openspec global config from the `.openspec-extended-baseline.json` snapshot |

### Workflow (autonomous, opt-in)

Run end-to-end implementation without manual intervention. Drives a change through seven phases: `PHASE0 ARTIFACT_REVIEW → PHASE1 IMPLEMENTATION → PHASE2 REVIEW → PHASE3 MAINTAIN_DOCS → PHASE4 SYNC → PHASE5 SELF_REFLECTION → PHASE6 ARCHIVE`.

```bash
# Run autonomous implementation
openspec-extended orchestrate <change-name>

# With options
openspec-extended orchestrate add-auth --max-phase-iterations 20 --verbose
openspec-extended orchestrate add-auth --from-phase PHASE3
openspec-extended orchestrate add-auth --dry-run

# Mutate change state directly (what the agents do per iteration)
openspec-extended osx state complete <change-name>
openspec-extended osx log append <change-name> --phase PHASE0 --iteration 1 --summary "…"
```

| Flag                       | Default | Effect |
|---------------------------|---------|--------|
| `--max-phase-iterations N` | 10      | Max retries per phase before failing (`-1` for unlimited) |
| `--timeout N`              | 1800    | Per-phase AI subprocess timeout (seconds) |
| `--model MODEL`            | (platform default) | Specify model to use |
| `--from-phase PHASEX`      | (auto-resume) | Resume from a specific phase (skips pre-flight) |
| `--clean`                  | off     | Wipe state files before starting |
| `--force`                  | off     | Continue without prompts |
| `--dry-run`                | off     | Show what would happen |
| `--verbose`                | off     | Verbose output |
| `--list`                   | off     | List available changes |
| `--schema <name>`          | (auto)  | Override schema resolution |

### Passthroughs to `openspec`

Every upstream `openspec` command is available directly through `openspec-extended`. These are thin pass-through wrappers — the binary delegates to your installed `openspec` CLI and forwards its exit code.

| Command                                  | Description                              |
| ---------------------------------------- | ---------------------------------------- |
| `openspec-extended validate [item]`      | Validate changes/specs (`--all`, `--strict`) |
| `openspec-extended list [--specs]`       | List active changes (or specs)           |
| `openspec-extended show [item]`          | Show a change or spec                    |
| `openspec-extended status [--change]`    | Show artifact completion status          |
| `openspec-extended instructions [art]`   | Output instructions for an artifact      |
| `openspec-extended templates [--schema]` | Show resolved template paths             |
| `openspec-extended schemas`              | List available workflow schemas          |
| `openspec-extended init [path]`          | Initialize OpenSpec in a project         |
| `openspec-extended update-core [path]`   | Refresh upstream instruction files       |
| `openspec-extended feedback <msg>`       | Submit feedback via `gh` issue           |
| `openspec-extended completion <shell>`   | Manage shell completions (bash/zsh/fish) |
| `openspec-extended view`                 | Interactive dashboard (v1.8.0+; requires TTY) |
| `openspec-extended archive [change]`     | Archive a completed change                |
| `openspec-extended new change <id>`      | Create a new change directory (v1.7.0+)  |
| `openspec-extended context`              | Print working context for resolved root (v1.5.0+) |
| `openspec-extended doctor`               | Report root relationship health (v1.5.0+) |
| `openspec-extended store <sub>`          | Manage stores (v1.5.0+)                  |
| `openspec-extended config <sub>`         | View/modify global OpenSpec config       |

For programmatic JSON access to store/schema state, see `openspec-extended osx <domain>` (e.g., `osx store list`).

```bash
openspec-extended validate --all --json --strict
openspec-extended show my-change --deltas-only --json
openspec-extended status --change my-change --json
openspec-extended feedback "love the new flow" --body "Detailed description..."
```

### Extension skills

The default install ships **3 extended skills**. `osx-workflow` (4th skill) requires `--with-autonomous`.

| Skill                        | Purpose                                        | Default? |
| ---------------------------- | ---------------------------------------------- | -------- |
| `osx-review-artifacts`       | Reviews artifacts for quality and completeness | yes      |
| `osx-review-test-compliance` | Review test coverage for OpenSpec changes      | yes      |
| `osx-commit`                 | Create commits matching project conventions    | yes      |
| `osx-workflow`               | Explains the 7-phase autonomous workflow       | opt-in (`--with-autonomous`) |

Framework concepts that used to live in the `osx-concepts` skill now ship
as `docs/concepts.md` (loaded on demand, not auto-deployed). Multi- and
single-artifact edits route through `/opsx:update` from upstream.

### Extension commands

The default install ships **9 slash commands** (7 phase commands on the
orchestrator side + 2 utility commands on the skills side). Each is
self-contained with its full body inline. The Claude mirror dual-emits
them as skills too.

| Command                       | Purpose                                       | Side          |
| ----------------------------- | --------------------------------------------- | ------------- |
| `/osx-changelog`              | Generate `CHANGELOG.md` from archived changes | orchestrator  |
| `/osx-maintain-docs`          | Update `AGENTS.md` and `CLAUDE.md`            | orchestrator  |
| `/osx-review`                 | Schema-driven pre-implementation audit        | skills        |
| `/osx-verify-tests`           | Spec-to-test alignment analysis               | skills        |
| `/osx-phase0`–`/osx-phase6`   | 7-phase autonomous workflow                   | orchestrator (opt-in) |

### Specialized agents (opt-in: `--with-autonomous`)

| Agent              | Purpose                 | Tools                               | Temp |
| ------------------ | ----------------------- | ----------------------------------- | ---- |
| `osx-analyzer`     | Read-only audit (PHASE0) | read, grep, glob, bash             | 0.1  |
| `osx-builder`      | Implementation (PHASE1)  | read, grep, glob, bash, write, edit, todowrite | 0.4  |
| `osx-reviewer`     | Verify + reflect (PHASE2/PHASE5) | read, grep, glob, bash, write, edit | 0.1  |
| `osx-maintainer`   | Docs, sync, archive (PHASE3/PHASE4/PHASE6) | read, grep, glob, bash, write, edit | 0.3  |

## State files

Located in `openspec/changes/<change>/`:

| File                | Purpose           | Lifecycle                |
| ------------------- | ----------------- | ------------------------ |
| `state.json`        | Phase tracking    | Deleted on success       |
| `complete.json`     | Completion marker | Deleted after validation |
| `iterations.json`   | Iteration history | Archived                 |
| `decision-log.json` | Agent reasoning   | Archived                 |

After `PHASE6`, files move to `openspec/changes/archive/YYYY-MM-DD-<change>/`.

## Environment variables

| Variable | Default | Effect |
|----------|---------|--------|
| `OPENSPEC_CONCURRENCY=<n>` | `6` | Propagated to `openspec validate --all`. |
| `OPENSPEC_LANGUAGE=<lang>` | (unset) | Sets the language for `openspec-extended init` and `openspec-extended install --with-core`. Overridden by the `--language` flag. |
| `NO_COLOR` | (unset) | Disable color in upstream `openspec` output. |
| `OPENSPEC_CONFIG` | `openspec/config.yaml` | Path to project OpenSpec config. |
| `OPENSPEC_VALIDATE_ARCHIVED_STRICT=1` | unset | When set, the post-install/update `validate --archived` sweep exits non-zero on warnings. Same effect as `--strict-archived`. |

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/concepts.md](docs/concepts.md) | Maintainer reference: repo layout, resource taxonomy, OpenSpec framework |
| [docs/cli-comparison.md](docs/cli-comparison.md) | Maps upstream `openspec` commands to `openspec-extended` passthroughs and the `osx` sub-app |
| [docs/orchestrator-state-machine.md](docs/orchestrator-state-machine.md) | Phase model, transition reasons, retry budget, schema resolution, resume semantics |
| [docs/review-modify-integration.md](docs/review-modify-integration.md) | Review/modify integration contract with core (v1.13.0 surface) |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Error code to fix table for state, git, missing CLI tools, schema, orchestrator errors |
| `osx-workflow` skill | Runtime reference for AI agents in deployed projects (4 tool layers, 7 phases, `osx` state I/O tool) |

## Development

```bash
# Install dev tools
mise install

# Verify code quality
mise run verify

# Run install.sh unit tests (hermetic — uses a local HTTP server)
bats tests/unit/install.bats

# Build the binary
mise run build

# Cut a release (from main, no API tokens needed locally)
mise run release patch
# → bumps versions, commits, tags, pushes the tag
# → GitHub Actions then builds + uploads the platform tarballs
```

`install.sh` honors a `BASE_URL` env var to redirect downloads away from
GitHub, which is how `tests/unit/install.bats` runs end-to-end install
tests without network access.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes (follow code style in `AGENTS.md`)
4. Run `mise run verify` before submitting
5. Open a pull request

## License

MIT License — see [LICENSE](LICENSE) file.
