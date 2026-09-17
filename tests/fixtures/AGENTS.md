---
paths:
  - "tests/fixtures/**"
---

# Test Fixtures

Static, read-only test data. Never mutate files in this directory.

## Layout

```
tests/fixtures/
├── changes/                       # OpenSpec change fixtures
│   ├── test-minimal/              # Bare-minimum valid change
│   │   ├── proposal.md
│   │   ├── design.md
│   │   ├── tasks.md
│   │   └── specs/
│   ├── add-hello-script/          # Audit-clean code-producing change
│   │   └── specs/
│   └── add-self-heal-script/      # Audit-dirty code-producing change
│       └── specs/                 #   ships with PHASE0 findings on
│                                  #   existing artifacts; the engine's
│                                  #   auto-fix dispatch must reconcile
│                                  #   them before the workflow advances
└── install/                       # Install-flow fixtures
    └── releases/
        └── download/
            └── v0.19.0/           # Fake release tarball/manifest for install tests
```

## Change Fixture Format

Each change directory is a self-contained OpenSpec change:

| File | Purpose |
|------|---------|
| `proposal.md` | Why and what |
| `design.md` | Approach and trade-offs |
| `tasks.md` | Numbered checklist of work items |
| `specs/<capability>/spec.md` | Delta specs (added/modified/removed requirements) |

## Audit-pass invariant

Fixtures consumed by `full-workflow.bats` (gated on `E2E_CONFIRM=1`)
must satisfy the orchestrator's PHASE0 audit — the suite exercises the
full PHASE0-PHASE6 flow end-to-end. Today that means new-capability
specs declare a `## Purpose` section (≥50 characters) before
`## ADDED Requirements`. When the audit rules tighten upstream,
update the fixture to satisfy them; the bats failure log now
distinguishes "halted with routes_pending" (printable route list,
classified by auto-fixable vs halt-and-surface) from a true workflow
crash.

## `add-self-heal-script` (auto-fix regression sentinel)

This fixture deliberately ships with PHASE0 findings on **existing**
artifacts so the orchestrator's auto-fix dispatch (`osc-update-change`)
is exercised end-to-end. It is consumed by
`tests/e2e/self-heal-workflow.bats` (gated on `E2E_CONFIRM=1`). The
fixture seeds:

- **Cross-artifact contradiction**: `proposal.md` says the script
  "exits with code 0 on invalid flags" while `design.md` and `spec.md`
  say "code 1". The audit's cross-artifact consistency check flags
  this as Critical; the auto-fix reconciles by editing `proposal.md`
  to say "code 1", matching the other two.

The auto-fix must successfully reconcile this contradiction; the
archived `proposal.md` is asserted to say "code 1 on invalid flags"
(`auto-fix: proposal.md exit-code mismatch was corrected`). If the
engine reverts to halting on `/osc-update-change`, the bats file's
`phase0: no halt-for-routed-commands for autofixable route` sentinel
fails with a clear regression message.

When the audit rules tighten upstream such that this fixture's
findings resolve as Suggestion-only, escalate the contradiction
(e.g. move the wrong exit-code statement to a more prominent
location, or add a second contradiction) so the route remains
Critical/Warning on existing artifacts.

## Conventions

- Fixtures are loaded by path — pass the fixture directory to the function under test.
- For new fixtures, mirror the OpenSpec change schema; the orchestrator's change validators are strict.
- For install fixtures, place new versions under `install/releases/download/v<VERSION>/`.

## See Also

- `tests/AGENTS.md` — Test layout
- `tests/integration/AGENTS.md` — Primary consumer
