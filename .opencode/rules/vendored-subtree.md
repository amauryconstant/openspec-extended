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
- Per-contract operational notes for v1.8.0+ orchestrator consumption also live in `docs/review-modify-integration.md §13`.

## What gets synced

The `source/` subtree tracks upstream directly. `sync-core`:

1. Discovers the latest stable release tag via `git ls-remote --tags`
2. `git subtree pull` from that tag into `source/` (squashed)
3. Builds the CLI in-place from `source/`
4. Configures the custom profile with all 12 workflows
5. Generates `.claude` and `.opencode` files via `openspec init --tools claude,opencode --profile custom`
6. Copies generated files into `orchestrator/core/`

Upstream: `https://github.com/Fission-AI/OpenSpec`.
