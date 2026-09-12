#!/usr/bin/env python3
"""Snapshot tests for the per-tool adapter registry.

Phase 1A introduces ``orchestrator/source/tools.py`` as the single
source of truth for tool-specific behaviour in the extended layer.
These tests pin the registry's shape, the per-adapter field values,
and the backwards-compat shims (``PLATFORM_TOKENS`` / ``TOOL_DIRS``)
that Phase 1B will use to rewire ``cli.py`` consumers.

Adding a third tool = an explicit ``REGISTRY[<id>] = ToolAdapter(...)``
entry plus a deliberate edit to the snapshot below. The tests here
exist to catch accidental drift — if anyone modifies the registry
without updating the snapshot, one of these tests fails loudly.
"""

from __future__ import annotations

import pytest
from source.tools import (
    PLATFORM_TOKENS,
    REGISTRY,
    TOOL_DIRS,
    ToolAdapter,
    _adapter_tokens,
)

pytestmark = pytest.mark.unit


# v1.10.0 contract: the shipped set is exactly opencode + claude.
# v1.11.0 adds cursor / codex / kimi; that release must update this
# set and the corresponding per-tool snapshots below.
SHIPPED_TOOLS = frozenset({"opencode", "claude"})


class TestRegistryShape:
    """The registry exposes the exact tool set we ship."""

    def test_registry_keys_match_shipped_set(self):
        assert set(REGISTRY) == SHIPPED_TOOLS, (
            f"Registry drifted from SHIPPED_TOOLS. Expected {sorted(SHIPPED_TOOLS)}, "
            f"got {sorted(REGISTRY)}. Adding a new adapter is intentional; update "
            f"SHIPPED_TOOLS in this test file alongside the new entry."
        )

    def test_each_value_is_a_tool_adapter(self):
        for tid, adapter in REGISTRY.items():
            assert isinstance(adapter, ToolAdapter), (
                f"{tid!r} registry value is {type(adapter).__name__}, expected ToolAdapter"
            )

    def test_each_tool_id_matches_its_key(self):
        for tid, adapter in REGISTRY.items():
            assert adapter.tool_id == tid, (
                f"Registry key {tid!r} maps to an adapter whose tool_id "
                f"is {adapter.tool_id!r}"
            )

    def test_skills_dir_is_dotfile_path(self):
        for tid, adapter in REGISTRY.items():
            assert adapter.skills_dir.startswith(".") and "/" not in adapter.skills_dir, (
                f"{tid}: skills_dir {adapter.skills_dir!r} must be a top-level dotfile"
            )

    def test_commands_ext_is_nonempty(self):
        for tid, adapter in REGISTRY.items():
            assert adapter.commands_ext, f"{tid}: commands_ext must be set"


class TestSkillsDirParity:
    """``TOOL_DIRS`` (the legacy ``cli.py`` constant) must match the
    registry's ``skills_dir`` for every shipped tool. Phase 1B
    removes the legacy constant; this test catches any premature
    drift before that lands.
    """

    def test_tooldirs_keys_match_registry(self):
        assert set(TOOL_DIRS) == set(REGISTRY)

    @pytest.mark.parametrize("tool_id", sorted(SHIPPED_TOOLS))
    def test_tooldirs_value_matches_adapter_skills_dir(self, tool_id):
        assert TOOL_DIRS[tool_id] == REGISTRY[tool_id].skills_dir


class TestTokenSubstitutionParity:
    """``PLATFORM_TOKENS`` (the legacy ``cli.py`` constant) must equal
    ``_adapter_tokens(<adapter>)`` for every shipped tool. Pins the
    deploy-time substitution table byte-for-byte.
    """

    @pytest.mark.parametrize("tool_id", sorted(SHIPPED_TOOLS))
    def test_platform_tokens_value_matches_adapter_tokens(self, tool_id):
        assert PLATFORM_TOKENS[tool_id] == _adapter_tokens(REGISTRY[tool_id])

    def test_opencode_tokens_match_documented_table(self):
        # Mirrors cli.py:38-53 verbatim. If the deploy table changes,
        # this test (and the deployed files) fail in lockstep.
        assert PLATFORM_TOKENS["opencode"] == {
            "ASK_TOOL": "AskUserQuestion",
            "DOCS_FILE": "AGENTS.md",
            "CMD_PREFIX": "osx-",
            "TOOL_NAME": "OpenCode",
            "PLATFORM_DIR": ".opencode",
        }

    def test_claude_tokens_match_documented_table(self):
        assert PLATFORM_TOKENS["claude"] == {
            "ASK_TOOL": "Ask",
            "DOCS_FILE": "CLAUDE.md",
            "CMD_PREFIX": "osx:",
            "TOOL_NAME": "Claude Code",
            "PLATFORM_DIR": ".claude",
        }

    def test_all_adapters_have_full_token_set(self):
        documented = {"ASK_TOOL", "DOCS_FILE", "CMD_PREFIX", "TOOL_NAME", "PLATFORM_DIR"}
        for tid, tokens in PLATFORM_TOKENS.items():
            assert documented.issubset(tokens), (
                f"{tid}: tokens missing {documented - tokens}"
            )


class TestAdapterDispatchAttributes:
    """Per-tool fields that drive cli.py / runner.py / engine.py
    dispatch. Each test pins one axis of variation; together they
    describe the deploy + run contract."""

    def test_opencode_uses_flat_commands(self):
        assert REGISTRY["opencode"].commands_style == "flat"

    def test_claude_dual_emits_via_nested_skill_mirror(self):
        assert REGISTRY["claude"].commands_style == "namespaced-with-skill-mirror"

    def test_opencode_commands_dir_is_flat_root(self):
        assert REGISTRY["opencode"].commands_dir == "commands"

    def test_claude_commands_dir_nests_under_osx(self):
        assert REGISTRY["claude"].commands_dir == "commands/osx"

    def test_opencode_has_agents_dir(self):
        assert REGISTRY["opencode"].has_agents_dir is True

    def test_claude_has_no_agents_dir(self):
        assert REGISTRY["claude"].has_agents_dir is False

    def test_opencode_uses_opencode_run_dispatch(self):
        assert REGISTRY["opencode"].runner_kind == "opencode_run"
        assert REGISTRY["opencode"].runner_binary == "opencode"

    def test_claude_uses_claude_print_dispatch(self):
        assert REGISTRY["claude"].runner_kind == "claude_print"
        assert REGISTRY["claude"].runner_binary == "claude"

    def test_opencode_slash_prefix_uses_hyphen(self):
        assert REGISTRY["opencode"].slash_prefix == "osx-"

    def test_claude_slash_prefix_uses_colon(self):
        assert REGISTRY["claude"].slash_prefix == "osx:"

    def test_slash_prefix_differs_between_shipped_tools(self):
        # Sanity check: the two shipped tools must not collide on the
        # slash-command space. If they ever did, deploy would clobber
        # commands on the wrong platform.
        assert (
            REGISTRY["opencode"].slash_prefix
            != REGISTRY["claude"].slash_prefix
        )

    def test_skill_prefix_is_slash_for_both_shipped_tools(self):
        # Both opencode and claude expose skills as ``/<skill-name>``.
        # Future v1.11.0 adapters (Codex, Kimi) diverge here.
        assert REGISTRY["opencode"].skill_prefix == "/"
        assert REGISTRY["claude"].skill_prefix == "/"

    def test_docs_file_opencode_uses_agents_md(self):
        assert REGISTRY["opencode"].docs_file == "AGENTS.md"

    def test_docs_file_claude_uses_claude_md(self):
        assert REGISTRY["claude"].docs_file == "CLAUDE.md"

    def test_tool_name_opencode(self):
        assert REGISTRY["opencode"].tool_name == "OpenCode"

    def test_tool_name_claude(self):
        assert REGISTRY["claude"].tool_name == "Claude Code"

    def test_detect_paths_opencode(self):
        assert REGISTRY["opencode"].detect_paths == (".opencode",)

    def test_detect_paths_claude(self):
        assert REGISTRY["claude"].detect_paths == (".claude",)

    def test_detect_paths_are_unique_across_shipped_tools(self):
        # ``detect_runner`` walks ``REGISTRY`` in registration order
        # and returns the first match. Distinct paths ensure each
        # tool is uniquely identifiable; collisions silently shadow
        # earlier adapters.
        all_paths = [p for a in REGISTRY.values() for p in a.detect_paths]
        assert len(all_paths) == len(set(all_paths)), (
            f"detect_paths overlap across shipped tools: {all_paths}"
        )

    def test_commands_ext_md_for_shipped_tools(self):
        # Both shipped tools use ``.md`` for command files. v1.11.0
        # adds ``.toml`` (Qwen Code) and ``.prompt.md`` (Kiro).
        assert REGISTRY["opencode"].commands_ext == "md"
        assert REGISTRY["claude"].commands_ext == "md"


class TestAdapterTokensAreConsistent:
    """Cross-checks between adapter fields and the derived token dict."""

    def test_cmd_prefix_token_matches_slash_prefix(self):
        for tid, adapter in REGISTRY.items():
            tokens = _adapter_tokens(adapter)
            assert tokens["CMD_PREFIX"] == adapter.slash_prefix, (
                f"{tid}: CMD_PREFIX token {tokens['CMD_PREFIX']!r} != "
                f"slash_prefix {adapter.slash_prefix!r}"
            )

    def test_docs_file_token_matches_docs_file_field(self):
        for adapter in REGISTRY.values():
            tokens = _adapter_tokens(adapter)
            assert tokens["DOCS_FILE"] == adapter.docs_file

    def test_tool_name_token_matches_tool_name_field(self):
        for adapter in REGISTRY.values():
            tokens = _adapter_tokens(adapter)
            assert tokens["TOOL_NAME"] == adapter.tool_name

    def test_platform_dir_token_matches_skills_dir(self):
        for adapter in REGISTRY.values():
            tokens = _adapter_tokens(adapter)
            assert tokens["PLATFORM_DIR"] == adapter.skills_dir
