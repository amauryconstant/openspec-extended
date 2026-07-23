---
description: Compare OpenSpec Core to OpenSpec Extended and verify the integration is correct and up-to-date; emits a prioritized CRITICAL→LOW backlog. Use when asked to audit, review, harmonize, or check drift.
---

## Input

`/audit [scope] [--refresh]`

Scope table, workflow, toolset, and process guardrails: `.opencode/skills/audit/SKILL.md`.

The report is written to `.audit/reports/<UTC-date>-audit.md` and printed to stdout.

## Project-specific guardrail

During the audit, do not run any command that mutates the surfaces under inspection: `git subtree pull`, `mise run sync-core`, `openspec update`, or the project installer.
