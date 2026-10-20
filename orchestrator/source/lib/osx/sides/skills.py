"""Skills-side resource constants.

The skills side owns the gap-filling utility skills and their slash
commands. The constants below mirror the entries declared in
``skills/resources/canonical/manifest.toml``.

See ``.agents/rules/resource-separation.md`` for the disjoint-
manifest invariant.
"""

from __future__ import annotations

REQUIRED_SKILLS = [
    "osx-review-artifacts",
    "osx-review-test-compliance",
    "osx-commit",
]
# `osx-changelog` and `osx-maintain-docs` are intentionally absent from
# REQUIRED_SKILLS: they are slash commands (with self-contained bodies), not
# skills. They do not appear under `skills/<name>/SKILL.md` on either platform,
# so the pre-flight skill gate is the wrong surface. The slash-command body is
# validated separately by `validate_commands` if needed. See `osx-concepts`
# §2.5 for the full taxonomy.
#
# `osx-workflow` is also absent: it is gated by `--with-autonomous` install and
# added to the required set only when the autonomous workflow is enabled.
