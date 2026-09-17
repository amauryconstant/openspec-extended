---
name: osx-verify-tests
description: Surface test coverage gaps and orphaned tests for OpenSpec changes. Use after implementation, between /osc-apply-change and /osc-verify-change, to confirm spec scenarios have tests.
license: MIT
compatibility: Requires openspec CLI.
allowed-tools: Bash(openspec:*)
metadata:
  author: openspec-extended
  audience: ad-hoc /osx-verify-tests invocation; PHASE1 end-of-iteration check
  workflow: post-implementation — between apply and verify
---

# osx-verify-tests

Surface test coverage gaps and orphaned tests for OpenSpec changes.

> **IMPORTANT**: This is an AI-guided analysis workflow. It does not use CLI flags.

> **Store selection** — see `{{PLATFORM_DIR}}/skills/references/store-selection.md`.

**Input**: Optionally specify `[<change-name>]` after `/osx-verify-tests` (e.g., `/osx-verify-tests add-auth`). `$1` is the change name. If omitted, check if it can be inferred from conversation context; auto-select if only one active change exists; otherwise run `openspec list --json` and prompt via `{{ASK_TOOL}}`. When the change is store-backed, carry `--store <id>` on every `openspec …` command.

**Invocation matrix**:

| Invocation | Effect |
| --- | --- |
| `/osx-verify-tests <change-name>` | Analyse test coverage for the change |
| `/osx-verify-tests` | Infer from context or prompt |

---

**Steps**

1. **Select the change** — If a name is provided (as `$1`), use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` and ask the user to select one

   Always announce: "Analysing test compliance for: <change-name>" and how to override (e.g., `/osx-verify-tests <other>`).

2. **Load the skill body** — read `{{PLATFORM_DIR}}/skills/osx-review-test-compliance/SKILL.md` and follow its `**Steps**` section. This command wraps that skill; do not duplicate steps here.

---

**Output**

Default output path: `openspec/changes/<name>/test-compliance-report.md`. The wrapped skill renders the coverage-by-requirement table, gaps analysis, and recommendations per its `**Output**` section.

---

**Guardrails**

- **Gap-focused.** Report what's missing, not just percentages.
- **Explain context.** Provide "why no match" explanations.
- **Project-aware.** Use `openspec/config.yaml` for test patterns if available.
- **Actionable.** Suggest specific test additions.
- **Reality check.** Acknowledge unit tests ≠ scenario tests.
- **Confidence transparency.** Show scores and explain matching.

---

## Tips

- Run after `/osc-apply-change` and before `/osc-verify-change` — the verify command expects compliance gaps already addressed.
- For languages not in the skill's discovery table (Rust, Kotlin, Swift), override via `openspec/config.yaml` `context` rather than inline regex hunting.
- Re-run after fixes to confirm previously-missing scenarios now have tests; the report does not store incremental state.

See `{{PLATFORM_DIR}}/skills/osx-review-test-compliance/SKILL.md` for the full contract, semantic matching methodology, and gap analysis.
