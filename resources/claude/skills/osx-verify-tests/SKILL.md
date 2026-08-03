---
description: Review test coverage for OpenSpec changes to ensure spec requirements have tests
license: MIT
allowed-tools: Bash(openspec:*)
name: osx-verify-tests
---

Review test coverage for OpenSpec changes, ensuring spec requirements have corresponding tests.

**IMPORTANT**: This is an AI-guided analysis workflow. It does not use CLI flags.

## Input

Optionally specify `[change-name]` after `/{{CMD_PREFIX}}verify-tests`. If omitted, the AI will infer from context or prompt for selection.

## Steps

Load the skill body — read `{{PLATFORM_DIR}}/skills/osx-review-test-compliance/SKILL.md` and follow the `## Steps` section. This command wraps that skill; do not duplicate steps here.

## Output

Default output path: `openspec/changes/<name>/test-compliance-report.md`. Use the template in `references/report-format.md` of the underlying skill.

## Guardrails

- **Gap-focused.** Report what's missing, not just percentages.
- **Explain context.** Provide "why no match" explanations.
- **Project-aware.** Use `openspec/config.yaml` for test patterns if available.
- **Actionable.** Suggest specific test additions.
- **Reality check.** Acknowledge unit tests ≠ scenario tests.
- **Confidence transparency.** Show scores and explain matching.

See `{{PLATFORM_DIR}}/skills/osx-review-test-compliance/SKILL.md` for the full contract, semantic matching methodology, and gap analysis.

<!--
# AUTO-GENERATED from opencode via `mise run sync:mirrors` — do not edit by hand.
Source: resources/opencode/commands/osx-verify-tests.md
Regenerate: `mise run sync:mirrors`
-->
