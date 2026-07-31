# OSX Autonomous Mode Conventions

When `openspec-extended orchestrate` dispatches a skill, it sets `OSX_AUTONOMOUS=1`. Interactive skills that prompt for user input should degrade to **auto-accept** in that mode and proceed with reasonable defaults.

## The convention

- Each "ask the user" step in a skill assumes `OSX_AUTONOMOUS=1` may be set.
- When set, the step uses **auto-accept** (or the documented autonomous default) without calling `AskUserQuestion` / `Ask`.
- When unset, the step prompts normally.
- State the convention once at the top of the skill; per-step prose stays terse.

## Per-step recipe

Inline restatement pattern:

```text
Mode check: if `OSX_AUTONOMOUS=1` is set in the environment, skip this question and auto-accept. Otherwise, use the `AskUserQuestion` tool to confirm.
```

Avoid restating this in every step. State it once at the top, then each step assumes it.

## What this does NOT change

- The user's answers still appear in `osx log append` and `osx iterations append` (now with the auto-accepted answer recorded).
- Per-edit confirmation remains mandatory even in autonomous mode — `auto-accept` is the default when the user can't respond, not a bypass.
- Blocker detection is unchanged; `BLOCKED` always requires `--blocker-reason`.

## See also

- `references/schema-agnostic-contract.md` — the rules autonomous mode operates within.
- `references/phase-protocol-common.md` — how phase commands use this convention.

<!--
# AUTO-GENERATED from opencode via `mise run sync:mirrors` — do not edit by hand.
Source: resources/opencode/skills/references/osx-mode-conventions.md
Regenerate: `mise run sync:mirrors`
-->
