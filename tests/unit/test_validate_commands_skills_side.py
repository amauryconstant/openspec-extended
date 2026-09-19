#!/usr/bin/env python3
"""Skills-side command cross-check in ``validate_commands``.

Phase 5 split the resource tree into two disjoint halves. The
``osx-review`` and ``osx-verify-tests`` commands live on the skills
side and are declared in ``skills-manifest.toml`` at the deployed
site. The orchestrator-side validator must walk both manifests — this
module pins the skills-side loop.
"""

from __future__ import annotations

import pytest
import toml

from source.lib import osx
from source.tools import REGISTRY


def _write_manifest(manifest_path, *, version="0.1.0", commands=None, skills=None, agents=None):
    payload: dict = {"version": version, "resources": {}}
    if commands:
        payload["resources"]["commands"] = {
            name: {"version": version} for name in commands
        }
    if skills:
        payload["resources"]["skills"] = {
            name: {"version": version} for name in skills
        }
    if agents:
        payload["resources"]["agents"] = {
            name: {"version": version} for name in agents
        }
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(toml.dumps(payload))


def _write_skill_side_manifest(tmp_path, *, commands=None, platform="opencode"):
    adapter = REGISTRY[platform]
    manifest_path = tmp_path / adapter.skills_dir / "skills-manifest.toml"
    _write_manifest(manifest_path, commands=commands or [])
    return manifest_path


def _write_opencode_command(tmp_path, name):
    adapter = REGISTRY["opencode"]
    cmd_path = tmp_path / adapter.skills_dir / "commands" / f"{name}.md"
    cmd_path.parent.mkdir(parents=True, exist_ok=True)
    cmd_path.write_text("# body")
    return cmd_path


def _write_claude_command_legacy(tmp_path, name):
    adapter = REGISTRY["claude"]
    base = name[len(adapter.cmd_filename_strip_prefix):] if name.startswith(adapter.cmd_filename_strip_prefix or "") else name
    cmd_path = tmp_path / adapter.skills_dir / "commands" / "osx" / f"{base}.md"
    cmd_path.parent.mkdir(parents=True, exist_ok=True)
    cmd_path.write_text("# body")
    return cmd_path


def _write_claude_skill_mirror(tmp_path, name):
    adapter = REGISTRY["claude"]
    skill_path = tmp_path / adapter.skills_dir / "skills" / name / "SKILL.md"
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(f"---\nname: {name}\n---\n# body")
    return skill_path


@pytest.mark.unit
class TestValidateCommandsSkillsSide:
    def test_opencode_skills_side_commands_validate_when_deployed(self, tmp_path):
        """Declared skills-side commands with matching on-disk files
        produce no ``commands-skills`` error."""
        adapter = REGISTRY["opencode"]
        (tmp_path / adapter.skills_dir).mkdir(parents=True)
        _write_skill_side_manifest(
            tmp_path,
            commands=["osx-review", "osx-verify-tests"],
        )
        _write_opencode_command(tmp_path, "osx-review")
        _write_opencode_command(tmp_path, "osx-verify-tests")

        result = osx.validate_commands(tmp_path)
        skills_errors = [
            e for e in result.get("errors", []) if e.get("check") == "commands-skills"
        ]
        assert not skills_errors, (
            f"deployed skills-side commands must validate; got {skills_errors!r}"
        )

    def test_opencode_missing_skills_side_command_emits_error(self, tmp_path):
        """A declared command with no on-disk file is reported under
        the ``commands-skills`` check so the operator can fix the
        install without grep'ing the manifest."""
        adapter = REGISTRY["opencode"]
        (tmp_path / adapter.skills_dir).mkdir(parents=True)
        _write_skill_side_manifest(
            tmp_path,
            commands=["osx-review", "osx-verify-tests"],
        )
        # osx-verify-tests declared but not deployed
        _write_opencode_command(tmp_path, "osx-review")

        result = osx.validate_commands(tmp_path)
        skills_errors = [
            e for e in result.get("errors", []) if e.get("check") == "commands-skills"
        ]
        assert skills_errors, (
            f"missing skills-side command must surface; got errors={result.get('errors')!r}"
        )
        assert any("osx-verify-tests" in e["message"] for e in skills_errors), (
            f"error must name the missing command; got {skills_errors!r}"
        )

    def test_no_skills_side_manifest_means_no_check(self, tmp_path):
        """A deployed tree without ``skills-manifest.toml`` runs no
        skills-side check — graceful degrade for partial installs."""
        adapter = REGISTRY["opencode"]
        (tmp_path / adapter.skills_dir).mkdir(parents=True)

        result = osx.validate_commands(tmp_path)
        skills_errors = [
            e for e in result.get("errors", []) if e.get("check") == "commands-skills"
        ]
        assert not skills_errors, (
            f"absent skills-manifest must not produce skills-side errors; "
            f"got {skills_errors!r}"
        )

    def test_claude_skills_side_command_resolves_via_modern_mirror(self, tmp_path):
        """Claude's ``namespaced-with-skill-mirror`` layout resolves a
        skills-side command via the modern skill mirror even when no
        legacy command file exists."""
        adapter = REGISTRY["claude"]
        (tmp_path / adapter.skills_dir).mkdir(parents=True)
        _write_skill_side_manifest(
            tmp_path,
            commands=["osx-review"],
            platform="claude",
        )
        # Deployed as a skill mirror only (modern form).
        _write_claude_skill_mirror(tmp_path, "osx-review")

        result = osx.validate_commands(tmp_path)
        skills_errors = [
            e for e in result.get("errors", []) if e.get("check") == "commands-skills"
        ]
        assert not skills_errors, (
            f"Claude modern-mirror must resolve skills-side command; "
            f"got {skills_errors!r}"
        )
