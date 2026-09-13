#!/usr/bin/env python3
"""Lock in the documented skill/command taxonomy.

Section D cleanup: every doc that claims a count or a name must match
the source of truth (manifest.toml + directory listings).

Phase 4 split the resource tree into ``orchestrator/resources/`` and
``skills/resources/``. These tests union both sides — the canonical
resource set is the merge of (orchestrator opencode) ∪ (skills opencode).
Per-adapter rendering is handled at deploy time; see
``.opencode/rules/per-adapter-rendering.md``.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import toml

REPO_ROOT = Path(__file__).parent.parent.parent
ORCHESTRATOR_OPENCODE = REPO_ROOT / "orchestrator" / "resources" / "opencode"
SKILLS_OPENCODE = REPO_ROOT / "skills" / "resources" / "opencode"
ORCHESTRATOR_CLAUDE = REPO_ROOT / "orchestrator" / "resources" / "claude"
SKILLS_CLAUDE = REPO_ROOT / "skills" / "resources" / "claude"

OPENCODE_SKILLS = ORCHESTRATOR_OPENCODE / "skills"
OPENCODE_COMMANDS = ORCHESTRATOR_OPENCODE / "commands"
OPENCODE_MANIFEST = ORCHESTRATOR_OPENCODE / "manifest.toml"
CLAUDE_SKILLS = ORCHESTRATOR_CLAUDE / "skills"
CLAUDE_SKILLS_AGENTS = CLAUDE_SKILLS / "AGENTS.md"

OSX_CHANGELOG_CMD = OPENCODE_COMMANDS / "osx-changelog.md"
OSX_MAINTAIN_DOCS_CMD = OPENCODE_COMMANDS / "osx-maintain-docs.md"

OSX_PY = REPO_ROOT / "orchestrator" / "source" / "lib" / "osx.py"

CANONICAL_SKILL_NAMES = frozenset(
    {
        "osx-commit",
        "osx-workflow",
        "osx-review-artifacts",
        "osx-review-test-compliance",
    }
)

CANONICAL_COMMAND_NAMES = frozenset(
    {
        "osx-changelog",
        "osx-maintain-docs",
        "osx-review",
        "osx-verify-tests",
        "osx-phase0",
        "osx-phase1",
        "osx-phase2",
        "osx-phase3",
        "osx-phase4",
        "osx-phase5",
        "osx-phase6",
    }
)


def _read(path: Path) -> str:
    return path.read_text()


def _all_skill_dirs() -> set[str]:
    """Union of skill dirs across orchestrator and skills opencode trees."""
    names: set[str] = set()
    for root in (ORCHESTRATOR_OPENCODE / "skills", SKILLS_OPENCODE / "skills"):
        if not root.is_dir():
            continue
        for p in root.iterdir():
            if p.is_dir() and p.name != "references":
                names.add(p.name)
    return names


def _all_command_files() -> set[str]:
    """Union of osx-*.md command files across orchestrator and skills opencode trees."""
    names: set[str] = set()
    for root in (ORCHESTRATOR_OPENCODE / "commands", SKILLS_OPENCODE / "commands"):
        if not root.is_dir():
            continue
        names.update(p.stem for p in root.glob("osx-*.md"))
    return names


def _all_manifest_skills() -> set[str]:
    names: set[str] = set()
    for manifest in (ORCHESTRATOR_OPENCODE / "manifest.toml", SKILLS_OPENCODE / "manifest.toml"):
        if manifest.is_file():
            names.update(_manifest_skills(manifest))
    return names


def _all_manifest_commands() -> set[str]:
    names: set[str] = set()
    for manifest in (ORCHESTRATOR_OPENCODE / "manifest.toml", SKILLS_OPENCODE / "manifest.toml"):
        if manifest.is_file():
            names.update(_manifest_commands(manifest))
    return names


def _manifest_skills(path: Path) -> set[str]:
    data = toml.loads(_read(path))
    skills = data.get("resources", {}).get("skills", {})
    return {name for name, meta in skills.items() if isinstance(meta, dict)}


def _manifest_commands(path: Path) -> set[str]:
    data = toml.loads(_read(path))
    commands = data.get("resources", {}).get("commands", {})
    return {name for name, meta in commands.items() if isinstance(meta, dict)}


def _claude_skill_dirs() -> set[str]:
    names: set[str] = set()
    for root in (ORCHESTRATOR_CLAUDE / "skills", SKILLS_CLAUDE / "skills"):
        if not root.is_dir():
            continue
        for p in root.iterdir():
            if p.is_dir() and p.name != "references":
                names.add(p.name)
    return names


@pytest.mark.unit
class TestSkillTaxonomy:
    """Every doc that claims a count or a name must match the source of truth."""

    def test_opencode_skill_count_matches_manifest(self):
        """orchestrator/ + skills/ opencode trees union to the 4 canonical skills; each is in manifest.toml."""
        skill_dirs = _all_skill_dirs()
        assert skill_dirs == CANONICAL_SKILL_NAMES, (
            f"skill directory set drift: dirs={skill_dirs} "
            f"expected={CANONICAL_SKILL_NAMES}"
        )

        manifest_skills = _all_manifest_skills()
        assert manifest_skills == CANONICAL_SKILL_NAMES, (
            f"manifest skill set drift: manifest={manifest_skills} "
            f"expected={CANONICAL_SKILL_NAMES}"
        )

    def test_opencode_command_count_matches_manifest(self):
        """orchestrator/ + skills/ opencode trees union to 11 osx-*.md files; each is in manifest.toml."""
        cmd_files = _all_command_files()
        assert cmd_files == CANONICAL_COMMAND_NAMES, (
            f"command file set drift: files={cmd_files} "
            f"expected={CANONICAL_COMMAND_NAMES}"
        )
        assert len(cmd_files) == 11, (
            f"expected 11 command files (7 phase + 4 workflow), got {len(cmd_files)}"
        )

        manifest_cmds = _all_manifest_commands()
        assert manifest_cmds == CANONICAL_COMMAND_NAMES, (
            f"manifest command set drift: manifest={manifest_cmds} "
            f"expected={CANONICAL_COMMAND_NAMES}"
        )

    def test_changelog_and_maintain_docs_are_commands_not_skills(self):
        """osx-changelog and osx-maintain-docs are slash commands, not skills.

        The merged bodies live in orchestrator/resources/opencode/commands/{changelog,maintain-docs}.md.
        The historical skills/osx-{generate-changelog,maintain-ai-docs} directories
        were removed in favour of the slash command bodies.
        """
        assert "osx-changelog" not in CANONICAL_SKILL_NAMES
        assert "osx-maintain-docs" not in CANONICAL_SKILL_NAMES
        assert "osx-changelog" in CANONICAL_COMMAND_NAMES
        assert "osx-maintain-docs" in CANONICAL_COMMAND_NAMES

        for root in (OPENCODE_SKILLS, ORCHESTRATOR_CLAUDE / "skills", SKILLS_CLAUDE / "skills"):
            assert not (root / "osx-generate-changelog").exists(), (
                f"stale skill dir: {root}/osx-generate-changelog should be deleted"
            )
            assert not (root / "osx-maintain-ai-docs").exists(), (
                f"stale skill dir: {root}/osx-maintain-ai-docs should be deleted"
            )

    def test_changelog_command_is_self_contained(self):
        """osx-changelog.md carries its full body — no thin-wrapper pointer."""
        text = _read(OSX_CHANGELOG_CMD)
        assert text.lstrip().startswith("---"), (
            "osx-changelog.md must start with YAML frontmatter so Claude's "
            "dual-emit can register it as a skill named 'osx-changelog'"
        )
        frontmatter_end = text.find("---", text.find("---") + 3)
        frontmatter = text[: frontmatter_end + 3]
        assert "name: osx-changelog" in frontmatter, (
            "osx-changelog.md frontmatter must include 'name: osx-changelog' "
            "so Claude's dual-emit registers the correct skill name"
        )

        assert "Load the skill body" not in text, (
            "osx-changelog.md must NOT contain a 'Load the skill body' pointer; "
            "the body is now self-contained"
        )
        assert "skills/osx-generate-changelog" not in text, (
            "osx-changelog.md must NOT reference the deleted "
            "skills/osx-generate-changelog/ directory"
        )
        assert "## Steps" in text and "## Guardrails" in text, (
            "osx-changelog.md must contain the merged Steps + Guardrails "
            "sections from the previous skill body"
        )

    def test_maintain_docs_command_is_self_contained(self):
        """osx-maintain-docs.md carries its full body — no thin-wrapper pointer."""
        text = _read(OSX_MAINTAIN_DOCS_CMD)
        assert text.lstrip().startswith("---"), (
            "osx-maintain-docs.md must start with YAML frontmatter so Claude's "
            "dual-emit can register it as a skill named 'osx-maintain-docs'"
        )
        frontmatter_end = text.find("---", text.find("---") + 3)
        frontmatter = text[: frontmatter_end + 3]
        assert "name: osx-maintain-docs" in frontmatter, (
            "osx-maintain-docs.md frontmatter must include 'name: osx-maintain-docs'"
        )

        assert "Load the skill body" not in text, (
            "osx-maintain-docs.md must NOT contain a 'Load the skill body' pointer"
        )
        assert "skills/osx-maintain-ai-docs" not in text, (
            "osx-maintain-docs.md must NOT reference the deleted "
            "skills/osx-maintain-ai-docs/ directory"
        )
        assert "## Steps" in text and "## Guardrails" in text, (
            "osx-maintain-docs.md must contain the merged Steps + Guardrails"
        )

    def test_required_skills_excludes_changelog_and_maintain_docs(self):
        """osx-changelog and osx-maintain-docs are slash commands, not skills;
        REQUIRED_SKILLS therefore does not name them."""
        from source.lib import osx

        for name in ("osx-changelog", "osx-maintain-docs"):
            assert name not in osx.REQUIRED_SKILLS, (
                f"{name} is a slash command with a self-contained body; it "
                "must not appear in REQUIRED_SKILLS (which validates skill dirs)."
            )

        osx_text = _read(OSX_PY)
        required_block_idx = osx_text.find("REQUIRED_SKILLS = [")
        assert required_block_idx != -1
        post_block = osx_text[required_block_idx:]
        assert "/osx-changelog" in post_block or "slash command" in post_block, (
            "comment block after REQUIRED_SKILLS must justify why "
            "osx-changelog / osx-maintain-docs are absent"
        )

    def test_required_skills_includes_three_default_skills(self):
        """The 3 default-required skills exist on disk (some on skills side, some on orchestrator side) and in the manifest.

        osx-workflow is gated by --with-autonomous. osx-changelog and
        osx-maintain-docs are slash commands, not skills.
        osx-modify-artifacts was dropped in favour of /opsx:update.
        osx-concepts was dropped; framework content moved to .opencode/rules/openspec-contract.md and orchestrator/source/AGENTS.md.
        """
        from source.lib import osx

        assert len(osx.REQUIRED_SKILLS) == 3, (
            f"REQUIRED_SKILLS should have 3 entries (excludes osx-workflow, "
            f"osx-changelog, osx-maintain-docs, osx-modify-artifacts, osx-concepts); "
            f"got {len(osx.REQUIRED_SKILLS)}: {osx.REQUIRED_SKILLS}"
        )

        manifest_skills = _all_manifest_skills()
        for skill in osx.REQUIRED_SKILLS:
            location = (
                SKILLS_OPENCODE / "skills" / skill
                if (SKILLS_OPENCODE / "skills" / skill).is_dir()
                else OPENCODE_SKILLS / skill
            )
            assert location.is_dir(), (
                f"required skill {skill} has no SKILL.md under "
                f"{SKILLS_OPENCODE/'skills'} or {OPENCODE_SKILLS}"
            )
            assert skill in manifest_skills, (
                f"required skill {skill} not declared in either manifest"
            )

    def test_osx_workflow_documents_decision_guidance(self):
        """osx-workflow has a Decision guidance section that absorbs the
        §3 content from the deleted osx-concepts skill. Renumbered to
        §11 in this revision (was misnumbered as a second §3)."""
        text = _read(OPENCODE_SKILLS / "osx-workflow" / "SKILL.md")
        section_marker = "## §11 Decision guidance"
        assert section_marker in text, (
            f"osx-workflow/SKILL.md must include a {section_marker} section"
        )

        section_start = text.index(section_marker)
        next_section = text.find("\n## §", section_start + 1)
        section = text[section_start : next_section if next_section != -1 else None]

        for marker in (
            "Use OpenSpec when",
            "Skip OpenSpec when",
            "Update vs new change",
            "Continue vs fast-forward",
        ):
            assert marker in section, (
                f"Decision guidance §11 must include the {marker!r} subsection"
            )

    def test_claude_skill_count_drift_is_documented(self):
        """Phase 2A: dropped with the on-disk mirror. Per-adapter
        rendering produces both forms from a single canonical source;
        the deploy-time parity is enforced by
        ``tests/integration/test_install_flow.py::TestInstallClaudeDualEmit``."""

    def test_required_skills_for_default_install_excludes_workflow(self):
        """osx-workflow is gated by --with-autonomous; absent from REQUIRED_SKILLS."""
        from source.lib import osx

        assert "osx-workflow" not in osx.REQUIRED_SKILLS, (
            "osx-workflow is gated by --with-autonomous install "
            "(see AUTONOMOUS_RESOURCE_NAMES). It must not be in REQUIRED_SKILLS "
            "because that would force --no-with-autonomous installs to deploy it."
        )

        assert "osx-workflow" in osx.AUTONOMOUS_RESOURCE_NAMES, (
            "osx-workflow must remain in AUTONOMOUS_RESOURCE_NAMES so that "
            "deploy_all_resources skips it without --with-autonomous"
        )

    def test_reference_pool_carries_merged_changelog_and_maintain_docs_refs(self):
        """The 6 per-skill references moved to the shared pool."""
        expected_refs = {
            "changelog-format.md",
            "example-output.md",
            "proposal-parsing-guide.md",
            "doc-structures.md",
            "update-examples.md",
            "update-rules.md",
        }
        pool_dir = OPENCODE_SKILLS / "references"
        actual_refs = {p.name for p in pool_dir.iterdir() if p.is_file()}
        missing = expected_refs - actual_refs
        assert not missing, f"shared references pool missing {missing}"
