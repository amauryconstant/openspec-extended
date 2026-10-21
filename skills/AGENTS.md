---
paths:
  - "skills/**"
---

# Skills Side

Gap-filling utility skills and commands, separated from the orchestrator
side at Phase 4. Houses the review/commit/verify-tests skills and their
slash commands. Each tree has its own manifest; the two side manifests
are disjoint (locked by `tests/unit/test_resource_contract.py::TestManifestParity`).

## Layout

```
skills/resources/
├── AGENTS.md                       # (you are here)
├── canonical/                      # Canonical source (single, tool-neutral)
│   ├── manifest.toml               # Skills-side manifest
│   ├── skills/
│   │   ├── osx-commit/             # commit message skill
│   │   │   ├── SKILL.md
│   │   │   ├── references/         # detection.md, standards.md (skill-local)
│   │   │   └── scripts/            # detect-commit-style helper
│   │   ├── osx-review-artifacts/   # pre-implementation review
│   │   └── osx-verify-tests/       # post-implementation test compliance
│   └── commands/
│       ├── osx-review.md           # slash command for review
│       └── osx-verify-tests.md     # slash command for test compliance
```

A skill directory is copied whole by `deploy_skills` (`source/cli.py`), so
`references/` and `scripts/` ship alongside `SKILL.md`. Skill-local
`scripts/` entries are covered by `mise run version:check` — bump them with
the skill.

Phase 2A: only `canonical/` is on disk. The per-adapter Claude/Codex/Kimi/etc.
layouts are rendered at deploy time by `orchestrator/source/cli.py:deploy_*`,
driven by `orchestrator/source/tools.py:ToolAdapter`. There is no
hand-maintained `claude/` mirror.

## Skills in this tree

| Skill                          | Type   | Purpose                                                 |
| ------------------------------ | ------ | ------------------------------------------------------- |
| `osx-commit`                   | skill  | Write conventional commit messages                      |
| `osx-review-artifacts`         | skill  | Pre-implementation review (schema-agnostic contract)    |
| `osx-verify-tests`             | skill  | Post-implementation test compliance (mirrors openspec-verify-change shape) |
| `osx-review`                   | command| Slash command — runs review flow                        |
| `osx-verify-tests`             | command| Slash command — runs test compliance check              |

The three skills plus the two slash commands total 5 resources. The skills-side manifest declares all 5; the orchestrator-side manifest declares none of them.

## Cross-cutting rules

Cross-cutting rules live in [`.agents/rules/`](../../.agents/rules/) (linked from root `AGENTS.md`). The review contract reference pool lives at `orchestrator/resources/canonical/skills/references/`.

## Shared references

Skills in this tree may consume shared references from `orchestrator/resources/canonical/skills/references/` (cross-cutting pool, orchestrator-owned). Declare consumed files in the resource's own entry via `references = [...]` — there is no top-level `[resources.references]` table. See `orchestrator/resources/AGENTS.md` for the pool inventory and the two discovery paths (skills declare; commands are scraped from body prose).

## Authoring workflow

1. Create or edit the file under `skills/resources/canonical/{skills,commands}/osx-<name>/...` first.
2. Add the entry to `skills/resources/canonical/manifest.toml`.
3. Bump the version in the manifest.

## Adding a new gap-filling skill

1. Create `skills/resources/canonical/skills/osx-<name>/SKILL.md` with required frontmatter (`name`, `description`, `license`). Directory name MUST match `name:`.
2. Add an entry to `skills/resources/canonical/manifest.toml` under `[resources.skills]`, adding a `references = [...]` list to that entry if the skill consumes shared references.
3. Bump the version: `mise run version:update`.
4. Add a unit test in `tests/unit/test_required_skills.py` if the skill should be in `REQUIRED_SKILLS`.
5. If the skill introduces a new slash command, also create `skills/resources/canonical/commands/osx-<name>.md` and a `[resources.commands]` entry for it.

## Conventions

- New resources get an `osx-` prefix; never collide with `osc-*` (core) names.
- Edit `skills/resources/canonical/` only; per-adapter rendering is driven
  by `ToolAdapter` fields at deploy time.
- The two side manifests are disjoint — never register a skills-side resource in `orchestrator/resources/canonical/manifest.toml`.

## See also

- [`.agents/rules/resource-separation.md`](../../.agents/rules/resource-separation.md) — Phase 5 disjoint-manifest invariant + shared-references pool ownership.
