# PR6 — Phase 3 part 2: legacy migration, aliases, Medium-tier adapters

**Goal:** Ship `legacy_skills_dirs` + the migration helper + `TOOL_ID_ALIASES` + the remaining Medium-tier adapters (antigravity, github-copilot, hermes, devin-finalised).

**Release:** v1.12.x patch (lands after PR5A/5B/5C ship v1.12.0).

**Effort:** ~3-4 days.

---

## Why this PR exists

PR5C ships the bulk of Low-effort adapters and the shared-root arbitration. PR6 handles the four Medium-effort adapters that need:

1. `legacy_skills_dirs` + auto-migration (antigravity, codex, devin, kimi)
2. File-typed detection paths (github-copilot, hermes)
3. The `windsurf → devin` alias (the only upstream alias today)

After PR6, openspec-extended covers 38 of 39 upstream tools (only minimax-code remains for PR7).

---

## New `ToolAdapter` field

```python
# In orchestrator/source/tools.py, ToolAdapter dataclass

legacy_skills_dirs: tuple[str, ...] = ()
"""Former project-local roots that map to the tool's current
``skills_dir`` and should be reconciled on install/update. Each entry
is a top-level dotfile directory name (e.g. ``.codex``, ``.windsurf``,
``.kimi``, ``.agent``). Drives the ``migrate_legacy_skills_dirs``
helper (added in this PR) which copies files from legacy roots to
the current skills_dir when the destination doesn't already exist.
Default ``()`` preserves shipped behaviour."""
```

## New module-level constant

```python
# In orchestrator/source/tools.py

TOOL_ID_ALIASES: dict[str, str] = {"windsurf": "devin"}
"""Aliases that resolve to canonical tool ids before unknown-id checks.

Mirrors upstream ``TOOL_ID_ALIASES`` at
``orchestrator/core/source/src/core/config.ts:100-102``. Used by
``_parse_tool_target:cli.py:1521-1552`` so ``windsurf`` resolves to
``devin`` without registering a separate ``windsurf`` REGISTRY entry.
"""
```

---

## New `migrate_legacy_skills_dirs` helper

Add to `orchestrator/source/lib/osx.py`:

```python
def migrate_legacy_skills_dirs(
    adapter: ToolAdapter,
    project_root: Path,
    *,
    dry_run: bool = True,
    snapshot_path: Path | None = None,
) -> dict:
    """Copy files from ``adapter.legacy_skills_dirs`` to ``adapter.skills_dir/skills/``.

    Conservative migration contract:
    1. Copy, not move. Source files preserved.
    2. Refuse to overwrite. If the destination file exists and differs
       from the source, log divergence and skip.
    3. Idempotent. A second run is a no-op.
    4. Snapshot. Writes a JSON snapshot listing every file touched.

    Args:
        adapter: The ToolAdapter to migrate for.
        project_root: The project root to resolve both legacy and target paths against.
        dry_run: When True (default), compute the migration plan and return it
            without writing any files. Use ``dry_run=False`` to apply.
        snapshot_path: Optional path to write the migration snapshot. Defaults
            to ``<project_root>/.openspec-extended-migration.json``.

    Returns:
        dict with keys: ``copied`` (list of relative paths), ``skipped`` (list
        of {path, reason}), ``snapshot_path`` (str or None).
    """
    if not adapter.legacy_skills_dirs:
        return {"copied": [], "skipped": [], "snapshot_path": None}

    target_skills = project_root / adapter.skills_dir / "skills"
    plan = {"copied": [], "skipped": []}

    for legacy_root in adapter.legacy_skills_dirs:
        legacy_skills = project_root / legacy_root / "skills"
        if not legacy_skills.is_dir():
            continue  # nothing to migrate

        for src_file in legacy_skills.rglob("*"):
            if not src_file.is_file():
                continue
            rel = src_file.relative_to(legacy_skills)
            dst_file = target_skills / rel

            if dst_file.exists():
                if dst_file.read_bytes() == src_file.read_bytes():
                    plan["skipped"].append({
                        "path": str(rel),
                        "reason": "destination identical",
                    })
                    continue
                plan["skipped"].append({
                    "path": str(rel),
                    "reason": "destination differs; refusing to overwrite",
                })
                continue

            if not dry_run:
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, dst_file)
            plan["copied"].append(str(rel))

    snapshot_path_str = None
    if not dry_run and plan["copied"]:
        snapshot_path = snapshot_path or (
            project_root / ".openspec-extended-migration.json"
        )
        snapshot_path.write_text(json.dumps({
            "tool_id": adapter.tool_id,
            "legacy_root": list(adapter.legacy_skills_dirs),
            "target_root": str(target_skills),
            "copied": plan["copied"],
            "timestamp": get_timestamp(),
        }, indent=2))
        snapshot_path_str = str(snapshot_path)

    plan["snapshot_path"] = snapshot_path_str
    return plan
```

---

## Production changes

### `orchestrator/source/tools.py` (+~80 lines)

Add `legacy_skills_dirs` field, `TOOL_ID_ALIASES` constant, and the 4 new REGISTRY entries (antigravity, github-copilot, hermes, devin-finalised with `legacy_skills_dirs`).

### `orchestrator/source/lib/osx.py` (+~120 lines)

Add `migrate_legacy_skills_dirs` helper.

### `orchestrator/source/cli.py` `deploy_all_resources` (+~30 lines)

Invoke the migration helper after a successful install:

```python
# In deploy_all_resources, after per-side manifest writes:
for adapter in REGISTRY.values():
    if adapter.legacy_skills_dirs:
        plan = osx_lib.migrate_legacy_skills_dirs(
            adapter, project_root, dry_run=True
        )
        if plan["copied"]:
            console.print(
                f"[yellow]Legacy migration proposed for {adapter.tool_id}:[/yellow]"
            )
            for path in plan["copied"]:
                console.print(f"  {path}")
            console.print(
                f"  Apply with: openspec-extended install {adapter.tool_id} --apply-migration"
            )
```

### `orchestrator/source/cli.py` `_parse_tool_target` (+~20 lines)

Resolve aliases first:

```python
def _parse_tool_target(arg: str) -> str:
    """Parse a single tool id, resolving aliases.

    Examples:
        'opencode' → 'opencode'
        'windsurf' → 'devin'  # via TOOL_ID_ALIASES
        'claude,opencode' → ['claude', 'opencode']
    """
    from source.tools import TOOL_ID_ALIASES

    target = arg.strip()
    if target in TOOL_ID_ALIASES:
        target = TOOL_ID_ALIASES[target]
    if target not in REGISTRY:
        raise ValueError(f"Unknown tool: {target!r}; available: {sorted(REGISTRY)}")
    return target
```

### `orchestrator/source/lib/osx.py` `detect_platform` (~5 line change)

Add PR5C's `exists()` change so file-typed detection paths work:

```python
# Old:
if any((project_root / p).is_dir() for p in adapter.detect_paths):
    return adapter.tool_id

# New:
if any((project_root / p).exists() for p in adapter.detect_paths):
    return adapter.tool_id
```

Same change in `runner.py:detect_runner:88-114`.

---

## New `REGISTRY` entries (4 tools + devin-finalised)

```python
# devin — update PR5B's entry with legacy_skills_dirs
"devin": ToolAdapter(
    # ... same fields as PR5B ...
    legacy_skills_dirs=(".windsurf",),
),

"antigravity": ToolAdapter(
    tool_id="antigravity",
    skills_dir=".agents",
    commands_dir="",
    commands_style="skills-only",
    commands_ext="md",
    slash_prefix="/",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install antigravity` to deploy skills to .agents/skills/.",
    runner_binary="agy",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Antigravity",
    detect_paths=(".agent", ".agents/workflows"),  # legacy .agent + current .agents/workflows
    requires_ide_restart=True,
    shared_skills_root=True,
    setup_note="",
    legacy_skills_dirs=(".agent",),  # migrate .agent/skills/ → .agents/skills/
),

"github-copilot": ToolAdapter(
    tool_id="github-copilot",
    skills_dir=".github",
    commands_dir="prompts",  # uses prompts/ not commands/
    commands_style="flat",
    commands_ext="prompt.md",
    slash_prefix="osx-",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install github-copilot` to deploy prompt files to .github/prompts/.",
    runner_binary="copilot",
    runner_kind="generic_print",
    runner_args=("--allow-all-tools",),  # auto-approve for write phases
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="GitHub Copilot",
    detect_paths=(
        ".github/copilot-instructions.md",  # file
        ".github/instructions",              # dir
        ".github/workflows/copilot-setup-steps.yml",  # file (cloud agent)
        ".github/prompts",                   # dir
        ".github/agents",                    # dir
        ".github/skills",                    # dir
        ".github/.mcp.json",                 # file
    ),
    requires_ide_restart=True,
    shared_skills_root=False,  # .github is project-shared but not tool-shared
    setup_note="GitHub Copilot picks up .github/prompts/ at IDE reload. The local CLI does not read these files; use the IDE for prompt invocation.",
),

"hermes": ToolAdapter(
    tool_id="hermes",
    skills_dir=".hermes",
    commands_dir="",
    commands_style="skills-only",
    commands_ext="md",
    slash_prefix="/",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install hermes` to deploy skills to .hermes/skills/.",
    runner_binary="hermes",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Hermes Agent",
    detect_paths=(".hermes", "HERMES.md", ".hermes.md"),  # 1 dir + 2 files
    requires_ide_restart=False,
    shared_skills_root=False,
    setup_note="Hermes only loads skills from ~/.hermes/skills/ by default. Add this project's .hermes/skills/ directory to skills.external_dirs in ~/.hermes/config.yaml, then restart Hermes.",
),
```

---

## Test changes

### `tests/unit/test_lib_registry_consumers.py` (+~80 lines) — `TestLegacySkillsDirsMigration`

```python
class TestLegacySkillsDirsMigration:
    """Drives migrate_legacy_skills_dirs against synthetic adapters with
    pre-existing legacy trees."""

    def test_antigravity_copies_agent_skills_to_agents(self, tmp_path):
        # Create .agent/skills/openspec-propose/SKILL.md
        # Run migrate for a synthetic antigravity adapter
        # Assert .agents/skills/openspec-propose/SKILL.md exists
        # Assert .agent/skills/openspec-propose/SKILL.md still exists (copy not move)

    def test_dry_run_does_not_write_files(self, tmp_path):
        # Same setup; dry_run=True (default)
        # Assert no files written; assert plan["copied"] is populated

    def test_refuses_to_overwrite_differing_files(self, tmp_path):
        # Create .agent/skills/openspec-propose/SKILL.md (version A)
        # Create .agents/skills/openspec-propose/SKILL.md (version B, differs)
        # Run migrate
        # Assert version B preserved; plan["skipped"] populated

    def test_idempotent_second_run_is_noop(self, tmp_path):
        # Run migrate twice
        # Assert second run plan["copied"] is empty

    def test_writes_snapshot_file(self, tmp_path):
        # Run migrate with dry_run=False
        # Assert .openspec-extended-migration.json exists with expected content
```

### `tests/unit/test_cli_registry_consumers.py` (+~30 lines) — `TestToolIdAlias`

```python
class TestToolIdAlias:
    def test_windsurf_resolves_to_devin(self):
        assert _parse_tool_target("windsurf") == "devin"

    def test_devin_passes_through(self):
        assert _parse_tool_target("devin") == "devin"

    def test_unknown_alias_raises(self):
        with pytest.raises(ValueError, match="Unknown tool"):
            _parse_tool_target("nonexistent")
```

### `tests/unit/test_lib_registry_consumers.py` (+~40 lines) — `TestMultiPathDetect`

```python
class TestMultiPathDetect:
    """Verify file-typed detection paths work after the exists() change."""

    def test_github_copilot_detected_by_file(self, tmp_path):
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github" / "copilot-instructions.md").write_text("# copilot\n")
        assert detect_platform(tmp_path) == "github-copilot"

    def test_hermes_detected_by_uppercase_file(self, tmp_path):
        (tmp_path / "HERMES.md").write_text("# hermes\n")
        assert detect_platform(tmp_path) == "hermes"

    def test_hermes_detected_by_lowercase_file(self, tmp_path):
        (tmp_path / ".hermes.md").write_text("# hermes\n")
        assert detect_platform(tmp_path) == "hermes"
```

### `tests/unit/test_tool_registry.py` (+~60 lines)

- `SHIPPED_TOOLS` becomes a 38-element frozenset.
- Per-tool snapshot tests for the 4 new entries.
- `TestAdapterFieldDefaults` extended to lock `legacy_skills_dirs` default to `()`.

### `tests/integration/test_install_flow.py` (+~30 lines)

- Multi-tool install smoke test: `openspec-extended install antigravity,github-copilot,hermes`.
- Legacy migration smoke test: install antigravity against a project with pre-existing `.agent/skills/`.

---

## Documentation

### `.opencode/rules/per-adapter-rendering.md` (+~50 lines)

Add 4 new rows. Note:
- antigravity's `legacy_skills_dirs=(".agent",)`.
- github-copilot's 7-path detection (3 file-typed).
- hermes's `setup_note` text.

### `orchestrator/source/AGENTS.md` (+~30 lines)

Document:
- `legacy_skills_dirs` field.
- `TOOL_ID_ALIASES` constant.
- The `migrate_legacy_skills_dirs` helper.
- The dry-run-by-default contract.

### `orchestrator/source/lib/AGENTS.md` (+~15 lines)

Add `migrate_legacy_skills_dirs` to the table of library functions. Note its conservative contract (copy not move, refuse to overwrite, idempotent, snapshot, dry-run default).

### Root `AGENTS.md` (+~10 lines)

If `AGENTS.md` has a section on adapter fields, add `legacy_skills_dirs` to the field reference.

---

## Acceptance criteria

- `mise run verify` is green.
- `SHIPPED_TOOLS` is a 38-element frozenset (4 new + devin-finalised).
- `openspec-extended install antigravity` against a project with `.agent/skills/` proposes a migration and writes the snapshot file.
- `openspec-extended install windsurf` (alias) resolves to `openspec-extended install devin`.
- `openspec-extended install github-copilot` against a project with `.github/copilot-instructions.md` detects github-copilot.
- `TestLegacySkillsDirsMigration` passes for all 5 cases.
- Shipped `opencode`, `claude`, and PR3/PR4/PR5 entries behave unchanged.

---

## Dependencies

- PR1, PR2, PR3, PR4, PR5A, PR5B, PR5C must have landed.

## Followed by

- PR7 ships `global_skills_dir` + the only Heavy adapter (minimax-code).

---

## Per-tool quirks

- **antigravity's `detect_paths=(".agent", ".agents/workflows")`** — both paths must exist or the migration doesn't trigger. Note `.agent` is the legacy singular form.
- **github-copilot's 7-path detection** — three of the seven are files (`.md` and `.yml` and `.json`). The `exists()` change in `lib/osx.py:219` is critical.
- **hermes's `detect_paths=(".hermes", "HERMES.md", ".hermes.md")`** — mix of directory and file paths; same `exists()` requirement.
- **devin's `legacy_skills_dirs=(".windsurf",)`** — combined with `TOOL_ID_ALIASES["windsurf"]="devin"`, this gives Windsurf users a clean migration path.

## Migration contract — restated for emphasis

Per [00-decisions.md](../00-decisions.md) Decision 3:

1. **Copy, not move.** Source files preserved.
2. **Refuse to overwrite.** If the destination file exists and differs, log divergence and skip.
3. **Idempotent.** Second run is a no-op.
4. **Snapshot.** Writes `.openspec-extended-migration.json` listing every file touched.
5. **Dry-run by default.** `--apply-migration` to actually run.

This is the same UX pattern as `rename_core_resources:cli.py:1054-1128` and `CORE_BASELINE_FILENAME:cli.py:1131`.

## Format-collision risk for github-copilot's `.prompt.md`

PR4's `_substitute_tokens_in_file:cli.py:380` accepts `.prompt.md` (verified in PR4's test suite). PR6 does not re-test the substitution; it relies on PR4 as the safety net.

The same goes for the `.md` and `.toml` cases. PR6 is purely about detection paths, aliases, and migration; it doesn't touch token substitution.
