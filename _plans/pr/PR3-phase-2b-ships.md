# PR3 — Phase 2B main: ship 4 first-party adapters

**Goal:** Prove the abstraction scales by landing 4 new first-party adapters. Most of the work is *removing* synthetic fixtures, not adding new ones.

**Release:** v1.11.0.

**Effort:** ~3-4 days.

> **Status update — the synthetic `cursor` adapter is already in `tests/unit/test_install_multi.py::cursor_adapter` (commit `e56acaf2`).** That fixture registers a `cursor`-shaped adapter for the duration of the test via `monkeypatch.setitem(REGISTRY, "cursor", synthetic)` and is consumed by `TestParseToolTargetValid::test_accepts_three_tool_inputs` and the `test_install_three_shipped_or_cursor_tools` smoke test. PR3's work is to **promote that fixture to a real `REGISTRY["cursor"]` entry** and remove the monkeypatch plumbing.

---

## New `REGISTRY` entries

Four entries land in this PR. Registration order matters for shared-root arbitration; PR5C adds the test that locks it.

```python
# In orchestrator/source/tools.py, REGISTRY

"cursor": ToolAdapter(
    tool_id="cursor",
    skills_dir=".cursor",
    commands_dir="commands",
    commands_style="flat",
    commands_ext="md",
    slash_prefix="osx-",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install cursor` after installing the Cursor CLI.",
    runner_binary="agent",
    runner_kind="generic_print",
    runner_args=("--force",),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Cursor",
    detect_paths=(".cursor",),
    requires_ide_restart=True,  # Cursor IDE picks up commands only after reload
    shared_skills_root=False,
    setup_note="",
),

"codex": ToolAdapter(
    tool_id="codex",
    skills_dir=".agents",
    commands_dir="",  # skills-only
    commands_style="skills-only",
    commands_ext="md",
    slash_prefix="/",
    skill_prefix="$",
    cross_ref_prefix="$",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install codex` after installing the Codex CLI.",
    runner_binary="codex",
    runner_kind="generic_print",
    runner_args=("--sandbox", "workspace-write"),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={"source": "openspec-extended"},
    docs_file="AGENTS.md",
    tool_name="Codex",
    detect_paths=(".agents",),  # zed MUST register before codex (PR5C adds the test)
    requires_ide_restart=False,
    shared_skills_root=True,  # shared with zed, antigravity, agents
    setup_note="",
),

"kimi": ToolAdapter(
    tool_id="kimi",
    skills_dir=".kimi-code",
    commands_dir="",  # skills-only
    commands_style="skills-only",
    commands_ext="md",
    slash_prefix="/",
    skill_prefix="/skill:",
    cross_ref_prefix="/skill:",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install kimi` after installing the Kimi Code CLI.",
    runner_binary="kimi",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Kimi Code",
    detect_paths=(".kimi-code", ".kimi"),
    requires_ide_restart=False,
    shared_skills_root=False,
    setup_note="",
),

"forgecode": ToolAdapter(
    tool_id="forgecode",
    skills_dir=".forge",
    commands_dir="",  # skills-only
    commands_style="skills-only",
    commands_ext="md",
    slash_prefix="/",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install forgecode` after installing the ForgeCode CLI.",
    runner_binary="forge",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="ForgeCode",
    detect_paths=(".forge",),
    requires_ide_restart=False,
    shared_skills_root=False,
    setup_note="",
),
```

---

## Registration order (locked)

```python
REGISTRY = {
    "opencode": ...,   # always first; canonical adapter; no shared roots
    "claude": ...,     # always second; unique .claude root
    "cursor": ...,     # .cursor — unique
    "codex": ...,      # .agents — shared, registered before zed/antigravity/agents
    "kimi": ...,       # .kimi-code — unique
    "forgecode": ...,  # .forge — unique
    # zed, antigravity, agents land in PR5C, registered AFTER codex in registration order
    # but BEFORE codex in specificity: zed's .zed wins the tie
}
```

The order matters because `detect_platform` walks `REGISTRY` in registration order. With `codex` registered before `zed` (PR5C), a project with both `.agents/skills/` and `.zed/` resolves to `codex` if `zed`'s detection logic doesn't fire first.

**The arbitration rule** (locked by PR5C's `TestDetectPlatformRegistrationOrderIsCanonical`):

> When two adapters could match the same project, the **more specific** `detect_paths` wins. Specifically: a path under `.zed/` wins over `.agents/`, and `.agents/skills/` (a sub-path) wins over `.agents/` (the parent).

This is implemented in PR5C by `detect_platform` walking `REGISTRY` in **specificity order** (sub-paths first) rather than registration order for shared-root collisions. PR3 does not implement this — it relies on PR1's confirmation that the synthetic fixtures resolve correctly under current registration order.

---

## Production changes

### `orchestrator/source/tools.py` (+~150 lines)

Add the 4 `REGISTRY` entries above. Place them in the documented registration order.

---

## Test changes

### `tests/unit/test_tool_registry.py` (+~120 lines)

Update `SHIPPED_TOOLS` to a 6-element frozenset. Add per-tool snapshot tests mirroring the existing `test_opencode_tokens_match_documented_table` pattern:

```python
class TestShippedAdapterTokens:
    @pytest.mark.parametrize("tool_id,expected_tokens", [
        ("opencode", {"ASK_TOOL": "AskUserQuestion", "DOCS_FILE": "AGENTS.md", "CMD_PREFIX": "osx-", "TOOL_NAME": "OpenCode", "PLATFORM_DIR": ".opencode", "SKILL_PREFIX": "/"}),
        ("claude",   {"ASK_TOOL": "Ask",              "DOCS_FILE": "CLAUDE.md", "CMD_PREFIX": "osx:", "TOOL_NAME": "Claude Code", "PLATFORM_DIR": ".claude", "SKILL_PREFIX": "/"}),
        ("cursor",   {"ASK_TOOL": "AskUserQuestion",  "DOCS_FILE": "AGENTS.md", "CMD_PREFIX": "osx-", "TOOL_NAME": "Cursor",      "PLATFORM_DIR": ".cursor", "SKILL_PREFIX": "/"}),
        ("codex",    {"ASK_TOOL": "AskUserQuestion",  "DOCS_FILE": "AGENTS.md", "CMD_PREFIX": "osx-", "TOOL_NAME": "Codex",       "PLATFORM_DIR": ".agents", "SKILL_PREFIX": "$"}),
        ("kimi",     {"ASK_TOOL": "AskUserQuestion",  "DOCS_FILE": "AGENTS.md", "CMD_PREFIX": "osx-", "TOOL_NAME": "Kimi Code",   "PLATFORM_DIR": ".kimi-code", "SKILL_PREFIX": "/skill:"}),
        ("forgecode",{"ASK_TOOL": "AskUserQuestion",  "DOCS_FILE": "AGENTS.md", "CMD_PREFIX": "osx-", "TOOL_NAME": "ForgeCode",   "PLATFORM_DIR": ".forge", "SKILL_PREFIX": "/"}),
    ])
    def test_shipped_adapter_tokens(self, tool_id, expected_tokens):
        adapter = REGISTRY[tool_id]
        actual = _adapter_tokens(adapter)
        for key, expected in expected_tokens.items():
            assert actual[key] == expected, f"{tool_id}: {key} mismatch"
```

### `tests/unit/test_runner_abstraction.py` (-~30 lines)

Remove the synthetic fixture monkeypatching for `cursor`, `codex`, `kimi` — they're now real REGISTRY entries. Replace the synthetic `def test_cursor_*` methods with real tests that read from `REGISTRY["cursor"]`.

### `tests/unit/test_cli_registry_consumers.py` (-~30 lines, +~80 lines)

Same: remove synthetic fixtures; add real tests. New tests:

```python
class TestCodexFrontmatterExtras:
    """Asserts that adapter.frontmatter_extras lands in the deployed SKILL.md."""

    def test_codex_source_marker_appears_in_skill_mirror(self, tmp_path):
        # Synthetic codex adapter with frontmatter_extras={"source": "openspec-extended"}
        # Deploy a SKILL.md via _build_skill_mirror
        # Assert "source: openspec-extended" is in the rendered body
```

### `tests/unit/test_lib_registry_consumers.py` (-~30 lines)

Remove synthetic fixtures; add real tests.

### `tests/unit/test_install_multi.py` (+~50 lines)

Add a smoke test:

```python
def test_install_cursor_opencode_codex(self, tmp_path):
    """Multi-tool install: cursor, opencode, codex, all in one invocation."""
    # Run `openspec-extended install cursor,opencode,codex` against tmp_path
    # Assert .cursor/, .opencode/, .agents/ all have skills
```

---

## Documentation

### `.opencode/rules/per-adapter-rendering.md` (+~40 lines)

Add the 4 new tools to the per-tool layout table. Note the registration order invariant.

### `orchestrator/source/AGENTS.md` (+~15 lines)

Update "Adding a new tool adapter" with the 3 fields added in PR2 (requiring IDE restart, shared skills root, setup note). Note that `codex` is the first user of `shared_skills_root`.

### `orchestrator/source/lib/AGENTS.md` (+~10 lines)

Add a one-paragraph note about the registration-order invariant: "When multiple adapters share `skills_dir`, registration order determines detection priority. See `docs/plans/upstream-parity/02-coverage-matrix.md` for the canonical order."

---

## Acceptance criteria

- `mise run verify` is green.
- `SHIPPED_TOOLS` is a 6-element frozenset.
- `openspec-extended install cursor` works end-to-end (deploys `.cursor/skills/...`, `.cursor/commands/osx-*.md`).
- `openspec-extended install codex` works end-to-end (deploys `.agents/skills/openspec-*/SKILL.md` with `$openspec-propose` references).
- `openspec-extended install kimi` works end-to-end (deploys `.kimi-code/skills/...` with `/skill:openspec-propose` references).
- `openspec-extended install forgecode` works end-to-end (deploys `.forge/skills/...`).
- Codex's `frontmatter_extras={"source": "openspec-extended"}` lands in the deployed SKILL.md.
- Cursor's `requires_ide_restart=True` triggers the post-install hint.
- Shipped `opencode` and `claude` behaviour is unchanged.

---

## Dependencies

- PR1 (Phase 2A) — abstraction validation tests are the safety net.
- PR2 (Phase 2B prep) — the 3 new fields are available.

## Followed by

- PR4 ships 2 more adapters (qwen, kiro) — extension-aware deploy for `.toml` and `.prompt.md`.
- PR5A/5B/5C ship ~27 more adapters in 3 alphabet-split sub-PRs.
- PR6 ships legacy migration + aliases + ~4 Medium-tier adapters.

---

## Codex shared-root caveat

This PR ships `codex` with `detect_paths=(".agents",)`. At this point in the rollout:

- A project with `.opencode/` and `.agents/` resolves to `opencode` (opencode is registered first).
- A project with `.claude/` and `.agents/` resolves to `claude` (claude is registered before codex).
- A project with `.cursor/` and `.agents/` resolves to `cursor` (cursor is registered before codex).
- A project with only `.agents/` resolves to `codex`.

PR5C adds `zed` (which has `.zed/` as a more specific match) and tests the registration-order invariant.

PR6 adds `antigravity` (which has `.agent` as a more specific match — note the singular vs. `.agents/` plural) and the legacy migration.

---

## Forgecode caveat

Forgecode's `runner_binary="forge"` is the ForgeCode CLI binary name. Verify against the live CLI before PR3 lands; if the binary is `forgecode` not `forge`, update the field. The `detect_paths=(".forge",)` is correct per upstream `config.ts:56`.
