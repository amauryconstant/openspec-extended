---
paths:
  - "orchestrator/resources/canonical/**"
  - "skills/resources/canonical/**"
---

# Per-adapter rendering

A single canonical source tree lives on disk and every supported tool adapter
renders from it at deploy time via `orchestrator/source/cli.py:deploy_*`,
parameterised by `source.tools.ToolAdapter`.

The on-disk source tree is single-tree since Phase 2A: there is exactly one
`orchestrator/resources/canonical/` and one `skills/resources/canonical/`.
Every shipped adapter renders from those same files. Per-tool layout,
dispatch model, and slash-command spelling are all driven by `ToolAdapter`
fields; the deploy functions do not branch on tool id.

## Token substitution

| Token                  | OpenCode value     | Claude value   |
| ---------------------- | ------------------ | -------------- |
| `{{ASK_TOOL}}`         | `AskUserQuestion`  | `Ask`          |
| `{{DOCS_FILE}}`        | `AGENTS.md`        | `CLAUDE.md`    |
| `{{CMD_PREFIX}}`       | `osx-`             | `osx:`         |
| `{{TOOL_NAME}}`        | `OpenCode`         | `Claude Code`  |
| `{{PLATFORM_DIR}}`     | `.opencode`        | `.claude`      |
| `{{SKILL_PREFIX}}`     | `/`                | `/`            |
| `{{CROSS_REF_PREFIX}}` | `/`                | `/`            |

Single source of truth: `orchestrator/source/tools.py:_adapter_tokens`.
Adding a new token requires extending the helper and adding a regression
test in `tests/unit/test_token_substitution.py`. Unknown tokens are left
verbatim — a future token added to source but not yet to the helper
surfaces as a literal in the deployed file rather than silently
disappearing.

`{{ASK_TOOL}}` is read from `adapter.ask_tool`; the per-tool values
`AskUserQuestion` (opencode) and `Ask` (claude) live in the registry,
not in a separate dispatch table. Adding a new tool = set the field on
its `ToolAdapter` entry; no `_adapter_tokens` edit required.

`{{CROSS_REF_PREFIX}}` is read as `adapter.cross_ref_prefix` when
non-empty, otherwise `adapter.skill_prefix`. Both shipped adapters
declare `cross_ref_prefix=""`, so the token resolves to `"/"` —
identical to `{{SKILL_PREFIX}}` for opencode and claude. Skills-only
adapters (Codex, Kimi) diverge here.

## Scope rules

- `{{CMD_PREFIX}}` is slash-command-only. Use inside slash-command prose
  where the tool's filename prefix matters (`osx-` for opencode, `osx:`
  for Claude).
- `{{SKILL_PREFIX}}` is user-invocation-only. Use inside prose where the
  user types the slash-command form (`/osx-...` for opencode, `/osx:...`
  for Claude). Skill directory paths are hardcoded `osx-` on every
  adapter — they are filesystem identifiers, not user invocations.

## Per-tool layout driven by `ToolAdapter`

| Axis               | Field                          | OpenCode      | Claude        |
| ------------------ | ------------------------------ | ------------- | ------------- |
| Skills root        | `skills_dir`                   | `.opencode`   | `.claude`     |
| Commands root      | `commands_dir`                 | `commands`    | `commands/osx`|
| Commands layout    | `commands_style`               | `flat`        | `namespaced-with-skill-mirror` |
| Slash prefix       | `slash_prefix`                 | `osx-`        | `osx:`        |
| Skill invocation   | `skill_prefix`                 | `/`           | `/`           |
| Deploy binary      | `runner_binary`                | `opencode`    | `claude`      |
| Runner kind        | `runner_kind`                  | `opencode_run`| `claude_print`|
| Agent dir          | `has_agents_dir`               | True          | False         |
| Frontmatter strip  | `agent_field_transform`        | None (keep)   | strip_agent_line |
| Skill mirror name  | `inject_name_in_skill_mirror`  | False         | True          |
| Filename prefix    | `cmd_filename_strip_prefix`    | None          | `osx-`        |

Adding a new tool = one `REGISTRY[<tool_id>] = ToolAdapter(...)` entry
plus, where its layout diverges enough from a shipped adapter, a new
`commands_style` / `commands_ext` literal. The deploy path reads from
the registry only; no `cli.py` / `runner.py` / `lib/osx.py` edits
required for a new adapter.

## Claude dual-emit (current behavior)

Every opencode command dual-emits on Claude:

- Legacy form: `.claude/commands/osx/<name>.md` (prefix stripped, in
  nested subdir — `commands_dir="commands/osx"` +
  `cmd_filename_strip_prefix="osx-"`).
- Modern form: `.claude/skills/osx-<name>/SKILL.md` (skill mirror
  built by `_build_skill_mirror` with `name:` injected and
  `agent:` stripped via `agent_field_transform`).

Mirrors upstream OpenSpec's dual-emit strategy (v1.7.0, current as
of v1.13.0). Either form satisfies `validate_commands`.
