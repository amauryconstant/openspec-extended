# Claude Code Platform Resources (Skills Side)

Phase-4 mirror for the skills-side Claude tree. Mirrors the
skills-side OpenCode tree at `skills/resources/opencode/`.

## Layout

```
skills/resources/claude/
├── manifest.toml
├── skills/
│   ├── osx-commit/                       # canonical skill mirror
│   ├── osx-review-artifacts/             # canonical skill mirror
│   ├── osx-review-test-compliance/       # canonical skill mirror
│   ├── osx-review/SKILL.md               # dual-emit of osx-review command (modern)
│   └── osx-verify-tests/SKILL.md         # dual-emit of osx-verify-tests command (modern)
└── commands/
    └── osx/
        ├── review.md                     # legacy slash-command form
        └── verify-tests.md               # legacy slash-command form
```

## See Also

- `orchestrator/resources/claude/AGENTS.md` — Sibling orchestrator-side Claude mirror
- `orchestrator/resources/AGENTS.md` — Resource types, manifest format
- `skills/resources/opencode/AGENTS.md` — Sibling platform (canonical for skills side)
- `research/claude-code-docs.md` — Claude Code capability reference
