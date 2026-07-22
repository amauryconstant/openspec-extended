---
description: Schema-driven pre-implementation artifact audit (read-only) plus routing to the right editor
license: MIT
allowed-tools: Bash(openspec:*)
---

## Tools Available

| Tool | Type | Usage |
|------|------|-------|
| `openspec` | Upstream CLI | `openspec <command> [options]` — npm package |
| `osx ctx` | Local script | `openspec-extended osx ctx get <change>` — load change context |

Schema-driven, **read-only** audit of planning artifacts in a change. Emits a
routing report; never edits files. Editors (`osx-modify-artifacts` or
`/opsx:update`) are invoked separately, typically by the user.

### Store selection

If the change lives in a registered store (a standalone OpenSpec repo
registered on this machine), run `openspec store list --json` to discover ids
and pass `--store <id>` on `status`, `instructions`, etc. Without a store,
commands act on the nearest local `openspec/` root.

## Input

Optionally specify `[change-name] [artifact-id]` after `/osx-review`. If omitted, the agent will infer from context or prompt for selection.

**Patterns**:
| Input | Behavior |
|-------|----------|
| `/osx-review add-auth specs/auth` | Audit specific artifact in specific change |
| `/osx-review add-auth` | Audit the entire change |
| `/osx-review` | Infer from context or prompt |

## Steps

1. **Load the skill body**.
   Read `.opencode/skills/osx-review-artifacts/SKILL.md` and follow the seven
   steps in `## Workflow`. This command wraps that skill; do not duplicate
   rules here.

2. **Persist the routing report** once the skill completes its work.

## Guardrails

- **Read-only.** Never edit planning artifacts from inside this command. The
  routed editor (`/osx-modify <name> <id>` for single-artifact defects;
  `/opsx:update <name>` for multi-artifact drift) does the writing.
- **No code edits.** Findings that imply code changes route to `/opsx:apply`.
- **No hardcoded artifact names.** Read ids and paths from
  `openspec status --change <name> --json` and `openspec instructions --json`.
- **Carry `--store <id>`** when the change is store-backed.

See `.opencode/skills/osx-review-artifacts/SKILL.md` for the full contract,
output templates, and severity calibration.
