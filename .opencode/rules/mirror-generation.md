---
paths:
  - "orchestrator/resources/claude/**"
  - "skills/resources/claude/**"
---

# Mirror Generation (Claude)

OpenCode is canonical. Claude mirrors are auto-generated. Never hand-edit Claude files.

## Rules

- **NEVER** edit files under `**/claude/` directly — every generated file carries an `# AUTO-GENERATED` header.
- Edit the OpenCode source first, then run `mise run sync:mirrors`, then commit both trees.
- Pre-commit hook `sync-mirrors-check` fails the commit if the mirror drifts from the OpenCode source.
- `mise run sync-mirrors --check` verifies without writing (used by CI and `mise run verify`).

## Token substitution

OpenCode source files carry `{{TOKEN}}` placeholders; the deploy step renders them per platform.

| Token             | OpenCode value     | Claude value   |
| ----------------- | ------------------ | -------------- |
| `{{ASK_TOOL}}`    | `AskUserQuestion`  | `Ask`          |
| `{{DOCS_FILE}}`   | `AGENTS.md`        | `CLAUDE.md`    |
| `{{CMD_PREFIX}}`  | `osx-`             | `osx:`         |
| `{{TOOL_NAME}}`   | `OpenCode`         | `Claude Code`  |
| `{{PLATFORM_DIR}}`| `.opencode`        | `.claude`      |

Single source of truth: `orchestrator/source/cli.py:PLATFORM_TOKENS`. Adding a new token requires extending both entries and adding a regression test in `tests/unit/test_token_substitution.py`. Unknown tokens are left verbatim.

## Scope rules

- `{{CMD_PREFIX}}` is slash-command-only. Use inside `/...` form (e.g. `/{{CMD_PREFIX}}review`).
- Skill directory paths are hardcoded `osx-` (works on both platforms). Never write `{{CMD_PREFIX}}<x>`.

## Dual-emit (Claude only)

Every opencode command dual-emits on Claude:

- Legacy form: `.claude/commands/osx/<name>.md`
- Modern form: `.claude/skills/osx-<name>/SKILL.md`

Mirrors upstream OpenSpec v1.7.0's strategy (current as of v1.13.0). Either form satisfies `validate_commands`.
