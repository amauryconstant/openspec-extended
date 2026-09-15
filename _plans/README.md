# Upstream Parity Plan — openspec-extended → OpenSpec Core AI_TOOLS

Bring `openspec-extended` to full parity with the AI tools supported by upstream OpenSpec Core (`orchestrator/core/source/src/core/config.ts:AI_TOOLS`). Today we ship 2; the upstream catalogue is 39.

## Status

The 4 preparatory commits referenced in the user's prompt have already landed on the local main branch (v1.10.4 onward). The plan starts from that baseline.

### Already landed (4 preparatory commits)

| Commit | Subject | What it did |
|--------|---------|-------------|
| `fb1cffc7` | Expand ToolAdapter surface for skills-only adapters | Added 5 fields: `ask_tool`, `install_hint`, `cross_ref_prefix`, `runner_args`, `frontmatter_extras`; dropped `_FALLBACK_BINARY`; `GenericPrintRunner` consumes `runner_args`; `check-platform-hardcodes` extended |
| `b9305ac5` | Wire purge and validate hooks for skills-only adapters | `purge_managed_resources` and `validate_deployment` honour `commands_style="skills-only"` |
| `18f97d02` | Render extended slash commands as skill mirrors for skills-only adapters | Skill-mirror rendering for `commands_style != "flat"` paths |
| `e56acaf2` | Document per-adapter fields and add cursor to the test matrix | Per-adapter field documentation in `.opencode/rules/`; synthetic `cursor` adapter in `test_install_multi.py` and friends |

### Remaining work (this plan)

| Release | PR(s) | Coverage shipped | ToolAdapter fields added | Status |
|---------|-------|------------------|--------------------------|--------|
| v1.10.x | PR1 (Phase 2A) | 2 (no change) | 0 | ⏳ planned |
| v1.11.0 | PR2 + PR3 + PR4 | **8** (opencode, claude, cursor, codex, kimi, forgecode, qwen, kiro) | 3 (`requires_ide_restart`, `shared_skills_root`, `setup_note`) | ⏳ planned |
| v1.12.0 | PR5A + PR5B + PR5C | **~35** (adds ~27 Low-effort adapters) | 0 (uses existing fields) | ⏳ planned |
| v1.12.x | PR6 | **~38** (antigravity, github-copilot, hermes, devin) + aliases + legacy migration | 2 (`legacy_skills_dirs`, `TOOL_ID_ALIASES`) | ⏳ planned |
| v1.13.0+ | PR7 | **39** (minimax-code with global skills dir) | 1 (`global_skills_dir`) | ⏳ planned |

> **Net new `ToolAdapter` fields across the remaining rollout: 6.** Each one is locked by `TestAdapterFieldDefaults`. Every new field's default preserves shipped behaviour byte-for-byte. The 5 fields added by the 4 preparatory commits (`ask_tool`, `install_hint`, `cross_ref_prefix`, `runner_args`, `frontmatter_extras`) are already shipped.

## Quick links

- [00-decisions.md](00-decisions.md) — the 5 locked decisions
- [01-current-state.md](01-current-state.md) — what's blocking adapter #3
- [02-coverage-matrix.md](02-coverage-matrix.md) — full 39-tool matrix
- [03-risks.md](03-risks.md) — risk register
- [pr/](pr/) — one file per PR with full acceptance criteria
- [reference/](reference/) — adapter field reference, cross-cutting concerns
- [research/](research/) — raw outputs from the 4 exploration agents

## Phase map

```
Phase 2A (PR1) ── validate the abstraction against every CommandsStyle value
       │
       ▼
Phase 2B prep (PR2) ── ship 3 new ToolAdapter fields; no new adapters
       │
       ▼
Phase 2B main (PR3) ── ship 4 first-party adapters (cursor, codex, kimi, forgecode)
       │
       ▼
Phase 2C (PR4) ── extension-aware deploy (.toml, .prompt.md); 2 more adapters (qwen, kiro)
       │
       ▼
Phase 3 part 1 (PR5A + PR5B + PR5C) ── bulk ship ~27 Low-effort adapters in 3 alphabet-split sub-PRs
       │
       ▼
Phase 3 part 2 (PR6) ── legacy migration, aliases, ~4 Medium-tier adapters
       │
       ▼
Phase 4 (PR7) ── global skills dir + the only Heavy adapter (minimax-code)
```

## Wall-clock estimate

| PR | Effort | Cumulative |
|----|--------|------------|
| PR1 (Phase 2A) | 1 day | 1 day |
| PR2 (Phase 2B prep) | 2-3 days | ~4 days |
| PR3 (Phase 2B main) | 3-4 days | ~7 days |
| PR4 (Phase 2C) | 1-2 days | ~9 days |
| PR5A | 1-2 days | ~10 days |
| PR5B | 1-2 days | ~12 days |
| PR5C | 1-2 days | ~14 days |
| PR6 (Phase 3 part 2) | 3-4 days | ~18 days |
| PR7 (Phase 4) | 2-3 days | ~21 days |

**Total: ~3-4 weeks of focused engineering, spread across 4 releases (v1.11.0 → v1.13.0+).**

## Conventions used in this plan

- **PR IDs** are stable; phase numbers (2A, 2B, 2C, 3, 4) reflect upstream's historical numbering and are kept for traceability.
- **ToolAdapter field proposals** carry code-shape sketches; PR-time implementation may refine the names (e.g. `legacy_skills_dirs` vs `LegacySkillsDir` sub-dataclass) but the **shape and consumer contracts are locked**.
- **Effort estimates** assume a single reviewer and PR-by-PR merges; bulk tiers (PR5*) are most efficient when split as shown.
- **Files outside `docs/plans/upstream-parity/`** are never modified by this plan — execution lands in `orchestrator/source/tools.py`, `orchestrator/source/cli.py`, `orchestrator/source/lib/osx.py`, and the relevant test files.

## Update protocol

When a PR lands:

1. Update the **Status** table above: PR row → ✅ done, mark "Coverage shipped" increment.
2. Update the **Cumulative count** in the wall-clock table.
3. Note any deviation from the plan in `pr/<id>-deviations.md` (same folder as the PR spec).

When a phase finishes (all PRs in a phase land):

1. Add a one-paragraph retrospective at the bottom of `00-decisions.md`.
2. If scope changed, update `02-coverage-matrix.md` accordingly.
