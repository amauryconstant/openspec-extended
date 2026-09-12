# OpenSpec Core Skills

**Source**: Official OpenSpec workflow skills - track upstream, do not modify locally.

**Version**: v1.13.0 (custom profile with all 12 workflows)

**v1.13.0 highlights** (current):

- `openspec instructions apply` now reports the full build-order chain via a `missingPrerequisites` array on the `--json` envelope, not just the first hop. The text remedies name `openspec instructions <artifact> --change <name>` commands rather than the `openspec-continue-change` skill (which the `core` profile never installs). A change with no delta specs (and no `skip_specs: true`) is reported as a warning at apply time.
- `openspec list --specs` is now a first-class spec-inventory command (parallel to `openspec list` for changes); `openspec show <id> --type spec --json --no-scenarios` is the filtered read used by generated guidance. The explore skill/command list the spec inventory alongside the change list and say which is which.
- `openspec archive` no longer rewrites the inside of fenced code blocks — blank-line collapsing now runs through a fence mask (`buildCodeFenceMask`), so YAML block scalars, Python samples, and Markdown-inside-Markdown keep their internal whitespace.
- REMOVED/RENAMED delta sections accept `*` or `+` as bullet markers, not just `-`. Duplicate section titles (`## ADDED Requirements` written twice, or beside `## Added Requirements`) now read every body, not just the first.
- `openspec proposal` planning loads project context first, honoring config precedence and validation limits; when no root exists it stops without writing files and offers initialization.
- `openspec init` and `openspec update` name the workflows your profile left out and how to add them, so a missing workflow no longer reads as a broken setup.
- `retire_capabilities: true` no longer refuses specs whose scenario bullets wrap onto a second line, nor specs whose scenarios use `+`-marker bullets.
- `openspec update` also compares command-file content (in addition to the skill-file `generatedBy` marker) when checking whether a tool is up to date.

---

## Purpose

This directory contains the official OpenSpec workflow skills for AI coding assistants. These skills implement the OpenSpec change management workflow.

**Do NOT modify these files.** Update only via `mise run sync-core`.

---

## Skills Reference (12 Workflows)

| Skill                          | Command            | Description                                                       |
| ------------------------------ | ------------------ | ----------------------------------------------------------------- |
| `openspec-propose`             | `/opsx:propose`    | Create change + all artifacts in one step                         |
| `openspec-explore`             | `/opsx:explore`    | Think through problems without code changes                       |
| `openspec-new-change`          | `/opsx:new`        | Start a new change with artifact workflow                         |
| `openspec-continue-change`     | `/opsx:continue`   | Continue working on an existing change                            |
| `openspec-apply-change`        | `/opsx:apply`      | Implement tasks from a change                                     |
| `openspec-update-change`       | `/opsx:update`     | Revise existing planning artifacts and reconcile them             |
| `openspec-ff-change`           | `/opsx:ff`         | Fast-forward: create all artifacts at once                        |
| `openspec-verify-change`       | `/opsx:verify`     | Verify implementation matches artifacts                            |
| `openspec-sync-specs`          | `/opsx:sync`       | Sync specs with implementation state                               |
| `openspec-archive-change`      | `/opsx:archive`    | Archive a completed change                                         |
| `openspec-bulk-archive-change` | `/opsx:bulk-archive` | Archive multiple changes at once                                  |
| `openspec-onboard`             | `/opsx:onboard`    | Guided tutorial for first-time OpenSpec users                     |

---

## Sync Strategy

To update these skills from upstream OpenSpec, run:

```bash
mise run sync-core
```

The `source/` subtree tracks upstream directly. This will:

1. Discover the latest stable release tag (e.g., `v1.13.0`) via `git ls-remote --tags`
2. `git subtree pull` from that tag into `source/` (squashed)
3. Build the CLI in-place from `source/`
4. Configure custom profile with all 12 workflows
5. Generate `.claude` and `.opencode` files via `openspec init --tools claude,opencode --profile custom`
6. Copy generated files into this directory

**Upstream**: <https://github.com/Fission-AI/OpenSpec>

Per-contract operational notes for v1.8.0+ orchestrator consumption (`isPlanningComplete`, `retire_capabilities`, `operations.{apply|archive}.guidance`, `show --diff`, `validate --archived`) live in [docs/review-modify-integration.md §13](../../docs/review-modify-integration.md#13-post-v170-contract-additions).
