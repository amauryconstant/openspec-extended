# Claude Skills (`skills/`)

Auto-generated Claude mirror of the OpenCode canonical skills. The
mirror is produced by `mise run sync:mirrors` from
`orchestrator/resources/opencode/` (and `skills/resources/opencode/`
for the skills side). Do not edit the files in this subtree by hand
— every Claude file carries an `# AUTO-GENERATED` header that the
script injects and the pre-commit `sync-mirrors-check` hook guards.

## Skill count on Claude

The Claude side ships **more skill directories** than the OpenCode
canonical, even though both trees deploy the same set of orchestrator
skills. The drift is intentional and stems from Claude Code's
**dual-emit** strategy (introduced in OpenSpec v1.7.0, current as of
v1.13.0):

- OpenCode ships a skill `S` at `<target>/skills/S/SKILL.md`.
- Claude dual-emits:
  1. The legacy `<target>/commands/osx/<id>.md` (slash commands
     resolved through Claude Code's commands surface).
  2. A modern `<target>/skills/<name>/SKILL.md` (slash commands
     resolved through Claude Code's skills surface).

Slash commands `osx-phase0` through `osx-phase6`, `osx-changelog`,
and `osx-maintain-docs` are emitted as **skill directories** on
Claude (the modern form), so this `skills/` subtree carries a
directory for every slash command the orchestrator dispatches —
not just the canonical skills declared in
`tests/unit/test_skill_taxonomy.py::CANONICAL_SKILL_NAMES`.

The `dual-emit` rationale is documented upstream in
`.opencode/rules/mirror-generation.md` and the Claude Code docs on
slash-command resolution.

## Layout

```
orchestrator/resources/claude/skills/
├── AGENTS.md                # (you are here)
├── osx-workflow/            # orchestrator-side skill (mirrored)
│   └── SKILL.md
├── osx-changelog/           # dual-emit of commands/osx-changelog.md
│   └── SKILL.md
├── osx-maintain-docs/       # dual-emit of commands/osx-maintain-docs.md
│   └── SKILL.md
├── osx-phase0/              # dual-emit of commands/osx-phase0.md
│   └── SKILL.md
├── osx-phase1/              # ...
│   └── SKILL.md
├── osx-phase2/  / SKILL.md
├── osx-phase3/  / SKILL.md
├── osx-phase4/  / SKILL.md
├── osx-phase5/  / SKILL.md
├── osx-phase6/  / SKILL.md
└── references/              # shared cross-cutting references
```

The same dual-emit applies on the **skills side** at
`skills/resources/claude/skills/`.

## What is and is not here

- **Present**: every slash command that the extended orchestrator
  dispatches, via its modern Claude form.
- **Absent**: agents/ — Claude Code has no on-disk agent dispatch
  model, so the opencode `agents/osx-*.md` files have no Claude
  mirror. The orchestrator's `validate_deployment` honours this
  absence (`has_agents_dir=False` on the Claude adapter in
  `orchestrator/source/tools.py`).

## Regeneration

Run `mise run sync:mirrors` after editing the opencode canonical.
CI runs `mise run sync-mirrors --check` and refuses to land
if the mirror has drifted.
