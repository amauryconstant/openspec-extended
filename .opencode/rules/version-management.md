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

**CHANGELOG prerequisite.** Before `mise run release` will commit and
tag, `CHANGELOG.md` must contain at least one entry for the upcoming
version — either a populated `## [Unreleased]` section (the release
script will rename it to `## [<X.Y.Z>] - <date>` on tag) or a
pre-existing `## [<X.Y.Z>] - <date>` section (the maintainer
hand-curated it). The check is a hard gate that runs before any file
mutations, so a failed gate leaves the working tree clean. Use
`--skip-changelog-check` to bypass (hotfix only). The gate helper is
`check_changelog_for_release`, and the post-tag rewrite that produces
the canonical layout is `apply_unreleased_rename`; both live in
`.mise/tasks/version/lib/bump.sh`.

The release script enforces the canonical post-tag form itself — an
empty `## [Unreleased]` header followed by `## [<X.Y.Z>] - <date>`
stamped with today's UTC date — regardless of which input form the
maintainer chose. The rewrite is idempotent and a no-op when the file
is already canonical, so re-running on top of a hand-curated entry is
safe.

The orchestrator-side `/osx-changelog` skill is shipped to **CLI
consumers** to generate their own `CHANGELOG.md` from archived
OpenSpec changes; it is not used to manage this repo's CHANGELOG.

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
