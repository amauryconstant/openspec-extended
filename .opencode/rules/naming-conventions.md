---
paths:
  - "orchestrator/resources/canonical/**"
  - "skills/resources/canonical/**"
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
- User-invocation prefix follows the adapter's `skill_prefix` field
  (``/`` for opencode and Claude today; ``$`` and ``/skill:`` for
  future skills-only adapters). Source files use the
  ``{{SKILL_PREFIX}}`` token so a single canonical source serves every
  invocation form. The skill directory name is `osx-<id>` on every
  adapter — never write the literal ``/osx-<id>`` in resource source files.
- Slash-command filename prefix follows the adapter's `slash_prefix`
  field (``osx-`` for opencode, ``osx:`` for Claude). Use
  ``{{CMD_PREFIX}}`` only where the filename prefix matters.
- `osx-concepts §2.5` enumerates the canonical taxonomy (workflow skill, agents, phase commands, gap-filling skills, slash commands with self-contained bodies).

## Frontmatter contract

`osx-*` skills and commands mirror upstream's frontmatter shape:

```yaml
---
name: osx-<id>                     # kebab-case, matches directory
description: <one trigger sentence — "Use when…">  # ≤ 1024 chars per OpenCode
allowed-tools: Bash(openspec:*)    # declared everywhere; OpenCode ignores, Claude Code enforces
license: MIT
compatibility: Requires openspec CLI.
metadata:
  audience: <phase or context>     # e.g. "PHASE1 + ad-hoc /osx-commit"
  workflow: <pre/post/orthogonal>  # e.g. "implementation"
---
```

Agent files additionally carry the OpenCode-only dispatch fields
documented in "OpenCode-only dispatch fields" below.

## OpenCode-only dispatch fields

Upstream `openspec-*` skills have no agents and no dispatch metadata.
The orchestrator introduces them for autonomous multi-phase operation.
These fields are recognized by OpenCode but ignored by Claude Code and
other adapters — they are an explicit, documented divergence:

| Field | Where | Why we have it |
| --- | --- | --- |
| `agent:` | phase commands | OpenCode dispatches each phase command into a specific subagent (e.g. `osx-builder` for PHASE1). Upstream has no agents; humans pick skills by hand. |
| `mode: subagent` | agents | Hides the agent from the user-driven picker; only the orchestrator's `RunRequest` flow invokes it. |
| `hidden: true` | agents | Pairs with `mode: subagent`; keeps the agent off the discovery surface. |
| `temperature:` | agents | Low (0.1–0.4) for deterministic audit behaviour. |
| `permission:` | agents | Per-agent tool allowlist (read-only for `osx-analyzer`; full for `osx-builder`/`osx-maintainer`/`osx-reviewer`). |
| `disable-model-invocation: true` | `osx-changelog`, `osx-maintain-docs` | These are user-invoked slash commands; we don't want the orchestrator picking them up. OpenCode-specific gate. |

## Adapter-rendering divergence

Upstream skills contain **no token placeholders** in source; per-tool
adapters rewrite the canonical slash form at deploy time. We follow
the same model but with two exceptions where the divergence is
genuine, not cosmetic:

| Token | Status | Rationale |
| --- | --- | --- |
| `{{DOCS_FILE}}` | keep | `AGENTS.md` (OpenCode) vs `CLAUDE.md` (Claude Code) — no canonical cross-tool form. |
| `{{PLATFORM_DIR}}` | keep | `.opencode` vs `.claude` — no canonical cross-tool form. |
| `{{ASK_TOOL}}` | keep | `AskUserQuestion` vs `Ask` — tool-specific UI affordance. |
| `{{TOOL_NAME}}` | keep | Display name only. |
| `{{SKILL_PREFIX}}` | keep | Adapter-routed slash prefix; non-trivial rewrite. |
| `{{CMD_PREFIX}}` | keep | Adapter-routed filename prefix. |
| `{{ASK_TOOL}}`, `{{DOCS_FILE}}`, `{{TOOL_NAME}}`, `{{PLATFORM_DIR}}` | keep | These have no canonical cross-tool form. |

The orchestrator deploy rewrites `/osx:<id>` → `/osx-<id>` for OpenCode
and `/osx:<id>` → `/osx:<id>` for Claude Code (already the form) via
`orchestrator/source/cli.py:_substitute_tokens`, mirroring upstream's
`src/utils/command-references.ts`. `orchestrator/core/` (`osc-*`) is
unaffected — those tokens belong to the per-tool adapters shipped
inside the core package.

## Shared references divergence

Upstream skills ship with zero `references/` subdirectories. We
declare shared cross-cutting material (`scoring-rubric.md`,
`schema-agnostic-contract.md`, `store-selection.md`, etc.) under
`orchestrator/resources/canonical/skills/references/` and copy each
consumed reference into the deploying skill's own `references/`
subdir so the deployed skill is self-sufficient. The
`skills-side manifest` declares which references each skill reads
via the manifest's `references = [...]` list.
