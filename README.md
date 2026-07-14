# OpenSpec-extended

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg?style=flat-square)](https://www.python.org/)
[![Version](https://img.shields.io/badge/version-v1.1.0-orange.svg?style=flat-square)](https://github.com/amauryconstant/openspec-extended)

An **extension pack** for [OpenSpec](https://github.com/Fission-AI/OpenSpec) that adds autonomous implementation capabilities and utility skills for AI coding assistants.

## Why use this?

| Feature                   | OpenSpec Core | OpenSpec-extended     |
| ------------------------- | ------------- | --------------------- |
| Manual change workflows   | ✓ 11 commands | ✓ (via `--with-core`) |
| Autonomous implementation | ✗             | ✓ 7-phase loop        |
| Specialized agents        | ✗             | ✓ 3 agents            |
| Utility skills            | ✗             | ✓ 8 skills            |
| Unified CLI surface       | ✓             | ✓ (passthrough + ext) |

**Key additions:**

- **Autonomous workflow** — Run end-to-end implementation without manual intervention
- **Specialized agents** — Analyzer (0.1 temp), Builder (0.4 temp), Maintainer (0.3 temp)
- **Utility skills** — Concepts, modify artifacts, review artifacts, changelogs, test compliance, AI docs
- **Unified CLI surface** — All upstream OpenSpec commands (`validate`, `list`, `show`, `status`, `instructions`, `templates`, `schemas`, `init`, `update`, `feedback`, `completion`) plus the 7-phase orchestrator under one binary.

## Requirements

- [OpenSpec](https://github.com/Fission-AI/OpenSpec) v1.2.0+ (recommended)
- Python 3.12 or higher (only for building from source)
- No Python needed when installing the prebuilt binary

## Installation

### Quick Install (Binary)

```bash
curl -sSL https://raw.githubusercontent.com/amauryconstant/openspec-extended/main/install.sh | bash
```

### Specific Version (Binary)

```bash
VERSION=v1.1.0 curl -sSL https://raw.githubusercontent.com/amauryconstant/openspec-extended/main/install.sh | bash
```

### System-wide Install (Binary)

```bash
PREFIX=/usr/local curl -sSL https://raw.githubusercontent.com/amauryconstant/openspec-extended/main/install.sh | bash
```

### From Source (Development)

```bash
git clone https://github.com/amauryconstant/openspec-extended.git
cd OpenSpec-extended
uv tool install .
# or: pip install .
```

The entry point `openspec-extended` is registered automatically.

### Verify

```bash
openspec-extended --version
# openspec-extended 0.19.0
```

## Setup in Your Project

```bash
cd your-project

# Install extension resources
openspec-extended install opencode

# Include core OpenSpec workflows (11 commands)
openspec-extended install opencode --with-core
```

### Verify Installation

```bash
ls .opencode/{skills,agents,commands}/
```

## Usage

### Installing Resources

| Command                                         | Description                           |
| ----------------------------------------------- | ------------------------------------- |
| `openspec-extended install opencode`            | Add missing resources (skip existing) |
| `openspec-extended install claude`              | Same for Claude Code                  |
| `openspec-extended install opencode --with-core`| Include 11 core OpenSpec workflows    |
| `openspec-extended update opencode`             | Force update all (overwrite existing) |
| `openspec-extended update-core [opencode]`      | Refresh upstream OpenSpec instruction files |

### Workflow Commands (Passthrough)

All upstream OpenSpec commands are available directly through `openspec-extended`. These are thin pass-through wrappers — the binary delegates to your installed `openspec` CLI and forwards its exit code.

| Command                                  | Description                              |
| ---------------------------------------- | ---------------------------------------- |
| `openspec-extended validate [item]`      | Validate changes/specs (--all, --strict) |
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

Example:

```bash
openspec-extended validate --all --json --strict
openspec-extended show my-change --deltas-only --json
openspec-extended status --change my-change --json
openspec-extended feedback "love the new flow" --body "Detailed description..."
```

### Extension Skills

| Skill                        | Purpose                                        |
| ---------------------------- | ---------------------------------------------- |
| `osx-concepts`               | Teaches AI agents about OpenSpec framework     |
| `osx-modify-artifacts`       | Modifies artifacts with dependency tracking    |
| `osx-review-artifacts`       | Reviews artifacts for quality and completeness |
| `osx-generate-changelog`     | Generate changelogs (Keep a Changelog format)  |
| `osx-review-test-compliance` | Review test coverage for OpenSpec changes      |
| `osx-maintain-ai-docs`       | Maintain AGENTS.md and CLAUDE.md               |

### Specialized Agents

| Agent              | Purpose                 | Tools                               | Temp |
| ------------------ | ----------------------- | ----------------------------------- | ---- |
| `osx-analyzer`     | Review, verify, reflect | read, grep, glob, bash              | 0.1  |
| `osx-builder`      | Implementation          | read, grep, glob, bash, write, edit, todowrite | 0.4  |
| `osx-maintainer`   | Docs, sync, archive     | read, grep, glob, bash, write, edit | 0.3  |

## Autonomous Workflow

7-phase loop for end-to-end implementation via `openspec-extended orchestrate`.

### Commands

| Command         | Phase   | Description                |
| --------------- | ------- | -------------------------- |
| `/osx-phase0`   | Review  | Analyze existing artifacts |
| `/osx-phase1`   | Build   | Implement tasks            |
| `/osx-phase2`   | Verify  | Verify implementation      |
| `/osx-phase3`   | Docs    | Update documentation       |
| `/osx-phase4`   | Sync    | Sync with upstream         |
| `/osx-phase5`   | Reflect | Self-assessment            |
| `/osx-phase6`   | Archive | Archive completed change   |

### Usage

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

### Options

| Option                     | Description                                                          |
| -------------------------- | -------------------------------------------------------------------- |
| `--max-phase-iterations N` | Max retries per phase before failing (default: 10, -1 for unlimited) |
| `--timeout N`              | Timeout in seconds                                                   |
| `--model MODEL`            | Specify model to use                                                 |
| `--verbose`                | Enable verbose output                                                |
| `--dry-run`                | Show what would happen                                               |
| `--force`                  | Force operation                                                      |
| `--clean`                  | Clean state before starting                                          |
| `--from-phase PHASEX`      | Start from specific phase                                            |
| `--list`                   | List available changes                                               |
| `--version`                | Show version                                                         |

### State Files

Located in `openspec/changes/<change>/`:

| File                | Purpose           | Lifecycle                |
| ------------------- | ----------------- | ------------------------ |
| `state.json`        | Phase tracking    | Deleted on success       |
| `complete.json`     | Completion marker | Deleted after validation |
| `iterations.json`   | Iteration history | Archived                 |
| `decision-log.json` | Agent reasoning   | Archived                 |

After PHASE6 (Archive), files move to `openspec/changes/archive/YYYY-MM-DD-<change>/`.

## Documentation

| Doc | Purpose |
|-----|---------|
| [docs/cli-comparison.md](docs/cli-comparison.md) | Maps upstream `openspec` commands to `openspec-extended` passthroughs and the `osx` sub-app |
| [docs/orchestrator-state-machine.md](docs/orchestrator-state-machine.md) | Phase model, transition reasons, retry budget, schema resolution, resume semantics |
| [docs/troubleshooting.md](docs/troubleshooting.md) | Error code to fix table for state, git, missing CLI tools, schema, orchestrator errors |

The repository also dogfoods the orchestrator on itself: see
[`openspec/changes/example-orchestrated/`](openspec/changes/example-orchestrated/)
for a real spec-driven change that the 7-phase loop can drive end-to-end,
producing [`examples/hello-orchestrator.md`](examples/hello-orchestrator.md).

## Project Structure

```
OpenSpec-extended/
├── source/                  # Python implementation
│   ├── cli.py               # Typer CLI (install/update/orchestrate/osx)
│   ├── lib/osx.py           # Change-management library (pure functions, no CLI)
│   ├── osx_cli.py           # Typer app for `openspec-extended osx …`
│   └── orchestrator/
│       ├── engine.py        # 7-phase orchestrator
│       └── runner.py        # AI-runner abstraction (opencode / claude dispatch)
├── install.sh               # Bash binary installer
├── openspec.spec            # PyInstaller spec
├── openspec-core/           # Core workflows (synced from upstream)
├── resources/
│   ├── opencode/            # OpenCode resources
│   │   ├── skills/          # 6 extension skills
│   │   ├── agents/          # 3 agent definitions
│   │   └── commands/        # Phase commands + osx-* utilities
│   └── claude/              # Claude Code resources (same structure)
├── tests/                   # pytest + bats suite (unit/integration/mechanism/e2e)
├── docs/                    # User-facing documentation
├── .mise/tasks/             # sync-core, release, version/{check,update} (bash)
└── research/                # Platform documentation
```

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
3. Make changes (follow code style in AGENTS.md)
4. Run `mise run verify` before submitting
5. Open a pull request

## License

MIT License - see [LICENSE](LICENSE) file
