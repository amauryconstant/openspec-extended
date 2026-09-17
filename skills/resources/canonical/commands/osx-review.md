---
name: osx-review
description: Schema-driven pre-implementation artifact audit (read-only) plus routing to the right editor. Use when artifacts exist and you want a routing report before implementation.
license: MIT
compatibility: Requires openspec CLI.
allowed-tools: Bash(openspec:*)
metadata:
  author: openspec-extended
  audience: ad-hoc pre-implementation /osx-review invocation
  workflow: pre-implementation — between artifact creation and apply
---

# osx-review

Schema-driven, **read-only** audit of planning artifacts in a change. Emits a routing report; never edits files. Editors (`osc-update-change` or `/osc-update-change`) are invoked separately, typically by the user.

> **Store selection** — see `{{PLATFORM_DIR}}/skills/references/store-selection.md`.

**Input**: Optionally specify `[<change-name>]` after `/osx-review` (e.g., `/osx-review add-auth`, `/osx-review`). `$1` is the change name. If the change name is omitted, check if it can be inferred from conversation context; auto-select if only one active change exists; otherwise run `openspec list --json` and prompt via `{{ASK_TOOL}}`. When the change is store-backed, carry `--store <id>` on every `openspec …` command.

**Invocation matrix**:

| Invocation | Effect |
| --- | --- |
| `/osx-review <change-name>` | Audit the entire change |
| `/osx-review` | Infer from context or prompt |

---

**Steps**

1. **Select the change** — If a name is provided (as `$1`), use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` and ask the user to select one

   Always announce: "Using change: <change-name>" and how to override (e.g., `/osx-review <other>`).

2. **Load the skill body** — read `{{PLATFORM_DIR}}/skills/osx-review-artifacts/SKILL.md` and follow `**Steps**`. This command wraps that skill; do not duplicate rules here.

3. **Load change context** when needed via `openspec-extended osx ctx get <change>` (per the skill's protocol).

4. **Persist the routing report** once the skill completes its work.

---

**Guardrails**

- **Read-only.** Never edit planning artifacts. The routed editor does the writing.
- **No code edits.** Findings that imply code changes route to `/osc-apply-change`.
- **No hardcoded artifact names.** Read ids and paths from `openspec status` and `openspec instructions` JSON.

---

## Tips

- Run after `openspec` reports `isPlanningComplete: true`; reviewing incomplete artifacts wastes the audit on missing files.
- Re-run after fixes to confirm previously-flagged findings are now clean; the report does not store incremental state.
- Apply the routed editor (`/osc-update-change` for the typical case) once the routing report chooses.

See `{{PLATFORM_DIR}}/skills/osx-review-artifacts/SKILL.md` for the full contract, output templates, and severity calibration.
