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
            (tmp_path / ".claude" / "commands" / "osx" / f"{cmd_name}.md").write_text(
                f"# {cmd_name}"
            )

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