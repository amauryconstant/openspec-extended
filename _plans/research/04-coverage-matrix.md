# Research 04 — Coverage Matrix and Sequenced Rollout Plan

**Purpose:** Final coverage matrix mapping the current openspec-extended adapter registry against upstream OpenSpec Core's full tool list, plus a 7-PR sequenced rollout plan.

**Source:** exploration agent (coverage + sequencing task).

**Date:** 2026-09-14.

---

## Coverage Matrix (39 upstream tools)

**Source of truth (us):** `orchestrator/source/tools.py` (2 entries — `opencode`, `claude`).
**Source of truth (upstream):** `orchestrator/core/source/src/core/config.ts` (`AI_TOOLS`, 39 entries).

### Legend

| Effort | Definition |
|--------|------------|
| **Low** | One `REGISTRY[<tool_id>] = ToolAdapter(...)` entry + `generic_print` + zero new ToolAdapter fields |
| **Medium** | Needs ≤ 3 new ToolAdapter fields (or a new `CommandsStyle` literal that reuses existing per-tool branches) |
| **High** | Needs a new `RunnerKind` literal + a bespoke runner class, OR a new `CommandsStyle` literal that doesn't reuse existing branches, OR multi-stage migration support (`legacy_skills_dirs`) |

| # | Tool id | Adapter-backed? | Skills-invocable? | REGISTRY today | Effort | First phase | Tool-specific quirks |
|---|---------|-----------------|------------------|----------------|--------|--------------|---------------------|
| 1 | `opencode` | yes | yes (`/osx-…`) | ✅ shipped | — | shipped | Canonical adapter |
| 2 | `claude` | yes | yes (`/osx:…`) | ✅ shipped | — | shipped | Dual-emit; `docs_file="CLAUDE.md"`, `ask_tool="Ask"` |
| 3 | `cursor` | yes (synthetic tests pass) | yes | ❌ → ✅ | **Low** | PR3 (v1.11.0) | Flat; `requiresIdeRestart` |
| 4 | `codex` | yes (synthetic tests pass) | yes (`$openspec-…`) | ❌ → ✅ | **Medium** | PR3 (v1.11.0) | `commands_style="skills-only"`; `cross_ref_prefix="$"`; shared `.agents` |
| 5 | `kimi` | yes (synthetic tests pass) | yes (`/skill:openspec-…`) | ❌ → ✅ | **Low** | PR3 (v1.11.0) | `.kimi-code`; `commands_style="skills-only"`; `cross_ref_prefix="/skill:"` |
| 6 | `zed` | no | yes (skills-only) | ❌ → ✅ | **Low** | PR5C | `skills_dir=".agents"` collides with codex/antigravity/agents |
| 7 | `antigravity` | no | yes (skills-only) | ❌ → ✅ | **Medium** | PR6 | Shared `.agents` + legacy `.agent` directory |
| 8 | `gemini` | no | yes | ❌ → ✅ | **Medium** | PR5B | Uses `.toml` extension; namespaced layout |
| 9 | `qwen` | no | yes | ❌ → ✅ | **Medium** | PR4 | `.toml` extension; `runner_args=("--yolo",)` |
| 10 | `kiro` | no | yes | ❌ → ✅ | **Medium** | PR4 | `commands_dir="prompts"`; `commands_ext="prompt.md"` |
| 11 | `github-copilot` | no | partial (skills-only) | ❌ → ✅ | **Medium** | PR6 | 7-path detection (3 file-typed) |
| 12 | `amazon-q` | no | yes | ❌ → ✅ | **Low** | PR5A | `requiresIdeRestart` |
| 13 | `cline` | no | yes | ❌ → ✅ | **Low** | PR5A | `requiresIdeRestart` |
| 14 | `command-code` | no | yes | ❌ → ✅ | **Low** | PR5A | `requiresIdeRestart` |
| 15 | `codeartsagent` | no | yes | ❌ → ✅ | **Low** | PR5A | – |
| 16 | `forgecode` | no | yes (skills-only) | ❌ → ✅ | **Low** | PR3 | `.forge` |
| 17 | `codebuddy` | no | yes | ❌ → ✅ | **Low** | PR5A | Namespaced layout |
| 18 | `continue` | no | yes | ❌ → ✅ | **Low** | PR5A | `.prompt` extension; IDE-only |
| 19 | `costrict` | no | yes | ❌ → ✅ | **Low** | PR5A | `.cospec` (not `.costrict`) |
| 20 | `crush` | no | yes | ❌ → ✅ | **Low** | PR5A | Namespaced layout |
| 21 | `factory` | no | yes | ❌ → ✅ | **Low** | PR5B | – |
| 22 | `hermes` | no | yes | ❌ → ✅ | **Medium** | PR6 | First tool that needs `setup_note` |
| 23 | `iflow` | no | yes | ❌ → ✅ | **Low** | PR5B | – |
| 24 | `junie` | no | yes | ❌ → ✅ | **Low** | PR5B | `requiresIdeRestart` |
| 25 | `kilocode` | no | yes | ❌ → ✅ | **Low** | PR5B | `requiresIdeRestart` |
| 26 | `lingma` | no | yes | ❌ → ✅ | **Low** | PR5B | Namespaced layout; `requiresIdeRestart` |
| 27 | `minimax-code` | no | yes (global) | ❌ → ✅ | **High** | PR7 | First tool that needs `global_skills_dir` |
| 28 | `vibe` | no | yes | ❌ → ✅ | **Low** | PR5C | – |
| 29 | `oh-my-pi` | no | yes | ❌ → ✅ | **Low** | PR5B | – |
| 30 | `pi` | no | yes | ❌ → ✅ | **Low** | PR5B | `commands_dir="prompts"` |
| 31 | `codeassistant` | no | yes | ❌ → ✅ | **Low** | PR5B | Natural-language refs |
| 32 | `qoder` | no | yes | ❌ → ✅ | **Low** | PR5C | Namespaced; `requiresIdeRestart` |
| 33 | `rovodev` | no | yes | ❌ → ✅ | **Low** | PR5C | Natural-language refs; `runner_binary="acli"` |
| 34 | `roocode` | no | yes | ❌ → ✅ | **Low** | PR5C | `requiresIdeRestart` |
| 35 | `trae` | no | yes | ❌ → ✅ | **Low** | PR5C | `requiresIdeRestart` |
| 36 | `devin` | no | yes | ❌ → ✅ | **Medium** | PR5B + PR6 | Multi-path detection; legacy `.windsurf` |
| 37 | `zcode` | no | yes | ❌ → ✅ | **Low** | PR5C | Namespaced layout |
| 38 | `agents` | no | yes (skills-only) | ❌ → ✅ | **Medium** | PR5C | Shared with codex/zed/antigravity |
| 39 | `auggie` | no | yes | ❌ → ✅ | **Low** | PR5A | – |
| — | `windsurf` (retired → `devin`) | n/a | n/a | n/a | n/a | PR6 | `TOOL_ID_ALIASES["windsurf"]="devin"` |

### Coverage summary

| Coverage tier | Tool count | Today |
|---|---|---|
| Shipped (REGISTRY entry, real deploy) | **2** | `opencode`, `claude` |
| Synthetic-tested (REGISTRY-ready, not shipped) | **3** | `cursor`, `codex`, `kimi` |
| Field-set ready (one-line REGISTRY entry, no new field) | **26** | All "Low" rows above |
| Field-blocked (need ≤ 3 new ToolAdapter fields) | **7** | `codex`, `antigravity`, `gemini`, `qwen`, `kiro`, `github-copilot`, `hermes`, `agents` |
| Heavy (need new runner / new style / multi-stage migration) | **1** | `minimax-code` |
| Aliases (no new entry; needs `TOOL_ID_ALIASES`) | **1** | `windsurf → devin` |

---

## Sequenced Rollout Plan

### Phase 2A — Adapter abstraction hardens (v1.10.x patch)

**Scope:** No new adapter ships; the goal is to ensure the abstraction is fully exercised by every code path.

**Prerequisite refactor work:** None — purely validation.

**New adapters shipped:** None.

**Test coverage:** Add `TestPurgeSkillsOnly`; parametrize `TestValidateDeploymentSharedSkillsRootNote`.

**Documentation:** No AGENTS.md changes.

**Estimated effort:** **small PR** (~50 lines of test).

### Phase 2B — `generic_print` ships with four first-party adapters (v1.11.0)

**Scope:** Add `cursor`, `codex`, `kimi`, `qwen`, `forgecode`. Then PR4 adds `qwen` and `kiro` finalised at `.toml` / `.prompt.md`.

**Prerequisite refactor work:**

1. Two new ToolAdapter fields (`requires_ide_restart`, `shared_skills_root`).
2. Update `deploy_all_resources` and `validate_deployment`.
3. Add 4 (then 6) REGISTRY entries.
4. `SHIPPED_TOOLS` becomes 8-element; per-tool byte-equality tests expand.

**New adapters shipped:** `cursor`, `codex`, `kimi`, `forgecode`, `qwen`, `kiro`.

**Test coverage:** Promote synthetic fixtures to shipped; add `TestAdapterRequiresIdeRestart`, `TestSharedSkillsRootSuppressesNote`, `TestCodexFrontmatterExtras`.

**Documentation:** `orchestrator/source/AGENTS.md`; `orchestrator/source/lib/AGENTS.md`; `orchestrator/source/orchestrator/AGENTS.md`; `.opencode/rules/per-adapter-rendering.md`.

**Estimated effort:** **medium PR** (~400 lines).

### Phase 2C — Extension media + Kiro-specific dispatch (v1.11.x patch)

**Scope:** Extend the deploy path to non-`.md` command files.

**Prerequisite refactor work:**

1. `_substitute_tokens_in_file` accepts `.toml` and `.prompt.md`.
2. `get_target_path` reads `commands_ext`.
3. `purge_managed_resources` flat branch reads `commands_ext`.

**New adapters shipped:** `qwen`, `kiro`.

**Effort:** **small PR** (~150 lines).

### Phase 3 — Broad coverage + restart-hint tools (v1.12.0)

**Scope:** Add ~27 more adapters in three alphabet-split sub-PRs.

**Prerequisite refactor work:**

1. `legacy_skills_dirs` field on `ToolAdapter`.
2. `setup_note` field.
3. `TOOL_ID_ALIASES` constant.
4. `migrate_legacy_skills_dirs` helper.
5. `agents` (vendor-neutral) adapter.

**New adapters shipped:** ~27 across PR5A/5B/5C.

**Effort:** **large PR** (~1500 lines, split into 3A/3B/3C sub-PRs).

### Phase 4 — Global skills dir + remaining Heavy adapters (v1.13.0+)

**Scope:** Land `minimax-code`.

**Prerequisite refactor work:**

1. `global_skills_dir` field.
2. `_target_root(adapter, project_root)` resolver.

**New adapters shipped:** `minimax-code`.

**Effort:** **medium PR** (~250 lines).

---

## Three-Tier Adapter Model

### Tier 1 — One-liner adapters (no new ToolAdapter fields)

26 tools. Each is a single `REGISTRY` entry. `commands_style="flat"` or `"skills-only"`, `runner_kind="generic_print"`, no new fields.

### Tier 2 — Mid-effort adapters (1-3 new ToolAdapter fields)

7 tools. Each needs ≤ 3 new fields.

| Tool | Fields needed |
|------|---------------|
| `codex` | `cross_ref_prefix`, `frontmatter_extras`, `shared_skills_root` |
| `qwen` | `commands_ext="md"` (no toml in practice) |
| `kiro` | `commands_dir="prompts"`, `commands_ext="prompt.md"` |
| `gemini` | `commands_ext="toml"` |
| `github-copilot` | `shared_skills_root`, `setup_note`, multi-path detection |
| `hermes` | `setup_note`, multi-path detection |
| `antigravity` | `legacy_skills_dirs=(".agent",)`, `shared_skills_root` |
| `agents` | `shared_skills_root` |

### Tier 3 — Heavy adapters (new resolver / new style)

1 tool: `minimax-code` (needs `global_skills_dir` + `_target_root` resolver).

---

## Concrete Sequence of Work (7 PRs)

### PR1 — Phase 2A: validate the abstraction (v1.10.x patch)

Validate `purge_managed_resources`, `validate_deployment`, `_command_resolved_for_phase`, `_install_hint` against synthetic `cursor` / `codex` / `kimi`. Add `TestPurgeSkillsOnly`. **Outcome:** abstraction empirically tested for every `CommandsStyle` value. ~1 day.

### PR2 — Phase 2B prep: two new ToolAdapter fields (v1.11.0 prep)

Add `requires_ide_restart`, `shared_skills_root`. Update `deploy_all_resources` and `validate_deployment`. Lock fields with `TestAdapterFieldDefaults`. **Outcome:** fields live, locked by tests, consumed in `cli.py`. ~2-3 days.

### PR3 — Phase 2B main: ship cursor, codex, kimi, forgecode (v1.11.0)

4 REGISTRY entries. Promote synthetic fixtures to shipped. **Outcome:** four new adapters ship. ~3-4 days.

### PR4 — Phase 2C: ship qwen and kiro (v1.11.x patch)

Extend `_substitute_tokens_in_file`, `get_target_path`, `purge_managed_resources` for `.toml` and `.prompt.md`. Ship `qwen` and `kiro`. **Outcome:** qwen and kiro ship. ~1-2 days.

### PR5A — Phase 3 part 1 first slice: amazon-q through crush (v1.12.0)

10 Low-effort adapters. ~1-2 days.

### PR5B — Phase 3 part 1 second slice: devin through pi (v1.12.0)

9 adapters. Includes `gemini` (TOML). ~1-2 days.

### PR5C — Phase 3 part 1 third slice: qoder through zed + agents (v1.12.0)

7 adapters + `zed` + `agents`. **Critical:** ships shared-root arbitration test. ~1-2 days.

### PR6 — Phase 3 part 2: legacy migration, aliases, hermes, antigravity, github-copilot, agents, devin (v1.12.x patch)

Add `legacy_skills_dirs`, `setup_note`, `TOOL_ID_ALIASES`. Ship `migrate_legacy_skills_dirs`. Ship 4 Medium-tier adapters. ~3-4 days.

### PR7 — Phase 4: ship minimax-code with global skills dir (v1.13.0+)

Add `global_skills_dir`. Add `_target_root` resolver. Ship `minimax-code`. ~2-3 days.

**Total wall-clock for the 7-PR sequence:** ~3-4 weeks of focused work, spread across 4 releases.

---

## Critical Infrastructure Questions

### Q1. Should `runner_kind` grow new literals, or should `plan_args` / `runner_args` absorb everything?

**Recommendation:** Stay with three literals and let `runner_args` absorb flag differences.

The synthetic `claude_style` test in `test_runner_abstraction.py:946-993` proves `slash_prefix` doesn't affect the prompt — the prompt is always `/osx-phase0 <change_id>` regardless of `slash_prefix`.

### Q2. Should we add `legacy_skills_dirs` + migration support now, or defer it to a later phase?

**Recommendation:** Defer to PR6.

antigravity moved from `.agent` to `.agents` in upstream v1.20.5 (a future release); most users will be fresh-installs.

### Q3. How do we handle `commands_ext="toml"` (Qwen) without breaking the current `.md`-only deploy path?

**Recommendation:** Extend `_substitute_tokens_in_file` to accept `.toml`, `.prompt.md`, `.prompt` (PR4).

The token grammar `{{TOKEN}}` is format-agnostic.

### Q4. Should we add a `minimax-code` global_skills_dir case in v1.11.0 or defer?

**Recommendation:** Defer to v1.13.0 (PR7).

### Q5. Should we keep the hardcoded `if adapter.tool_id == "opencode": ...` ladder in `_adapter_ask_tool`?

**Recommendation:** No ladder exists. The `ask_tool` field is already on `ToolAdapter`. `_adapter_tokens` reads it.

### Q6. Should we ship one Tier-3 adapter (`minimax-code`) as the proof-of-concept for global_skills_dir, or two Tier-1 adapters as the bulk increment in v1.11.0?

**Recommendation:** Tier-1-first. v1.11.0 should be the "we ship 4-7 new adapters" release that proves the abstraction scales.

---

## Risks and Tradeoffs

1. **Registration-order coupling when multiple adapters share `skills_dir`** — High likelihood, medium impact. Mitigation: `TestDetectPlatformRegistrationOrderIsCanonical` + registration-order invariant documented in `lib/AGENTS.md`.
2. **`commands_ext="toml"` / `".prompt.md"` substitution may collide with the host format's syntax** — Medium likelihood, medium impact. Mitigation: contract tests against live Qwen/Kiro CLIs.
3. **`legacy_skills_dirs` migration is destructive** — Medium likelihood, high impact. Mitigation: conservative contract (copy not move, refuse to overwrite, idempotent, snapshot, dry-run default).
4. **Bulk-shipping 25 adapters in one PR is a review and CI hazard** — High likelihood, medium impact. Mitigation: split PR5 into 3A/3B/3C sub-PRs.
5. **Upstream renames keep happening** — High likelihood, low-medium impact. Mitigation: `TOOL_ID_ALIASES` + `legacy_skills_dirs` machinery + rebrand audit step in `mise run sync-core`.

---

**End of research output 04.**
