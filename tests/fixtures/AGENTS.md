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
│   └── add-hello-script/          # Concrete code-producing change
│       └── specs/
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
distinguishes "halted with routes_pending" (printable route list)
from a true workflow crash.

## Conventions

- Fixtures are loaded by path — pass the fixture directory to the function under test.
- For new fixtures, mirror the OpenSpec change schema; the orchestrator's change validators are strict.
- For install fixtures, place new versions under `install/releases/download/v<VERSION>/`.

## See Also

- `tests/AGENTS.md` — Test layout
- `tests/integration/AGENTS.md` — Primary consumer
