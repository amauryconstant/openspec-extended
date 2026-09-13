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

## Per-adapter behaviour

Every adapter's `ToolAdapter` declares whether its target tree ships
an `agents/` directory (`has_agents_dir` field). Adapters that don't
expose an on-disk agent dispatch model (Claude Code, Cursor, Codex,
Kimi — they use a session model instead) set `has_agents_dir=False`;
`validate_deployment` skips agent validation for those targets. The
orchestrator's `RunRequest` flow looks for the CLI binary and skill
definitions instead, per the tool's session model.
