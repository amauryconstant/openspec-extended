#!/usr/bin/env python3
"""
Static resource-contract tests for the pre-implementation review/modify
rewrite (see ``docs/review-modify-integration.md``).

These tests lock in the v1.6 schema-agnostic contract adopted by
``osx-review-artifacts`` and ``osx-modify-artifacts``:

- No hardcoded artifact names in any prompt.
- ``existingOutputPaths`` / ``resolvedOutputPath`` discipline.
- Store-selection paragraph for store-backed changes.
- v1.6 ``allowed-tools: Bash(openspec:*)`` frontmatter for the rewritten
  skills and their slash commands.
- Manifest parity between the OpenCode and Claude trees (same version for
  every rewritten resource).
- The deleted rubric files are gone and the empty reference directories
  are gone.
- The PHASE0 / PHASE2 commands route to ``/opsx:update`` (default) or
  ``/osx-modify`` (fallback) instead of patching in place.
- Stale slash-command references inside ``osx-review-test-compliance`` are
  fixed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import toml

REPO_ROOT = Path(__file__).parent.parent.parent

OPENCODE = REPO_ROOT / "resources" / "opencode"
CLAUDE = REPO_ROOT / "resources" / "claude"
OPENCODE_MANIFEST = OPENCODE / "manifest.toml"
CLAUDE_MANIFEST = CLAUDE / "manifest.toml"


def _read(path: Path) -> str:
    return path.read_text()


def _read_frontmatter(path: Path) -> dict[str, str]:
    text = _read(path)
    if not text.startswith("---"):
        return {}
    body = text.split("---", 2)[1]
    fm: dict[str, str] = {}
    for line in body.strip().splitlines():
        if ":" not in line or line.startswith("#") or line.strip().startswith("-"):
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip().strip('"').strip("'")
    return fm


def _manifest_versions(path: Path) -> dict[str, str]:
    """Read a flattened map of ``<type>.<id>`` -> ``version`` from a manifest."""
    manifest = toml.loads(_read(path))
    out: dict[str, str] = {}
    resources = manifest.get("resources", {})
    for kind, items in resources.items():
        if not isinstance(items, dict):
            continue
        for rid, meta in items.items():
            if isinstance(meta, dict) and "version" in meta:
                out[f"{kind}.{rid}"] = str(meta["version"])
    return out


# ============================================================================
# Frontmatter shape
# ============================================================================


@pytest.mark.unit
class TestSkillFrontmatter:
    """Skills must match their platform's frontmatter contract and declare
    the v1.6 ``allowed-tools: Bash(openspec:*)`` precedent."""

    RESOURCES = [
        "skills/osx-review-artifacts/SKILL.md",
        "skills/osx-modify-artifacts/SKILL.md",
        "skills/osx-review-test-compliance/SKILL.md",
    ]

    @pytest.mark.parametrize("relpath", RESOURCES)
    def test_opencode_skill_has_allowed_tools(self, relpath: str):
        fm = _read_frontmatter(OPENCODE / relpath)
        assert fm.get("allowed-tools") == "Bash(openspec:*)", (
            f"{relpath} must carry `allowed-tools: Bash(openspec:*)` in "
            f"frontmatter; got: {fm.get('allowed-tools')!r}"
        )

    @pytest.mark.parametrize("relpath", RESOURCES)
    def test_opencode_skill_has_required_basics(self, relpath: str):
        fm = _read_frontmatter(OPENCODE / relpath)
        for required in ("name", "description", "license"):
            assert required in fm, (
                f"{relpath} missing required frontmatter key {required!r}"
            )

    @pytest.mark.parametrize("relpath", RESOURCES)
    def test_claude_skill_has_allowed_tools(self, relpath: str):
        fm = _read_frontmatter(CLAUDE / relpath)
        assert fm.get("allowed-tools") == "Bash(openspec:*)", (
            f"{relpath} must carry `allowed-tools: Bash(openspec:*)` in "
            f"frontmatter; got: {fm.get('allowed-tools')!r}"
        )

    @pytest.mark.parametrize("relpath", RESOURCES)
    def test_claude_skill_has_metadata(self, relpath: str):
        """Claude skills accept richer frontmatter; ``metadata`` is the
        platform-specific extension point."""
        text = _read(CLAUDE / relpath)
        assert "metadata:" in text, (
            f"{relpath} should declare a `metadata` block per "
            f"resources/claude/skills/AGENTS.md"
        )


@pytest.mark.unit
class TestCommandFrontmatter:
    """Commands must match their platform's frontmatter contract."""

    RESOURCES = [
        "commands/osx-review.md",
        "commands/osx-modify.md",
        "commands/osx-verify-tests.md",
    ]

    @pytest.mark.parametrize("relpath", RESOURCES)
    def test_opencode_command_has_allowed_tools(self, relpath: str):
        fm = _read_frontmatter(OPENCODE / relpath)
        assert fm.get("allowed-tools") == "Bash(openspec:*)", (
            f"{relpath} must carry `allowed-tools: Bash(openspec:*)` in "
            f"frontmatter; got: {fm.get('allowed-tools')!r}"
        )

    def test_opencode_review_command_wraps_skill(self):
        text = _read(OPENCODE / "commands/osx-review.md")
        assert "osx-review-artifacts/SKILL.md" in text, (
            "osx-review.md must tail the rewritten skill body"
        )

    def test_opencode_modify_command_wraps_skill(self):
        text = _read(OPENCODE / "commands/osx-modify.md")
        assert "osx-modify-artifacts/SKILL.md" in text, (
            "osx-modify.md must tail the rewritten skill body"
        )


# ============================================================================
# Schema-agnostic contract wording
# ============================================================================


@pytest.mark.unit
class TestSchemaAgnosticContract:
    """Both rewritten skills must encode the schema-agnostic contract from
    ``resources/{opencode,claude}/skills/AGENTS.md``."""

    SKILLS = [
        OPENCODE / "skills/osx-review-artifacts/SKILL.md",
        OPENCODE / "skills/osx-modify-artifacts/SKILL.md",
        CLAUDE / "skills/osx-review-artifacts/SKILL.md",
        CLAUDE / "skills/osx-modify-artifacts/SKILL.md",
    ]

    @pytest.mark.parametrize(
        "skill", SKILLS, ids=lambda p: str(p.relative_to(REPO_ROOT))
    )
    def test_skill_uses_status_cli(self, skill: Path):
        text = _read(skill)
        assert "openspec status --change" in text, (
            f"{skill.relative_to(REPO_ROOT)} must use "
            "openspec status --change ... --json"
        )

    @pytest.mark.parametrize(
        "skill", SKILLS, ids=lambda p: str(p.relative_to(REPO_ROOT))
    )
    def test_skill_uses_instructions_cli(self, skill: Path):
        text = _read(skill)
        assert "openspec instructions" in text, (
            f"{skill.relative_to(REPO_ROOT)} must use "
            "openspec instructions <id> --change ... --json"
        )

    @pytest.mark.parametrize(
        "skill", SKILLS, ids=lambda p: str(p.relative_to(REPO_ROOT))
    )
    def test_skill_references_existing_paths(self, skill: Path):
        text = _read(skill)
        assert "existingOutputPaths" in text, (
            f"{skill.relative_to(REPO_ROOT)} must reference "
            "artifactPaths.<id>.existingOutputPaths"
        )

    @pytest.mark.parametrize(
        "skill", SKILLS, ids=lambda p: str(p.relative_to(REPO_ROOT))
    )
    def test_skill_warns_against_resolved_output_path_writes(self, skill: Path):
        text = _read(skill)
        assert "resolvedOutputPath" in text, (
            f"{skill.relative_to(REPO_ROOT)} must call out "
            "the glob hazard of resolvedOutputPath"
        )

    @pytest.mark.parametrize(
        "skill", SKILLS, ids=lambda p: str(p.relative_to(REPO_ROOT))
    )
    def test_skill_disallows_code_edits(self, skill: Path):
        text = _read(skill)
        lowered = text.lower()
        assert "opsx:apply" in lowered or "/opsx:apply" in lowered, (
            f"{skill.relative_to(REPO_ROOT)} must route code-change "
            "implications to /opsx:apply"
        )

    @pytest.mark.parametrize(
        "skill", SKILLS, ids=lambda p: str(p.relative_to(REPO_ROOT))
    )
    def test_skill_includes_store_selection_paragraph(self, skill: Path):
        text = _read(skill)
        assert "openspec store list --json" in text, (
            f"{skill.relative_to(REPO_ROOT)} must include the v1.6 "
            "store-selection paragraph"
        )

    def test_modify_skill_confirms_each_dependent(self):
        """Per the plan, every dependent edit is shown and confirmed
        individually — no auto-write threshold."""
        for skill in (
            OPENCODE / "skills/osx-modify-artifacts/SKILL.md",
            CLAUDE / "skills/osx-modify-artifacts/SKILL.md",
        ):
            text = _read(skill)
            assert "individually" in text.lower(), (
                f"{skill.relative_to(REPO_ROOT)} must confirm each "
                "dependent edit individually"
            )


@pytest.mark.unit
class TestReviewSkillNoHardcodedNames:
    """The rewritten review skill must not hardcode proposal/specs/design/tasks."""

    PATHS = [
        OPENCODE / "skills/osx-review-artifacts/SKILL.md",
        CLAUDE / "skills/osx-review-artifacts/SKILL.md",
    ]

    @pytest.mark.parametrize(
        "skill", PATHS, ids=lambda p: str(p.relative_to(REPO_ROOT))
    )
    def test_skill_contains_no_hardcoded_artifact_names(self, skill: Path):
        text = _read(skill)
        forbidden = ["proposal.md", "design.md", "tasks.md"]
        # We tolerate the exception: when used as a *negative example* of
        # "never assume X". Outside that context, these strings must not
        # appear.
        for name in forbidden:
            occurrences = text.count(name)
            # The skill may mention them once each in a "never assume" warning.
            assert occurrences <= 1, (
                f"{skill.relative_to(REPO_ROOT)} references hardcoded "
                f"artifact name {name!r} {occurrences} times; "
                f"the rewritten skill must be schema-driven"
            )


# ============================================================================
# Rubric / reference cleanup
# ============================================================================


@pytest.mark.unit
class TestRubricCleanup:
    """The 321-line / 292-line rubric files were deleted; the empty
    reference directories are gone."""

    def test_opencode_rubric_gone(self):
        assert not (
            OPENCODE / "skills/osx-review-artifacts/references/review-criteria.md"
        ).exists(), (
            "resources/opencode/skills/osx-review-artifacts/references/"
            "review-criteria.md must be removed (rubric replaced by schema-driven audit)"
        )

    def test_claude_rubric_gone(self):
        assert not (
            CLAUDE / "skills/osx-review-artifacts/references/review-criteria.md"
        ).exists(), (
            "resources/claude/skills/osx-review-artifacts/references/"
            "review-criteria.md must be removed (rubric replaced by schema-driven audit)"
        )

    def test_opencode_review_references_dir_gone(self):
        assert not (OPENCODE / "skills/osx-review-artifacts/references").exists(), (
            "The empty references/ directory under opencode review-artifacts "
            "should be removed after rubric + common-issues deletion"
        )

    def test_claude_review_references_dir_gone(self):
        assert not (CLAUDE / "skills/osx-review-artifacts/references").exists(), (
            "The empty references/ directory under claude review-artifacts "
            "should be removed after rubric + common-issues deletion"
        )


# ============================================================================
# PHASE0 / PHASE2 routing
# ============================================================================


@pytest.mark.unit
class TestPhaseRouting:
    """PHASE0 emits a routing report (not in-place fixes); PHASE2 Case A
    defaults to ``/opsx:update`` with ``/osx-modify`` as a fallback."""

    def test_phase0_does_not_invoke_modify_inline(self):
        text = _read(OPENCODE / "commands/osx-phase0.md")
        assert "DO NOT" in text or "Do not" in text or "do not" in text, (
            "PHASE0 must instruct the agent not to fix inside the dispatched phase"
        )
        assert "/osx-modify" in text or "osx-modify-artifacts" in text, (
            "PHASE0 must emit /osx-modify as a routing recommendation"
        )
        assert "/opsx:update" in text or "osc-update-change" in text, (
            "PHASE0 must emit /opsx:update as a routing recommendation"
        )

    def test_phase0_claude_mirrors(self):
        text = _read(CLAUDE / "commands/osx/phase0.md")
        assert "/osx-modify" in text
        assert "/opsx:update" in text or "osc-update-change" in text

    def test_phase2_case_a_defaults_to_update(self):
        text = _read(OPENCODE / "commands/osx-phase2.md")
        assert "/opsx:update" in text or "osc-update-change" in text, (
            "PHASE2 Case A must default to /opsx:update, not osx-modify-artifacts"
        )

    def test_phase2_claude_case_a_defaults_to_update(self):
        text = _read(CLAUDE / "commands/osx/phase2.md")
        assert "/opsx:update" in text or "osc-update-change" in text

    def test_workflow_table_lists_update(self):
        for path in (
            OPENCODE / "skills/osx-workflow/SKILL.md",
            CLAUDE / "skills/osx-workflow/SKILL.md",
        ):
            text = _read(path)
            assert "osc-update-change" in text or "openspec-update-change" in text, (
                f"{path.relative_to(REPO_ROOT)} must list update-change in the "
                f"phase table"
            )


# ============================================================================
# Manifest parity
# ============================================================================


@pytest.mark.unit
class TestManifestParity:
    """Every rewritten resource must have the same version on both platforms."""

    PARITY_KEYS = [
        "skills.osx-review-artifacts",
        "skills.osx-modify-artifacts",
        "skills.osx-review-test-compliance",
        "skills.osx-workflow",
        "skills.osx-concepts",
        "skills.osx-generate-changelog",
        "skills.osx-maintain-ai-docs",
        "skills.osx-commit",
        "commands.osx-review",
        "commands.osx-modify",
        "commands.osx-verify-tests",
        "commands.osx-maintain-docs",
        "commands.osx-phase0",
        "commands.osx-phase2",
    ]

    @pytest.mark.parametrize("key", PARITY_KEYS)
    def test_versions_match(self, key: str):
        oc = _manifest_versions(OPENCODE_MANIFEST).get(key)
        cl = _manifest_versions(CLAUDE_MANIFEST).get(key)
        assert oc is not None, f"{key} missing from opencode manifest"
        assert cl is not None, f"{key} missing from claude manifest"
        assert oc == cl, f"version drift on {key}: opencode={oc} claude={cl}"

    @pytest.mark.parametrize(
        "key,expected",
        [
            ("skills.osx-review-artifacts", "0.3.0"),
            ("skills.osx-modify-artifacts", "0.3.1"),
            ("skills.osx-workflow", "0.3.2"),
            ("skills.osx-concepts", "0.9.3"),
            ("skills.osx-review-test-compliance", "0.2.3"),
            ("skills.osx-generate-changelog", "0.2.3"),
            ("skills.osx-maintain-ai-docs", "0.2.3"),
            ("commands.osx-review", "0.2.0"),
            ("commands.osx-modify", "0.2.0"),
            ("commands.osx-verify-tests", "0.1.2"),
            ("commands.osx-maintain-docs", "0.2.2"),
            ("commands.osx-phase0", "0.3.0"),
            ("commands.osx-phase2", "0.3.1"),
        ],
    )
    def test_target_versions(self, key: str, expected: str):
        oc = _manifest_versions(OPENCODE_MANIFEST).get(key)
        assert oc == expected, f"opencode {key} expected {expected}; got {oc}"
        cl = _manifest_versions(CLAUDE_MANIFEST).get(key)
        assert cl == expected, f"claude {key} expected {expected}; got {cl}"


# ============================================================================
# Stale references in test compliance skill
# ============================================================================


@pytest.mark.unit
class TestStaleRefs:
    """``osx-review-test-compliance`` was carrying stale command names."""

    @pytest.mark.parametrize(
        "path",
        [
            OPENCODE / "skills/osx-review-test-compliance/SKILL.md",
            CLAUDE / "skills/osx-review-test-compliance/SKILL.md",
        ],
    )
    def test_no_osx_test_compliance_stale_ref(self, path: Path):
        text = _read(path)
        scrubbed = text.replace("/osx-verify-tests", "")
        scrubbed = scrubbed.replace("/osx:verify-tests", "")
        for stale in [
            "/osx-test-compliance",
            "/osx:test-compliance",
        ]:
            assert stale not in scrubbed, (
                f"{path.relative_to(REPO_ROOT)} still references stale "
                f"command {stale!r}"
            )

    @pytest.mark.parametrize(
        "path",
        [
            OPENCODE / "skills/osx-review-test-compliance/SKILL.md",
            CLAUDE / "skills/osx-review-test-compliance/SKILL.md",
        ],
    )
    def test_no_osx_verify_stale_ref(self, path: Path):
        text = _read(path)
        # Strip out the well-formed "/osx:verify-tests" references so the
        # substring check targets the dangling "/osx:verify" form only.
        scrubbed = text.replace("/osx:verify-tests", "")
        scrubbed = scrubbed.replace("/osx-verify-tests", "")
        assert "/osx-verify <name>" not in scrubbed, (
            f"{path.relative_to(REPO_ROOT)} still references stale "
            f"`/osx-verify <name>` (should be `/opsx:verify <name>`)"
        )
        # Claude's mirror used `/osx:verify` (without the `-tests` suffix).
        assert "/osx:verify " not in scrubbed, (
            f"{path.relative_to(REPO_ROOT)} still references stale "
            f"`/osx:verify` (should be `/opsx:verify`)"
        )
        assert "/osx:verify\n" not in scrubbed
