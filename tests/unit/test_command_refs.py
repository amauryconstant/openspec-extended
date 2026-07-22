#!/usr/bin/env python3
"""
Locks in that extended skills and commands do NOT reference dead
``/osx-<upstream-verb>`` slash commands (e.g. ``/osx-apply``,
``/osx-verify``, ``/osx-archive``, ``/osx-sync``, ``/osx-ff``). Those
refer to upstream core workflows that the wrapper renames to ``/osc-*``
after ``install --with-core``; without the rename they do not exist.

The extended namespace ``/osx-*`` is reserved for our own commands
(``osx-changelog``, ``osx-maintain-docs``, ``osx-modify``, ``osx-review``,
``osx-verify-tests``, ``osx-phase0..6``).

This test fails if any skill or command body references a non-existent
``/osx-<verb>`` slash command.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent.parent
OPENCODE_COMMANDS = REPO_ROOT / "resources" / "opencode" / "commands"
OPENCODE_SKILLS = REPO_ROOT / "resources" / "opencode" / "skills"

# Real extended slash commands (file: ``osx-<name>.md``).
EXTENDED_COMMAND_NAMES = {
    "changelog",
    "maintain-docs",
    "modify",
    "review",
    "verify-tests",
    "phase0",
    "phase1",
    "phase2",
    "phase3",
    "phase4",
    "phase5",
    "phase6",
}

# Upstream core verbs that the wrapper renames to /osc-* after
# `install --with-core`. References to /osx-<verb> for these are dead.
UPSTREAM_VERBS_RENAMED = {
    "apply",
    "verify",
    "archive",
    "sync",
    "update",
    "continue",
    "new",
    "propose",
    "explore",
    "ff",
    "bulk-archive",
    "onboard",
    "change",  # see `openspec new change`
}

# Build the regex set
DEAD_REFS = {f"/osx-{verb}" for verb in UPSTREAM_VERBS_RENAMED}
DEAD_REFS.update({f"/osx:{verb}" for verb in UPSTREAM_VERBS_RENAMED})

# Allow `/osc-*` (post-install) — these are correct references.
# Allow `/osx-verify-tests` etc. — they ARE extended commands.

SCAN_TARGETS: list[Path] = []
for path in OPENCODE_COMMANDS.glob("*.md"):
    SCAN_TARGETS.append(path)
for skill_md in OPENCODE_SKILLS.rglob("SKILL.md"):
    SCAN_TARGETS.append(skill_md)


def _is_substantive_ref(line: str, dead_ref: str) -> bool:
    """Return True if ``line`` contains ``dead_ref`` as a slash-command reference.

    We treat mentions inside markdown code, command tables, and prose all the
    same — any reference to a dead /osx-<verb> is a contract violation.
    """
    return dead_ref in line


def _lines_with_ref(text: str, dead_ref: str) -> list[tuple[int, str]]:
    """Return (line_no, line) for every line containing ``dead_ref`` as a
    terminator (followed by whitespace, end-of-line, or punctuation).

    A naive substring match would falsely match ``/osx-verify`` inside
    ``/osx-verify-tests`` or ``/osx-change`` inside ``/osx-changelog``.
    The terminator check requires the next character to NOT be a
    command-name hyphen (``-``), letter, or digit.
    """
    pattern = re.compile(re.escape(dead_ref) + r"(?![\w-])")
    out: list[tuple[int, str]] = []
    for i, line in enumerate(text.splitlines(), start=1):
        if pattern.search(line):
            out.append((i, line))
    return out


@pytest.mark.unit
class TestNoDeadSlashCommandReferences:
    """Static guard: extended skills and commands must not reference dead
    ``/osx-<upstream-verb>`` slash commands.
    """

    @pytest.mark.parametrize(
        "path", SCAN_TARGETS, ids=lambda p: str(p.relative_to(REPO_ROOT))
    )
    @pytest.mark.parametrize("dead_ref", sorted(DEAD_REFS))
    def test_no_dead_ref(self, path: Path, dead_ref: str):
        text = path.read_text()
        hits = _lines_with_ref(text, dead_ref)
        assert not hits, (
            f"{path.relative_to(REPO_ROOT)} references dead slash command "
            f"{dead_ref!r}; replace with `/osc-{dead_ref[len('/osx') :]}` "
            f"(post-install rename). Hits:\n"
            + "\n".join(f"  L{i}: {line.strip()}" for i, line in hits)
        )


# Backtick-ticketed references: ``osc log`` does not exist; agents and skills
# must reference the log command via ``openspec-extended osx log`` (or just
# ``osx log`` when the context is unambiguously the wrapper).
LOG_FORM_PATTERNS = [
    re.compile(r"\bvia\s+`osc log`"),
    re.compile(r"\bvia\s+`openspec-extended osc log`"),
    re.compile(r"`osc log`\b"),
    re.compile(r"\b`openspec-extended\s+`osc\s+log`"),  # the exact wrong compound
]


@pytest.mark.unit
class TestLogCommandTerminology:
    """``osc log`` does not exist; only ``openspec-extended osx log`` does.

    LLM-friendly agents and skills are prone to guess command names. This
    test forbids the wrong form ``osc log`` anywhere under ``resources/``.
    """

    @pytest.mark.parametrize(
        "path", SCAN_TARGETS, ids=lambda p: str(p.relative_to(REPO_ROOT))
    )
    def test_no_osc_log_reference(self, path: Path):
        text = path.read_text()
        for pat in LOG_FORM_PATTERNS:
            match = pat.search(text)
            if match:
                line_no = text[: match.start()].count("\n") + 1
                raise AssertionError(
                    f"{path.relative_to(REPO_ROOT)}:{line_no} "
                    f"references non-existent `osc log`. "
                    f"Use `openspec-extended osx log`."
                )
