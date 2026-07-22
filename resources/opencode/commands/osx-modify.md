---
description: Surgical single-artifact edit with forward-only dependent propagation
license: MIT
allowed-tools: Bash(openspec:*)
---

## Tools Available

| Tool | Type | Usage |
|------|------|-------|
| `openspec` | Upstream CLI | `openspec <command> [options]` — npm package |
| `osx ctx` | Local script | `openspec-extended osx ctx get <change>` — load change context |

Single-artifact surgical edit with forward-only `unlocks` propagation. For
multi-artifact reconciliation, run `/opsx:update <name>` instead.

### Store selection

If the change lives in a registered store (a standalone OpenSpec repo
registered on this machine), run `openspec store list --json` to discover ids
and pass `--store <id>` on `status`, `instructions`, etc. Without a store,
commands act on the nearest local `openspec/` root.

## Input

Positional `<change-name>` (required) and optional `<artifact-id>`. If
`<artifact-id>` is omitted, the agent prompts (smallest blast radius first).

**Patterns**:
| Input | Behavior |
|-------|----------|
| `/osx-modify add-auth specs/auth` | Edit specific artifact in change |
| `/osx-modify add-auth` | Prompt for artifact selection |
| `/osx-modify` | Prompt for change and artifact |

## Steps

1. **Load the skill body**.
   Read `.opencode/skills/osx-modify-artifacts/SKILL.md` and follow the nine
   steps in `## Workflow`. This command wraps that skill; do not duplicate
   rules here.

2. **Apply the per-artifact confirmation model** the skill spells out: confirm
   root edit, then confirm each propagated dependent individually.

## Guardrails

- **Schema-agnostic.** Never assume `proposal.md`/`specs/`/`design.md`/`tasks.md`.
  Read ids and paths from `openspec status --change <name> --json` and
  `openspec instructions <id> --change <name> --json`.
- **Glob safety.** Write only to `existingOutputPaths`. Never to a glob
  `resolvedOutputPath`.
- **Frontier discipline.** A missing artifact is not an editing target. Route
  the user to `/opsx:continue <name>`.
- **Forward-only propagation.** Never edit an artifact in `dependencies`.
- **No code edits.** If the user asks to change code, refuse and point to
  `/opsx:apply <name>`.
- **Per-edit confirmation.** Show each proposed revision; write only after
  the user confirms. Rejected revisions are left unchanged.
- **Carry `--store <id>`** when the change is store-backed.

See `.opencode/skills/osx-modify-artifacts/SKILL.md` for the full contract,
intent-level change detection, and hand-off templates.
