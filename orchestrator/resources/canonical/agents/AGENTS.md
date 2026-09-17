---
paths:
  - "orchestrator/resources/canonical/agents/**"
---

# Orchestrator Agents (`agents/`)

Orchestrator-dispatched sub-agents. Phase 0 read-only; Phases 1–6
write-state (read files, run helpers, edit artifacts in the
project repo).

## Conventions

- **`hidden: true`** — every agent file carries this frontmatter
  field. It keeps the agent off the user-driven picker so the only
  way the agent is invoked is through the orchestrator's
  `RunRequest` flow. Sub-agents also omit a `description` lede that
  would otherwise invite manual invocation.
- **`mode:` left unset** — orchestrator-dispatched agents must NOT
  declare `mode: subagent`. The orchestrator invokes them through
  `opencode run --agent <name>` (see
  `orchestrator/source/orchestrator/runner.py`); the runtime rejects
  subagent dispatch via that flag and silently falls back to the
  default primary agent, which drops the per-phase `permission:`
  block (PHASE0's read-only `edit: deny` would be lost). `mode:`
  matters only when a primary agent wants to spawn the target via
  the Task tool, which the orchestrator does not do today.
- Permissions follow a per-agent allowlist:
  - `osx-analyzer`: read-only across the board (`edit: deny`);
    never edits files; emits routing reports.
  - `osx-builder`: writes code under the project root; commits per
    milestone; never edits OpenSpec planning artifacts in PHASE1.
  - `osx-maintainer`: edits docs (`AGENTS.md`, `CLAUDE.md`),
    syncs specs, archives completed changes.
  - `osx-reviewer`: writes verification reports and reflections,
    then commits.
- Temperature is low (0.1) for deterministic behaviour. Higher
  creativity would defeat the audit purpose.
- Each agent dispatches via the orchestrator's `RunRequest` flow —
  see `orchestrator/source/orchestrator/engine.py` for the
  `PHASE_AGENTS` mapping. Never invoke an agent directly.

## Files

| File                  | Purpose                                                   |
| --------------------- | --------------------------------------------------------- |
| `osx-analyzer.md`     | PHASE0 — read-only artifact review; emits routing reports |
| `osx-builder.md`      | PHASE1 — implement `tasks.md`; milestone commits          |
| `osx-maintainer.md`   | PHASE3 / PHASE4 / PHASE6 — docs, sync, archive            |
| `osx-reviewer.md`     | PHASE2 / PHASE5 — write reports; commit                   |
| `AGENTS.md`           | (this file) — conventions                                |

## Per-adapter behaviour

Every adapter's `ToolAdapter` declares whether its target tree ships
an `agents/` directory (`has_agents_dir` field). Adapters that don't
expose an on-disk agent dispatch model (Claude Code, Cursor, Codex,
Kimi — they use a session model instead) set `has_agents_dir=False`;
`validate_deployment` skips agent validation for those targets. The
orchestrator's `RunRequest` flow looks for the CLI binary and skill
definitions instead, per the tool's session model.
