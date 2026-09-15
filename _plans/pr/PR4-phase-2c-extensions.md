# PR4 — Phase 2C: extension-aware deploy + qwen + kiro

**Goal:** Make the deploy path extension-aware so Qwen Code's `.toml` commands and Kiro's `.prompt.md` files work. Lands 2 more adapters.

**Release:** v1.11.x patch (lands after PR3 ships; same minor line if calendar permits, else v1.11.1).

**Effort:** ~1-2 days.

---

## Why this PR exists

The deploy path is currently `.md`-only:

- `_substitute_tokens_in_file:cli.py:380-387` hardcodes `if path.suffix != ".md": return`.
- `get_target_path:cli.py:318-338` hardcodes `f"{name}.md"` for commands.
- `purge_managed_resources:cli.py:925-940` (flat branch) hardcodes `.md` matching.

Qwen Code uses `.toml` command files (`orchestrator/core/source/src/core/command-generation/adapters/qwen.ts:20`). Kiro uses `.prompt.md` files (`orchestrator/core/source/src/core/command-generation/adapters/kiro.ts:16`).

The `{{TOKEN}}` substitution grammar is format-agnostic — same regex works on `.toml`, `.prompt.md`, and any UTF-8 text. The change is purely about extending the file-matching logic.

---

## Production changes

### `orchestrator/source/cli.py` `_substitute_tokens_in_file` (+~10 lines)

Currently:

```python
def _substitute_tokens_in_file(path: Path, tool: str) -> None:
    """Rewrite ``path`` in place with ``{{TOKEN}}`` values for ``tool``.

    Non-``.md`` files are skipped silently — only text files carry tokens.
    """
    if path.suffix != ".md":
        return
    path.write_text(_substitute_tokens(path.read_text(), tool))
```

After:

```python
def _substitute_tokens_in_file(path: Path, tool: str) -> None:
    """Rewrite ``path`` in place with ``{{TOKEN}}`` values for ``tool``.

    Files with a known text extension are token-substituted in place.
    Other extensions are skipped silently. Extension list matches
    ``CommandsStyle`` requirements: ``.md`` (opencode, claude, kimi, ...),
    ``.toml`` (qwen), ``.prompt.md`` (kiro, github-copilot),
    ``.prompt`` (continue).
    """
    if path.suffix not in (".md", ".toml", ".prompt") and not path.name.endswith(".prompt.md"):
        return
    path.write_text(_substitute_tokens(path.read_text(), tool))
```

### `orchestrator/source/cli.py` `get_target_path` (+~5 lines)

Currently:

```python
def get_target_path(resource_type: str, target_dir: Path, name: str) -> Path:
    if resource_type == "skills":
        return target_dir / "skills" / name
    elif resource_type == "commands":
        cmd_path = target_dir / "commands" / f"{name}.md"
        ...
```

After (the change is for the `commands` branch only):

```python
def get_target_path(resource_type: str, target_dir: Path, name: str, commands_ext: str = "md") -> Path:
    if resource_type == "skills":
        return target_dir / "skills" / name
    elif resource_type == "commands":
        cmd_path = target_dir / "commands" / f"{name}.{commands_ext}"
        ...
```

Callers pass `commands_ext=adapter.commands_ext`.

### `orchestrator/source/cli.py` `purge_managed_resources` (+~10 lines)

Currently (lines 925-940):

```python
if adapter.commands_style == "flat":
    # Flat layout: commands/<name>.md
    for entry in commands_dir.iterdir():
        if not (entry.is_file() or entry.is_symlink()):
            continue
        stem = entry.stem
        ...
```

After:

```python
if adapter.commands_style == "flat":
    # Flat layout: commands/<name>.<commands_ext>
    cmd_suffix = "." + adapter.commands_ext
    for entry in commands_dir.iterdir():
        if not (entry.is_file() or entry.is_symlink()):
            continue
        stem = entry.stem
        # .prompt.md files have a compound stem; strip the .md suffix
        if adapter.commands_ext == "prompt.md" and stem.endswith(".prompt"):
            stem = stem[:-len(".prompt")]
        ...
```

### `orchestrator/source/tools.py` (+~50 lines)

Add 2 REGISTRY entries (qwen, kiro):

```python
"qwen": ToolAdapter(
    tool_id="qwen",
    skills_dir=".qwen",
    commands_dir="commands",
    commands_style="flat",
    commands_ext="toml",  # Qwen Code uses TOML for command files
    slash_prefix="osx-",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install qwen` after installing the Qwen Code CLI.",
    runner_binary="qwen",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Qwen Code",
    detect_paths=(".qwen",),
    requires_ide_restart=False,
    shared_skills_root=False,
    setup_note="",
),

"kiro": ToolAdapter(
    tool_id="kiro",
    skills_dir=".kiro",
    commands_dir="prompts",  # Kiro uses prompts/ not commands/
    commands_style="flat",
    commands_ext="prompt.md",  # Kiro uses .prompt.md extension
    slash_prefix="osx-",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install kiro` after installing the Kiro CLI.",
    runner_binary="kiro-cli",
    runner_kind="generic_print",
    runner_args=(),  # confirm against live spec
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Kiro",
    detect_paths=(".kiro",),
    requires_ide_restart=True,
    shared_skills_root=False,
    setup_note="",
),
```

---

## Test changes

### `TestSubstituteTokensInTomlFile` (+~25 lines)

```python
def test_toml_file_is_substituted(self, tmp_path):
    toml_file = tmp_path / "opsx-propose.toml"
    toml_file.write_text('description = "{{TOOL_NAME}}"\nprompt = """{{PLATFORM_DIR}}"""')
    _substitute_tokens_in_file(toml_file, "qwen")
    content = toml_file.read_text()
    assert "{{TOOL_NAME}}" not in content
    assert "Qwen Code" in content
    assert "{{PLATFORM_DIR}}" not in content
    assert ".qwen" in content
```

### `TestPurgeManagedResourcesRespectsCommandsExt` (+~25 lines)

```python
def test_toml_stale_files_are_purged(self, tmp_path):
    target = tmp_path / ".qwen"
    target.mkdir()
    (target / "commands").mkdir()
    stale = target / "commands" / "opsx-stale.toml"
    stale.write_text('description = "stale"')
    removed = purge_managed_resources(
        target, "qwen",
        keep_names=set(),
        prefixes=("opsx-",),  # NB: qwen / forgecode use 'opsx-' not 'osx-' as the managed prefix
    )
    assert removed == 1
    assert not stale.exists()
```

> **Note on the prefix**: qwen / kiro / github-copilot use `opsx-` (upstream's `OpenSpec` prefix), not `osx-` (our extended prefix). The slash prefix `osx-` is for the OS-level command name; the on-disk filename prefix is `opsx-` because we deploy OpenSpec-managed files. This is consistent with upstream's adapter behaviour.

### `TestKiroPromptsLayout` (+~25 lines)

```python
def test_kiro_deploys_prompts_subdir(self, tmp_path):
    # Synthetic kiro adapter
    # Run deploy_commands
    # Assert target/.kiro/prompts/osx-propose.prompt.md exists
```

### `TestQwenTomlCommands` (+~25 lines)

```python
def test_qwen_deploys_toml_commands(self, tmp_path):
    # Synthetic qwen adapter with commands_ext="toml"
    # Run deploy_commands
    # Assert target/.qwen/commands/osx-propose.toml exists
```

---

## Documentation

### `.opencode/rules/per-adapter-rendering.md` (+~20 lines)

Add a "Commands extensions" subsection listing the four supported extensions and which tools use which. Note that the substitution helper is format-agnostic.

---

## Acceptance criteria

- `mise run verify` is green.
- `openspec-extended install qwen` deploys `.toml` command files under `.qwen/commands/`.
- `openspec-extended install kiro` deploys `.prompt.md` files under `.kiro/prompts/`.
- `purge_managed_resources` correctly cleans `.toml` and `.prompt.md` files (not just `.md`).
- `_substitute_tokens_in_file` accepts `.toml`, `.prompt.md`, `.prompt`, and `.md` (the four `commands_ext` values across the 39 tools).
- Shipped `opencode` and `claude` behaviour is unchanged.

---

## Dependencies

- PR1, PR2, PR3 must have landed.

## Followed by

- PR5A/5B/5C ship the bulk of the remaining Low-effort adapters. `gemini` (PR5B) uses `.toml` like qwen and reuses PR4's extension plumbing.

---

## Format-collision risk mitigation

Before PR4 lands, run a live contract test against the Qwen Code and Kiro CLIs:

1. Deploy a known-shape `osx-propose.toml` to a test project.
2. Invoke `qwen /osx-propose` (or whatever Qwen's slash form is).
3. Assert the command resolves and the prompt is interpreted correctly.

The same for Kiro with `.prompt.md`. If the TOML/YAML/Markdown parser chokes on a `{{TOKEN}}` that survived substitution, document it in the per-tool adapter docstring and add a per-format token allow-list.

`_substitute_tokens:cli.py:128-129` already leaves unknown tokens verbatim, which is safe for unknown TOML keys but may collide with the host format's own placeholder grammar. The contract tests are the empirical check.

---

## Future extension additions

After PR4, adding a new `commands_ext` to the registry (e.g. `.json`) requires:

1. Update the `_substitute_tokens_in_file` extension allow-list.
2. Update `get_target_path` if the extension is non-standard.
3. Update `purge_managed_resources` flat branch if the extension affects filename matching.
4. Add a `TestSubstituteTokensIn<Ext>` and `TestPurgeManagedResourcesRespectsCommandsExt` test.

This is the smallest viable change pattern. Document it in `orchestrator/source/AGENTS.md` under "Adding a new tool adapter".
