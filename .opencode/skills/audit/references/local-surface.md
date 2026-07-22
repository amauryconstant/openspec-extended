# Local Surface Map Template (openspec-extended)

Use this template to capture the local surface in Phase B. Fill every applicable section; mark sections N/A when the surface lacks the artifact. Cite `file:line` for every claim.

## Contents

- [Repository Metadata](#repository-metadata)
- [Top-level CLI (`source/cli.py`)](#top-level-cli-sourceclipy)
- [`osx` Sub-app (`source/osx_cli.py`)](#osx-sub-app-sourceosx_clipy)
- [Library (`source/lib/osx.py`)](#library-sourcelibosxpy)
- [Orchestrator (`source/orchestrator/`)](#orchestrator-sourceorchestrator)
- [Skills (8)](#skills-8)
- [Agents (3)](#agents-3)
- [Commands (12)](#commands-12)
- [Manifest Format](#manifest-format)
- [State Files](#state-files)
- [Documentation](#documentation)

## Repository Metadata

| Field | Value |
|-------|-------|
| Project path | `<cwd>` |
| Head commit | `<hash>` |
| Date | `<YYYY-MM-DD>` |
| Project version (`source/__init__.py`) | `<A.B.C>` |
| Python version | `≥3.12` |
| Build system | PyInstaller (`openspec.spec`) |
| Package manager | `uv` (`pyproject.toml`) |
| File count (Python source) | `<number>` |
| Lines of code (Python source) | `<number>` |

## Top-level CLI (`source/cli.py`)

Source: `source/cli.py`.

| # | Command | Purpose | Key flags | file:line |
|---|---------|---------|-----------|-----------|
| 1 | `install TOOL` | Deploy extended resources | `--with-core` | `cli.py:522-550` |
| 2 | `update TOOL` | Force-overwrite extended resources | `--with-core` | `cli.py:552-579` |
| 3 | `orchestrate [CHANGE]` | Run 7-phase autonomous workflow | `--store`, `--timeout`, `--model`, `--log-file`, `--verbose`, `--dry-run`, `--force`, `--clean`, `--no-color`, `--max-phase-iterations`, `--from-phase`, `--schema`, `--list` | `cli.py:582-645` |
| 4 | `validate [ITEM]` | Passthrough to `openspec validate` | `--all`, `--changes`, `--specs`, `--type`, `--strict`, `--json`, `--concurrency`, `--no-interactive`, `--store` | `cli.py:648-692` |
| 5 | `list` | Passthrough to `openspec list` | `--specs`, `--changes`, `--sort`, `--json`, `--store` | `cli.py:695-716` |
| 6 | `show [ITEM]` | Passthrough to `openspec show` | `--type`, `--deltas-only`, `--requirements-only`, `--requirements`, `--no-scenarios`, `-r/--requirement`, `--json`, `--store` | `cli.py:719-767` |
| 7 | `status` | Passthrough to `openspec status` | `--change`, `--schema`, `--json`, `--store` | `cli.py:770-788` |
| 8 | `instructions [ARTIFACT]` | Passthrough to `openspec instructions` | `--change`, `--schema`, `--json`, `--store` | `cli.py:791-815` |
| 9 | `templates` | Passthrough to `openspec templates` | `--schema`, `--json` | `cli.py:818-830` |
| 10 | `schemas` | Passthrough to `openspec schemas` | `--json` | `cli.py:833-842` |
| 11 | `schema ACTION ...` | Generic passthrough to `openspec schema` | action-specific (`which`, `list`, `validate`, `fork`, `init`) | `cli.py:845-892` |
| 12 | `init [PATH]` | Passthrough to `openspec init` | `--tools`, `--force`, `--profile` | `cli.py:895-919` |
| 13 | `update-core [PATH]` | Passthrough to `openspec update` | `--force` | `cli.py:922-937` |
| 14 | `feedback MESSAGE` | Passthrough to `openspec feedback` | `--body` | `cli.py:940-952` |
| 15 | `completion [SHELL]` | Passthrough to `openspec completion` | `--install`, `--uninstall`, `--verbose`, `--yes` | `cli.py:955-976` |

The internal `osx` sub-app is mounted at `cli.py:34`: `app.add_typer(osx_app, name="osx")`.

## `osx` Sub-app (`source/osx_cli.py`)

Source: `source/osx_cli.py`. Output contract: success → single JSON object on stdout; `OSXError` → JSON on stderr + exit 1.

| Domain | Actions | file:line |
|--------|---------|-----------|
| `baseline` | `record`, `get` (alias: `show`) | `osx_cli.py:64-75` |
| `ctx` | `get CHANGE` (alias: `show`) | `osx_cli.py:78-89` |
| `git` | `get CHANGE` (alias: `show`) | `osx_cli.py:91-102` |
| `phase` | `current`, `next`, `advance` | `osx_cli.py:104-122` |
| `state` | `get`, `complete`, `transition`, `clear-transition`, `set-phase` (aliases: `show`, `clear`, `set`) | `osx_cli.py:125-160` |
| `iterations` | `get` (read); append via flags | `osx_cli.py:163-210` |
| `log` | `get` (read); append via flags | `osx_cli.py:213-258` |
| `complete` | `check`, `get`, `set [STATUS] [--blocker-reason]` | `osx_cli.py:261-285` |
| `validate` | `json`, `skills`, `commands`, `change-dir`, `archive`, `iterations`, `completion`, `change`, `spec`, `all`, `changes`, `specs` | `osx_cli.py:288-380` |
| `instructions` | `ARTIFACT [--change] [--json]` (shells out to `openspec instructions`) | `osx_cli.py:383-402` |
| `store` sub-app | `list`, `doctor [STORE]`, `register PATH [--name NAME]`, `unregister STORE` | `osx_cli.py:405-439` |
| `schema` sub-app | `which`, `list`, `validate`, `fork`, `init` | `osx_cli.py:442-507` |

`--store` / `-s` is a global option on `osx`, sets `osx_lib.current_store` context (`osx_cli.py:27-42`).

## Library (`source/lib/osx.py`)

Source: `source/lib/osx.py`. Pure Python; no Typer imports.

| Domain | Functions | file:line |
|--------|-----------|-----------|
| Platform/layout | `detect_platform`, `skills_dir`, `commands_dir` | `lib/osx.py:87-111` |
| Change/store resolution | `resolve_change_paths`, `_find_change_dir` | `lib/osx.py:164-247` |
| Time/JSON | `get_timestamp`, `write_json`, `append_to_json_array`, `get_next_phase` | `lib/osx.py:124-353` |
| Baseline | `baseline_record`, `baseline_get` | `lib/osx.py:361-409` |
| Context | `ctx_get` | `lib/osx.py:412-505` |
| Git | `git_get` | `lib/osx.py:508-557` |
| Phase | `phase_current`, `phase_next`, `phase_advance` | `lib/osx.py:560-659` |
| State | `state_get`, `state_complete`, `state_transition`, `state_clear_transition`, `state_set_phase` | `lib/osx.py:662-778` |
| Iterations | `iterations_get`, `iterations_append` | `lib/osx.py:781-877` |
| Decision log | `log_get`, `log_append` | `lib/osx.py:880-986` |
| Complete/blocker | `complete_check`, `complete_get`, `complete_set` | `lib/osx.py:989-1056` |
| Store delegation | `store_list`, `store_doctor`, `store_register`, `store_unregister` | `lib/osx.py:1059-1085` |
| Validation (local + upstream-translated) | `validate_json`, `validate_skills`, `validate_commands`, `validate_change_dir`, `validate_archive`, `validate_iterations`, `validate_completion`, `validate_change`, `validate_spec`, `validate_all`, `validate_changes_only`, `validate_specs_only`, `_translate_validate_payload`, `_run_openspec_json` | `lib/osx.py:1088-1494` |
| Schema | `resolve_schema`, `list_artifacts_for_schema`, `required_core_skills`, `schema_which`, `schema_validate`, `schema_fork`, `schema_init`, `schema_list` | `lib/osx.py:1490-1679` |
| Validation safety | `_validate_log_text_field` (zsh command-substitution fingerprint guard) | `lib/osx.py:60-65, 269-299` |

Phase constants are also defined at `source/orchestrator/engine.py:29-59` (duplication).

## Orchestrator (`source/orchestrator/`)

Source: `source/orchestrator/engine.py` + `runner.py`.

| Component | Purpose | file:line |
|-----------|---------|-----------|
| `OrchestratorState` | 21-field state container (change_id, paths, timeouts, model, store, schema, etc.) | `engine.py:87-110` |
| Phase constants | `PHASES`, `PHASE_NAMES`, `PHASE_COMMANDS`, `PHASE_AGENTS` (duplicated from `lib/osx.py`) | `engine.py:29-59` |
| Phase dispatch table | PHASE0 REVIEW → `osx-phase0`/`osx-analyzer`; PHASE1 IMPL → `osx-phase1`/`osx-builder`; PHASE2 REVIEW → `osx-phase2`/`osx-analyzer`; PHASE3 DOCS → `osx-phase3`/`osx-maintainer`; PHASE4 SYNC → `osx-phase4`/`osx-maintainer`; PHASE5 REFLECT → `osx-phase5`/`osx-analyzer`; PHASE6 ARCHIVE → `osx-phase6`/`osx-maintainer` | `engine.py:29-59` |
| `run_orchestrator` | Main entry; constructs state, runs preflight, dispatches phases | `engine.py:851-...` |
| Preflight | Validates skills/commands/git/change; gated on `state.clean` (`engine.py:930-989`) | `engine.py:930-989` |
| Per-phase loop | `run_phase`; iteration counter; waits for `phase_complete=true` | `engine.py:578-607` |
| Transition handling | Reads/clears `state.transition` after each phase | `engine.py:1093-1112` |
| Blocker handling | Reads `complete.json` before each phase; halts if `with_blocker=true` | `engine.py:1038-1057` |
| PHASE6 special-case | `archive_log_file` moves auto log into archive; cleanup deletes transient files | `engine.py:659-714, 1066-1091, 777-782` |
| Cleanup on success | Removes `state.json`, `complete.json`, `.openspec-baseline.json`, auto log | `engine.py:767-788` |
| `get_version` | Reads `resources.scripts.osx-orchestrate` (key never set) | `engine.py:71-84` |
| Runner detection | OpenCode wins ties over Claude | `runner.py:65-84` |
| OpenCode invocation | `opencode run --command <cmd> --agent <name> <id> --title=... --model=...` | `runner.py:87-110` |
| Claude invocation | `claude --print --dangerously-skip-permissions "/<cmd> <id>"` | `runner.py:113-135` |
| Log/signal handling | Background thread streams stdout/stderr; SIGINT/SIGTERM kills child | `runner.py:138-203` |

## Skills (8)

Per `resources/opencode/manifest.toml:1-23`.

| Skill | Version | Purpose | file:line |
|-------|---------|---------|-----------|
| `osx-concepts` | 0.9.0 | Framework/reference taxonomy for AI agents | `skills/osx-concepts/SKILL.md` |
| `osx-workflow` | 0.3.0 | 7-phase protocol + state CLI operational reference | `skills/osx-workflow/SKILL.md` |
| `osx-review-artifacts` | 0.3.0 | Schema-aware preimplementation audit (read-only) | `skills/osx-review-artifacts/SKILL.md` |
| `osx-modify-artifacts` | 0.3.0 | Surgical schema-aware single-artifact editor (forward-only) | `skills/osx-modify-artifacts/SKILL.md` |
| `osx-review-test-compliance` | 0.2.2 | Semantic spec-scenario ↔ test alignment | `skills/osx-review-test-compliance/SKILL.md` |
| `osx-maintain-ai-docs` | 0.2.0 | Updates `AGENTS.md`/`CLAUDE.md` from artifacts + git history | `skills/osx-maintain-ai-docs/SKILL.md` |
| `osx-generate-changelog` | 0.2.1 | Keep-a-Changelog entry from archived proposals | `skills/osx-generate-changelog/SKILL.md` |
| `osx-commit` | 0.1.0 | Conventional / Angular / Gitmoji / Classic commit-style detection | `skills/osx-commit/SKILL.md` |

`REQUIRED_SKILLS` is hardcoded at `lib/osx.py:67-74` and includes 6 of the 8 (omits `osx-commit`, `osx-generate-changelog`).

## Agents (3)

Per `resources/opencode/agents/`.

| Agent | Version | Mode | Edit | Question | Temperature | file:line |
|-------|---------|------|------|----------|-------------|-----------|
| `osx-analyzer` | 0.2.2 | `all` | deny | deny | 0.1 | `agents/osx-analyzer.md` |
| `osx-builder` | 0.2.2 | `all` | allow | deny | 0.4 | `agents/osx-builder.md` |
| `osx-maintainer` | 0.2.2 | `all` | allow | deny | 0.3 | `agents/osx-maintainer.md` |

Convention says `mode: subagent` for orchestrator-dispatched agents (`resources/opencode/agents/AGENTS.md:34`).

## Commands (12)

Per `resources/opencode/manifest.toml:34-68`.

**User-facing (5):**

| Command | Version | Purpose | file:line |
|---------|---------|---------|-----------|
| `osx-changelog` | 0.1.1 | Generate Keep-a-Changelog entry | `commands/osx-changelog.md` |
| `osx-maintain-docs` | 0.1.1 | Update AGENTS.md/CLAUDE.md | `commands/osx-maintain-docs.md` |
| `osx-modify` | 0.2.0 | Wrapper for surgical single-artifact edit | `commands/osx-modify.md` |
| `osx-review` | 0.2.0 | Schema-driven pre-impl audit | `commands/osx-review.md` |
| `osx-verify-tests` | 0.1.2 | Spec-to-test alignment | `commands/osx-verify-tests.md` |

**Orchestrator-only (7):**

| Command | Version | Phase | Agent | file:line |
|---------|---------|-------|-------|-----------|
| `osx-phase0` | 0.3.0 | ARTIFACT REVIEW | `osx-analyzer` | `commands/osx-phase0.md` |
| `osx-phase1` | 0.3.5 | IMPLEMENTATION | `osx-builder` | `commands/osx-phase1.md` |
| `osx-phase2` | 0.3.0 | REVIEW | `osx-analyzer` | `commands/osx-phase2.md` |
| `osx-phase3` | 0.3.5 | MAINTAIN DOCS | `osx-maintainer` | `commands/osx-phase3.md` |
| `osx-phase4` | 0.2.13 | SYNC | `osx-maintainer` | `commands/osx-phase4.md` |
| `osx-phase5` | 0.3.4 | SELF-REFLECTION | `osx-analyzer` | `commands/osx-phase5.md` |
| `osx-phase6` | 0.3.6 | ARCHIVE | `osx-maintainer` | `commands/osx-phase6.md` |

Claude mirror exists at `resources/claude/commands/osx/<name>.md`.

## Manifest Format

`resources/{opencode,claude}/manifest.toml`:

```toml
[resources.skills.osx-<name>]
version = "<semver>"

[resources.agents.osx-<name>]
version = "<semver>"

[resources.commands.osx-<name>]
version = "<semver>"
```

Versions bumped per-resource by `mise run version:update`. Pre-commit hook at `.pre-commit-config.yaml` gates staged changes to resource files + `install.sh`.

## State Files

| File | Location | Owner | Schema (informal) |
|------|----------|-------|-------------------|
| `state.json` | `<change_dir>/` | orchestrator | `{phase, phase_name, iteration, phase_complete, phase_iterations, total_invocations, started_at, last_updated, transition?}` |
| `complete.json` | `<change_dir>/` | orchestrator | `{status, with_blocker, blocker_reason?}` |
| `iterations.json` | `<change_dir>/` | orchestrator | array of iteration entries |
| `decision-log.json` | `<change_dir>/` | orchestrator | array of decision entries |
| `.openspec-baseline.json` | repo root | orchestrator | `{commit, branch, timestamp}` |
| `.osx-orchestrate-<change>.log` | repo root | runner | free-form log |
| `verification-report.md` | `<change_dir>/` | PHASE2 | free-form report |
| `reflections.md` | `<change_dir>/` | PHASE5 | free-form report |
| `test-compliance-report.md` | `<change_dir>/` | `osx-review-test-compliance` | free-form report |
| `suggestions.md` | `<change_dir>/` | PHASE2 | free-form report |

`.gitignore` patterns added at `cli.py:322-349`. Core never reads these files.

## Documentation

| Doc | Purpose | file:line |
|-----|---------|-----------|
| Root `AGENTS.md` | Project contract, naming, version domains, testing | `AGENTS.md` |
| `README.md` | User-facing overview, install, comparison | `README.md` |
| `install.sh` | Bash installer (downloads PyInstaller binary) | `install.sh` |
| `docs/` | Extended docs | `docs/` |
| `source/AGENTS.md` | Source subsystem contract | `source/AGENTS.md` |
| `source/lib/AGENTS.md` | `osx.py` module contract | `source/lib/AGENTS.md` |
| `source/orchestrator/AGENTS.md` | Engine/runner contract | `source/orchestrator/AGENTS.md` |
| `resources/AGENTS.md` | Resource types + manifest format | `resources/AGENTS.md` |
| `resources/opencode/AGENTS.md` | OpenCode platform conventions | `resources/opencode/AGENTS.md` |
| `resources/opencode/commands/AGENTS.md` | OpenCode commands layout | `resources/opencode/commands/AGENTS.md` |
| `resources/opencode/skills/AGENTS.md` | OpenCode skills layout | `resources/opencode/skills/AGENTS.md` |
| `resources/opencode/agents/AGENTS.md` | OpenCode agents layout | `resources/opencode/agents/AGENTS.md` |
| `research/opencode-docs.md` | Platform capability reference | `research/opencode-docs.md` |
