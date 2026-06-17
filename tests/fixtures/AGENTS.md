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

## Conventions

- Fixtures are loaded by path — pass the fixture directory to the function under test.
- For new fixtures, mirror the OpenSpec change schema; the orchestrator's change validators are strict.
- For install fixtures, place new versions under `install/releases/download/v<VERSION>/`.

## See Also

- `tests/AGENTS.md` — Test layout
- `tests/integration/AGENTS.md` — Primary consumer
