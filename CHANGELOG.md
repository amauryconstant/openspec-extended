# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).


## [Unreleased]


## [1.10.7] - 2026-09-16

### Changed

- Eliminate redundant backups and nested core orphans on install

## [1.10.6] - 2026-09-16

### Fixed

- Fix inline /opsx-* leakage in installed skill bodies

## [1.10.5] - 2026-09-15

### Changed

- Document per-adapter fields and add cursor to the test matrix
- Render extended slash commands as skill mirrors for skills-only adapters
- Wire purge and validate hooks for skills-only adapters
- Expand ToolAdapter surface for skills-only adapters

## [1.10.4] - 2026-09-14

### Changed

- Rename canonical source tree from opencode/ to canonical/
- Align osx resources to v1.13.0 naming and dispatch contract

## [1.10.3] - 2026-09-14

### Changed

- Make bats orchestrate callers non-interactive by default
- Honour pre-resolved state.change_dir across engine entry points

## [1.10.2] - 2026-09-14

### Added

- Add build dependency to test:mechanism:bats

### Changed

- Move mise build task into standalone shell script
- Consolidate AGENTS.md cross-cutting rules, fix stale tables, add workflows
- Consolidate duplicated test bodies via parametrization

### Removed

- Drop bats_parallel.py; run test:mechanism:bats sequentially
- Remove Phase 2A no-op sentinels from resource contract suite

## [1.10.1] - 2026-09-13

### Changed

- Cut bats E2E from 215s to 24s and split pytest markers
- Speed up test suite from ~450s to ~120s via parallelization

## [1.10.0] - 2026-09-13

### Added

- Add pre-commit guard against platform hardcodes
- Add GenericPrintRunner skeleton for headless CLI tools
- Add per-tool adapter registry skeleton

### Changed

- Anchor shared-references pool to canonical opencode path
- Reformat Python source with ruff format
- Expand hardcode-check for new dispatch axes
- Single canonical source, per-adapter deploy
- Pin single-tool exit-code preservation
- Accept comma-separated tool targets in install and update
- Document the adapter registry and per-adapter rendering
- Drive lib/osx platform helpers from the adapter registry
- Derive ai_binary and install hints from REGISTRY
- Route detect_runner through REGISTRY, plumb adapter into runners
- Wire cli.py tool dispatch through the per-tool adapter registry

### Removed

- Remove pre-registry references and completed Phase 2 plan
- Remove unused target_dir in _install_one_tool

## [1.9.1] - 2026-09-12

### Changed

- Extract OpenSpec contract surface to path-glob rule, retire docs/
- Consolidate AGENTS.md files into hub-and-domain layout

### Removed

- Delete research/ folder of stale upstream mirrors

## [1.9.0] - 2026-09-11

### Changed

- Align orchestrator surface with OpenSpec v1.13.0
- Migrate OpenSpec subtree to orchestrator/core/source
- Squashed 'orchestrator/core/source/' changes from a0ddb60d..9d4e5974
- Standardize tmpdir cleanup in CI and tests
- Normalize remaining openspec-core references across docs and tests
- Migrate sync-core task to orchestrator/core subtree prefix

## [1.8.0] - 2026-09-11

### Added

- Add osx instructions archive, schema fork-diff, validate archived
- Add CLI passthroughs and subcommand mirrors for upstream v1.5+
- Add env-var propagation, archived sweep, and operation guidance in CLI

### Changed

- Realign release version bump with source/ relocation
- Split manifests per side and align documentation
- Rewrite v1.6 review/modify tests for post-split resource tree
- Consolidate osx-commit format examples into SKILL.md
- Rename openspec-core/ paths to orchestrator/core/ across docs
- Update test suite for orchestrator/skills dual-tree layout
- Migrate skills-side utilities, retire deprecated resources, add docs
- Migrate orchestrator-side resources into orchestrator/resources/ tree
- Update sync-mirrors task for dual-tree architecture
- Relocate CLI engine and OpenSpec core into orchestrator/ tree
- Bring contract suite and bats tests up to v1.11.0 surface
- Document post-v1.7.0 contracts in review-modify integration plan
- Consolidate osx-changelog and osx-maintain-docs slash commands
- Track external writing-great-skills symlink under .agents/
- Adopt v1.11.0 contract surface across skills and docs
- Wire retire-capabilities metadata and planning gate into orchestrator
- Reconcile extended side with OpenSpec core v1.11.0
- Squashed 'openspec-core/source/' changes from 4e16790d..a0ddb60d

### Removed

- Drop dangling examples/ refs from osx-commit standards

## [1.7.3] - 2026-08-03

### Changed

- Substitute resource tokens at deploy time
- Dual-emit slash commands on Claude as skills

## [1.7.2] - 2026-08-03

### Changed

- Install all 12 canonical core workflows via --with-core

## [1.7.1] - 2026-07-31

### Changed

- Package shared references into each skill at deploy

## [1.7.0] - 2026-07-31

### Changed

- Consolidate osx command workflow guidance
- Consolidate shared conventions across osx skills
- Clarify skill triggers and disable automatic changelog invocation
- Generate Claude mirror from OpenCode source via token substitution
- Reconcile stale osx/osc resources during update

## [1.6.0] - 2026-07-31

### Changed

- Bump pytest, pyinstaller, and annotated-doc in uv.lock
- Gate autonomous resources behind --with-autonomous flag

## [1.5.0] - 2026-07-31

### Changed

- Sync resources, library, and CLI with OpenSpec core v1.7.0
- Reformat type hints and import order (separate from v1.7.0 sync)
- Squashed 'openspec-core/source/' changes from e1b51d11..4e16790d

## [1.4.0] - 2026-07-30

### Changed

- Refresh workflow docs and bump versions to 1.3.0 / 0.2.2
- Re-resolve change path for cleanup and split preflight checks
- Halt on phase-written blockers and cross-check deployed manifest
- Wire store/schema env propagation and harden subprocess teardown
- Halt orchestration for pending phase routes
- Align osx state transition docs with named-option CLI
- Decouple installer test from fixture release version
- Restructure audit skill to separate process from project state

### Fixed

- Fix Claude command validation for unprefixed filenames

## [1.3.0] - 2026-07-23

### Added

- Add osx-reviewer agent, autonomous-mode gates, and full slash commands
- Add osx-commit to REQUIRED_SKILLS and contract test marker
- Add PID callback and process-group termination for live AI subprocesses
- Add osx-reviewer agent and reassign PHASE2/PHASE5 dispatch
- Add audit command and skill for openspec integration audits

### Changed

- Align docs and framework versions with the 1.2.1 release
- Wire OSX_AUTONOMOUS=1 and tighten validation contracts
- Centralize version on __version__ and add atomic state_io module
- Make install --with-core non-destructive with snapshot and restore-core
- Enforce openspec >= 1.6.0 at orchestrator startup
- Stub skills and bump install fixture for mechanism test
- Adapt orchestrator and CLI to openspec v1.6+ contracts
- Move transient file cleanup from phase6 to orchestrator
- Adopt schema-agnostic review/modify contract from openspec-update-change
- Squashed 'openspec-core/source/' changes from 546224e..e1b51d1

### Fixed

- Fix dead /osx-* slash-command references in skills and commands

## [1.2.1] - 2026-07-22

### Added

- Add hermetic install fixture and wire bats to build

### Changed

- Make resource path test independent of checkout name
- Align sync-core with current OpenSpec generation

## [1.2.0] - 2026-07-15

### Added

- Add E2E_SKIP_ORCHESTRATOR support for archive replay
- Add clean mise task to remove PyInstaller artifacts
- Add dogfooded orchestrator example and update README
- Add unified CLI passthrough and osx schema sub-app
- Add schema-aware orchestration with 4-level resolution precedence
- Add pyyaml dependency for schema-aware orchestration
- Add Claude Code phase commands and platform-aware resource resolution
- Add AI runner abstraction for opencode and claude dispatch
- Add OpenSpec v1.5.0 store support across CLI, lib, and orchestrator

### Changed

- Update OpenSpec version requirement to v1.5.0+
- Drive sync-core from in-tree git subtree at latest release tag
- Thread project_root through orchestrator validators and sync docs
- Clean up unused imports in tests and document test files
- Document CLI surface, orchestrator state machine, and troubleshooting
- Squashed 'openspec-core/source/' content from commit 546224e
- Refresh docs for OpenSpec v1.5.0 stores

### Fixed

- Fix version:check to detect manifest entries under nested command paths

### Removed

- Remove dogfooded orchestrator example and README section

## [1.1.0] - 2026-06-19

### Changed

- Split version task ownership between release and version:check
- Mount osx tool as binary subcommand, drop deployed wrappers

## [1.0.3] - 2026-06-17

### Fixed

- Fix installed manifest top-level version defaulting to 'unknown'

## [1.0.2] - 2026-06-17

### Fixed

- Fix release workflow combining SHA256SUMS

## [1.0.1] - 2026-06-17

### Changed

- Bump release workflow actions to Node 24

### Removed

- Drop darwin-x86_64 from release build matrix

## [1.0.0] - 2026-06-17

### Added

- Add shell-argument safety guard to decision log writes
- Add per-directory AGENTS.md docs and exclude from binary
- Add pytest marker system and convert remaining BATS tests to Python
- Add Python rewrites of openspec-extended and osx-orchestrate

### Changed

- Sync uv.lock in release and version:update tasks
- Wire GitHub Actions to build and publish release tarballs
- Migrate add-hello-script fixture to delta-spec convention
- Extract osx-workflow skill from osx-concepts
- Document osx lib verb vocabulary and accept show/list aliases
- Stream agent subprocess output to terminal in real time
- Refactor orchestrator to use in-process osx library
- Wire bats suites into default test task
- Miscellaneous configuration and dependency updates
- Update documentation with E2E strategy and build/release docs
- Improve install.sh with BASE_URL override and platform detection
- Rename CLI command run to orchestrate and split skills list
- Migrate E2E tests from pytest to bats
- Convert version management scripts from Python to Bash
- Refactor CLI commands to hide internal osx command
- Refactor pre-commit hooks and test configuration
- Restructure AGENTS.md for Python implementation
- Refactor CLI tools from Bash to Python
- Convert manifest storage from JSON to TOML
- Refactor version management from Bash to Python
- Complete Bash-to-Python rewrite with 61 new integration tests

### Fixed

- Fix version:check to detect manifest version bumps for resources
- Fix core resource renaming and add post-deploy validation
- Fix orchestrator color output and script deployment in frozen binary
- Fix Python 3.12 compatibility and expand lint/typecheck coverage - Use Python 3.12-compatible exception syntax: except (X, Y): instead of except X, Y: - Change requires-python from >=3.14 to >=3.12 in pyproject.toml and uv.lock - Add explicit type annotations in osx lib script (dict[str, Any]) - Expand mise lint and typecheck to include osx script and mise version scripts - Rename ambiguous variable l to line in detect.py
- Fix TOML manifest parsing after JSON→TOML migration

### Removed

- Remove unused AGENTS.md file

## [0.19.0] - 2026-06-10

### Changed

- Bump openspec-core version note to v1.4.1

### Fixed

- Fix sync-core to allow esbuild postinstall under pnpm 10.26+

### Removed

- Remove opencode singular command/ workaround

## [0.18.2] - 2026-03-18

### Added

- Add tests for installer validation and core rename logic

### Fixed

- Fix orchestration logging to capture agent output and archive correctly

## [0.18.1] - 2026-03-16

### Fixed

- Fix installer validation and core command handling

## [0.18.0] - 2026-03-16

### Changed

- Refactor installer for version-aware updates

### Fixed

- Fix core resource renaming for Claude and document original names

## [0.17.2] - 2026-03-16

### Changed

- Refactor E2E tests to run workflow once with 28 verification tests
- Clarify PHASE6 completion detection in documentation

## [0.17.1] - 2026-03-16

### Changed

- Refactor osx-concepts skill for AI agent audience - Add skill taxonomy distinguishing core (osc-*) from extended (osx-*) skills - Add enhancement patterns showing how extended skills augment core workflow - Remove all slash command syntax (/osx:*) - use skill names instead - Replace command table with skill reference table - Delete osx-lifecycle.md (command-focused, wrong audience) - Add autonomous-workflow.md reference for orchestrator details - Condense from 593 to 425 lines with progressive disclosure to references

## [0.17.0] - 2026-03-15

### Added

- Add osx-commit skill with standardized phase command invocation

### Fixed

- Fix PHASE6 log archiving to use archive directory path The log file was being moved to the change directory instead of the archive directory. Now queries the osx lib for the correct archive path before moving the log file.

## [0.16.0] - 2026-03-13

### Security

- Add security validation and safety improvements to install.sh

## [0.15.4] - 2026-03-13

### Added

- Add uv sync to tag task after pyproject.toml version update

### Changed

- Bump command versions for osc→osx tool alignment

## [0.15.3] - 2026-03-13

### Changed

- Push main branch when creating release tags

### Fixed

- Fix version detection to use manifest.json

## [0.15.2] - 2026-03-13

### Fixed

- Fix resource deployment to skip existing files during install

## [0.15.1] - 2026-03-13

### Changed

- Relocate lib-scripts docs to resources/opencode/scripts/lib

### Fixed

- Fix PHASE6 log file archiving validation
- Fix validation to support nested spec dirs and display errors

## [0.15.0] - 2026-03-13

### Changed

- Rename resources to osx-* prefix for extended variants

## [0.14.0] - 2026-03-12

### Added

- Add run subcommand to openspecx for workflow execution

### Changed

- Continue osc tool migration with baseline and phase domains
- Complete osc tool migration with ctx and git domains
- Replace JSON-heavy bash scripts with unified Python CLI tool - Add osc tool (998 lines) replacing osc-state, osc-iterations, osc-log, osc-complete, osc-validate - Add 87 unit tests for osc tool (pytest) - Update openspec-auto to use osc via run_osc() wrapper - Add uv integration for Python dependency management - Update mise tasks: postinstall runs uv sync, test:unit:python uses uv run pytest - Add pyproject.toml version bumping to tag task - Track osc in manifest.json for version checking - Update installer to deploy osc Python tool - Read osc version from manifest.json instead of hardcoded constant
- Improve the formatting of the README

### Fixed

- Fix phase progression and osc command compatibility in autonomous workflow

## [0.13.2] - 2026-03-05

### Added

- Add log archiving and fix agent temp directory permissions

## [0.13.1] - 2026-03-05

### Fixed

- Fix PHASE6 workflow issues in openspec-auto - osc-phase: return error for archived changes without state.json - openspec-auto: skip show_progress after PHASE6 (state deleted) - openspec-auto: remove duplicate "Agent invocation" log - openspec-phase6.md: update logs before commit (was leaving uncommitted changes) - Add test for archived change without state.json
- Fix output capture race condition in E2E streaming helper

## [0.13.0] - 2026-03-05

### Added

- Add log file output and short CLI flags to openspec-auto

### Changed

- Improve openspec-auto logging with separate verbose mode

### Fixed

- Fix --from-phase agent execution failure in openspec-auto

## [0.12.1] - 2026-03-04

### Fixed

- Fix phase transition bug causing premature exit with set -e - Use conditional pattern for check_transition to handle empty result - Add capture_optional helper for safe optional value capture - Document function return conventions (check_* vs get_* functions) - Add 21 tests covering phase transition scenarios

## [0.12.0] - 2026-03-04

### Added

- Add explicit phase transitions and fix PHASE6 archive cleanup
- Add manifest.json version sync to tag task

## [0.11.0] - 2026-03-04

### Added

- Add demo/ to gitignore
- Add openspec/ to gitignore to prevent runtime state commits

### Changed

- Enable /tmp access for autonomous agents
- Restructure PHASE6 for atomic execution and clarify iteration limits

### Fixed

- Correct openspec-auto version from 1.0.5 to 1.2.1

### Removed

- Remove accidentally committed openspec/changes runtime directory

## [0.10.0] - 2026-03-03

### Changed

- Bump openspecx version to 0.10.2 Version history analysis from git commits: - 0.9.0 → 0.9.1: Bash 3.2 compatibility - 0.9.1 → 0.10.0: Curl-based installer with --version/--help - 0.10.0 → 0.10.1: Symlink resolution fix - 0.10.1 → 0.10.2: Error handling fix
- Enhance tag task with README version sync and dry-run mode
- Update repository URLs to amauryconstant/openspec-extended

## [0.9.2] - 2026-03-03

### Fixed

- Fix error handling for invalid tool argument

## [0.9.1] - 2026-03-03

### Changed

- Extend version check to cover all resources and root scripts

### Fixed

- Fix install script symlink resolution and repository paths
- Fix version check to process script files after resources

## [0.9.0] - 2026-03-03

### Added

- Add GitHub Actions workflow for automated releases
- Add curl-based installer with script version tracking

### Changed

- Refactor shell scripts for Bash 3.2 compatibility

### Fixed

- Fix version check for first-time script versioning
- Fix PHASE6 archive loop and standardize phase names

## [0.8.5] - 2026-03-03

### Fixed

- Fix workflow bugs in autonomous implementation system

## [0.8.4] - 2026-03-02

### Added

- Add blocker handling to autonomous workflow phases

## [0.8.3] - 2026-03-02

### Fixed

- Fix osc_find_change_dir silent exit with pipefail

## [0.8.2] - 2026-03-02

### Changed

- Reorder workflow phases: Self-Reflection before Archive

## [0.8.1] - 2026-03-02

### Changed

- Update gitignore to track archived workflow state files
- Disable question tool for autonomous workflow agents
- Refactor JSON handling in lib scripts with shared functions

### Fixed

- Fix version check to use relative paths for git show

## [0.8.0] - 2026-03-01

### Added

- Add explicit phase-to-agent mapping in autonomous workflow

### Changed

- Centralize resource versioning in manifest files
- Narrow E2E test scope to full-workflow only
- Review and iterate artifacts for add-hello-script

### Fixed

- Fix YAML frontmatter indentation in skill files

## [0.7.1] - 2026-03-01

### Added

- Add Tools Available sections to command files
- Add E2E tests for openspec-auto workflow
- Add integration tests for osc-* script workflows
- Add unit tests for osc-* lib scripts

### Changed

- Extend version tracking to phase commands and lib scripts
- Start phase iterations at 1 instead of 0
- Refactor openspec-auto validation into composable osc-* scripts

### Fixed

- Fix phase transition and artifact review in autonomous workflow

### Removed

- Remove flaky stdin input tests from osc-iterations and osc-log
- Remove single-phase E2E tests and fix iteration assertions

## [0.7.0] - 2026-02-28

### Fixed

- Fix phase command paths and add .gitignore force overwrite

## [0.6.3] - 2026-02-28

### Changed

- Enforce mandatory commits in autonomous workflow phases
- Refactor autonomous workflow to use lib scripts and JSON-only logging

## [0.6.2] - 2026-02-28

### Removed

- Remove slash prefix from command invocation in openspec-auto

## [0.6.1] - 2026-02-28

### Fixed

- Fix command flag syntax in openspec-auto

## [0.6.0] - 2026-02-28

### Changed

- Consolidate resources to OpenCode and add phase commands
- Refactor version checking to state-driven auto-detection
- Extend version tracking to autonomous workflow components

### Fixed

- Fix installer bugs and differentiate core vs extended content
- Fix phase completion signaling in autonomous workflow

## [0.5.1] - 2026-02-27

### Fixed

- Fix OpenCode agent invocation with multi-line prompts

## [0.5.0] - 2026-02-27

### Added

- Add --with-core flag and fix command directory naming

## [0.4.2] - 2026-02-27

### Changed

- Configure sync-core for OpenSpec v1.2.0 custom profile

### Removed

- Remove model field from OpenSpec agent definitions

## [0.4.1] - 2026-02-17

### Fixed

- Fix gitignore patterns to use recursive wildcards

## [0.4.0] - 2026-02-17

### Changed

- Refactor autonomous workflow to use specialized phase agents

## [0.3.4] - 2026-02-17

### Changed

- Make model selection optional in openspec-auto

## [0.3.3] - 2026-02-17

### Added

- Add graceful interrupt handling to openspec-auto script

### Changed

- Automate phase transitions and add commit protocol for autonomous workflow

## [0.3.2] - 2026-02-17

### Added

- Add gitignore management for autonomous workflow state files

## [0.3.1] - 2026-02-16

### Changed

- Refactor skill frontmatter description to single-line format

## [0.3.0] - 2026-02-16

### Added

- Add autonomous implementation workflow

### Changed

- Restructure openspec-concepts with anti-patterns and JSON schemas

## [0.2.1] - 2026-02-14

### Added

- Add OPSX extension commands and comprehensive concepts guide
- Add OpenSpec core reference documentation
- Add comprehensive guides for building OpenSpec-style skills and commands
- Add OpenSpec core skills sync infrastructure

### Changed

- Extend version tracking to command files with paired updates

## [0.2.0] - 2026-02-13

### Added

- Add install and update subcommands to openspecx CLI

### Changed

- Standardize skill frontmatter and reference documentation

## [0.1.0] - 2026-02-13

### Added

- Add version tracking system for skill management
- Add GitLab CI for GitHub mirroring
- Add autonomous OpenCode commands for skill invocation
- Add documentation maintenance, changelog, and test compliance skills
- Add openspec-review-artifact skill for artifact quality validation
- Add OpenSpec-extended with skills for Claude Code and OpenCode

### Changed

- Rename commands directory to command (singular)
- Make skill frontmatter platform-specific
- Initial project setup

### Fixed

- Fix command directory creation in openspecx
