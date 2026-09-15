# PR2 — Phase 2B prep: three new ToolAdapter fields

**Goal:** Lay the schema for the rollout without shipping any new adapter. Three fields land now so every downstream PR can use them.

**Release:** v1.11.0 (lands at the start of v1.11.0 work, immediately before PR3).

**Effort:** ~2-3 days.

> **Status update — the 4 preparatory commits have already shipped 5 of the 6 fields originally planned for the rollout.** `ask_tool`, `install_hint`, `cross_ref_prefix`, `runner_args`, and `frontmatter_extras` are already on `ToolAdapter` (commit `fb1cffc7`), with consumers wired into `GenericPrintRunner`, `_build_skill_mirror`, `_substitute_tokens`, the install-hint consumer in `lib/osx.py`, and the `check-platform-hardcodes` regex. The synthetic `cursor` adapter is already in `test_install_multi.py` (commit `e56acaf2`).
>
> What this PR now adds is **3 additional fields** that the 4 preparatory commits did not cover: `requires_ide_restart`, `shared_skills_root`, `setup_note`. The "post-prep" remaining field count across the rollout is 6 (down from 11 in the original plan): 3 in PR2 + 2 in PR6 + 1 in PR7.

---

## New `ToolAdapter` fields

Three fields, each with default values that preserve shipped behaviour byte-for-byte.

```python
# In orchestrator/source/tools.py, ToolAdapter dataclass

requires_ide_restart: bool = False
"""Whether the target IDE/editor needs to be restarted to pick up new
slash commands. When True, ``deploy_all_resources`` prints a post-install
hint naming the IDE. Upstream declares this for 16 of 39 tools (CLI-only
tools don't need it — see orchestrator/core/source/src/core/config.ts).
Default False — opencode and claude don't need it."""

shared_skills_root: bool = False
"""Whether this adapter's ``skills_dir`` is shared with other tools and
the orchestrator should suppress the "no other adapter uses this dir"
sanity check. Required for codex, zed, antigravity, and the vendor-neutral
``agents`` adapter, which all map to ``.agents``. Default False —
opencode and claude have unique ``skills_dir`` values."""

setup_note: str = ""
"""Optional post-install hint printed by ``deploy_all_resources`` after a
successful install. Used by tools whose skills root requires manual
configuration (e.g. Hermes — see orchestrator/core/source/src/core/config.ts
``setupNote``). Default empty — opencode and claude don't need one."""
```

### Recap: fields already shipped by the preparatory commits (do NOT re-add)

| Field | Type | Default | Added in |
|-------|------|---------|----------|
| `ask_tool` | `str` | `"AskUserQuestion"` | `fb1cffc7` |
| `install_hint` | `str` | `""` | `fb1cffc7` |
| `cross_ref_prefix` | `str` | `""` | `fb1cffc7` |
| `runner_args` | `tuple[str, ...]` | `()` | `fb1cffc7` |
| `frontmatter_extras` | `dict[str, str]` | `{}` | `fb1cffc7` |

These are already in `orchestrator/source/tools.py` and locked by `tests/unit/test_tool_registry.py::TestAdapterFieldDefaults` (extended in `e56acaf2` to cover them). Do not re-add or re-lock them.

---

## Production changes

### `orchestrator/source/tools.py` (+~50 lines)

Add the three fields with default values + per-field docstrings. Place them adjacent to the existing `install_hint` field for discoverability.

### `orchestrator/source/cli.py` `deploy_all_resources` (+~50 lines)

After a successful install, print the setup note and restart hint when present.

```python
# In deploy_all_resources, after the per-side manifest writes (around line 683):
for tool_id in active_tools:
    adapter = REGISTRY[tool_id]
    if adapter.setup_note:
        console.print(
            f"[yellow]Setup note for {tool_id}:[/yellow] {adapter.setup_note}"
        )
    if adapter.requires_ide_restart:
        console.print(
            f"[yellow]Restart your IDE to pick up the new {tool_id} "
            f"slash commands.[/yellow]"
        )
```

### `orchestrator/source/cli.py` `validate_deployment` (+~20 lines)

Suppress the "no other adapter uses this dir" sanity check when `adapter.shared_skills_root=True`.

```python
# In validate_deployment, the "no other adapter uses this dir" branch (around line 1425):
if not adapter.shared_skills_root:
    other_adapters = [t for t in REGISTRY if t != tool_id and REGISTRY[t].skills_dir == adapter.skills_dir]
    if other_adapters:
        # existing yellow-info line: "<skills_dir> is shared with: <other_adapters>"
        ...
```

---

## Test changes

### `tests/unit/test_tool_registry.py` `TestAdapterFieldDefaults` (+~40 lines)

Extend the existing class to lock the defaults:

```python
class TestAdapterFieldDefaults:
    # ... existing tests for ask_tool, install_hint, etc. ...

    @pytest.mark.parametrize("tool_id", ["opencode", "claude"])
    def test_requires_ide_restart_defaults_to_false(self, tool_id):
        assert REGISTRY[tool_id].requires_ide_restart is False

    @pytest.mark.parametrize("tool_id", ["opencode", "claude"])
    def test_shared_skills_root_defaults_to_false(self, tool_id):
        assert REGISTRY[tool_id].shared_skills_root is False

    @pytest.mark.parametrize("tool_id", ["opencode", "claude"])
    def test_setup_note_defaults_to_empty(self, tool_id):
        assert REGISTRY[tool_id].setup_note == ""
```

### `tests/unit/test_cli_registry_consumers.py` (+~60 lines)

Three new test classes:

```python
class TestAdapterRequiresIdeRestart:
    """Asserts that deploy_all_resources prints the IDE-restart hint when
    adapter.requires_ide_restart is True."""

    def test_hint_printed_when_field_set(self, tmp_path, monkeypatch):
        # Build a synthetic adapter with requires_ide_restart=True
        # Run deploy_all_resources against it
        # Capture stdout
        # Assert "Restart your IDE" appears

    def test_no_hint_when_field_false(self, tmp_path, monkeypatch):
        # Synthetic adapter with requires_ide_restart=False
        # Assert hint does NOT appear


class TestSharedSkillsRootSuppressesNote:
    """Asserts that validate_deployment skips the shared-root warning
    when adapter.shared_skills_root is True."""

    def test_shared_root_does_not_emit_warning(self, tmp_path, monkeypatch):
        # Synthetic adapter with shared_skills_root=True
        # Another synthetic adapter also using .agents
        # Assert no warning is emitted

    def test_unique_root_emits_warning(self, tmp_path, monkeypatch):
        # Synthetic adapter with shared_skills_root=False
        # No other adapter uses its skills_dir
        # Assert no warning (sanity case)


class TestSetupNoteEmitted:
    """Asserts that deploy_all_resources prints the setup note when
    adapter.setup_note is non-empty."""

    def test_note_printed_when_field_set(self, tmp_path, monkeypatch):
        # Synthetic adapter with setup_note="Add ~/.hermes/skills to external_dirs"
        # Assert the note text appears in stdout

    def test_no_note_when_field_empty(self, tmp_path, monkeypatch):
        # Synthetic adapter with setup_note=""
        # Assert no note appears
```

---

## Documentation

### `.opencode/rules/per-adapter-rendering.md` (+~25 lines)

Extend the per-tool layout table with the three new fields. Add a "Capabilities" row showing `requires_ide_restart` and `shared_skills_root` (both default False for shipped adapters; will be set for new adapters in PR3+).

### `orchestrator/source/AGENTS.md` (+~15 lines)

Update the "Adding a new tool adapter" section with the three new fields. For each:

- When to set `requires_ide_restart=True`: when the tool reads its commands from an IDE process that doesn't hot-reload (per upstream `AI_TOOLS` which declares it for 16 tools).
- When to set `shared_skills_root=True`: when the tool's `skills_dir` is shared with another registered tool (e.g. `.agents` shared between codex, zed, antigravity, agents).
- When to set `setup_note`: when the tool requires manual post-install configuration (Hermes is the canonical example).

---

## Acceptance criteria

- `mise run verify` is green.
- The three new fields are present on `ToolAdapter` with the documented defaults.
- `TestAdapterFieldDefaults` extended to lock the defaults.
- Three new test classes pass: `TestAdapterRequiresIdeRestart`, `TestSharedSkillsRootSuppressesNote`, `TestSetupNoteEmitted`.
- Shipped `opencode` and `claude` behaviour is unchanged (verified by `test_opencode_tokens_match_documented_table` and the equivalent claude tests).
- No new REGISTRY entries — this PR is purely additive.

---

## Dependencies

- PR1 must land first (its tests are the safety net that catches any regression introduced by the field additions).

## Followed by

- PR3 ships 4 new adapters that exercise `requires_ide_restart` (cursor) and `shared_skills_root` (codex).
- PR6 ships `legacy_skills_dirs` and `TOOL_ID_ALIASES` (further additions to the adapter surface).
- PR7 ships `global_skills_dir` (the last field addition).

---

## Why this PR exists separately from PR3

If PR2 and PR3 were combined, a reviewer would face a ~400-line diff with both new fields and new REGISTRY entries. Splitting them:

1. Lets the schema PR (PR2) get a focused review on whether the three fields are the right shape.
2. Lets the implementation PR (PR3) focus on per-tool config correctness.
3. If a field shape needs to change (e.g. `setup_note` becomes a richer structure), only PR2 is affected, not PR3.

This is the same pattern as the Phase 1A→1D work in commit history (`74782fbf` registry skeleton → `71b5c7e2` cli consumers → `706625e7` engine consumers).
