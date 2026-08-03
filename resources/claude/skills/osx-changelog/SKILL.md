---
description: Generate changelogs in Keep a Changelog format from archived OpenSpec changes
license: MIT
name: osx-changelog
---

Generate changelogs from archived OpenSpec changes in Keep a Changelog format.

**IMPORTANT**: This is an AI-guided workflow. It does not use CLI flags. All filtering is done through user interaction.

## Input

No arguments required. The AI guides through scope selection.

## Steps

Load the skill body — read `.claude/skills/osx-generate-changelog/SKILL.md` and follow the `## Steps` section. This command wraps that skill; do not duplicate steps here.

## Output

Write to `CHANGELOG.md` (project root). Format: Keep a Changelog. New entries under `## [Unreleased]`.

## Guardrails

- Follow Keep a Changelog format.
- Handle missing `proposal.md` gracefully (fall back to `design.md` or `tasks.md`).
- Use concise entries (1–2 sentences).
- Highlight `**BREAKING**` and security changes.
- Confirm before writing — always preview and ask.
- Preserve existing changelog content when updating.

See `.claude/skills/osx-generate-changelog/SKILL.md` for the full contract, categorisation algorithm, and version management.

<!--
# AUTO-GENERATED from opencode via `mise run sync:mirrors` — do not edit by hand.
Source: resources/opencode/commands/osx-changelog.md
Regenerate: `mise run sync:mirrors`
-->
