#!/usr/bin/env python3
"""
Contract tests for ``AUTONOMOUS_RESOURCE_NAMES`` and the install grouping.

Locks in:

- The autonomous set is exactly 12 entries (4 agents + 7 phase commands +
  ``osx-workflow`` skill).
- Every name in the autonomous set corresponds to a real resource directory
  or file under ``resources/opencode/``.
- No autonomous name appears in the utility default.
- The utility default (24 - 12 = 12) is the complement of the autonomous set
  within the opencode manifest.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import toml

from source.lib import osx

REPO_ROOT = Path(__file__).parent.parent.parent
OPENCODE = REPO_ROOT / "resources" / "opencode"


def _manifest_resources(path: Path) -> dict[str, dict[str, dict]]:
    manifest = toml.loads(path.read_text())
    return manifest.get("resources", {})


@pytest.mark.unit
class TestAutonomousResourceSet:
    """``AUTONOMOUS_RESOURCE_NAMES`` is the install gating list."""

    def test_contains_expected_agents(self):
        assert "osx-analyzer" in osx.AUTONOMOUS_RESOURCE_NAMES
        assert "osx-builder" in osx.AUTONOMOUS_RESOURCE_NAMES
        assert "osx-maintainer" in osx.AUTONOMOUS_RESOURCE_NAMES
        assert "osx-reviewer" in osx.AUTONOMOUS_RESOURCE_NAMES

    def test_contains_expected_phase_commands(self):
        for phase in osx.PHASES:
            cmd = osx.PHASE_COMMANDS[phase]
            assert cmd in osx.AUTONOMOUS_RESOURCE_NAMES, (
                f"Phase command {cmd} for {phase} must be in the autonomous set"
            )

    def test_contains_workflow_skill(self):
        assert "osx-workflow" in osx.AUTONOMOUS_RESOURCE_NAMES

    def test_excludes_utility_skills(self):
        utility_skills = [
            "osx-commit",
            "osx-concepts",
            "osx-generate-changelog",
            "osx-maintain-ai-docs",
            "osx-modify-artifacts",
            "osx-review-artifacts",
            "osx-review-test-compliance",
        ]
        for skill in utility_skills:
            assert skill not in osx.AUTONOMOUS_RESOURCE_NAMES, (
                f"Utility skill {skill} must not be gated by --with-autonomous"
            )

    def test_excludes_utility_commands(self):
        utility_commands = [
            "osx-changelog",
            "osx-maintain-docs",
            "osx-modify",
            "osx-review",
            "osx-verify-tests",
        ]
        for cmd in utility_commands:
            assert cmd not in osx.AUTONOMOUS_RESOURCE_NAMES, (
                f"Utility command {cmd} must not be gated by --with-autonomous"
            )

    def test_size_is_12(self):
        assert len(osx.AUTONOMOUS_RESOURCE_NAMES) == 12, (
            f"Autonomous set should be 12 entries (4 agents + 7 phase commands "
            f"+ 1 workflow skill); got {len(osx.AUTONOMOUS_RESOURCE_NAMES)}"
        )


@pytest.mark.unit
class TestInstallGrouping:
    """Each name in ``AUTONOMOUS_RESOURCE_NAMES`` resolves to a shipped resource."""

    @pytest.mark.parametrize("name", sorted(osx.AUTONOMOUS_RESOURCE_NAMES))
    def test_autonomous_resource_shipped(self, name: str):
        resources = _manifest_resources(OPENCODE / "manifest.toml")
        declared_kinds = [
            kind for kind, entries in resources.items() if name in entries
        ]
        assert declared_kinds, (
            f"Autonomous resource {name!r} is not declared in the opencode "
            f"manifest. Either add it to resources/{{opencode,claude}}/manifest.toml "
            f"or remove it from AUTONOMOUS_RESOURCE_NAMES."
        )
        for kind in declared_kinds:
            if kind == "skills":
                assert (OPENCODE / "skills" / name).is_dir(), (
                    f"Autonomous skill {name!r} declared but not shipped under "
                    f"{OPENCODE / 'skills' / name}"
                )
            elif kind == "agents":
                assert (OPENCODE / "agents" / f"{name}.md").is_file(), (
                    f"Autonomous agent {name!r} declared but not shipped under "
                    f"{OPENCODE / 'agents' / f'{name}.md'}"
                )
            elif kind == "commands":
                assert (OPENCODE / "commands" / f"{name}.md").is_file(), (
                    f"Autonomous command {name!r} declared but not shipped under "
                    f"{OPENCODE / 'commands' / f'{name}.md'}"
                )

    def test_utility_set_is_complement(self):
        """Utility resources are everything declared minus the autonomous set."""
        resources = _manifest_resources(OPENCODE / "manifest.toml")
        all_names = {name for entries in resources.values() for name in entries}
        utility = all_names - osx.AUTONOMOUS_RESOURCE_NAMES
        assert len(utility) == 12, (
            f"Utility default should be 12 entries under utility-only install; "
            f"got {len(utility)}"
        )
