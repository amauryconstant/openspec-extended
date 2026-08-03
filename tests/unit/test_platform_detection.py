#!/usr/bin/env python3
"""
Unit tests for platform-aware path resolution in source.lib.osx.

Covers the detect_platform / skills_dir / commands_dir helpers added
to fix Claude Code's .claude/ layout versus OpenCode's .opencode/ layout.
"""

import pytest

from source.lib import osx


pytestmark = pytest.mark.unit


class TestDetectPlatform:
    def test_opencode_only(self, tmp_path):
        (tmp_path / ".opencode").mkdir()
        assert osx.detect_platform(tmp_path) == "opencode"

    def test_claude_only(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        assert osx.detect_platform(tmp_path) == "claude"

    def test_both_opencode_wins(self, tmp_path):
        (tmp_path / ".opencode").mkdir()
        (tmp_path / ".claude").mkdir()
        assert osx.detect_platform(tmp_path) == "opencode"

    def test_neither_returns_opencode_default(self, tmp_path):
        assert osx.detect_platform(tmp_path) == "opencode"


class TestSkillsDir:
    def test_opencode_path(self, tmp_path):
        (tmp_path / ".opencode").mkdir()
        assert osx.skills_dir(tmp_path) == tmp_path / ".opencode" / "skills"

    def test_claude_path(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        assert osx.skills_dir(tmp_path) == tmp_path / ".claude" / "skills"


class TestCommandsDir:
    def test_opencode_path(self, tmp_path):
        (tmp_path / ".opencode").mkdir()
        assert osx.commands_dir(tmp_path) == tmp_path / ".opencode" / "commands"

    def test_claude_path(self, tmp_path):
        (tmp_path / ".claude").mkdir()
        assert osx.commands_dir(tmp_path) == tmp_path / ".claude" / "commands" / "osx"


class TestValidateSkillsPlatformAware:
    def test_validates_claude_layout(self, tmp_path):
        (tmp_path / ".claude" / "skills").mkdir(parents=True)
        for skill in osx.REQUIRED_SKILLS + osx.REQUIRED_CORE_SKILLS:
            skill_path = tmp_path / ".claude" / "skills" / skill
            skill_path.mkdir()
            (skill_path / "SKILL.md").write_text(f"# {skill}")

        result = osx.validate_skills(tmp_path)
        assert result["valid"] is True, result

    def test_validates_opencode_layout(self, tmp_path):
        (tmp_path / ".opencode" / "skills").mkdir(parents=True)
        for skill in osx.REQUIRED_SKILLS + osx.REQUIRED_CORE_SKILLS:
            skill_path = tmp_path / ".opencode" / "skills" / skill
            skill_path.mkdir()
            (skill_path / "SKILL.md").write_text(f"# {skill}")

        result = osx.validate_skills(tmp_path)
        assert result["valid"] is True, result

    def test_reports_missing_skill_for_claude(self, tmp_path):
        (tmp_path / ".claude" / "skills").mkdir(parents=True)
        result = osx.validate_skills(tmp_path)
        assert result["valid"] is False
        assert result["missing_skills"]


class TestValidateCommandsPlatformAware:
    def test_validates_claude_layout(self, tmp_path):
        (tmp_path / ".claude" / "commands" / "osx").mkdir(parents=True)
        for phase, cmd_name in osx.PHASE_COMMANDS.items():
            deployed_name = cmd_name.replace("osx-", "", 1)
            (
                tmp_path / ".claude" / "commands" / "osx" / f"{deployed_name}.md"
            ).write_text(f"# {cmd_name}")

        result = osx.validate_commands(tmp_path)
        assert result["valid"] is True, result

    def test_validates_opencode_layout(self, tmp_path):
        (tmp_path / ".opencode" / "commands").mkdir(parents=True)
        for phase, cmd_name in osx.PHASE_COMMANDS.items():
            (tmp_path / ".opencode" / "commands" / f"{cmd_name}.md").write_text(
                f"# {cmd_name}"
            )

        result = osx.validate_commands(tmp_path)
        assert result["valid"] is True, result

    def test_rejects_claude_layout_with_osx_prefixed_filenames(self, tmp_path):
        (tmp_path / ".claude" / "commands" / "osx").mkdir(parents=True)
        for phase, cmd_name in osx.PHASE_COMMANDS.items():
            (tmp_path / ".claude" / "commands" / "osx" / f"{cmd_name}.md").write_text(
                f"# {cmd_name}"
            )

        result = osx.validate_commands(tmp_path)
        assert result["valid"] is False
        assert any("phase0" in err["message"] for err in result["errors"])

    def test_rejects_opencode_layout_with_unprefixed_filenames(self, tmp_path):
        (tmp_path / ".opencode" / "commands").mkdir(parents=True)
        for phase, cmd_name in osx.PHASE_COMMANDS.items():
            deployed_name = cmd_name.replace("osx-", "", 1)
            (tmp_path / ".opencode" / "commands" / f"{deployed_name}.md").write_text(
                f"# {cmd_name}"
            )

        result = osx.validate_commands(tmp_path)
        assert result["valid"] is False
        assert any("osx-phase0" in err["message"] for err in result["errors"])

    def test_claude_error_names_deployed_filename_not_internal_name(self, tmp_path):
        (tmp_path / ".claude" / "commands" / "osx").mkdir(parents=True)
        result = osx.validate_commands(tmp_path)
        assert result["valid"] is False
        messages = [err["message"] for err in result["errors"]]
        assert any("phase0" in m for m in messages)
        assert not any("osx-phase0" in m for m in messages)


class TestValidateCommandsEitherForm:
    """Claude Code dual-emits slash commands as both a legacy
    ``.claude/commands/<name>.md`` file and a modern
    ``.claude/skills/<name>/SKILL.md`` directory. Either form satisfies a
    phase command's contract — mirroring upstream OpenSpec v1.7.0.
    """

    def test_claude_skill_only_is_valid(self, tmp_path):
        """A slash command present only as a skill (no legacy command file)
        is valid on Claude. Mirrors the post-migration world where Claude
        Code resolves every slash command through the skills surface."""
        (tmp_path / ".claude").mkdir()
        for phase, cmd_name in osx.PHASE_COMMANDS.items():
            skill_path = tmp_path / ".claude" / "skills" / cmd_name
            skill_path.mkdir(parents=True, exist_ok=True)
            (skill_path / "SKILL.md").write_text(f"---\nname: {cmd_name}\n---\n# x")

        result = osx.validate_commands(tmp_path)
        assert result["valid"] is True, result

    def test_claude_command_only_still_valid(self, tmp_path):
        """The legacy command-only form is still valid on Claude — back-compat."""
        (tmp_path / ".claude" / "commands" / "osx").mkdir(parents=True)
        for phase, cmd_name in osx.PHASE_COMMANDS.items():
            deployed_name = cmd_name.replace("osx-", "", 1)
            (
                tmp_path / ".claude" / "commands" / "osx" / f"{deployed_name}.md"
            ).write_text(f"# {cmd_name}")

        result = osx.validate_commands(tmp_path)
        assert result["valid"] is True, result

    def test_claude_both_forms_is_valid(self, tmp_path):
        """Dual-emit (both forms present) is valid."""
        (tmp_path / ".claude" / "commands" / "osx").mkdir(parents=True)
        for phase, cmd_name in osx.PHASE_COMMANDS.items():
            deployed_name = cmd_name.replace("osx-", "", 1)
            (
                tmp_path / ".claude" / "commands" / "osx" / f"{deployed_name}.md"
            ).write_text(f"# {cmd_name}")
            skill_path = tmp_path / ".claude" / "skills" / cmd_name
            skill_path.mkdir(parents=True, exist_ok=True)
            (skill_path / "SKILL.md").write_text(f"---\nname: {cmd_name}\n---\n# x")

        result = osx.validate_commands(tmp_path)
        assert result["valid"] is True, result

    def test_claude_partial_skill_only_some_phases_invalid(self, tmp_path):
        """If some phases have skills and others don't, validation fails for
        the missing ones but the existing ones still satisfy."""
        (tmp_path / ".claude").mkdir()
        # Only phase0 as a skill — the rest should fail validation.
        phase0_name = osx.PHASE_COMMANDS["PHASE0"]
        skill_path = tmp_path / ".claude" / "skills" / phase0_name
        skill_path.mkdir(parents=True)
        (skill_path / "SKILL.md").write_text(f"---\nname: {phase0_name}\n---")

        result = osx.validate_commands(tmp_path)
        assert result["valid"] is False
        messages = [err["message"] for err in result["errors"]]
        # The error names use the deployed filename convention (e.g. "phase1"
        # not "osx-phase1") on Claude.
        assert any("phase1" in m for m in messages)
