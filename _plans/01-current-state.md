# 01 — Current State: What's Blocking Adapter #3

A field-level audit of `orchestrator/source/tools.py` against the upstream OpenSpec Core tool catalogue (`orchestrator/core/source/src/core/config.ts:27-38,40-92`). Every line is anchored to a file in the repo.

> **Status of the 4 preparatory commits.** Five `ToolAdapter` fields (`ask_tool`, `install_hint`, `cross_ref_prefix`, `runner_args`, `frontmatter_extras`) were already added by commit `fb1cffc7` and wired into consumers by `b9305ac5`, `18f97d02`, and `e56acaf2`. The rows below list them as already-shipped; the "needs to be added" section that follows is the post-prep remaining work.

## What's already in place (no work needed)

These fields and behaviours exist on `ToolAdapter` today and cover most of what we need:

| Capability | Field | Locked by | Added in |
|---|---|---|---|
| Per-adapter ask tool | `ask_tool: str = "AskUserQuestion"` (`tools.py:192`) | `TestL1NewAxisHardcodes` | `fb1cffc7` |
| Per-adapter install hint | `install_hint: str = ""` (`tools.py:198`) | `tests/unit/test_tool_registry.py::TestAdapterFieldDefaults` | `fb1cffc7` |
| Per-adapter skill-reference rewrite prefix | `cross_ref_prefix: str = ""` (`tools.py:205`) | consumed by `cli.py:_rewrite_skill_body_refs` | `fb1cffc7` |
| Extra CLI flags before `--print` | `runner_args: tuple[str, ...] = ()` (`tools.py:214`) | consumed by `GenericPrintRunner:runner.py:310` | `fb1cffc7` |
| Extra frontmatter key/value pairs | `frontmatter_extras: dict[str, str] = {}` (`tools.py:220`) | consumed by `cli.py:_build_skill_mirror:419-456` | `fb1cffc7` |
| Skills-only deploy (no command files) | `commands_style="skills-only"` (`tools.py:74`) | `b9305ac5` wired purge/validate hooks | `b9305ac5` |
| Skill-mirror rendering for non-flat styles | `_build_skill_mirror:cli.py` | rendered for `commands_style != "flat"` | `18f97d02` |
| Custom slash prefix per tool | `slash_prefix: str` (`tools.py:131-135`) | token substitution in `_substitute_tokens:cli.py:99-137` | (Phase 1A) |
| Multi-path detection | `detect_paths: tuple[str, ...]` (`tools.py:184-189`) | walked by `detect_platform:lib/osx.py:218-220` | (Phase 1A) |
| Per-tool synthetic test fixtures | `cursor_adapter` fixture in `tests/unit/test_install_multi.py` | `TestParseToolTargetValid::test_accepts_three_tool_inputs` | `e56acaf2` |
| `OpencodeRunner` / `ClaudeRunner` no longer carry `_FALLBACK_BINARY` | constructor requires `adapter` | `TestRunnerForFactory` | `fb1cffc7` |

The `ask_tool` ladder in `tools.py:249-253` (the historical `if adapter.tool_id == "opencode": ...`) **does not exist** — it was removed when `ask_tool` became a field in `fb1cffc7`. `TestL1NewAxisHardcodes` actively fails any future re-introduction.

## What needs to be added (the 6 remaining fields)

Post-prep, **6 fields still need to land** across PRs PR2 (3 fields) + PR6 (2 fields) + PR7 (1 field). The 5 fields added by the preparatory commits are already shipped — see the recap table at the top.

| Field | Default | PR | Purpose | Consumers |
|-------|---------|----|---------|-----------|
| `requires_ide_restart: bool = False` | `False` | PR2 | Surface "Restart your IDE to pick up the new slash commands" hint post-install | `deploy_all_resources:cli.py:760-826` |
| `shared_skills_root: bool = False` | `False` | PR2 | Suppress the "no other adapter uses this dir" sanity check when `.agents` is legitimately shared | `validate_deployment:cli.py:1400-1493` |
| `setup_note: str = ""` | `""` | PR2 | Print a per-tool post-install hint (Hermes needs it) | `deploy_all_resources:cli.py:760-826` |
| `legacy_skills_dirs: tuple[str, ...] = ()` | `()` | PR6 | Map former roots (`.codex`, `.windsurf`, `.kimi`, `.agent`) to the tool's current `skills_dir` for auto-migration | new `migrate_legacy_skills_dirs` helper in `lib/osx.py` |
| `TOOL_ID_ALIASES: dict[str, str]` | module-level constant | PR6 | Resolve `windsurf → devin` before unknown-id checks | new alias-aware path in `_parse_tool_target:cli.py:1521-1552` |
| `global_skills_dir: str \| None = None` | `None` | PR7 | Home-relative skills target (only `minimax-code` declares one) | new `_target_root(adapter, project_root)` resolver in `cli.py` |

Each new field is locked by `TestAdapterFieldDefaults` (extended in PR2, PR6, PR7). Every default preserves shipped behaviour byte-for-byte — verified by `TestOpencodeTokensMatchDocumentedTable` and the equivalent claude tests.

### Why `setup_note` lands alongside `install_hint` instead of replacing it

`install_hint` (already shipped) is the post-install message printed when the deploy fails because the resources are missing — it tells the user **how to install**. `setup_note` (PR2) is the post-install message printed after a **successful** install for tools that need manual configuration (Hermes's `~/.hermes/config.yaml` `external_dirs` entry is the canonical example). The two fields are complementary: `install_hint` is "if something's wrong, run this"; `setup_note` is "after install, you also need to do this once".

## What needs to be generalized (no new fields, just plumbing)

| Change | PR | Where |
|--------|----|-----|
| `_substitute_tokens_in_file` accepts `.toml` and `.prompt.md` | PR4 | `cli.py:380-387` |
| `get_target_path` reads `commands_ext` instead of hardcoding `.md` | PR4 | `cli.py:318-338` |
| `purge_managed_resources` flat branch matches `commands_ext` | PR4 | `cli.py:925-940` |
| `detect_platform` switches from `is_dir()` to `exists()` | PR6 | `lib/osx.py:219` (also `runner.py:105`) |

The `_substitute_tokens_in_file` change is the most subtle. The current `{{TOKEN}}` regex `\{\{([A-Z_]+)\}\}` (`cli.py:54`) is format-agnostic — same syntax works in TOML, YAML, Markdown, and any UTF-8 text. The risk is that Qwen's TOML parser or Kiro's prompt parser might choke on a `{{TOKEN}}` that survives substitution. Mitigation: `_substitute_tokens:cli.py:128-129` already leaves unknown tokens verbatim, which is safe behaviour for any host format.

## What does NOT need to be added

Despite the diversity of upstream's 39 tools, these abstractions stay as-is:

- **`RunnerKind` literals** — 3 stay 3 (per Decision 1 in [00-decisions.md](00-decisions.md)).
- **`CommandsStyle` literals** — 4 stay 4. Every layout upstream uses (`flat`, `namespaced`, `namespaced-with-skill-mirror`, `skills-only`) maps to one of these.
- **`agent_field_transform`** — `strip_agent_line` covers every tool that doesn't read opencode's `agent:` directive.
- **`inject_name_in_skill_mirror`** — covers the Claude-style slash resolver that reads from frontmatter; other tools derive from on-disk name.
- **`cmd_filename_strip_prefix`** — covers the opencode (`osx-`) vs Claude (`osx:`) filename conventions.
- **`docs_file`** — covers AGENTS.md vs CLAUDE.md.

## What does NOT need a custom runner class

This is the key insight from the audit: **none of the 39 upstream tools need a new `RunnerKind` literal**, because all of them fit `GenericPrintRunner`'s argv shape once `runner_args` carries the per-tool flag set:

```
[binary, *runner_args, --print, --dangerously-skip-permissions, prompt]
```

For tools that don't use `--print` (e.g. `codex exec`, `kimi -p`, `qwen -p`), the prompt is passed as a positional argument and `runner_args` would carry the tool's flag — but the argv shape stays `[binary, *runner_args, prompt]` and is still parameterised by `adapter.skill_prefix`. (For prompt-mode tools, `--print` is not used at all; this is a `_runner_for` branch in v1.11.0+ that we explicitly defer — see [00-decisions.md](00-decisions.md) Decision 1.)

For tools that need a subcommand (e.g. `cursor agent`, `acli rovodev run`, `kiro-cli chat`), `runner_args` carries the subcommand:

```python
runner_args=("agent",)              # cursor
runner_args=("run",)                # rovodev
runner_args=("chat", "--no-interactive")  # kiro-cli
```

The argv becomes `[binary, *runner_args, --print, --dangerously-skip-permissions, prompt]` or `[binary, *runner_args, prompt]` depending on the tool. **No new runner class needed** — `GenericPrintRunner` is the right shape for all 39 tools modulo which flags land in `runner_args`.

The only structural divergence is `OpencodeRunner` itself, which uses `opencode run --command <cmd> --agent <agent> <change>` rather than the print-style argv. That shape is unique to opencode and stays behind `runner_kind="opencode_run"`. We never replicate it for a third tool.

## Where the audit was done

Full per-tool mapping in [research/03-tool-adapter-audit.md](research/03-tool-adapter-audit.md). Per-tool invocation shapes (CLI argv, plan flags, sandbox flags) in [research/02-tool-invocation-shapes.md](research/02-tool-invocation-shapes.md). Original `ToolAdapter` field inventory at `orchestrator/source/tools.py:88-226`. Original `AIToolOption` shape at `orchestrator/core/source/src/core/config.ts:27-38`. Original `AI_TOOLS` registry at `orchestrator/core/source/src/core/config.ts:40-92`.

## Net change footprint

| File | Lines added | Lines removed | Net |
|------|-------------|---------------|-----|
| `orchestrator/source/tools.py` | ~250 (6 fields + ~30 REGISTRY entries across the rollout) | 0 | +250 |
| `orchestrator/source/cli.py` | ~150 (hint printing, `_target_root`, alias resolution, extension-aware purge) | ~10 (hardcoded `.md`) | +140 |
| `orchestrator/source/lib/osx.py` | ~150 (migration helper, `migrate_legacy_skills_dirs`, alias-aware detection) | ~5 (`is_dir()` → `exists()`) | +145 |
| `orchestrator/source/orchestrator/runner.py` | ~30 (`plan_args` consumption) | 0 | +30 |
| `tests/unit/test_tool_registry.py` | ~400 (per-tool snapshots, field-defaults locks) | ~30 (synthetic fixture teardown) | +370 |
| `tests/unit/test_runner_abstraction.py` | ~150 | ~30 | +120 |
| `tests/unit/test_cli_registry_consumers.py` | ~250 | ~30 | +220 |
| `tests/unit/test_lib_registry_consumers.py` | ~150 | ~30 | +120 |
| `tests/unit/test_install_multi.py` | ~50 | 0 | +50 |
| `tests/integration/test_install_flow.py` | ~30 | 0 | +30 |
| docs (.opencode/rules/per-adapter-rendering.md, AGENTS.md files) | ~250 | 0 | +250 |
| **Total** | **~1860** | **~165** | **~+1700 net** |

Distributed across 7 PRs; each PR lands in isolation and is independently reviewable.
