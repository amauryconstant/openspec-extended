"""Side-tagged resource constants.

Each constant belongs to exactly one side of the resource split:

- :mod:`.orchestrator` — workflow skill, dispatch agents, phase commands,
  user-invoked slash commands. The orchestrator side of the library.
- :mod:`.skills` — gap-filling utility skills and their slash commands.
- :mod:`.core` — vendored OpenSpec skills shipped via ``--with-core``;
  never declared in source manifests, only absorbed into the
  orchestrator-side TARGET manifest by ``_preserve_core_tracking``.

The constants are re-exported from ``source.lib.osx`` for backward
compatibility so call sites like
``from source.lib.osx import REQUIRED_SKILLS`` continue to resolve.

See ``.opencode/rules/resource-separation.md`` for the disjoint-
manifest invariant.
"""

from __future__ import annotations

from source.lib.osx.sides.core import REQUIRED_CORE_SKILLS
from source.lib.osx.sides.orchestrator import (
    AUTONOMOUS_RESOURCE_NAMES,
    ORCHESTRATION_RESOURCE_NAMES,
    PHASE_COMMANDS,
    PHASE_NAMES,
    PHASES,
)
from source.lib.osx.sides.skills import REQUIRED_SKILLS

__all__ = [
    "AUTONOMOUS_RESOURCE_NAMES",
    "ORCHESTRATION_RESOURCE_NAMES",
    "PHASES",
    "PHASE_COMMANDS",
    "PHASE_NAMES",
    "REQUIRED_CORE_SKILLS",
    "REQUIRED_SKILLS",
]
