# Design: Self-Heal Script

## Context

The orchestrator's PHASE0 audit emits findings on **existing** artifacts
when the change is in flux. The auto-fix route (`/osc-update-change`)
is engine-handled; other routes (`/osc-continue-change`,
`/osc-new-change`, `/osc-archive-change`, `/osc-explore`) halt the
phase for user judgment. To exercise the auto-fix path end-to-end we
need a fixture whose initial state ships with findings the skill can
resolve by editing existing files — and which has no findings that
require user judgment (so the auto-fix is the only sensible route).

This fixture is engineered with two such findings:

1. **Critical** — `proposal.md` falsely claims the script "exits with
   code 0 on invalid flags", contradicting the design. PHASE0 flags
   the cross-artifact inconsistency as Critical.
2. **Warning** — `proposal.md` claims an unrelated decision lives at a
   specific line number in `design.md` that does not match. PHASE0
   flags the wrong line reference as Warning.

Both findings are resolvable by editing existing files (the proposal
and the design). The auto-fix dispatches `osc-update-change` (which
edits existing artifacts only), reconciles the two, and PHASE0 re-reviews
clean.

## Goals / Non-Goals

**Goals:**

- Produce a self-contained executable `scripts/self-heal.sh` that
  prints `Hello, {NAME}!` (default `World`), accepts `--name NAME`,
  `--help`, and exits 0 on success / 1 on invalid flags.
- Match the `add-hello-script` precedent (shebang, strict mode,
  `readonly`, `local`, `usage()`, `main()`, `main "$@"`).
- Embed two PHASE0 findings the auto-fix dispatch can resolve: a
  cross-artifact contradiction and a wrong line reference.

**Non-Goals:**

- Configuration file support.
- Internationalization.
- Logging / verbose / diagnostic flags.
- A `--version` flag.

## Decisions

- **Shebang `#!/usr/bin/env bash`** — Portability across distributions
  where `bash` lives at different paths.
- **Strict mode `set -euo pipefail`** — Project bash convention; fail
  fast on errors and unset variables.
- **Exit code 1 on invalid flags** — Consistent with `add-hello-script`
  and the project-wide CLI convention.
- **`main "$@"` invocation** — Single entry point forwarding all
  arguments unmodified.
- **Auto-fixable fixture findings** — The fixture ships with two
  findings the `osc-update-change` skill resolves in a single pass:
  - The `proposal.md` text contradicts `design.md` on the
    invalid-flag exit code (Critical).
  - The `proposal.md` references an unrelated line number in
    `design.md` (Warning).

## Risks / Trade-offs

- **Audit findings depend on schema strictness** → Mitigation: the
  `osx-review-artifacts` skill applies the severity calibration rule
  (`Suggestion` ↔ `Warning` ↔ `Critical`); the fixture's findings
  resolve as Critical/Warning on existing artifacts so the route is
  `/osc-update-change` regardless of upstream severity-tightening.
- **AI model drift could re-resolve findings as Suggestion-only** →
  Mitigation: this is a regression-test fixture; if upstream tightens
  rules and these findings drop to Suggestion, update the fixture to
  escalate them.
