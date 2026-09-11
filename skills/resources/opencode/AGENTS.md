# OpenCode Platform Resources (Skills Side)

Phase-4 split site for the skills-side OpenCode tree. Houses the
gap-filling skills (`osx-commit`, `osx-review-artifacts`,
`osx-review-test-compliance`) and their slash commands
(`osx-review`, `osx-verify-tests`). The orchestrator-side OpenCode tree
lives under `orchestrator/resources/opencode/`.

## Layout

```
skills/resources/opencode/
├── manifest.toml            # single unified manifest (split happens in Phase 5)
├── skills/                  # gap-filling skills (review, commit, test-compliance)
│   ├── osx-commit/
│   ├── osx-review-artifacts/
│   └── osx-review-test-compliance/
└── commands/                # gap-filling commands
    ├── osx-review.md
    └── osx-verify-tests.md
```

## Naming

All extended resources use the `osx-` prefix. The 3 skills and 2 commands here are listed in `manifest.toml`.

## See Also

- `orchestrator/resources/AGENTS.md` — Resource types, manifest format
- `orchestrator/resources/opencode/AGENTS.md` — Sibling orchestrator-side docs
- `skills/resources/opencode/commands/` — Slash command files
- `skills/resources/claude/AGENTS.md` — Mirror platform
- `research/opencode-docs.md` — Platform capability reference
