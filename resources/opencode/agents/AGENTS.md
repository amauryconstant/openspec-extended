# Agents (OpenCode)

OpenCode agent definitions, one file per agent. Consumed by the orchestrator's phase dispatch.

## Files

| File | Phases |
|------|--------|
| `osx-analyzer.md` | PHASE0, PHASE2, PHASE5 (read-only, critical review) |
| `osx-builder.md` | PHASE1 (write code, run tests) |
| `osx-maintainer.md` | PHASE3, PHASE4, PHASE6 (docs, sync, archive) |

See `source/orchestrator/AGENTS.md` for the phase → agent mapping.

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

- `osx-analyzer` is read-only (`edit: deny`); the other agents may write.
- `mode: subagent` is the default for orchestrator-dispatched agents.
- Keep `temperature` low (≤0.2) for deterministic phase outcomes.

## See Also

- `resources/AGENTS.md` — Manifest format
- `source/orchestrator/AGENTS.md` — Phase → agent dispatch
- `research/opencode-docs.md` — OpenCode agent spec
