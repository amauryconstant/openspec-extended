# Skills (Claude Code)

Claude Code skills. Same directory layout as the OpenCode side; frontmatter is richer.

## Layout

```
skills/
└── <skill-name>/
    ├── SKILL.md              # Required: skill body + frontmatter
    ├── references/           # Optional: deeper reference docs
    └── scripts/              # Optional: helper scripts
```

## Frontmatter

Claude Code skills accept the full YAML frontmatter spec, including a `metadata` block:

```yaml
---
name: osx-<skill-name>
description: <one-line purpose>
license: MIT
metadata:
  audience: <who this is for>
  workflow: <when to load>
---
```

## Naming

Same rules as OpenCode (`osx-` prefix, lowercase-hyphenated, must match directory name). The 8 skills mirror their OpenCode counterparts.

## Authoring Workflow

1. Create or edit the skill under `resources/opencode/skills/osx-<name>/SKILL.md` first.
2. Mirror the body under `resources/claude/skills/osx-<name>/SKILL.md`.
3. Adapt the frontmatter for Claude Code's richer schema.
4. Add entries to both `resources/opencode/manifest.toml` and `resources/claude/manifest.toml`.

## Schema-Agnostic Contract for Review/Modify Skills

`osx-review-artifacts` and `osx-modify-artifacts` adopt the same six rules as core's `openspec-update-change`. Every skill, command, and orchestrator phase that handles pre-implementation review/modify must honor them:

1. **Schema source of truth** — read artifact ids, descriptions, and paths from `openspec status --change <name> --json` and `openspec instructions <id> --change <name> --json`. Never hardcode `proposal.md`/`specs/`/`design.md`/`tasks.md`. v1.7.0 status adds a `requires` array per artifact — prefer it over a separate `instructions` call when building the dependency graph.
2. **Glob safety** — write only to concrete files in `existingOutputPaths`. Never write to a glob `resolvedOutputPath` (it is still a pattern).
3. **Frontier discipline** — refuse to create new artifacts or new files under glob artifacts. Route missing-artifact cases to `/opsx:continue <name>` (Claude: `/opsx:continue`).
4. **No code edits** — refuse to touch implementation code. If a finding implies code changes, stop and point to `/opsx:apply <name>` (Claude: `/opsx:apply`).
5. **Per-edit confirmation** — show each proposed revision and write only after the user confirms. Rejected revisions are left unchanged.
6. **Severity calibration** — adopt the same rule as `openspec-verify-change`: when uncertain, prefer `Suggestion` over `Warning`, `Warning` over `Critical`. Implementation-readiness issues are never `Critical`.

Always carry the v1.7.0 store-selection paragraph at the top of skills and commands that read from or write to a change: `openspec store list --json` to discover registered stores; pass `--store <id>` on `new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`. Without a store, commands act on the nearest local `openspec/` root. v1.7.0 layers `openspec config set defaultStore <id>` on top as a machine-level fallback (status `root.source` reports `global_default` when used).

v1.7.0 also adds `openspec instructions archive` as a read-only mirror of the proposal/apply variants — pass `--change <name>` and `--store <id>` like the apply/proposal forms. Use it for archive-readiness pre-checks (or as a defensive fallback when an envelope is missing).
v1.7.0 also exposes `operations.apply.guidance` and `operations.archive.guidance` in `openspec/config.yaml` — per-operation text surfaced through the `instructions` surface. Mention these as escape hatches when project-specific guidance is needed.

## See Also

- `resources/claude/AGENTS.md` — Platform differences
- `resources/opencode/skills/AGENTS.md` — Sibling layout (treat as canonical)
- `resources/AGENTS.md` — Manifest format
- Root `AGENTS.md` — Adding New Skills
