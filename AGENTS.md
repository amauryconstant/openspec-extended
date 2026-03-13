# OpenSpec-extended - OpenCode Reference

## Project Context

**Purpose**: Bridge AI coding assistants with OpenSpec - spec-driven development framework.

**Philosophy**: Agree on WHAT to build before writing code. Artifacts live in repository, not tool-specific systems.

**Scope**: Minimal project - no deep infrastructure, CI, or complex install scripts.

## Naming Convention

| Resource        | Core (upstream) | Extended (local)    |
| --------------- | --------------- | ------------------- |
| **CLI**         | `openspec`      | `openspec-extended` |
| **Commands**    | `/osc-*`        | `/osx-*`            |
| **Skills**      | `osc-*`         | `osx-*`             |
| **Agents**      | N/A             | `osx-*`             |
| **Lib scripts** | N/A             | `osx`               |

**Extension Skills** (core skills in `openspec-core/AGENTS.md`):

| Skill                        | Purpose                                                  |
| ---------------------------- | -------------------------------------------------------- |
| `osx-concepts`               | Teaches AI agents about OpenSpec framework               |
| `osx-modify-artifacts`       | Modifies OpenSpec artifacts with dependency tracking     |
| `osx-review-artifacts`       | Reviews artifacts for quality, completeness, consistency |
| `osx-maintain-ai-docs`       | Maintain AGENTS.md and CLAUDE.md documentation           |
| `osx-generate-changelog`     | Generate changelogs in Keep a Changelog format           |
| `osx-review-test-compliance` | Review test coverage for OpenSpec changes                |

---

## Quick Reference

| Command                              | Purpose                                               |
| ------------------------------------ | ----------------------------------------------------- |
| `openspec-extended install opencode` | Add skills, commands, agents, scripts to `.opencode/` |
| `openspec-extended install claude`   | Add skills, commands to `.claude/`                    |
| `openspec-extended update opencode`  | Force update all resources in `.opencode/`            |
| `openspec-extended update claude`    | Force update all resources in `.claude/`              |

**Verify**: `ls .opencode/{skills,agents,commands,scripts}/`

---

## Code Style

### Bash Requirements

| Rule        | Format                                |
| ----------- | ------------------------------------- |
| Header      | `#!/bin/bash` (Bash 4.0+)             |
| Strict mode | `set -euo pipefail` at top            |
| Constants   | `readonly UPPER_CASE`                 |
| Variables   | `snake_case`, always quoted: `"$VAR"` |
| Functions   | `snake_case()`                        |
| Arrays      | `UPPER_CASE`                          |

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

1. Shebang + description 2. `set -euo pipefail` 3. readonly constants 4. Logging functions 5. Argument validation 6. Main logic 7. Exit codes only on errors

---

## Project Structure

```
bin/openspec-extended       # Main executable
openspec-core/              # Official OpenSpec workflows (read-only, sync from upstream)
resources/opencode/         # Extended resources (maintained locally)
  ├── skills/               # Extension skills (osx-*)
  ├── agents/               # Agent definitions (osx-*)
  ├── commands/             # Phase commands (osx-phase*, osx-*)
  └── scripts/
      ├── osx-orchestrate   # Autonomous workflow orchestrator
      └── lib/osx           # Helper CLI tool
research/                   # Platform documentation
```

---

## Adding New Skills

Create `resources/opencode/skills/<skill-name>/SKILL.md` with frontmatter:

```yaml
---
name: osx-my-skill
description: Brief description
license: MIT
---
```

**Naming**: 1-64 chars, lowercase with hyphens, regex `^[a-z0-9]+(-[a-z0-9]+)*$`, must match directory name. Use `osx-` prefix for extended skills.

**Platform details**: `research/opencode-docs.md`

---

## Autonomous Workflow

**Purpose**: 7-phase autonomous implementation loop via `osx-orchestrate`

### Agents & Commands

| Agent            | Tools                               | Temp | Phases                 |
| ---------------- | ----------------------------------- | ---- | ---------------------- |
| `osx-analyzer`   | read, grep, glob, bash              | 0.1  | PHASE0, PHASE2, PHASE5 |
| `osx-builder`    | read, grep, glob, bash, write, edit | 0.4  | PHASE1                 |
| `osx-maintainer` | read, grep, glob, bash, write, edit | 0.3  | PHASE3, PHASE4, PHASE6 |

| Command       | Agent      | Description     |
| ------------- | ---------- | --------------- |
| `/osx-phase0` | analyzer   | Artifact Review |
| `/osx-phase1` | builder    | Implementation  |
| `/osx-phase2` | analyzer   | Verification    |
| `/osx-phase3` | maintainer | Maintain-Docs   |
| `/osx-phase4` | maintainer | Sync            |
| `/osx-phase5` | analyzer   | Self-Reflection |
| `/osx-phase6` | maintainer | Archive         |

### Usage

```bash
.opencode/scripts/osx-orchestrate <change-name>
.opencode/scripts/osx-orchestrate add-auth --max-phase-iterations 20 --verbose
.opencode/scripts/osx-orchestrate add-auth --from-phase PHASE3
.opencode/scripts/osx-orchestrate add-auth --dry-run
```

### Options

`--max-phase-iterations N` `--timeout N` `--model MODEL` `--verbose` `--dry-run` `--force` `--clean` `--from-phase PHASEX` `--list` `--version`

### State Files (`openspec/changes/<change>/`)

| File                | Purpose                      | Lifecycle                     |
| ------------------- | ---------------------------- | ----------------------------- |
| `state.json`        | Phase tracking + transitions | Deleted before archive commit |
| `complete.json`     | Workflow completion (PHASE5) | Deleted before archive commit |
| `iterations.json`   | Iteration history            | Archived (never deleted)      |
| `decision-log.json` | Agent reasoning              | Archived (never deleted)      |

Note: After PHASE6 (Archive), historical files move to `openspec/changes/archive/YYYY-MM-DD-<change>/`. Transient files (state.json, complete.json, baseline) are deleted before the archive commit, leaving a clean git history. The `osx` lib tool automatically detects archived locations.

### Manual Invocation

```
/osx-phase0 my-change-name
@osx-analyzer  # hidden but accessible
```

---

## License

MIT License - see LICENSE file
