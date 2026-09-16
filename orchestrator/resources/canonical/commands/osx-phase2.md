---
name: osx-phase2
description: PHASE2 — verify implementation against change artifacts and route any defects. Use when dispatched by the orchestrator after implementation, or ad-hoc via `/osc-verify-change` augmented with routing transitions.
license: MIT
compatibility: Requires openspec CLI.
allowed-tools: Bash(openspec:*)
agent: osx-reviewer
metadata:
  audience: PHASE2 verification (dispatched by orchestrator)
  workflow: verification
---

# PHASE2: Review

Change: $1

> **Protocol spine** — see `references/phase-protocol-common.md`. **Blocker semantics** — `references/blocker-semantics.md`. **Decision-log schema** — `references/osx-decision-logging.md`. **Shell-arg safety** — `references/shell-argument-safety.md`. **Tools** — `osx-workflow` §1. **Store selection** — `references/store-selection.md`.

**Input**: The orchestrator dispatches `<change-name>` as `$1` (e.g., `/osx-phase2 add-auth`). For ad-hoc invocations: if omitted, check if it can be inferred from conversation context; auto-select if only one active change exists; otherwise run `openspec list --json` and prompt via `{{ASK_TOOL}}`. When the change is store-backed, carry `--store <id>` on every `openspec …` command. Phase name canonical to the engine is `REVIEW`; the upstream skill is `osc-verify-change` ("Verification"). Both names refer to PHASE2.

## Mandatory start / end

```bash
# Start
openspec-extended osx ctx get "$1"
# End
openspec-extended osx log append "$1" --phase REVIEW --iteration N \
  --summary "..." --commit-hash "<hash or null>" --next-steps "..." \
  --extra '{"verification_report":"...","case":"A|B|C"}'
openspec-extended osx iterations append "$1" --phase REVIEW --iteration N \
  --commit-hash "<hash or null>" --notes "..."
# Phase end (Case A routing uses transition; Case B / C use complete — see Steps above)
openspec-extended osx state complete "$1"
```

## Steps

1. **Select the change**

   If a name is provided (the orchestrator dispatches `<change-name>` as `$1`), use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` (filtered to changes with implementation tasks, i.e. where a `tasks` artifact exists) and ask the user to select one

   Always announce: "Using change: <change-name>" and how to override (e.g., `/osx-phase2 <other>`).

2. Load context per protocol spine.
3. Load and use `osc-verify-change` skill for change `<change-name>`. Execute the skill's verification instructions exactly. Do NOT modify the skill's verification report format.
3. **Embed requirement-level diff** in `verification-report.md`:

   ```bash
   openspec show "$1" --diff --json
   ```

   The report gets three new sections when the diff envelope is non-empty: `## Delta inventory`, `## Requirement diff`, `## Verification warnings`.

4. **Case A — Critical / Warning findings** (default). Use `/osc-update-change` to reconcile artifacts of any shape — single- or multi-artifact. Transition:

   ```bash
   openspec-extended osx state transition "$1" --target PHASE1 --reason artifacts_modified --details "Brief description of what was fixed"
   ```

   Do not bypass via `--no-verify`.

5. **Case B — Implementation defect (code wrong, artifacts right).** When verification reveals an implementation defect rather than an artifact defect, route back to PHASE1 with `implementation_incorrect`:

   ```bash
   openspec-extended osx state transition "$1" --target PHASE1 --reason implementation_incorrect --details "Brief description of what needs fixing"
   ```

6. **Case C — Suggestion only or all clean.** Mark phase complete; orchestrator advances to PHASE3. If a re-verification is needed (suggestion track), use `retry_requested`:

   ```bash
   openspec-extended osx state transition "$1" --target PHASE2 --reason retry_requested --details "Brief description of alternative approach"
   ```

   **Missing-artifact sub-case.** If verification surfaces a *missing* artifact (a task or spec the implementation needs but does not yet exist), do **not** route via `/osc-update-change` — that command revises existing artifacts; creating new artifacts is `/osc-continue-change`'s job. Use `/osc-continue-change <name>` to create the missing artifact, then re-run verify. The Case A update path only applies when the missing piece is a defect in something that already exists.

   **Design-ambiguity sub-case.** If the report surfaces design-level ambiguities (e.g. the spec is internally consistent but its intent is unclear in context), consider `/openspec-explore <name>` for explicit thinking time *before* reconciling via `/osc-update-change <name>`. Avoid using `/osc-update-change` to "decide by editing" — capture the intent in conversation first, then reconcile the artifacts.
7. Append `verification_report` field via `osx log`. Track suggestions in `suggestions.md` and reference them at PHASE5.
8. **Mandatory end** — append `osx log` and `osx iterations` per protocol spine, then `osx state complete "$1"` (Case B / C) or `osx state transition "$1" --target PHASE1 --reason artifacts_modified --details "..."` (Case A).

## Output

`verification-report.md` with three dimensions (Completeness / Correctness / Coherence), an embedded requirement-level diff when applicable, and one of three case determinations. Logged via `osx log` with field `verification_report`.

## Guardrails

- **Agent**: `osx-reviewer` (`edit: allow`). Writes `verification-report.md`; commits via `osx-commit` after the report is finalised.
- **Suggestion ↔ Warning ↔ Critical** — when uncertain, prefer Suggestion over Warning, Warning over Critical. Implementation-readiness concerns are never Critical.
- **Never delegates** `openspec-sync-specs` work here; sync is a separate phase.
- **Max 10 iterations** per phase. If exceeded, signal `BLOCKED` with `iteration_budget_exceeded`.
- **Failure modes**:
  - `openspec show --diff --json` returns `specs_locked` or diff is empty → treat as Case C.
  - Verification reveals an implementation defect (code wrong, artifacts right) → `state transition --target PHASE1 --reason implementation_incorrect`.
  - Verification reveals an artifacts defect → Case A (default `/osc-update-change`).
