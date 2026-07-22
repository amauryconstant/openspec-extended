---
description: PHASE0 - Artifact Review (read-only audit + routing; do not edit here)
agent: osx-analyzer
---

## Tools Available

| Tool | Usage |
|------|-------|
| `osx` | `openspec-extended osx <domain> <action> [args]` - unified OpenSpec tool |
| Domains: `ctx`, `state`, `iterations`, `log`, `complete`, `validate` |

# PHASE0: Artifact Review

Change: $1

## MANDATORY START

1. Load context:
   !`openspec-extended osx ctx get "$1"`
2. Confirm `phase` is PHASE0
3. Review `history.iterations_recorded` for previous attempts
4. Load skills: `osx-concepts` and `osx-workflow` (both reference only)

## PURPOSE

Ensure OpenSpec artifacts are excellent before implementation. Validate:
- Schema-driven format conformance (per `openspec instructions <id> --json`'s `template` and `rules`).
- Cross-artifact consistency across the `dependencies` / `unlocks` graph.
- Implementation readiness (dependencies, scope achievability, task specificity).

PHASE0 is dispatched as `osx-analyzer` (`edit: deny`, `question: deny`).
**Do not edit artifacts inside this phase.** The phase produces a routing
report; the user or another invocation performs the edits via
`osx-modify-artifacts` or `/opsx:update`.

## PROCESS

1. Load and use `osx-review-artifacts` skill for change "$1"
2. Execute review instructions from the skill
3. Review findings bucketed as Critical / Warning / Suggestion.

4. **Routing rule.** Produce a routing recommendation using this table:

   | Finding pattern | Recommended route |
   |---|---|
   | All findings target a single artifact AND no coherence-level finding | `/osx-modify <name> <artifact-id>` |
   | Findings span ≥2 artifacts OR any coherence-level finding | `/opsx:update <name>` |
   | Missing artifacts | `/opsx:continue <name>` |
   | All clean | mark phase complete and hand off to PHASE1 |

5. **Do not fix in this phase.** The dispatched agent cannot write
   (`edit: deny`). Surface the routing to the user; they (or a follow-up
   slash command invocation) perform the fixes.

6. Track iteration via `osx log` and `osx iterations` per the §DECISION LOG /
   §ITERATIONS.JSON sections below. Do **not** include an `artifacts-modified`
   list unless the change's artifacts were modified by something other than
   this phase.

7. After the user has applied fixes via `/osx-modify` or `/opsx:update`, the
   next PHASE0 iteration runs review again. Repeat up to the iteration cap
   defined by the §GUARDRAILS.

8. IF MAX ITERATIONS (10) reached without clean review:
   a. Document all remaining Critical issues via `osx log`
   b. Create `complete.json` with BLOCKED status (workflow stops)

## MANDATORY END

PHASE0 never commits artifacts because it never edits them. The user invokes
`osx-commit` (or another workflow) after running the routed editor.

When artifacts are later modified by `/osx-modify` or `/opsx:update` and the
PHASE0 transition log records `artifacts_modified`, record the commit hash
in the decision log entry below.

## STATE FILE UPDATES

Phase complete (clean review):
```bash
openspec-extended osx state complete "$1"
```

Critical blocker (cannot proceed):
```bash
openspec-extended osx complete set "$1" BLOCKED --blocker-reason "[Describe the blocking issue]"
```

## DECISION LOG

Append entry:
```bash
openspec-extended osx log append "$1" \
  --phase ARTIFACT_REVIEW \
  --iteration N \
  --summary "Brief summary of this iteration" \
  --commit-hash "<hash or null>" \
  --next-steps "Proceed to PHASE1 or continue review" \
  --issues '{"critical":N,"warning":N,"suggestion":N}' \
  --extra '{"routed_to":"/osx-modify or /opsx:update or /opsx:continue"}'
```

## ITERATIONS.JSON

Append entry:
```bash
openspec-extended osx iterations append "$1" \
  --phase ARTIFACT_REVIEW \
  --iteration N \
  --commit-hash "<hash or null>" \
  --notes "Brief summary" \
  --extra '{"artifacts_audited":["<id>"],"issues_found":{"critical":N,"warning":N,"suggestion":N},"routed_to":"/osx-modify or /opsx:update or /opsx:continue"}'
```

## GUARDRAILS

- Read-only in this phase. Editor actions belong to `/osx-modify` (single
  artifact) or `/opsx:update` (multi-artifact / coherence drift).
- Max 10 review iterations.
- Single source of artifact names: `openspec status --change <name> --json`
  and `openspec instructions <id> --change <name> --json`. No hardcoded
  `proposal.md`/`specs/`/`design.md`/`tasks.md`.
- Carry `--store <id>` when the change is store-backed.
- Early exit if the first review returns clean.

## SHELL ARGUMENT SAFETY

When passing free-text to `--summary`, `--next-steps`, or any other shell argument, **DO NOT use backticks** (`` `like this` ``) for inline code references. Backticks are interpreted as command substitution by bash/zsh — the shell will execute whatever is inside the backticks and substitute its output. In zsh, `` `local` `` dumps the entire shell environment (PATH, tokens, internal variables) into your string, which then gets stored verbatim in `decision-log.json`.

**Use instead:**

- Single quotes: `'local'`
- Double quotes: `"local"`
- Plain text: `local`
- Markdown `code` (which uses backticks in raw form, NOT shell backticks) — fine only when the argument is not passed through a shell

If `osx log append` returns `input_too_long` or `input_tainted`, remove the backticks from the offending argument and retry.
