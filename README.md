# OpenSpec-extended

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Bash](https://img.shields.io/badge/Bash-3.2+-green.svg?style=flat-square)](https://www.gnu.org/software/bash/)
[![Version](https://img.shields.io/badge/version-v0.13.0-orange.svg?style=flat-square)](https://github.com/amauryconstant/openspec-extended)

An **extension pack** for [OpenSpec](https://github.com/Fission-AI/OpenSpec) that adds autonomous implementation capabilities and utility skills for AI coding assistants.

## Why use this?

| Feature | OpenSpec Core | OpenSpec-extended |
|---------|---------------|-------------------|
| Manual change workflows | ✓ 11 commands | ✓ (via `--with-core`) |
| Autonomous implementation | ✗ | ✓ 7-phase loop |
| Specialized agents | ✗ | ✓ 3 agents |
| Utility skills | ✗ | ✓ 6 skills |

**Key additions:**

- **Autonomous workflow** — Run end-to-end implementation without manual intervention
- **Specialized agents** — Analyzer (0.1 temp), Builder (0.4 temp), Maintainer (0.3 temp)
- **Utility skills** — Concepts, modify artifacts, review artifacts, changelogs, test compliance, AI docs

## Requirements

- [OpenSpec](https://github.com/Fission-AI/OpenSpec) v1.2.0+ (recommended)
- Bash 3.2 or higher

## Installation

### Quick Install

```bash
curl -sSL https://raw.githubusercontent.com/amauryconstant/openspec-extended/main/install.sh | bash
```

### Specific Version

```bash
VERSION=v0.13.0 curl -sSL https://raw.githubusercontent.com/amauryconstant/openspec-extended/main/install.sh | bash
```

### System-wide Install

```bash
PREFIX=/usr/local curl -sSL https://raw.githubusercontent.com/amauryconstant/openspec-extended/main/install.sh | bash
```

### From Source (Development)

```bash
git clone https://github.com/amauryconstant/openspec-extended.git
cd OpenSpec-extended
export PATH="$PWD/bin:$PATH"
```

### Verify

```bash
openspecx --version
# openspecx 0.13.0
```

## Setup in Your Project

```bash
cd your-project

# Install extension resources
openspecx install opencode

# Include core OpenSpec workflows (11 commands)
openspecx install opencode --with-core
```

### Verify Installation

```bash
ls .opencode/{skills,agents,commands,scripts}/
```

## Usage

### Installing Resources

| Command | Description |
|---------|-------------|
| `openspecx install opencode` | Add missing resources (skip existing) |
| `openspecx install claude` | Same for Claude Code |
| `openspecx install opencode --with-core` | Include 11 core OpenSpec workflows |
| `openspecx update opencode` | Force update all (overwrite existing) |

### Extension Skills

| Skill | Purpose |
|-------|---------|
| `openspec-concepts` | Teaches AI agents about OpenSpec framework |
| `openspec-modify-artifacts` | Modifies artifacts with dependency tracking |
| `openspec-review-artifacts` | Reviews artifacts for quality and completeness |
| `openspec-generate-changelog` | Generate changelogs (Keep a Changelog format) |
| `openspec-review-test-compliance` | Review test coverage for OpenSpec changes |
| `openspec-maintain-ai-docs` | Maintain AGENTS.md and CLAUDE.md |

### Specialized Agents

| Agent | Purpose | Tools | Temp |
|-------|---------|-------|------|
| `openspec-analyzer` | Review, verify, reflect | read, grep, glob, bash | 0.1 |
| `openspec-builder` | Implementation | read, grep, glob, bash, write, edit | 0.4 |
| `openspec-maintainer` | Docs, sync, archive | read, grep, glob, bash, write, edit | 0.3 |

## Autonomous Workflow

7-phase loop for end-to-end implementation via `openspec-auto`.

### Commands

| Command | Phase | Description |
|---------|-------|-------------|
| `/openspec-phase0` | Review | Analyze existing artifacts |
| `/openspec-phase1` | Build | Implement tasks |
| `/openspec-phase2` | Verify | Verify implementation |
| `/openspec-phase3` | Docs | Update documentation |
| `/openspec-phase4` | Sync | Sync with upstream |
| `/openspec-phase5` | Reflect | Self-assessment |
| `/openspec-phase6` | Archive | Archive completed change |

### Usage

```bash
# Run autonomous implementation
.opencode/scripts/openspec-auto <change-name>

# With options
.opencode/scripts/openspec-auto add-auth --max-phase-iterations 20 --verbose
.opencode/scripts/openspec-auto add-auth --from-phase PHASE3
.opencode/scripts/openspec-auto add-auth --dry-run
```

### Options

| Option | Description |
|--------|-------------|
| `--max-phase-iterations N` | Max retries per phase before failing (default: 10, -1 for unlimited) |
| `--timeout N` | Timeout in seconds |
| `--model MODEL` | Specify model to use |
| `--verbose` | Enable verbose output |
| `--dry-run` | Show what would happen |
| `--force` | Force operation |
| `--clean` | Clean state before starting |
| `--from-phase PHASEX` | Start from specific phase |
| `--list` | List available phases |
| `--version` | Show version |

### State Files

Located in `openspec/changes/<change>/`:

| File | Purpose | Lifecycle |
|------|---------|-----------|
| `state.json` | Phase tracking | Deleted on success |
| `complete.json` | Completion marker | Deleted after validation |
| `iterations.json` | Iteration history | Archived |
| `decision-log.json` | Agent reasoning | Archived |

After PHASE6 (Archive), files move to `openspec/changes/archive/YYYY-MM-DD-<change>/`.

## Project Structure

```
OpenSpec-extended/
├── bin/openspecx           # CLI installer
├── install.sh              # Installation script
├── openspec-core/          # Core workflows (synced from upstream)
├── resources/
│   ├── opencode/           # OpenCode resources
│   │   ├── skills/         # 6 extension skills
│   │   ├── agents/         # 3 agent definitions
│   │   ├── commands/       # Phase commands + opsx-* utilities
│   │   └── scripts/        # openspec-auto + lib/
│   └── claude/             # Claude Code resources (same structure)
└── research/               # Platform documentation
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes (follow code style in AGENTS.md)
4. Run `mise run test` before submitting
5. Open a pull request

## License

MIT License - see [LICENSE](LICENSE) file
