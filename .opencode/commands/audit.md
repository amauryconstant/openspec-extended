---
description: Run a multi-agent harmonization audit of openspec-core (subtree) vs openspec-extended (Python wrapper, skills, agents, commands, orchestrator). Maps both surfaces in parallel via subagents, evaluates surface quality, and emits a prioritized CRITICAL→LOW backlog with file:line references. Read-only — never edits files. Use after an openspec-core sync, before a release, or when asked to audit, review, harmonize, or check drift between openspec-core and openspec-extended.
license: MIT
---

## Tools Available

| Tool | Type | Usage |
|------|------|-------|
| Task | Subagent dispatcher | Spawn parallel `explore` subagents for surface mapping, diff, and quality eval |
| Read | File reader | Read source files, manifests, SKILL.md, AGENTS.md |
| Grep | Pattern search | Find references, flag drift, count occurrences |
| Glob | File matcher | Enumerate skills, agents, commands, manifests |
| Bash | Limited shell | `git log`, `git diff --stat`, `mkdir -p`, `date -u`, `realpath`, `wc -l` |

The audit is **pure file-system analysis**. It does not shell out to `openspec` or `openspec-extended` binaries.

## Input

`/audit [scope]`

| Scope | What runs | When to use |
|-------|-----------|-------------|
| `full` (default) | Capture → Upstream map ∥ Local map → Diff ∥ Quality → Synthesize | Periodic review, pre-release |
| `upstream` | Capture → Upstream map only | Quick upstream inventory, post-upgrade |
| `local` | Capture → Local map only | Local surface inventory, post-refactor |
| `integration` | Capture → Diff only (assumes recent maps) | After a library/orchestrator change |
| `skills` | Capture → Local map (skills/agents/commands) → Quality eval → Synthesize | Skill/agent review |
| `docs` | Capture → Diff (doc subset) → Synthesize | Doc-drift sweep |

## Steps

1. Load the skill body.
   Read `.opencode/skills/audit/SKILL.md` and follow the workflow in `## Workflow`. This command wraps that skill; do not duplicate logic here.

2. Write the report once.
   The skill saves the report to `docs/audits/<UTC-date>-audit.md` and prints it to stdout. Do not duplicate the write step.

## Guardrails

- **Read-only.** Never edit files during the audit.
- **No mutation during audit.** Do not run `git subtree pull`, `mise run sync-core`, `openspec update`, or any installer — would change the surface under inspection.
- **Save once per UTC date.** Same-date rerun overwrites; do not append.
- **Cite file:line for every claim.** No paraphrasing. Group related findings under one header.
- **Capture first, then dispatch.** The capture step runs before any subagent; do not parallelize it.

See `.opencode/skills/audit/SKILL.md` for the full contract, output template, and severity rubric.
