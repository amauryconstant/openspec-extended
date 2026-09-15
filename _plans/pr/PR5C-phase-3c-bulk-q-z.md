# PR5C — Phase 3 part 1, third slice: qoder through zed + agents

**Goal:** Ship the final ~7 Low-effort adapters plus the vendor-neutral `agents` target. **Critical:** this PR ships the shared-root arbitration test that locks the registration order invariant.

**Release:** v1.12.0 (third of 3 sub-PRs).

**Effort:** ~1-2 days.

---

## New `REGISTRY` entries (8 tools — 7 alphabetical + `agents`)

```python
# In orchestrator/source/tools.py, REGISTRY (continuing from PR5B)

"qoder": ToolAdapter(
    tool_id="qoder",
    skills_dir=".qoder",
    commands_dir="commands/osx",
    commands_style="namespaced",
    commands_ext="md",
    slash_prefix="osx:",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install qoder` after installing the Qoder CLI.",
    runner_binary="qoder",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix="osx-",
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Qoder",
    detect_paths=(".qoder",),
    requires_ide_restart=True,
    shared_skills_root=False,
    setup_note="",
),

"rovodev": ToolAdapter(
    tool_id="rovodev",
    skills_dir=".rovodev",
    commands_dir="",
    commands_style="skills-only",
    commands_ext="md",
    slash_prefix="",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install rovodev` to deploy skills to .rovodev/skills/.",
    runner_binary="acli",
    runner_kind="generic_print",
    runner_args=("rovodev", "run", "--yolo"),  # acli rovodev run --yolo "<prompt>"
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Rovo Dev CLI",
    detect_paths=(".rovodev", ".rovodev/skills"),
    requires_ide_restart=False,
    shared_skills_root=False,
    setup_note="Rovo Dev CLI is invoked as `acli rovodev run --yolo \"<prompt>\"` — not as a standalone binary.",
),

"roocode": ToolAdapter(
    tool_id="roocode",
    skills_dir=".roo",
    commands_dir="commands",
    commands_style="flat",
    commands_ext="md",
    slash_prefix="osx-",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install roocode` after installing the Zoo Code CLI.",
    runner_binary="roo",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Zoo Code",
    detect_paths=(".roo",),
    requires_ide_restart=True,
    shared_skills_root=False,
    setup_note="",
),

"trae": ToolAdapter(
    tool_id="trae",
    skills_dir=".trae",
    commands_dir="commands",
    commands_style="flat",
    commands_ext="md",
    slash_prefix="osx-",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install trae` after installing the Trae CLI.",
    runner_binary="trae",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Trae",
    detect_paths=(".trae",),
    requires_ide_restart=True,
    shared_skills_root=False,
    setup_note="",
),

"vibe": ToolAdapter(
    tool_id="vibe",
    skills_dir=".vibe",
    commands_dir="",
    commands_style="skills-only",
    commands_ext="md",
    slash_prefix="/",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install vibe` after installing the Mistral Vibe CLI.",
    runner_binary="vibe",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Mistral Vibe",
    detect_paths=(".vibe",),
    requires_ide_restart=False,
    shared_skills_root=False,
    setup_note="",
),

"zcode": ToolAdapter(
    tool_id="zcode",
    skills_dir=".zcode",
    commands_dir="commands/osx",
    commands_style="namespaced",
    commands_ext="md",
    slash_prefix="osx:",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install zcode` after installing the ZCode CLI.",
    runner_binary="zcode",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix="osx-",
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="ZCode",
    detect_paths=(".zcode",),
    requires_ide_restart=False,
    shared_skills_root=False,
    setup_note="",
),

"zed": ToolAdapter(
    tool_id="zed",
    skills_dir=".agents",  # shared with codex, antigravity, agents
    commands_dir="",
    commands_style="skills-only",
    commands_ext="md",
    slash_prefix="/",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install zed` to deploy skills to .agents/skills/.",
    runner_binary="",  # Zed has no headless CLI; IDE only
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Zed Agent",
    detect_paths=(".zed", ".agents/skills"),  # more specific than codex/antigravity
    requires_ide_restart=True,
    shared_skills_root=True,
    setup_note="Zed Agent is an IDE extension with no headless CLI; skills are loaded at IDE startup.",
),

# Vendor-neutral agent target — must register LAST
"agents": ToolAdapter(
    tool_id="agents",
    skills_dir=".agents",
    commands_dir="",
    commands_style="skills-only",
    commands_ext="md",
    slash_prefix="/",
    skill_prefix="/",
    cross_ref_prefix="",
    ask_tool="AskUserQuestion",
    install_hint="Run `openspec-extended install agents` to deploy vendor-neutral skills to .agents/skills/.",
    runner_binary="",
    runner_kind="generic_print",
    runner_args=(),
    has_agents_dir=False,
    agent_field_transform=strip_agent_line,
    inject_name_in_skill_mirror=False,
    cmd_filename_strip_prefix=None,
    frontmatter_extras={},
    docs_file="AGENTS.md",
    tool_name="Shared .agents skills",
    detect_paths=(".agents/skills",),  # sub-path; more specific than codex's .agents
    requires_ide_restart=False,
    shared_skills_root=True,
    setup_note="Vendor-neutral target for tools that share the .agents/skills/ root (Zed, vendor-neutral agent platforms).",
),
```

---

## Registration order (final canonical)

```python
REGISTRY = {
    # Phase 1A — original shipped
    "opencode": ...,
    "claude": ...,
    # PR3 — Phase 2B main
    "cursor": ...,
    "codex": ...,        # .agents — must register before zed/antigravity/agents
    "kimi": ...,
    "forgecode": ...,
    # PR4 — Phase 2C
    "qwen": ...,
    "kiro": ...,
    # PR5A — Phase 3a
    "amazon-q": ...,
    "auggie": ...,
    "bob": ...,
    "cline": ...,
    "codeartsagent": ...,
    "codebuddy": ...,
    "command-code": ...,
    "continue": ...,
    "costrict": ...,
    "crush": ...,
    # PR5B — Phase 3b
    "devin": ...,
    "factory": ...,
    "gemini": ...,
    "iflow": ...,
    "junie": ...,
    "kilocode": ...,
    "lingma": ...,
    "oh-my-pi": ...,
    "pi": ...,
    "codeassistant": ...,
    # PR5C — Phase 3c
    "qoder": ...,
    "rovodev": ...,
    "roocode": ...,
    "trae": ...,
    "vibe": ...,
    "zcode": ...,
    "zed": ...,          # .agents/skills — must register AFTER codex but with more specific paths
    "agents": ...,       # .agents/skills — last; vendor-neutral fallback
    # PR6 will add: antigravity (before agents, with .agent as a more specific path)
    # PR7 will add: minimax-code (global skills dir)
}
```

The order matters for shared-root arbitration. Specifically:

- **`zed` registers AFTER `codex`** in iteration order, but `zed.detect_paths=(".zed", ".agents/skills")` is more specific than `codex.detect_paths=(".agents",)`. The current `detect_platform` walks `REGISTRY` in registration order and returns the first match — so `codex` would win ties. PR5C changes this to walk by specificity for shared-root adapters.
- **`agents` registers LAST** as the vendor-neutral fallback for `.agents/skills/` when no other adapter matches.

---

## Production changes

### `orchestrator/source/tools.py` `detect_platform` refactor (+~30 lines)

Currently:

```python
def detect_platform(project_root: Path) -> str:
    for adapter in REGISTRY.values():
        if any((project_root / p).is_dir() for p in adapter.detect_paths):
            return adapter.tool_id
    return next(iter(REGISTRY))
```

After:

```python
def detect_platform(project_root: Path) -> str:
    """Return the active tool id for ``project_root``.

    Walks REGISTRY in registration order, but for shared-root tools
    (those with shared_skills_root=True), sorts by detection-path
    specificity (more specific paths first). The more specific match
    wins, so a project with both ``.zed/`` and ``.agents/skills/``
    resolves to ``zed``, not to ``codex`` or ``agents``.

    Default to the first registered tool id when no marker is present.
    """
    # First pass: walk tools with non-shared roots (registration order)
    for adapter in REGISTRY.values():
        if adapter.shared_skills_root:
            continue
        if any((project_root / p).is_dir() for p in adapter.detect_paths):
            return adapter.tool_id

    # Second pass: walk shared-root tools sorted by specificity (descending)
    shared = [a for a in REGISTRY.values() if a.shared_skills_root]
    shared.sort(key=_specificity_key, reverse=True)
    for adapter in shared:
        if any((project_root / p).is_dir() for p in adapter.detect_paths):
            return adapter.tool_id

    return next(iter(REGISTRY))


def _specificity_key(adapter: ToolAdapter) -> tuple:
    """Sort key for shared-root arbitration.

    More specific paths (sub-paths, longer paths) sort higher. Adapters
    with no detect_paths sort lowest. The exact formula doesn't matter
    as long as it's deterministic and stable across registration order.
    """
    if not adapter.detect_paths:
        return (0, "")
    # Sort by (max number of path segments, sum of lengths)
    return (
        max(p.count("/") for p in adapter.detect_paths),
        sum(len(p) for p in adapter.detect_paths),
    )
```

Same change in `runner.py:detect_runner:88-114`.

### `orchestrator/source/tools.py` REGISTRY additions (+~250 lines)

Add the 8 REGISTRY entries above.

---

## Test changes

### `tests/unit/test_lib_registry_consumers.py` (+~80 lines) — `TestDetectPlatformRegistrationOrderIsCanonical`

```python
class TestDetectPlatformRegistrationOrderIsCanonical:
    """Locks the shared-root arbitration invariant.

    When multiple adapters could match the same project, the more
    specific detect_paths wins. A future contributor who reorders the
    REGISTRY dict must not break this invariant.
    """

    def test_zed_wins_over_codex_when_both_match(self, tmp_path):
        (tmp_path / ".zed").mkdir()
        (tmp_path / ".agents").mkdir()
        (tmp_path / ".agents" / "skills").mkdir()
        assert detect_platform(tmp_path) == "zed"

    def test_codex_wins_when_only_agents_present(self, tmp_path):
        (tmp_path / ".agents").mkdir()
        (tmp_path / ".agents" / "skills").mkdir()
        assert detect_platform(tmp_path) == "codex"

    def test_agents_wins_when_only_skills_dir_present(self, tmp_path):
        (tmp_path / ".agents" / "skills").mkdir()
        assert detect_platform(tmp_path) == "agents"

    def test_opencode_wins_over_anything_else(self, tmp_path):
        (tmp_path / ".opencode").mkdir()
        (tmp_path / ".zed").mkdir()
        (tmp_path / ".agents" / "skills").mkdir()
        assert detect_platform(tmp_path) == "opencode"

    def test_cursor_wins_over_codex(self, tmp_path):
        (tmp_path / ".cursor").mkdir()
        (tmp_path / ".agents").mkdir()
        assert detect_platform(tmp_path) == "cursor"

    def test_specificity_key_orders_by_path_segments(self):
        from source.tools import _specificity_key
        zed = ToolAdapter(tool_id="zed", detect_paths=(".zed", ".agents/skills"), shared_skills_root=True, ...)
        codex = ToolAdapter(tool_id="codex", detect_paths=(".agents",), shared_skills_root=True, ...)
        agents = ToolAdapter(tool_id="agents", detect_paths=(".agents/skills",), shared_skills_root=True, ...)
        # .agents/skills (2 segments) > .zed (1 segment) > .agents (1 segment)
        # But zed also has .zed (1 segment, shorter path)
        # Specificity formula: max segments + sum lengths
        # zed: max(0, 1)=1, sum=4+13=17 → (1, 17)
        # codex: max(0)=0, sum=7 → (0, 7)
        # agents: max(1)=1, sum=13 → (1, 13)
        # zed wins
        sorted_tools = sorted([codex, zed, agents], key=_specificity_key, reverse=True)
        assert sorted_tools[0].tool_id == "zed"
        assert sorted_tools[1].tool_id == "agents"
        assert sorted_tools[2].tool_id == "codex"
```

### `tests/unit/test_tool_registry.py` (+~80 lines)

- `SHIPPED_TOOLS` becomes a 34-element frozenset.
- Per-tool snapshot tests for each new entry.

### `tests/unit/test_runner_abstraction.py` (+~80 lines)

- Parametrize `TestDetectRunnerWalksRegistry` over the 8 new tool ids.
- Mirror `TestDetectPlatformRegistrationOrderIsCanonical` for the runner layer.

### `tests/integration/test_install_flow.py` (+~30 lines)

- Multi-tool install smoke test: `openspec-extended install qoder,rovodev,roocode,trae,vibe,zcode,zed,agents`.

---

## Documentation

### `.opencode/rules/per-adapter-rendering.md` (+~40 lines)

Add 8 new rows to the per-tool layout table.

### `orchestrator/source/lib/AGENTS.md` (+~25 lines)

Document the shared-root arbitration invariant. Reference `TestDetectPlatformRegistrationOrderIsCanonical` and `docs/plans/upstream-parity/02-coverage-matrix.md` for the canonical registration order.

### `orchestrator/source/orchestrator/AGENTS.md` (+~15 lines)

Note that `detect_runner` mirrors the same specificity-based ordering for shared-root adapters.

---

## Acceptance criteria

- `mise run verify` is green.
- `SHIPPED_TOOLS` is a 34-element frozenset.
- `openspec-extended install qoder,rovodev,roocode,trae,vibe,zcode,zed,agents` works end-to-end.
- `TestDetectPlatformRegistrationOrderIsCanonical` passes for all 6 test cases.
- `zed` registers AFTER `codex` in iteration order but wins ties via specificity.
- `agents` registers LAST as the vendor-neutral fallback.
- Shipped `opencode`, `claude`, and all PR3/PR4/PR5A/PR5B entries behave unchanged.

---

## Dependencies

- PR1, PR2, PR3, PR4, PR5A, PR5B must have landed.

## Followed by

- PR6 ships `legacy_skills_dirs`, `TOOL_ID_ALIASES`, the `migrate_legacy_skills_dirs` helper, and 4 Medium-tier adapters (antigravity, github-copilot, hermes, devin-finalised).

---

## Per-tool quirks

- **rovodev's `runner_args=("rovodev", "run", "--yolo")`** — Rovo Dev CLI is invoked through Atlassian's `acli` umbrella command, not as a standalone binary. The argv becomes `acli rovodev run --yolo "<prompt>"`.
- **rovodev's empty `slash_prefix` + natural-language refs** — same as codeassistant (PR5B).
- **zed's empty `runner_binary`** — Zed has no headless CLI; preflight binary probe must skip (per PR5A's caveat).
- **agents' `detect_paths=(".agents/skills",)`** — sub-path only, NOT the bare `.agents/` root. This is intentional: `.agents/` is used for many things beyond skills, so only `.agents/skills/` is the OpenSpec signal.
- **zed's `detect_paths=(".zed", ".agents/skills")`** — includes both the IDE marker (`.zed/`) and the OpenSpec signal (`.agents/skills/`). Either is enough to trigger the detection.

## Specificity key choice

The `_specificity_key` function uses `(max_segment_count, sum_path_lengths)` as a tiebreaker. Alternatives:

- **Path-prefix length**: longer path → more specific. Fails for `.agents/skills/` vs `.zed/` (neither is a prefix of the other).
- **Most-specific-first walk**: walk `detect_paths` for all adapters, sort all matches by path specificity, return the first. More correct but more complex.
- **Registration order with shared_root=True flag**: skip the shared-root pass for tools with `detect_paths` that overlap with a more-specific tool. Implemented here.

The chosen implementation is correct for the current 4 shared-root adapters (codex, zed, antigravity, agents). Future shared-root additions may need a more sophisticated rule; document the limitation in `_specificity_key`'s docstring.

## Why `detect_paths=(".agents/skills",)` for agents, not `.agents/`

The bare `.agents/` directory is used for many things beyond OpenSpec (e.g. agent-specific state, configuration). If we used `.agents/` as the detection path, every project with `.agents/` would resolve to `agents`, even when the user has a specific tool (codex, zed, antigravity) installed. The sub-path `.agents/skills/` is the OpenSpec-specific signal.

Upstream confirms this in `orchestrator/core/source/src/core/config.ts:91` — the `agents` entry uses `detectionPaths: ['.agents/skills']`, not `.agents/`.
