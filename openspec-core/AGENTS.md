# OpenSpec Core Skills

**Source**: Official OpenSpec workflow skills - track upstream, do not modify locally.

**Version**: v1.6.0 (custom profile with all 12 workflows)

**v1.6.0 highlights**:
- Adds `openspec-update-change` (`/opsx:update`): revise existing planning artifacts in place and reconcile them bidirectionally.
- Generated skills and `/opsx:*` slash commands now carry `allowed-tools: Bash(openspec:*)` in frontmatter (auto-approves the openspec CLI).

**v1.5.0 highlight**: introduces "stores" — standalone OpenSpec repos registered on this machine via `openspec store <subcommand>`. Workflows check `openspec store list --json` and pass `--store <id>` on `new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`. Without a store, commands act on the nearest local `openspec/` root.

---

## Purpose

This directory contains the official OpenSpec workflow skills for AI coding assistants. These skills implement the OpenSpec change management workflow.

**Do NOT modify these files directly.** They should be updated only by syncing with the upstream OpenSpec repository.

---

## Structure

```
openspec-core/
├── AGENTS.md                    # This file
├── source/                      # Upstream subtree (git subtree pull; do not edit locally)
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

## Skills Reference (12 Workflows)

| Skill | Command | Description |
|-------|---------|-------------|
| `openspec-propose` | `/opsx:propose` | Create change + all artifacts in one step (v1.2.0) |
| `openspec-explore` | `/opsx:explore` | Think through problems without code changes |
| `openspec-new-change` | `/opsx:new` | Start a new change with artifact workflow |
| `openspec-continue-change` | `/opsx:continue` | Continue working on an existing change |
| `openspec-apply-change` | `/opsx:apply` | Implement tasks from a change |
| `openspec-update-change` | `/opsx:update` | Revise existing planning artifacts and reconcile them (v1.6.0) |
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

The `source/` subtree tracks upstream directly. This will:
1. Refuse if `source/` has uncommitted local changes
2. Discover the latest stable release tag (e.g., `v1.6.0`) via `git ls-remote --tags`
3. `git subtree pull` from that tag into `source/` (squashed)
4. Build the CLI in-place from `source/`
5. Configure custom profile with all 12 workflows
6. Generate `.claude` and `.opencode` files via `openspec init --tools claude,opencode --profile custom`
7. Copy generated files into this directory

**Upstream**: https://github.com/Fission-AI/OpenSpec (ref: latest stable tag, e.g. `v1.6.0`)

---

## Related Directories

- `../resources/` - Extended utility skills (maintained locally)
- `../research/` - Documentation about AI assistant platforms
