# OpenSpec-extended - OpenCode Reference

## Project Context & Philosophy

**Purpose**: Bridge AI coding assistants with OpenSpec - spec-driven development framework.

**Core Philosophy**: Agree on WHAT to build before writing code. Artifacts live in repository, not tool-specific systems.

**Project Scope**: This is a rough, minimal project. No deep infrastructure, CI, or complex install scripts needed.

**Extension Skills** (see `openspec-core/AGENTS.md` for core workflow skills):
- `openspec-concepts`: Teaches AI agents about OpenSpec framework
- `openspec-modify-artifact`: Modifies OpenSpec artifacts with dependency tracking
- `openspec-review-artifact`: Reviews OpenSpec artifacts for quality, completeness, and consistency
- `openspec-maintain-ai-docs`: Maintain AGENTS.md and CLAUDE.md documentation to keep synchronized with available skills
- `openspec-generate-changelog`: Generate changelogs in Keep a Changelog format from archived changes
- `openspec-review-test-compliance`: Review test coverage for OpenSpec changes, ensuring spec requirements have corresponding tests

**Research Maintenance**: Use `update-research` skill to maintain `research/` documentation (accuracy, structure, consistency).

**Resource Creation**: See `research/claude-code-docs.md` for Claude Code specifics, `research/opencode-docs.md` for OpenCode.

---

Minimal shell script utility extending OpenSpec with custom skills.

**Purpose**: Install/update OpenSpec skills via `openspecx <install|update> <tool>`

**Location**: `/home/amaury/Projects/OpenSpec-extended`

---

## Quick Reference

| Command | Purpose |
|----------|----------|
| `openspecx install claude` | Add missing skills to `.claude/skills/` |
| `openspecx install opencode` | Add missing skills to `.opencode/skills/` |
| `openspecx update claude` | Force update all skills in `.claude/skills/` |
| `openspecx update opencode` | Force update all skills in `.opencode/skills/` |

---

## Running / Testing

**No automated tests** - manual testing only.

```bash
./bin/openspecx install claude
./bin/openspecx install opencode

# Verify
ls .claude/skills/
ls .opencode/skills/
```

---

## Code Style

### Bash Requirements

**Header**: Always use `#!/bin/bash` (Bash 4.0+)

**Strict Mode**: `set -euo pipefail` at top of all scripts

### Variables

**Constants**: `readonly UPPER_CASE`
```bash
readonly VERSION="0.1.0"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
```

**Local variables**: `snake_case`
```bash
tool_name="claude"
target_dir="$SCRIPT_DIR/../resources"
```

**Always quote**: `"$VAR"` not `$VAR`

### Key Patterns

```bash
# Associative arrays
declare -A TOOL_DIRS=(["claude"]=".claude/skills" ["opencode"]=".opencode/skills")

# Logging (colors)
readonly COLOR_GREEN='\033[0;32m' COLOR_RED='\033[0;31m' COLOR_RESET='\033[0m'
log_success() { echo -e "${COLOR_GREEN}✓${COLOR_RESET} $*"; }
log_error() { echo -e "${COLOR_RED}✗${COLOR_RESET} $*" >&2; }

# Conditionals
if [[ $# -eq 0 ]]; then log_error "Usage: ..."; exit 1; fi
if [[ -z "${TOOL_DIRS[$TOOL]:-}" ]]; then log_error "Unknown tool: $TOOL"; exit 1; fi

# Directory operations
mkdir -p "$FULL_PATH"
cp -r "$SOURCE_DIR"/* "$TARGET_DIR/"
SOURCE_COUNT=$(find "$DIR" -mindepth 1 -maxdepth 1 -type d | wc -l)

# Error handling: exit 1 (error), exit 0 (success), messages to >&2
```

### Naming

| Type | Format | Examples |
|-------|---------|-----------|
| Constants | UPPER_CASE | `VERSION`, `SCRIPT_DIR` |
| Variables | snake_case | `tool_name`, `source_count` |
| Functions | snake_case() | `log_success()`, `log_error()` |
| Arrays | UPPER_CASE | `TOOL_DIRS` |

### Script Structure

1. Shebang + description/usage comment
2. `set -euo pipefail`
3. readonly constants
4. Logging functions
5. Argument validation
6. Main logic
7. Exit codes only on errors

---

## Project Structure

```
bin/openspecx              # Main executable
openspec-core/             # Official OpenSpec workflow skills (read-only)
  ├── .claude/             # Claude Code commands + skills
  └── .opencode/           # OpenCode commands + skills
resources/                 # Extended utility skills (maintained here)
  ├── claude/skills/       # Claude Code extension skills
  └── opencode/skills/     # OpenCode extension skills
research/                  # Platform documentation
```

**Key Distinction**:
- `openspec-core/` - Official OpenSpec workflows, sync from upstream only
- `resources/` - Extended skills, maintained locally

---

## Adding New Skills

Create `resources/<tool>/skills/<skill-name>/SKILL.md`:

```bash
mkdir -p resources/claude/skills/my-skill
cat > resources/claude/skills/my-skill/SKILL.md << 'EOF'
---
name: my-skill
description: Brief description
license: MIT
---

# Your Skill Instructions
EOF
```

**Required frontmatter**: `---` delimiters, `name`, `description`, `license`

**Naming constraints** (from research/):
- 1-64 chars, lowercase with hyphens only
- Regex: `^[a-z0-9]+(-[a-z0-9]+)*$`
- No consecutive `--`, cannot start/end with `-`
- Must match directory name

**Platform differences**: See research/claude-code-docs.md and research/opencode-docs.md for field variations

---

## Platform-Specific Details

**Claude Code Skills**: research/claude-code-docs.md:20-78
**OpenCode Skills**: research/opencode-docs.md:75-129
**Skill Discovery Paths**: research/opencode-docs.md:79-85

---

## License

MIT License - see LICENSE file
