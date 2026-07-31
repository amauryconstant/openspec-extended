# Blocker Semantics

A blocker is **unrecoverable within the current phase**. The orchestrator halts on `complete.json` with `status: BLOCKED`. This reference distinguishes blockers from fixable failures.

## Signal a blocker

```bash
openspec-extended osx complete set "$1" BLOCKED --blocker-reason "Specific reason"
```

The orchestrator detects `complete.json` and halts. The user investigates.

## When to signal a blocker

A blocker is **not**:

- Failing tests → fix in PHASE1, commit, re-iterate.
- Unclear specs → route via `osx-review-artifacts` (PHASE0), fix via `/osx-modify` or `/opsx:update`; the user applies the fix outside the dispatched phase.
- Missing dependency → add it.
- Implementation bug → transition to PHASE1 with `--reason implementation_incorrect`.
- Pre-commit hook failure → fix and re-stage.

A blocker **is**:

- Third-party API or external dependency unavailable.
- Missing required access (credentials, network).
- Contradictory specs that block all paths.
- Three pre-commit hook failures with no progress.

## Resume after a blocker

```bash
# Fix the underlying issue first, then:
rm openspec/changes/<change>/complete.json
openspec-extended orchestrate <change>            # resumes from state.json
# or skip ahead:
openspec-extended orchestrate <change> --from-phase PHASE3
```

## See also

- `references/phase-protocol-common.md` — the full phase command spine.