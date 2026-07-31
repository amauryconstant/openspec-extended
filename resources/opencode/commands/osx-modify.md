---
description: Surgical single-artifact edit with forward-only dependent propagation
license: MIT
allowed-tools: Bash(openspec:*)
---

Single-artifact surgical edit with forward-only `unlocks` propagation. For multi-artifact reconciliation, run `/opsx:update <name>` instead.

> **Store selection** — see `{{PLATFORM_DIR}}/skills/references/store-selection.md`.

## Input

Positional `<change-name>` (required) and optional `<artifact-id>`. If `<artifact-id>` is omitted, the agent prompts (smallest blast radius first).

| Input | Behavior |
|-------|----------|
| `/{{CMD_PREFIX}}modify add-auth specs/auth` | Edit specific artifact in change |
| `/{{CMD_PREFIX}}modify add-auth` | Prompt for artifact selection |
| `/{{CMD_PREFIX}}modify` | Prompt for change and artifact |

## Steps

1. **Load the skill body** — read `{{PLATFORM_DIR}}/skills/{{CMD_PREFIX}}modify-artifacts/SKILL.md` and follow the `## Workflow` section. This command wraps that skill; do not duplicate rules here.
2. **Load change context** when needed via `openspec-extended osx ctx get <change>` (per the skill's protocol).
3. **Apply the per-artifact confirmation model** the skill spells out: confirm root edit, then confirm each propagated dependent individually.

## Guardrails

- **Schema-agnostic.** Never assume `proposal.md`/`specs/`/`design.md`/`tasks.md`; read from CLI JSON.
- **Glob safety.** Write only to `existingOutputPaths`.
- **Frontier discipline.** A missing artifact is not an editing target; route to `/opsx:continue`.
- **Forward-only propagation.** Never edit an artifact in `dependencies`.
- **No code edits.** Refuse and point to `/opsx:apply`.
- **Per-edit confirmation.** Show each proposed revision; write only after confirmation.

See `{{PLATFORM_DIR}}/skills/{{CMD_PREFIX}}modify-artifacts/SKILL.md` for the full contract, intent-level change detection, and hand-off templates.