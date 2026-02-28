# OpenSpec-extended - OpenCode Reference

## Project Context

**Purpose**: Bridge AI coding assistants with OpenSpec - spec-driven development framework.

**Philosophy**: Agree on WHAT to build before writing code. Artifacts live in repository, not tool-specific systems.

**Scope**: Minimal project - no deep infrastructure, CI, or complex install scripts.

**Extension Skills** (core skills in `openspec-core/AGENTS.md`):

| Skill | Purpose |
|-------|---------|
| `openspec-concepts` | Teaches AI agents about OpenSpec framework |
| `openspec-modify-artifact` | Modifies OpenSpec artifacts with dependency tracking |
| `openspec-review-artifact` | Reviews artifacts for quality, completeness, consistency |
| `openspec-maintain-ai-docs` | Maintain AGENTS.md and CLAUDE.md documentation |
| `openspec-generate-changelog` | Generate changelogs in Keep a Changelog format |
| `openspec-review-test-compliance` | Review test coverage for OpenSpec changes |

---

## Quick Reference

| Command | Purpose |
| ------- | ------- |
| `openspecx install opencode` | Add skills, commands, agents, scripts to `.opencode/` |
| `openspecx install claude` | Add skills, commands to `.claude/` |
| `openspecx update opencode` | Force update all resources in `.opencode/` |
| `openspecx update claude` | Force update all resources in `.claude/` |

**Verify**: `ls .opencode/{skills,agents,commands,scripts}/`

---

## Code Style

### Bash Requirements

| Rule | Format |
| ---- | ------ |
| Header | `#!/bin/bash` (Bash 4.0+) |
| Strict mode | `set -euo pipefail` at top |
| Constants | `readonly UPPER_CASE` |
| Variables | `snake_case`, always quoted: `"$VAR"` |
| Functions | `snake_case()` |
| Arrays | `UPPER_CASE` |

### Key Patterns

```bash
# Associative arrays
declare -A TOOL_DIRS=(["opencode"]=".opencode")

# Logging
log_success() { echo -e "${COLOR_GREEN}✓${COLOR_RESET} $*"; }
log_error() { echo -e "${COLOR_RED}✗${COLOR_RESET} $*" >&2; }

# Error handling: exit 1 (error), exit 0 (success), messages to >&2
```

### Script Structure

1. Shebang + description  2. `set -euo pipefail`  3. readonly constants  4. Logging functions  5. Argument validation  6. Main logic  7. Exit codes only on errors

---

## Project Structure

```
bin/openspecx              # Main executable
openspec-core/             # Official OpenSpec workflows (read-only, sync from upstream)
resources/opencode/        # Extended resources (maintained locally)
  ├── skills/              # Extension skills
  ├── agents/              # Agent definitions (personality + capabilities)
  ├── commands/            # Phase-specific commands
  └── scripts/
      ├── openspec-auto    # Autonomous workflow orchestrator
      └── lib/             # Helper utilities (osc-*)
research/                  # Platform documentation
```

---

## Adding New Skills

Create `resources/opencode/skills/<skill-name>/SKILL.md` with frontmatter:

```yaml
---
name: my-skill
description: Brief description
license: MIT
---
```

**Naming**: 1-64 chars, lowercase with hyphens, regex `^[a-z0-9]+(-[a-z0-9]+)*$`, must match directory name.

**Platform details**: `research/opencode-docs.md`

---

## Autonomous Workflow

**Purpose**: 7-phase autonomous implementation loop via `openspec-auto`

### Agents & Commands

| Agent | Tools | Temp | Phases |
| ----- | ----- | ---- | ------ |
| `openspec-analyzer` | read, grep, glob, bash | 0.1 | PHASE0, PHASE2, PHASE6 |
| `openspec-builder` | read, grep, glob, bash, write, edit | 0.4 | PHASE1 |
| `openspec-maintainer` | read, grep, glob, bash, write, edit | 0.3 | PHASE3, PHASE4, PHASE5 |

| Command | Agent | Description |
| ------- | ----- | ----------- |
| `/openspec-phase0` | analyzer | Artifact Review |
| `/openspec-phase1` | builder | Implementation |
| `/openspec-phase2` | analyzer | Verification |
| `/openspec-phase3` | maintainer | Maintain-Docs |
| `/openspec-phase4` | maintainer | Sync |
| `/openspec-phase5` | maintainer | Archive |
| `/openspec-phase6` | analyzer | Self-Reflection |

### Usage

```bash
.opencode/scripts/openspec-auto <change-name>
.opencode/scripts/openspec-auto add-auth --max-iterations 20 --verbose
.opencode/scripts/openspec-auto add-auth --from-phase PHASE3
.opencode/scripts/openspec-auto add-auth --dry-run
```

### Options

`--max-iterations N` `--timeout N` `--model MODEL` `--verbose` `--dry-run` `--force` `--clean` `--from-phase PHASEX` `--list` `--version`

### State Files (`openspec/changes/<change>/`)

| File | Purpose | Lifecycle |
| ---- | ------- | --------- |
| `state.json` | Phase tracking + completion | Deleted on success |
| `complete.json` | Workflow completion (PHASE6) | Deleted after validation |
| `iterations.json` | Iteration history | Never deleted |
| `decision-log.json` | Agent reasoning | Never deleted |

### Manual Invocation

```
/openspec-phase0 my-change-name
@openspec-analyzer  # hidden but accessible
```

### Lib Scripts

@docs/lib-scripts.md

---

## License

MIT License - see LICENSE file
