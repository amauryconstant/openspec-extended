#!/usr/bin/env python3
"""Unit tests for ``purge_managed_resources``.

Covers path-scoping, prefix ownership, keep-set semantics, layout
differences between OpenCode and Claude, and symlink safety. No subprocess,
no AI, no filesystem outside ``tmp_path``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from source.cli import (
    _core_keep_set,
    _expected_extension_names,
    purge_managed_resources,
    rename_core_resources,
)

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, content: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


def _seed_opencode_legacy(target_dir: Path) -> None:
    """Seed a fully populated OpenCode-style target tree."""
    target_dir.mkdir(parents=True, exist_ok=True)

    # Skills (managed dirs + a custom one)
    for skill in ("osx-concepts", "osx-workflow", "osx-old-skill", "osc-apply-change"):
        _write(target_dir / "skills" / skill / "SKILL.md", skill)
    _write(target_dir / "skills" / "custom-review" / "SKILL.md", "kept")

    # Agents
    _write(target_dir / "agents" / "osx-analyzer.md")
    _write(target_dir / "agents" / "osx-old-agent.md")
    _write(target_dir / "agents" / "local-reviewer.md", "kept")

    # Commands (flat)
    _write(target_dir / "commands" / "osx-phase0.md")
    _write(target_dir / "commands" / "osx-old-cmd.md")
    _write(target_dir / "commands" / "openspec-old-legacy.md")
    _write(target_dir / "commands" / "custom.md", "kept")


def _seed_claude_legacy(target_dir: Path) -> None:
    """Seed a fully populated Claude-style target tree."""
    target_dir.mkdir(parents=True, exist_ok=True)

    # Skills
    for skill in ("osx-concepts", "osx-workflow", "osx-old-skill", "osc-archive-change"):
        _write(target_dir / "skills" / skill / "SKILL.md", skill)
    _write(target_dir / "skills" / "custom-review" / "SKILL.md", "kept")

    # Commands nested under osx/ and osc/
    for name in ("phase0", "phase1", "old-cmd", "phase99"):
        _write(target_dir / "commands" / "osx" / f"{name}.md")
    for name in ("apply-change", "archive-change", "old-osc-cmd"):
        _write(target_dir / "commands" / "osc" / f"{name}.md")

    # Legacy flat files that should also be purged
    _write(target_dir / "commands" / "openspec-legacy-flat.md")

    # Custom command subdir with custom file (must NOT be touched)
    _write(target_dir / "commands" / "custom" / "my-command.md", "kept")


# ---------------------------------------------------------------------------
# OpenCode cleanup
# ---------------------------------------------------------------------------


class TestOpenCodeCleanup:
    def test_removes_obsolete_osx_skill(self, tmp_path: Path):
        target = tmp_path / ".opencode"
        _seed_opencode_legacy(target)
        keep = {"osx-concepts", "osx-workflow", "osx-phase0"}

        removed = purge_managed_resources(
            target, "opencode", keep_names=keep, prefixes=("osx-",)
        )

        assert removed >= 1
        assert not (target / "skills" / "osx-old-skill").exists()
        assert (target / "skills" / "osx-concepts").is_dir()
        assert (target / "skills" / "osx-workflow").is_dir()
        assert (target / "skills" / "custom-review").is_dir()

    def test_removes_obsolete_osx_command(self, tmp_path: Path):
        target = tmp_path / ".opencode"
        _seed_opencode_legacy(target)
        keep = {"osx-phase0", "osx-concepts", "osx-workflow", "osx-analyzer"}

        purge_managed_resources(
            target, "opencode", keep_names=keep, prefixes=("osx-",)
        )

        assert not (target / "commands" / "osx-old-cmd.md").exists()
        assert (target / "commands" / "osx-phase0.md").is_file()
        assert (target / "commands" / "custom.md").is_file()

    def test_removes_obsolete_osx_agent(self, tmp_path: Path):
        target = tmp_path / ".opencode"
        _seed_opencode_legacy(target)
        keep = {"osx-analyzer", "osx-concepts", "osx-workflow", "osx-phase0"}

        purge_managed_resources(
            target, "opencode", keep_names=keep, prefixes=("osx-",)
        )

        assert not (target / "agents" / "osx-old-agent.md").exists()
        assert (target / "agents" / "osx-analyzer.md").is_file()
        assert (target / "agents" / "local-reviewer.md").is_file()

    def test_removes_legacy_openspec_flat_commands(self, tmp_path: Path):
        target = tmp_path / ".opencode"
        _seed_opencode_legacy(target)
        keep = {"osx-concepts", "osx-workflow", "osx-phase0", "osx-analyzer"}

        purge_managed_resources(
            target, "opencode", keep_names=keep, prefixes=("osx-",)
        )

        assert not (target / "commands" / "openspec-old-legacy.md").exists()

    def test_does_not_touch_osc_resources_with_osx_prefix(self, tmp_path: Path):
        """``osx-`` prefix cleanup must leave ``osc-*`` resources alone."""
        target = tmp_path / ".opencode"
        _seed_opencode_legacy(target)
        keep = {"osx-concepts", "osx-workflow", "osx-phase0", "osx-analyzer"}

        purge_managed_resources(
            target, "opencode", keep_names=keep, prefixes=("osx-",)
        )

        assert (target / "skills" / "osc-apply-change").is_dir()


# ---------------------------------------------------------------------------
# Claude cleanup
# ---------------------------------------------------------------------------


class TestClaudeCleanup:
    def test_removes_obsolete_nested_osx_command(self, tmp_path: Path):
        target = tmp_path / ".claude"
        _seed_claude_legacy(target)
        keep = {"osx-phase0", "osx-phase1", "osx-concepts", "osx-workflow"}

        removed = purge_managed_resources(
            target, "claude", keep_names=keep, prefixes=("osx-",)
        )

        assert removed >= 1
        assert (target / "commands" / "osx" / "phase0.md").is_file()
        assert (target / "commands" / "osx" / "phase1.md").is_file()
        assert not (target / "commands" / "osx" / "old-cmd.md").exists()
        assert not (target / "commands" / "osx" / "phase99.md").exists()

    def test_removes_obsolete_nested_osc_command(self, tmp_path: Path):
        target = tmp_path / ".claude"
        _seed_claude_legacy(target)
        keep = {
            "osc-apply-change",
            "osc-archive-change",
            "osx-concepts",
            "osx-workflow",
            "osx-phase0",
        }

        purge_managed_resources(
            target, "claude", keep_names=keep, prefixes=("osc-",)
        )

        assert not (target / "commands" / "osc" / "old-osc-cmd.md").exists()
        assert (target / "commands" / "osc" / "apply-change.md").is_file()
        assert (target / "commands" / "osc" / "archive-change.md").is_file()

    def test_removes_legacy_flat_command(self, tmp_path: Path):
        target = tmp_path / ".claude"
        _seed_claude_legacy(target)
        keep = {"osx-phase0", "osx-concepts", "osx-workflow"}

        purge_managed_resources(
            target, "claude", keep_names=keep, prefixes=("osx-",)
        )

        # openspec-* flat files were always considered legacy junk
        assert not (target / "commands" / "openspec-legacy-flat.md").exists()

    def test_does_not_touch_arbitrary_command_subdirectory(self, tmp_path: Path):
        target = tmp_path / ".claude"
        _seed_claude_legacy(target)
        keep = {"osx-phase0", "osx-concepts", "osx-workflow"}

        purge_managed_resources(
            target, "claude", keep_names=keep, prefixes=("osx-",)
        )

        assert (target / "commands" / "custom" / "my-command.md").is_file()

    def test_does_not_touch_other_tool(self, tmp_path: Path):
        """Cleanup is scoped to the requested tool's directory."""
        opencode = tmp_path / ".opencode"
        claude = tmp_path / ".claude"
        _seed_opencode_legacy(opencode)
        _seed_claude_legacy(claude)
        keep = {"osx-phase0", "osx-concepts", "osx-workflow"}

        purge_managed_resources(
            opencode, "opencode", keep_names=keep, prefixes=("osx-",)
        )

        # Claude tree entirely untouched
        assert (claude / "skills" / "osx-old-skill").is_dir()
        assert (claude / "commands" / "osx" / "old-cmd.md").is_file()


# ---------------------------------------------------------------------------
# Prefix ownership / safety
# ---------------------------------------------------------------------------


class TestPrefixSafety:
    def test_does_not_remove_non_prefixed_names(self, tmp_path: Path):
        target = tmp_path / ".opencode"
        target.mkdir(parents=True)
        # Custom resources with names that are NEAR but not exact matches
        _write(target / "skills" / "my-osx-tool" / "SKILL.md")
        _write(target / "skills" / "osx_custom" / "SKILL.md")
        _write(target / "skills" / "oscillator" / "SKILL.md")
        _write(target / "commands" / "oscillator.md")
        keep: set[str] = set()

        purge_managed_resources(
            target, "opencode", keep_names=keep, prefixes=("osx-", "osc-")
        )

        assert (target / "skills" / "my-osx-tool").is_dir()
        assert (target / "skills" / "osx_custom").is_dir()
        assert (target / "skills" / "oscillator").is_dir()
        assert (target / "commands" / "oscillator.md").is_file()

    def test_osc_only_purge_does_not_touch_osx(self, tmp_path: Path):
        target = tmp_path / ".opencode"
        target.mkdir(parents=True)
        _write(target / "skills" / "osx-keep" / "SKILL.md")
        _write(target / "skills" / "osc-remove" / "SKILL.md")
        keep: set[str] = {"osx-keep"}

        purge_managed_resources(
            target, "opencode", keep_names=keep, prefixes=("osc-",)
        )

        assert (target / "skills" / "osx-keep").is_dir()
        assert not (target / "skills" / "osc-remove").exists()

    def test_keeps_explicitly_named_resource(self, tmp_path: Path):
        target = tmp_path / ".opencode"
        target.mkdir(parents=True)
        _write(target / "skills" / "osx-phase0" / "SKILL.md")
        keep = {"osx-phase0"}

        removed = purge_managed_resources(
            target, "opencode", keep_names=keep, prefixes=("osx-",)
        )

        assert removed == 0
        assert (target / "skills" / "osx-phase0").is_dir()


# ---------------------------------------------------------------------------
# Idempotency, symlinks, and edge cases
# ---------------------------------------------------------------------------


class TestIdempotency:
    def test_running_twice_is_a_noop(self, tmp_path: Path):
        target = tmp_path / ".opencode"
        _seed_opencode_legacy(target)
        keep = {"osx-phase0", "osx-concepts", "osx-workflow", "osx-analyzer"}

        first = purge_managed_resources(
            target, "opencode", keep_names=keep, prefixes=("osx-",)
        )
        second = purge_managed_resources(
            target, "opencode", keep_names=keep, prefixes=("osx-",)
        )

        assert first > 0
        assert second == 0

    def test_no_op_when_target_dir_missing(self, tmp_path: Path):
        target = tmp_path / ".opencode"
        # intentionally not created
        removed = purge_managed_resources(
            target, "opencode", keep_names=set(), prefixes=("osx-",)
        )
        assert removed == 0

    def test_no_op_when_resources_dir_missing(self, tmp_path: Path):
        target = tmp_path / ".opencode"
        target.mkdir()
        removed = purge_managed_resources(
            target, "opencode", keep_names=set(), prefixes=("osx-",)
        )
        assert removed == 0

    def test_unknown_tool_raises(self, tmp_path: Path):
        with pytest.raises(ValueError):
            purge_managed_resources(
                tmp_path, "bogus", keep_names=set(), prefixes=("osx-",)
            )


class TestSymlinkSafety:
    def test_symlinked_skill_dir_is_unlinked_not_followed(self, tmp_path: Path):
        target = tmp_path / ".opencode"
        target.mkdir(parents=True)
        (target / "skills").mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        sentinel = outside / "sentinel.md"
        sentinel.write_text("do-not-touch")

        skill_link = target / "skills" / "osx-orphan"
        skill_link.symlink_to(outside)

        removed = purge_managed_resources(
            target, "opencode", keep_names=set(), prefixes=("osx-",)
        )

        assert removed == 1
        assert not skill_link.exists()
        # The symlink target must remain intact
        assert sentinel.is_file()
        assert sentinel.read_text() == "do-not-touch"


# ---------------------------------------------------------------------------
# Helper-function tests
# ---------------------------------------------------------------------------


class TestExpectedExtensionNames:
    def test_returns_all_resources_when_autonomous_enabled(self):
        names = _expected_extension_names("opencode", with_autonomous=True)
        assert "osx-concepts" in names
        assert "osx-phase0" in names
        assert "osx-analyzer" in names

    def test_excludes_autonomous_resources_when_disabled(self):
        names = _expected_extension_names("opencode", with_autonomous=False)
        assert "osx-concepts" in names
        # Phase commands are gated by --with-autonomous
        assert "osx-phase0" not in names
        assert "osx-analyzer" not in names


class TestCoreKeepSet:
    def test_discovers_osc_skills(self, tmp_path: Path):
        skills = tmp_path / "skills"
        for name in ("osc-apply-change", "osc-archive-change", "osc-stale"):
            (skills / name).mkdir(parents=True)
            (skills / name / "SKILL.md").write_text(name)

        keep = _core_keep_set(tmp_path)

        assert keep == {"osc-apply-change", "osc-archive-change", "osc-stale"}

    def test_derives_osc_command_canonical_names_claude(self, tmp_path: Path):
        osc_dir = tmp_path / "commands" / "osc"
        osc_dir.mkdir(parents=True)
        for stem in ("apply-change", "archive-change"):
            (osc_dir / f"{stem}.md").write_text(stem)

        keep = _core_keep_set(tmp_path)

        assert "osc-apply-change" in keep
        assert "osc-archive-change" in keep

    def test_ignores_non_osc_skills(self, tmp_path: Path):
        skills = tmp_path / "skills"
        (skills / "osx-concepts").mkdir(parents=True)
        (skills / "osx-concepts" / "SKILL.md").write_text("x")
        (skills / "osc-apply-change").mkdir(parents=True)
        (skills / "osc-apply-change" / "SKILL.md").write_text("x")

        keep = _core_keep_set(tmp_path)

        assert "osx-concepts" not in keep
        assert "osc-apply-change" in keep


# ---------------------------------------------------------------------------
# Core rename: opsx-* → osc-* (flat) and opsx/ → osc/ (Claude nested)
# ---------------------------------------------------------------------------


CANONICAL_CORE_WORKFLOW_IDS = [
    "apply",
    "archive",
    "bulk-archive",
    "continue",
    "explore",
    "ff",
    "new",
    "onboard",
    "propose",
    "sync",
    "update",
    "verify",
]


class TestRenameCoreResources:
    """``rename_core_resources`` rewrites the artifacts produced by
    ``openspec init --profile custom`` (``opsx-<id>.md`` / ``opsx/<id>.md``)
    into the openspec-extended convention (``osc-<id>.md`` /
    ``osc/<id>.md``). Every canonical workflow ID must round-trip cleanly.
    """

    @pytest.mark.parametrize("wid", CANONICAL_CORE_WORKFLOW_IDS)
    def test_renames_opencode_flat_command(self, tmp_path: Path, monkeypatch, wid: str):
        target = tmp_path / ".opencode"
        (target / "commands").mkdir(parents=True)
        (target / "commands" / f"opsx-{wid}.md").write_text(f"---\ndescription: {wid}\n---\n")

        monkeypatch.chdir(tmp_path)
        rename_core_resources("opencode")

        assert (target / "commands" / f"osc-{wid}.md").is_file()
        assert not (target / "commands" / f"opsx-{wid}.md").exists()

    @pytest.mark.parametrize("wid", CANONICAL_CORE_WORKFLOW_IDS)
    def test_renames_claude_nested_command(self, tmp_path: Path, monkeypatch, wid: str):
        target = tmp_path / ".claude"
        (target / "commands" / "opsx").mkdir(parents=True)
        (target / "commands" / "opsx" / f"{wid}.md").write_text(
            f"---\nname: {wid}\n---\n"
        )

        monkeypatch.chdir(tmp_path)
        rename_core_resources("claude")

        assert (target / "commands" / "osc" / f"{wid}.md").is_file()
        assert not (target / "commands" / "opsx" / f"{wid}.md").exists()

    def test_renames_skill_dirs(self, tmp_path: Path, monkeypatch):
        target = tmp_path / ".opencode"
        (target / "skills" / "openspec-apply-change").mkdir(parents=True)
        (target / "skills" / "openspec-apply-change" / "SKILL.md").write_text("x")

        monkeypatch.chdir(tmp_path)
        rename_core_resources("opencode")

        assert (target / "skills" / "osc-apply-change").is_dir()
        assert not (target / "skills" / "openspec-apply-change").exists()