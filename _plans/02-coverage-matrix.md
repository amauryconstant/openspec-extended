# 02 — Coverage Matrix

Full per-tool mapping of upstream OpenSpec's 39 `AI_TOOLS` entries against the field set available in `openspec-extended` after each phase. Effort rating:

- **Low** = one `REGISTRY[<tool_id>] = ToolAdapter(...)` entry, uses `generic_print`, needs no new `ToolAdapter` fields beyond what already exists in `source/tools.py`
- **Medium** = needs ≤ 3 new `ToolAdapter` fields (or a small plumbing change like `_substitute_tokens_in_file` accepting new extensions)
- **High** = needs substantial new infrastructure (new resolver, home-relative deploy target, multi-stage migration)

## Today (v1.10.4)

| # | Tool id | Adapter-backed? | Skills-invocable? | REGISTRY today | Effort | First phase |
|---|---------|-----------------|------------------|----------------|--------|--------------|
| 1 | `opencode` | yes | yes (`/osx-…`) | ✅ shipped | — | shipped |
| 2 | `claude` | yes | yes (`/osx:…`) | ✅ shipped | — | shipped |

After PR1 (Phase 2A) — no adapter change; only test coverage expansion.

After PR3 (Phase 2B main, v1.11.0):

| # | Tool id | Adapter-backed? | Skills-invocable? | REGISTRY today | Effort | First phase |
|---|---------|-----------------|------------------|----------------|--------|--------------|
| 3 | `cursor` | yes | yes | ❌ → ✅ | Low | PR3 (v1.11.0) |
| 4 | `codex` | yes (synth-tested) | yes (`$openspec-…`) | ❌ → ✅ | Medium | PR3 (v1.11.0) |
| 5 | `kimi` | yes (synth-tested) | yes (`/skill:openspec-…`) | ❌ → ✅ | Low | PR3 (v1.11.0) |
| 6 | `forgecode` | n/a | yes (skills-only) | ❌ → ✅ | Low | PR3 (v1.11.0) |

After PR4 (Phase 2C, v1.11.x):

| # | Tool id | REGISTRY today | Effort | First phase |
|---|---------|----------------|--------|--------------|
| 7 | `qwen` | ❌ → ✅ | Medium | PR4 (v1.11.x) |
| 8 | `kiro` | ❌ → ✅ | Medium | PR4 (v1.11.x) |

After PR5A (Phase 3 part 1 first slice, v1.12.0):

| # | Tool id | REGISTRY today | Effort | First phase |
|---|---------|----------------|--------|--------------|
| 9 | `amazon-q` | ❌ → ✅ | Low | PR5A |
| 10 | `auggie` | ❌ → ✅ | Low | PR5A |
| 11 | `bob` | ❌ → ✅ | Low | PR5A |
| 12 | `cline` | ❌ → ✅ | Low | PR5A |
| 13 | `codeartsagent` | ❌ → ✅ | Low | PR5A |
| 14 | `codebuddy` | ❌ → ✅ | Low | PR5A |
| 15 | `command-code` | ❌ → ✅ | Low | PR5A |
| 16 | `continue` | ❌ → ✅ | Low | PR5A |
| 17 | `costrict` | ❌ → ✅ | Low | PR5A |
| 18 | `crush` | ❌ → ✅ | Low | PR5A |

After PR5B (Phase 3 part 1 second slice, v1.12.0):

| # | Tool id | REGISTRY today | Effort | First phase |
|---|---------|----------------|--------|--------------|
| 19 | `devin` | ❌ → ✅ | Low | PR5B |
| 20 | `factory` | ❌ → ✅ | Low | PR5B |
| 21 | `gemini` | ❌ → ✅ | Medium (PR4's `.toml` plumbing required) | PR5B |
| 22 | `iflow` | ❌ → ✅ | Low | PR5B |
| 23 | `junie` | ❌ → ✅ | Low | PR5B |
| 24 | `kilocode` | ❌ → ✅ | Low | PR5B |
| 25 | `lingma` | ❌ → ✅ | Low | PR5B |
| 26 | `oh-my-pi` | ❌ → ✅ | Low | PR5B |
| 27 | `pi` | ❌ → ✅ | Low | PR5B |
| 28 | `codeassistant` | ❌ → ✅ | Low | PR5B |

After PR5C (Phase 3 part 1 third slice, v1.12.0):

| # | Tool id | REGISTRY today | Effort | First phase |
|---|---------|----------------|--------|--------------|
| 29 | `qoder` | ❌ → ✅ | Low | PR5C |
| 30 | `rovodev` | ❌ → ✅ | Low | PR5C |
| 31 | `roocode` | ❌ → ✅ | Low | PR5C |
| 32 | `trae` | ❌ → ✅ | Low | PR5C |
| 33 | `vibe` (Mistral Vibe) | ❌ → ✅ | Low | PR5C |
| 34 | `zcode` | ❌ → ✅ | Low | PR5C |
| 35 | `zed` | ❌ → ✅ | Low | PR5C |

After PR6 (Phase 3 part 2, v1.12.x):

| # | Tool id | REGISTRY today | Effort | First phase |
|---|---------|----------------|--------|--------------|
| 36 | `antigravity` | ❌ → ✅ | Medium (needs `legacy_skills_dirs`) | PR6 |
| 37 | `github-copilot` | ❌ → ✅ | Medium (file-typed detection paths, `.prompt.md` extension) | PR6 |
| 38 | `hermes` | ❌ → ✅ | Medium (needs `setup_note`, file-typed detection) | PR6 |
| 39 | `agents` (vendor-neutral `.agents`) | ❌ → ✅ | Medium (shared-root arbitration) | PR6 |

Plus: `TOOL_ID_ALIASES["windsurf"] = "devin"` added in PR6. `devin` entry's `legacy_skills_dirs=(".windsurf",)` enables auto-migration.

After PR7 (Phase 4, v1.13.0+):

| # | Tool id | REGISTRY today | Effort | First phase |
|---|---------|----------------|--------|--------------|
| 40 | `minimax-code` | ❌ → ✅ | High (needs `global_skills_dir`, `_target_root` resolver) | PR7 |

## Tier summary

| Tier | Tool count | Examples |
|------|-----------|----------|
| Shipped today | 2 | `opencode`, `claude` |
| Low effort (one-line REGISTRY entry) | 26 | `cursor`, `kimi`, `forgecode`, `amazon-q`, `auggie`, `bob`, `cline`, `codeartsagent`, `codebuddy`, `command-code`, `continue`, `costrict`, `crush`, `devin`, `factory`, `iflow`, `junie`, `kilocode`, `lingma`, `oh-my-pi`, `pi`, `codeassistant`, `qoder`, `rovodev`, `roocode`, `trae`, `vibe`, `zcode`, `zed` |
| Medium effort (≤ 3 new fields or small plumbing) | 8 | `codex`, `qwen`, `kiro`, `gemini`, `antigravity`, `github-copilot`, `hermes`, `agents` |
| High effort (new resolver / multi-stage migration) | 1 | `minimax-code` |
| Aliases (no new entry) | 1 | `windsurf → devin` |
| Skipped (not in upstream) | 1 | `aider` |

## Tool-specific quirks that will trip up an unsuspecting integrator

These are the tools that need a moment of care when registering them. Each is captured in detail in [research/02-tool-invocation-shapes.md](research/02-tool-invocation-shapes.md) and the relevant PR file.

### `.agents` shared root (codex, zed, antigravity, agents)

Four tools share `.agents`. `detect_platform` walks `REGISTRY` in registration order; tools with **more specific** paths must register **before** tools with broad `.agents` matches. Specifically:

1. `opencode` (always first; no overlap)
2. `cursor` (`.cursor`)
3. `zed` (`.zed`, `.agents/skills` — must register before codex and antigravity)
4. `codex` (`.agents`)
5. `antigravity` (`.agent`, `.agents/workflows` — must register before `agents`)
6. `agents` (`.agents/skills` — vendor-neutral, registers last)

`TestDetectPlatformRegistrationOrderIsCanonical` (PR5C) walks every pair of shared-root adapters and asserts the more-specific one wins.

### Codex dual-syntax skill references

For `.agents/skills/`, both `$openspec-propose (Codex)` and `/openspec-propose (other agents)` must be emitted in SKILL.md bodies (per upstream `transformToCodexCompatibleSkillReferences` at `orchestrator/core/source/src/utils/command-references.ts:116-123`). The `cross_ref_prefix="$"` field handles this.

### Windsurf rebrand

`.windsurf/` is legacy; `.devin/` is current. Requires `legacy_skills_dirs=(".windsurf",)` + `TOOL_ID_ALIASES["windsurf"]="devin"` (both PR6).

### Antigravity rebrand

`.agent/` → `.agents/` (upstream v1.20.5). Same machinery: `legacy_skills_dirs=(".agent",)` + `detection_paths=(".agent", ".agents/workflows")`.

### Codex legacy

`.codex/skills/` → `.agents/skills/`. Same machinery.

### Kimi legacy

`.kimi/` → `.kimi-code/`. Same machinery.

### GitHub Copilot's 7-path detection

Upstream declares `[".github/copilot-instructions.md", ".github/instructions", ".github/workflows/copilot-setup-steps.yml", ".github/prompts", ".github/agents", ".github/skills", ".github/.mcp.json"]`. Three of these are **files**, not directories. Current local `detect_platform:lib/osx.py:219` uses `is_dir()` only; PR6 must change it to `exists()` (also `runner.py:105`). Backwards-compatible (every existing entry is a directory).

### Minimax Code global skills

Skills install at `~/.minimax/skills/`, not in the project root. Requires the binary to write outside `cwd` — needs explicit user consent in install hints + an `OPENSPEC_GLOBAL_SKILLS_HOME` env var for testability. PR7 only.

### Continue / Zed / rovodev / codeassistant have no headless CLI

These are IDE extensions only. They get `commands_style="skills-only"` for file-generation parity, but their `runner_binary` should be left empty (or set to the IDE binary for IDE-resident hinting) — never spawned as a subprocess by the orchestrator.

### Aider is not in upstream

Aider is its own product with no first-class OpenSpec support. **Skip.** Documented in [research/02-tool-invocation-shapes.md](research/02-tool-invocation-shapes.md) §10 with the rationale.

### Continue's CLI is not stable

Continue is primarily a VS Code / JetBrains extension. No widely-shipped Continue CLI as of OpenSpec v1.13.0. Until Continue ships a stable headless CLI, do **not** add a `continue` adapter to `REGISTRY` with a `runner_binary`. Ship the prompt files only.

### GitHub Copilot's CLI does not read prompt files

The new agentic Copilot CLI does **not** read `.github/prompts/*.prompt.md` directly (only the IDE extension does). The OpenSpec adapter writes those files for the IDE; the local CLI is invoked through a different mechanism (slash commands inside the TUI, or the cloud agent via GitHub Actions). For openspec-extended, register github-copilot as `commands_style="flat"` with `runner_binary="copilot"` but treat the runner as optional — many users will have the IDE only.

## Skipped tools

| Tool id | Why skipped |
|---------|-------------|
| `aider` | Not in upstream `AI_TOOLS`; Aider's filesystem layout and edit model don't fit OpenSpec's skill/command abstraction. |

## Cumulative coverage after each phase

| Phase | PRs | Shipped adapters (cumulative) | REGISTRY entries |
|-------|-----|-------------------------------|------------------|
| v1.10.4 (today) | — | 2 | 2 |
| v1.10.x | PR1 | 2 | 2 |
| v1.11.0 | PR2, PR3 | 6 | 6 |
| v1.11.x | PR4 | 8 | 8 |
| v1.12.0 | PR5A, PR5B, PR5C | 35 | 35 |
| v1.12.x | PR6 | 38 (+ 1 alias) | 38 (+ 1 alias) |
| v1.13.0+ | PR7 | 39 | 39 |
