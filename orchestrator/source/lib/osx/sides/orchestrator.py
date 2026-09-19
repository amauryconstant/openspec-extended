"""Orchestrator-side resource constants.

The orchestrator side owns the workflow skill, the four dispatch
agents, the seven phase commands, and the two user-invoked slash
commands (``osx-changelog``, ``osx-maintain-docs``). The constants
below are the in-process mirror of the
``orchestrator/resources/canonical/manifest.toml`` entries — kept
side-tagged here so the orchestrator side of the library surfaces its
own resource names without leaking into the skills or core modules.

See ``.opencode/rules/resource-separation.md`` for the disjoint-
manifest invariant.
"""

from __future__ import annotations

PHASES = ["PHASE0", "PHASE1", "PHASE2", "PHASE3", "PHASE4", "PHASE5", "PHASE6"]

PHASE_NAMES: dict[str, str] = {
    "PHASE0": "ARTIFACT REVIEW",
    "PHASE1": "IMPLEMENTATION",
    "PHASE2": "REVIEW",
    "PHASE3": "MAINTAIN DOCS",
    "PHASE4": "SYNC",
    "PHASE5": "SELF-REFLECTION",
    "PHASE6": "ARCHIVE",
}

PHASE_COMMANDS = {
    "PHASE0": "osx-phase0",
    "PHASE1": "osx-phase1",
    "PHASE2": "osx-phase2",
    "PHASE3": "osx-phase3",
    "PHASE4": "osx-phase4",
    "PHASE5": "osx-phase5",
    "PHASE6": "osx-phase6",
}

ORCHESTRATION_RESOURCE_NAMES = frozenset(
    {
        "osx-analyzer",
        "osx-builder",
        "osx-editor",
        "osx-maintainer",
        "osx-reviewer",
        "osx-phase0",
        "osx-phase1",
        "osx-phase2",
        "osx-phase3",
        "osx-phase4",
        "osx-phase5",
        "osx-phase6",
        "osx-workflow",
    }
)

AUTONOMOUS_RESOURCE_NAMES = ORCHESTRATION_RESOURCE_NAMES
