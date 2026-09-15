# PR5A — Phase 3 part 1, first slice: amazon-q through crush

**Goal:** Ship the first ~10 Low-effort adapters in alphabetical order. Continues the bulk-coverage work of Phase 3.

**Release:** v1.12.0 (first of 3 sub-PRs).

**Effort:** ~1-2 days.

---

## New `REGISTRY` entries (10 tools)

```python
# In orchestrator/source/tools.py, REGISTRY

"amazon-q": ToolAdapter(
    tool_id="amazon-q",
    skills_dir=".amazonq",
    commands_dir="commands",
    commands_style="flat",
    commands_ext="md",
    slash_prefix="osx-",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install amazon-q` after installing the Amazon Q Developer CLI.",
    runner_binary="q",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Amazon Q Developer",
    detect_paths=(".amazonq",),
    requires_ide_restart=True,
    shared_skills_root=False,
    setup_note="",
),

"auggie": ToolAdapter(
    tool_id="auggie",
    skills_dir=".augment",
    commands_dir="commands",
    commands_style="flat",
    commands_ext="md",
    slash_prefix="osx-",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install auggie` after installing the Augment CLI.",
    runner_binary="auggie",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Auggie",
    detect_paths=(".augment",),
    requires_ide_restart=False,
    shared_skills_root=False,
    setup_note="",
),

"bob": ToolAdapter(
    tool_id="bob",
    skills_dir=".bob",
    commands_dir="commands",
    commands_style="flat",
    commands_ext="md",
    slash_prefix="osx-",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install bob` after installing the Bob Shell.",
    runner_binary="bob",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Bob Shell",
    detect_paths=(".bob",),
    requires_ide_restart=False,
    shared_skills_root=False,
    setup_note="",
),

"cline": ToolAdapter(
    tool_id="cline",
    skills_dir=".cline",
    commands_dir="commands",
    commands_style="flat",
    commands_ext="md",
    slash_prefix="osx-",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install cline` after installing the Cline CLI.",
    runner_binary="cline",
    runner_kind="generic_print",
    runner_args=("--json", "--auto-approve", "true"),  # Cline's headless mode
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Cline",
    detect_paths=(".cline",),
    requires_ide_restart=True,
    shared_skills_root=False,
    setup_note="",
),

"codeartsagent": ToolAdapter(
    tool_id="codeartsagent",
    skills_dir=".codeartsdoer",
    commands_dir="",
    commands_style="skills-only",
    commands_ext="md",
    slash_prefix="/",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install codeartsagent` after installing the CodeArts CLI.",
    runner_binary="codearts",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="CodeArts",
    detect_paths=(".codeartsdoer",),
    requires_ide_restart=False,
    shared_skills_root=False,
    setup_note="",
),

"codebuddy": ToolAdapter(
    tool_id="codebuddy",
    skills_dir=".codebuddy",
    commands_dir="commands/osx",  # namespaced layout
    commands_style="namespaced",
    commands_ext="md",
    slash_prefix="osx:",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install codebuddy` after installing the CodeBuddy CLI.",
    runner_binary="codebuddy",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix="osx-",  # namespaced layout strips the prefix
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="CodeBuddy Code",
    detect_paths=(".codebuddy",),
    requires_ide_restart=True,
    shared_skills_root=False,
    setup_note="",
),

"command-code": ToolAdapter(
    tool_id="command-code",
    skills_dir=".commandcode",
    commands_dir="commands",
    commands_style="flat",
    commands_ext="md",
    slash_prefix="osx-",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install command-code` after installing the Command Code CLI.",
    runner_binary="commandcode",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Command Code",
    detect_paths=(".commandcode",),
    requires_ide_restart=False,
    shared_skills_root=False,
    setup_note="",
),

"continue": ToolAdapter(
    tool_id="continue",
    skills_dir=".continue",
    commands_dir="prompts",  # Continue uses prompts/ not commands/
    commands_style="flat",
    commands_ext="prompt",  # Continue uses .prompt files (no .md)
    slash_prefix="osx-",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install continue` to add prompt files to .continue/prompts/.",
    runner_binary="",  # no headless CLI for Continue
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Continue",
    detect_paths=(".continue",),
    requires_ide_restart=True,
    shared_skills_root=False,
    setup_note="Continue reads these files only inside the VS Code / JetBrains extension; there is no headless CLI.",
),

"costrict": ToolAdapter(
    tool_id="costrict",
    skills_dir=".cospec",  # NB: directory is .cospec, not .costrict
    commands_dir="openspec/commands",  # nested under openspec/
    commands_style="flat",
    commands_ext="md",
    slash_prefix="osx-",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install costrict` after installing the CoStrict CLI.",
    runner_binary="cos",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="CoStrict",
    detect_paths=(".cospec",),
    requires_ide_restart=True,
    shared_skills_root=False,
    setup_note="",
),

"crush": ToolAdapter(
    tool_id="crush",
    skills_dir=".crush",
    commands_dir="commands/osx",
    commands_style="namespaced",
    commands_ext="md",
    slash_prefix="osx:",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install crush` after installing the Crush CLI.",
    runner_binary="crush",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix="osx-",
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Crush",
    detect_paths=(".crush",),
    requires_ide_restart=True,
    shared_skills_root=False,
    setup_note="",
),
```

---

## Production changes

### `orchestrator/source/tools.py` (+~300 lines)

Add the 10 REGISTRY entries above. Place them in registration order **after** the PR3-shipped entries (`opencode`, `claude`, `cursor`, `codex`, `kimi`, `forgecode`) and before the PR5B/PR5C entries that follow.

---

## Test changes

### `tests/unit/test_tool_registry.py` (+~120 lines)

- Update `SHIPPED_TOOLS` to a 16-element frozenset.
- Add per-tool snapshot tests for each of the 10 new entries (mirroring the PR3 pattern).

### `tests/unit/test_runner_abstraction.py` (+~100 lines)

- Parametrize `TestDetectRunnerWalksRegistry` over the 10 new tool ids.
- Assert each returns a `GenericPrintRunner`.

### `tests/unit/test_cli_registry_consumers.py` (+~80 lines)

- Per-tool byte-equality snapshot tests (matching the existing `test_opencode_tokens_match_documented_table` pattern).

### `tests/integration/test_install_flow.py` (+~30 lines)

- Multi-tool install smoke test: `openspec-extended install amazon-q,auggie,bob,cline,codebuddy` against a tmp project.

---

## Documentation

### `.opencode/rules/per-adapter-rendering.md` (+~50 lines)

Add 10 new rows to the per-tool layout table.

---

## Acceptance criteria

- `mise run verify` is green.
- `SHIPPED_TOOLS` is a 16-element frozenset.
- `openspec-extended install amazon-q,auggie,bob,cline,codeartsagent,codebuddy,command-code,continue,costrict,crush` works end-to-end.
- Per-tool preflight binary probe confirms the binary is on PATH (or warns cleanly when missing).
- Shipped `opencode`, `claude`, `cursor`, `codex`, `kimi`, `forgecode` behaviour is unchanged.

---

## Dependencies

- PR1, PR2, PR3, PR4 must have landed.

## Followed by

- PR5B ships ~10 more Low-effort adapters (devin through pi).
- PR5C ships the remaining ~7 (qoder through zed) plus the shared-root arbitration test.

---

## Per-tool quirks

- **Cline's `runner_args=("--json", "--auto-approve", "true")`** — Cline's headless mode requires explicit JSON output and auto-approval. The argv becomes `cline --json --auto-approve true "<prompt>"`.
- **Continue's empty `runner_binary`** — Continue has no headless CLI; the entry exists only for file generation. The preflight binary probe should skip tools with `runner_binary=""`.
- **CoStrict's `.cospec` directory** — easy typo; the directory is `.cospec` not `.costrict`. The detect path is also `.cospec`.
- **codebuddy's namespaced layout** — `commands_dir="commands/osx"`, `cmd_filename_strip_prefix="osx-"`. This mirrors Claude's dual-emit behaviour.
- **crush's namespaced layout** — same as codebuddy.

## Continuing's `commands_ext="prompt"` caveat

Continue's prompt files have NO `.md` extension — just `.prompt`. Confirm that `_substitute_tokens_in_file:cli.py:380` correctly handles the compound `.prompt` suffix. If `path.suffix` returns `.prompt` for files like `osx-propose.prompt`, the allow-list needs `.prompt` in the set.

The change in PR4 (line 380 of cli.py) should be:

```python
if path.suffix not in (".md", ".toml", ".prompt") and not path.name.endswith(".prompt.md"):
    return
```

This is verified in PR4's `TestSubstituteTokensInPromptFile` test (which this PR does NOT add; it relies on PR4's test as the safety net).

## Continuing's empty `runner_binary` caveat

The preflight binary probe at `orchestrator/source/orchestrator/engine.py:1262` runs `[runner_binary, "--version"]`. For tools with `runner_binary=""` (Continue, GitHub Copilot when no CLI is installed), the probe should skip silently:

```python
if not adapter.runner_binary:
    log_verbose(state, f"Skipping binary probe for {tool_id} (no runner_binary)")
    return
```

This is a 2-line change in `engine.py:validate_skills` (or wherever the probe lives). Add it to PR5A's checklist if not already covered.
