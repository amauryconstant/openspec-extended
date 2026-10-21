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
│   └── add-hello-script/          # Audit-clean code-producing change
│       └── specs/
└── install/                       # Install-flow fixtures
    ├── VERSION                    # Version string used by install.bats
    ├── pack.sh                    # Builds the fake tarball on demand
    └── releases/download/v<VER>/  # Fake release tarball + SHA256SUMS
```

## Consumers

| Fixture tree | Consumer |
|--------------|----------|
| `changes/` | `tests/e2e/helpers/e2e-helpers.bash::copy_fixture` (copied into a bats tmpdir), and `tests/contract/test_upstream_envelopes.py` (read in place) |
| `install/` | `tests/unit/install.bats` via `tests/helpers/test-helpers.bash` (`$FIXTURES_DIR`) |

No test under `tests/integration/` reads this directory.

## Change Fixture Format

Each change directory is a self-contained OpenSpec change:

| File | Purpose |
|------|---------|
| `proposal.md` | Why and what |
| `design.md` | Approach and trade-offs |
| `tasks.md` | Numbered checklist of work items |
| `specs/<capability>/spec.md` | Delta specs (added/modified/removed requirements) |

## Audit-pass invariant

Fixtures consumed by `full-workflow.bats` (gated on `E2E_CONFIRM=1`) must
satisfy the orchestrator's PHASE0 audit — the suite exercises the full
PHASE0-PHASE6 flow end-to-end. Today that means new-capability specs declare
a `## Purpose` section (≥50 characters) before `## ADDED Requirements`. When
the audit rules tighten upstream, update the fixture to satisfy them; the
bats failure log distinguishes "halted with routes_pending" (printable route
list, classified by auto-fixable vs halt-and-surface) from a true workflow
crash.

## Conventions

- Fixtures are loaded by path — pass the fixture directory to the function
  under test. `copy_fixture` copies out of `changes/`; nothing writes back.
- For new fixtures, mirror the OpenSpec change schema; the orchestrator's
  change validators are strict.
- For install fixtures, place new versions under
  `install/releases/download/v<VERSION>/` and update `install/VERSION`.

## See Also

- `tests/AGENTS.md` — Test layout
- `tests/e2e/AGENTS.md` — Primary consumer of `changes/`
- `tests/unit/AGENTS.md` — Primary consumer of `install/`