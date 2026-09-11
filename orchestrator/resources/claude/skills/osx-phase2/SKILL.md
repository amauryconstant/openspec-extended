---
description: PHASE2 - Review
name: osx-phase2
---

# PHASE2: Review

Change: $1

> **Phase name**: engine canonical is `REVIEW`; skill is `osc-verify-change` ("Verification"). Both names refer to PHASE2. See `osx-workflow` §2.
> **Tools** — see `osx-workflow` §1.

## MANDATORY START

See `references/phase-protocol-common.md#mandatory-start`.

## MANDATORY CHECKPOINT: CLI Output Logging

Before PHASE2 verification:

1. `openspec status --change "$1" --json` → log via `osx log` with `cli_status` field
2. `openspec instructions apply --change "$1" --json` → log via `osx log` with `cli_instructions` field
3. `openspec show "$1" --diff --json` → log via `osx log` with `cli_diff` field (v1.11.0+; the envelope carries per-requirement `diff` blocks for MODIFIED deltas, `ADDED` payloads for new requirements, and `RENAMED` FROM/TO for renames)

## PURPOSE

Validate implementation matches artifacts — completeness, correctness, coherence.

## PROCESS

Load `osc-verify-change` (originally `openspec-verify-change`) skill for change "$1". Execute the skill's verification instructions exactly. Log the verification report via `osx log` in `verification_report` field. Do NOT modify the skill's verification report format.

The skill provides verification dimensions (completeness, correctness, coherence), issue classification (CRITICAL / WARNING / SUGGESTION), and specific recommendations for each issue.

### Embed requirement-level diff in verification-report.md

When writing `verification-report.md`, include a `## Delta inventory` section near
the top listing every ADDED, REMOVED, and RENAMED delta requirement (one line
each, citing the capability path and requirement id).

Below the inventory, include a `## Requirement diff` section that copies each
MODIFIED requirement's `diff` block verbatim from the `openspec show "$1" --diff
--json` payload you logged in step 3. Use the colorized form when writing for a
terminal; use the plain unified-diff form when writing to the file. Each diff
block must be fenced (```diff ... ```) so downstream tooling can parse it.

If `openspec show "$1" --diff --json` returns a `warning` field on any MODIFIED
delta, surface it in the report's `## Verification warnings` section above the
diff.

## AFTER VERIFICATION

**If CRITICAL or WARNING issues found**, determine the root cause:

**Case A — Artifacts are wrong** (specs/design unclear or incomplete):

1. Use `osc-update-change` (`/opsx:update`) skill to reconcile the affected artifacts. The typical verify-blamed-artifact case spans ≥2 artifacts (specs + design + tasks move together). For a clearly isolated single-artifact defect, `osx-modify-artifacts` is acceptable.
2. Commit the artifact changes.
3. Signal transition back to PHASE1:
   ```bash
   openspec-extended osx state transition "$1" --target PHASE1 --reason artifacts_modified --details "Brief description of what was fixed"
   ```
4. Log: "Artifacts modified via /opsx:update, transitioning to PHASE1 for re-implementation".

**Case B — Artifacts are correct, implementation is wrong**:

1. DO NOT modify artifacts.
2. Signal transition:
   ```bash
   openspec-extended osx state transition "$1" --target PHASE1 --reason implementation_incorrect --details "Brief description of what needs fixing"
   ```
3. Log: "Implementation incorrect, transitioning to PHASE1 for fixes".

**Case C — Same phase needs retry with different approach**:

```bash
openspec-extended osx state transition "$1" --target PHASE2 --reason retry_requested --details "Brief description of alternative approach"
```

Log: "Requesting retry with different approach".

**If NO CRITICAL or WARNING issues** (SUGGESTIONS OK):

1. Log: "Verification passed, no CRITICAL or WARNING issues". Log any SUGGESTION issues for future reference.
2. Mark phase complete:
   ```bash
   openspec-extended osx state complete "$1"
   ```
3. Script advances to PHASE3.

## SUGGESTION TRACKING

If SUGGESTION issues found (even when verification passed): append to `openspec/changes/$1/suggestions.md` as checkboxes with category tag (`[cosmetic]` / `[performance]` / `[future]` / `[docs]`). Each suggestion is a checkbox for future follow-up. This file is archived with the change.

## MANDATORY END

If artifacts were modified during this phase (CRITICAL/WARNING fixes): invoke `osx-commit` skill, commit changes, record commit hash in decision log and `iterations.json`.

See `references/phase-protocol-common.md#mandatory-end` for the standard end sequence.

## STATE FILE UPDATES

```bash
# Verification passed
openspec-extended osx state complete "$1"
```

## LOGGING

```bash
# decision log
openspec-extended osx log append "$1" --phase REVIEW --iteration N \
  --summary "..." --commit-hash "<hash or null>" --next-steps "..." \
  --extra '{"verification_result":"passed|failed","issues_found":{"critical":N,"warning":N,"suggestion":N},"verification_report_path":"openspec/changes/$1/verification-report.md","artifacts_modified":false,"cli_diff":{}}'

# iterations log
openspec-extended osx iterations append "$1" --phase REVIEW --iteration N \
  --commit-hash "<hash or null>" --notes "..." \
  --extra '{"verification_result":"passed|failed","issues_found":{},"artifacts_modified":false,"cli_diff":{}}'
```

Full schema in `references/osx-decision-logging.md`. Write the verification report to `openspec/changes/$1/verification-report.md` (full markdown allowed; do not modify the format).

## TRANSITION

Use `osx state transition` for explicit phase control:

| Scenario | Command | Reason |
|----------|---------|--------|
| Artifacts fixed | `osx state transition "$1" --target PHASE1 --reason artifacts_modified --details "..."` | Specs/design updated via `/opsx:update` (or `osx-modify-artifacts` for isolated defects) |
| Implementation wrong | `osx state transition "$1" --target PHASE1 --reason implementation_incorrect --details "..."` | Artifacts correct, code needs fix |
| Retry with new approach | `osx state transition "$1" --target PHASE2 --reason retry_requested --details "..."` | Try different solution |
| Review passed | `osx state complete "$1"` | Normal advance to PHASE3 |

## BLOCKER HANDLING

See `references/blocker-semantics.md` for the canonical signal. Phase-specific reasons:

- Verification fails with contradictory findings (Case A vs B unclear)
- Three failed retry attempts (Case C) without resolution

## SHELL ARGUMENT SAFETY

See `references/shell-argument-safety.md`.

<!--
# AUTO-GENERATED from opencode via `mise run sync:mirrors` — do not edit by hand.
Source: opencode/commands/osx-phase2.md
Regenerate: `mise run sync:mirrors`
-->
