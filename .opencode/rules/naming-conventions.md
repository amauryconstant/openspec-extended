---
paths:
  - "orchestrator/resources/opencode/**"
  - "orchestrator/resources/claude/**"
  - "skills/resources/opencode/**"
  - "skills/resources/claude/**"
---

# Naming Conventions

| Resource     | Core (upstream) | Extended (local)    |
| ------------ | --------------- | ------------------- |
| **CLI**      | `openspec`      | `openspec-extended` |
| **Commands** | `/osc-*`        | `/osx-*`            |
| **Skills**   | `osc-*`         | `osx-*`             |
| **Agents**   | n/a             | `osx-*`             |

**Skill name regex**: `^[a-z0-9]+(-[a-z0-9]+)*$`, 1–64 chars, lowercase with hyphens.

- Skill directory name MUST match frontmatter `name:` field.
- `osx-` prefix for extended skills; `osc-` reserved for core OpenSpec skills.
- Two disjoint resource trees: orchestrator-side (`orchestrator/resources/`) and skills-side (`skills/resources/`). Each tree has its own `manifest.toml`; never cross-register.
- Slash command name = skill directory name (e.g. `osx-phase0` → `/osx-phase0`).
- `osx-concepts §2.5` enumerates the canonical taxonomy (workflow skill, agents, phase commands, gap-filling skills, slash commands with self-contained bodies).
