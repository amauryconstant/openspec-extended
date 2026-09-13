# Skills Side

Gap-filling utility skills and commands, separated from the orchestrator
side at Phase 4. Houses the review/commit/verify-tests skills and their
slash commands. Each tree has its own manifest; the two side manifests
are disjoint (locked by `tests/unit/test_resource_contract.py::TestManifestParity`).

## Layout

```
skills/resources/
├── AGENTS.md                       # (you are here)
├── opencode/                       # OpenCode platform (canonical, single source)
│   ├── manifest.toml               # Skills-side manifest
│   ├── skills/
│   │   ├── osx-commit/             # commit message skill
│   │   ├── osx-review-artifacts/   # pre-implementation review
│   │   └── osx-review-test-compliance/  # test compliance scoring
│   └── commands/
│       ├── osx-review.md           # slash command for review
│       └── osx-verify-tests.md     # slash command for test compliance
```

Phase 2A: only `opencode/` is on disk. The per-adapter Claude/Codex/Kimi/etc.
layouts are rendered at deploy time by `orchestrator/source/cli.py:deploy_*`,
driven by `orchestrator/source/tools.py:ToolAdapter`. There is no
hand-maintained `claude/` mirror.

## Skills in this tree

| Skill                          | Type   | Purpose                                                 |
| ------------------------------ | ------ | ------------------------------------------------------- |
| `osx-commit`                   | skill  | Write conventional commit messages                      |
| `osx-review-artifacts`         | skill  | Pre-implementation review (schema-agnostic contract)    |
| `osx-review-test-compliance`   | skill  | Test compliance scoring (`scoring-rubric.md`)           |
| `osx-review`                   | command| Slash command — runs review flow                        |
| `osx-verify-tests`             | command| Slash command — runs test compliance check              |

The three skills plus the two slash commands total 5 resources. The skills-side manifest declares all 5; the orchestrator-side manifest declares none of them.

## Cross-cutting rules

| Concern | Where the rules live |
|---|---|
| Naming (`osx-`/`osc-` prefixes) | `.opencode/rules/naming-conventions.md` |
| Per-adapter rendering (deploy-time token substitution + skill mirror) | `.opencode/rules/per-adapter-rendering.md` |
| Per-resource version bumps | `.opencode/rules/version-management.md` |
| Review contract (`schema-agnostic-contract.md`, `store-selection.md`) | `orchestrator/resources/opencode/skills/references/` |

## Shared references

Skills in this tree may consume shared references from `orchestrator/resources/opencode/skills/references/` (cross-cutting pool). Declare consumed files via the manifest's `references = [...]` list.

## Authoring workflow

1. Create or edit the file under `skills/resources/opencode/{skills,commands}/osx-<name>/...` first.
2. Add the entry to `skills/resources/opencode/manifest.toml`.
3. Bump the version in the manifest.

## Conventions

- New resources get an `osx-` prefix; never collide with `osc-*` (core) names.
- Edit `skills/resources/opencode/` only; per-adapter rendering is driven
  by `ToolAdapter` fields at deploy time.
- The two side manifests are disjoint — never register a skills-side resource in `orchestrator/resources/opencode/manifest.toml`.
