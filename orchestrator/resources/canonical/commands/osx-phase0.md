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
# Routes — ALWAYS queue via set-routes for any Critical/Warning finding,
# regardless of whether the route is auto-fixable. The engine reads
# routes_pending from state.json, dispatches auto-fixable routes itself
# (/osc-update-change → spawns osx-editor + invokes the slash command,
# re-enters PHASE0 to verify), and halts for non-auto-fixable or mixed
# routes (/osc-continue-change, /osc-new-change, /osc-archive-change,
# /osc-explore). The agent must NEVER silently swallow auto-fixable
# routes — the engine is the only one that knows whether a given route
# is auto-fixable.
openspec-extended osx state set-routes "$1" --routes "/osc-update-change"                   # auto-fix (engine dispatches)
openspec-extended osx state set-routes "$1" --routes "/osc-continue-change,/osc-new-change" # halt-and-surface
openspec-extended osx complete set "$1" BLOCKED --blocker-reason "..."                     # blocker
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

   | Finding pattern | Recommended route (in-orchestration) | Halt-and-surface (any mode) |
   |---|---|---|
   | Any Critical or Warning finding on existing artifacts (regardless of breadth) | **auto-fix** — engine clears routes_pending, invokes `osc-update-change` itself, re-enters PHASE0 to verify | `/osc-update-change <name>` (ad-hoc only) |
   | Missing artifacts | `/osc-continue-change <name>` | `/osc-continue-change <name>` |
   | `retire_capabilities: true` in `.openspec.yaml` AND planning is complete | `/osc-archive-change <name>` (orchestrator stamps `state.retire_capabilities = true` so PHASE6 runs directly) | `/osc-archive-change <name>` |
   | All clean (no Critical/Warning/Suggestion findings; ad-hoc invocation) | advance to PHASE1 automatically via `osx state complete` | `/osc-apply-change <name>` |
   | Intent-level change detected (per `osc-update-change` "Update vs. Start Fresh" heuristic) | `/osc-new-change <fresh-name>` | `/osc-new-change <fresh-name>` |
   | All clean **OR** Suggestion-only findings | mark phase complete and hand off to PHASE1 (Suggestions are advisory; they are logged in `decision-log.json` / `iterations.json` and surfaced in the routing report, but do not block) | — |

   **Do not fix in this phase.** Surface the routing; the user (or a follow-up slash command) performs the fixes.

   **Severity calibration guardrail.** When classifying a finding as `Suggestion` to avoid routing, confirm it is genuinely stylistic or advisory. Any finding that misleads implementation, breaks the spec/dependency graph, or contradicts an existing capability must be classified at least `Warning`. Prefer the more conservative severity when uncertain — this prevents the new threshold from becoming a regression vector.

5. When a retirement is detected, the routing report must include a one-line summary naming the capabilities being removed (parse `## REMOVED Requirements` for capability paths). The orchestrator's pre-flight reads `.openspec.yaml` once and stashes `retire_capabilities` on `state.json`. Subsequent phases PHASE1–PHASE5 should be skipped via `--from-phase PHASE6`.

6. **Max iterations reached without clean review:** document all remaining Critical issues via `osx log`, create `complete.json` with BLOCKED status (workflow stops).

## Output

Routing report with the single best editor for the aggregate finding set, plus the per-finding Severity / Artifact / File:line / Fix / Route lines. The skill never invokes the routed command itself.

## Guardrails

- **Read-only within PHASE0 itself.** The dispatched `osx-analyzer` agent stays `edit: deny`. Editor actions for in-orchestration routes are auto-handled by the engine (spawns the `osx-editor` agent + the `osc-update-change` slash command); out-of-orchestration routes still surface to the user.
- **Max 10 review iterations** (`--max-phase-iterations`).
- **Single source of artifact names**: `openspec status --change <name> --json` and `openspec instructions <id> --change <name> --json`. No hardcoded `proposal.md` / `specs/` / `design.md` / `tasks.md`.
- **Carry `--store <id>`** when the change is store-backed.
- **Early exit** if the first review returns clean.
- **State updates**: `osx state complete "$1"` on clean review **or Suggestion-only findings** (advisory; phase proceeds to PHASE1); `osx state set-routes "$1" --routes "<routed slash commands>"` on **any** Critical or Warning finding — the routed slash commands may be auto-fixable (`/osc-update-change`) or halt-and-surface (`/osc-continue-change`, `/osc-new-change`, `/osc-archive-change`, `/osc-explore`). The agent does NOT decide auto-fix vs halt — the engine does, by reading `routes_pending` from `state.json`: if every pending route is auto-fixable, the engine clears routes_pending, dispatches the fix itself (spawning the `osx-editor` agent + the relevant slash command), and re-enters PHASE0 to verify; if any route is non-auto-fixable or the set is mixed, the engine exits 0 with "Halted for routed commands" so the user can run the routed command(s) themselves. After the user runs the routed commands (ad-hoc path), the next `orchestrate` run re-enters PHASE0 to verify the fix. As a fallback for agents that emit `routed_to` in `decision-log.json` but forget `set-routes`, the engine also reads the latest `routed_to` from `decision-log.json` and dispatches auto-fix from there — see `engine._latest_routed_to`.
- **Never commits** (this phase never edits directly); the auto-fix dispatch is owned by the engine, which spawns the `osx-editor` agent that invokes `osx-commit` after applying fixes. Capture the commit hash in the decision-log entry when `artifacts_modified` is later recorded.
