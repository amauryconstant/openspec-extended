---
paths:
  - "orchestrator/core/**"
---

# Vendored Subtree (Read-Only)

`orchestrator/core/` is a vendored copy of upstream OpenSpec, synced via subtree pull.

## Rules

- **NEVER** edit files in `orchestrator/core/` directly. Use `mise run sync-core`.
- `sync-core` refuses to run if `orchestrator/core/source/` has uncommitted local changes.
- The current upstream version and per-version contract notes live in `orchestrator/core/AGENTS.md`.
- Per-contract operational notes for v1.8.0+ orchestrator consumption also live in `.opencode/rules/openspec-contract.md`.

## What gets synced

The `source/` subtree tracks upstream directly. `sync-core`:

1. Discovers the latest stable release tag via `git ls-remote --tags`
2. Force-replaces `orchestrator/core/source/` with upstream's tree at that tag (no 3-way merge — see "Why force-replace" below)
3. Builds the CLI in-place from `source/`
4. Configures the custom profile with all 12 workflows
5. Generates `.claude` and `.opencode` files via `openspec init --tools claude,opencode --profile custom`
6. Copies generated files into `orchestrator/core/`

### Why force-replace, not `git subtree pull`

`git subtree pull --squash` does a 3-way merge between (a) the squash annotation's `git-subtree-split:` SHA, (b) the current local tree at the prefix, and (c) the new upstream tag's tree. The split SHA is locked at the time of the original `subtree add` and cannot be retroactively corrected, so the bookkeeping always drifts relative to the on-disk content. Result: every pull after the first relocates produces spurious merge conflicts even though `orchestrator/core/source/` has zero local edits.

The script's force-update path (`git rm -rf $PREFIX` → `git read-tree --prefix=$PREFIX -u <upstream-tree>` → manual squash commit) honors the read-only mirror invariant and writes a correct `git-subtree-split:` annotation into the new commit so future runs don't accumulate the same drift.

Upstream: `https://github.com/Fission-AI/OpenSpec`.
