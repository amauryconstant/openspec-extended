# Orchestrator Agents (`agents/`)

Orchestrator-dispatched sub-agents. Phase 0 read-only; Phases 1–6
write-state (read files, run helpers, edit artifacts in the
project repo).

## Conventions

- **`mode: subagent`** — every agent file carries this frontmatter
  field. The orchestrator dispatches these by name (e.g.
  `osx-analyzer`, `osx-builder`); the `subagent` mode hides them
  from the user-driven picker so the only way the user invokes them
  is through the orchestrator's `RunRequest` flow.
- **`hidden: true`** — paired with `mode: subagent`, keeps the agent
  off the discovery surface entirely. Sub-agents also omit a
  `description` lede that would otherwise invite manual invocation.
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
| `osx-analyzer.md`     | PHASE0 + PHASE2 + PHASE5 — review, verify, self-reflect    |
| `osx-builder.md`      | PHASE1 — implement `tasks.md`; milestone commits          |
| `osx-maintainer.md`   | PHASE3 / PHASE4 / PHASE6 — docs, sync, archive            |
| `osx-reviewer.md`     | PHASE2 / PHASE5 — write reports; commit                   |
| `AGENTS.md`           | (this file) — conventions                                |

## Mirror

The Claude mirror does **not** ship agents/ — Claude Code has no
on-disk agent dispatch model. The Claude `validate_deployment`
path skips agent validation for that reason (`has_agents_dir=False`
on the Claude `ToolAdapter` in `orchestrator/source/tools.py`).
The orchestrator's `RunRequest` flow looks for the CLI binary and
skill definitions instead, relying on Claude Code's session model.
