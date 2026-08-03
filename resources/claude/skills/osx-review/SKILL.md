---
description: Schema-driven pre-implementation artifact audit (read-only) plus routing to the right editor
license: MIT
allowed-tools: Bash(openspec:*)
name: osx-review
---

Schema-driven, **read-only** audit of planning artifacts in a change. Emits a routing report; never edits files. Editors (`osx-modify-artifacts` or `/opsx:update`) are invoked separately, typically by the user.

> **Store selection** — see `.claude/skills/references/store-selection.md`.

## Input

Optionally specify `[change-name] [artifact-id]` after `/osx:review`. If omitted, the agent infers from context or prompts.

| Input | Behavior |
|-------|----------|
| `/osx:review add-auth specs/auth` | Audit specific artifact in specific change |
| `/osx:review add-auth` | Audit the entire change |
| `/osx:review` | Infer from context or prompt |

## Steps

1. **Load the skill body** — read `.claude/skills/osx:review-artifacts/SKILL.md` and follow `## Workflow`. This command wraps that skill; do not duplicate rules here.
2. **Load change context** when needed via `openspec-extended osx ctx get <change>` (per the skill's protocol).
3. **Persist the routing report** once the skill completes its work.

## Guardrails

- **Read-only.** Never edit planning artifacts. The routed editor does the writing.
- **No code edits.** Findings that imply code changes route to `/opsx:apply`.
- **No hardcoded artifact names.** Read ids and paths from `openspec status` and `openspec instructions` JSON.

See `.claude/skills/osx:review-artifacts/SKILL.md` for the full contract, output templates, and severity calibration.

<!--
# AUTO-GENERATED from opencode via `mise run sync:mirrors` — do not edit by hand.
Source: resources/opencode/commands/osx-review.md
Regenerate: `mise run sync:mirrors`
-->
