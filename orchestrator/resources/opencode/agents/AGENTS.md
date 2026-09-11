# Agents (OpenCode) — Orchestrator Side

OpenCode agent definitions, one file per agent. Consumed by the
orchestrator's phase dispatch. Phase 4 moved this directory under
`orchestrator/resources/opencode/agents/`. The skills side ships **no
agents** — Claude and OpenCode both use the orchestrator-side agents.

## Files

| File | Phases |
|------|--------|
| `osx-analyzer.md` | PHASE0 (read-only audit + routing) |
| `osx-builder.md` | PHASE1 (write code, run tests) |
| `osx-reviewer.md` | PHASE2, PHASE5 (verification + reflection; writes reports) |
| `osx-maintainer.md` | PHASE3, PHASE4, PHASE6 (docs, sync, archive) |

See `orchestrator/source/orchestrator/AGENTS.md` for the phase → agent mapping.

## Frontmatter

```yaml
---
description: <purpose>
hidden: true                   # Optional, hides from default picker
mode: subagent | all | primary # Optional
temperature: <0.0-1.0>         # Optional, lower = more deterministic
permission:                    # Optional
  read: allow | deny
  edit: allow | deny
  bash: allow | deny
  ...
---
```

## Conventions

- `osx-analyzer` is read-only (`edit: deny`); `osx-reviewer` writes verification reports / reflections (low temp); `osx-builder` and `osx-maintainer` may write freely.
- `mode: subagent` is the default for orchestrator-dispatched agents.
- Keep `temperature` low (≤0.2) for deterministic phase outcomes.

## See Also

- `orchestrator/resources/AGENTS.md` — Manifest format
- `orchestrator/source/orchestrator/AGENTS.md` — Phase → agent dispatch
- `research/opencode-docs.md` — OpenCode agent spec
