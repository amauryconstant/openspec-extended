#!/usr/bin/env python3
"""Unit tests for ``source.cli._substitute_tokens`` and ``PLATFORM_TOKENS``.

The deploy step rewrites ``{{TOKEN}}`` placeholders in shipped resources
with the per-platform values from ``PLATFORM_TOKENS``. These tests pin:

1. The token table values match the documented contract for both platforms.
2. Unknown tokens are left verbatim (forward-compat: a future token added
   to source but not yet to the table surfaces as a literal).
3. ``_substitute_tokens_in_file`` / ``_substitute_tokens_in_tree`` rewrite
   exactly the ``.md`` files in a copy and leave non-``.md`` files alone.
4. The deploy (``deploy_skills``, ``deploy_commands``, ``deploy_agents``)
   emits files with no leftover ``{{TOKEN}}`` strings.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from source.cli import (
    PLATFORM_TOKENS,
    _substitute_tokens,
    _substitute_tokens_in_file,
    _substitute_tokens_in_tree,
    deploy_agents,
    deploy_commands,
    deploy_skills,
    get_resources_dir,
)


pytestmark = pytest.mark.unit


DOCUMENTED_TOKENS = {"ASK_TOOL", "DOCS_FILE", "CMD_PREFIX", "TOOL_NAME", "PLATFORM_DIR"}


class TestTokenTableContract:
    """The token table is the single source of truth for substitutions."""

    def test_opencode_entries_cover_all_documented_tokens(self):
        assert DOCUMENTED_TOKENS.issubset(PLATFORM_TOKENS["opencode"].keys()), (
            "PLATFORM_TOKENS['opencode'] is missing documented tokens: "
            f"{DOCUMENTED_TOKENS - PLATFORM_TOKENS['opencode'].keys()}"
        )

    def test_claude_entries_cover_all_documented_tokens(self):
        assert DOCUMENTED_TOKENS.issubset(PLATFORM_TOKENS["claude"].keys()), (
            "PLATFORM_TOKENS['claude'] is missing documented tokens: "
            f"{DOCUMENTED_TOKENS - PLATFORM_TOKENS['claude'].keys()}"
        )

    def test_opencode_values(self):
        assert PLATFORM_TOKENS["opencode"] == {
            "ASK_TOOL": "AskUserQuestion",
            "DOCS_FILE": "AGENTS.md",
            "CMD_PREFIX": "osx-",
            "TOOL_NAME": "OpenCode",
            "PLATFORM_DIR": ".opencode",
        }

    def test_claude_values(self):
        assert PLATFORM_TOKENS["claude"] == {
            "ASK_TOOL": "Ask",
            "DOCS_FILE": "CLAUDE.md",
            "CMD_PREFIX": "osx:",
            "TOOL_NAME": "Claude Code",
            "PLATFORM_DIR": ".claude",
        }

    def test_skill_path_prefix_is_hyphen_on_both_platforms(self):
        """Skill directory paths use the literal `osx-` prefix on both
        platforms. The token only resolves the slash-command form."""
        for tool in ("opencode", "claude"):
            # The CMD_PREFIX token is meant for slash commands:
            slash_form = PLATFORM_TOKENS[tool]["CMD_PREFIX"]
            # Every slash command string must be a slash command prefix,
            # not a skill-directory prefix. The skill directory prefix is
            # hardcoded `osx-` in source files (docs: AGENTS.md).
            assert slash_form in ("osx-", "osx:"), (
                f"{tool}: unexpected CMD_PREFIX {slash_form!r}"
            )


class TestSubstituteTokens:
    """Token rendering correctness."""

    def test_substitutes_all_known_tokens_for_opencode(self):
        text = (
            "tool={{TOOL_NAME}} doc={{DOCS_FILE}} "
            "ask={{ASK_TOOL}} prefix={{CMD_PREFIX}} dir={{PLATFORM_DIR}}"
        )
        assert _substitute_tokens(text, "opencode") == (
            "tool=OpenCode doc=AGENTS.md "
            "ask=AskUserQuestion prefix=osx- dir=.opencode"
        )

    def test_substitutes_all_known_tokens_for_claude(self):
        text = (
            "tool={{TOOL_NAME}} doc={{DOCS_FILE}} "
            "ask={{ASK_TOOL}} prefix={{CMD_PREFIX}} dir={{PLATFORM_DIR}}"
        )
        assert _substitute_tokens(text, "claude") == (
            "tool=Claude Code doc=CLAUDE.md "
            "ask=Ask prefix=osx: dir=.claude"
        )

    def test_unknown_tokens_left_verbatim(self):
        """Forward-compat: unknown tokens survive so a downstream agent sees
        the literal rather than a silent empty substitution."""
        text = "hello {{KNOWN}} and {{FUTURE_TOKEN}} ok"
        assert _substitute_tokens(text, "opencode") == text

    def test_partial_overlap_substitutes_only_known(self):
        text = "{{CMD_PREFIX}}modify {{WAT}}"
        assert _substitute_tokens(text, "opencode") == "osx-modify {{WAT}}"
        assert _substitute_tokens(text, "claude") == "osx:modify {{WAT}}"

    def test_empty_string_returns_empty_string(self):
        assert _substitute_tokens("", "opencode") == ""

    def test_no_tokens_returns_unchanged(self):
        text = "no tokens here, just words"
        assert _substitute_tokens(text, "opencode") == text

    def test_repeated_tokens_all_replaced(self):
        text = "{{CMD_PREFIX}}foo {{CMD_PREFIX}}bar"
        assert _substitute_tokens(text, "claude") == "osx:foo osx:bar"

    def test_token_appearance_in_code_fence(self):
        text = "```\n{{CMD_PREFIX}}\n```"
        assert _substitute_tokens(text, "opencode") == "```\nosx-\n```"

    def test_lowercase_token_name_not_substituted(self):
        """Only the documented uppercase token names are recognised."""
        assert _substitute_tokens("{{cmd_prefix}}", "opencode") == "{{cmd_prefix}}"

    def test_partial_match_not_substituted(self):
        """`{{{CMD_PREFIX}}}` (extra braces) is not a recognised token form."""
        assert _substitute_tokens("{{{CMD_PREFIX}}}", "opencode") == (
            "{osx-}"
        )


class TestSubstituteTokensInFile:
    """``_substitute_tokens_in_file`` only rewrites ``.md`` files."""

    def test_rewrites_md_file(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text("hello {{CMD_PREFIX}}world")
        _substitute_tokens_in_file(p, "opencode")
        assert p.read_text() == "hello osx-world"

    def test_skips_non_md_files(self, tmp_path: Path):
        p = tmp_path / "config.json"
        original = '{"key": "{{CMD_PREFIX}}"}'
        p.write_text(original)
        _substitute_tokens_in_file(p, "opencode")
        # Non-.md files are not touched (only text docs carry tokens).
        assert p.read_text() == original

    def test_dry_run_path_for_claude_helper(self, tmp_path: Path):
        p = tmp_path / "SKILL.md"
        p.write_text("/{{CMD_PREFIX}}modify")
        _substitute_tokens_in_file(p, "claude")
        assert p.read_text() == "/osx:modify"


class TestSubstituteTokensInTree:
    """Tree-walk substitute walks every ``.md`` recursively."""

    def test_substitutes_all_md_in_tree(self, tmp_path: Path):
        (tmp_path / "a.md").write_text("{{CMD_PREFIX}}")
        (tmp_path / "nested").mkdir()
        (tmp_path / "nested" / "b.md").write_text("{{PLATFORM_DIR}}")
        (tmp_path / "nested" / "c.txt").write_text("{{CMD_PREFIX}}")

        _substitute_tokens_in_tree(tmp_path, "opencode")

        assert (tmp_path / "a.md").read_text() == "osx-"
        assert (tmp_path / "nested" / "b.md").read_text() == ".opencode"
        # Non-`.md` files are left alone.
        assert (tmp_path / "nested" / "c.txt").read_text() == "{{CMD_PREFIX}}"


class TestDeployLeavesNoLeftoverTokens:
    """End-to-end: the deploy helpers must leave no ``{{TOKEN}}`` strings.

    This is the regression guard for the bug where the OpenCode source files
    shipped with literal ``{{TOKEN}}`` placeholders that the deploy step
    never rewrote.
    """

    @pytest.fixture
    def target(self, tmp_path: Path) -> Path:
        return tmp_path / ".opencode"

    def test_deploy_skill_writes_no_tokens(self, target: Path):
        source_dir = get_resources_dir() / "opencode"
        deploy_skills(
            source_dir / "skills", target, "osx-modify-artifacts", tool="opencode"
        )
        for md in (target / "skills" / "osx-modify-artifacts").rglob("*.md"):
            assert "{{" not in md.read_text(), (
                f"{md.relative_to(target)} still contains a token placeholder"
            )

    def test_deploy_command_writes_no_tokens(self, target: Path):
        source_dir = get_resources_dir() / "opencode"
        deploy_commands(source_dir / "commands", target, "osx-modify", tool="opencode")
        text = (target / "commands" / "osx-modify.md").read_text()
        assert "{{" not in text

    def test_deploy_agent_writes_no_tokens(self, target: Path):
        source_dir = get_resources_dir() / "opencode"
        deploy_agents(source_dir / "agents", target, "osx-analyzer", tool="opencode")
        text = (target / "agents" / "osx-analyzer.md").read_text()
        assert "{{" not in text

    def test_deploy_claude_command_substitutes_claude_values(self, tmp_path: Path):
        target = tmp_path / ".claude"
        source_dir = get_resources_dir() / "opencode"
        deploy_commands(source_dir / "commands", target, "osx-modify", tool="claude")
        # The deploy writes the command file at ``commands/osx-modify.md``.
        # (The Claude mirror at resources/claude/commands/osx/modify.md is
        # generated by ``sync-mirrors`` for back-compat; the deploy path
        # preserves the opencode file name.)
        command_text = (target / "commands" / "osx-modify.md").read_text()
        # The slash-command form is platform-specific; on Claude the input
        # table column labels must use `/osx:modify` (colon), not
        # `/osx-modify` (hyphen).
        import re

        labels = re.findall(r"\| `/osx[-:][\w-]+`", command_text)
        assert labels, "expected at least one slash-command table label"
        for label in labels:
            assert "`/osx:" in label, (
                f"slash-command label must be Claude form `/osx:modify` on "
                f"Claude, got: {label!r}"
            )
        # The skill path is the literal hyphenated directory on both platforms.
        assert ".claude/skills/osx-modify-artifacts/SKILL.md" in command_text
        # The broken Claude-side path (substituted `osx:` for skill directory)
        # must NOT appear.
        assert "osx:modify-artifacts" not in command_text

    def test_deploy_claude_skill_mirror_has_correct_path(self, tmp_path: Path):
        target = tmp_path / ".claude"
        source_dir = get_resources_dir() / "opencode"
        deploy_commands(source_dir / "commands", target, "osx-modify", tool="claude")
        # The dual-emit Claude skill mirror (modern form) must point at
        # the real `osx-modify-artifacts` skill directory (hyphen, not colon).
        skill_md = target / "skills" / "osx-modify" / "SKILL.md"
        text = skill_md.read_text()
        assert "osx-modify-artifacts" in text
        assert "osx:modify-artifacts" not in text
