# PR7 — Phase 4: global skills dir + minimax-code

**Goal:** Land the lone Heavy adapter by teaching the deploy/purge/validate pipeline to honour a `global_skills_dir` (home-relative target) when present.

**Release:** v1.13.0+ (lands after PR6 ships v1.12.x).

**Effort:** ~2-3 days.

---

## Why this PR exists

`minimax-code` is the only upstream tool that uses a global skills directory (not project-local). Upstream `config.ts:72` declares `globalSkillsDir: '.minimax'`, which `shared/skill-paths.ts:23-38` resolves from the user's home directory.

This is the only adapter that cannot be expressed by the existing `skills_dir: str` field, because the deploy target is `~/.minimax/`, not `<project_root>/.minimax/`. The entire deploy/purge/validate pipeline assumes a project-relative root.

---

## New `ToolAdapter` field

```python
# In orchestrator/source/tools.py, ToolAdapter dataclass

global_skills_dir: str | None = None
"""Home-relative global skills root (e.g. ``.minimax``). When set, the
deploy target is ``Path.home() / global_skills_dir`` rather than
``project_root / skills_dir``. The home directory is resolved by the
``_target_root`` helper which honours ``OPENSPEC_GLOBAL_SKILLS_HOME``
for testability. Default ``None`` preserves shipped behaviour for all
existing adapters."""
```

---

## New `_target_root` resolver

Add to `orchestrator/source/cli.py`:

```python
def _target_root(adapter: ToolAdapter, project_root: Path) -> Path:
    """Resolve the deploy target for an adapter.

    For global-skill adapters (``global_skills_dir`` set), returns
    ``Path.home() / adapter.global_skills_dir`` (or the
    ``OPENSPEC_GLOBAL_SKILLS_HOME`` override for tests).

    For project-local adapters, returns ``project_root / adapter.skills_dir``.

    Args:
        adapter: The ToolAdapter to resolve for.
        project_root: The project root for project-local adapters.

    Returns:
        Path to the deploy target root (e.g. ``<target>/.opencode`` or
        ``~/.minimax``).
    """
    if adapter.global_skills_dir:
        override = os.environ.get("OPENSPEC_GLOBAL_SKILLS_HOME")
        if override:
            return Path(override) / adapter.global_skills_dir
        return Path.home() / adapter.global_skills_dir
    return project_root / adapter.skills_dir
```

---

## New `REGISTRY` entry

```python
"minimax-code": ToolAdapter(
    tool_id="minimax-code",
    skills_dir="",  # unused; global_skills_dir drives the deploy target
    commands_dir="",
    commands_style="skills-only",
    commands_ext="md",
    slash_prefix="/",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install minimax-code` to deploy skills to ~/.minimax/skills/.",
    runner_binary="minimax",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="MiniMax Code",
    detect_paths=(),  # detected via global_skills_dir, not project paths
    requires_ide_restart=False,
    shared_skills_root=False,
    setup_note="MiniMax Code reads skills from ~/.minimax/skills/ globally, not from your project directory. Skills installed here apply to all your projects.",
    global_skills_dir=".minimax",
),
```

---

## Production changes

### `orchestrator/source/tools.py` (+~30 lines)

- Add `global_skills_dir` field.
- Add `minimax-code` REGISTRY entry.

### `orchestrator/source/cli.py` (+~60 lines)

- Add `_target_root` helper.
- Update `deploy_all_resources:cli.py:760-826` (~10 line refactor): use `_target_root` instead of `Path.cwd() / TOOL_DIRS[tool]`.
- Update `purge_managed_resources:cli.py:836-1010` (~10 line refactor): accept a `target_root` argument instead of inferring from `target_dir / skills_dir`.
- Update `validate_deployment:cli.py:1400-1493` (~10 line refactor): same.

### Caller changes

The three callers (`deploy_all_resources`, `purge_managed_resources`, `validate_deployment`) currently receive `project_root: Path` and infer `target_dir = project_root / skills_dir`. PR7 changes them to receive `target_dir: Path` directly, computed by the caller via `_target_root(adapter, project_root)`.

This is a small refactor: ~10 lines per function × 3 functions = ~30 lines net. The call sites (in `install_cmd`, `update_cmd`, etc.) need to call `_target_root(adapter, project_root)` before passing the result.

---

## Test changes

### `tests/unit/test_lib_registry_consumers.py` (+~30 lines) — `TestGlobalSkillsDirResolvesToHome`

```python
class TestGlobalSkillsDirResolvesToHome:
    """Locks the _target_root resolver's contract for global vs project-local adapters."""

    def test_project_local_uses_project_root(self, tmp_path):
        adapter = REGISTRY["opencode"]
        target = _target_root(adapter, tmp_path)
        assert target == tmp_path / ".opencode"

    def test_global_uses_home_dir(self, monkeypatch, tmp_path):
        monkeypatch.setenv("HOME", str(tmp_path))
        adapter = REGISTRY["minimax-code"]
        target = _target_root(adapter, Path("/some/project"))
        assert target == tmp_path / ".minimax"

    def test_global_override_via_env_var(self, monkeypatch, tmp_path):
        custom_home = tmp_path / "custom_home"
        custom_home.mkdir()
        monkeypatch.setenv("HOME", str(tmp_path / "real_home"))
        monkeypatch.setenv("OPENSPEC_GLOBAL_SKILLS_HOME", str(custom_home))
        adapter = REGISTRY["minimax-code"]
        target = _target_root(adapter, Path("/some/project"))
        assert target == custom_home / ".minimax"
```

### `tests/unit/test_cli_registry_consumers.py` (+~60 lines)

Three new test classes:

- `TestGlobalSkillsDirPurge` — assert `purge_managed_resources` cleans `~/.minimax/skills/...` when called with the global target.
- `TestGlobalSkillsDirValidate` — assert `validate_deployment` reads from `~/.minimax/manifest.toml`.
- `TestGlobalSkillsDirManifestWrites` — assert `deploy_all_resources` writes to `~/.minimax/manifest.toml`, not `<cwd>/.minimax/manifest.toml`.

All three use `monkeypatch.setenv("HOME", tmp_path)` and `monkeypatch.setenv("OPENSPEC_GLOBAL_SKILLS_HOME", tmp_path / "home")`.

### `tests/unit/test_tool_registry.py` (+~30 lines)

- `SHIPPED_TOOLS` becomes a 39-element frozenset.
- Per-tool snapshot test for `minimax-code`.
- `TestAdapterFieldDefaults` extended to lock `global_skills_dir` default to `None`.

### `tests/integration/test_install_flow.py` (+~30 lines)

- Global install smoke test: `openspec-extended install minimax-code` against a tmp home, assert `~/.minimax/skills/openspec-propose/SKILL.md` and `~/.minimax/manifest.toml` exist.

---

## Documentation

### `orchestrator/source/AGENTS.md` (+~15 lines)

Document `global_skills_dir`. Add a "Global vs project-local skills" subsection:

> When an adapter declares `global_skills_dir` (e.g. `minimax-code`), its skills deploy to `~/.minimax/skills/` instead of `<project>/.minimax/skills/`. Global installs apply to all the user's projects. The `OPENSPEC_GLOBAL_SKILLS_HOME` env var overrides `Path.home()` for testability.

### `.opencode/rules/per-adapter-rendering.md` (+~25 lines)

Add a "Global vs project-local skills" subsection. Reference `minimax-code` as the canonical example.

### `orchestrator/source/lib/AGENTS.md` (+~10 lines)

Add `_target_root` to the helper table. Note its dependency on `OPENSPEC_GLOBAL_SKILLS_HOME`.

---

## Acceptance criteria

- `mise run verify` is green.
- `SHIPPED_TOOLS` is a 39-element frozenset.
- `openspec-extended install minimax-code` against a tmp home (`HOME=tmp_path`) writes to `tmp_path/.minimax/skills/openspec-propose/SKILL.md` and `tmp_path/.minimax/manifest.toml`.
- `purge_managed_resources` correctly cleans `~/.minimax/skills/`.
- `validate_deployment` reads from `~/.minimax/manifest.toml`.
- `OPENSPEC_GLOBAL_SKILLS_HOME` override is honoured.
- Shipped `opencode`, `claude`, and all PR3/PR4/PR5/PR6 entries behave unchanged.

---

## Dependencies

- All previous PRs (PR1-PR6) must have landed.

## Final release after PR7

After PR7 lands, openspec-extended is at full parity with upstream OpenSpec's 39 `AI_TOOLS` entries. Adding a 40th tool is one `REGISTRY` entry (Tier 1), or one entry + ≤ 3 new fields (Tier 2), or one entry + `global_skills_dir` (Tier 3).

---

## Per-tool quirks

- **`minimax-code`'s empty `detect_paths`** — the tool is detected by the presence of `~/.minimax/skills/` (resolved via `global_skills_dir`), not by any project-relative path. `detect_platform` needs a special case for `global_skills_dir`-only adapters:

```python
# In detect_platform, after the existing walks:
for adapter in REGISTRY.values():
    if adapter.global_skills_dir:
        target = _target_root(adapter, project_root)
        if (target / "skills").is_dir():
            return adapter.tool_id
```

This means a user with `~/.minimax/skills/openspec-propose/SKILL.md` resolves to `minimax-code` regardless of which project they're in. That is the correct upstream behaviour.

- **`minimax-code`'s empty `skills_dir` and `commands_dir`** — both are unused because the deploy target is the global root. The fields are required by `ToolAdapter` today; PR7 relaxes them to `str | None = ""` (default empty string), or refactors `ToolAdapter` to make them optional. The minimal change is to leave them as required with `""` default and document the constraint.

## Security / UX consideration

`global_skills_dir` means the binary writes outside the project root. This is a meaningful security surface:

- **Risk**: a malicious project (e.g. a typosquatted OpenSpec skill) could trick the user into running `openspec-extended install minimax-code` and overwrite their global skills.
- **Mitigation**:
  1. The install hint clearly states "deploys skills to `~/.minimax/skills/`".
  2. The setup note explains "applies to all your projects".
  3. (Future) Add a `--global` opt-in flag that the user must explicitly pass; without it, `minimax-code` install is refused. This is not in scope for PR7 but is the next iteration.

PR7 ships the minimum viable global-skill support. Future hardening (explicit consent, audit log, dry-run) is in scope for v1.14.0 if user feedback warrants it.

## Why `OPENSPEC_GLOBAL_SKILLS_HOME` env var

The env var override exists for two reasons:

1. **Testability** — `monkeypatch.setenv("HOME", tmp_path)` works on POSIX, but the test must use `OPENSPEC_GLOBAL_SKILLS_HOME` directly to bypass `Path.home()` resolution. This is the same pattern as upstream's `options.homeDir` argument (`shared/skill-paths.ts:23-38`).
2. **Power-user override** — users who keep their home on a slow filesystem can redirect the global skills root to a faster mount.

The env var is read by `_target_root` only — it doesn't propagate anywhere else.
