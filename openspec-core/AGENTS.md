# OpenSpec Core Skills

**Source**: Official OpenSpec workflow skills - track upstream, do not modify locally.

**Version**: v1.2.0 (custom profile with all 11 workflows)

---

## Purpose

This directory contains the official OpenSpec workflow skills for AI coding assistants. These skills implement the OpenSpec change management workflow.

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
│   │   ├── bulk-archive.md
│   │   ├── continue.md
│   │   ├── explore.md
│   │   ├── ff.md
│   │   ├── new.md
│   │   ├── onboard.md
│   │   ├── propose.md
│   │   ├── sync.md
│   │   └── verify.md
│   └── skills/                  # Claude Code skills
│       └── openspec-*/SKILL.md
└── .opencode/
    ├── commands/                # OpenCode slash commands
    │   ├── opsx-apply.md
    │   ├── opsx-archive.md
    │   ├── opsx-bulk-archive.md
    │   ├── opsx-continue.md
    │   ├── opsx-explore.md
    │   ├── opsx-ff.md
    │   ├── opsx-new.md
    │   ├── opsx-onboard.md
    │   ├── opsx-propose.md
    │   ├── opsx-sync.md
    │   └── opsx-verify.md
    └── skills/                  # OpenCode skills
        └── openspec-*/SKILL.md
```

---

## Platform Differences

| Aspect | Claude Code | OpenCode |
|--------|-------------|----------|
| Commands directory | `commands/opsx/*.md` | `commands/opsx-*.md` |
| Command naming | `new.md`, `apply.md` | `opsx-new.md`, `opsx-apply.md` |
| Command frontmatter | `name`, `description`, `category`, `tags` | `description` only |
| Skills directory | `skills/<name>/SKILL.md` | Same |
| Skill frontmatter | Full YAML with `metadata` | Same |

---

## Skills Reference (11 Workflows)

| Skill | Command | Description |
|-------|---------|-------------|
| `openspec-propose` | `/opsx:propose` | Create change + all artifacts in one step (v1.2.0) |
| `openspec-explore` | `/opsx:explore` | Think through problems without code changes |
| `openspec-new-change` | `/opsx:new` | Start a new change with artifact workflow |
| `openspec-continue-change` | `/opsx:continue` | Continue working on an existing change |
| `openspec-apply-change` | `/opsx:apply` | Implement tasks from a change |
| `openspec-ff-change` | `/opsx:ff` | Fast-forward: create all artifacts at once |
| `openspec-verify-change` | `/opsx:verify` | Verify implementation matches artifacts |
| `openspec-sync-specs` | `/opsx:sync` | Sync specs with implementation state |
| `openspec-archive-change` | `/opsx:archive` | Archive a completed change |
| `openspec-bulk-archive-change` | `/opsx:bulk-archive` | Archive multiple changes at once |
| `openspec-onboard` | `/opsx:onboard` | Guided tutorial for first-time OpenSpec users |


---

## Sync Strategy

To update these skills from upstream OpenSpec, run:

```bash
mise run sync-core
```

This will:
1. Clone the OpenSpec repository (https://github.com/Fission-AI/OpenSpec)
2. Build the CLI from source
3. Configure custom profile with all 11 workflows
4. Generate .claude and .opencode files using `openspec init --tools claude,opencode --profile custom`
5. Copy generated files to this directory

**Upstream**: https://github.com/Fission-AI/OpenSpec

---

## Related Directories

- `../resources/` - Extended utility skills (maintained locally)
- `../research/` - Documentation about AI assistant platforms
