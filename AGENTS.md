# OpenSpec-extended - OpenCode Reference

## Project Context

**Purpose**: Bridge AI coding assistants with OpenSpec - spec-driven development framework.

**Philosophy**: Agree on WHAT to build before writing code. Artifacts live in repository, not tool-specific systems.

**Scope**: Minimal project - no deep infrastructure, CI, or complex install scripts.

---

## Naming Convention

| Resource        | Core (upstream) | Extended (local)    |
| --------------- | --------------- | ------------------- |
| **CLI**         | `openspec`      | `openspec-extended` |
| **Commands**    | `/osc-*`        | `/osx-*`            |
| **Skills**      | `osc-*`         | `osx-*`             |
| **Agents**      | N/A             | `osx-*`             |
| **Lib scripts** | N/A             | `osx`               |

**Extension Skills** (core skills tracked in `openspec-core/AGENTS.md`)

---

## Code Style

### Python Requirements

| Rule     | Format                                |
| -------- | ------------------------------------- |
| Style    | PEP 8 + ruff formatting               |
| Imports  | Standard library, typer, rich, toml   |
| Testing  | pytest with markers (unit/integration/mechanism/e2e) |

### Key Patterns

```python
# Typer CLI (source/cli.py)
from typer import Typer
app = Typer()

# State management via toml (source/lib/osx.py)
import toml
from pathlib import Path

# Rich console output
from rich.console import Console
console = Console()
```

### Testing

```bash
# Run unit tests
pytest -m unit

# Run integration tests
pytest -m integration

# E2E tests (requires AI calls)
E2E_CONFIRM=1 pytest -m e2e

# Run with verbose output
pytest -v
```

---

## Project Structure

```
source/
├── __init__.py          # Version: 0.18.2
├── __main__.py          # Entry: python -m source
├── cli.py               # Typer CLI (install/update/orchestrate/run)
├── lib/
│   └── osx.py           # Change management (baseline, ctx, git, phase, state)
└── orchestrator/
    └── engine.py        # 7-phase autonomous workflow

bin/                     # Empty (was Bash CLI, now in source/)

resources/
├── opencode/            # Skills, agents, commands, scripts
└── claude/              # Same structure for Claude Code

openspec-core/           # Official OpenSpec workflows (read-only)
research/                # Platform documentation
tests/                   # pytest suite (unit/integration/e2e)
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

## Version Bumping

```bash
mise run version
```

Updates version in `source/__init__.py` and `pyproject.toml`.

---

## License

MIT License - see LICENSE file
