# Skills (OpenCode)

OpenCode skills: one directory per skill, `SKILL.md` as the entry point.

## Layout

```
skills/
└── <skill-name>/
    ├── SKILL.md              # Required: skill body + frontmatter
    ├── references/           # Optional: deeper reference docs
    └── scripts/              # Optional: helper scripts the skill may invoke
```

Example: `osx-concepts/SKILL.md` plus `osx-concepts/references/`.

## Frontmatter

```yaml
---
name: osx-<skill-name>          # Required, must match directory name
description: <one-line purpose> # Required
license: MIT                   # Required
---
```

## Naming Rules

| Rule | Constraint |
|------|------------|
| Length | 1–64 chars |
| Charset | `^[a-z0-9]+(-[a-z0-9]+)*$` |
| Prefix | `osx-` for extended skills; `osc-` reserved for core |
| Match | Directory name must equal the `name` field |

## Authoring Workflow

See root `AGENTS.md` "Adding New Skills" section for the full procedure. Briefly:

1. Create `resources/opencode/skills/osx-<name>/SKILL.md`.
2. Add the entry to `resources/opencode/manifest.toml`.
3. Mirror the skill under `resources/claude/skills/osx-<name>/` if Claude Code support is needed.
4. Bump the version in the manifest.

## Schema-Agnostic Contract for Review/Modify Skills

`osx-review-artifacts` and `osx-modify-artifacts` adopt the same six rules as core's `openspec-update-change`. Every skill, command, and orchestrator phase that handles pre-implementation review/modify must honor them:

1. **Schema source of truth** — read artifact ids, descriptions, and paths from `openspec status --change <name> --json` and `openspec instructions <id> --change <name> --json`. Never hardcode `proposal.md`/`specs/`/`design.md`/`tasks.md`.
2. **Glob safety** — write only to concrete files in `existingOutputPaths`. Never write to a glob `resolvedOutputPath` (it is still a pattern).
3. **Frontier discipline** — refuse to create new artifacts or new files under glob artifacts. Route missing-artifact cases to `/opsx:continue <name>`.
4. **No code edits** — refuse to touch implementation code. If a finding implies code changes, stop and point to `/opsx:apply <name>`.
5. **Per-edit confirmation** — show each proposed revision and write only after the user confirms. Rejected revisions are left unchanged.
6. **Severity calibration** — adopt the same rule as `openspec-verify-change`: when uncertain, prefer `Suggestion` over `Warning`, `Warning` over `Critical`. Implementation-readiness issues are never `Critical`.

Always carry the v1.6 store-selection paragraph at the top of skills and commands that read from or write to a change: `openspec store list --json` to discover registered stores; pass `--store <id>` on `new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`. Without a store, commands act on the nearest local `openspec/` root.

## See Also

- Root `AGENTS.md` — Adding New Skills
- `resources/AGENTS.md` — Manifest format, resource types
- `resources/opencode/AGENTS.md` — Platform overview
- `research/opencode-docs.md` — OpenCode skill spec
