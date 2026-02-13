# OpenSpec Core Skills

**Source**: Official OpenSpec workflow skills - track upstream, do not modify locally.

---

## Purpose

This directory contains the official OpenSpec workflow skills for AI coding assistants. These skills implement the OpenSpec change management workflow (explore → new → apply → archive).

**Do NOT modify these files directly.** They should be updated only by syncing with the upstream OpenSpec repository.

---

## Structure

```
openspec-core/
├── AGENTS.md                    # This file
├── .claude/
│   ├── commands/opsx/           # Claude Code slash commands
│   │   ├── apply.md
│   │   ├── archive.md
│   │   ├── continue.md
│   │   ├── explore.md
│   │   ├── ff.md
│   │   ├── new.md
│   │   ├── onboard.md
│   │   ├── sync.md
│   │   └── verify.md
│   └── skills/                  # Claude Code skills
│       └── openspec-*/SKILL.md
└── .opencode/
    ├── command/                 # OpenCode slash commands
    │   ├── opsx-apply.md
    │   ├── opsx-archive.md
    │   └── ...
    └── skills/                  # OpenCode skills
        └── openspec-*/SKILL.md
```

---

## Platform Differences

| Aspect | Claude Code | OpenCode |
|--------|-------------|----------|
| Commands directory | `commands/opsx/*.md` | `command/opsx-*.md` |
| Command naming | `new.md`, `apply.md` | `opsx-new.md`, `opsx-apply.md` |
| Command frontmatter | `name`, `description`, `category`, `tags` | `description` only |
| Skills directory | `skills/<name>/SKILL.md` | Same |
| Skill frontmatter | Full YAML with `metadata` | Same |

---

## Skills Reference

| Skill | Description |
|-------|-------------|
| `openspec-onboard` | Guided tutorial for first-time OpenSpec users |
| `openspec-new-change` | Start a new change with artifact workflow |
| `openspec-continue-change` | Continue working on an existing change |
| `openspec-apply-change` | Implement tasks from a change |
| `openspec-verify-change` | Verify implementation matches artifacts |
| `openspec-archive-change` | Archive a completed change |
| `openspec-ff-change` | Fast-forward: create all artifacts at once |
| `openspec-explore` | Think through problems without code changes |
| `openspec-sync-specs` | Sync specs with implementation state |
| `openspec-bulk-archive-change` | Archive multiple changes at once |

---

## Sync Strategy

To update these skills from upstream OpenSpec, run:

```bash
mise sync-core
```

This will:
1. Clone the OpenSpec repository (https://github.com/Fission-AI/OpenSpec)
2. Build the CLI from source
3. Generate .claude and .opencode files using `openspec init --tools claude,opencode`
4. Copy generated files to this directory

**Upstream**: https://github.com/Fission-AI/OpenSpec

---

## Related Directories

- `../resources/` - Extended utility skills (maintained locally)
- `../research/` - Documentation about AI assistant platforms
