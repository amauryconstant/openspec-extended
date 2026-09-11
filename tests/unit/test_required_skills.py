#!/usr/bin/env python3
"""
Contract tests for ``source.lib.osx.REQUIRED_SKILLS``.

Locks in:

- Every name in ``REQUIRED_SKILLS`` corresponds to a real skill directory
  under ``resources/{opencode,claude}/skills/``.
- Every name has a manifest entry with a version.
- ``osx-commit`` is included (it is referenced by every phase command's
  MANDATORY END).
- ``osx-workflow`` is intentionally excluded because it is gated by
  ``--with-autonomous`` install.
- ``osx-changelog`` and ``osx-maintain-docs`` are intentionally excluded
  because they are slash commands with self-contained bodies, not skills.
- Manifest parity between the OpenCode and Claude trees.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import toml

REPO_ROOT = Path(__file__).parent.parent.parent
OPENCODE = REPO_ROOT / "orchestrator" / "resources" / "opencode"
SKILLS_OPENCODE = REPO_ROOT / "skills" / "resources" / "opencode"
CLAUDE = REPO_ROOT / "orchestrator" / "resources" / "claude"
SKILLS_CLAUDE = REPO_ROOT / "skills" / "resources" / "claude"

from source.lib import osx  # noqa: E402


def _read(p: Path) -> str:
    return p.read_text()


def _manifest_versions(path: Path) -> dict[str, str]:
    manifest = toml.loads(_read(path))
    out: dict[str, str] = {}
    for kind, items in manifest.get("resources", {}).items():
        if not isinstance(items, dict):
            continue
        for rid, meta in items.items():
            if isinstance(meta, dict) and "version" in meta:
                out[f"{kind}.{rid}"] = str(meta["version"])
    return out


@pytest.mark.unit
class TestRequiredSkillsContract:
    """``REQUIRED_SKILLS`` is the orchestrator's preflight gate list."""

    def test_osx_commit_is_required(self):
        """Every phase command invokes ``osx-commit`` in its MANDATORY END."""
        assert "osx-commit" in osx.REQUIRED_SKILLS, (
            "osx-commit must be in REQUIRED_SKILLS; it is referenced by every "
            "phase command (PHASE1-PHASE6) for git commits. Omitting it leaves "
            "the preflight gate allowing a deploy missing the skill."
        )

    def test_generate_changelog_intentionally_excluded(self):
        """osx-changelog and osx-maintain-docs are slash commands, not skills."""
        assert "osx-changelog" not in osx.REQUIRED_SKILLS
        assert "osx-maintain-docs" not in osx.REQUIRED_SKILLS

    def test_no_dead_names(self):
        """No name in REQUIRED_SKILLS references a missing skill directory."""
        for name in osx.REQUIRED_SKILLS:
            on_disk = any(
                (root / "skills" / name).is_dir()
                for root in (OPENCODE, SKILLS_OPENCODE)
            )
            assert on_disk, f"required skill {name} has no SKILL.md on disk"

    def test_every_required_skill_has_manifest_entry(self):
        oc = _manifest_versions(OPENCODE / "manifest.toml")
        cl = _manifest_versions(CLAUDE / "manifest.toml")
        skills_oc = _manifest_versions(SKILLS_OPENCODE / "manifest.toml")
        skills_cl = _manifest_versions(SKILLS_CLAUDE / "manifest.toml")
        for name in osx.REQUIRED_SKILLS:
            key = f"skills.{name}"
            assert key in oc or key in skills_oc, (
                f"manifest opencode missing {key}"
            )
            assert key in cl or key in skills_cl, (
                f"manifest claude missing {key}"
            )

    def test_manifest_versions_match_across_platforms(self):
        oc = _manifest_versions(OPENCODE / "manifest.toml")
        cl = _manifest_versions(CLAUDE / "manifest.toml")
        skills_oc = _manifest_versions(SKILLS_OPENCODE / "manifest.toml")
        skills_cl = _manifest_versions(SKILLS_CLAUDE / "manifest.toml")
        for name in osx.REQUIRED_SKILLS:
            key = f"skills.{name}"
            v_oc = oc.get(key) or skills_oc.get(key)
            v_cl = cl.get(key) or skills_cl.get(key)
            assert v_oc == v_cl, (
                f"version drift on {key}: opencode={v_oc} claude={v_cl}"
            )

    def test_required_core_skills_match_upstream_rename(self):
        """CORE skill names must match the post-install rename (osc-*)."""
        assert "osc-apply-change" in osx.REQUIRED_CORE_SKILLS
        assert "osc-verify-change" in osx.REQUIRED_CORE_SKILLS
        assert "osc-sync-specs" in osx.REQUIRED_CORE_SKILLS
        assert "osc-archive-change" in osx.REQUIRED_CORE_SKILLS
