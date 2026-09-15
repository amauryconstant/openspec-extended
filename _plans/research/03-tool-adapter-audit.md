# Research 03 — ToolAdapter Audit vs Upstream `AI_TOOLS`

**Purpose:** Audit of `orchestrator/source/tools.py` (ToolAdapter dataclass + REGISTRY) against the broader upstream OpenSpec Core tool catalogue. Identifies field gaps, generalization needs, and per-tool mapping strategy.

**Source:** exploration agent (audit task).

**Date:** 2026-09-14.

---

## 0. Scope and Source Map

| Layer | Path | What it owns |
|-------|------|--------------|
| **Local (orchestrator)** | `orchestrator/source/tools.py` (lines 88–226) | `ToolAdapter` dataclass, `CommandsStyle`, `RunnerKind`, `REGISTRY`, `PLATFORM_TOKENS`, `TOOL_DIRS`, `strip_agent_line`, `_adapter_tokens` |
| **Local consumers** | `orchestrator/source/cli.py`, `orchestrator/source/lib/osx.py`, `orchestrator/source/orchestrator/{runner.py,engine.py}` | Per-adapter deploy / detect / preflight / run |
| **Upstream (vendored)** | `orchestrator/core/source/src/core/config.ts` | `AI_TOOLS: AIToolOption[]`, `TOOL_ID_ALIASES` |
| **Upstream adapters** | `orchestrator/core/source/src/core/command-generation/adapters/*.ts` | One per tool (31 total) |
| **Upstream detection** | `orchestrator/core/source/src/core/shared/tool-detection.ts`, `shared-skill-target.ts`, `ide-restart.ts`, `skill-paths.ts` | Where skills live, who owns them, how to surface them |
| **Upstream migration** | `orchestrator/core/source/src/core/migration.ts`, `legacy-cleanup.ts` | `.codex` → `.agents`, `.windsurf` → `.devin`, `.kimi` → `.kimi-code`, `.agent` → `.agents` |
| **Upstream invocation** | `orchestrator/core/source/src/core/command-generation/invocation.ts` | How `getFilePath` → invocation form |
| **Upstream capabilities** | `orchestrator/core/source/src/core/command-surface.ts` | `adapter-backed` / `skills-invocable` / `none` |

---

## 1. Current `ToolAdapter` Field Inventory (lines 88–226 of `source/tools.py`)

21 fields. Listed in source-order with consumers (anchored to file:line where possible).

| # | Field | Type | Consumers |
|---|-------|------|-----------|
| 1 | `tool_id` | `str` | `tools.py:300`; `lib/osx.py:1401,1480,1503`; `cli.py:1429,1435`; `runner.py:104,140,295,309` |
| 2 | `skills_dir` | `str` | `tools.py:371` (TOOL_DIRS); `cli.py:206,1412,1430,1441`; `lib/osx.py:232,245,1354,1469,1483,1536` |
| 3 | `commands_dir` | `str` | `cli.py:594`; `lib/osx.py:245` |
| 4 | `commands_style` | `CommandsStyle` | `cli.py:423,574,607,925,941,978,999,1006`; `lib/osx.py:1454,1468,1483,1504` |
| 5 | `commands_ext` | `str` | `cli.py:603` (deployed filename) |
| 6 | `slash_prefix` | `str` | `tools.py:274` (CMD_PREFIX token); `cli.py:93,134,135` |
| 7 | `skill_prefix` | `str` | `tools.py:277,278`; `runner.py:245,305`; `cli.py:93,96` |
| 8 | `runner_binary` | `str` | `engine.py:1259,1262,1265`; `runner.py:159,238,298,309` |
| 9 | `runner_kind` | `RunnerKind` | `runner.py:132,134,136,140,141` |
| 10 | `has_agents_dir` | `bool` | `cli.py:1415`; `lib/osx.py:1516,1533,1536` |
| 11 | `agent_field_transform` | `Callable[[str], str] \| None` | `cli.py:422,423,446` |
| 12 | `inject_name_in_skill_mirror` | `bool` | `cli.py:421,437,454` |
| 13 | `cmd_filename_strip_prefix` | `str \| None` | `cli.py:599,600,602`; `lib/osx.py:1448,1457,1458,1460,1497,1498,1500` |
| 14 | `docs_file` | `str` | `tools.py:273` |
| 15 | `tool_name` | `str` | `tools.py:275` |
| 16 | `detect_paths` | `tuple[str, ...]` | `runner.py:105`; `lib/osx.py:219` |
| 17 | `ask_tool` | `str` | `tools.py:272` |
| 18 | `install_hint` | `str` | `engine.py:215,230`; `lib/osx.py:1406,1423,1555` |
| 19 | `cross_ref_prefix` | `str` | `tools.py:278`; `cli.py:93,94,96` |
| 20 | `runner_args` | `tuple[str, ...]` | `runner.py:310` |
| 21 | `frontmatter_extras` | `dict[str, str]` | `cli.py:419,420,439,456` |

**Literal types:**

```python
CommandsStyle = Literal["flat", "namespaced", "namespaced-with-skill-mirror", "skills-only"]
RunnerKind = Literal["opencode_run", "claude_print", "generic_print"]
```

There is **no** field for `successLabel`, `legacySkillsDirs`, `globalSkillsDir`, `setupNote`, `requiresIdeRestart`, `available`, `plan_args`, etc. — these exist only upstream.

---

## 2. Upstream `AIToolOption` Field Inventory vs `ToolAdapter`

| Upstream field | Maps to which `ToolAdapter` field? | Status |
|----------------|------------------------------------|--------|
| `name` | `tool_name` | **Equivalent** |
| `value` | `tool_id` | **Equivalent** |
| `available` | (none) | **Need new field** (`available: bool`) |
| `successLabel` | (close to `tool_name` but distinct) | **Could express via `tool_name`**, but pre-shipped divergence calls for a separate `success_label: str \| None`. **Need new field** in practice. |
| `skillsDir` | `skills_dir` | **Equivalent**, but currently mandatory. **Relax to `str \| None`** for global-only tools. |
| `legacySkillsDirs` | (none) | **Need new field** |
| `globalSkillsDir` | (none) | **Need new field** |
| `detectionPaths` | `detect_paths` | **Could express via existing** but **need to switch `is_dir()` to `exists()`** for file-typed paths. |
| `setupNote` | (none) | **Need new field** |
| `requiresIdeRestart` | (none) | **Need new field** |

### 2.1 Net new fields needed

Across the rollout:

1. `requires_ide_restart: bool = False` (PR2)
2. `shared_skills_root: bool = False` (PR2)
3. `setup_note: str = ""` (PR2)
4. `legacy_skills_dirs: tuple[str, ...] = ()` (PR6)
5. `TOOL_ID_ALIASES: dict[str, str]` constant (PR6)
6. `global_skills_dir: str \| None = None` (PR7)

---

## 3. Upstream Adapter Pattern Taxonomy

### 3.1 Per-adapter layout summary

| Adapter | File format | Layout | Slash prefix | Body rewrite | Frontmatter |
|---------|-------------|--------|--------------|--------------|-------------|
| `opencode` | Markdown + YAML frontmatter | flat | `/` | `$ARGUMENTS` injection | `description:` |
| `claude` | Markdown + YAML frontmatter | namespaced | `/` | none | `name:`, `description:`, `allowed-tools:`, `category:`, `tags:` |
| `cursor` | Markdown + YAML | flat | `/` | none | `name: /opsx-<id>`, `id:`, `category:`, `description:` |
| `amazon-q` | Markdown + YAML | flat | `@` | none | `description:` |
| `antigravity` | Markdown + YAML | flat | `/` | none | `description:` |
| `auggie` | Markdown + YAML | flat | `/` | none | `description:`, `argument-hint:` |
| `bob` | Markdown + YAML | flat | `/` | none | `description:`, `argument-hint:` |
| `cline` | Markdown (no frontmatter) | flat | `/` | none | `# <name>` header |
| `codebuddy` | Markdown + YAML | namespaced | `/` | none | `name:`, `description:`, `argument-hint:` |
| `codeassistant` | Markdown + YAML | flat | natural-lang | none | `description:` |
| `command-code` | Plain Markdown | flat | `/` | `$ARGUMENTS` injection | none |
| `continue` | `.prompt` | flat | `/` | none | `name:`, `description:`, `invokable: true` |
| `costrict` | Markdown + YAML | flat | `/` | none | `description:`, `argument-hint:` |
| `crush` | Markdown + YAML | namespaced | `/` | none | `name:`, `description:`, `category:`, `tags:` |
| `devin` | Markdown + YAML | flat | `/` | none | `name:`, `description:`, `category:`, `tags:` |
| `factory` | Markdown + YAML | flat | `/` | none | `description:`, `argument-hint:` |
| `gemini` | TOML | namespaced | `/` | none | `description =`, `prompt =` |
| `github-copilot` | Markdown + YAML | flat | `/` | none | `description:` (`.prompt.md`) |
| `iflow` | Markdown + YAML | flat | `/` | none | `name: /opsx-<id>`, `id:`, `category:`, `description:` |
| `junie` | Markdown + YAML | flat | `/` | none | `description:` |
| `kilocode` | Plain Markdown | flat | `/` | none | none |
| `kiro` | Markdown + YAML | flat | `/` | none | `description:` (`.prompt.md`) |
| `lingma` | Markdown + YAML | namespaced | `/` | none | `name:`, `description:`, `category:`, `tags:` |
| `oh-my-pi` | Markdown + YAML | flat | `/` | `$@` injection | `description:` |
| `pi` | Markdown + YAML | flat | `/` | `$@` injection | `description:` |
| `qoder` | Markdown + YAML | namespaced | `/` | none | `name:`, `description:`, `category:`, `tags:` |
| `qwen` | Markdown + YAML | flat | `/` | none | `description:` |
| `roocode` | Markdown (no frontmatter) | flat | `/` | none | `# <name>` header |
| `trae` | Markdown + YAML | flat | `/` | none | `name:`, `description:` |
| `zcode` | Markdown + YAML | namespaced | `/` | none | `name:`, `description:`, `category:`, `tags:` |

### 3.2 Mapping summary

The current `ToolAdapter`'s vocabulary encodes **4 `commands_style` values, 4 `commands_ext` values, 4 `slash_prefix` shapes**, plus per-tool frontmatter customisation via `frontmatter_extras`.

Every upstream adapter can be expressed using these. The only open frontmatter kind (`markdown-header-no-frontmatter` for cline/kilocode/roocode) is a code-body rewrite concern; the deploy path would strip the leading `---` block if needed (current code already does this via `agent_field_transform` when set).

---

## 4. Capabilities Taxonomy

The 3-state model maps cleanly:

| Upstream capability | Today's `commands_style` |
|---------------------|--------------------------|
| `adapter-backed` | `flat`, `namespaced`, `namespaced-with-skill-mirror` |
| `skills-invocable` | `skills-only` (codex is the only one) |
| `none` | `skills-only` |

**Both non-`adapter-backed` tools can share `commands_only="skills-only"`**. No new literal needed.

### 4.1 Per-tool classification

| Tool | Capability | `commands_style` | Special fields |
|------|-----------|------------------|----------------|
| `cursor` | adapter-backed | `flat` | `requires_ide_restart=True` |
| `codex` | skills-invocable | `skills-only` | `cross_ref_prefix="$"`, `frontmatter_extras={"source": "openspec-extended"}`, `shared_skills_root=True` |
| `kimi` | none | `skills-only` | `skill_prefix="/skill:"`, `cross_ref_prefix="/skill:"` |
| `qwen` | adapter-backed | `flat` | `commands_ext="md"` |
| `kiro` | adapter-backed | `flat` | `commands_ext="prompt.md"`, `commands_dir="prompts"` |
| `gemini` | adapter-backed | `namespaced` | `commands_ext="toml"` |
| `github-copilot` | adapter-backed | `flat` | `commands_ext="prompt.md"`, `commands_dir="prompts"`, `setup_note`, `requires_ide_restart=True` |
| `antigravity` | skills-only | `skills-only` | `legacy_skills_dirs=(".agent",)`, `shared_skills_root=True` |
| `hermes` | skills-only | `skills-only` | `setup_note`, multi-path detection |
| `minimax-code` | skills-only | `skills-only` | `global_skills_dir=".minimax"` |
| `rovodev` | none | `skills-only` | `slash_prefix=""` (natural-language), `runner_binary="acli"` |
| `codeassistant` | none | `skills-only` | `slash_prefix=""` (natural-language) |

---

## 5. Detection Paths

Upstream `detectionPaths` is `string[]` with **6 tools declaring multi-path detection**:

| Tool (id) | detectionPaths (upstream) | Each path is … |
|-----------|---------------------------|----------------|
| antigravity | `['.agent', '.agents/workflows']` | directory, directory |
| codex | `['.agents/skills', '.codex/skills']` | directory, directory |
| devin | `['.devin', '.windsurf']` | directory, directory |
| github-copilot | 7 paths | mix of files and directories |
| hermes | `['.hermes', 'HERMES.md', '.hermes.md']` | dir, file, file |
| kimi | `['.kimi-code', '.kimi']` | directory, directory |

**Schema change needed**: switch `(root / p).is_dir()` → `(root / p).exists()` in `lib/osx.py:219` and `runner.py:105` to support file-typed paths.

**Arbitration needed**: when `.agents/` is shared, the more-specific path wins. `detect_platform` needs a 2-pass walk (registration order, then specificity) — implemented in PR5C.

---

## 6. Global vs Repo-Local Skills

Upstream `globalSkillsDir: '.minimax'` is declared by exactly one tool (`minimax-code`). Resolved from `process.env.HOME` per `shared/skill-paths.ts:23-38`.

### 6.1 The gap

- Current `ToolAdapter.skills_dir: str` is **mandatory** and unconditionally resolved as `Path.cwd() / skills_dir / "skills"`.
- No concept of a global skills target.
- CLI cannot configure `~/.minimax/skills/openspec-*/SKILL.md`.

### 6.2 Proposed fix

```python
skills_dir: str | None  # RELAX to optional; None ⇒ global-only tool
global_skills_dir: str | None = None
"""Global-only skills root (e.g. ``.minimax``); resolved from the user's
home directory (``$HOME`` / ``%USERPROFILE%``)."""
```

Consumer updates:

- `lib/osx.py:skills_dir()` branches on `global_skills_dir` first.
- `lib/osx.py:detect_platform()` includes a global-root check.
- `lib/osx.py:validate_skills()` projects under global root for global-only tools.

Helper mirrors upstream `resolveToolSkillsDir` (precedence: explicit kwarg → `USERPROFILE` → `HOME` → `Path.home()`).

---

## 7. Legacy Reconciliation

`orchestrator/core/source/src/core/migration.ts:LEGACY_TOOL_ROOTS` enumerates 4 rebrand/move events:

| Tool id | Legacy root(s) | needsConsent | timing |
|---------|---------------|--------------|--------|
| kimi | `.kimi` | false | before-generation |
| devin | `.windsurf` | true | before-generation |
| codex | `.codex` | false | after-generation |
| antigravity | `.agent` | false | after-generation |

### 7.1 Proposed new field

```python
legacy_skills_dirs: tuple[str, ...] = ()
"""Former project-local roots that map to the tool's current skills_dir
and should be reconciled on install/update."""
```

Or a richer sub-dataclass for consent + timing:

```python
@dataclass(frozen=True)
class LegacySkillsDir:
    root: str
    needs_consent: bool = False
    timing: Literal["before-generation", "after-generation"] = "before-generation"
```

---

## 8. Plan Mode

Upstream OpenSpec Core does **not** implement plan-mode flag injection. Each tool's plan flag varies:

| Tool | Plan-mode flag | Position |
|------|---------------|----------|
| Codex | `--plan` | between binary and prompt |
| Cursor | `--mode plan` | between binary and `--print` |
| Kimi | `--plan` | before prompt |
| Qwen Code | `--approval-mode plan` | between binary and prompt |
| Cline | `-p` / `--plan` | between binary and prompt |
| Devin | `--permission-mode plan` | between binary and `--print` |
| Claude Code | `--permission-mode plan` | between binary and `--print` |
| Auggie | `--plan` | between binary and prompt |

### 8.1 Proposed fields

```python
plan_args: tuple[str, ...] = ()
"""Args injected when plan mode is requested for the phase."""

plan_args_position: Literal["flag", "before_prompt", "after_prompt"] = "flag"
"""Where in the command line ``plan_args`` go."""
```

The runner would resolve these per-request:

```python
if request.plan_mode:
    if adapter.plan_args_position == "flag":
        cmd = [binary, *adapter.plan_args, *adapter.runner_args, "--print", "--dangerously-skip-permissions", prompt]
    elif adapter.plan_args_position == "before_prompt":
        cmd = [binary, *adapter.runner_args, "--print", "--dangerously-skip-permissions", *adapter.plan_args, prompt]
    else:
        cmd = [binary, *adapter.runner_args, "--print", "--dangerously-skip-permissions", prompt, *adapter.plan_args]
```

---

## 9. Process Model and Detection — Per-tool Classification

| Tool | Binary? | `--print` / `-p`? | Unique subcommand? | Plan flag? | CWD flag? |
|------|---------|-------------------|--------------------|-----------|-----------|
| opencode | yes (`opencode`) | n/a (custom `run`) | yes (`run`) | n/a | `--file` (for guidance) |
| claude | yes (`claude`) | yes | n/a | `--permission-mode plan` | no |
| cursor | yes (`agent`) | yes (`agent --print`) | `agent` | `--mode plan` | `--workspace` |
| codex | yes (`codex`) | yes (`codex exec`) | `exec` | `--plan` | `--cd` |
| kimi | yes (`kimi`) | yes (`--prompt`) | n/a | `--plan` | `--cd` |
| qwen | yes (`qwen`) | yes (`--prompt`) | n/a | `--approval-mode plan` | no (uses CWD) |
| cline | yes (`cline`) | yes (`--json`) | n/a | `-p` / `--plan` | `--cwd` |
| kiro | yes (`kiro-cli`) | yes (`--print`) | `chat` | n/a | no |
| auggie | yes | yes | n/a | `--plan` | `--workspace` |
| devin | yes | yes (`--print`) | n/a | `--permission-mode plan` | `--workspace` |
| gemini | yes | yes (`--prompt`) | n/a | n/a | `--sandbox` |
| continue | no | n/a | n/a | n/a | n/a |
| github-copilot | yes (`copilot` CLI) | unstable | n/a | n/a | `--workspace` |
| antigravity | yes | yes | n/a | n/a | n/a |
| factory | yes (`droid`) | yes | n/a | n/a | `--workspace` |
| hermes | yes | yes | n/a | n/a | `--workspace` |
| minimax-code | yes (`minimax`) | yes | n/a | n/a | n/a |
| roocode | IDE-only | n/a | n/a | n/a | n/a |
| rovodev | yes (`acli`) | yes | `rovodev run` | n/a | n/a |
| codeassistant | IDE-only | n/a | n/a | n/a | n/a |

---

## 10. Specific Gap Recommendations

Concrete recommendations (with code-shape sketches):

1. **`ask_tool` per adapter** — already exists on `ToolAdapter`; remove any future per-tool hardcoded ladder.
2. **`runner_args` flag injection** — already exists; used by `GenericPrintRunner`.
3. **`commands_ext` honoured in deploy/purge/substitute** — currently `.md`-only; extend in PR4.
4. **`commands_style="skills-only"`** — already exists; used by kimi, codex, forgecode, minimax-code.
5. **`requires_ide_restart`** — needed for PR2.
6. **`shared_skills_root`** — needed for PR2 (suppress "no other adapter uses this dir" warning).
7. **`legacy_skills_dirs` + migration helper** — needed for PR6.
8. **`setup_note`** — needed for PR2.
9. **`TOOL_ID_ALIASES`** — needed for PR6.
10. **`detection_paths_extra` or multi-kind `DetectionPath`** — current `tuple[str, ...]` works with the `exists()` switch; sub-dataclass not needed.
11. **`global_skills_dir`** — needed for PR7.
12. **`plan_args` + `plan_args_position`** — needed if plan-mode support is in scope (deferred per Decision 1).

### 10.1 Net change footprint

| File | Lines added |
|------|-------------|
| `orchestrator/source/tools.py` | ~250 (6 fields + ~30 REGISTRY entries across the rollout) |
| `orchestrator/source/cli.py` | ~150 |
| `orchestrator/source/lib/osx.py` | ~150 |
| `orchestrator/source/orchestrator/runner.py` | ~30 |
| Tests | ~1030 |
| Docs | ~250 |
| **Total** | **~1860 lines** |

---

**End of research output 03.**
