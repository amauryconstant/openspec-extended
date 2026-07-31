# Shell Argument Safety

When passing free-text to `--summary`, `--next-steps`, or any other shell argument for `osx log append` / `osx iterations append` / `openspec-extended osx ...`, **do not use backticks** (`` `like this` ``) for inline code references.

## Why

Backticks are interpreted as command substitution by bash/zsh — the shell executes whatever is inside and substitutes its output. In zsh, `` `local` `` dumps the entire shell environment (PATH, tokens, internal variables) into your string, which then gets stored verbatim in `decision-log.json` or the orchestrator log.

## Use instead

| Form | Example | Safe? |
|---|---|---|
| Single quotes | `'local'` | yes |
| Double quotes | `"local"` | yes |
| Plain text | `local` | yes |
| Markdown `code` (backticks in raw form, NOT shell backticks) | fine only when the argument is not passed through a shell |
| Shell backticks | `` `local` `` | **no** — executes |

## Recovery

If `osx log append` returns `input_too_long` or `input_tainted`, the offending argument contains shell backticks. Remove them and retry with one of the safe forms above.

## Examples

```bash
# WRONG: shell expands \`local\` to the entire shell environment
openspec-extended osx log append "$1" --summary "Used \`local\` scope for x"

# RIGHT: single quotes keep the literal text
openspec-extended osx log append "$1" --summary 'Used local scope for x'

# RIGHT: double quotes work too
openspec-extended osx log append "$1" --summary "Used local scope for x"
```

<!--
# AUTO-GENERATED from opencode via `mise run sync:mirrors` — do not edit by hand.
Source: resources/opencode/skills/references/shell-argument-safety.md
Regenerate: `mise run sync:mirrors`
-->
