# Adapter Field Reference

Single source of truth for every `ToolAdapter` field. The complete list after the v1.13.0+ rollout, with default values, consumers, and per-tool values for the 39 upstream tools.

## Identity

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `tool_id` | `str` | required | Stable identifier (`opencode`, `claude`, `cursor`, ...) |
| `tool_name` | `str` | required | Human-readable name (`OpenCode`, `Claude Code`, ...) |

## Filesystem

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `skills_dir` | `str` | required | Project-local root (`.opencode`, `.claude`, ...) — empty when `global_skills_dir` is set |
| `commands_dir` | `str` | required | Subdir under `skills_dir` (`commands`, `commands/osx`, `prompts`, `workflows`, ...) |
| `commands_style` | `CommandsStyle` | required | `flat`, `namespaced`, `namespaced-with-skill-mirror`, `skills-only` |
| `commands_ext` | `str` | required | File extension (`md`, `toml`, `prompt`, `prompt.md`) |
| `cmd_filename_strip_prefix` | `str \| None` | required | Prefix stripped from on-disk filename (`osx-` or `None`) |
| `global_skills_dir` | `str \| None` | `None` | Home-relative root (only `minimax-code` uses it; `.minimax`) |
| `legacy_skills_dirs` | `tuple[str, ...]` | `()` | Former roots to migrate (`.codex`, `.windsurf`, `.kimi`, `.agent`) |

## Slash surface

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `slash_prefix` | `str` | required | Filename prefix for slash commands (`osx-`, `osx:`, ...) |
| `skill_prefix` | `str` | required | User-typed prefix for skills (`/`, `$`, `/skill:`) |
| `cross_ref_prefix` | `str` | `""` | Cross-reference prefix (`$` for codex, `/skill:` for kimi) |

## Dispatch

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `runner_binary` | `str` | required | CLI binary (`opencode`, `claude`, `codex`, `agent`, ...) |
| `runner_kind` | `RunnerKind` | required | `opencode_run`, `claude_print`, `generic_print` |
| `runner_args` | `tuple[str, ...]` | `()` | Extra args before `--print` (e.g. `("--sandbox", "workspace-write")`) |

## Capabilities

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `has_agents_dir` | `bool` | required | Whether `agents/` subdir is exposed |
| `agent_field_transform` | `Callable \| None` | required | Per-line frontmatter transform (`None` or `strip_agent_line`) |
| `inject_name_in_skill_mirror` | `bool` | required | Auto-inject `name:` in skill mirror |
| `frontmatter_extras` | `dict[str, str]` | `{}` | Extra frontmatter key/value pairs |
| `requires_ide_restart` | `bool` | `False` | Print post-install IDE restart hint |
| `shared_skills_root` | `bool` | `False` | Suppress "no other adapter uses this dir" warning |
| `setup_note` | `str` | `""` | Post-install manual setup hint |

## Detection

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `detect_paths` | `tuple[str, ...]` | required | Project-relative paths (file or directory) |
| `docs_file` | `str` | required | Documentation filename (`AGENTS.md` or `CLAUDE.md`) |

## Per-tool field values (39 upstream tools)

The full table. Reading order: tool_id → all fields.

| tool_id | skills_dir | commands_dir | commands_style | commands_ext | slash_prefix | skill_prefix | runner_binary | runner_kind | has_agents_dir | requires_ide_restart | shared_skills_root | legacy_skills_dirs | global_skills_dir | setup_note |
|---------|------------|--------------|----------------|--------------|--------------|--------------|---------------|-------------|----------------|---------------------|-------------------|-------------------|-------------------|-----------|
| opencode | `.opencode` | `commands` | `flat` | `md` | `osx-` | `/` | `opencode` | `opencode_run` | ✓ | ✗ | ✗ | – | – | – |
| claude | `.claude` | `commands/osx` | `namespaced-with-skill-mirror` | `md` | `osx:` | `/` | `claude` | `claude_print` | ✗ | ✗ | ✗ | – | – | – |
| cursor | `.cursor` | `commands` | `flat` | `md` | `osx-` | `/` | `agent` | `generic_print` | ✗ | ✓ | ✗ | – | – | – |
| codex | `.agents` | `""` | `skills-only` | `md` | `/` | `$` | `codex` | `generic_print` | ✗ | ✗ | ✓ | `(.codex,)` | – | – |
| kimi | `.kimi-code` | `""` | `skills-only` | `md` | `/` | `/skill:` | `kimi` | `generic_print` | ✗ | ✗ | ✗ | `(.kimi,)` | – | – |
| forgecode | `.forge` | `""` | `skills-only` | `md` | `/` | `/` | `forge` | `generic_print` | ✗ | ✗ | ✗ | – | – | – |
| qwen | `.qwen` | `commands` | `flat` | `toml` | `osx-` | `/` | `qwen` | `generic_print` | ✗ | ✗ | ✗ | – | – | – |
| kiro | `.kiro` | `prompts` | `flat` | `prompt.md` | `osx-` | `/` | `kiro-cli` | `generic_print` | ✗ | ✓ | ✗ | – | – | – |
| amazon-q | `.amazonq` | `commands` | `flat` | `md` | `osx-` | `/` | `q` | `generic_print` | ✗ | ✓ | ✗ | – | – | – |
| auggie | `.augment` | `commands` | `flat` | `md` | `osx-` | `/` | `auggie` | `generic_print` | ✗ | ✗ | ✗ | – | – | – |
| bob | `.bob` | `commands` | `flat` | `md` | `osx-` | `/` | `bob` | `generic_print` | ✗ | ✗ | ✗ | – | – | – |
| cline | `.cline` | `commands` | `flat` | `md` | `osx-` | `/` | `cline` | `generic_print` | ✗ | ✓ | ✗ | – | – | – |
| codeartsagent | `.codeartsdoer` | `""` | `skills-only` | `md` | `/` | `/` | `codearts` | `generic_print` | ✗ | ✗ | ✗ | – | – | – |
| codebuddy | `.codebuddy` | `commands/osx` | `namespaced` | `md` | `osx:` | `/` | `codebuddy` | `generic_print` | ✗ | ✓ | ✗ | – | – | – |
| command-code | `.commandcode` | `commands` | `flat` | `md` | `osx-` | `/` | `commandcode` | `generic_print` | ✗ | ✗ | ✗ | – | – | – |
| continue | `.continue` | `prompts` | `flat` | `prompt` | `osx-` | `/` | `""` | `generic_print` | ✗ | ✓ | ✗ | – | – | IDE-only setup hint |
| costrict | `.cospec` | `openspec/commands` | `flat` | `md` | `osx-` | `/` | `cos` | `generic_print` | ✗ | ✓ | ✗ | – | – | – |
| crush | `.crush` | `commands/osx` | `namespaced` | `md` | `osx:` | `/` | `crush` | `generic_print` | ✗ | ✓ | ✗ | – | – | – |
| devin | `.devin` | `workflows` | `flat` | `md` | `osx-` | `/` | `devin` | `generic_print` | ✗ | ✓ | ✗ | `(.windsurf,)` | – | – |
| factory | `.factory` | `commands` | `flat` | `md` | `osx-` | `/` | `droid` | `generic_print` | ✗ | ✗ | ✗ | – | – | – |
| gemini | `.gemini` | `commands/opsx` | `namespaced` | `toml` | `osx:` | `/` | `gemini` | `generic_print` | ✗ | ✗ | ✗ | – | – | – |
| github-copilot | `.github` | `prompts` | `flat` | `prompt.md` | `osx-` | `/` | `copilot` | `generic_print` | ✗ | ✓ | ✗ | – | – | IDE-only setup hint |
| iflow | `.iflow` | `commands` | `flat` | `md` | `osx-` | `/` | `iflow` | `generic_print` | ✗ | ✗ | ✗ | – | – | – |
| junie | `.junie` | `commands` | `flat` | `md` | `osx-` | `/` | `junie` | `generic_print` | ✗ | ✓ | ✗ | – | – | – |
| kilocode | `.kilocode` | `workflows` | `flat` | `md` | `osx-` | `/` | `kilocode` | `generic_print` | ✗ | ✓ | ✗ | – | – | – |
| lingma | `.lingma` | `commands/osx` | `namespaced` | `md` | `osx:` | `/` | `lingma` | `generic_print` | ✗ | ✓ | ✗ | – | – | – |
| oh-my-pi | `.omp` | `commands` | `flat` | `md` | `osx-` | `/` | `omp` | `generic_print` | ✗ | ✗ | ✗ | – | – | – |
| pi | `.pi` | `prompts` | `flat` | `md` | `osx-` | `/` | `pi` | `generic_print` | ✗ | ✗ | ✗ | – | – | – |
| codeassistant | `.codeassistant` | `commands` | `flat` | `md` | `""` | `/` | `""` | `generic_print` | ✗ | ✓ | ✗ | – | – | Natural-language refs |
| qoder | `.qoder` | `commands/osx` | `namespaced` | `md` | `osx:` | `/` | `qoder` | `generic_print` | ✗ | ✓ | ✗ | – | – | – |
| rovodev | `.rovodev` | `""` | `skills-only` | `md` | `""` | `/` | `acli` | `generic_print` | ✗ | ✗ | ✗ | – | – | Natural-language refs + acli subcommand |
| roocode | `.roo` | `commands` | `flat` | `md` | `osx-` | `/` | `roo` | `generic_print` | ✗ | ✓ | ✗ | – | – | – |
| trae | `.trae` | `commands` | `flat` | `md` | `osx-` | `/` | `trae` | `generic_print` | ✗ | ✓ | ✗ | – | – | – |
| vibe | `.vibe` | `""` | `skills-only` | `md` | `/` | `/` | `vibe` | `generic_print` | ✗ | ✗ | ✗ | – | – | – |
| zcode | `.zcode` | `commands/osx` | `namespaced` | `md` | `osx:` | `/` | `zcode` | `generic_print` | ✗ | ✗ | ✗ | – | – | – |
| zed | `.agents` | `""` | `skills-only` | `md` | `/` | `/` | `""` | `generic_print` | ✗ | ✓ | ✓ | – | – | IDE-only setup hint |
| antigravity | `.agents` | `""` | `skills-only` | `md` | `/` | `/` | `agy` | `generic_print` | ✗ | ✓ | ✓ | `(.agent,)` | – | – |
| hermes | `.hermes` | `""` | `skills-only` | `md` | `/` | `/` | `hermes` | `generic_print` | ✗ | ✗ | ✗ | – | – | Hermes external_dirs hint |
| agents | `.agents` | `""` | `skills-only` | `md` | `/` | `/` | `""` | `generic_print` | ✗ | ✗ | ✓ | – | – | Vendor-neutral hint |
| minimax-code | `""` | `""` | `skills-only` | `md` | `/` | `/` | `minimax` | `generic_print` | ✗ | ✗ | ✗ | – | `.minimax` | Global skills hint |

## Fields NOT on ToolAdapter

These exist upstream but do **not** need to be on ToolAdapter because the openspec-extended abstraction absorbs them via existing fields:

| Upstream field | Where openspec-extended handles it |
|----------------|-----------------------------------|
| `successLabel` | Use `tool_name` (no divergence today) |
| `available` | Every shipped adapter is `available: true`; gating deferred |
| `name` | Use `tool_name` |

## Where each field is consumed

| Field | Consumer(s) |
|-------|-------------|
| `tool_id` | `REGISTRY` key; passed everywhere |
| `tool_name` | `{{TOOL_NAME}}` token (`tools.py:_adapter_tokens:275`); log lines; install hint labels |
| `skills_dir` | `TOOL_DIRS` shim (`tools.py:330`); `lib/osx.py:detect_platform`; `{{PLATFORM_DIR}}` token |
| `commands_dir` | `cli.py:deploy_commands:417-419` (multi-segment); `lib/osx.py:commands_dir` |
| `commands_style` | `cli.py:deploy_commands:404-411`; `cli.py:purge_managed_resources:780-845`; `lib/osx.py:_command_resolved_for_phase` |
| `commands_ext` | `cli.py:get_target_path` (PR4); `cli.py:_substitute_tokens_in_file` (PR4); `cli.py:purge_managed_resources` (PR4) |
| `cmd_filename_strip_prefix` | `cli.py:deploy_commands:436-439` |
| `global_skills_dir` | `cli.py:_target_root` (PR7) |
| `legacy_skills_dirs` | `lib/osx.py:migrate_legacy_skills_dirs` (PR6) |
| `slash_prefix` | `{{CMD_PREFIX}}` token; `cli.py:_substitute_tokens:81-83` (slash rewrite) |
| `skill_prefix` | `{{SKILL_PREFIX}}` token; `runner.py:ClaudeRunner:245`, `runner.py:GenericPrintRunner:308` |
| `cross_ref_prefix` | `cli.py:_rewrite_skill_body_refs` |
| `runner_binary` | `runner.py:_binary:159`; `engine.py:1262` (preflight binary probe) |
| `runner_kind` | `runner.py:_runner_for:117-142` |
| `runner_args` | `runner.py:GenericPrintRunner:308-310` |
| `has_agents_dir` | `lib/osx.py:validate_commands:1516-1536` |
| `agent_field_transform` | `cli.py:_build_skill_mirror:378-381` |
| `inject_name_in_skill_mirror` | `cli.py:_build_skill_mirror:372,383` |
| `frontmatter_extras` | `cli.py:_build_skill_mirror:419-456` |
| `requires_ide_restart` | `cli.py:deploy_all_resources` (PR2) |
| `shared_skills_root` | `cli.py:validate_deployment` (PR2); `lib/osx.py:detect_platform` (PR5C) |
| `setup_note` | `cli.py:deploy_all_resources` (PR2) |
| `detect_paths` | `lib/osx.py:detect_platform:218-220`; `runner.py:detect_runner:104-106` |
| `docs_file` | `{{DOCS_FILE}}` token |
| `ask_tool` | `{{ASK_TOOL}}` token (`tools.py:_adapter_ask_tool:241-253`) |
| `install_hint` | `cli.py:validate_skills` warning; `engine.py:215,230` install hint |

## How a future 40th tool would land

After the v1.13.0+ rollout, adding a new tool is:

1. **Tier 1 (one-line REGISTRY entry)**: tool matches an existing `commands_style` and uses `generic_print`. ~30 lines (REGISTRY entry + per-tool snapshot test).

2. **Tier 2 (≤ 3 new fields)**: requires a small field addition (e.g. `plan_args: tuple[str, ...]`). ~100 lines.

3. **Tier 3 (`global_skills_dir`-only)**: home-relative target. ~250 lines.

4. **Beyond Tier 3**: requires a new runner class. This is a sign that the existing 3 runner kinds don't fit; design discussion needed before code.
