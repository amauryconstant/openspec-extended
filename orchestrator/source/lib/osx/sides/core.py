"""Core (vendored OpenSpec) resource constants.

The core side owns the upstream OpenSpec skills shipped via
``--with-core``. These are vendored from ``orchestrator/core/`` and
absorbed into the orchestrator-side TARGET manifest post-deploy by
``_preserve_core_tracking``. The constants below mirror the
``[resources.skills.osc-*]`` entries that ``openspec init`` produces.

Source manifests must never declare these names — see the disjoint-
manifest invariant in ``.agents/rules/resource-separation.md``.
"""

from __future__ import annotations

REQUIRED_CORE_SKILLS = [
    "osc-propose",
    "osc-explore",
    "osc-new-change",
    "osc-continue-change",
    "osc-apply-change",
    "osc-update-change",
    "osc-ff-change",
    "osc-verify-change",
    "osc-sync-specs",
    "osc-archive-change",
    "osc-bulk-archive-change",
    "osc-onboard",
]
