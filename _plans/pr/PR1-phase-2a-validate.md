# PR1 — Phase 2A: validate the abstraction

**Goal:** Empirically exercise the abstraction against every `CommandsStyle` value before we commit to scaling it. No production code change. No version bump.

**Release:** v1.10.x patch (land at any time after the current v1.10.4 release).

**Effort:** ~1 day.

---

## Why this PR exists

The current test suite covers `opencode` and `claude` (the two shipped adapters). Three synthetic fixtures (`cursor`, `codex`, `kimi`) exist in `tests/unit/test_runner_abstraction.py:240-274`, `tests/unit/test_cli_registry_consumers.py:599-651`, and `tests/unit/test_lib_registry_consumers.py:36-70` — but they're not exercised end-to-end against the deploy / purge / detect consumers.

Specifically:

- `purge_managed_resources` is only tested for `flat` (opencode) and `namespaced-with-skill-mirror` (claude). The `skills-only` branch (kimi's `commands_style`) has no test.
- `validate_deployment` is only tested for shipped adapters. A project with both `.cursor/` and `.opencode/` (two detection paths present) is not exercised.
- `_command_resolved_for_phase` and `_load_manifest` are only tested for shipped adapters.

Before we commit to scaling the abstraction (PR2 adds new fields; PR3 adds 4 new adapters), we want empirical confidence that every existing `CommandsStyle` value behaves correctly.

---

## Files touched

| File | Change | Lines |
|------|--------|-------|
| `tests/unit/test_cli_registry_consumers.py` | Add `TestPurgeSkillsOnly` | +~50 |
| `tests/unit/test_cli_registry_consumers.py` | Add `TestValidateDeploymentMultiPathDetection` | +~30 |
| `tests/unit/test_lib_registry_consumers.py` | Add `TestCommandResolvedForPhaseAcrossCommandsStyles` | +~30 |
| `tests/unit/test_runner_abstraction.py` | Add `TestDetectRunnerWalksRegistryAcrossCommandsStyles` | +~30 |

**No production code change.** No `AGENTS.md` change. No `.opencode/rules/` change.

---

## Test additions

### `TestPurgeSkillsOnly` (in `test_cli_registry_consumers.py`)

Drive `purge_managed_resources` against a synthetic `kimi` adapter (commands_style="skills-only", detect_paths=(".kimi-code", ".kimi")). Asserts:

1. A pre-existing `.kimi-code/skills/osx-stale/` is removed.
2. A pre-existing `.kimi/skills/osx-stale/` (legacy root) is left untouched (no `legacy_skills_dirs` declared).
3. The legacy migration is NOT the responsibility of this PR — that's PR6.

```python
def test_skills_only_purges_only_managed(self, tmp_path):
    target = tmp_path / ".kimi-code"
    target.mkdir()
    (target / "skills").mkdir()
    stale = target / "skills" / "osx-stale"
    stale.mkdir()
    keep_path = target / "skills" / "osx-keep"
    keep_path.mkdir()

    removed = purge_managed_resources(
        target, "kimi",
        keep_names={"osx-keep"},
        prefixes=("osx-",),
    )
    assert removed == 1
    assert not stale.exists()
    assert keep_path.exists()

def test_skills_only_does_not_touch_legacy_root(self, tmp_path):
    target = tmp_path / ".kimi-code"
    target.mkdir()
    (target / "skills").mkdir()
    legacy = tmp_path / ".kimi"
    legacy.mkdir()
    (legacy / "skills").mkdir()
    stale_legacy = legacy / "skills" / "osx-stale"
    stale_legacy.mkdir()

    removed = purge_managed_resources(
        target, "kimi",
        keep_names=set(),
        prefixes=("osx-",),
    )
    assert removed == 0  # skills-only purge only touches the target, not legacy
    assert stale_legacy.exists()  # PR6 introduces the migration helper
```

### `TestValidateDeploymentMultiPathDetection` (in `test_cli_registry_consumers.py`)

Drive `validate_deployment` against a project with both `.cursor/` and `.opencode/` present. Asserts:

1. Opencode wins because it's registered first (existing behaviour locked by `test_opencode_takes_precedence`).
2. The validation passes for the opencode deployment.

```python
def test_opencode_wins_when_both_detect_paths_present(self, tmp_path):
    (tmp_path / ".opencode").mkdir()
    (tmp_path / ".cursor").mkdir()
    # ... deploy opencode skills/commands under .opencode ...
    # ... validate_deployment passes ...
```

### `TestCommandResolvedForPhaseAcrossCommandsStyles` (in `test_lib_registry_consumers.py`)

For each `CommandsStyle` value (`flat`, `namespaced`, `namespaced-with-skill-mirror`, `skills-only`), assert that `_command_resolved_for_phase` returns the right path:

- `flat` → `<target>/commands/<name>.md`
- `namespaced` → `<target>/commands/<namespace>/<name>.md`
- `namespaced-with-skill-mirror` → both `<target>/commands/<namespace>/<name>.md` and `<target>/skills/<name>/SKILL.md`
- `skills-only` → no command file; assert that `_command_resolved_for_phase` returns `None` (the engine should not dispatch a slash command to a skills-only adapter)

### `TestDetectRunnerWalksRegistryAcrossCommandsStyles` (in `test_runner_abstraction.py`)

For each synthetic adapter in the test fixtures (`cursor`, `codex`, `kimi`), assert that `detect_runner` returns the right runner class:

- `cursor` → `GenericPrintRunner`
- `codex` → `GenericPrintRunner`
- `kimi` → `GenericPrintRunner`

This locks the dispatch shape even though the synthetic fixtures are not in the shipped `REGISTRY` (they live in `monkeypatch.setitem(REGISTRY, ...)` blocks within the test methods).

---

## Acceptance criteria

- `mise run verify` is green.
- All 4 new test classes pass.
- No production code change (diff is test-only).
- Existing 174 integration tests + 84 mechanism tests + 57 mechanism bats + 29 install bats still pass.

---

## Why this PR is small

The synthetic fixtures already exist. The work is *running* them against the consumers, not *adding* them. This is a 1-day PR because the heavy lifting was done when the synthetic fixtures were added in the Phase 1A→1D work (commits `74782fbf`, `71b5c7e2`, `d8eb3d2a`, `706625e7`, `75c4b0e9`, `6f6e4de5`, `a46c20e1`, `e150d63b`).

## Why this PR matters

PR2 adds 3 new `ToolAdapter` fields and changes the behaviour of `deploy_all_resources` and `validate_deployment`. PR3 adds 4 new REGISTRY entries that exercise the abstraction end-to-end. Both PRs assume the abstraction is correct. PR1 verifies that assumption before we lean on it.

If PR1 surfaces a bug in `purge_managed_resources`'s `skills-only` branch (or any other consumer), we fix it before PR2 lands. This is a regression-prevention PR, not a feature PR.
