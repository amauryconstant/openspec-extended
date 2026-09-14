---
paths:
  - "orchestrator/source/**"
  - "orchestrator/resources/canonical/**"
  - "tests/**"
---

# OpenSpec Contract Surface (v1.8.0–v1.13.0)

This file catalogues every v1.8.0–v1.13.0 contract the extended orchestrator depends on. Each entry has: (1) the contract, (2) the source version, (3) the consumer, (4) the operational note. Upstream context (changelog entries, design intent) lives in `orchestrator/core/AGENTS.md` and `orchestrator/core/source/CHANGELOG.md`; this file is the extended-side mirror.

`MIN_OPENSPEC_VERSION = (1, 13, 0)` — orchestrator refuses to start with older cores. The floor guarantees the v1.13.0 contract surface is available. `OPENSPEC_EXTENDED_NO_PLANNING_CORE=1` bypasses the core planning-status call; without it, falls back to a local file-existence check.

## 13.1 `isPlanningComplete` (v1.8.0+)

**Contract**: `openspec status --change <name> --json` returns `isPlanningComplete: bool` distinct from `isComplete`. `isPlanningComplete` is true when every non-skipped planning artifact exists; `isComplete` is a backward-compatibility alias that folds planning and implementation together.

**Consumer**: `validate_change_dir` library helper (`source/lib/osx.py:1450`) reads the field via `_fetch_planning_status` (`source/lib/osx.py:254`); engine wrapper at `source/orchestrator/engine.py:242` logs the source (`core` or `local-heuristic`) on success. Falls back to `_validate_change_dir_local` (`source/lib/osx.py:1559`) when the CLI is missing, the call fails, the version is below v1.8.0, or `OPENSPEC_EXTENDED_NO_PLANNING_CORE=1` is set.

**Operational note**: When the AI sees a pre-flight failure citing specific missing artifact ids, fetch those artifacts via `/opsx:continue <name>` — the local file check is a fallback, not the source of truth. The pre-flight surface is `planning_complete` (tri-state: `True` / `False` / `None`), not the raw core boolean; treat `None` as "we couldn't reach core; local-heuristic result follows in `missing`".

**Reference**: `source/lib/osx.py:1450`, `source/orchestrator/engine.py:242`. Tests: `tests/unit/test_validation_translator.py::TestValidateChangeDirPlanning`, `tests/contract/test_upstream_envelopes.py::TestStatusPlanning::test_status_includes_isPlanningComplete`. Authoritative core: `orchestrator/core/AGENTS.md` v1.8.0 highlights.

## 13.2 `retire_capabilities: true` (v1.8.0+)

**Contract**: A change with `retire_capabilities: true` in `.openspec.yaml` (alongside the mandatory `schema:`) declares that `openspec archive` may delete the capability's main spec if its last requirement is REMOVED. Without the marker, archive aborts with "Spec must have at least one requirement". Core additionally aborts when the emptied spec also holds content the merge cannot account for — the abort names the blocking lines and reports the marker as the way out (v1.10.0).

**Consumer**: `osx.read_change_metadata(change_dir)` (`source/lib/osx.py:2037`) reads `.openspec.yaml` once during pre-flight. The result is stashed on `OrchestratorState.retire_capabilities` (`source/orchestrator/engine.py:79`; set in `validate_change_dir` wrapper at `:262` and in `validate_archive` at `:324`). PHASE0's routing table (`orchestrator/resources/canonical/commands/osx-phase0.md`) routes the change to `/opsx:archive <name>` (skipping PHASE1–PHASE5) when the marker is set *and* planning is complete.

**Operational note**: An in-flight MODIFIED change against the retired capability will keep validating clean and then refuse to archive ("target spec does not exist; only ADDED requirements are allowed for new specs"). Close or rework that change alongside the retirement. The retirement is whole-file deletion: the marker is honored only when the emptied spec has nothing left but its title, `## Purpose`, and its requirement blocks — any `## Notes` section or comment under a requirement causes the abort to name those lines.

**Reference**: `source/lib/osx.py:2037`, `source/orchestrator/engine.py` (OrchestratorState.retire_capabilities), `orchestrator/resources/canonical/commands/osx-phase0.md` (routing table). Tests: `tests/unit/test_validation_translator.py::TestReadChangeMetadata`, `tests/integration/test_phase_workflow.py::test_validate_change_dir_stamps_retire_capabilities`, `tests/contract/test_upstream_envelopes.py::TestArchiveWithRetireCapabilities`.

## 13.3 `operations.{apply,archive}.guidance` (v1.7.0+)

**Contract**: `openspec/config.yaml` may declare per-operation advisory strings:

```yaml
schema: spec-driven
operations:
  apply:
    guidance:
      - "Always run unit tests after a milestone commit."
  archive:
    guidance:
      - "Move CHANGELOG.md entry above the v-next header."
```

The strings surface as `operationGuidance: string[]` in `openspec instructions apply|archive --json`. The operations supported are exactly `apply` and `archive`. Neither field is an enforceable check.

**Consumer**: `osx.fetch_operation_guidance(operation, project_root, store=None)` (`source/lib/osx.py:2193`) reads `openspec/config.yaml` directly. The orchestrator's `build_run_request` (`source/orchestrator/engine.py:545`) calls this helper only for PHASE1 (`operation="apply"`) and PHASE6 (`operation="archive"`) and passes the joined strings as `RunRequest.extra_prompt` (`source/orchestrator/runner.py:47`). Other phases ignore the guidance (the field stays `""`). The OpenCode runner attaches the prompt via `--file` (`runner.py:134`); the Claude runner prepends it to the slash-command prompt (`runner.py:179`).

**Operational note**: The guidance is **advisory**, not authoritative. Treat it as project context that shapes implementation choices; do not copy it verbatim into artifact files or commit messages. Don't confuse `operationGuidance` with `rules` — they share a YAML shape but mean different things.

**Reference**: `source/lib/osx.py:2193`, `source/orchestrator/runner.py:47`, `source/orchestrator/engine.py:545`. Tests: `tests/unit/test_schema_resolution.py::TestFetchOperationGuidance` (parser), `tests/integration/test_phase_workflow.py` line 1231 (orchestrator integration).

## 13.4 `show <change> --diff` (v1.11.0+)

**Contract**: `openspec show <change> --diff --json` renders each MODIFIED requirement as a unified diff against the requirement it replaces in the main spec; ADDED requirements print in full (no `diff` block); REMOVED print authored Reason/Migration; RENAMED print FROM/TO. `--json --diff` adds `diff` and `warning` fields to MODIFIED deltas only. Main specs resolve against the same root as the change.

**Consumer**: PHASE2 (REVIEW) fetches this payload during its MANDATORY CHECKPOINT step 3 (`orchestrator/resources/canonical/commands/osx-phase2.md`) and embeds it as a `## Requirement diff` appendix in `verification-report.md`. ADDED/REMOVED/RENAMED deltas appear in a separate `## Delta inventory` section; MODIFIED deltas with a `warning` field get a `## Verification warnings` section.

**Operational note**: The diff payload replaces the hand-rolled "what changed in this requirement?" prose that earlier versions of PHASE2 produced. Reviewers should still write their own narrative — the diff is supplementary context, not the report.

**Reference**: `orchestrator/resources/canonical/commands/osx-phase2.md`. Tests: `tests/contract/test_upstream_envelopes.py::TestShowDiffEnvelope`, `tests/integration/test_phase_workflow.py` line 962, `tests/e2e/mechanism.bats` line 462.

## 13.5 `validate --archived` (v1.9.0+)

**Contract**: `openspec validate --archived` is an opt-in CI/pre-commit gate that every change under `changes/archive/` has all `tasks.md` checkboxes ticked. Exits non-zero if any are unchecked. Standalone scope — does not alter any other `validate` invocation.

**Consumer**: `source/cli.py._post_install_archived_sweep(strict=False, timeout=30)` (`source/cli.py:1214`) runs `openspec validate --archived --json` after `deploy_core` (`source/cli.py:1071`) and after `update-core_cmd` (`source/cli.py:1898`). Default is non-fatal: a yellow warning names the remediation. Opt-in to fail-on-warning via `--strict-archived` or `OPENSPEC_VALIDATE_ARCHIVED_STRICT=1`.

**Operational note**: The sweep is a CI hygiene check, not a regression test. It catches the case where someone archived a change with unfinished work. The function also bridges the broader `validate --archived` envelope into the `osx validate archived` subcommand (`source/lib/osx.py:1990`) for in-process callers.

**Reference**: `source/cli.py:1214`, `source/lib/osx.py:1990`. Tests: `tests/integration/test_install_flow.py::TestValidateArchivedSweep`, `tests/unit/test_no_double_json.py` line 172, `tests/unit/test_validate_subcommands.py:164`, `tests/e2e/mechanism.bats:501`.

## 13.6 Related v1.7.0+ contracts (informational)

- **`requires: string[]`** on each `artifacts[]` entry — used by `osx-review-artifacts` Step 4 to build the dependency graph. See `orchestrator/resources/canonical/skills/osx-review-artifacts/SKILL.md`.
- **`skip_specs: true`** change metadata — zero-delta changes (pure refactors). Honoured by core's validator; extended side surfaces it in `read_change_metadata` (`source/lib/osx.py:2037`).
- **`defaultStore` machine-level fallback** — `openspec config set defaultStore <id>` sets a per-machine fallback. The status `root` block reports `source: "global_default"` when used. Resolution flows through `current_store.get()`.
- **`instructions archive`** — read-only mirror of `instructions apply`. Returns `{ "changeName", "context"?, "operationGuidance"?, "root" }`.

## 13.7 `validate --report findings`, `missingPrerequisites`, `list --specs` (v1.12.0–v1.13.0)

### 13.7.1 `validate --report findings` (v1.12.0+)

**Contract**: `openspec validate --report findings` is an opt-in bulk-scope flag. It returns only items with errors / warnings / informational findings while keeping full-run totals and exit codes. Delta merge conflicts during validation surface as informational findings, without changing exit codes.

**Consumer**: Informational. The orchestrator's existing `osx validate *` callers keep using the full report; `validate_all` does not opt into `--report findings` because the orchestrator's failure path reads `findings` shape directly from the unfiltered envelope.

**Operational note**: An informational finding for a delta-merge conflict is a sign that the merge preflight couldn't fully resolve its inputs (file-read errors, schema ambiguity). Treat as a yellow warning: review the affected capability path manually before archiving.

**Reference**: `orchestrator/core/source/CHANGELOG.md` v1.12.0 PRs #1710, #1713. Covered in `references/schema-agnostic-contract.md`.

### 13.7.2 `missingPrerequisites` (v1.13.0+)

**Contract**: `openspec instructions apply --change <name> --json` adds a `missingPrerequisites` array naming the full build-order chain for an apply whose `applyRequires` set is not yet satisfied — not just the first hop. A change with no delta specs (and no `skip_specs: true`) is reported as a warning at apply time. PR #1783 in v1.13.0.

**Consumer**: PHASE1 (IMPLEMENTATION) fetches the envelope during its MANDATORY CHECKPOINT step (`orchestrator/resources/canonical/commands/osx-phase1.md`). When the response carries a non-empty `missingPrerequisites`, each entry's name + remedy command is surfaced in the decision log via `osx log append --extra '{"missing_prerequisites": [...]}'`; PHASE1 still proceeds with the existing apply gate (logging is informational, not blocking). The in-process helper is `osx.fetch_apply_prerequisites(change_id, *, store=None)` (`source/lib/osx.py`), which returns `list[str] | None` (`None` for cores that don't surface the field).

**Operational note**: The `missingPrerequisites` array is the structured counterpart to the text remedies; consumers should prefer it over regex-parsing the text response. When the field is absent but the change has no `applyRequires` blockers, core simply reports apply-ready.

**Reference**: `source/lib/osx.py` (`fetch_apply_prerequisites`); `orchestrator/resources/canonical/commands/osx-phase1.md`. Tests: `tests/unit/test_apply_prerequisites.py::TestFetchApplyPrerequisites`, `tests/unit/test_resource_contract.py::TestOrchestratorContracts::test_missing_prerequisites_helper_exists`.

### 13.7.3 `openspec list --specs` + `show <id> --type spec --json --no-scenarios` (v1.13.0+)

**Contract**: `openspec list --specs` is a first-class spec-inventory command (parallel to `openspec list` for changes); `openspec show <id> --type spec --json --no-scenarios` is the filtered read used by generated guidance. The filtered read is only an overview; agents still read relevant specs in full (with scenarios) before deciding what is already covered. PR #1700 in v1.13.0.

**Consumer**: PHASE0 spec-aware review (`orchestrator/resources/canonical/skills/osx-review-artifacts/SKILL.md` Step 2) runs `openspec list --specs` and a per-spec `show --type spec --json --no-scenarios` for every spec id, building a `{spec_id → {path, purpose, requirements_count}}` map. Step 4 (Cross-artifact consistency) adds a "Capability-already-exists" check: for each delta `ADDED Requirements` capability path, if the spec inventory already has that path, emit a `Warning` finding pointing to `/opsx:update <name>`. In-process helpers: `osx.list_specs(*, store=None)` and `osx.show_spec(spec_id, *, store=None)` (`source/lib/osx.py`).

**Operational note**: The new check is **additive** and never escalates above `Warning` per the calibration rule (prefer `Suggestion`). When the spec inventory can't be loaded (older core, missing `--specs` flag), the helper returns `None` and the consumer silently skips the new check — backwards-compatible with v1.11.0 cores.

**Reference**: `source/lib/osx.py` (`list_specs`, `show_spec`); `orchestrator/resources/canonical/skills/osx-review-artifacts/SKILL.md`. Tests: `tests/unit/test_spec_inventory.py`, `tests/unit/test_resource_contract.py::TestOrchestratorContracts::test_spec_inventory_consumer_is_wired`.

### 13.7.4 Archive preserves fenced code blocks (v1.13.0+)

**Contract**: `openspec archive` no longer rewrites the inside of fenced code blocks. Blank-line collapsing now runs through a fence mask (`buildCodeFenceMask`), so YAML block scalars, Python samples, expected-output fixtures, and Markdown-inside-Markdown keep their internal whitespace. PR #1798.

**Consumer**: Informational. PHASE6 (`osc-archive-change`) benefits automatically; no orchestrator-side change.

### 13.7.5 Delta `[-*+]` bullet markers and duplicate-header handling (v1.13.0+)

**Contract**: REMOVED and RENAMED delta sections now accept `*` or `+` as bullet markers, not just `-`. Duplicate section titles now read every body, not just the first. PR #1800 (markers) and PR #1802 (duplicate-header handling).

**Consumer**: Informational. The schema-agnostic contract already derives parsing from `instructions --json`'s `template` / `rules` rather than hardcoded markers, so no extension code needed to change.

### 13.7.6 `retire_capabilities` line-wrap and `+`-marker relaxations (v1.13.0+)

**Contract**: `retire_capabilities: true` no longer refuses specs whose scenario bullets wrap onto a second line. Specs whose scenarios use `+`-marker bullets are also covered. PR #1782.

**Consumer**: `osx-phase6` Step 0 (Precondition check) at `orchestrator/resources/canonical/commands/osx-phase6.md`. The previous strict precondition is now redundant — the check is: confirm `state.retire_capabilities == true`; confirm `openspec show "$1" --json` reports at least one REMOVED delta; log `retirement_intent: true`; defer the rest to core.

**Operational note**: Users who relied on the strict preflight to surface "wrap your bullets" or "use `-` markers" warnings before archive will see those warnings suppressed; core now handles them. The orchestrator's `BLOCKED` path is unchanged.

## 13.8 Interaction with the §4.2 schema-agnostic contract

The six rules in §4.2 (Schema source of truth, Glob safety, Frontier discipline, No code edits, Per-edit confirmation, Severity calibration) were authored at v1.6.0. Two rules are now load-bearing beyond their original scope:

- **Rule 1 (Schema source of truth)** — extended to include `isPlanningComplete`, `retire_capabilities`, `operationGuidance`, `missingPrerequisites`, and the spec inventory. Review and modify skills must consume these when present.
- **Rule 2 (Glob safety)** — unchanged. The `requires` field (v1.7.0+) does not change which paths are safe to write. The v1.13.0 fenced-code preservation in archive means `existingOutputPaths` written by previous archives now retain their internal whitespace, but the path surface is unchanged.
