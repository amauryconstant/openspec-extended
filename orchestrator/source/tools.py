"""Per-tool adapter registry for the extended layer.

OpenSpec ships an ``openspec init --tools`` flag that accepts every
AI-assistant id it knows about (35+ tools as of OpenSpec v1.13.0;
see ``orchestrator/core/source/docs/supported-tools.md``). The extended
layer was, until v1.10.0, hardcoded to two of them — ``opencode`` and
``claude`` — with their layout, dispatch model, and slash-command
spelling baked into ``cli.py``, ``runner.py``, and ``lib/osx.py``.

This module introduces the adapter abstraction that the rest of the
extended layer will read from. A v1.11.0 release adds Cursor / Codex /
Kimi adapters; adding one is a single ``REGISTRY[<tool_id>] = ...``
entry plus, where its layout diverges enough from the opencode
canonical, a new ``commands_style`` / ``commands_ext`` value. Consumers
in v1.10.0 keep their byte-identical behaviour because the two
initial adapters reproduce the existing constants exactly.

Public surface
--------------

``ToolAdapter``
    Frozen dataclass. One instance per supported tool. Each field
    describes a single axis of variation across tools (skills dir,
    command layout, slash-command prefix, runner binary, etc.).

``REGISTRY: dict[str, ToolAdapter]``
    The shipped tool set. Adding a tool = adding an entry here. The
    set is locked by ``tests/unit/test_tool_registry.py``; future
    additions must be explicit.

``_adapter_tokens(adapter) -> dict[str, str]``
    Derive the 5-token ``PLATFORM_TOKENS`` dict for one adapter.
    Source files under ``orchestrator/resources/opencode/`` ship
    ``{{TOKEN}}`` placeholders; the deploy step renders them per
    active tool. Single source of truth: token values are computed
    from adapter fields, not hand-maintained per tool.

``PLATFORM_TOKENS`` and ``TOOL_DIRS``
    Backwards-compat shims. They mirror the same data as
    ``cli.py``'s old constants so Phase 1B can swap ``cli.py``
    consumers to read from this module without an interim
    test-failing diff. Phase 1B rewrites ``cli.py`` to derive
    these from the registry; ``PLATFORM_TOKENS`` and ``TOOL_DIRS``
    here remain so external callers (and the snapshot tests)
    keep working.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

# ---------------------------------------------------------------------------
# Adapter shape
# ---------------------------------------------------------------------------


CommandsStyle = Literal[
    # opencode today: ``.opencode/commands/osx-<id>.md`` flat.
    "flat",
    # future: ``.tool/commands/<id>.md`` flat with a single command file
    # (no skill mirror).
    "namespaced",
    # claude today: ``.claude/commands/osx/<id>.md`` legacy AND
    # ``.claude/skills/osx-<id>/SKILL.md`` modern — dual-emit mirrors
    # upstream OpenSpec's v1.7.0 strategy (current as of v1.13.0).
    "namespaced-with-skill-mirror",
]

RunnerKind = Literal[
    # ``opencode run --command <cmd> --agent <agent> <change>``
    "opencode_run",
    # ``claude --print --dangerously-skip-permissions --model <model> "<prompt>"``
    "claude_print",
    # future: ``<tool> --print --dangerously-skip-permissions "<prompt>"`` —
    # the generic headless shape used by Cursor, Qwen Code, Kiro, and others.
    # Lands in v1.11.0 with the third-party adapters.
    "generic_print",
]


@dataclass(frozen=True)
class ToolAdapter:
    """Per-tool adapter. One instance per supported AI CLI / IDE.

    Field choices for the v1.10.0 two-tool set reproduce today's
    constants in ``cli.py`` byte-for-byte. Phase 1B rewires consumers
    to read from this class; Phase 1C generalises the runner; v1.11.0
    adds third-party adapters (Cursor, Codex, Kimi) that diverge on
    ``commands_ext``, ``skill_prefix``, and ``runner_kind``.
    """

    tool_id: str
    """Stable identifier used everywhere ('opencode', 'claude', 'cursor')."""

    skills_dir: str
    """Project-local root, e.g. ``.opencode`` / ``.claude`` / ``.cursor``.
    Used as ``Path.cwd() / <skills_dir>`` for the deploy target."""

    commands_dir: str
    """Subdirectory under ``<skills_dir>`` where slash-command files
    land. ``'commands'`` for flat layouts, ``'commands/osx'`` for
    Claude's nested legacy form, ``'prompts'`` for tools that store
    commands as prompt files (Kiro, GitHub Copilot)."""

    commands_style: CommandsStyle
    """Drives deploy_command's per-tool branching:
    - ``flat``: ``<skills_dir>/commands/<id>.<commands_ext>``
    - ``namespaced``: ``<skills_dir>/<commands_dir>/<id>.<commands_ext>``
    - ``namespaced-with-skill-mirror``: legacy command file plus a
      ``<skills_dir>/skills/<id>/SKILL.md`` skill mirror.
    """

    commands_ext: str
    """File extension for command files. ``'md'`` today; future
    adapters may need ``'toml'`` (Qwen Code) or ``'prompt.md'``
    (Kiro, GitHub Copilot)."""

    slash_prefix: str
    """Slash-command prefix the tool registers commands under.
    ``'osx-'`` for opencode (filename-derived), ``'osx:'`` for
    claude (nested-dir-derived). Future tools may use other forms
    (e.g. ``'$'`` for Codex, ``'/skill:'`` for Kimi)."""

    skill_prefix: str
    """How the tool invokes a skill by name. ``'/'`` for opencode
    and claude; ``'/skill:'`` for Kimi; ``'$'`` for Codex. The
    prefix is applied to skill directory names — ``<prefix>osx-...``.
    """

    runner_binary: str
    """Binary the orchestrator spawns to dispatch an AI phase.
    ``'opencode'`` and ``'claude'`` today; future adapters point at
    their tool's CLI (e.g. ``'cursor'``, ``'qwen'``)."""

    runner_kind: RunnerKind
    """Drives ``runner.detect_runner`` and the per-adapter
    ``<Kind>Runner.run()`` implementation.
    ``opencode_run`` and ``claude_print`` have bespoke classes
    today; ``generic_print`` lands with the v1.11.0 third-party
    adapters."""

    has_agents_dir: bool
    """Whether the tool exposes an ``agents/`` subdirectory used by
    the orchestrator's dispatch model. ``opencode`` does; ``claude``
    does not (Claude Code's session model is agent-per-conversation,
    not on-disk agent definitions)."""

    agent_field_transform: Callable[[str], str] | None
    """Transform applied to a command file's frontmatter ``agent:``
    line during deploy. ``None`` = strip the line (claude's case;
    opencode ships the literal ``agent:`` through). Future adapters
    may rewrite ``agent:`` to a tool-specific equivalent (e.g.
    Anthropic-style ``subagent_type:``)."""

    docs_file: str
    """Filename the tool reads for project documentation. Most tools
    use ``AGENTS.md``; Claude Code uses ``CLAUDE.md``. The token
    ``{{DOCS_FILE}}`` resolves to this value at deploy time."""

    tool_name: str
    """Human-readable display name used in log lines and install
    hints: ``'OpenCode'``, ``'Claude Code'``, ``'Cursor'``, etc."""

    detect_paths: tuple[str, ...]
    """Directory names whose presence at ``project_root`` marks the
    tool as active. ``detect_platform`` / ``detect_runner`` walk
    ``REGISTRY`` in registration order and return the first adapter
    whose ``detect_paths`` include an existing directory. Opencode
    wins ties by being registered first."""


# ---------------------------------------------------------------------------
# Token derivation
# ---------------------------------------------------------------------------


def _adapter_tokens(adapter: ToolAdapter) -> dict[str, str]:
    """Derive the 5-token ``PLATFORM_TOKENS`` dict for one adapter.

    Single source of truth: token values are computed from
    ``ToolAdapter`` fields, not hand-maintained per tool. The dict
    shape (keys, value types) is preserved exactly so the existing
    ``tests/unit/test_token_substitution.py`` snapshots stay green
    after Phase 1B rewires ``cli.py``.

    The five tokens cover everything that varies between opencode and
    claude in today's shipped resources:

    - ``ASK_TOOL``: the user-question tool name (``AskUserQuestion``
      / ``Ask``).
    - ``DOCS_FILE``: project documentation filename (``AGENTS.md`` /
      ``CLAUDE.md``).
    - ``CMD_PREFIX``: slash-command prefix (``osx-`` / ``osx:``).
    - ``TOOL_NAME``: human-readable tool name in log lines
      (``OpenCode`` / ``Claude Code``).
    - ``PLATFORM_DIR``: the skills_dir (``{{PLATFORM_DIR}}`` is
      substituted literally into ``.opencode/`` / ``.claude/``
      prose references).

    Forward-compat: the underlying ``_substitute_tokens`` in
    ``cli.py`` leaves unknown tokens verbatim, so a future adapter
    that needs a sixth token can extend this dict without breaking
    earlier tokens.
    """
    return {
        "ASK_TOOL": _adapter_ask_tool(adapter),
        "DOCS_FILE": adapter.docs_file,
        "CMD_PREFIX": adapter.slash_prefix,
        "TOOL_NAME": adapter.tool_name,
        "PLATFORM_DIR": adapter.skills_dir,
    }


def _adapter_ask_tool(adapter: ToolAdapter) -> str:
    """Resolve the ask-tool token for an adapter.

    Today both shipped tools have a distinct ask tool name
    (``AskUserQuestion`` for opencode, ``Ask`` for claude). The
    mapping lives here as the single point of truth; future
    adapters default to ``'AskUserQuestion'`` unless overridden
    by a per-adapter field added in v1.11.0+."""
    if adapter.tool_id == "opencode":
        return "AskUserQuestion"
    if adapter.tool_id == "claude":
        return "Ask"
    return "AskUserQuestion"


# ---------------------------------------------------------------------------
# Shipped adapters
# ---------------------------------------------------------------------------


REGISTRY: dict[str, ToolAdapter] = {
    "opencode": ToolAdapter(
        tool_id="opencode",
        skills_dir=".opencode",
        commands_dir="commands",
        commands_style="flat",
        commands_ext="md",
        slash_prefix="osx-",
        skill_prefix="/",
        runner_binary="opencode",
        runner_kind="opencode_run",
        has_agents_dir=True,
        agent_field_transform=None,  # ship the literal `agent:` through
        docs_file="AGENTS.md",
        tool_name="OpenCode",
        detect_paths=(".opencode",),
    ),
    "claude": ToolAdapter(
        tool_id="claude",
        skills_dir=".claude",
        commands_dir="commands/osx",  # nested for legacy dual-emit
        commands_style="namespaced-with-skill-mirror",
        commands_ext="md",
        slash_prefix="osx:",
        skill_prefix="/",
        runner_binary="claude",
        runner_kind="claude_print",
        has_agents_dir=False,
        agent_field_transform=None,  # strip `agent:` via the claude-only build helper
        docs_file="CLAUDE.md",
        tool_name="Claude Code",
        detect_paths=(".claude",),
    ),
}


# ---------------------------------------------------------------------------
# Backwards-compat shims
# ---------------------------------------------------------------------------
#
# ``cli.py`` (and external callers, and the snapshot tests) read
# ``PLATFORM_TOKENS`` and ``TOOL_DIRS`` as top-level constants today.
# Phase 1B rewires ``cli.py`` consumers to derive these from the
# registry; the shims below keep every external reader working
# through the transition. Both dicts are constructed from the
# registry at import time so any change to ``REGISTRY`` propagates
# immediately — there is no hand-maintained copy.


PLATFORM_TOKENS: dict[str, dict[str, str]] = {
    tid: _adapter_tokens(adapter) for tid, adapter in REGISTRY.items()
}


TOOL_DIRS: dict[str, str] = {
    tid: adapter.skills_dir for tid, adapter in REGISTRY.items()
}


__all__ = [
    "PLATFORM_TOKENS",
    "REGISTRY",
    "TOOL_DIRS",
    "CommandsStyle",
    "RunnerKind",
    "ToolAdapter",
    "_adapter_tokens",
]
