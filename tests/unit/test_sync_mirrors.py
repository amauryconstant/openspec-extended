#!/usr/bin/env python3
"""
Tests for ``.mise/tasks/sync-mirrors`` — the bash script that regenerates
``resources/claude/`` (skills, commands, manifest) from ``resources/opencode/``.

Each opencode command must dual-emit on the Claude side as both a legacy
``commands/osx/<name>.md`` file and a modern ``skills/osx-<name>/SKILL.md``
file. These tests exercise the actual script and assert on its output.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
SYNC_MIRRORS = PROJECT_ROOT / ".mise" / "tasks" / "sync-mirrors"
OPENCODE_COMMANDS = PROJECT_ROOT / "resources" / "opencode" / "commands"
CLAUDE_COMMANDS = PROJECT_ROOT / "resources" / "claude" / "commands"
CLAUDE_SKILLS = PROJECT_ROOT / "resources" / "claude" / "skills"


pytestmark = pytest.mark.unit


def _run(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(SYNC_MIRRORS), *args],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=check,
    )


def _all_opencode_command_files() -> list[Path]:
    return sorted(p for p in OPENCODE_COMMANDS.glob("osx-*.md") if p.is_file())


class TestSyncMirrorsSmoke:
    def test_script_syntax_is_valid(self):
        """The bash script parses without errors. ``bash -n`` is a static
        check that catches unbalanced quotes / unterminated braces before we
        attempt any real work."""
        result = subprocess.run(
            ["bash", "-n", str(SYNC_MIRRORS)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

    def test_check_mode_passes_after_fresh_sync(self):
        """``sync-mirrors --check`` is the pre-commit hook gate. After a
        normal sync, it must exit 0 with no drift report."""
        _run([])
        result = _run(["--check"], check=False)
        assert result.returncode == 0, result.stderr


class TestSyncMirrorsDualEmitsCommands:
    """The ``commands/osx-*.md`` → ``commands/osx/<X>.md`` mapping is the
    legacy path. The dual-emit rule says we ALSO emit a skill at
    ``skills/osx-<X>/SKILL.md`` for every command. The script must produce
    both files for every opencode command.
    """

    def test_skill_mirror_exists_for_every_opencode_command(self):
        _run([])
        for src in _all_opencode_command_files():
            stem = src.stem  # "osx-phase0"
            assert stem.startswith("osx-"), stem
            skill_md = CLAUDE_SKILLS / stem / "SKILL.md"
            assert skill_md.is_file(), (
                f"missing skill mirror for {stem}; run `mise run sync-mirrors`"
            )

    def test_command_mirror_still_exists_for_every_opencode_command(self):
        """Legacy form must not be dropped by the dual-emit change."""
        _run([])
        for src in _all_opencode_command_files():
            stem = src.stem  # "osx-phase0"
            base = stem[len("osx-") :]  # "phase0"
            legacy = CLAUDE_COMMANDS / "osx" / f"{base}.md"
            assert legacy.is_file(), (
                f"missing legacy command mirror for {stem}; the dual-emit "
                f"change must not remove the legacy .claude/commands/<name>.md form"
            )

    def test_skill_mirror_injects_name_frontmatter(self):
        """The Claude skill mirror must carry an explicit ``name: osx-<X>``
        frontmatter so Claude Code's slash-command resolver picks it up."""
        _run([])
        for src in _all_opencode_command_files():
            stem = src.stem
            skill_md = CLAUDE_SKILLS / stem / "SKILL.md"
            content = skill_md.read_text()
            assert f"\nname: {stem}\n" in content, (
                f"skill {stem} missing name frontmatter: {content[:200]}"
            )

    def test_skill_mirror_drops_agent_frontmatter(self):
        """The opencode-only ``agent:`` directive is platform-specific. The
        Claude mirror must not leak it through (Claude has no equivalent
        dispatch model)."""
        _run([])
        for src in _all_opencode_command_files():
            stem = src.stem
            content = (CLAUDE_SKILLS / stem / "SKILL.md").read_text()
            assert "\nagent:" not in content, (
                f"skill {stem} leaked agent: directive: {content[:200]}"
            )


class TestSyncMirrorsDetectsDrift:
    """If a Claude mirror file is manually edited to drift from the opencode
    source, ``sync-mirrors --check`` must exit non-zero so CI / pre-commit
    catches the inconsistency.
    """

    def test_check_fails_when_legacy_command_drifts(self, tmp_path):
        # Make a backup, run, then break one file, then re-check.
        backup = CLAUDE_COMMANDS / "osx" / "phase0.md"
        original = backup.read_text()
        try:
            _run([])
            backup.write_text(original + "\n\nmanual edit that drifts it\n")
            result = _run(["--check"], check=False)
            assert result.returncode != 0, (
                "expected sync-mirrors --check to detect drift in legacy command"
            )
            assert "DRIFT" in result.stdout or "DRIFT" in result.stderr, result
        finally:
            backup.write_text(original)
            _run([])

    def test_check_fails_when_skill_mirror_drifts(self, tmp_path):
        skill_md = CLAUDE_SKILLS / "osx-phase0" / "SKILL.md"
        original = skill_md.read_text()
        try:
            _run([])
            skill_md.write_text(original + "\n\nmanual edit that drifts it\n")
            result = _run(["--check"], check=False)
            assert result.returncode != 0, (
                "expected sync-mirrors --check to detect drift in skill mirror"
            )
        finally:
            skill_md.write_text(original)
            _run([])
