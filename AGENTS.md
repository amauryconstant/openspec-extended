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

Two distinct version domains, owned by separate tasks:

**Project version** (owned by `mise run release`):
- `source/__init__.py` — `__version__`
- `pyproject.toml` — `version`
- `README.md` — version badge + install example
- `uv.lock` — synced after `pyproject.toml` bump
- git tag (`vX.Y.Z`)

The new version is computed from the latest tag + bump type, written to all
files in lockstep, then committed and tagged. Run from `main` (override
with `RELEASE_ALLOW_BRANCH=true`).

**Framework components** (owned by `mise run version:check` / `version:update`):
- Per-resource versions in `resources/*/manifest.toml` (skills, commands, agents)
- `install.sh` — independent installer version cycle (separate from project version)

`version:check` is wired as a pre-commit hook (`.pre-commit-config.yaml`)
and gates staged changes to resource files and `install.sh`. `version:update`
applies the bumps detected by `version:check`.

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
├── cli.py               # Typer CLI (install/update/orchestrate)
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
.mise/tasks/             # sync-core, release, version/{check,update,lib/*} (all bash)
```

---

## Build & Release

```bash
# Build the binary locally (PyInstaller)
mise run build
# Output: dist/openspec-extended

# Cut a release (from main, no API tokens needed locally)
mise run release patch
# → bumps versions, commits, tags, pushes the tag
# → GitHub Actions then builds + uploads the platform tarballs
```

Releases are published by the `.github/workflows/release.yml` workflow on
`vX.Y.Z` tag push. The workflow matrix builds `linux-x86_64`,
`linux-arm64`, and `darwin-arm64`, packages each binary
into `openspec-extended-v$VERSION-{platform}.tar.gz` (with a `bin/openspec-extended`
layout), combines per-platform `SHA256SUMS` into a single file, and
uploads everything to the matching GitHub release.

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

Two flows, separate concerns:

```bash
# Project release (bumps source/__init__.py, pyproject.toml,
# README.md, uv.lock, git tag)
mise run release patch

# Framework component bumps (bumps resources/*/manifest.toml entries + install.sh)
mise run version:check       # reports what needs bumping
mise run version:update      # applies the bumps
```

Do not edit `__version__` / `[project] version` by hand —
those files are owned by `mise run release` and are intentionally outside
the scope of `version:check`/`version:update`.

---

## License

MIT License - see LICENSE file
