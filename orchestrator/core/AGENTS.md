# OpenSpec Core Skills

**Source**: Official OpenSpec workflow skills - track upstream, do not modify locally.

**Version**: v1.11.0 (custom profile with all 12 workflows)

**v1.11.0 highlights** (current):
- `openspec status --all` — single-process sweep of every active change; `--all --json` emits `{"changes": [ … ], "root"}` sorted by change name; a failing change contributes a diagnostic in place rather than aborting the sweep; partial failure exits 1 with the complete JSON envelope preserved. Mutually exclusive with `--change`.
- `openspec show <change> --diff` — renders each MODIFIED requirement as a colorized unified diff against the requirement it replaces in the main spec; ADDED requirements print in full; REMOVED print authored Reason/Migration; RENAMED print FROM/TO. `--json --diff` extends each MODIFIED delta with a `diff` and `warning` field.
- `openspec validate` now warns on the `## Purpose` placeholder that archive writes for new capabilities (default warn; `--strict` fails). The marker is recognized wherever it appears in the Purpose; fenced code is excluded.
- Explore skill now requires explicit, scope-bound confirmation before any write-capable action (create/edit/move/delete). Read-only commands remain unconfirmed; expanding the confirmed scope requires a fresh confirmation.
- Explore diagrams are plain ASCII only (`+`, `-`, `|`, `-->`); Unicode glyphs drift across terminals/fonts.
- `openspec archive` preserves a requirement's original position when renaming it instead of moving the renamed block to the end of the spec.

**v1.10.0 highlights**:
- `openspec init --language <language>` — configure the language used for artifacts in new projects.
- `npm postinstall` script removed (no `allow-scripts` warning; completion tip now prints from the CLI on first run instead).
- Spec-driven `specs` instruction now reads/edits main specs through the store-aware root (`<planningHome.root>/openspec/specs/...`).
- `openspec update` no longer shows the IDE-restart hint for CLI-only tools (Claude Code, Codex, Gemini CLI).
- Archive retirement guidance: when a change removes a capability's last requirement, archive names the blocking lines and reports a `retire_capabilities` marker that is present but cannot be honored.
- Generated tasks must state how completion can be verified.

**v1.9.0 highlights**:
- Command Code adapter (`openspec init --tools commandcode`) — skills-only at `.commandcode/skills/`, invoked as `/openspec-*`.
- `openspec validate --archived` — opt-in CI gate that every change under `changes/archive/` has all `tasks.md` checkboxes ticked; exits non-zero otherwise.
- Apply workflow now surfaces unexpected scope instead of silently narrowing/deferring/simplifying away specified behavior.
- `openspec archive` no longer writes ANSI cursor-move sequences to a redirected or captured stdout.
- Spec rebuilt trailing newlines are now exactly one final LF (no double-newline).
- Blank lines around `## Requirements` are preserved on sync/archive.
- `openspec validate --all` and `openspec list --json` no longer silently pass when run outside an OpenSpec project.

**v1.8.0 highlights**:
- Vendor-neutral `agents` target (`openspec init --tools agents`) — installs workflow skills to `.agents/skills/openspec-*/SKILL.md` (skills-only, no slash commands). `--tools all` includes it.
- GitHub Copilot coding-agent setup is now opt-in (`openspec init` asks, default No; override with `--copilot-cloud` / `--no-copilot-cloud`; persisted as `githubCopilot.cloudAgent` in `openspec/config.yaml`).
- Atlassian Rovo Dev CLI (`openspec init --tools rovodev`) — skills-only at `.rovodev`.
- MiniMax Code — global skills-only target.
- Codex skills now live under `.agents/skills/` (canonical location); existing `.codex` skills directories migrate in place; `.codex` legacy `.md` files retained.
- `openspec status` separates planning from implementation: `isPlanningComplete` is distinct from overall progress; `isComplete` is kept as an alias.
- `retire_capabilities: true` change metadata — a change whose REMOVED entries take a capability's last requirement may be archived; the capability's main spec is deleted instead of aborting.
- `--tools windsurf` renamed to `devin`; writes to `.devin/`, reads `.windsurf/` as legacy fallback. `--tools windsurf` still resolves.
- `openspec archive` no-arg exits 1 (was exit 0); reads confirmations as plain text when stdout/stdin is not a terminal.
- `openspec validate` reports a MODIFIED requirement that omits a scenario the main spec still has (the same loss archive already refuses to apply).
- `SHALL`/`MUST` is treated as guidance in normal mode so non-English requirements validate; strict mode still enforces.
- `telemetry.enabled` honored in global config; `false` disables telemetry and update checks.

**v1.7.0 highlights** (historical context):
- Three new tools supported via `openspec init --tools`: `codeartsagent`, `hermes` (skills-only), `zcode`. Codex is now skills-only (`$openspec-<skill>` invocation).
- `openspec config set defaultStore <id>` — machine-level fallback root. Status `root` block reports `source: "global_default"` when used; all explicit forms still win on precedence.
- `skip_specs: true` change metadata for pure refactors, tooling, or docs changes that have no spec-level behavior.
- `openspec status --json` now reports a `requires` array on each artifact (additive, backward-compatible) — agents can derive the full transitive required set from one call.
- New read-only `openspec instructions archive` surface returns archive inputs for the selected root (mirrors the proposal/apply variants).
- `openspec update` offers to upgrade a stale CLI interactively when behind upstream (bypassed by `OPENSPEC_NO_UPDATE_CHECK` / `DO_NOT_TRACK=1` / `OPENSPEC_TELEMETRY=0` / CI detection).
- `openspec archive` no longer stacks a second date prefix on already-date-prefixed names; tolerates already-synced REMOVED/RENAMED deltas as no-ops; uses a delta's `## Purpose` as the new main spec's Purpose when present.
- `openspec archive` runs the spec sync inline before moving the change folder — no more archive-after-sync races.
- `--change` accepts any change name that exists on disk (e.g. `2026-07-04-voice-copilot-v1`); kebab-case still enforced on create.
- `design.md` no longer restates `proposal.md` — the schema's design instruction and template now state the (why,what) vs (how) boundary explicitly.
- `--tools windsurf` renamed to `devin`; `.windsurf/` still read as legacy fallback, new commands write to `.devin/`.
- `openspec new change` accepts numeric-prefixed names like `100-add-feature`.
- Static `skills/<name>/SKILL.md` files published so `npx skills add Fission-AI/OpenSpec` works.
- Multi-select prompts render with `[x]`/`[ ]` checkbox markers.

**v1.6.0 highlights** (historical context, unchanged through v1.11.0):
- Adds `openspec-update-change` (`/opsx:update`): revise existing planning artifacts in place and reconcile them bidirectionally.
- Generated skills and `/opsx:*` slash commands carry `allowed-tools: Bash(openspec:*)` in frontmatter (auto-approves the openspec CLI).

**v1.5.0 highlight** (historical context): introduces "stores" — standalone OpenSpec repos registered on this machine via `openspec store <subcommand>`. Workflows check `openspec store list --json` and pass `--store <id>` on `new change`, `status`, `instructions`, `list`, `show`, `validate`, `archive`, `doctor`, `context`. Without a store, commands act on the nearest local `openspec/` root. v1.7.0 layers `defaultStore` config on top for a per-machine fallback that sits below all other resolution paths.

---

## Purpose

This directory contains the official OpenSpec workflow skills for AI coding assistants. These skills implement the OpenSpec change management workflow.

**Do NOT modify these files directly.** They should be updated only by syncing with the upstream OpenSpec repository.

---

## Structure

```
orchestrator/core/
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
| `openspec-update-change` | `/opsx:update` | Revise existing planning artifacts and reconcile them (v1.6.0; unchanged through v1.11.0) |
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
2. Discover the latest stable release tag (e.g., `v1.11.0`) via `git ls-remote --tags`
3. `git subtree pull` from that tag into `source/` (squashed)
4. Build the CLI in-place from `source/`
5. Configure custom profile with all 12 workflows
6. Generate `.claude` and `.opencode` files via `openspec init --tools claude,opencode --profile custom`
7. Copy generated files into this directory

**Upstream**: https://github.com/Fission-AI/OpenSpec (ref: latest stable tag, e.g. `v1.11.0`)

---

## Related Directories

- `../resources/` - Extended utility skills (maintained locally)
- `../research/` - Documentation about AI assistant platforms
