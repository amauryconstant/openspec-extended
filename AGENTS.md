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
| Version  | Python 3.12 or higher                 |

### Tooling Languages

- Project source (`source/`, `install.sh`, `openspec.spec`) is **Python**
  except where bash is more natural.
- `install.sh` is bash: it must run with no Python dependency when
  bootstrapping a fresh machine.
- All `mise` tasks are **bash**; the project content can be Python, but
  build/release/version tooling is bash + `jq`.

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

### Versioning

The tool version lives in three synchronized places:
- `source/__init__.py` — `__version__`
- `source/cli.py` — `SCRIPT_VERSION` (alias of `__version__`)
- `pyproject.toml` — `version`

`mise run version:update` is the **single source of truth** for these
three files. The `mise run release` task delegates to `version:update`
for source-file bumps. Per-resource versions in `resources/*/manifest.toml`
are bumped independently when skills, agents, or commands change.

### Testing

```bash
# Run all default tests (unit, integration, mechanism, including bats)
mise run test

# Run unit tests
pytest -m unit

# Run install.sh unit tests (bats, hermetic via local HTTP server)
mise run test:unit:bats

# Run integration tests
pytest -m integration

# Run mechanism tests (CLI validation, no AI calls)
pytest -m mechanism

# Run bats mechanism tests against the built binary (no AI calls)
mise run test:mechanism:bats

# Run e2e full workflow tests (requires built binary + E2E_CONFIRM=1)
E2E_CONFIRM=1 mise run test:e2e

# Run all checks
mise run verify
```

### E2E Test Strategy

The full workflow runs against the **built binary** (`dist/openspec-extended`).
There is no pytest equivalent because PyInstaller freeze changes runtime
behavior in ways that the source-only path can't reproduce.

- `tests/e2e/test_mechanism.py` — pytest, `@pytest.mark.mechanism`, runs by default. Tests CLI options without AI calls.
- `tests/e2e/mechanism.bats` — bats, runs by default. Same coverage as the pytest mechanism suite, executed against the built binary.
- `tests/e2e/full-workflow.bats` — bats, requires `E2E_CONFIRM=1`. Runs the full workflow end-to-end against the built binary.

The `test:mechanism:bats` and `test:e2e` mise tasks call `build` first so
the binary is always current.

---

## Project Structure

```
source/
├── __init__.py          # __version__
├── __main__.py          # Entry: python -m source
├── cli.py               # Typer CLI (install/update/orchestrate) + SCRIPT_VERSION
├── lib/
│   └── osx.py           # Change management (baseline, ctx, git, phase, state)
└── orchestrator/
    └── engine.py        # 7-phase autonomous workflow

install.sh              # Bash installer (downloads PyInstaller binary)
openspec.spec           # PyInstaller spec
pyproject.toml          # Project metadata + entry point

resources/
├── opencode/            # Skills, agents, commands
└── claude/              # Same structure for Claude Code

openspec-core/           # Official OpenSpec workflows (read-only)
research/                # Platform documentation
tests/                   # pytest + bats suite
.mise/tasks/             # sync-core, release, build-release, version/{check,update,lib/*} (all bash)
```

---

## Build & Release

```bash
# Build the binary (PyInstaller)
mise run build
# Output: dist/openspec-extended

# Build + package + upload to GitHub release
VERSION=v0.19.0 mise run build-release --skip-build   # if dist/ is current
VERSION=v0.19.0 mise run build-release                 # build, then upload
```

`build-release` produces a tarball named
`openspec-extended-v$VERSION-{platform}.tar.gz` containing `bin/openspec-extended`
plus a `SHA256SUMS` file, and uploads them to the matching GitHub release.

`install.sh` fetches this tarball from the release matching `VERSION` (or
`latest`/`main` if not pinned).

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
# Check what needs bumping (pre-commit hook)
mise run version:check

# Auto-bump versions in resources/*/manifest.toml, source/cli.py,
# source/__init__.py, and pyproject.toml
mise run version:update

# Cut a release: bump version everywhere, commit, tag, push
mise run release patch
```

`version:update` is the single source of truth for the three locked
version fields. It updates `source/cli.py` (canonical), then mirrors the
same version to `source/__init__.py` and `pyproject.toml`. The `release`
task shares the same helpers via `.mise/tasks/version/lib/bump.bash`,
so `README.md` is the only file the release task updates that
`version:update` does not.

---

## License

MIT License - see LICENSE file
