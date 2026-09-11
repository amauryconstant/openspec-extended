# OpenCode Platform Resources (Orchestrator Side)

Resources for the OpenCode AI coding assistant. Phase 4 moved this tree
under `orchestrator/resources/opencode/` (alongside the orchestration
engine source). The mirror lives at `orchestrator/resources/claude/`.
The skills side has a parallel tree under `skills/resources/{opencode,claude}/`.

## Layout

```
orchestrator/resources/opencode/
├── manifest.toml            # single unified manifest (split happens in Phase 5)
├── skills/                  # osx-* skills, one directory per skill
│   ├── osx-workflow/        # 7-phase orchestrator workflow skill
│   └── references/          # Shared references pool (cross-cutting)
├── agents/                  # osx-*.md agent files (orchestrator-dispatched)
└── commands/                # osx-*.md slash command files
```

## Platform Conventions

- Command files use the OpenCode frontmatter: `description` and (for autonomous
  phase commands) `agent: <sub-agent-name>`. The `agent:` field is OpenCode-only;
  the Claude mirror drops it.
- Commands are flat files named `osx-<command>.md` (no subdirectory).
- Skill directories follow `<name>/SKILL.md` with optional `references/` and `scripts/`.
- Agents use OpenCode-specific frontmatter including `mode`, `temperature`, and `permission` blocks.

## Naming

All extended resources use the `osx-` prefix. The skills, agents, and commands that drive the 7-phase orchestrator live here; gap-filling skills (review, commit, verify-tests) live on the skills side at `skills/resources/opencode/`. The combined manifest is at `orchestrator/resources/opencode/manifest.toml`.

## Claude Mirror Note

The Claude mirror at `orchestrator/resources/claude/` dual-emits every opencode command: the legacy `.claude/commands/osx/<name>.md` form is preserved for back-compat, and the modern `.claude/skills/osx-<name>/SKILL.md` form is also produced. This mirrors upstream OpenSpec v1.7.0's own dual-emit on Claude (see `orchestrator/resources/claude/AGENTS.md` for the rationale). OpenCode itself is single-emit (commands only); the `syncing` between the two trees is handled by `.mise/tasks/sync-mirrors`.

## See Also

- `orchestrator/resources/AGENTS.md` — Resource types, manifest format
- `orchestrator/resources/opencode/skills/AGENTS.md` — Skill directory layout
- `orchestrator/resources/opencode/agents/AGENTS.md` — Agent files
- `orchestrator/resources/opencode/commands/AGENTS.md` — Command files
- `orchestrator/resources/claude/AGENTS.md` — Sibling platform + dual-emit rationale
- `skills/resources/opencode/AGENTS.md` (TBD) — Skills-side platform docs
- `research/opencode-docs.md` — Platform capability reference
