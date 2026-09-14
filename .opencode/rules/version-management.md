---
paths:
  - "**/manifest.toml"
  - "install.sh"
---

# Version Management

Two distinct version domains, owned by separate tasks. Never mix them.

## Project version (one bump per release)

Command: `mise run release <patch|minor|major>`

Files updated in lockstep:

- `orchestrator/source/__init__.py` — `__version__`
- `pyproject.toml` — `[project] version`
- `README.md` — version badge + install example
- `uv.lock` — synced after `pyproject.toml` bump
- git tag (`vX.Y.Z`)

Run from `main` (override with `RELEASE_ALLOW_BRANCH=true`).

## Framework components (per-resource bumps)

Commands: `mise run version:check` → `mise run version:update`

Files updated:

- `orchestrator/resources/canonical/manifest.toml`
- `skills/resources/canonical/manifest.toml`
- `install.sh` (independent installer version cycle)

`version:check` runs as pre-commit hook and gates staged changes to `manifest.toml` and `install.sh`.

## Rules

- **NEVER** edit `__version__` or `[project] version` by hand — owned by `release`.
- `version:check` is wired into `.pre-commit-config.yaml`.
- `mise run verify` runs version gates together with `typecheck`,
  `format`, `lint`, and `test`.
