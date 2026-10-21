---
name: osx-verify-tests
description: Verify that implementation tests cover every scenario in an OpenSpec change. Use after implementation, between /osc-apply-change and /osc-verify-change. Mirrors the three-dimension report (Completeness / Correctness / Coherence) and the CRITICAL / WARNING / SUGGESTION severity scale of openspec-verify-change.
license: MIT
compatibility: Requires openspec CLI.
allowed-tools: Bash(openspec:*)
metadata:
  author: openspec-extended
  audience: ad-hoc /osx-verify-tests invocation; PHASE1 end-of-iteration check
  workflow: post-implementation — between apply and verify
---

# osx-verify-tests

Surface spec-to-test alignment for an OpenSpec change.

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
   - Infer from conversation context
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` and ask the user to select one

   Always announce: "Using test-compliance for: <change-name>" and how to override (e.g., `/osx-verify-tests <other>`).

2. **Load the skill body** — read `{{PLATFORM_DIR}}/skills/osx-verify-tests/SKILL.md` and follow its `**Steps**` section. This command wraps that skill; do not duplicate steps here.

---

**Output**

The wrapped skill emits a `## Test Compliance Report: <change-name>` with the three-dimension summary scorecard from `openspec-verify-change`'s shape, an issues-by-priority block (CRITICAL / WARNING / SUGGESTION), and a final-assessment line routing the user toward `/osc-verify-change` or back into `osc-apply-change` iterations.

---

**Guardrails**

- **Schema-agnostic.** No hardcoded spec artifact names; read ids and paths from `openspec status` and `openspec instructions apply` JSON.
- **Semantic, not syntactic.** This skill matches actions, entities, and outcomes rather than token strings.
- **Calibration.** When uncertain, prefer SUGGESTION over WARNING, WARNING over CRITICAL.
- **Skip awareness.** Use **Not applicable** when a check has no expected target; use **Not verified** when evidence is missing. Never score a skipped check as passing.
- **Complements `/osc-verify-change`.** Treat the two reports as a layered review: implementation correctness (upstream) followed by test coverage (this skill).

---

## Tips

- Run after `/osc-apply-change` and before `/osc-verify-change` — the verify command expects compliance gaps already addressed.
- For languages not in the skill's discovery table (Rust, Kotlin, Swift), override via `openspec/config.yaml` `context` rather than inline regex hunting.
- Re-run after fixes to confirm previously-missing scenarios now have tests; the report does not store incremental state.
- Treat the `## Test Compliance Report` and `/osc-verify-change`'s `## Verification Report` as two halves of a single review pass.

See `{{PLATFORM_DIR}}/skills/osx-verify-tests/SKILL.md` for the full contract, semantic matching methodology, and gap analysis.
