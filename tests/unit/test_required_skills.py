#!/usr/bin/env python3
"""
Contract tests for ``source.lib.osx.REQUIRED_SKILLS``.

Locks in:

- Every name in ``REQUIRED_SKILLS`` corresponds to a real skill directory
  under ``resources/{opencode,claude}/skills/``.
- Every name has a manifest entry with a version.
- ``osx-commit`` is included (it is referenced by every phase command's
  MANDATORY END).
- ``osx-generate-changelog`` is intentionally excluded because it has its
  own ``/osx-changelog`` dispatch and is not on the phase-command path.
- Manifest parity between the OpenCode and Claude trees.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import toml

REPO_ROOT = Path(__file__).parent.parent.parent
OPENCODE = REPO_ROOT / "resources" / "opencode"
CLAUDE = REPO_ROOT / "resources" / "claude"

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
        """osx-generate-changelog is on its own dispatch, not the phase path."""
        assert "osx-generate-changelog" not in osx.REQUIRED_SKILLS

    def test_no_dead_names(self):
        """No name in REQUIRED_SKILLS references a missing skill directory."""
        for name in osx.REQUIRED_SKILLS:
            assert (OPENCODE / "skills" / name).is_dir(), (
                f"required skill {name} has no SKILL.md under "
                f"{OPENCODE / 'skills' / name}"
            )
            assert (CLAUDE / "skills" / name).is_dir(), (
                f"required skill {name} has no SKILL.md under "
                f"{CLAUDE / 'skills' / name}"
            )

    def test_every_required_skill_has_manifest_entry(self):
        oc = _manifest_versions(OPENCODE / "manifest.toml")
        cl = _manifest_versions(CLAUDE / "manifest.toml")
        for name in osx.REQUIRED_SKILLS:
            key = f"skills.{name}"
            assert key in oc, f"manifest opencode missing {key}"
            assert key in cl, f"manifest claude missing {key}"

    def test_manifest_versions_match_across_platforms(self):
        oc = _manifest_versions(OPENCODE / "manifest.toml")
        cl = _manifest_versions(CLAUDE / "manifest.toml")
        for name in osx.REQUIRED_SKILLS:
            key = f"skills.{name}"
            assert oc[key] == cl[key], (
                f"version drift on {key}: opencode={oc[key]} claude={cl[key]}"
            )

    def test_required_core_skills_match_upstream_rename(self):
        """CORE skill names must match the post-install rename (osc-*)."""
        assert "osc-apply-change" in osx.REQUIRED_CORE_SKILLS
        assert "osc-verify-change" in osx.REQUIRED_CORE_SKILLS
        assert "osc-sync-specs" in osx.REQUIRED_CORE_SKILLS
        assert "osc-archive-change" in osx.REQUIRED_CORE_SKILLS
