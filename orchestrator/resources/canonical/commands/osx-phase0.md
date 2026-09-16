---
name: osx-phase0
description: PHASE0 — read-only artifact review and routing report. Use when dispatched by the orchestrator between artifact creation and implementation, or when running ad-hoc to surface issues before apply.
license: MIT
compatibility: Requires openspec CLI.
allowed-tools: Bash(openspec:*)
agent: osx-analyzer
metadata:
  audience: PHASE0 read-only audit (dispatched by orchestrator)
  workflow: pre-implementation — between artifact creation and apply
---

# PHASE0: Artifact Review

Change: $1

> **Protocol spine** — see `references/phase-protocol-common.md` (Mandatory Start / Mandatory End / State File Updates / Logging / Blocker Handling / Shell-Argument Safety). Phase-specific blocker reasons and logging fields are listed below.
> **Blocker semantics** — `references/blocker-semantics.md`. **Decision-log schema** — `references/osx-decision-logging.md`. **Shell-arg safety** — `references/shell-argument-safety.md`. **Tools** — `osx-workflow` §1. **Store selection** — `references/store-selection.md`.

**Input**: The orchestrator dispatches `<change-name>` as `$1` (e.g., `/osx-phase0 add-auth`). For ad-hoc invocations: if omitted, check if it can be inferred from conversation context; auto-select if only one active change exists; otherwise run `openspec list --json` and prompt via `{{ASK_TOOL}}`. When the change is store-backed, carry `--store <id>` on every `openspec …` command.

## Mandatory start / end

```bash
# Start
openspec-extended osx ctx get "$1"
# End
openspec-extended osx log append "$1" --phase ARTIFACT_REVIEW --iteration N \
  --summary "..." --commit-hash "<hash or null>" --next-steps "..." \
  --extra '{"routed_to":"...","issues_found":{"critical":N,"warning":N,"suggestion":N}}'
openspec-extended osx iterations append "$1" --phase ARTIFACT_REVIEW --iteration N \
  --commit-hash "<hash or null>" --notes "..." \
  --extra '{"artifacts_audited":["<id>"],"issues_found":{},"routed_to":"..."}'
# Phase end
openspec-extended osx state complete "$1"   # clean review OR Suggestion-only (advisory, see §5 routing rule)
openspec-extended osx state set-routes "$1" --routes "/osc-update-change"   # routes pending (Critical/Warning findings only)
openspec-extended osx complete set "$1" BLOCKED --blocker-reason "..."   # blocker
```

## Input

`<change-name>` (kebab-case). Carries `--store <id>` when the change is store-backed.

## Steps

1. **Select the change**

   If a name is provided (the orchestrator dispatches `<change-name>` as `$1`), use it. Otherwise:
   - Infer from conversation context if the user mentioned a change
   - Auto-select if only one active change exists
   - If ambiguous, run `openspec list --json` to get available changes and ask the user to select one

   Always announce: "Using change: <change-name>" and how to override (e.g., `/osx-phase0 <other>`).

2. Load context per protocol spine.
3. Load and use `osx-review-artifacts` skill for change `<change-name>`. Follow the skill's Steps 1–7 (select change → load schema state → per-artifact audit → cross-artifact consistency → implementation-readiness → classify findings → routing recommendation). Slash-command equivalent for ad-hoc runs (between dispatched iterations): `/osx-review <change-name>` — same skill body.
4. Classify findings Critical / Warning / Suggestion. Apply the verify calibration rule — implementation-readiness concerns are never Critical.

5. **Routing rule.** Apply the **severity threshold** — only Critical and Warning findings trigger a route; Suggestion findings are advisory and do not block. Produce a routing recommendation:

   | Finding pattern | Recommended route |
   |---|---|
   | Any Critical or Warning finding (regardless of breadth) | `/osc-update-change <name>` — single- and multi-artifact fixes both use this command; the skill reconciles any combination of findings against the dependency graph |
   | Missing artifacts | `/osc-continue-change <name>` |
   | `retire_capabilities: true` in `.openspec.yaml` AND planning is complete | `/osc-archive-change <name>` (skip PHASE1–PHASE5; orchestrator stamps `state.retire_capabilities = true` so PHASE6 runs directly) |
   | All clean (no Critical/Warning/Suggestion findings; ad-hoc invocation) | `/osc-apply-change <name>` — orchestrated loop hands off to PHASE1 via `osx state complete` automatically; `/osc-apply-change` is the ad-hoc equivalent users run between dispatched iterations |
   | Intent-level change detected (per `osc-update-change` "Update vs. Start Fresh" heuristic) | `/osc-new-change <fresh-name>` |
   | All clean **OR** Suggestion-only findings | mark phase complete and hand off to PHASE1 (Suggestions are advisory; they are logged in `decision-log.json` / `iterations.json` and surfaced in the routing report, but do not block) |

   **Do not fix in this phase.** Surface the routing; the user (or a follow-up slash command) performs the fixes.

   **Severity calibration guardrail.** When classifying a finding as `Suggestion` to avoid routing, confirm it is genuinely stylistic or advisory. Any finding that misleads implementation, breaks the spec/dependency graph, or contradicts an existing capability must be classified at least `Warning`. Prefer the more conservative severity when uncertain — this prevents the new threshold from becoming a regression vector.

5. When a retirement is detected, the routing report must include a one-line summary naming the capabilities being removed (parse `## REMOVED Requirements` for capability paths). The orchestrator's pre-flight reads `.openspec.yaml` once and stashes `retire_capabilities` on `state.json`. Subsequent phases PHASE1–PHASE5 should be skipped via `--from-phase PHASE6`.

6. **Max iterations reached without clean review:** document all remaining Critical issues via `osx log`, create `complete.json` with BLOCKED status (workflow stops).

## Output

Routing report with the single best editor for the aggregate finding set, plus the per-finding Severity / Artifact / File:line / Fix / Route lines. The skill never invokes the routed command itself.

## Guardrails

- **Read-only.** Editor actions belong to `/osc-update-change` (covers single- and multi-artifact fixes; PHASE0 routes all corrective edits through this command). Dispatched via `osx-analyzer` (`edit: deny`).
- **Max 10 review iterations** (`--max-phase-iterations`).
- **Single source of artifact names**: `openspec status --change <name> --json` and `openspec instructions <id> --change <name> --json`. No hardcoded `proposal.md` / `specs/` / `design.md` / `tasks.md`.
- **Carry `--store <id>`** when the change is store-backed.
- **Early exit** if the first review returns clean.
- **State updates**: `osx state complete "$1"` on clean review **or Suggestion-only findings** (advisory; phase proceeds to PHASE1); `osx state set-routes "$1" --routes "/osc-update-change"` when at least one Critical or Warning finding is present; `osx complete set "$1" BLOCKED --blocker-reason "..."` on Critical blockers. The engine reads `routes_pending` from `state.json` after the phase ends — if non-empty (and `phase_complete` is false), the orchestrator exits 0 with "Halted for routed commands". After the user runs the routed commands, the next `orchestrate` run re-enters PHASE0 to verify the fix.
- **Never commits** (this phase never edits); the user invokes `osx-commit` after running the routed editor. Capture the commit hash in the decision-log entry when `artifacts_modified` is later recorded.
