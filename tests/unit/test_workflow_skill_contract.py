#!/usr/bin/env python3
"""
Contract test: the dispatch table in ``osx-workflow/SKILL.md`` must match
``source.orchestrator.engine.PHASE_AGENTS``.

Locks in two things:

1. The PHASE_N rows of the §2 phase table reference the correct agent name
   (so a drift in the prose cannot re-introduce the stale "PHASE2 → osx-analyzer"
   claim).
2. The TL;DR summary table at the top of the skill uses the same mapping.

Mirrored for both ``resources/opencode/`` and ``resources/claude/`` trees.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent

SKILL_PATHS = [
    REPO_ROOT / "resources" / "opencode" / "skills" / "osx-workflow" / "SKILL.md",
    REPO_ROOT / "resources" / "claude" / "skills" / "osx-workflow" / "SKILL.md",
]


def _phase_agents() -> dict[str, str]:
    from source.orchestrator.engine import PHASE_AGENTS

    return dict(PHASE_AGENTS)


# Phase row format: `| PHASEN | ... | agent-name | ... |`
PHASE_TABLE_ROW = re.compile(
    r"^\|\s*(PHASE\d)\s*\|\s*`?([A-Z_]+)`?\s*\|\s*`?(\S+?)`?\s*\|"
)


def _extract_section_table(text: str, start_marker: str) -> list[tuple[str, str]]:
    """Return a list of ``(phase, agent)`` for rows in the first table that
    appears after ``start_marker`` (the ``| Phase | Name | Agent | ...`` header).
    """
    pos = text.find(start_marker)
    if pos == -1:
        return []
    table_lines: list[str] = []
    in_table = False
    for line in text[pos:].splitlines():
        if line.lstrip().startswith("|") and "Phase" in line and "Agent" in line:
            in_table = True
            continue
        if in_table:
            if not line.lstrip().startswith("|"):
                break
            # Skip the header separator row (e.g. `|---|---|...`).
            if set(line.replace("|", "").strip()) <= {"-", " "}:
                continue
            table_lines.append(line)
    rows: list[tuple[str, str]] = []
    for line in table_lines:
        m = PHASE_TABLE_ROW.match(line)
        if m:
            phase, _name, agent = m.group(1), m.group(2), m.group(3)
            rows.append((phase, agent))
    return rows


def _extract_tldr_rows(text: str) -> list[tuple[str, str]]:
    """Parse the TL;DR code block at the top of the skill (lines 16-23).

    The TL;DR uses a fixed-width text format:
    ``PHASE0 ARTIFACT_REVIEW → osx-analyzer  → ...``
    """
    tldr_re = re.compile(
        r"^(PHASE\d)\s+[A-Z_]+\s+→\s+(\S+)\s+→",
        re.MULTILINE,
    )
    return [(m.group(1), m.group(2)) for m in tldr_re.finditer(text)]


@pytest.mark.unit
@pytest.mark.parametrize("skill_path", SKILL_PATHS, ids=lambda p: p.relative_to(REPO_ROOT).as_posix())
class TestWorkflowSkillContract:
    """Phase rows in osx-workflow/SKILL.md must match PHASE_AGENTS."""

    def test_phase2_dispatches_to_reviewer(self, skill_path: Path) -> None:
        text = skill_path.read_text()
        rows = _extract_section_table(text, "## §2 The 7 phases")
        mapping = dict(rows)
        assert mapping.get("PHASE2") == "osx-reviewer", (
            f"{skill_path.relative_to(REPO_ROOT)} §2 table shows PHASE2 → "
            f"{mapping.get('PHASE2')!r}; expected 'osx-reviewer'"
        )

    def test_phase5_dispatches_to_reviewer(self, skill_path: Path) -> None:
        text = skill_path.read_text()
        rows = _extract_section_table(text, "## §2 The 7 phases")
        mapping = dict(rows)
        assert mapping.get("PHASE5") == "osx-reviewer", (
            f"{skill_path.relative_to(REPO_ROOT)} §2 table shows PHASE5 → "
            f"{mapping.get('PHASE5')!r}; expected 'osx-reviewer'"
        )

    def test_phase0_remains_analyzer(self, skill_path: Path) -> None:
        text = skill_path.read_text()
        rows = _extract_section_table(text, "## §2 The 7 phases")
        mapping = dict(rows)
        assert mapping.get("PHASE0") == "osx-analyzer", (
            f"{skill_path.relative_to(REPO_ROOT)} §2 table shows PHASE0 → "
            f"{mapping.get('PHASE0')!r}; PHASE0 must stay read-only with osx-analyzer"
        )

    def test_full_phase_table_matches_engine(self, skill_path: Path) -> None:
        text = skill_path.read_text()
        rows = _extract_section_table(text, "## §2 The 7 phases")
        skill_mapping = dict(rows)
        assert set(skill_mapping) == set(_phase_agents()), (
            f"{skill_path.relative_to(REPO_ROOT)} §2 covers phases "
            f"{sorted(skill_mapping)} but PHASE_AGENTS covers "
            f"{sorted(_phase_agents())}"
        )
        for phase, agent in _phase_agents().items():
            assert skill_mapping[phase] == agent, (
                f"{skill_path.relative_to(REPO_ROOT)} §2 row for {phase} says "
                f"{skill_mapping[phase]!r}; engine.PHASE_AGENTS[{phase}] = "
                f"{agent!r}"
            )

    def test_tldr_matches_engine(self, skill_path: Path) -> None:
        text = skill_path.read_text()
        tldr = _extract_tldr_rows(text)
        tldr_mapping = dict(tldr)
        assert set(tldr_mapping) == set(_phase_agents()), (
            f"{skill_path.relative_to(REPO_ROOT)} TL;DR covers phases "
            f"{sorted(tldr_mapping)}; engine.PHASE_AGENTS covers "
            f"{sorted(_phase_agents())}"
        )
        for phase, agent in _phase_agents().items():
            assert tldr_mapping[phase] == agent, (
                f"{skill_path.relative_to(REPO_ROOT)} TL;DR row for {phase} "
                f"says {tldr_mapping[phase]!r}; engine.PHASE_AGENTS[{phase}] = "
                f"{agent!r}"
            )

    def test_no_stale_analyzer_for_write_phases(self, skill_path: Path) -> None:
        """The skill body must not claim PHASE2/PHASE5 dispatch osx-analyzer."""
        text = skill_path.read_text()
        # After the rewrite, PHASE2/PHASE5 should reference osx-reviewer.
        # The skill may legitimately mention osx-analyzer for PHASE0 only.
        # We check that "PHASE2" followed by "osx-analyzer" does not appear.
        for phase in ("PHASE2", "PHASE5"):
            pattern = re.compile(
                rf"{phase}[^\n]*osx-analyzer",
                re.MULTILINE,
            )
            m = pattern.search(text)
            assert not m, (
                f"{skill_path.relative_to(REPO_ROOT)} mentions "
                f"'{phase} ... osx-analyzer' at L"
                f"{text[: m.start()].count(chr(10)) + 1 if m else '?'}; "
                f"PHASE2/PHASE5 must dispatch osx-reviewer (write-capable)"
            )

    def test_phase0_readonly_prose_present(self, skill_path: Path) -> None:
        """The skill must explicitly call out PHASE0 as read-only and PHASE2/PHASE5
        as write-capable (split, not grouped as "PHASE0 and PHASE2 read-only").
        """
        text = skill_path.read_text()
        assert "PHASE0" in text and "read-only" in text, (
            f"{skill_path.relative_to(REPO_ROOT)} must distinguish PHASE0 as "
            "read-only"
        )
        # PHASE2/PHASE5 should be characterized as write-capable (not read-only).
        assert "write-capable" in text or "edit: allow" in text, (
            f"{skill_path.relative_to(REPO_ROOT)} must describe PHASE2/PHASE5 "
            "as write-capable (edit: allow)"
        )
