#!/usr/bin/env python3
"""
Static contract tests for the orchestrator's agent ↔ phase wiring.

Locks in:

- Every entry in ``engine.PHASE_AGENTS`` resolves to an existing agent file
  in ``resources/opencode/agents/``.
- Every entry in ``engine.PHASE_AGENTS`` has a manifest entry with a version.
- Agents used by ``PHASE2`` and ``PHASE5`` must allow ``edit`` (those phases
  write ``verification-report.md`` / ``reflections.md`` and ``git commit``).
- Agents used by write phases (``PHASE2``, ``PHASE3``, ``PHASE4``, ``PHASE5``,
  ``PHASE6``) must allow ``edit``; only ``PHASE0``'s read-only audit may
  declare ``edit: deny``.
- ``PHASE0``'s body explicitly forbids writes; verified by grep.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
import toml

REPO_ROOT = Path(__file__).parent.parent.parent
OPENCODE_AGENTS = REPO_ROOT / "resources" / "opencode" / "agents"
OPENCODE_COMMANDS = REPO_ROOT / "resources" / "opencode" / "commands"
OPENCODE_MANIFEST = REPO_ROOT / "resources" / "opencode" / "manifest.toml"


def _read(p: Path) -> str:
    return p.read_text()


def _parse_frontmatter(p: Path) -> dict[str, str]:
    text = _read(p)
    if not text.startswith("---"):
        return {}
    try:
        body = text.split("---", 2)[1]
    except IndexError:
        return {}
    fm: dict[str, str] = {}
    for line in body.strip().splitlines():
        if (
            ":" not in line
            or line.strip().startswith("#")
            or line.strip().startswith("-")
        ):
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm


def _parse_permission_block(p: Path) -> dict[str, str]:
    text = _read(p)
    if "permission:" not in text:
        return {}
    block: dict[str, str] = {}
    in_block = False
    for line in text.splitlines():
        if line.strip().startswith("permission:"):
            in_block = True
            continue
        if in_block:
            stripped = line.strip()
            if not stripped or not line.startswith(" "):
                if stripped and ":" in stripped:
                    in_block = False
                    continue
                continue
            if ":" in stripped:
                k, _, v = stripped.partition(":")
                block[k.strip()] = v.strip()
    return block


def _phase_agents() -> dict[str, str]:
    from source.orchestrator.engine import PHASE_AGENTS

    return dict(PHASE_AGENTS)


WRITE_PATTERNS = re.compile(
    r"(\bcat >\b|\bgit commit\b|openspec-extended osx log append\b|"
    r"openspec-extended osx iterations append\b|openspec-extended osx state complete\b|"
    r"openspec-extended osx state transition\b|>\s*\S*verification-report\.md\b|"
    r"openspec/changes/\S*/suggestions\.md\b|openspec/changes/\S*/reflections\.md\b|"
    r"openspec/changes/\S*/verification-report\.md\b)"
)


@pytest.mark.unit
class TestPhaseAgentResolution:
    """Every entry in engine.PHASE_AGENTS must point at an existing agent."""

    @pytest.mark.parametrize(
        "phase", ["PHASE0", "PHASE1", "PHASE2", "PHASE3", "PHASE4", "PHASE5", "PHASE6"]
    )
    def test_phase_agent_file_exists(self, phase: str):
        agent_name = _phase_agents()[phase]
        path = OPENCODE_AGENTS / f"{agent_name}.md"
        assert path.is_file(), (
            f"{phase} dispatches to {agent_name} but {path.relative_to(REPO_ROOT)} "
            f"does not exist"
        )

    def test_review_agent_present(self):
        """The new osx-reviewer must be present for PHASE2 and PHASE5."""
        mapping = _phase_agents()
        assert mapping["PHASE2"] == "osx-reviewer"
        assert mapping["PHASE5"] == "osx-reviewer"

    def test_phase0_still_analyzer(self):
        """PHASE0 stays read-only - analyzer is correct."""
        assert _phase_agents()["PHASE0"] == "osx-analyzer"

    def test_agent_in_manifest(self):
        """Every agent in PHASE_AGENTS has a manifest entry with a version."""
        manifest = toml.loads(_read(OPENCODE_MANIFEST))
        agents = manifest.get("resources", {}).get("agents", {})
        for phase, name in _phase_agents().items():
            assert name in agents, (
                f"{phase} → {name} but no manifest entry under "
                f"[resources.agents.{name}]"
            )
            ver = agents[name].get("version")
            assert ver, f"manifest entry for {name} has no version: {agents[name]!r}"


@pytest.mark.unit
class TestAgentPermissions:
    """Write-bearing phases must dispatch to an agent that allows ``edit``."""

    WRITE_PHASES = ["PHASE2", "PHASE3", "PHASE4", "PHASE5", "PHASE6"]

    @pytest.mark.parametrize("phase", WRITE_PHASES)
    def test_write_phase_agent_allows_edit(self, phase: str):
        agent_name = _phase_agents()[phase]
        perms = _parse_permission_block(OPENCODE_AGENTS / f"{agent_name}.md")
        assert perms.get("edit") == "allow", (
            f"{phase} dispatches to {agent_name} which has `edit: {perms.get('edit')!r}`; "
            f"the phase body writes reports and commits, so `edit: allow` is required"
        )

    def test_read_only_phase_agent_denies_edit(self):
        perms = _parse_permission_block(OPENCODE_AGENTS / "osx-analyzer.md")
        assert perms.get("edit") == "deny", (
            f"PHASE0 agent osx-analyzer must have `edit: deny`; got `edit: "
            f"{perms.get('edit')!r}`"
        )


@pytest.mark.unit
class TestPhaseBodyWrites:
    """Phase commands that write files must dispatch to a write-capable agent."""

    @pytest.mark.parametrize(
        "phase,filename",
        [
            ("PHASE0", "osx-phase0.md"),
            ("PHASE1", "osx-phase1.md"),
            ("PHASE2", "osx-phase2.md"),
            ("PHASE3", "osx-phase3.md"),
            ("PHASE4", "osx-phase4.md"),
            ("PHASE5", "osx-phase5.md"),
            ("PHASE6", "osx-phase6.md"),
        ],
    )
    def test_agent_line_present(self, phase: str, filename: str) -> None:
        fm = _parse_frontmatter(OPENCODE_COMMANDS / filename)
        assert "agent" in fm, (
            f"{filename} ({phase}) frontmatter must include "
            f"`agent: ...` for OpenCode dispatch"
        )
        expected = _phase_agents()[phase]
        assert fm["agent"] == expected, (
            f"{filename} declares `agent: {fm['agent']!r}` "
            f"but engine.PHASE_AGENTS[{phase}] = {expected!r}"
        )


@pytest.mark.unit
class TestAgentsAreSubagent:
    """Orchestrator-dispatched agents must declare ``mode: subagent``.

    ``mode: all`` exposes them in the user-driven picker; orchestrator
    dispatch picks them by name so they should be invisible to users.
    See ``resources/opencode/agents/AGENTS.md`` §Conventions.
    """

    ORCHESTRATOR_AGENTS = [
        "osx-analyzer.md",
        "osx-builder.md",
        "osx-reviewer.md",
        "osx-maintainer.md",
    ]

    @pytest.mark.parametrize("filename", ORCHESTRATOR_AGENTS)
    def test_mode_is_subagent(self, filename: str):
        fm = _parse_frontmatter(OPENCODE_AGENTS / filename)
        assert fm.get("mode") == "subagent", (
            f"{filename} must declare `mode: subagent` (orchestrator-dispatched); "
            f"got {fm.get('mode')!r}"
        )

    def test_orchestrator_agents_md_documents_convention(self):
        text = _read(OPENCODE_AGENTS / "AGENTS.md")
        assert "subagent" in text.lower(), (
            "agents/AGENTS.md must document the `mode: subagent` convention"
        )
