# PR5B — Phase 3 part 1, second slice: devin through pi

**Goal:** Ship the second ~10 Low-effort adapters in alphabetical order. Includes `gemini`, which uses `.toml` like qwen.

**Release:** v1.12.0 (second of 3 sub-PRs).

**Effort:** ~1-2 days.

---

## New `REGISTRY` entries (10 tools)

```python
# In orchestrator/source/tools.py, REGISTRY (continuing from PR5A)

"devin": ToolAdapter(
    tool_id="devin",
    skills_dir=".devin",
    commands_dir="workflows",  # Devin uses workflows/ not commands/
    commands_style="flat",
    commands_ext="md",
    slash_prefix="osx-",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install devin` after installing the Devin CLI.",
    runner_binary="devin",
    runner_kind="generic_print",
    runner_args=("--permission-mode", "bypass"),  # bypass for write phases; plan for read-only
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Devin Desktop",
    detect_paths=(".devin", ".windsurf"),  # detects both; .windsurf is legacy
    requires_ide_restart=True,
    shared_skills_root=False,
    setup_note="",
    # legacy_skills_dirs and the .windsurf alias land in PR6
),

"factory": ToolAdapter(
    tool_id="factory",
    skills_dir=".factory",
    commands_dir="commands",
    commands_style="flat",
    commands_ext="md",
    slash_prefix="osx-",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install factory` after installing the Factory Droid CLI.",
    runner_binary="droid",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Factory Droid",
    detect_paths=(".factory",),
    requires_ide_restart=False,
    shared_skills_root=False,
    setup_note="",
),

"gemini": ToolAdapter(
    tool_id="gemini",
    skills_dir=".gemini",
    commands_dir="commands/opsx",
    commands_style="namespaced",
    commands_ext="toml",
    slash_prefix="osx:",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install gemini` after installing the Gemini CLI.",
    runner_binary="gemini",
    runner_kind="generic_print",
    runner_args=("--yolo",),  # auto-approve for write phases
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix="osx-",
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Gemini CLI",
    detect_paths=(".gemini",),
    requires_ide_restart=False,
    shared_skills_root=False,
    setup_note="",
),

"iflow": ToolAdapter(
    tool_id="iflow",
    skills_dir=".iflow",
    commands_dir="commands",
    commands_style="flat",
    commands_ext="md",
    slash_prefix="osx-",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install iflow` after installing the iFlow CLI.",
    runner_binary="iflow",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="iFlow",
    detect_paths=(".iflow",),
    requires_ide_restart=False,
    shared_skills_root=False,
    setup_note="",
),

"junie": ToolAdapter(
    tool_id="junie",
    skills_dir=".junie",
    commands_dir="commands",
    commands_style="flat",
    commands_ext="md",
    slash_prefix="osx-",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install junie` after installing the Junie CLI.",
    runner_binary="junie",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Junie",
    detect_paths=(".junie",),
    requires_ide_restart=True,
    shared_skills_root=False,
    setup_note="",
),

"kilocode": ToolAdapter(
    tool_id="kilocode",
    skills_dir=".kilocode",
    commands_dir="workflows",
    commands_style="flat",
    commands_ext="md",
    slash_prefix="osx-",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install kilocode` after installing the Kilo Code CLI.",
    runner_binary="kilocode",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Kilo Code",
    detect_paths=(".kilocode",),
    requires_ide_restart=True,
    shared_skills_root=False,
    setup_note="",
),

"lingma": ToolAdapter(
    tool_id="lingma",
    skills_dir=".lingma",
    commands_dir="commands/osx",
    commands_style="namespaced",
    commands_ext="md",
    slash_prefix="osx:",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install lingma` after installing the Lingma CLI.",
    runner_binary="lingma",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix="osx-",
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Lingma",
    detect_paths=(".lingma",),
    requires_ide_restart=True,
    shared_skills_root=False,
    setup_note="",
),

"oh-my-pi": ToolAdapter(
    tool_id="oh-my-pi",
    skills_dir=".omp",
    commands_dir="commands",
    commands_style="flat",
    commands_ext="md",
    slash_prefix="osx-",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install oh-my-pi` after installing the Oh My Pi CLI.",
    runner_binary="omp",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Oh My Pi",
    detect_paths=(".omp",),
    requires_ide_restart=False,
    shared_skills_root=False,
    setup_note="",
),

"pi": ToolAdapter(
    tool_id="pi",
    skills_dir=".pi",
    commands_dir="prompts",  # Pi uses prompts/ not commands/
    commands_style="flat",
    commands_ext="md",
    slash_prefix="osx-",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install pi` after installing the Pi CLI.",
    runner_binary="pi",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Pi",
    detect_paths=(".pi",),
    requires_ide_restart=False,
    shared_skills_root=False,
    setup_note="",
),

"codeassistant": ToolAdapter(
    tool_id="codeassistant",
    skills_dir=".codeassistant",
    commands_dir="commands",
    commands_style="flat",
    commands_ext="md",
    slash_prefix="",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install codeassistant` to deploy skills to .codeassistant/skills/.",
    runner_binary="",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="SourceCraft Code Assistant",
    detect_paths=(".codeassistant",),
    requires_ide_restart=True,
    shared_skills_root=False,
    setup_note="SourceCraft is an IDE extension with no slash surface; references are rewritten as natural-language ('the openspec-propose skill').",
),
```

---

## Production changes

### `orchestrator/source/tools.py` (+~300 lines)

Add the 10 REGISTRY entries above.

---

## Test changes

### `tests/unit/test_tool_registry.py` (+~120 lines)

- `SHIPPED_TOOLS` becomes a 26-element frozenset.
- Per-tool snapshot tests for each new entry.

### `tests/unit/test_runner_abstraction.py` (+~100 lines)

- Parametrize `TestDetectRunnerWalksRegistry` over the 10 new tool ids.

### `tests/unit/test_cli_registry_consumers.py` (+~80 lines)

- Per-tool byte-equality snapshot tests.
- `TestGeminiTomlCommands` — verifies the TOML output structure (matches upstream `escapeTomlBasicString` behaviour).

### `tests/integration/test_install_flow.py` (+~30 lines)

- Multi-tool install smoke test.

---

## Documentation

### `.opencode/rules/per-adapter-rendering.md` (+~50 lines)

Add 10 new rows to the per-tool layout table.

---

## Acceptance criteria

- `mise run verify` is green.
- `SHIPPED_TOOLS` is a 26-element frozenset.
- `openspec-extended install devin,factory,gemini,iflow,junie,kilocode,lingma,oh-my-pi,pi,codeassistant` works end-to-end.
- `gemini` deploys TOML command files under `.gemini/commands/opsx/<name>.toml`.
- `codeassistant`'s empty `slash_prefix` results in skill references being rewritten as natural-language prose.
- Shipped `opencode`, `claude`, `cursor`, `codex`, `kimi`, `forgecode`, `qwen`, `kiro` behaviour is unchanged.

---

## Dependencies

- PR1, PR2, PR3, PR4, PR5A must have landed.

## Followed by

- PR5C ships the remaining ~7 adapters (qoder through zed) plus the shared-root arbitration test.

---

## Per-tool quirks

- **devin's `detect_paths=(".devin", ".windsurf")`** — detects both, but `legacy_skills_dirs=(".windsurf",)` and `TOOL_ID_ALIASES["windsurf"]="devin"` only land in PR6. Until then, a user with only `.windsurf/` is detected but not migrated.
- **gemini's TOML output** — must match upstream's `escapeTomlBasicString` / `escapeTomlMultilineBasicString` behaviour. Test with hostile inputs (control chars, CR/LF, lone CRs, quote runs, trailing backslashes).
- **codeassistant's natural-language skill refs** — the upstream `NATURAL_LANGUAGE_SKILL_TOOLS = new Set(['rovodev', 'codeassistant'])` set is hardcoded in `orchestrator/core/source/src/utils/command-references.ts:88`. The openspec-extended equivalent in `cli.py:_rewrite_skill_body_refs` needs to recognise `cross_ref_prefix=""` and route to a natural-language rewrite.
- **codeassistant's empty `runner_binary`** — same caveat as Continue in PR5A.
- **factory's `runner_binary="droid"`** — Factory Droid's CLI binary is `droid`, not `factory`. Verify against the live CLI.
- **oh-my-pi's `runner_binary="omp"`** — OMP's CLI binary is `omp`, not `oh-my-pi` or `omp-cli`. Verify against the live CLI.
- **pi's `commands_dir="prompts"`** — Pi uses prompts/ not commands/. Same pattern as Kiro (PR4).

## Natural-language skill reference handling

Upstream's `command-references.ts:99-103`:

```ts
export function transformToNaturalLanguageSkillReferences(text: string): string {
  return text.replace(/\/opsx:([a-z-]+)/g, (match, commandId: string) => {
    const skillName = COMMAND_TO_SKILL_NAME[commandId];
    return skillName === undefined ? match : `the openspec-${skillName} skill`;
  });
}
```

The openspec-extended equivalent lives in `cli.py:_rewrite_skill_body_refs`. The current implementation (per the agent audit) uses a single regex rewrite; it needs to route to one of three strategies based on `adapter.cross_ref_prefix`:

| Strategy | Trigger | Rewrite |
|----------|---------|---------|
| Slash | `cross_ref_prefix=""` (default) | `/opsx:<cmd>` → `/openspec-<cmd>` |
| Skill-prefix | `cross_ref_prefix="$"` (codex) | `/opsx:<cmd>` → `$openspec-<cmd>` |
| Skill-prefix | `cross_ref_prefix="/skill:"` (kimi) | `/opsx:<cmd>` → `/skill:openspec-<cmd>` |
| Natural-language | `cross_ref_prefix=""` AND `tool_id in NATURAL_LANGUAGE_SKILL_TOOLS` | `/opsx:<cmd>` → `the openspec-<cmd> skill` |

The last case is what codeassistant and rovodev need. The current `_rewrite_skill_body_refs` likely only handles the first three; PR5B needs to add the fourth.

**Implementation:**

```python
NATURAL_LANGUAGE_SKILL_TOOLS = frozenset({"codeassistant", "rovodev"})

def _rewrite_skill_body_refs(text: str, adapter: ToolAdapter) -> str:
    if adapter.tool_id in NATURAL_LANGUAGE_SKILL_TOOLS:
        # Natural-language rewrite
        return re.sub(
            r"/opsx:([a-z-]+)",
            lambda m: f"the openspec-{COMMAND_TO_SKILL_NAME.get(m.group(1), m.group(1))} skill",
            text,
        )
    if adapter.cross_ref_prefix:
        # Skill-prefix rewrite (codex $ / kimi /skill:)
        return re.sub(
            r"/opsx:([a-z-]+)",
            lambda m: f"{adapter.cross_ref_prefix}openspec-{COMMAND_TO_SKILL_NAME.get(m.group(1), m.group(1))}",
            text,
        )
    # Default slash rewrite
    return re.sub(r"/opsx:([a-z-]+)", r"/openspec-\1", text)
```

Add a corresponding test:

```python
def test_codeassistant_uses_natural_language_rewrite(self, tmp_path):
    # Synthetic codeassistant adapter
    # Run deploy_skills with a body containing "/opsx:propose"
    # Assert the rendered body contains "the openspec-propose skill", not "/openspec-propose"
```

## Pre-existing references caveat

The `cli.py:_rewrite_skill_body_refs` function may already handle cross_ref_prefix correctly (the agent audit confirms it's tested in `test_cli_registry_consumers.py:753-786` for kimi's `/skill:`). The natural-language case is the new addition.
