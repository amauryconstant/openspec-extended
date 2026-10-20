# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]

## [1.12.1] - 2026-10-20

### Added

- Add a `build:local` mise task that builds the PyInstaller one-file binary and installs it into the local bin dir, so a contributor can exercise the frozen CLI straight from `PATH` without cutting a release tarball or running `install.sh`. The task depends on the existing `build` task, so its source-staleness check still skips PyInstaller when nothing under `orchestrator/source`, `orchestrator/resources`, or `skills/resources` has changed — the copy and chmod re-run every time, which makes it a cheap reinstall loop. The destination resolves to `$XDG_BIN_HOME`, defaulting to `~/.local/bin` to match `install.sh`'s `PREFIX` default, and the task warns when that directory is absent from `PATH`. Declared in `.mise/config.toml` rather than as a file task because mise normalizes a colon-named file (`.mise/tasks/build:local`) to `build_local`, which would leave `mise run build:local` unresolvable — the same reason `test:unit` and `version:check` live in the config. Document the task in the README Development block and the `AGENTS.md` command table.

### Changed

- Sync the vendored OpenSpec subtree at `orchestrator/core/source` to upstream v1.14.3 (commit `c794978f…84c`).
- Rewrite the entire `CHANGELOG.md` history in the same full Keep-a-Changelog prose style established for the v1.11.0–v1.12.0 work. Older releases had terse commit subjects pulled by the original heuristic; every bullet is now expanded to the same `imperative subject + body` form, with file paths, test counts, and rationale inlined. Backfill: 3 new release sections (`v1.11.0`, `v1.11.1`, `v1.12.0`) and 7 missing v1.12.0 bullets drafted from the corresponding commit bodies (the 5-commit Side dispatch refactor series + PHASE0 self-heal + redundant e2e deletion + engine dispatch-tail collapse). Related-commit collapsing applied across the file — 306 total bullets across 79 sections, diff +334 / −308 (net +26).

## [1.12.0] - 2026-09-19

### Added

- Introduce a Side-aware canonical resource tree at `.opencode/` (`commands/` + `skills/` + per-side `manifest.toml`) replacing the legacy `opencode/canonical/` and `skills/canonical/` trees. The commands tree ships 12 `osc-*` wrappers vendored from OpenSpec v1.13.1 plus 4 `osx-*` wrappers (`osx-changelog`, `osx-maintain-docs`, `osx-review`, `osx-verify-tests`) that delegate to the matching skill body; the skills tree ships the matching 12 `osc-*` + 3 `osx-*` skills (`osx-commit`, `osx-review-artifacts`, `osx-review-test-compliance`) with their references and the `detect-commit-style` helper. Both manifests pin core (1.13.1) and extended (0.x.y) resource versions so the deploy side can fail-fast on drift.

### Changed

- Land a four-commit "Side dispatch refactor" series: split the seven mixed-attribution resource constants in `lib/osx.py` into per-side sub-modules (`lib/osx/sides/orchestrator.py`, `skills.py`, `core.py`) with the package re-exporting the symbols at module level so existing call sites keep resolving byte-for-byte; unify shared-references resolution behind a single `_shared_refs_dir()` helper that always points at the orchestrator-side canonical tree (closing a latent bug where `_deploy_skill_mirror` resolved to a non-existent `skills/resources/canonical/skills/references/` path and silently dropped every ref copy); enforce Phase 5 resource separation in deploy and validator (reject side manifests that declare non-`osx-*` names or share keys, split `deploy_all_resources` into `deploy_orchestrator_side` + `deploy_skills_side`, stamp `meta.side` on each deployed manifest, extend `validate_commands` to walk the skills-side manifest); and introduce a `Side = Literal["orchestrator", "skills"]` type alias in `source.tools` that three call sites (`_deploy_one_side`, `_validate_target_after_deploy`, `_load_per_side_manifests`) annotate so a typo at any dispatch site becomes a static error rather than silently misrouting. Six new manifest-ownership tests and four skills-side validator tests pin the contracts.
- Consolidate the engine dispatch tail and phase-transition table: collapse the 41 byte-identical runner-tail lines shared by `engine.run_agent` and `engine._run_auto_fix` into a new `engine._dispatch(state, request, *, splice_label, timeout_msg, failure_msg)` (both callers keep their own pre-checks and `RunRequest`; the unreachable post-run `child_pid` fallback is dropped, the now-unused `on_pid` parameter is removed from `build_run_request`); replace `engine.advance_phase`'s private copy of the phase-transition table with a re-export of `osx.get_next_phase`; and remove three no-op declarations surfaced by a repo-wide audit (`_FENCE_OPEN` in `cli.py`, `get_source_type_dir` in `cli.py`, `_ORCHESTRATION_SKILL_NAMES` in `lib/osx.py`). The shared `_dispatch` tail gains `TestDispatchSharedTail` unit coverage; `tests/unit/test_phase_constants_identity.py` gains the matching `engine.advance_phase is osx.get_next_phase` assertion.
- Make PHASE0 self-heal on `/osc-update-change` routes and drop the redundant e2e that pinned the regression: the engine used to halt on any non-empty `routes_pending`, including auto-fixable `/osc-update-change` routes that an audit agent emits when existing artifacts need reconciliation. The orchestrator now dispatches the fix itself instead of surfacing it to the caller. The now-redundant `tests/e2e/self-heal-workflow.bats` is deleted because the regression surface it pinned (engine halt vs auto-fix on `/osc-update-change`) is fully covered by finer-grained `TestPhase0RouteHaltFallback` (4 cases) plus `TestDispatchSharedTail` unit coverage — the e2e required `E2E_CONFIRM=1` and ~20 min of AI subprocess time to exercise a single path.

## [1.11.1] - 2026-09-18

### Changed

- Extract the shared opencode-tree setup/teardown logic into `setup_shared_e2e_dir` / `teardown_shared_e2e_dir` helpers so individual bats files can override `setup_file()` while still sharing the pre-installed opencode tree (~10x faster than per-test reinstalls). Wire `full-workflow.bats` to the new helpers via `setup_file` / `teardown_file` overrides and add a `check-e2e-shared-setup` pre-commit hook that verifies every `tests/e2e/*.bats` overriding those entry points chains the shared helpers (guards the `cp: cannot stat /.opencode` failure mode where `SHARED_E2E_DIR` is never populated).
- Drop `mode: subagent` from the four orchestrator-dispatched agents (`osx-analyzer`, `osx-builder`, `osx-maintainer`, `osx-reviewer`): newer runtimes reject subagent dispatch via `opencode run --agent <name>` and silently fall back to the default primary agent, which drops the per-phase `permission:` block (e.g. PHASE0's read-only `edit: deny`). `hidden: true` alone keeps agents off the user-driven picker; orchestrator dispatch via `--agent` continues to work. Rename `TestAgentsAreSubagent` → `TestOrchestratorAgentsAreHiddenFromPicker`; the test now asserts both `hidden == "true"` (picker invisibility) and `mode != "subagent"` (forward-looking lock).
- Surface the designed `routes_pending` halt as a distinct exit in `full-workflow.bats`: grep the log for `Halted for routed commands` and print the routed command list straight to bats' stderr so the next audit-strictness change is debuggable from the bats output alone instead of fishing the log out of the test tmpdir. Fall back to the prior `Workflow did not produce an archive` message plus a pointer to the `.osx-orchestrate-*.log` file when the halt isn't `routes_pending`.

### Fixed

- Mirror `show_progress()` output to `state.log_file` so the Progress Summary lands in the archived `osx-orchestrate.log`. Previously every line in `show_progress` used `print()`, bypassing the orchestrator's `log*` helper contract and breaking the e2e `log: has expected content` assertion that greps for "Progress Summary" in the archived log. Also skip `show_progress` after PHASE6 (state.json is gone by then), aligning with the upstream `openspec-auto` precedent referenced in `skills/resources/canonical/skills/osx-commit/SKILL.md`. Regression-locked by `TestShowProgressMirrorsToFile` in `tests/unit/test_engine_logging.py`.
- Rename the PHASE6 decision-log key from `archived_path` to `archive_path` across the phase-command body, the `osx-decision-logging.md` reference, and the E2E suite (the AI follows the body verbatim, so drift silently strands data on the wrong key). Lock the alignment with `TestPhase6DecisionLogKeys` and document the "Key naming is authoritative" invariant in `osx-decision-logging.md` so future renames update the body, the reference, and the E2E suite together.
- Bring `tests/fixtures/changes/add-hello-script` back in sync with the PHASE0 audit tightened by the 02c2a35d severity-threshold change. The fixture's spec previously named internal function names (`usage()`, `main()`, `main "$@"`) and language constructs (`readonly`, `local`) in a normative SHALL rule (violating the spec-driven schema's "Avoid in specs: Internal class/function names" guidance), and listed a `Exit Codes`/`Invalid flag` scenario with no matching task-6 verification entry — both routed to `/osc-update-change` and halted `full-workflow.bats`. Drop the `Code Quality` and `Bash Strict Mode` requirements (both belong in `design.md`'s Decisions section, where they already live) and add task 6.6 for the invalid-flag smoke test.
- Harden `test_cleanup_skips_when_path_disappears` against pytest-xdist and isolated-run order dependence: the previous test relied on stale `_PATHS_CACHE` entries from earlier fixtures in the class to mask resolution. Switch to an explicit empty `cwd` plus a stubbed `_resolve_post_phase6_path` so the contract holds regardless of execution order.

## [1.11.0] - 2026-09-17

### Added

- Introduce `CHANGELOG.md` in Keep a Changelog 1.1.0 + SemVer format, with one `## [X.Y.Z] - YYYY-MM-DD` section per vX.Y.Z git tag covering all 75 prior releases. Each release's commit subjects are bucketed into Added / Changed / Fixed / Removed / Breaking / Security via a keyword heuristic, the `## [Unreleased]` section is placed first, and the latest release sits immediately below it.

### Changed

- Cross-reference every upstream Core skill in the orchestration prompts: PHASE0 gains `/osc-apply-change` and `/osc-new-change`; PHASE2 gains missing-artifact and design-ambiguity sub-cases; PHASE4 routes malformed-delta fixes via `/osc-update-change`. Cross-reference the slash-command wrappers (`PHASE0 → /osx-review`, `PHASE1 → /osx-verify-tests`, `PHASE6 → /osx-changelog`). Add a pause-and-route guardrail to PHASE1 on scope / design drift and an optional `/openspec-explore` pre-step in PHASE5 when iteration history is dense. Add a top-of-file "Before you orchestrate" callout in `osx-workflow` with 5 entry points and mirror every enhancement in `autonomous-workflow.md`. Patch-bump 12 orchestration resources via `mise run version:update`.
- Stop halting PHASE0 with "Halted for routed commands" on any non-empty finding set: only Critical / Warning findings now set `routes_pending`, while Suggestion-only findings log to `decision-log.json` / `iterations.json` and complete the phase. Align the engine with the `osx-review-artifacts` policy ("Suggestion → optional; user may proceed"). Document the threshold in `osx-workflow` §5 and in the state-updates table, and add a severity-calibration guardrail requiring agents to classify anything that misleads implementation or breaks the dependency graph at least Warning so the new threshold does not regress review quality. Backed by `TestPhase0SeverityThreshold`.
- Reformat the four pre-/post-implementation review resources (`osx-review`, `osx-verify-tests`, `osx-review-artifacts`, `osx-review-test-compliance`) and their slash-command wrappers to OpenSpec Core conventions: add `metadata.author: openspec-extended`, convert `## Steps` / `## Output` / `## Guardrails` H2 sections to bold pseudo-headings, convert `#### Step Nb` H4 sub-steps to lettered sub-points (a., b.), and add missing H1s. Preserve all project value-adds (severity classification, `{{ASK_TOOL}}` / `{{PLATFORM_DIR}}` tokens, invocation matrix, tips, failure modes). Bump `osx-review` to 0.3.0, `osx-verify-tests` to 0.2.0, `osx-review-artifacts` to 0.4.0, and `osx-review-test-compliance` to 0.3.0.
- Restrict `detect_bump_type()` in `detect.sh` to scanning only added diff lines for `feat:` / `fix:` / `breaking` / `major:` keywords. Previously both `+` and `-` lines were scanned, so removing documentation that mentioned "breaking changes" (e.g. the Conventional Commits spec line in `osx-commit`) tripped the major-bump heuristic. Line-count heuristics (`removed > added * 2` → major, `added > 0` → minor, else patch) are unchanged.
- Reformat `osx-commit` — the last remaining gap-filling skill — to match the OpenSpec Core workflow-camp convention: add `metadata.author: openspec-extended`, convert `## Process` to a **Steps** numbered list, convert `## Format examples` to **Output**, and add a new **Guardrails** section. Preserve all project value-adds (4-style detection matrix, per-standard application rules and examples, common types / emojis / verbs, `{{ASK_TOOL}}` token, fallback rule). Reorder the Conventional Commits spec text from "breaking changes" to "incompatible commits" so it does not trip the bump-detection keyword heuristic. Bump `osx-commit` to 0.3.0.
- Reformat the `osx-workflow` 7-phase reference manual to a hybrid convention: add `metadata.author: openspec-extended` to frontmatter and add a **Steps** bold pseudo-heading above the existing 7-phase sequence diagram (the diagram is the procedural spine). Keep all §1–§11 sections verbatim so cross-references from `osx-phase0..6` remain valid. Bump `osx-workflow` to 0.6.0.
- Replace `git subtree pull --squash` in `mise run sync-core` with a force-replace sequence (fetch tag, `git rm -rf $PREFIX`, `git read-tree --prefix=$PREFIX -u <upstream-tree>`, squash-commit with `git-subtree-dir` / `git-subtree-split` annotations). The previous 3-way merge combined a stale locked `git-subtree-split` SHA against the local prefix and the new tag and produced spurious conflicts on every pull after the first relocate, even though the on-disk tree is always pristine. Only the steady-state pull path is replaced; old-prefix migration seed and initial subtree-add paths are left intact. Update `orchestrator/core/AGENTS.md` step 2 and `.opencode/rules/vendored-subtree.md` to document the new mechanics.
- Sync the vendored OpenSpec subtree at `orchestrator/core/source` to upstream v1.13.1 (commit `634c557b…3c1b`).
- Gate `mise run release` on a populated `CHANGELOG.md` entry for the upcoming version (either `## [Unreleased]` or `## [<X.Y.Z>]`); the check runs before any file mutations, so a failed gate leaves the working tree clean. Add a `--skip-changelog-check` flag to bypass the gate for hotfixes, document the prerequisite in `AGENTS.md`, `README.md`, and `.opencode/rules/version-management.md`, and cover the helper with a new bats suite at `tests/unit/test_changelog_gate.bats` wired into `test:unit:bats`.

### Fixed

- Correct three stale claims in `AGENTS.md` discovered during an audit: bump the `osx-review-artifacts` example block to 0.4.0 (manifest, after the 07b6b3a1 bump); correct the `REQUIRED_SKILLS` count from 5 to 3 in `orchestrator/source/lib/AGENTS.md` (the two slash commands `osx-review` / `osx-verify-tests` are commands, not skills, and were correctly excluded — only the count was stale); and add `lib/state_io.py` and `orchestrator/runner.py` to the "Files" table in `orchestrator/source/AGENTS.md`. No code or behavior change.
- Replace the PCRE lookaheads `(?!\+\+)` / `(?!--)` in `detect_bump_type()` with ERE-compatible character classes (`^\+[^+]` / `^-[^-]`). POSIX ERE silently emitted `grep: warning: ? at start of expression` and returned 0 for both counts, so every non-keyword diff defaulted to a patch bump regardless of actual change size.

## [1.10.7] - 2026-09-16

### Changed

- Eliminate the redundant backups and nested core orphans left behind by `install --with-core --force` against trees that already carried the renamed `osc-*` core resources. Two artefacts recurred: `*.user-backup-*` files inside every `osc-*/SKILL.md` and `commands/osc-*.md`, because the renamer's collision branch always backed up the existing file even when the incoming content was byte-for-byte identical to what the wrapper had previously written itself; and `osc-X/openspec-X/SKILL.md` nests, because `openspec init` writes a nested skill dir inside the existing renamed one and the renamer's merge branch does not recurse. Three fixes: `_backup_existing` short-circuits when incoming bytes match the existing file (file targets only; dir targets still copy); `_purge_identical_backups` is a new post-deploy sweep that deletes `*.user-backup-*` whose bytes match the corresponding non-backup sibling (user-authored backups with mismatched bytes survive); and `_purge_nested_core_orphans` moves into `deploy_core` so both install and update paths clean up `osc-X/openspec-X/` nests in the same pass that creates them. Verified on `airk`: pre-install messy state (12 top-level `osc-X`, 12 top-level `openspec-X`, 12 nested `openspec-X` orphans) reduced to a clean tree (12 `osc-X`, 0 `openspec-X`, 0 orphans, 0 backups) by a single `install --with-core --force`; a second install against the clean tree leaves 0 backups; a manual user-edit still produces a preserved backup. Locked by 13 new cases across `TestBackupSkipOnIdenticalContent`, `TestPurgeIdenticalBackups`, `TestNestedOrphanPurgeRunsOnInstall`.

## [1.10.6] - 2026-09-16

### Fixed

- Stop the install pipeline from emitting inline `/opsx-*` leakage inside deployed skill bodies. The rewriter was emitting the upstream slash-command cross-reference prefix unchanged for adapters where the installed invocation token is `/osx-*`, so on those adapters every shipped skill body contained a `/opsx-*` reference that the runtime would silently fail to resolve. The install-time token rewriter now matches the `cross_ref_prefix` declared by each adapter and emits `/osx-*` instead, so installed bodies match the deployed surface.

## [1.10.5] - 2026-09-15

### Changed

- Document per-adapter `ToolAdapter` fields (the five Phase 1 surface fields: `ask_tool`, `install_hint`, `cross_ref_prefix`, `runner_args`, `frontmatter_extras`) and add Cursor to the test matrix so future adapters are exercised against the same surface contract.
- Render extended slash commands (`/osx-*`) as skill mirrors for skills-only adapters — adapters whose `commands_style == "skills-only"` and which resolve skill invocations only — so a single on-disk skill body is the source for both the slash command and the skill picker entry. Cursor and the upcoming Codex / Kimi / Zed adapters inherit the layout.
- Wire purge and validate hooks for skills-only adapters so the install / update / validate pipeline can detect and remove stale per-adapter skill mirrors without breaking the canonical opencode source.
- Expand the `ToolAdapter` surface for skills-only adapters: add `inject_name_in_skill_mirror: bool` (whether to stamp `name:` frontmatter into the mirror) and `cmd_filename_strip_prefix: str | None` (whether the mirror filename drops the `osx-` prefix); registry defaults land on the opencode adapter (`None`) and the claude adapter (`"osx-"`) so the existing opencode flat layout is unchanged while the namespaced claude layout conveys the prefix via its `commands/osx/` subdir.

## [1.10.4] - 2026-09-14

### Changed

- Rename the canonical source tree from `opencode/` to `canonical/` (and the corresponding skills-side `canonical/` mirror) so the on-disk name matches the deploy-time role rather than the opencode adapter. `REGISTRY["opencode"].source_dir` and `REGISTRY["skills"].source_dir` both now point at the new path; the deploy pipeline still treats the orchestrator-side tree as the single canonical pool.
- Align `osx-*` resources to the OpenSpec v1.13.0 naming and dispatch contract: bump resource identifiers from the v1.11.0-era names, refresh the manifest registry to enumerate only resources that satisfy the v1.13.0 validator, and verify that the orchestrator-side and skills-side manifests both pass `validate_commands` against the new surface.

## [1.10.3] - 2026-09-14

### Changed

- Make the bats orchestrate callers non-interactive by default: pre-seed `BATS_TEST_TMPDIR`, pre-install the opencode tree under `SHARED_E2E_DIR`, and short-circuit interactive `read` prompts so the bats E2E suite can run in CI without a TTY or expect failures on `OSX_INTERACTIVE=1` defaults.
- Honour a pre-resolved `state.change_dir` across engine entry points (`engine.run`, `engine.run_agent`, `engine.run_phase`) so callers that resolve the change directory once at orchestration start no longer get it re-resolved (and potentially re-pointed at a different change) by the per-phase entry. The pre-resolved value flows through unchanged.

## [1.10.2] - 2026-09-14

### Added

- Add a build dependency to `test:mechanism:bats`: the task now invokes `mise run build` before the bats run when the mechanism tests depend on a fresh binary, so contributors no longer hit "binary missing" failures on a fresh checkout.

### Changed

- Move the mise build task into a standalone shell script (`.mise/tasks/build`) instead of the inline heredoc it lived as inside `.mise/config.toml`. Same staleness-based rebuild behaviour (the script re-runs PyInstaller when anything under `orchestrator/source`, `orchestrator/resources`, or `skills/resources` changes), now shellcheck-lintable and callable as a normal script.
- Consolidate the cross-cutting rules previously duplicated across root `AGENTS.md`, `orchestrator/resources/AGENTS.md`, and `skills/AGENTS.md` into the root file as the single source of truth. Drop the 3-row "where the rules live" table from the resource-side AGENTS.md files; collapse the v1.13.0 contract enumeration in `orchestrator/source/lib/AGENTS.md:MIN_OPENSPEC_VERSION` into a one-line link to `.opencode/rules/openspec-contract.md`; and rewrite stale tables in `tests/unit/AGENTS.md` (14-row file table replaced by a marker-based reference) and the per-marker AGENTS files. Add new "Workflows" sections across the migrated files documenting the per-adapter deploy and the bats + pytest marker split.
- Consolidate duplicated test bodies via `@pytest.mark.parametrize` across `tests/unit/test_install_flow.py`, `tests/unit/test_resource_contract.py`, and `tests/unit/test_release.py` — the previous per-case duplication made the bodies drift on every heuristic fix and the parametrized matrix is now the single source of truth.

### Removed

- Drop `tests/unit/bats_parallel.py`; run `test:mechanism:bats` sequentially. The custom Python worker runner split bats tests round-robin across processes via `--filter`; mechanism tests now invoke `bats` directly on both files (~145s sequential vs ~24s parallel, but the parallel path raced on the shared `SHARED_E2E_DIR` and was masking real failures).
- Remove the Phase 2A no-op sentinels from the resource contract suite (`TestResourceContract.test_phase2a_*`) — the sentinels never asserted behaviour and only existed to keep the parametrized matrix symmetric; the contract surface is now exercised by the live Phase 5 cases.

## [1.10.1] - 2026-09-13

### Changed

- Cut the bats E2E suite from 215s to 24s and split pytest markers into `unit` / `integration` / `mechanism` / `e2e` so the default `mise run test` task can run only the fast tiers. The bats speedup comes from pre-installing the opencode tree once into `SHARED_E2E_DIR` (instead of per-test reinstalls), short-circuiting the interactive prompts that previously stalled under CI, and dropping redundant `setup_file` / `teardown_file` plumbing. The pytest split lets the default task skip the gated `e2e` tier without `--ignore`.
- Speed up the test suite from ~450s to ~120s overall via parallelization: pytest-xdist fans out the unit tier across cores, bats runs the install suite and mechanism suite in parallel, and the e2e bats remains sequential because it serializes against the binary.

## [1.10.0] - 2026-09-13

### Added

- Add a pre-commit guard against platform hardcodes in `cli.py` / `runner.py` / `lib/osx.py` (`.opencode/scripts/check-platform-hardcodes.sh`): the script greps the per-tool hardcode patterns and fails the commit if any slips into the dispatch / runner / library layers. The patterns cover the original `adapter.commands_style` axis and are extended by 1.10.5 to also cover `adapter.skill_prefix` and `adapter.runner_kind`.
- Add a `GenericPrintRunner` skeleton for headless CLI tools — adapters that drive the CLI via `<tool> --print --dangerously-skip-permissions "<prompt>"` rather than spawning an interactive agent. The skeleton ships with cursor and qwen-code shapes so the registry has a non-`opencode_run` / non-`claude_print` runner to plug into.
- Add the per-tool adapter registry skeleton in `orchestrator/source/tools.py`: `ToolAdapter` dataclass, `REGISTRY` dict, `detect_platform` resolution, and the on-disk mirror generation. The registry becomes the single source of truth for tool-specific behaviour so deploy-time rendering derives every per-adapter layout from the on-disk opencode source.

### Changed

- Anchor the shared-references pool to the canonical opencode path: the deploy was resolving shared references under `<resources>/<tool>/skills/references/`, but only the opencode variant exists on disk — the per-tool directories are generated at deploy time and never carry shared refs. Deploys to claude (and any non-opencode tool) emitted `Shared reference not found` warnings and shipped skills without their declared references. Aligns the code with the single-canonical-pool contract locked by `TestSharedReferencesPackaging` and documented in `orchestrator/resources/AGENTS.md`.
- Reformat Python source with `ruff format`: PEP 8 space-before-colon in slice expressions in `cli.py`, align slice spacing and wrap return dict literal in `lib/osx.py`. No behaviour change.
- Expand the hardcode-check for new dispatch axes (1.10.5 follow-on; landed in this release's pre-commit chain): add three patterns for `adapter.commands_style`, `adapter.skill_prefix`, `adapter.runner_kind`. Patterns are intentionally narrow — they match comparisons to tool names (`'opencode'`, `'claude'`), not to axis values (`'flat'`, `'skills-only'`, `'claude_print'`, `'/'`, etc.); the latter are legitimate dispatch that enumerates supported literals and must NOT trip the guard.
- Single canonical source, per-adapter deploy: opencode is the single on-disk source for every shipped adapter; per-adapter layouts render at deploy time via `ToolAdapter`. The on-disk `claude/` mirrors are gone. `_adapter_tokens` grows to 6 keys (adds `SKILL_PREFIX = adapter.skill_prefix`); new `ToolAdapter` fields `inject_name_in_skill_mirror: bool` and `cmd_filename_strip_prefix: str | None`; `CommandsStyle` literal adds `'skills-only'`; new module helper `strip_agent_line(line) -> str` drops opencode-only `agent:` frontmatter, wired into `REGISTRY['claude']`; `REGISTRY['opencode'].cmd_filename_strip_prefix = None` (flat layout keeps the prefix in the filename); `REGISTRY['claude'].cmd_filename_strip_prefix = 'osx-'` (namespaced layout conveys the prefix via the `commands/osx/` subdir).
- Pin single-tool exit-code preservation: the install / update pipeline now preserves the per-tool exit code instead of letting the aggregated exit mask per-tool failures. A single failing tool no longer reports success because the others passed.
- Accept comma-separated tool targets in `install` and `update` so contributors can drive a multi-tool deploy in one invocation (`openspec-extended install opencode,claude`). Previously the CLI only accepted a single tool per invocation.
- Document the adapter registry and per-adapter rendering across `AGENTS.md`, `orchestrator/source/AGENTS.md`, `orchestrator/source/lib/AGENTS.md`, `orchestrator/resources/AGENTS.md`, and `.opencode/rules/per-adapter-rendering.md`. New adopters see the registry as the entry point.
- Drive `lib/osx` platform helpers from the adapter registry so every helper that read a tool name from the environment now reads from `REGISTRY` (single source of truth). Tests updated accordingly.
- Derive `ai_binary` and install hints from `REGISTRY`: the `install --hint` output is generated from the registry's `install_hint` field, and the runner resolves `ai_binary` from the same field. Hand-edited constants in `cli.py` and `runner.py` are gone.
- Route `detect_runner` through `REGISTRY`, plumb adapter into runners so the runner construction knows its adapter and can apply adapter-specific `runner_args` between the binary name and `--print`. `GenericPrintRunner` benefits directly.
- Wire `cli.py` tool dispatch through the per-tool adapter registry: every `dispatch_to_tool` / `install_for_tool` / `update_for_tool` call now resolves via `REGISTRY[tool_id]` instead of via tool-specific branches.

### Removed

- Remove pre-registry references and completed Phase 2 plan. The adapter registry is the single source of truth; doc and code still carried references to the pre-registry world (a deleted bash `sync-mirrors` script, deleted on-disk `claude/` mirrors, a renamed `mirror-generation.md` rule). Sweep them so the next adapter is a single-file edit: drop `mirror-generation` reference in `AGENTS.md`, rename Claude-mirror rule to `per-adapter-mirror`, drop the "Mirror generation" rule; reframe Claude-mirror wording in `README.md` as adapter-agnostic; rename "Naming, mirroring, versioning" section header in `orchestrator/resources/AGENTS.md`; rename "Mirror" to "Per-adapter behaviour" in `orchestrator/resources/opencode/agents/AGENTS.md`; drop the "bash sync-mirrors script" comments in `cli.py`; drop the `sync-mirrors` reference in `.mise/tasks/version/check`; rephrase Claude-mirror wording to per-adapter rendering language across `tests/*`; delete `PHASE_2_PLAN.md`. Full suite green (174 integration, 84 mechanism, 57 mechanism bats, 29 install bats).
- Remove the unused `target_dir` parameter from `_install_one_tool`: every adapter resolves its own target dir via `ToolAdapter.target_dir`, the parameter was vestigial and shadowed the registry value in one call site.

## [1.9.1] - 2026-09-12

### Changed

- Extract the OpenSpec contract surface to a path-glob rule and retire the `docs/` directory. Add `.opencode/rules/openspec-contract.md` carrying §13 (v1.8.0–v1.13.0 contracts) scoped to `orchestrator/source/**`, `orchestrator/resources/opencode/**`, and `tests/**`. Delete the `docs/` directory entirely (6 files, 1815 lines): `audit`, `cli-comparison`, `concepts`, `orchestrator-state-machine`, `review-modify-integration`, `troubleshooting` — all were historical audit / process material rather than actionable rules. Update the references in the vendored-subtree rule, orchestrator AGENTS.md files, README.md, and test docstrings to point at the new path.
- Consolidate `AGENTS.md` files into a hub-and-domain layout: reduce 28 files to 13 (756 lines down from ~1,500). Add path-glob rules under `.opencode/rules/` for naming, versioning, mirror generation, and vendored subtree concerns; rewrite root `AGENTS.md` as a 76-line mental map (was 240); delete Claude mirror docs (auto-generated, rules live in opencode); delete vendored subtree docs (synced from upstream OpenSpec); drop trivial test-helper docs (`helpers/`, `lib/`, `e2e/helpers/`); fix broken cross-references across `source/lib`, `source/orchestrator`, `tests/e2e`, and `docs/review-modify-integration`.

### Removed

- Delete the `research/` folder of stale upstream mirrors: 10 files, 5,915 lines — 5 OpenSpec doc mirrors (already vendored via `orchestrator/core/source/docs/`), 2 platform docs (the canonical sources at opencode.ai/docs and the Anthropic docs are authoritative), and 2 generic building guides. Zero project references: no `source/`, `tests/`, `AGENTS.md`, or `.opencode/rules/` file imports content from `research/`. Root `AGENTS.md` updated to point at canonical upstream sources instead.

## [1.9.0] - 2026-09-11

### Changed

- Align the orchestrator surface with OpenSpec v1.13.0: bump `MIN_OPENSPEC_VERSION` from `(1, 11, 0)` to `(1, 13, 0)`; adopt the `missingPrerequisites` chain in PHASE1 via `fetch_apply_prerequisites`; adopt `list --specs` and `show --type spec` in PHASE0 via `list_specs` / `show_spec`; relax the `osx-phase6` `retire_capabilities` precondition for v1.13.0 line-wrap and `+-marker` tolerance; refresh shared contract docs and `review-modify-integration.md` across the v1.12.0 and v1.13.0 additions; bump `osx-phase1` (0.3.6→0.3.7), `osx-phase6` (0.3.9→0.4.0), `osx-review-artifacts` (0.3.3→0.3.4); add `test_apply_prerequisites.py` and `test_spec_inventory.py` for the new helpers.
- Migrate the OpenSpec subtree to `orchestrator/core/source` (was `openspec-core/source`): the previous path was renamed in v1.8.0 but the subtree gitlink still pointed at the old location, so `subtree pull --squash` would have re-created the old path. Single squash-commit carries the new `git-subtree-dir` / `git-subtree-split` annotations; `sync-core` learns to handle the post-relocate state (see "Migrate sync-core task" below).
- Sync the OpenSpec subtree at `orchestrator/core/source` from `https://github.com/Fission-AI/OpenSpec@v1.13.0`. Squashed `a0ddb60d..9d4e5974`.
- Standardize tmpdir cleanup in CI and tests: `release.yml` swaps the manual `rm -rf "$STAGE_DIR"` for a `trap ... EXIT` registered right after `mktemp`, so the staging dir is also cleaned up if the tar / sha256sum steps fail (previously leaked through `set -euo pipefail`); `mechanism.bats` replaces per-test `mktemp -d` + `cd` + `rm -rf` with bats' built-in `$BATS_TEST_TMPDIR` (auto-cleaned per test, survives failed assertions).
- Normalize the remaining `openspec-core` references across docs and tests: seven files still pointed at the old path or the upstream name as if it were a local tree. Rename to `orchestrator/core` (where the subtree now lives) or rephrase to "upstream OpenSpec project" where the original referred to filing issues against the upstream repo: `docs/audit.md`, `docs/review-modify-integration.md`, `orchestrator/core/AGENTS.md`, `orchestrator/resources/AGENTS.md`, the `osx-review-artifacts` SKILL.md on both opencode and claude, and `tests/contract/test_upstream_envelopes.py`.
- Migrate the `sync-core` task to the `orchestrator/core` subtree prefix. The task still pointed at the old `openspec-core/source` prefix after the v1.8.0 relocation, so `subtree pull --squash` would have either re-created the old path or refused outright. Update `CORE_DIR` and `SUBTREE_PREFIX` to `orchestrator/core/source` and replace the single `pull_subtree` with a three-state `sync_subtree`: new prefix already registered → steady-state `subtree pull --squash`; old prefix registered but new prefix only exists on disk (the post-relocate state) → seed a synthetic squash commit pointing at the last-synced upstream SHA, then `subtree merge --squash`; neither registered → fresh `subtree add --squash`. Also explicit-rm the temp dir in `generate_ai_files` before resetting the EXIT trap.

## [1.8.0] - 2026-09-11

### Added

- Add `osx` instructions archive, schema fork-diff, and `validate --archived` to the CLI surface. Instructions route through a new `fetch_instructions()` library for structured errors; require `--change`; drop the `--json` no-op flag. The schema fork-diff forks a schema and asserts YAML fidelity against the source (v1.9.0+ Document API guarantee); exit 1 on drift. `validate --archived` brings `--archived` scope to parity with the other validate actions; optional `--change` scopes to one archive. 42 new pytest cases across 6 test files and 2 new mechanism bats cover the surface; `source/lib/AGENTS.md` grows from 10 to 11 domains (added schema row).
- Add CLI passthroughs and subcommand mirrors for upstream v1.5+. `view`, `archive`, `context`, `doctor`: 4 new top-level passthroughs to upstream. `new change`: create a change directory (v1.7.0+). `store <sub>`: full upstream mirror (`setup`, `register`, `unregister`, `remove`, `list`, `doctor`; v1.5.0+) with the `osx store` JSON facade preserved. `config <sub>`: full upstream mirror (`path`, `list`, `get`, `set`, `unset`, `reset`, `edit`, `profile`). 33 new pytest cases + 17 new bats cases wired into `test:mechanism:bats`; docs (README passthrough table, `cli-comparison.md` matrix, "Mirrored upstream groups" subsection) reflect the new surface. Closes the CLI surface gap with upstream OpenSpec v1.5.0+ without duplicating or deprecating the existing programmatic `osx store`.
- Add env-var propagation, archived sweep, and operation guidance in CLI. New flags `--language` and `--strict-archived` on `install` / `update` / `update-core`; `OPENSPEC_LANGUAGE` and `OPENSPEC_VALIDATE_ARCHIVED_STRICT` env-var fallbacks (empty string treated as unset). `OPENSPEC_CONCURRENCY` propagates to `openspec-extended validate --all` and `osx validate all`; invalid values silently fall back to 6. `_post_install_archived_sweep()` runs `openspec validate --archived` after `install` / `update-core`; non-fatal by default, enforced via `--strict-archived` or `OPENSPEC_VALIDATE_ARCHIVED_STRICT=1`. `_resolve_concurrency()` central helper for validate precedence (explicit arg > env > default 6). `fetch_operation_guidance()` reads `operations.{apply|archive}.guidance` from `openspec/config.yaml` for PHASE1/PHASE6 prompts (A.4). Tests cover install flow (language, env-var fallback), CLI passthrough (concurrency), validation translator (concurrency), validate subcommands, core-version gate, mechanism bats.

### Changed

- Realign the release version bump with the `source/` relocation: the release task and `bump.sh` still targeted `source/__init__.py` after commit `4370e76` relocated the CLI engine into `orchestrator/source/`. The old path no longer exists, so `mise run release` silently failed to bump `__version__`. Point both scripts at the new path and refresh matching status output.
- Split manifests per side and align documentation. Each side's source manifest now declares only its own resources (orchestrator keeps workflow scope; skills keeps gap-filling scope); Claude mirrors regenerated. Per-side target manifests: orchestrator deploy writes `<target>/manifest.toml` (legacy position); skills deploy writes `<target>/skills-manifest.toml`. Consumers (`_load_manifest`, `validate_skills`, `validate_commands`, `validate_deployment`, `_expected_extension_names`) read both files for cross-checks. `osx-workflow` skill scoped to runtime audience (fixed misnumbered §3 → §11, dropped orphan `osx-concepts` reference); `docs/concepts.md` scoped to maintainer audience (explicit "Audience" heading, refocused on this repo's layout and framework reference). README medium trim (348 → 276 lines). **Breaking change**: target-side manifest is now two files (`<target>/manifest.toml` + `<target>/skills-manifest.toml`) instead of one merged file; external tooling that reads the on-disk manifest must read both.
- Rewrite the v1.6 review / modify tests for the post-split resource tree. Phase 7 rewrite of the v1.6 review / modify contract suite; source of truth is the four split manifests under `orchestrator/resources/` and `skills/resources/`. Coverage: manifest parity (resource set + per-resource versions agree pairwise across the four manifests; strict semver; no accidental downgrades); dual-emit discipline on Claude (every opencode command legacy + skill mirror; `name` frontmatter injection; `agent:` leak prevention); frontmatter invariants on the live utilities (`osx-commit`, `osx-review-artifacts`, `osx-review-test-compliance`, `osx-workflow`); schema-agnostic contract wording pinned on `osx-review-artifacts` only (the live consumer of §4.2); no hardcoded artifact names in the review skill; model-invocation trigger word pinned for every canonical skill; §13 v1.8.0–v1.11.0 contract surface mirrored (`isPlanningComplete`, `retire_capabilities`, `operationGuidance`, `show --diff`, `validate --archived`); shared references packaging against the single canonical pool at `orchestrator/resources/opencode/skills/references/`.
- Consolidate `osx-commit` format examples into `SKILL.md`. Drop the four `references/examples/*.md` files and inline compact per-style examples (Conventional / Angular / Gitmoji / Classic) into `SKILL.md`. `references/standards.md` and `references/detection.md` remain as full references; `scripts/detect-commit-style` stays (still invoked from `SKILL.md`). Bump `osx-commit` to 0.2.1 across all four manifests; `sync-mirrors` carries the new version + slimmed body to the Claude side.
- Rename `openspec-core/` paths to `orchestrator/core/` across docs. Rewrite historical references to the Phase-4-rename source tree across the three docs that quoted the pre-split layout. The bare project name `openspec-core` on line 115 of `review-modify-integration.md` is left as-is (it's the upstream project name, not a path).
- Update the test suite for the `orchestrator/skills` dual-tree layout. The tests previously assumed a single `resources/` tree; they now point at `orchestrator/resources/` (for the workflow resources) and `skills/resources/` (for the gap-filling utilities), and reference the new skill names: `osx-commit` replaces `osx-concepts`, `osx-review` replaces `osx-modify`, and `osx-review-artifacts` / `osx-review-test-compliance` keep their identities. `tests/unit/test_skill_taxonomy` and `test_skill_autonomous_gating` reflect the 4-skill default install (was 6); `tests/integration/test_install_flow` covers `osx-commit` (skills side) and `osx-review` as the hyphen-form slash command; `tests/unit/test_required_skills`, `test_resource_contract`, and `test_sync_mirrors` align with the dual tree; `tests/unit/test_token_substitution` and `test_workflow_skill_contract` cover the new path substitutions; the e2e mechanism suite (bats + pytest) walks the new layout.
- Migrate skills-side utilities, retire deprecated resources, add docs. The skills side carries gap-filling utilities (`osx-commit`, `osx-review-artifacts`, `osx-review-test-compliance`) and the review / test commands that don't fit the autonomous workflow. Multi- and single-artifact edits now route through upstream `/opsx:update`, so `osx-modify` and `osx-modify-artifacts` are retired. The `osx-concepts` skill is replaced by `docs/concepts.md` and the `.opencode/skills/audit` skill is retired in `docs/audit.md`. Add `skills/resources/{opencode,claude}/{skills,commands}/` for the three gap-filling skills and `osx-{review,verify-tests}` commands; refresh `REQUIRED_SKILLS` in `orchestrator/source/lib/osx.py` (drop `osx-concepts` and `osx-modify-artifacts`; add `osx-review-artifacts`, `osx-review-test-compliance`, `osx-commit`); add `docs/concepts.md` and `docs/audit.md`; delete the deprecated `osx-{concepts,modify-artifacts}` resources and their Claude mirrors, the `osx-modify.md` command + Claude mirror, and the audit skill from the user's local `.opencode/` config.
- Migrate orchestrator-side resources into the `orchestrator/resources/` tree. The orchestrator side carries the 7-phase autonomous workflow plus the two orchestrator-scoped slash commands (`osx-changelog`, `osx-maintain-docs`). Each opencode resource is mirrored to the Claude tree by `sync-mirrors`. Move agents (`osx-analyzer`, `-builder`, `-maintainer`, `-reviewer`), commands `osx-phase{0..6}` + `osx-changelog` + `osx-maintain-docs`, skill `osx-workflow` + shared references (`blocker-semantics`, `doc-structures`, `phase-protocol-common`, `update-{examples,rules}`, etc.), and `manifest.toml` to `orchestrator/resources/{opencode,claude}/`. Refresh resource-tree `AGENTS.md` docs to match.
- Update the `sync-mirrors` task for the dual-tree architecture. The mirror sync now writes Claude artifacts for both resource trees (`orchestrator/resources/` and `skills/resources/`) instead of a single `resources/` tree. Paths and references are parameterized so each tree mirrors independently without leaking paths between them.
- Relocate the CLI engine and OpenSpec core into the `orchestrator/` tree. Move `source/` to `orchestrator/source/` (Python CLI engine) and `openspec-core/` to `orchestrator/core/` (synced from upstream). Update `.mise/config.toml` lint / format / typecheck paths, the `openspec.spec` PyInstaller package paths, `pyproject.toml` hatch packages path, and `.gitignore` (replace `openspec-core/` entry with `orchestrator/core/.claude/` and `orchestrator/core/.opencode/` generated-build ignores). Drop the `.agents/skills/writing-great-skills` symlink (external ref); refresh `AGENTS.md` and `README.md` project-tree and core-path references.
- Bring the contract suite and bats tests up to the v1.11.0 surface. Bump version floor from 1.7.0 to 1.11.0 with `OPENSPEC_EXTENDED_MIN_CORE_VERSION_OVERRIDE` opt-out for local dev; consolidate three duplicate `_core_version` static methods into one module-level helper; add `TestStatusAllEnvelope` for the `status --all --json` multi-change sweep (v1.11.0+); add bats tests pinning `status --store` and `validate --archived` passthrough help + execution.
- Document the post-v1.7.0 contracts in the review-modify integration plan. The orchestrator now consumes five v1.8.0–v1.11.0 contracts (`isPlanningComplete`, `retire_capabilities`, `operationGuidance`, `show --diff`, `validate --archived`) that the v1.6.0 / v1.7.0-era plan didn't document. `docs/review-modify-integration.md`: new §13 catalogues each contract with consumer, operational note, and `file:line` anchor; header bumped to v1.11.0; §4.3 lists the new JSON fields and the `show --diff` envelope; §5.3 line refs rewritten with verified anchors; §6 adds Phase H for Section A; §9 reflects current manifest versions; §12 adds three open questions; glossary extended with the new terms. `AGENTS.md`, `source/lib/AGENTS.md`, `source/orchestrator/AGENTS.md`: one-line cross-reference pointers to the new §13.
- Consolidate `osx-changelog` and `osx-maintain-docs` slash commands. `lib/osx.py`: drop `osx-workflow` from `REQUIRED_SKILLS` (the `--with-autonomous` gate was added in `fc8b6ba` but the preflight still expected the skill on disk, false-failing `validate_skills` on every default install); drop `osx-maintain-ai-docs` for the same reason (now a slash command, not a skill). `resources`: merge skill bodies into slash command files (`commands/osx-changelog.md`, `commands/osx-maintain-docs.md`); delete `skills/osx-generate-changelog/` and `skills/osx-maintain-ai-docs/` on both opencode and claude mirrors; move 6 per-skill references into the shared `skills/references/` pool. `manifest.toml`: drop the two skill entries; bump `osx-changelog` to 0.2.0 and `osx-maintain-docs` to 0.3.0. README, AGENTS.md, `osx-concepts §2.5`: update taxonomy counts (8 → 6 skills) and remove the slash-command vs skill-body naming-mismatch callouts. 12-case `test_skill_taxonomy.py` locks in the new inventory; 6 existing test modules updated for the rename. Merged slash command bodies retain `references/<file>.md` links to the shared pool; Claude's dual-emit deploy already packages those refs alongside the modern skill form.
- Track the external `writing-great-skills` symlink under `.agents/`. Symlink points at the upstream `mattpocock-skills` checkout outside the repo so the local `.agents/skills/` mirror follows it without copying the upstream content into the repo.
- Adopt the v1.11.0 contract surface across skills and docs. `osx-phase0/phase6`: retirement short-circuit (PHASE0 → PHASE6 when `retire_capabilities: true`) and step-0 precondition check. `osx-phase1/phase6`: project operation guidance as authoritative context for PHASE1/PHASE6 spawns. `osx-phase2`: embed requirement-level diff in `verification-report.md` (Delta inventory + Requirement diff + Verification warnings). `osx-workflow`: document the new PHASE0 short-circuit, operation guidance row in the tool-layer table, retire-capabilities section, and verification-report diff appendix. `schema-agnostic-contract.md`: `retire_capabilities` + `isPlanningComplete` contract notes refreshed. `cli-reference.md`: cover `operations.{apply|archive}.guidance` and the new `--language`, `OPENSPEC_LANGUAGE`, `--concurrency`, `OPENSPEC_CONCURRENCY` propagation. `troubleshooting.md`: retirement + post-install-archived-sweep + verification-report sections. `orchestrator-state-machine.md`: planning-completeness gate and retirement footnote. `cli-comparison.md`: lists the new flags and env vars. README env-vars table. `test_phase_workflow.py` gains `TestPhase2DiffLogField` covering the `cli_diff` envelope round-trip.
- Wire `retire_capabilities` metadata and the planning gate into the orchestrator. `read_change_metadata()` parses `.openspec.yaml` (schema, `skip_specs`, `retire_capabilities`); tolerant of missing / malformed files. `_fetch_planning_status()` wraps `openspec status --change <id> --json` for the planning-complete gate. `validate_change_dir()` consults core's `isPlanningComplete` first; local file-existence check retained as fallback (CI escape hatch: `OPENSPEC_EXTENDED_NO_PLANNING_CORE=1`). `engine.py`: `state.retire_capabilities` field; `read_change_metadata` called from `validate_change_dir` and `validate_archive`; PHASE0 short-circuit feeds off the marker. AGENTS.md documents the new short-circuit in `source/orchestrator`. `test_upstream_envelopes.py` (`TestStatusPlanning`), `test_schema_resolution.py` (`TestSchemaAndMetadataAgreement`) cover the contract.
- Reconcile the extended side with OpenSpec core v1.11.0. The v1.11.0 subtree sync bumped `openspec-core` without updating the extended side; all CLI flags and JSON envelopes the wrapper relies on remain valid in v1.11.0, so this is a coordinated doc refresh, floor raise, and feature adoption — not a bug fix. `MIN_OPENSPEC_VERSION`: `(1, 7, 0)` → `(1, 11, 0)`; orchestrator refuses cores below v1.11.0. `list_changes()`: switch to `openspec status --all`. `show` / `validate` / `init`: add passthrough `--diff`, `--archived`, `--language`. Docs, skill references, AGENTS.md: sweep v1.7.0 citations; document v1.8.0+ fields (`isPlanningComplete`, `retire_capabilities`). Tests: floor fixtures retargeted at v1.10.5; comments refreshed. **Breaking change**: orchestrator pre-flight now exits 2 for cores below v1.11.0. `install`, `update`, and non-orchestrate subcommands are unaffected.
- Sync the OpenSpec subtree at `openspec-core/source` from `https://github.com/Fission-AI/OpenSpec@v1.11.0`. Squashed `4e16790d..a0ddb60d`.

### Removed

- Drop dangling `examples/` refs from `osx-commit` standards (cleanup only).

## [1.7.3] - 2026-08-03

### Changed

- Substitute resource tokens at deploy time. `{{TOKEN}}` placeholders in shipped resources were only rendered by the bash `sync-mirrors` script; that rewrote the Claude mirror but never reached the opencode deploy path, so users got literal `"{{CMD_PREFIX}}"` and `"{{PLATFORM_DIR}}"` strings in their `.opencode/` tree. The Claude deploy also produced broken skill paths (`osx:modify-artifacts`) where the real directory is `osx-modify-artifacts`. Add `PLATFORM_TOKENS` table + `_substitute_tokens` helper in `source/cli.py`; applied by `deploy_skills` / `deploy_commands` / `deploy_agents` so the deploy rewrites every `{{TOKEN}}` per platform. `.mise/tasks/sync-mirrors` becomes a pure mirror (no token substitution); rendering is the Python deploy's job. `resources/opencode/commands/osx-{modify,review,verify-tests}.md`: hardcode `osx-` for skill directory paths (slash-command form keeps `{{CMD_PREFIX}}` since the prefix differs per platform). Regression tests cover "no leftover `{{TOKEN}}` placeholders after install" and "skill-path references resolve to real directories on both platforms".
- Dual-emit slash commands on Claude as skills. Claude Code merges custom commands into skills per v2.1.x docs; mirror upstream OpenSpec v1.7.0's strategy: every `osx-*` command now produces both a legacy `.claude/commands/<name>.md` and a modern `.claude/skills/<name>/SKILL.md` on the Claude side. `.mise/tasks/sync-mirrors` emits a skill mirror per opencode command; `deploy_commands` dual-emits on Claude with per-skill references copy; `validate_commands` / `validate_deployment` accept either form; `REQUIRED_CORE_SKILLS` tracks all 12 upstream workflows (was 4); 12 new `resources/claude/skills/osx-*/SKILL.md` mirrors; tests + AGENTS.md cover the dual-emit contract.

## [1.7.2] - 2026-08-03

### Changed

- Install all 12 canonical core workflows via `--with-core`. `openspec init` defaults to `profile=core` (6 workflows: `propose`, `explore`, `apply`, `update`, `sync`, `archive`) so installs silently shipped a half set: `osc-new`, `osc-continue`, `osc-ff`, `osc-bulk-archive`, `osc-verify`, and `osc-onboard` never landed. `deploy_core`: seed `~/.config/openspec/config.json` with `profile=custom` + `delivery=both` + the 12-workflow list before invoking `openspec init --tools <t> --profile custom --force`; snapshot the prior global config into `.openspec-extended-baseline.json` when one exists (even without a prior core deployment), so `restore-core` can revert the overwrite; `_core_keep_set`: also discover OpenCode's flat `osc-*.md` commands (was only seeing Claude's nested `osc/<id>.md`); without this, `update --with-core --force` deleted the 12 commands it had just installed. Strict 12-set assertions across install / update / opencode / claude; global-config seeding / snapshot / restore round-trip; parametrized rename coverage for all 12 canonical IDs; README lists the 12 workflow names and documents the global-config write + snapshot behavior.

## [1.7.1] - 2026-07-31

### Changed

- Package shared references into each skill at deploy. Manifest gains `references = [...]` per skill declaring shared pool files; the deploy copies each declared file into the skill's own `references/` folder. Tests cover packaging, link / manifest parity, and pool orphan detection.

## [1.7.0] - 2026-07-31

### Changed

- Consolidate the `osx` command workflow guidance (per-command bodies share one canonical workflow rather than each command re-stating it).
- Consolidate shared conventions across `osx` skills. Skills extract store selection, autonomous-mode gating, schema-agnostic contract, and scoring rubric into `resources/{opencode,claude}/skills/references/`; manifests bump patch version for each affected skill; tests assert shared-reference pointer and allow single top-level autonomous-mode declaration.
- Clarify skill triggers and disable automatic changelog invocation. Skill descriptions move to single-line triggers (lowercase, no leading verb) so the picker reliably matches user input; the changelog generator no longer auto-invokes on commit.
- Generate the Claude mirror from the OpenCode source via token substitution. Add `mise run sync:mirrors` task that mirrors `resources/opencode/` to `resources/claude/` via `{{TOKEN}}` substitution (`ASK_TOOL`, `DOCS_FILE`, `CMD_PREFIX`, `TOOL_NAME`, `PLATFORM_DIR`); new pre-commit hook (`sync-mirrors-check`) and `mise run verify` step fail the commit when the mirror drifts from source. OpenCode is now the canonical source; Claude files carry an `# AUTO-GENERATED` header and must not be edited by hand. Extract 8 cross-cutting references under `skills/references/` (`blocker-semantics`, `osx-decision-logging`, `osx-mode-conventions`, `phase-protocol-common`, `schema-agnostic-contract`, `scoring-rubric`, `shell-argument-safety`, `store-selection`); skills now point at them via one-line markers instead of duplicating content. Scope `version:check` to opencode (the canonical manifest); bump eight skill / command versions to reflect the refactored content. Make tests token-aware so the autonomous-gating and resource-contract checks pass against the new mirrored format.
- Reconcile stale `osx` / `osc` resources during update. Add `purge_managed_resources` helper scoped to `osx-*` / `osc-*` skills, commands, and agents; honors OpenCode flat vs. Claude nested layouts and unlinks symlinks without following them. `update` purges `osx-*` leftovers before redeploy and `osc-*` leftovers after a successful `--with-core` deploy, against the source manifest and the freshly generated core tree respectively. `install` and `update-core` remain non-destructive; only `update` reconciles the deployed tree. Unit and integration coverage for both platforms, autonomous toggle, custom-resource preservation, and core / non-core split.

## [1.6.0] - 2026-07-31

### Changed

- Bump `pytest`, `pyinstaller`, and `annotated-doc` in `uv.lock` to the latest compatible versions, picked up by the next pre-commit `uv run pytest` round.
- Gate autonomous resources behind the `--with-autonomous` flag. The default install now ships only the 7 utility skills and 5 utility commands; the 4 agents, 7 phase commands, and `osx-workflow` skill (12 resources total) deploy only when `--with-autonomous` is passed. CLI gains `--with-autonomous` / `--no-with-autonomous` on `install` and `update`; autonomous resources are filtered from the deployed manifest; the orchestrator markers are skipped from `.gitignore` under utility-only install; `lib/osx.py` gains an `AUTONOMOUS_RESOURCE_NAMES` frozenset (12 entries); `validate_skills` / `validate_commands` surface the install hint in error messages. Unit, integration, and mechanism coverage plus README and `cli-comparison` documentation land.

## [1.5.0] - 2026-07-30

### Changed

- Sync resources, library, and CLI with OpenSpec core v1.7.0. Raise the core floor to `MIN_OPENSPEC_VERSION = (1, 7, 0)` (audit #11 resolved). Skills adopt v1.7.0 `requires` per artifact and `instructions archive`; v1.7.0 `defaultStore` fallback and `skip_specs` marker; and v1.7.0 `operations.{apply,archive}.guidance` config. CLI suppresses the v1.7.0 upgrade prompt via `OPENSPEC_NO_UPDATE_CHECK=1`; README requires v1.7.0+ (was v1.6.0+ recommended); cleanups cover ruff `EXE001` noqa, `check=False`, and exception narrowing.
- Reformat type hints and import order across the library and CLI (separate from the v1.7.0 sync).
- Sync the OpenSpec subtree at `openspec-core/source` from `https://github.com/Fission-AI/OpenSpec@v1.7.0`. Squashed `e1b51d11..4e16790d`.

## [1.4.0] - 2026-07-30

### Changed

- Refresh workflow docs and bump versions to 1.3.0 / 0.2.2. Fix `_detect_existing_core_deployment` to key on `payload["items"]` (`openspec list --json` returns items at the top level, so iterating `skills/specs/changes` at the top level was a no-op). Bump project version (1.2.1 → 1.3.0), `install.sh` SCRIPT_VERSION (0.2.1 → 0.2.2), and the OpenSpec contract reference (1.5.0 → 1.6.0) in CLI / install docs. Refresh per-resource manifest versions (`osx-concepts` 0.9.3 → 0.9.4, `osx-workflow` 0.3.3 → 0.3.4, `osx-phase6` 0.3.7 → 0.3.8). Update autonomous-workflow references to show PHASE2 and PHASE5 dispatching to `osx-reviewer` (the analyzer / maintainer split is now reflected in the table). Clarify in `osx-phase6` command docs that the orchestrator cleans transients from the archive directory, not the pre-archive path; the phase must not pre-empt the cleanup. Update README commands count (11 → 12) and document `update-core` taking an optional path argument.
- Re-resolve change path for cleanup and split preflight checks. `cleanup()` re-resolves the change directory via `find_change_dir` with a direct archive-walk fallback, so transients (`state.json`, `complete.json`, the per-change auto-log) are removed from `openspec/changes/archive/YYYY-MM-DD-<change>/` after PHASE6 rather than from the stale pre-archive path (C4). `cleanup()` logs a warning when a transient still exists after cleanup and surfaces the underlying `OSError` when removal fails. `validate_archive` asserts `decision-log.json`, `iterations.json`, and a git commit exist in the archive directory before declaring it valid (previously any matching archive directory passed). Preflight split: skills, commands, git, change_dir, and schema checks always run; binary probes (`jq`, `openspec`, AI CLI), the OpenSpec version floor, and baseline recording only run on a fresh start (skipped with `--from-phase`). `detect_platform` now reads `_project_root(state)` so the preflight probes inspect the project root, not CWD.
- Halt on phase-written blockers and cross-check the deployed manifest. Engine exposes `check_blocker()` that reads `complete.json`'s `with_blocker` flag and returns the `blocker_reason`; called from both the main loop and `run_phase` so a phase that writes BLOCKED without `phase_complete` is not re-invoked in the next iteration (M22). The top-level blocker check now uses `check_blocker` instead of inlining the JSON parsing. `validate_skills` and `validate_commands` load the deployed `manifest.toml` and assert every required skill / command is declared in `[resources.skills]` / `[resources.commands]`, plus every `PHASE_AGENTS` entry exists as an agent file (opencode) (M23). Missing manifest entries are caught at preflight rather than surfacing later as a half-deployed install.
- Wire store / schema env propagation and harden subprocess teardown. `RunRequest` gains `store` / `schema_name` fields; the runner injects them as `OSX_STORE` / `OSX_SCHEMA` env vars so AI subprocesses inherit the active store and schema without explicit flags (M18). Engine `run_agent` forwards `state.store` / `state.schema_name` into the subprocess request. Engine clears `state.child_pid` after `run_agent` returns, so a stale PID cannot be signalled by a later SIGINT (M21b). Runner uses process groups on POSIX (`setsid` + `killpg`) for timeout teardown, escalating SIGTERM to SIGKILL after a grace period (M21a). `_terminate_child` / `_terminate_subprocess_tree` send `CTRL_BREAK_EVENT` on Windows when available, falling back to SIGTERM (M21c). `osx` CLI callback consults `OSX_STORE` env var as a fallback when `--store` is not passed.
- Halt orchestration for pending phase routes. Persist routed commands from non-clean phase reviews; stop PHASE0 cleanly until users complete the routed commands; add CLI coverage and synchronize phase0 resource versions.
- Align `osx` state transition docs with the named-option CLI. Phase2 commands + `osx-workflow` `skills/references`: switch bash examples to `--target` / `--reason` / `--details` (the form the CLI accepts); bump `osx-workflow` (0.3.2 → 0.3.3) and `osx-phase2` (0.3.1 → 0.3.2). Add integration tests that extract phase2 transition bash blocks and execute them against the CLI so docs stay runnable.
- Decouple the installer test from the fixture release version so `install.bats` doesn't break every time the fixture bumps.
- Restructure the audit skill to separate process from project state. `SKILL.md`: process-only; only mentions the two targets by name. `references/targets.toml`: declares OpenSpec Core and OpenSpec Extended roots, head paths, and allowed reads. `references/templates`: `diff-patterns`, `quality-categories`, `severity-rubric`, `output-template`, `rubric-examples` — versioned with the skill, drift deliberately. `references/{local,upstream}-surface.md`: deleted; surface data was project-specific and is now generated per audit. `.opencode/commands/audit.md`: trimmed; defers process guardrails to `SKILL.md`, keeps only the project-specific no-mutation guardrail. `.gitignore`: `.audit/` becomes a single rule covering runtime artifacts (captures, maps, reports); templates and config move into the skill.

### Fixed

- Fix Claude command validation for unprefixed filenames: match Claude validation to the deployed phase command filenames; preserve prefixed command validation for OpenCode.

## [1.3.0] - 2026-07-23

### Added

- Add the `osx-reviewer` agent, autonomous-mode gates, and full slash commands. The new `osx-reviewer` agent is write-capable (`edit: allow`); PHASE2 / PHASE5 dispatch to it. PHASE0 stays read-only on `osx-analyzer`. PHASE1 / PHASE3 / PHASE4 / PHASE6 keep their existing assignments. Update `osx-workflow` TL;DR + §2 phase tables and `osx-concepts` agents table (both platforms); contract test pins the workflow mapping to `engine.PHASE_AGENTS`. Gate `AskUserQuestion` prompts in `osx-maintain-ai-docs` and `osx-modify-artifacts` behind `OSX_AUTONOMOUS=1` so the orchestrator-driven path skips interactive confirmation with a documented default. Replace abbreviated slash forms (`/osc-archive`, `/osc-apply`, `/osc-verify`, `/opsx:verify`, `/osc-sync`) with full names (`/osc-archive-change`, `/osc-apply-change`, `/osc-verify-change`, `/osc-verify`, `/osc-sync-specs`); `TestFullCommandNames` forbids the bare-verb abbreviations (with one allowed exception for `/osc-verify` in `osx-review-test-compliance`).
- Add `osx-commit` to `REQUIRED_SKILLS` and a `contract` pytest marker. Every phase command (PHASE1–PHASE6) invokes `osx-commit` at MANDATORY END to land its iteration, so the preflight gate must require it. Also add a `contract` pytest marker for opt-in live tests against an installed `openspec` CLI (auto-skipped when the binary is missing) and expand the resource-parity tests to cover the new skills and commands: `source/lib/osx.py` adds `osx-commit` to `REQUIRED_SKILLS` and documents that `osx-generate-changelog` is intentionally excluded (it has its own `/osx-changelog` dispatch); `source/lib/AGENTS.md` bumps the `REQUIRED_SKILLS` count from 5 to 7 and records the exclusion rationale; `pyproject.toml` registers `pytest.mark.contract`; bumps `osx-concepts` (0.9.0 → 0.9.1) and `osx-workflow` (0.3.0 → 0.3.1) in both manifests; new `tests/contract/__init__.py` + `test_upstream_envelopes.py` live envelope checks for status, templates, store, validate, version; `tests/unit/test_required_skills.py` contract for `REQUIRED_SKILLS` (existence, manifest entries, platform parity); parametrized `tests/unit/test_resource_contract.py` plus new skill and command parity entries; preflight fixture integration covers `osx-commit`.
- Add PID callback and process-group termination for live AI subprocesses. The orchestrator captured `child_pid` after `process.wait()` returned, which is too late for SIGINT to cancel a running AI session. The runner now fires an `on_pid` callback before `wait()` so `handle_interrupt` and `cleanup` can signal the child, and spawns the child in its own session (`os.setsid` on POSIX; `CREATE_NEW_PROCESS_GROUP` on Windows) so the whole process group dies together. `source/orchestrator/runner.py`: add `OnPidCallback` type and `RunRequest` field; fire `on_pid` before `process.wait`; use `os.setsid` / `CREATE_NEW_PROCESS_GROUP` at `Popen`. `source/orchestrator/engine.py`: extract `_terminate_child` helper that signals the child's process group; wire `_capture_pid` via `RunRequest` in `run_agent` with a `None` fallback for the post-hoc case. `tests/unit/test_runner_pid_callback.py` locks in callback timing, child session isolation, and runner wiring.
- Add the `osx-reviewer` agent and reassign PHASE2 / PHASE5 dispatch. The read-only `osx-analyzer` can no longer cover phases that write reports: PHASE2 (verify) writes `verification-report.md` and PHASE5 (self-reflect) writes `reflections.md` and runs `git commit`; `osx-analyzer` denies edits, so the orchestrator's edits were silently failing under the v1.6+ permission model. Add `resources/opencode/agents/osx-reviewer.md` (write-capable, low temperature) for verification and self-reflection; switch all four orchestrator-dispatched agents to `mode: subagent` so they stay hidden from the user picker; point `osx-phase2.md` and `osx-phase5.md` at `osx-reviewer` (PHASE0 stays on `osx-analyzer` for its read-only audit); bump `osx-analyzer`, `osx-builder`, `osx-maintainer`, `osx-phase2`, `osx-phase5` and add `osx-reviewer` in both manifests; `tests/unit/test_phase_agent_contract.py` asserts the wiring.
- Add the `audit` command and skill for OpenSpec integration audits. New project-local dev tool under `.opencode/` (not deployable, no manifest): `/audit` slash command delegates to `.opencode/skills/audit/` skill; the skill runs a 4-phase workflow (capture → parallel surface map (upstream ∥ local) → diff + quality eval → synthesize report); 3 reference files (`upstream-surface`, `local-surface`, `severity-rubric`); pure file-system analysis (does not invoke `openspec` CLI).

### Changed

- Align docs and framework versions with the 1.2.1 release. README / install.sh bump to 1.2.1; OpenSpec requirement v1.5.0+ → v1.6.0+; skill / agent counts (8 skills + 4 agents); skills and agents tables; project layout counts. CLI reference (`osx-concepts/references`, both platforms): re-verify JSON shapes against OpenSpec 1.6.0; document `--id` for `store register`; update `complete set BLOCKED` to "rejected without a reason". Framework component bumps in `resources/{opencode,claude}/manifest.toml`: `osx-concepts` 0.9.1 → 0.9.3, `osx-workflow` 0.3.1 → 0.3.2, `osx-modify-artifacts` 0.3.0 → 0.3.1, `osx-generate-changelog` / `osx-review-test-compliance` / `osx-maintain-ai-docs` 0.2.x → 0.2.3, `osx-maintain-docs` 0.2.1 → 0.2.2. Resource contract test expects the bumped versions. Project `__version__` and `[project]` version are intentionally not touched here (owned by `mise run release`, already at 1.2.1).
- Wire `OSX_AUTONOMOUS=1` and tighten validation contracts. Set `OSX_AUTONOMOUS=1` in `cli.orchestrate` and forward through `engine.run_agent` → `RunRequest.env`. PID callback failures are logged to stderr instead of silently swallowed. `complete_set("BLOCKED")` without `blocker_reason` raises `OSXError(invalid_blocker)` (incl. empty string). `_translate_validate_payload` returns `valid=None` + `unverifiable_envelope` warning when `summary.totals.failed` is missing. `resolve_schema` logs YAML / IO errors to stderr instead of swallowing them; narrows exception types. `update_gitignore` adds `!openspec/changes/archive/**/...` re-includes after each active-change ignore.
- Centralize version on `__version__` and add an atomic `state_io` module. Drop `SCRIPT_VERSION`; `engine.get_version` reads `source.__version__` directly. `__version__` stays the single source of truth, and `mise run release` no longer bumps a duplicate target. Add `source.lib.state_io` (atomic tempfile + `os.replace`) shared by the engine and the osx library. Resume phase iteration count via `get_next_phase_iteration` so a restarted orchestrator continues at the next `phase_iterations[phase]` slot instead of restarting at 1. Preserve `started_at` across writes so it reflects the original change activation. Engine drops duplicated `PHASES` / `PHASE_NAMES` / `PHASE_COMMANDS` constants and imports them from `osx`; a test pins the shared identity.
- Make `install --with-core` non-destructive with snapshot and `restore-core`. `install --with-core` previously ran `openspec init --tools <t> --force`, clobbering any pre-existing core deployment and the user's global config under `~/.config/openspec`. Now detect a prior deploy via `openspec list`, a post-rename `osc-*` marker, or `[core].installed` in `manifest.toml`; refuse to overwrite (exit 2) unless `--force` is given; on `--force`, snapshot the prior global config to `.openspec-extended-baseline.json` so it can be restored with `restore-core`. `source/cli.py`: `--force` on install / update, `_detect_existing_core_deployment`, `_capture_global_config`, `_write_core_baseline`, `restore-core` command, baseline filename in `.gitignore` envelope, baseline path recorded in manifest core block. Bump `osx-maintain-docs` command to 0.2.1 in both manifests. `tests/integration/test_install_with_core_safe.py` locks in the refusal, the snapshot-on-force, the restore-core round-trip, and the gitignore envelope.
- Enforce `openspec >= 1.6.0` at orchestrator startup. The orchestrator dispatches to `osc-update-change` in PHASE2 Case A; that command does not exist before v1.6.0, so old cores silently no-op the update. Add a hard floor: `run_orchestrator` now parses `openspec --version` and exits 2 with an upgrade hint if the floor is not met. `source/lib/osx.py`: add `MIN_OPENSPEC_VERSION` constant and `get_core_version()` parser that returns `None` on missing binary, non-zero exit, timeout, or unparseable output. `source/orchestrator/engine.py`: gate `run_orchestrator` right after the `openspec` probe so the check runs before any side effects. `tests/unit/test_core_version_gate.py` locks in refusal for old core (1.5.3) and acceptance for 1.6.0+.
- Stub skills and bump the install fixture for the mechanism test. Bump fixture `VERSION` 1.2.0 → 1.2.1 to match current release; add stub skills + phase commands to the e2e mechanism fixture so preflight validators pass without a source checkout.
- Adapt orchestrator and CLI to OpenSpec v1.6+ contracts. `engine.py`: preflight always runs unless `--from-phase` (Fix 5; was double-gated on `--clean`); AI binary probe matches detected platform (Fix 6; opencode vs claude). `osx_cli.py`: `state transition` requires `--target` and `--reason` options (was silent-misbind on positional). `osx.py`: `store_register` uses upstream `--id` flag (was `--name` in v1.4); drop redundant `--json` from `validate_*` / `schema_*` wrappers (`_run_openspec_json` owns the flag). Add integration tests pinning preflight, state-transition, and no-double-json contracts; update unit tests for `--id` and `--json` ownership changes.
- Move transient file cleanup from phase6 to orchestrator. Renumber steps 1-5 → 1-4 (drop Step 1 cleanup; orchestrator now owns it). Phase6 must NOT delete `.osx-orchestrate-*.log` (orchestrator needs it to amend the archive commit after success). Document orchestrator's success-path cleanup (`state.json`, `complete.json`, baseline). Bump `osx-phase6` manifest version 0.3.6 → 0.3.7.
- Adopt the schema-agnostic review / modify contract from `openspec-update-change`. Rewrite `osx-review-artifacts` and `osx-modify-artifacts` to consume OpenSpec `status` / `instructions` JSON verbatim: no hardcoded artifact names, write only to `existingOutputPaths`, never to glob-resolved `outputPath`. Drop the 321-line review-criteria rubric and common-issues reference; rely on schema template + rules from OpenSpec instructions for conformance. Modify narrows to surgical single-artifact edit with per-artifact confirmation; forward-only unlocks propagation, never rewrites deps. PHASE0 emits routing report instead of in-place fixes; PHASE2 Case A defaults to `/opsx:update` with `/osx-modify` as isolated single-artifact fallback. Slash commands `osx-review` / `osx-modify` / `osx-verify-tests` adopt the schema-agnostic body and reference the rewritten skills; fix stale `/osx-test-compliance` and `/osx-verify` refs in `osx-review-test-compliance`. Wire v1.6 store-selection paragraph and `Bash(openspec:*)` allowed-tools throughout affected skills / commands; bump related manifest entries to align OpenCode and Claude trees. Add `tests/unit/test_resource_contract.py` (77 static assertions); extend `tests/e2e/mechanism.bats` to assert rubric deletion after install. Document the integration plan in `docs/review-modify-integration.md`.
- Sync the OpenSpec subtree at `openspec-core/source` from `https://github.com/Fission-AI/OpenSpec@v1.6.0`. Squashed `546224e..e1b51d1`.

### Fixed

- Fix dead `/osx-*` slash-command references in skills and commands. After `install --with-core`, the wrapper renames upstream workflows to `/osc-*` (`apply`, `verify`, `archive`, `sync`, ...); the `osx-*` namespace is reserved for our own commands. Several skills and one command still advertised the dead `/osx-apply`, `/osx-verify`, `/osx-archive`, and `/osx-sync` names. `resources/opencode/skills/osx-generate-changelog/SKILL.md`: `/osx-{apply,verify,archive}` → `/osc-{apply,verify,archive}`; `resources/opencode/skills/osx-maintain-ai-docs/SKILL.md`: `/osx-archive` → `/osc-archive`; `resources/opencode/commands/osx-maintain-docs.md`: `/osx-{sync,archive}` → `/osc-{sync,archive}`. Bump `osx-generate-changelog` (0.2.1 → 0.2.2) and `osx-maintain-ai-docs` (0.2.0 → 0.2.1) in both manifests. `tests/unit/test_command_refs.py` static guard scans every skill and command body for the dead `/osx-<verb>` patterns.

## [1.2.1] - 2026-07-22

### Added

- Add a hermetic install fixture and wire bats to build. `pack.sh` stages `dist/openspec-extended` into the release tarball layout, mirroring the GitHub Actions release workflow. `VERSION` file pins the fixture version (1.2.0); `pack.sh` and `install.bats` read it instead of hard-coding 0.19.0. `.gitignore` narrowed to `tests/fixtures/install/releases/` so `pack.sh`, `VERSION`, and `README.md` stay tracked. `verify` and `test:unit:bats` depend on build (`--log-level FATAL`) so the binary exists before bats runs. Document the new layout and dependencies in `install/README.md`.

### Changed

- Make the resource path test independent of the checkout name.
- Align `sync-core` with the current OpenSpec generation. Include the update workflow and use upstream `pnpm` build policy; keep temporary cleanup traps scoped to file generation.

## [1.2.0] - 2026-07-15

### Added

- Add `E2E_SKIP_ORCHESTRATOR=1` support for archive replay. Allow skipping orchestrator execution; replay tests from pre-existing archives using `E2E_DIR` and `E2E_CHANGE_NAME`; enable cleanup by uncommenting `teardown_e2e_repo`.
- Add a `clean` mise task to remove PyInstaller artifacts (`dist/`, `build/`, `*.spec`).
- Add a dogfooded orchestrator example and update README. `examples/hello-orchestrator.md` is the real output of running the 7-phase loop on `openspec/changes/add-orchestrator-example`, providing a self-contained reproducible proof that the orchestrator works on a spec-driven change. README documents the new unified CLI surface (passthrough commands and the schema override), adds the Documentation section linking to `docs/`, and updates the project tree to include the runner module and `docs/` directory.
- Add a unified CLI passthrough and `osx schema` sub-app. Every upstream `openspec` command is now exposed as a top-level `openspec-extended` passthrough (`validate`, `list`, `show`, `status`, `instructions`, `templates`, `schemas`, `init`, `update-core`, `feedback`, `completion`). A shared `run_openspec` helper forwards argv, stdout, stderr, and exit code with no transformation. The `orchestrate` command grows a `--schema` override flag for one-shot schema pinning. The `osx` sub-app gains an `osx schema` group (`which`, `list`, `validate`, `fork`, `init`) so programmatic access matches the CLI surface one-to-one.
- Add schema-aware orchestration with 4-level resolution precedence. `resolve_schema()` walks four sources in order: explicit override, per-change `.openspec.yaml`, `openspec/config.{yaml,yml}`, and the `'spec-driven'` default. The orchestrator now calls `validate_schema` in its pre-flight and caches the result on `OrchestratorState` (`schema_override` / `name` / `source`) so subsequent phases can branch on it. `ctx_get` reports the active schema alongside the change's existing artifacts. The `osx validate` domain grows five programmatic actions (`change`, `spec`, `all`, `changes`, `specs`) that shell out to `openspec validate --json` and translate the upstream contract into our `{valid, errors, warnings, items}` shape. `validate_change_dir` switches its required-files list off the resolved schema instead of hardcoding spec-driven artifacts.
- Add `pyyaml` dependency for schema-aware orchestration (consumed by the new `resolve_schema()`).
- Add Claude Code phase commands and platform-aware resource resolution. Mirror the 7 `osx-phase` commands to `.claude/commands/osx/` so the orchestrator works on Claude Code installs alongside opencode; register each in the Claude manifest at version 0.1.0. The osx library now resolves skill / command directories per platform via `detect_platform()` (`.opencode/` wins ties, `.claude/` is otherwise detected, opencode is the default fallback). `validate_skills` and `validate_commands` take an optional `project_root` and pick the right base directory, so install / validate work uniformly on either platform.
- Add an AI runner abstraction for opencode and claude dispatch. Extract subprocess management from `run_agent` into a `Runner` protocol with two implementations: `OpencodeRunner` (`opencode run`) and `ClaudeRunner` (`claude --print`). `detect_runner` selects based on the `.opencode/` or `.claude/` directory at the project root. The orchestrator now dispatches each phase through `runner.run(request)` instead of building `Popen` commands inline. Enables Claude Code support without branching in `engine.py`.
- Add OpenSpec v1.5.0 store support across CLI, lib, and orchestrator. `lib/osx`: `resolve_change_paths()` + `_run_openspec_json()` consult the `openspec` CLI first, fall back to repo-local paths; `current_store` `ContextVar` threads store context through every public verb (`ctx_get`, `phase_*`, `state_get`, `log_append`, `complete_*`, `validate_*`); new `store_list` / `store_doctor` / `store_register` / `store_unregister` wrappers. `osx_cli`: top-level `--store/-s` callback sets the contextvar; new `osx store {list,doctor,register,unregister}` sub-app. `cli.orchestrate`: `--store` flag plus `store:change` positional parsing. `orchestrator.engine`: `OrchestratorState.store`, `parse_change_spec`, multi-store `list_changes` aggregation, store context set across the run loop. Tests cover unit (path resolution, store_* library functions), integration (store-aware orchestrator), and bats mechanism (`--store` flag and sub-app on the built binary). `mise` registers `pnpm` tool.

### Changed

- Update the OpenSpec version requirement to v1.5.0+ across README and the install preflight.
- Drive `sync-core` from an in-tree git subtree at the latest release tag. Replace the fresh upstream clone with `git subtree pull` against `openspec-core/source`; resolve the latest stable `vX.Y.Z` tag via `git ls-remote --tags`, skipping pre-release tags; build in-place inside the subtree rather than a tempdir; refuse to run when the subtree has uncommitted local changes. Update `openspec-core/AGENTS.md` to document the new flow.
- Thread `project_root` through orchestrator validators and sync docs. `engine.py`: derive `project_root` from the active change dir and pass to `validate_skills` / `validate_commands`; `source/lib/AGENTS.md`: document the new `project_root=None` parameter; `docs/cli-comparison.md`: note `osx` instructions passthrough, domain count 10 → 12, fix schema discovery commands; `docs/orchestrator-state-machine.md`: clarify budget is per-phase visit, not cumulative; `docs/troubleshooting.md`: split decision-log missing / malformed, switch phase_complete fix to `osx phase current`, link openspec not-found to roadmap Tier 4; README and `examples/hello-orchestrator.md`: rename `add-orchestrator-example` → `example-orchestrated`.
- Clean up unused imports in tests and document test files. Drop unused `osx`, `Path`, `json`, `app`, and `MagicMock` imports from the lifecycle, completion, git, install, orchestration-logging, and phase-workflow integration tests; fix an unneeded f-string in the logging test. The `osx_orchestrate` unit test no longer needs its redundant `osx` import once `check_complete_detection` stopped dereferencing it. `tests/unit/AGENTS.md` adds the new schema-aware unit and integration files to the test roster.
- Document the CLI surface, orchestrator state machine, and troubleshooting. `docs/cli-comparison.md` maps every upstream `openspec` command to its `openspec-extended` passthrough and the programmatic `osx` equivalent. `docs/orchestrator-state-machine.md` describes the 7-phase loop, retry budget, transition reasons, schema resolution, and resume semantics. `docs/troubleshooting.md` pairs each error code surfaced by the `osx` library with a likely cause and fix.
- Sync the OpenSpec subtree at `openspec-core/source` from `https://github.com/Fission-AI/OpenSpec@v1.5.0`. Squashed `546224e`.
- Refresh docs for OpenSpec v1.5.0 stores. `openspec-core/AGENTS.md`: bump Version to v1.5.0; add store highlight paragraph. `osx-concepts/SKILL.md` (opencode + claude): drop "verified v1.4.1" wording; mention `--store` flag on `status`. `osx-concepts/references/cli-reference.md` (opencode + claude): bump 10 version pins, add "openspec store and `--store` flag" subsection, add §C "store" subsection, add `.openspec.yaml` note. `resources/{opencode,claude}/manifest.toml`: bump `osx-concepts` 0.7.0 → 0.8.0.

### Fixed

- Fix `version:check` to detect manifest entries under nested command paths.

### Removed

- Remove the dogfooded orchestrator example and README section (folded into docs/).

## [1.1.0] - 2026-06-19

### Changed

- Split version task ownership between `release` and `version:check`. `version:check` / `version:update` now scope to framework components (resource manifests) and `install.sh`; remove the tool-version case and the duplicated lockstep block. Pre-commit drops tool-version files from the `check-version-bump` regex so non-version edits no longer trigger false `needs_bump`. AGENTS.md clarifies that `release` owns the three tool-version files. Fix a pre-existing bug in `version:update` where `||` should be `&&` in three `[[ -z "$line" ]]` guards, causing silent skips.
- Mount the `osx` tool as a binary subcommand and drop deployed wrappers. Previously the install phase copied `source/lib/osx.py` and `source/orchestrator/engine.py` into `.opencode/scripts/` as Python files the AI agents invoked directly; that failed with `ModuleNotFoundError: No module named 'typer'` when the deployed script ran against system Python. Split `source/lib/osx.py` into a pure library (no Typer import) and a new `source/osx_cli.py` holding the Typer app; mount the Typer app as the `osx` subcommand of the main CLI; drop `deploy_scripts` and `deploy_lib` code paths and the corresponding `[resources.scripts]` / `[resources.lib]` manifest entries; update all phase command prompts and skill docs to call the binary directly. Add `tests/unit/test_architecture.py` with static guards (library purity, manifest invariant, prompt content) and 3 new mechanism bats tests covering the binary path.

## [1.0.3] - 2026-06-17

### Fixed

- Fix the installed manifest top-level version defaulting to `'unknown'`. `cli.py` now writes `__version__` instead of `source_manifest.get("version", "unknown")`; tests assert installed manifest version equals `__version__` (not just non-empty).

## [1.0.2] - 2026-06-17

### Fixed

- Fix the release workflow combining `SHA256SUMS`. `merge-multiple` flattened downloaded artifacts, breaking `artifacts/*/SHA256SUMS`; removing it restores the per-artifact subdirectories the combine step expects.

## [1.0.1] - 2026-06-17

### Changed

- Bump release workflow actions to Node 24. `actions/checkout@v4` → `@v6`; `jdx/mise-action@v2` → `@v4`; `actions/upload-artifact@v4` → `@v7`; `actions/download-artifact@v4` → `@v8`; `softprops/action-gh-release@v2` → `@v3`. Resolves GitHub's Node.js 20 deprecation warning on the release workflow, which was forcing these actions onto Node 24 anyway.

### Removed

- Drop `darwin-x86_64` from the release build matrix. The `macos-13` runner image was removed from GitHub Actions, so the matrix entry was failing on the next tag push. Apple Silicon has been the standard for macOS since 2020, so the Intel Mac audience for this tool is negligible. AGENTS.md updated to match the new 3-platform matrix (`linux-x86_64`, `linux-arm64`, `darwin-arm64`).

## [1.0.0] - 2026-06-17

### Added

- Add a shell-argument safety guard to decision log writes. When agents pass markdown backticks (e.g. `` `local` ``) inside a shell argument like `--summary "...\`local\`..."`, zsh interprets the backticks as command substitution and dumps the entire shell environment (20KB+ of PATH, tokens, internal variables) into the string; that blob then lands verbatim in `decision-log.json` and inflates the workflow log by orders of magnitude. `source/lib/osx.py`: add `LOG_TEXT_FIELD_MAX_LENGTH` and a fingerprint set of common zsh env-dump markers; `log_append` rejects oversized or tainted `summary` / `next_steps` strings with a clear error before they reach disk. `source/orchestrator/engine.py`: default `state.log_file` to `.osx-orchestrate-<change>.log` when the user does not pass `--log-file`, so the workflow log is visible and cleanable. `tests/lib/test_osx.py`: 3 new unit tests (oversized summary, zsh-fingerprint summary, oversized next_steps) plus a happy-path test. `osx-{analyzer,builder,maintainer}.md`: add "never use backticks in shell arguments" guardrail. `osx-phase{0..6}.md`: add SHELL ARGUMENT SAFETY section. `osx-phase6.md`: also add `rm -f .osx-orchestrate-$1.log` to the transient-file cleanup.
- Add per-directory AGENTS.md docs and exclude from binary. 20 new AGENTS.md files document `resources/`, `source/`, `tests/` trees; `openspec.spec` excludes AGENTS.md from PyInstaller data; `install.sh` deletes AGENTS.md from the extracted tarball; `version/check` filters AGENTS.md from staged-file detection; `version/check` supports `readonly SCRIPT_VERSION=` and detects bump via diff; `install.sh` bumps SCRIPT_VERSION 0.2.0 → 0.2.1.
- Add a pytest marker system and convert remaining BATS tests to Python. Generalized pytest markers (`unit`, `integration`, `mechanism`, `e2e`); `pytestmark` to all Python test files; port `schema-validation.bats` (23 tests) to `test_schema_validation.py`; port `full-workflow.bats` (30 tests) to `test_full_workflow.py`; delete 9 obsolete bats files; add `tests/conftest.py` with marker registration and e2e skip logic; add `pyproject.toml` `pytest.ini_options`; update mise tasks to use `pytest -m` marker filtering. Test counts: 196 unit + 61 integration + 6 mechanism + 30 e2e (skipped unless `E2E_CONFIRM=1`).
- Add Python rewrites of `openspec-extended` and `osx-orchestrate`. Rewrite `bin/openspec-extended` from Bash to Python + Typer (installer CLI); rewrite `resources/opencode/scripts/osx-orchestrate` from Bash to Python + Typer (workflow orchestrator); add 60 Python unit tests (32 for openspec-extended, 28 for osx-orchestrate); add mise tasks for lint (ruff) and typecheck (ty); add typer and rich as runtime dependencies (eliminates jq dependency).

### Changed

- Sync `uv.lock` in the release and `version:update` tasks. Pre-commit's `test` hook runs `uv run pytest`, which re-syncs the project and updates `uv.lock` when `pyproject.toml`'s version drifts from the lock file. Without an explicit `uv lock` in the bump flow, the hook does the sync itself — and aborts with "files were modified by this hook".
- Wire GitHub Actions to build and publish release tarballs. The `release.yml` workflow now runs a 4-platform matrix build on tag push (`linux-x86_64`, `linux-arm64`, `darwin-x86_64`, `darwin-arm64`), packages each binary into `openspec-extended-v$VERSION-{platform}.tar.gz` with the `bin/` layout `install.sh` expects, merges per-platform `SHA256SUMS`, and uploads everything to the matching GitHub release. Previously the workflow created the release page but never produced or uploaded any assets, so `install.sh` 404'd on every tag. `release` task refuses to run on non-main branches (`RELEASE_ALLOW_BRANCH` override) so feature branches cannot push tags; `version:check` flags content changes to `pyproject.toml` and `source/__init__.py` without a matching version bump; `version:update` mirrors the highest target across the three tool-version files. AGENTS.md, README.md, and the fixture README drop references to the never-existing `mise run build-release` task and document the CI-driven flow.
- Migrate the `add-hello-script` fixture to delta-spec convention. The fixture was using a flat `specs/hello.md` and a homegrown artifact format; migrate to OpenSpec's `specs/<capability>/spec.md` delta format and reformat proposal / design / tasks to match the OSC templates. `specs/hello.md` deleted. `specs/hello-script/spec.md`: new, in OpenSpec `## ADDED Requirements` format with WHEN / THEN scenarios. `proposal.md`: rewritten with `## Why` / `## What Changes` / `## Capabilities` / `## Impact` sections. `design.md`: rewritten with `## Context` / `## Goals / Non-Goals` / `## Decisions` / `## Risks / Trade-offs`. `tasks.md`: rewritten with 6 numbered sections, 19 numbered tasks. `tests/e2e/full-workflow.bats`: `E2E_TIMEOUT` 3600 → 12000; `+--clean` flag so the run starts fresh; `teardown_e2e_repo` commented out (orchestrator leaves artifacts in active use); archive test updated `specs/hello.md` → `find specs -name spec.md`.
- Extract the `osx-workflow` skill from `osx-concepts`. `osx-concepts` had grown to 443+531=974 lines mixing the framework reference with the workflow reference; split into two: `osx-concepts` (framework only: artifacts, delta specs, decision guidance, glossary; 178 + ~150 lines) and `osx-workflow` (workflow only: 4 tool layers, phases, state files, full `osx` verb table, invocation, blocker / resume, edge cases; 401 + 663 lines, mostly moved from the deleted `autonomous-workflow.md` reference). New `osx-workflow` skill mirrored under `resources/claude/skills/`; `autonomous-workflow.md` moved from `osx-concepts/references/` to `osx-workflow/references/` on both platforms; `resources/opencode/commands/osx-{modify,phase0..6}.md`: now load both `osx-concepts` and `osx-workflow` (Step 4 / 5); `osx-modify` fixes a `osc ctx` → `osx ctx` typo; phase0 / 5 raise the iteration cap 5 → 10 and replace `CRITICAL BLOCKER` with `BLOCKED`; phase2 renames the title to "Review" with a callout explaining the Verification / Review naming collision; phase4 fixes `PHASE5 (ARCHIVE)` → `PHASE5 (SELF_REFLECTION)`. Resource manifests bumped; PyInstaller bundles Claude resources alongside OpenCode; mechanism bats asserts both skills deploy to fresh tmpdirs on both platforms.
- Document the `osx` lib verb vocabulary and accept `show` / `list` aliases. `osx` lib CLI: `show` / `list` / `set` / `clear` silently route to canonical `get` / `append` / `set-phase` / `clear-transition`; error responses still list canonical verbs only. `osx-concepts` skill gains a complete vocabulary table to anchor the model on the canonical verbs (no `show`, no `list` — only `get`). Autonomous-workflow reference: fix 6 broken paths, drop invalid `validate changes` row, mirror the vocabulary table. Bump `osx-concepts` 0.5.1 → 0.5.2 and `lib.osx` 0.1.3 → 0.1.4.
- Stream agent subprocess output to terminal in real time so contributors can follow AI progress as it happens.
- Refactor the orchestrator to use the in-process `osx` library. Expose `osx` as Python library (`state_get`, `phase_advance`, etc.) with `OSXError` for in-process error handling; Typer CLI retained for `python -m source.lib.osx` invocation and tests. Orchestrator imports `osx` directly, replacing `subprocess run_osx_command`. Fix unreachable PHASE6 branch in `run_orchestrator` that prevented log archiving after workflow completion. Fix agent log capture (subprocess stdout was redirected to a leaked `tempfile.mkstemp` fd and an empty file, so e2e logs contained only session markers, no agent responses). Allow `orchestrate --list` without a change ID. Update AGENTS.md to reflect the in-process library architecture.
- Wire bats suites into the default test task. `test:unit:bats`: hermetic install.bats, no build needed. `test:mechanism:bats`: mechanism.bats against built binary, depends on build. Both wired into parent `test` task in `.mise/config.toml`. AGENTS.md Testing section refreshed; remove stale `test:eunit` reference.
- Update miscellaneous configuration and dependencies: `.gitignore` for test fixtures; Python version to 3.12; shellcheck config; `uv` lock file.
- Update documentation with E2E strategy and build / release docs. New E2E test strategy section explaining mechanism vs full-workflow tests; document build / release process (`mise run build`, `build-release`); version management details (3 synchronized version fields); improve project structure section with build tooling.
- Improve `install.sh` with `BASE_URL` override and platform detection. Add `BASE_URL` env var to override the release host for testing; `detect_platform()` for platform-aware tarball naming; improve checksum verification with platform-specific filename; add pre-commit and mise configs for install tests.
- Rename CLI command `run` to `orchestrate` and split the skills list. Rename `run` command to `orchestrate` for clarity; split `REQUIRED_SKILLS` into extended (`osx-*`) and core (`osc-*`) lists; hide the internal `osx` subcommand from the public CLI interface.
- Migrate E2E tests from pytest to bats. Replace `pytest test_full_workflow.py` with `full-workflow.bats` and `mechanism.bats`. Bats tests run against the built binary for authentic PyInstaller validation.
- Convert version management scripts from Python to Bash. Replace Python modules with pure Bash equivalents using inline Python for text manipulation. `version:check` / `version:update` tasks now use a bash-only approach. Deleted `version/lib/__init__.py`, `detect.py`, `manifest.py`, `state.py`. Added `version/lib/bump.sh`, `detect.sh`, `manifest.sh`, `state.sh`.
- Refactor CLI commands to hide the internal `osx` command. Remove `osx` from CLI help (internal change-management tool); remove `run` command (redundant with `orchestrate`); add help descriptions to `install`, `update`, `orchestrate`.
- Refactor pre-commit hooks and test configuration. Narrow shellcheck scope to `install.sh` (old bash scripts removed); rename `test` hook to `verify` with `mise run verify`; remove deprecated pytest marker registration from conftest; use equals-style CLI args in `test_mechanism`.
- Restructure AGENTS.md for Python implementation. Remove Bash requirements, shell patterns, and `/osx-*` command table; add Python code style (typer CLI, toml state, rich console); add pytest markers and testing patterns; update project structure to reflect `source/` layout; document `mise run version` for version bumping; remove autonomous workflow and E2E workflow sections.
- Refactor CLI tools from Bash to Python. Convert `openspec-extended` CLI to Python with typer / rich; convert `osx-orchestrate` to Python orchestrator engine; convert `osx` lib tool to Python with full API parity; add hatch build system with `source/` package layout; add PyInstaller spec for binary distribution; update test suite to Python with integration coverage.
- Convert manifest storage from JSON to TOML. Source manifests were already TOML but code read them as JSON, causing install / update to fail. `bin/openspec-extended`: replace `json` with `toml` module; all manifest references `.json` → `.toml`; `pyproject.toml` adds `toml>=0.10` dependency; tests updated to use TOML format; fix ruff incorrectly "fixing" multi-exception syntax.
- Refactor version management from Bash to Python. Convert `version/check` and `version/update` tasks to Python; replace bash lib scripts with Python modules (`detect`, `manifest`, `state`); migrate manifest format from JSON to TOML; simplify the `release` task to remove manifest updates.
- Complete the Bash-to-Python rewrite with 61 new integration tests. Swap `openspec-extended` and `osx-orchestrate` to Python (remove intermediate `.py` files); convert bats integration / e2e tests to pytest (61 tests across 7 new files); fix `get_target_path` to handle missing commands directory; fix `_list_changes` JSON parsing for `openspec list --json` output format; update `.mise/config.toml` for new script paths without `.py` extension.

### Fixed

- Fix `version:check` to detect manifest version bumps for resources. `check_resource_file` reported `needs_bump` for any staged resource file that exists in HEAD, regardless of whether the version was actually bumped in `resources/<platform>/manifest.toml`. This made the `check-version-bump` pre-commit hook impossible to satisfy for any commit that touched a versioned resource, forcing `--no-verify` on every such commit. Fix: `check_resource_file` skips the check when the staged file has no content diff (mirror the script fix from `b5b8398`); compares the working-tree version in the manifest to the version in `git show HEAD:<manifest>` and reports `ok` when they differ, `needs_bump` when they match; `lib/manifest.sh` extracts the awk version-parser into `parse_resource_version_from_stdin` so the check can pipe `git show` through the same logic that `get_resource_version` uses; `check` drops the now-unused `get_git_show_content` helper.
- Fix core resource renaming and add post-deploy validation. Merge contents when the destination dir exists during `openspec-*` → `osc-*` rename; validate all core `osc-*` skills installed after `deploy_core()` and fail fast; extract and track core skill versions in `manifest.toml`; split `REQUIRED_SKILLS` into extended (`osx-*`) and core (`osc-*`) lists; update `osx validate skills` to check both lists with improved error reporting.
- Fix orchestrator color output and script deployment in the frozen binary. Use `rich.print` instead of `print` for markup (plain `print` doesn't interpret `[color]` tags); bundle `source/orchestrator` and `source/lib` in PyInstaller for frozen binary access.
- Fix Python 3.12 compatibility and expand lint / typecheck coverage. Use Python 3.12-compatible exception syntax `except (X, Y):` instead of `except X, Y:`; change `requires-python` from `>=3.14` to `>=3.12` in `pyproject.toml` and `uv.lock`; add explicit type annotations in `osx` lib script (`dict[str, Any]`); expand `mise lint` and `typecheck` to include `osx` script and `mise` version scripts; rename ambiguous variable `l` to `line` in `detect.py`.
- Fix TOML manifest parsing after the JSON → TOML migration. Use external `toml` package instead of stdlib `tomllib` for compatibility; update manifest path references from `.json` to `.toml`; bump `osx-orchestrate` and `openspec-extended` to v2.0.0.

### Removed

- Remove the unused `AGENTS.md` file.

## [0.19.0] - 2026-06-10

### Changed

- Bump the `openspec-core` version note to v1.4.1 in the core subtree's `AGENTS.md` so the documented minimum version matches what the v1.6+ OpenSpec contracts require.

### Fixed

- Fix `sync-core` to allow the esbuild postinstall under pnpm 10.26+. pnpm 10.26+ blocks dependency build scripts by default and exits non-zero when any are unreviewed, which `set -euo pipefail` propagates as a task failure. Esbuild's postinstall downloads the native binary the OpenSpec build needs, so it must be allowed: write `pnpm-workspace.yaml` with `allowBuilds.esbuild: true` in the cloned temp directory before running `pnpm install`.

### Removed

- Remove the OpenCode singular `command/` workaround. The OpenSpec opencode adapter installed files in `.opencode/command/` (singular) before v1.3.0; the upstream fix lets `rename_core_resources()` drop its migration logic. Drop the `command/` iteration, the `osc-*.md` elif branch, the `osx/` subdir handling, and the trailing rmdir; point integration-test mocks at `commands/` (where upstream now writes) and drop the singular→plural migration case.

## [0.18.2] - 2026-03-18

### Added

- Add tests for installer validation and core rename logic. Test no false-positive warnings for scripts / lib resources; test opsx-* to osc-* command renaming with mocked OpenSpec CLI; test command/ to commands/ directory consolidation.

### Fixed

- Fix orchestration logging to capture agent output and archive correctly. Capture agent output to a temp file with session markers (`"> osx-analyzer"`); strip ANSI color codes from all log writes for cleaner logs; archive the log file BEFORE validating the archive (was causing missing logs); improve `archive_log_file` error handling and validation; add mock opencode / git helpers for testing; add integration tests for logging patterns.

## [0.18.1] - 2026-03-16

### Fixed

- Fix installer validation and core command handling. Fix false-positive warnings for scripts / lib resources; handle OpenSpec CLI's `command/` directory alongside `commands/`; consolidate all core commands to the canonical `commands/` location.

## [0.18.0] - 2026-03-16

### Changed

- Refactor the installer for version-aware updates. Add semver comparison to upgrade outdated resources on install; remove conflicting core resource removal (osc-* and osx-* coexist); unify deployment logic with a single `deploy_type()` loop; support nested command directories for Claude; track core resources in the manifest when using `--with-core`; add 18 tests for version comparison and upgrade behavior.

### Fixed

- Fix core resource renaming for Claude and document original names. Add Claude support to `rename_core_resources` (`opsx/` → `osc/` directory); rewrite internal references (`/opsx-*` → `/osc-*`, `/opsx:*` → `/osc:*`); document original `openspec-*` names alongside `osc-*` in all resources; fix typos in command references (`osxreview` → `osx-review`); sync manifest versions across platforms.

## [0.17.2] - 2026-03-16

### Changed

- Refactor E2E tests to run the workflow once with 28 verification tests. Use BATS `setup_file()` to run the expensive workflow once per file; add state-file infrastructure for sharing variables between setup and tests; fix jq queries for JSON array structures (`iterations.json`, `decision-log.json`); organize tests into 11 categories (workflow, artifact, archive, iterations, logs).
- Clarify PHASE6 completion detection in documentation: correct step 5 description to "commit archive" (not "mark phase complete"); document that the orchestrator detects completion via archive directory existence.

## [0.17.1] - 2026-03-16

### Changed

- Refactor the `osx-concepts` skill for an AI-agent audience. Add a skill taxonomy distinguishing core (`osc-*`) from extended (`osx-*`) skills; add enhancement patterns showing how extended skills augment the core workflow; remove all slash-command syntax (`/osx:*`) — use skill names instead; replace the command table with a skill reference table; delete `osx-lifecycle.md` (command-focused, wrong audience); add `autonomous-workflow.md` reference for orchestrator details; condense from 593 to 425 lines with progressive disclosure to references.

## [0.17.0] - 2026-03-15

### Added

- Add the `osx-commit` skill with standardized phase command invocation. Add a detection script for Conventional, Angular, Gitmoji, and Classic styles; add reference docs with examples for all 4 commit standards; standardize `osx-commit` invocation across all 7 phase commands; update manifests with the `osx-commit` skill and version bumps; update version check to track skill scripts.

### Fixed

- Fix PHASE6 log archiving to use the archive directory path. The log file was being moved to the change directory instead of the archive directory; now queries the `osx` lib for the correct archive path before moving the log file.

## [0.16.0] - 2026-03-13

### Security

- Add security validation and safety improvements to `install.sh`. Validate `REPO`, `VERSION`, `PREFIX` inputs to prevent injection attacks; add download integrity verification with SHA256 checksums; secure temporary directory handling with owner-only permissions; enhance `uninstall` with confirmation prompts and a removal preview; add OS-specific dependency installation hints; detect shell type for PATH setup suggestions. Replace the test suite: delete `test_install_sh.sh` and add 23 new input-validation and code-quality tests; fix a pre-existing test in `openspec-extended.bats`.

## [0.15.4] - 2026-03-13

### Added

- Add `uv sync` to the `tag` task after `pyproject.toml` version update. Ensures `uv.lock` stays synchronized when bumping version during release.

### Changed

- Bump command versions for `osc` → `osx` tool alignment. Update manifest versions for modified commands; align tool references from `lib/osc` to `lib/osx`; phase commands: `osx-phase0` (0.2.7), `osx-phase1` (0.2.9), `osx-phase2` (0.2.12), `osx-review` (0.1.2).

## [0.15.3] - 2026-03-13

### Changed

- Push the main branch when creating release tags (the release pipeline was leaving the tag orphaned).

### Fixed

- Fix version detection to use `manifest.json` (instead of scanning resource frontmatter, which lagged behind manual edits).

## [0.15.2] - 2026-03-13

### Fixed

- Fix resource deployment to skip existing files during install. `install`: skip existing commands / lib scripts (only add new); `update`: force-overwrite all files as before; remove conflicting `osc-*` files when `osx-*` extended resources exist; clean manifest (remove deprecated `osx-*` lib script entries); add `AGENTS.md` to lib deployment.

## [0.15.1] - 2026-03-13

### Changed

- Relocate lib-scripts docs to `resources/opencode/scripts/lib` so the on-disk tree matches what the installer copies.

### Fixed

- Fix PHASE6 log file archiving validation. The `archive_log_file` function was returning success even when it failed to move or commit the log file, causing the orchestrator to report "Implementation completed successfully!" when the log file wasn't archived, making the e2e test fail. Return error code when `git commit --amend` fails; return error code when `mv` fails to move the log file; change warnings to errors with diagnostic messages; check `archive_log_file` return value in PHASE6 completion; exit with error when log archiving fails. Bump `osx-orchestrate` to 1.7.0.
- Fix validation to support nested spec dirs and display errors. Change `osx validate` to use `rglob` for recursive spec file detection so specs in nested directories (`specs/subdir/spec.md`) are detected instead of only flat structure (`specs/spec.md`). Fix silent failures in `osx-orchestrate` when `osx` commands fail: modify `run_osx` to always output result before checking exit code; add `|| true` to all `run_osx` calls to prevent `set -e` exit; improve `print_validation_errors` to avoid subshell pipeline issues. These fixes ensure error messages are displayed before script exits.

## [0.15.0] - 2026-03-13

### Changed

- Rename resources to the `osx-*` prefix for extended variants. CLI: `openspecx` → `openspec-extended`. Skills: `openspec-*` → `osx-*`. Commands: `openspec-phase*`, `opsx-*` → `osx-*`. Agents: `openspec-*` → `osx-*`. Scripts: `openspec-auto` → `osx-orchestrate`, `osc` → `osx`. Update docs, config, and tests to match the new naming.

## [0.14.0] - 2026-03-12

### Added

- Add `run` subcommand to `openspecx` for workflow execution. Delegates to `.opencode/scripts/openspec-auto`; passes all arguments through to `openspec-auto`; provides a helpful error when the script is not installed.

### Changed

- Continue the `osc` tool migration with baseline and phase domains. Add `baseline` domain (`record`, `get`) and `phase` domain (`current`, `next`, `advance`); delete 10 deprecated bash scripts (`osc-baseline`, `osc-common`, `osc-complete`, `osc-ctx`, `osc-git`, `osc-iterations`, `osc-log`, `osc-phase`, `osc-state`, `osc-validate`); update `openspec-auto` to use `osc` directly instead of `osc-common`; update `manifest.json` to track only `osc` (version 0.3.0); update tests and documentation for the new argument order.
- Complete the `osc` tool migration with `ctx` and `git` domains. Add `ctx` and `git` domains to the `osc` Python tool; update phase prompts to use `osc ctx get`, `osc state`, `osc log`, etc.; replace JSON pipe patterns with direct CLI arguments; add tests for `ctx` and `git` domains.
- Replace JSON-heavy bash scripts with a unified Python CLI tool. Add the `osc` tool (998 lines) replacing `osc-state`, `osc-iterations`, `osc-log`, `osc-complete`, `osc-validate`; add 87 unit tests for the `osc` tool (pytest); update `openspec-auto` to use `osc` via a `run_osc()` wrapper; add `uv` integration for Python dependency management (postinstall runs `uv sync`; `test:unit:python` uses `uv run pytest`); add `pyproject.toml` version bumping to the `tag` task; track `osc` in `manifest.json` for version checking; update installer to deploy the `osc` Python tool; read `osc` version from `manifest.json` instead of a hardcoded constant.
- Improve the formatting of the README (heading hierarchy, table layout, install snippet).

### Fixed

- Fix phase progression and `osc` command compatibility in the autonomous workflow. Remove duplicate `run_osc()` that overwrote the error-handling version; add a `phase_determined` flag to prevent re-reading stale `state.json`; add `osc state show/set` aliases and `--iteration` support for agents; add `osc instructions` domain proxying to the `openspec` CLI; read `state.json` directly in `get_current_phase` to avoid error logs; fix the E2E test race condition with `sleep` instead of `wait` for `tee`.

## [0.13.2] - 2026-03-05

### Added

- Add log archiving and fix agent temp-directory permissions. `openspec-auto`: archive log to the change directory after PHASE6; use the project root for log files during execution. Agents: fix the `external_directory` pattern from `/tmp` to `/tmp/*`. `.gitignore`: add `suggestions.md` and `openspec-auto` log patterns. Version bumps: 0.11.0 (openspecx), 0.14.0 (manifest), 1.4.0 (script).

## [0.13.1] - 2026-03-05

### Fixed

- Fix PHASE6 workflow issues in `openspec-auto`. `osc-phase`: return error for archived changes without `state.json`. `openspec-auto`: skip `show_progress` after PHASE6 (state deleted); remove duplicate "Agent invocation" log. `openspec-phase6.md`: update logs before commit (was leaving uncommitted changes). Add test for archived change without `state.json`.
- Fix the output-capture race condition in the E2E streaming helper.

## [0.13.0] - 2026-03-05

### Added

- Add log file output and short CLI flags to `openspec-auto`. `--log-file` flag with optional path (default: `openspec/changes/<change>/openspec-auto.log`); ISO 8601 timestamps on all log output; short-flag aliases: `-t`, `-m`, `-l`, `-v`, `-d`, `-f`, `-c`, `-n`, `-V`.

### Changed

- Improve `openspec-auto` logging with a separate verbose mode. Add `log_verbose()` for conditional verbose output; strip ANSI codes from log files while preserving terminal colors; refactor `show_progress()` to respect the verbose flag; add comprehensive logging-behavior tests.

### Fixed

- Fix `--from-phase` agent execution failure in `openspec-auto`. The `AI_BINARY` variable was not initialized when `--from-phase` skipped pre-flight validation, causing timeout to fail with an empty command. Replace the variable with the literal `opencode` command since this project is opencode-specific.

## [0.12.1] - 2026-03-04

### Fixed

- Fix phase-transition bug causing premature exit with `set -e`. Use a conditional pattern for `check_transition` to handle empty result; add `capture_optional` helper for safe optional-value capture; document function-return conventions (`check_*` vs `get_*` functions); add 21 tests covering phase-transition scenarios.

## [0.12.0] - 2026-03-04

### Added

- Add explicit phase transitions and fix PHASE6 archive cleanup. `osc-state` gains the `transition` action for controlled phase jumps; clean transient files BEFORE archive commit (not after); detect PHASE6 completion by archive existence; update PHASE2 to use the transition system.
- Add `manifest.json` version sync to the `tag` task. Update `manifest.json` version field alongside `README.md` during releases; add `jq` dependency check with clear error message; include `manifest.json` in dry-run output.

## [0.11.0] - 2026-03-04

### Added

- Add `demo/` to `.gitignore` (interactive scratch space).
- Add `openspec/` to `.gitignore` to prevent runtime state commits.

### Changed

- Enable `/tmp` access for autonomous agents (relax the sandbox scope so the AI subprocess can use system temp).
- Restructure PHASE6 for atomic execution and clarify iteration limits. Add atomic-execution requirement section to prevent partial completion; merge PROCESS, MANDATORY END, and STATE FILE UPDATES into a numbered sequence; add verification checklist to ensure all steps complete before stopping; rename `--max-iterations` → `--max-phase-iterations` for clarity; update documentation and tests for the renamed option. Bump versions: `openspec-phase6` 0.2.10, `openspec-auto` 1.0.5. Fixes the issue where PHASE6 ran twice: once to archive, once to commit.

### Fixed

- Correct `openspec-auto` version from 1.0.5 to 1.2.1 (matched the manifest after a missed bump).

### Removed

- Remove accidentally committed `openspec/changes` runtime directory.

## [0.10.0] - 2026-03-03

### Changed

- Bump `openspecx` to 0.10.2 (cumulative patch series: 0.9.0 → 0.9.1 Bash 3.2 compatibility; 0.9.1 → 0.10.0 curl-based installer with `--version` / `--help`; 0.10.0 → 0.10.1 symlink-resolution fix; 0.10.1 → 0.10.2 error-handling fix).
- Enhance the `tag` task with README version sync and dry-run mode. Add automatic version update in `README.md` (badge + examples); add `--dry-run` flag to preview changes without executing; add `--no-commit` flag to update files without committing.
- Update repository URLs to `amauryconstant/openspec-extended`. Fix the badge link in `README.md`; update install examples to use the correct org / repo; fix the default `REPO` in `install.sh`.

## [0.9.2] - 2026-03-03

### Fixed

- Fix error handling for invalid tool argument. Temporarily disable errexit to capture `get_tool_dir` exit code; bump version to 0.9.2.

## [0.9.1] - 2026-03-03

### Changed

- Extend version check to cover all resources and root scripts so a single `mise run version:check` invocation catches every versioned file.

### Fixed

- Fix install script symlink resolution and repository paths. Add symlink resolution in `openspecx` to find the resources directory; fix default `REPO` to `amauryconstant/openspec-extended`; normalize version strings to prevent a double `v` prefix; use a generic directory search for tarball extraction; check the executable instead of `--help` for verification.
- Fix version check to process script files after resources so the script-version sweep doesn't miss newly added scripts.

## [0.9.0] - 2026-03-03

### Added

- Add a GitHub Actions workflow for automated releases: tag push triggers build + upload to GitHub Releases.
- Add a curl-based installer with script version tracking. `install.sh` supports `VERSION`, `PREFIX`, `REPO` options; `openspecx` gains `--version`, `--help`, and improved resource resolution; `version:check` validates `install.sh` and `bin/openspecx` versions; rewrite README with installation guide and feature comparison; add test coverage for install flow and CLI commands.

### Changed

- Refactor shell scripts for Bash 3.2 compatibility. Replace associative arrays with case-based lookup functions; standardize shebangs to `#!/usr/bin/env bash` for portability (macOS ships with Bash 3.2 due to GPLv3 licensing, which lacks associative-array support).

### Fixed

- Fix version check for first-time script versioning: require a version bump when introducing `SCRIPT_VERSION` to existing files, not just when the version is unchanged.
- Fix the PHASE6 archive loop and standardize phase names. Track phase iterations in `state.json.phase_iterations`; add canonical phase-name functions in `osc-common`; update lib scripts to support archived changes; standardize display names (`MAINTAIN DOCS`) and JSON names (`MAINTAIN_DOCS`).

## [0.8.5] - 2026-03-03

### Fixed

- Fix workflow bugs in the autonomous implementation system. Make `osc-phase` archive-aware via `osc_find_change_dir`; handle PHASE6 as a terminal phase with dedicated cleanup; fix phase labels in `show_progress` output; add `AGENTS.md` deferral notes in PHASE1 / PHASE3 and the review skill; add `suggestions.md` creation and tracking.

## [0.8.4] - 2026-03-02

### Added

- Add blocker handling to autonomous workflow phases. Add BLOCKER HANDLING sections to all phase commands with `osc-complete` usage; refactor `openspec-auto` to use a `run_lib_script` helper for better error output; auto-create initial state in `osc-phase` when `state.json` is missing; restructure completion flow to validate archive after PHASE6; add skill references and `osc-common` to version-check patterns.

## [0.8.3] - 2026-03-02

### Fixed

- Fix `osc_find_change_dir` silent exit with `pipefail`. The new archive-aware change-detection function failed silently when the archive directory didn't exist; with `set -o pipefail`, the `find | head` pipeline exits non-zero on missing directories, causing immediate script exit via `set -e` before error messages could output. Add an archive directory existence check before running `find`; use the `if ! var=$(func)` pattern instead of `$?` check for `set -e` safety; add 5 unit tests for `osc_find_change_dir` covering all scenarios; fix the pre-commit test hook regex to match files within the scripts directory; make the e2e version test resilient with a semver regex. Bump versions: `osc-iterations` 0.2.2, `osc-log` 0.3.2, `osc-state` 0.3.1.

## [0.8.2] - 2026-03-02

### Changed

- Reorder workflow phases: Self-Reflection before Archive. Swap PHASE5 and PHASE6 (Self-Reflection → PHASE5, Archive → PHASE6); update agent assignments (analyzer for reflection, maintainer for archive); add `osc_find_change_dir()` to detect changes in active or archived locations; update `osc-*` lib scripts to use archive-aware change detection; add mandatory commit sections to PHASE2 and PHASE3 command files; update state file lifecycle documentation in `AGENTS.md`.

## [0.8.1] - 2026-03-02

### Changed

- Update `.gitignore` to track archived workflow state files (so post-PHASE6 state is committed for forensics).
- Disable the `question` tool for autonomous workflow agents. Prevents `openspec-analyzer`, `openspec-builder`, and `openspec-maintainer` from asking user questions during autonomous execution, ensuring non-blocking operation. Bump versions: `openspec-analyzer` 0.1.3 → 0.1.4, `openspec-builder` 0.1.3 → 0.1.4, `openspec-maintainer` 0.1.2 → 0.1.3.
- Refactor JSON handling in lib scripts with shared functions. Add `osc-common` with safe JSON functions (`length`, `update`, `append`); update `osc-log`, `osc-iterations`, `osc-state`, `osc-ctx` to use the shared functions; move large content to separate files in phase2 / phase6; add PHASE5 archive verification for report files; add 18 unit tests for `osc-common`.

### Fixed

- Fix version check to use relative paths for `git show`. The check was using absolute paths with `git show HEAD:`, which always failed silently and returned empty previous versions, causing the check to incorrectly report "ok" instead of "needs_bump".

## [0.8.0] - 2026-03-01

### Added

- Add explicit phase-to-agent mapping in the autonomous workflow: a per-phase dispatch table that locks which of the 3 specialized agents each phase routes to.

### Changed

- Centralize resource versioning in manifest files. Move version tracking from individual file frontmatter to centralized `manifest.json` files per platform (opencode / claude). The manifest serves as the single source of truth for resource versions: add `manifest.json` with a version registry per resource type; remove `metadata.version` / `author` from skill, command, and agent files; update `version:check` / `version:update` tasks to use manifest-based lookups; update the installer to copy the manifest and validate deployment; update agent definitions to use the `permission` block instead of `tools`.
- Narrow the E2E test scope to full-workflow only (drop redundant per-phase E2E suites that share infrastructure with the full flow).
- Review and iterate artifacts for `add-hello-script` (first fixture to exercise the orchestrator end-to-end).

### Fixed

- Fix YAML frontmatter indentation in skill files (initial manifest extraction surfaced off-by-one indentation in the auto-generated frontmatter).

## [0.7.1] - 2026-03-01

### Added

- Add "Tools Available" sections to command files. Reference tables for each phase command (`openspec-phase0` through `phase6`) listing which upstream CLI tools and local `osc-*` scripts the phase can invoke; remove inline CLI comments (now redundant with the header context).
- Add E2E tests for the `openspec-auto` workflow. 14 E2E tests across 3 tiers (mechanism, single-phase, full-workflow); E2E helpers with real-time output streaming via BATS FD 3; `add-hello-script` fixture for full-workflow testing; mise tasks `test:e2e` and `test:mechanism`; fix 2 unit tests with incorrect error-message expectations.
- Add integration tests for `osc-*` script workflows: `phase-workflow` (state transitions across phases), `completion-workflow` (completion flow and cleanup), `git-integration` (baseline and git status integration), `change-lifecycle` (full create → complete → archive flow). New helpers `assert_phase_equals`, `assert_change_complete`; mise config separates `test:unit` and `test:integration` tasks.
- Add unit tests for `osc-*` lib scripts. Bats testing framework and test tasks in mise; test helpers and minimal change fixtures; 69 tests covering `osc-state`, `osc-iterations`, `osc-log`, `osc-git`, and `osc-ctx`.

### Changed

- Extend version tracking to phase commands and lib scripts. Add `openspec-phase*.md` patterns to version check and the pre-commit hook; add MANIFEST.json tracking for lib-script versions; add `get_version_json()` for extracting versions from JSON files; apply retroactive version bumps for changes missed by the detection gap; complete MANIFEST.json with missing `osc-*` scripts.
- Start phase iterations at 1 instead of 0. `osc-phase`: initialize iteration to 1 on phase advance; `openspec-auto`: move counter increment to loop start; remove redundant `write_state` calls with iteration 0.
- Refactor `openspec-auto` validation into composable `osc-*` scripts. Extract `validate_skills`, `validate_commands`, `validate_json`, `validate_change_dir`, `validate_archive`, `validate_iterations`, `validate_completion` into `osc-validate`; extract phase transitions (`current`, `next`, `advance`) into `osc-phase`; extract baseline tracking (`record`, `get`) into `osc-baseline`; extract completion status (`check`, `get`, `set`) into `osc-complete`; update `openspec-auto` to delegate to the new scripts; add 83 unit tests for all new scripts and 23 schema-validation tests for JSON output consistency (152 tests passing across 10 test files).

### Fixed

- Fix phase transition and artifact review in the autonomous workflow. `openspec-auto`: call `osc-phase advance` to persist state changes; `openspec-phase0`: enforce immediate artifact fixes in the same invocation.

### Removed

- Remove flaky stdin-input tests from `osc-iterations` and `osc-log` (tests incorrectly expected "invalid_json" but scripts check `-t 0` first, returning "no_input" when stdin is a terminal as in BATS run context; since this is an edge-case guard rarely hit in production, remove rather than fix).
- Remove single-phase E2E tests and fix iteration assertions: delete unused `single-phase.bats`; update test expectations (iterations start at 1, not 0).

## [0.7.0] - 2026-02-28

### Fixed

- Fix phase command paths and add `.gitignore` force overwrite. Correct the `osc-ctx` path from `opencode/` to `.opencode/` in all phases; add a force flag to `update_gitignore` for the update command; bump patch versions on all phase commands.

## [0.6.3] - 2026-02-28

### Changed

- Enforce mandatory commits in autonomous workflow phases. PHASE1: remove conflicting skill-deviation instruction, inline the commit protocol as a MANDATORY step. PHASE0 / 4 / 5: move commits to MANDATORY END sections. Add commit-tracking fields (`commits_made`, `commit_hash`) to decision logs. Fixes agents skipping commits due to non-mandatory placement.
- Refactor the autonomous workflow to use lib scripts and JSON-only logging. All phase commands now use `osc-state`, `osc-log`, `osc-iterations`, `osc-ctx`; `osc-log` generates JSON only (removed markdown output); prevents `/tmp` permission rejections from inline `jq` commands; updates agent guidelines to reference `osc-log` instead of `decision-log.md`.

## [0.6.2] - 2026-02-28

### Removed

- Remove the slash prefix from command invocation in `openspec-auto`. Pass command names directly to the AI binary without the `/` prefix; sync version to 0.5.2 (header and variable).

## [0.6.1] - 2026-02-28

### Fixed

- Fix command flag syntax in `openspec-auto`. The `--command=` syntax caused `opencode run` to exit immediately without executing the agent; use a space separator instead.

## [0.6.0] - 2026-02-28

### Changed

- Consolidate resources to OpenCode and add phase commands. Remove Claude-specific agents and scripts (now OpenCode-only); restructure paths to tool-level directories (`<tool>/` not `<tool>/skills/`); add phase-specific commands for the autonomous workflow; add lib scripts (`osc-*`) for state-management utilities; enhance `openspecx` with version validation and `generatedBy` injection.
- Refactor version checking to state-driven auto-detection. Add a state file for version-check results with JSON output format; integrate AI analysis for ambiguous bump-type detection; extract shared logic to `lib/common.sh` and `lib/detect-bump.sh`; simplify `.gitignore` to a single `version-state.json` pattern; reset agent versions to 0.1.0 for a clean baseline.
- Extend version tracking to autonomous workflow components. Add version tracking for `openspec-auto` script and agent definitions; refactor version tasks to handle both YAML (md) and Bash formats; fix OpenCode agent invocation with a temp file for multi-line prompts; bump version to 0.4.1 across all autonomous workflow files.

### Fixed

- Fix installer bugs and differentiate core vs extended content. Fix `cp` error when copying the scripts directory (use `find` for files only); fix `generatedBy` duplication by always placing it in the metadata block; core content copied verbatim without metadata modification; standardize command frontmatter to use the metadata block; remove deprecated `mode: subagent` and `subtask` fields from agents / commands.
- Fix phase-completion signaling in the autonomous workflow. Separate phase-level signaling (`state.json.phase_complete`) from workflow-level signaling (`complete.json`) to prevent premature workflow termination after each phase. Add `phase_complete` field to `state.json` with check / clear functions; remove `check_complete_signal()` and use `check_phase_complete()` instead; update all agent definitions to set `phase_complete: true` when done; document state-file architecture with lifecycle in `AGENTS.md`. Script version: 0.4.1 → 0.4.2; agent versions: 0.1.0 → 0.1.1.

## [0.5.1] - 2026-02-27

### Fixed

- Fix OpenCode agent invocation with multi-line prompts. The `opencode run` command expects message arguments as an array, not a single string; when prompt content contains newlines (from agent definitions), argument parsing fails and shows help instead. Write prompt content to a temp file; pass the file path with `-f` flag; clean up the temp file after execution.

## [0.5.0] - 2026-02-27

### Added

- Add the `--with-core` flag and fix command directory naming. Optional `--with-core` flag deploys core OpenSpec skills alongside extended; fix directory path (`command/` → `commands/` to match OpenSpec v1.2.0); handle nested Claude `commands/opsx/` structure correctly; remove reference to the non-existent `update-research` skill.

## [0.4.2] - 2026-02-27

### Changed

- Configure `sync-core` for the OpenSpec v1.2.0 custom profile. Write `config.json` with all 11 workflows before init; use the `--profile custom` flag to enable the full workflow set; update `AGENTS.md` to reflect v1.2.0 structure and all workflows; fix the OpenCode directory path from `command/` to `commands/`.

### Removed

- Remove the `model` field from OpenSpec agent definitions (let each runtime use its configured default).

## [0.4.1] - 2026-02-17

### Fixed

- Fix gitignore patterns to use recursive wildcards. Change state file patterns from single-level (`*`) to recursive (`**`) matching to correctly ignore nested directory structures.

## [0.4.0] - 2026-02-17

### Changed

- Refactor the autonomous workflow to use specialized phase agents. Replace the monolithic `prompt-template.md` with 3 focused agent definitions: `analyzer` handles PHASE0 / 2 / 6 (review, verify, reflect); `builder` handles PHASE1 (implementation); `maintainer` handles PHASE3 / 4 / 5 (docs, sync, archive). Update `openspecx` to deploy agents to `.<tool>/agents/`; bump version to 0.4.0.

## [0.3.4] - 2026-02-17

### Changed

- Make model selection optional in `openspec-auto`. Remove the hardcoded default model to respect each CLI's configured default (settings files, environment variables, subscription tier). `MODEL` defaults to empty instead of `zai-coding-plan/glm-4.7`; `--model` flag is only passed to the CLI when explicitly provided; the banner only shows the Model line when set.

## [0.3.3] - 2026-02-17

### Added

- Add graceful interrupt handling to the `openspec-auto` script. Trap `SIGINT` and `SIGTERM` signals during agent execution; terminate child AI processes on interrupt; preserve state files for resumption after interruption; use `timeout --foreground` for proper signal propagation.

### Changed

- Automate phase transitions and add a commit protocol for the autonomous workflow. The script now manages phase transitions automatically via `advance_phase()`; add a commit-protocol section with pre-commit-hook guardrails; require an archive commit as the PHASE5 completion step.

## [0.3.2] - 2026-02-17

### Added

- Add gitignore management for autonomous workflow state files. Add `update_gitignore()` to `openspecx` with marker-based entries; make the PHASE0 commit conditional on artifact modifications; fix state-file location docs to match implementation.

## [0.3.1] - 2026-02-16

### Changed

- Refactor skill frontmatter description to single-line format (previously multi-line) so the picker reliably matches user input.

## [0.3.0] - 2026-02-16

### Added

- Add the autonomous implementation workflow. The `openspec-auto` script runs a 7-phase loop (Artifact Review → Implementation → Review → Maintain-Docs → Sync → Archive → Self-Reflection). Extend `openspecx` installer to deploy scripts to platform directories; add documentation in `AGENTS.md` and `README.md`; support resuming, dry-run, progress tracking, and CI / CD integration.

### Changed

- Restructure `openspec-concepts` with anti-patterns and JSON schemas. Add comprehensive anti-patterns reference (16 patterns with recovery); enhance `cli-reference` with complete TypeScript JSON schemas; restructure `SKILL.md` with TL;DR, philosophy narrative, AI behavior guide; add Related Documentation sections to all reference files; fix broken cross-reference paths in reference files; delete outdated command files (`concepts.md`); bump version to 0.3.0. Improves token efficiency (630 → 495 lines) and adds comprehensive guidance for AI agents working with OpenSpec-empowered projects.

## [0.2.1] - 2026-02-14

### Added

- Add OPSX extension commands and a comprehensive concepts guide: `/opsx:changelog`, `/opsx:modify`, `/opsx:review`, `/opsx:verify-tests`, `/opsx:maintain-docs`, `/opsx:concepts`. Expand the `openspec-concepts` skill with full lifecycle, decision guidance, and CLI reference; add `cli-reference.md` and `opsx-lifecycle.md` reference documentation; update extension skills with detailed workflows and guardrails.
- Add OpenSpec core reference documentation: `openspec-opsx.md` (OPSX workflow overview, fluid iterative approach), `openspec-concepts.md` (philosophy, specs, changes, delta specs, schemas), `openspec-workflows.md` (patterns for explore, quick feature, parallel work), `openspec-commands.md` (AI slash commands), `openspec-cli.md` (terminal commands). Update `AGENTS.md` index with local cross-references.
- Add comprehensive guides for building OpenSpec-style skills and commands. `building-openspec-skills.md`: philosophy, frontmatter fields, body structure patterns, CLI integration, user interaction patterns, validation checklist. `building-openspec-commands.md`: command / skill distinction, naming conventions, argument patterns, transition patterns, platform differences. Update `AGENTS.md` to document the new guide files.
- Add OpenSpec core skills sync infrastructure. Add mise `sync-core` task to pull official OpenSpec skills from upstream; add `openspec-core/AGENTS.md` documentation for core workflow skills; configure `.gitignore` to track only documentation, not generated files; update project `AGENTS.md` to distinguish core vs extended skills.

### Changed

- Extend version tracking to command files with paired updates. Add `metadata.version` to Claude commands for consistency with OpenCode; extend `version:check` to validate both skill and command files; refactor `version:update` to update all 4 paired files by concept name; update the pre-commit hook to match command file patterns.

## [0.2.0] - 2026-02-13

### Added

- Add `install` and `update` subcommands to the `openspecx` CLI. `install`: add missing skills, skip existing; `update`: force-update all skills, overwrite existing; update documentation to reflect the new command structure.

### Changed

- Standardize skill frontmatter and reference documentation. Remove the platform-specific `compatibility` field (skills are agnostic); add References sections to skills with existing reference files; fix the skill path typo in `opsx-modify` command.

## [0.1.0] - 2026-02-13

### Added

- Add a version tracking system for skill management. Mise tasks for git tagging (`tag`) and version bumping (`version:update`); pre-commit hooks for shellcheck and version-bump enforcement; the installer reads version from git tags and injects the `generatedBy` field; standardize metadata (`author`, `version`, `license`) across all `SKILL.md` files; rename skills to plural form (`modify-artifacts`, `review-artifacts`).
- Add GitLab CI for GitHub mirroring.
- Add autonomous OpenCode commands for skill invocation: `opsx-concepts` (display OpenSpec framework overview), `opsx-modify` (modify artifacts with dependency tracking), `opsx-review` (review artifacts for quality and completeness), `opsx-maintain-docs` (update `AGENTS.md` and `CLAUDE.md`), `opsx-changelog` (generate changelogs from archived changes), `opsx-verify-tests` (review test coverage for spec requirements). Commands provide concise interfaces with inference, auto-selection, and `AskUserQuestion` for ambiguous cases.
- Add documentation maintenance, changelog, and test-compliance skills: `openspec-maintain-ai-docs` (keep `AGENTS.md` / `CLAUDE.md` synchronized), `openspec-generate-changelog` (generate Keep a Changelog from archives), `openspec-review-test-compliance` (verify test coverage for spec changes).
- Add the `openspec-review-artifact` skill for artifact quality validation.
- Add OpenSpec-extended with skills for Claude Code and OpenCode. Install script for copying skills to `.claude/skills/` and `.opencode/skills/`; `OpenSpec-concepts` and `openspec-modify-artifact` skills for both platforms; `update-research` skill for maintaining research documentation accuracy; research docs covering platform-specific capabilities and constraints.

### Changed

- Rename the `commands/` directory to `command/` (singular) — corrected in a later release to match upstream OpenSpec's plural form.
- Make skill frontmatter platform-specific. Claude Code: remove OpenCode-only fields, add `argument-hint` and `allowed-tools`; OpenCode: fix `compatibility` from tool requirement to platform identifier, add `argument-hint`; remove incorrectly installed `update-research` skill from `.opencode/`.
- Initial project setup (skeleton repo, install script, version management, basic skills).

### Fixed

- Fix command directory creation in `openspecx` (the `mkdir` for the new command directory was missing the parent creation step).
