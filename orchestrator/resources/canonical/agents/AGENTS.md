---
paths:
  - "orchestrator/resources/canonical/agents/**"
---

# Orchestrator Agents (`agents/`)

Orchestrator-dispatched sub-agents. Phases 1–6 write-state (read files, run
helpers, edit artifacts in the project repo). PHASE0's main agent
`osx-analyzer` is read-only; the engine may separately dispatch
`osx-editor` to reconcile findings the analyzer reported.

## Conventions

- **`hidden: true`** — every agent file carries this frontmatter
  field. It keeps the agent off the user-driven picker so the only
  way the agent is invoked is through the orchestrator's
  `RunRequest` flow or the auto-fix dispatch.
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
  - `osx-editor`: reconciles **existing** artifacts only when the
    engine auto-fixes an auto-fixable PHASE0 route. Never creates
    or implements artifacts.
  - `osx-builder`: writes code under the project root; commits per
    milestone; never edits OpenSpec planning artifacts in PHASE1.
  - `osx-maintainer`: edits docs (`AGENTS.md`, `CLAUDE.md`),
    syncs specs, archives completed changes.
  - `osx-reviewer`: writes verification reports and reflections,
    then commits.
- Temperature is low and deliberate, not uniform: `0.1` for the
  deterministic auditors (`osx-analyzer`, `osx-editor`,
  `osx-reviewer`), `0.3` for `osx-maintainer`, `0.4` for
  `osx-builder` (implementation benefits from some creativity).
- Each agent dispatches via the orchestrator's `RunRequest` flow —
  see `PHASE_AGENTS` in `orchestrator/source/orchestrator/engine.py`
  for phase dispatch and `AUTO_FIX_AGENTS` for auto-fix routes.
  Never invoke an agent directly.

## Files

| File                  | Purpose                                                   |
| --------------------- | --------------------------------------------------------- |
| `osx-analyzer.md`     | PHASE0 — read-only artifact review; emits routing reports |
| `osx-editor.md`       | PHASE0 auto-fix reconciler (`AUTO_FIX_AGENTS`)            |
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
