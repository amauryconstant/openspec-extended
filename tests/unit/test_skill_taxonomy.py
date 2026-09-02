#!/usr/bin/env python3
"""Lock in the documented skill/command taxonomy.

Section D cleanup: every doc that claims a count or a name must match
the source of truth (manifest.toml + directory listings).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import toml

REPO_ROOT = Path(__file__).parent.parent.parent
OPENCODE = REPO_ROOT / "resources" / "opencode"
CLAUDE = REPO_ROOT / "resources" / "claude"

OPENCODE_SKILLS = OPENCODE / "skills"
OPENCODE_COMMANDS = OPENCODE / "commands"
OPENCODE_MANIFEST = OPENCODE / "manifest.toml"
CLAUDE_SKILLS = CLAUDE / "skills"
CLAUDE_SKILLS_AGENTS = CLAUDE / "skills" / "AGENTS.md"

OSX_CONCEPTS_SKILL = OPENCODE_SKILLS / "osx-concepts" / "SKILL.md"
OSX_CHANGELOG_CMD = OPENCODE_COMMANDS / "osx-changelog.md"
OSX_MAINTAIN_DOCS_CMD = OPENCODE_COMMANDS / "osx-maintain-docs.md"

OSX_PY = REPO_ROOT / "source" / "lib" / "osx.py"

CANONICAL_SKILL_NAMES = frozenset(
    {
        "osx-commit",
        "osx-concepts",
        "osx-workflow",
        "osx-modify-artifacts",
        "osx-review-artifacts",
        "osx-review-test-compliance",
    }
)

CANONICAL_COMMAND_NAMES = frozenset(
    {
        "osx-changelog",
        "osx-maintain-docs",
        "osx-modify",
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


def _manifest_skills(path: Path) -> set[str]:
    data = toml.loads(_read(path))
    skills = data.get("resources", {}).get("skills", {})
    return {name for name, meta in skills.items() if isinstance(meta, dict)}


def _manifest_commands(path: Path) -> set[str]:
    data = toml.loads(_read(path))
    commands = data.get("resources", {}).get("commands", {})
    return {name for name, meta in commands.items() if isinstance(meta, dict)}


@pytest.mark.unit
class TestSkillTaxonomy:
    """Every doc that claims a count or a name must match the source of truth."""

    def test_opencode_skill_count_matches_manifest(self):
        """resources/opencode/skills/ has 6 dirs; each is in manifest.toml."""
        skill_dirs = {
            p.name
            for p in OPENCODE_SKILLS.iterdir()
            if p.is_dir() and p.name != "references"
        }
        assert skill_dirs == CANONICAL_SKILL_NAMES, (
            f"skill directory set drift: dirs={skill_dirs} "
            f"expected={CANONICAL_SKILL_NAMES}"
        )

        manifest_skills = _manifest_skills(OPENCODE_MANIFEST)
        assert manifest_skills == CANONICAL_SKILL_NAMES, (
            f"manifest skill set drift: manifest={manifest_skills} "
            f"expected={CANONICAL_SKILL_NAMES}"
        )

    def test_opencode_command_count_matches_manifest(self):
        """resources/opencode/commands/ has 12 osx-*.md files; each is in manifest.toml."""
        cmd_files = {p.stem for p in OPENCODE_COMMANDS.glob("osx-*.md")}
        assert cmd_files == CANONICAL_COMMAND_NAMES, (
            f"command file set drift: files={cmd_files} "
            f"expected={CANONICAL_COMMAND_NAMES}"
        )
        assert len(cmd_files) == 12, (
            f"expected 12 command files (7 phase + 5 workflow), got {len(cmd_files)}"
        )

        manifest_cmds = _manifest_commands(OPENCODE_MANIFEST)
        assert manifest_cmds == CANONICAL_COMMAND_NAMES, (
            f"manifest command set drift: manifest={manifest_cmds} "
            f"expected={CANONICAL_COMMAND_NAMES}"
        )

    def test_changelog_and_maintain_docs_are_commands_not_skills(self):
        """osx-changelog and osx-maintain-docs are slash commands, not skills.

        The merged bodies live in resources/opencode/commands/{changelog,maintain-docs}.md.
        The historical skills/osx-{generate-changelog,maintain-ai-docs} directories
        were removed in favour of the slash command bodies.
        """
        assert "osx-changelog" not in CANONICAL_SKILL_NAMES
        assert "osx-maintain-docs" not in CANONICAL_SKILL_NAMES
        assert "osx-changelog" in CANONICAL_COMMAND_NAMES
        assert "osx-maintain-docs" in CANONICAL_COMMAND_NAMES

        assert not (OPENCODE_SKILLS / "osx-generate-changelog").exists(), (
            "stale skill dir: resources/opencode/skills/osx-generate-changelog "
            "should be deleted; the body lives in commands/osx-changelog.md"
        )
        assert not (OPENCODE_SKILLS / "osx-maintain-ai-docs").exists(), (
            "stale skill dir: resources/opencode/skills/osx-maintain-ai-docs "
            "should be deleted; the body lives in commands/osx-maintain-docs.md"
        )
        assert not (CLAUDE_SKILLS / "osx-generate-changelog").exists(), (
            "stale claude skill dir: osx-generate-changelog mirror"
        )
        assert not (CLAUDE_SKILLS / "osx-maintain-ai-docs").exists(), (
            "stale claude skill dir: osx-maintain-ai-docs mirror"
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

    def test_required_skills_includes_five_default_skills(self):
        """The 5 default-required skills exist on disk and in the manifest.

        osx-workflow is gated by --with-autonomous. osx-changelog and
        osx-maintain-docs are slash commands, not skills.
        """
        from source.lib import osx

        assert len(osx.REQUIRED_SKILLS) == 5, (
            f"REQUIRED_SKILLS should have 5 entries (excludes osx-workflow, "
            f"osx-changelog, osx-maintain-docs); got {len(osx.REQUIRED_SKILLS)}: "
            f"{osx.REQUIRED_SKILLS}"
        )

        manifest_skills = _manifest_skills(OPENCODE_MANIFEST)
        for skill in osx.REQUIRED_SKILLS:
            assert (OPENCODE_SKILLS / skill).is_dir(), (
                f"required skill {skill} has no SKILL.md under {OPENCODE_SKILLS}"
            )
            assert skill in manifest_skills, (
                f"required skill {skill} not declared in {OPENCODE_MANIFEST}"
            )

    def test_osx_concepts_documents_six_skills(self):
        """osx-concepts §2.5 mentions all 6 canonical skill names."""
        text = _read(OSX_CONCEPTS_SKILL)
        assert "### 2.5 Resource taxonomy" in text, (
            "osx-concepts/SKILL.md is missing §2.5 Resource taxonomy"
        )

        section_start = text.index("### 2.5 Resource taxonomy")
        next_section = text.find("\n## ", section_start + 1)
        section = text[section_start : next_section if next_section != -1 else None]

        for skill in CANONICAL_SKILL_NAMES:
            assert f"`{skill}`" in section, (
                f"§2.5 Resource taxonomy must mention `{skill}` "
                f"as one of the canonical extended skills"
            )

        # The merged/renamed entries must NOT appear in the skills table anymore:
        for stale in (
            "osx-generate-changelog",
            "osx-maintain-ai-docs",
            "Slash-command vs skill",
        ):
            assert stale not in section, (
                f"§2.5 must not mention `{stale}` after the rename + merge"
            )

    def test_osx_concepts_documents_twelve_commands(self):
        """osx-concepts §2.5 lists 7 phase commands (range notation) and 5 workflow commands."""
        text = _read(OSX_CONCEPTS_SKILL)
        section_start = text.index("### 2.5 Resource taxonomy")
        next_section = text.find("\n## ", section_start + 1)
        section = text[section_start : next_section if next_section != -1 else None]

        phase_endpoints = ("osx-phase0", "osx-phase6")
        for endpoint in phase_endpoints:
            assert f"`{endpoint}`" in section, (
                f"§2.5 must mention phase endpoint `{endpoint}` "
                f"(range `osx-phase0` … `osx-phase6` covers all 7 phase commands)"
            )

        workflow_names = [
            "osx-modify",
            "osx-review",
            "osx-verify-tests",
            "osx-changelog",
            "osx-maintain-docs",
        ]
        for name in workflow_names:
            assert f"`{name}`" in section, (
                f"§2.5 must mention workflow command `{name}` (canonical inventory)"
            )

        assert "Phase** (7)" in section, (
            "§2.5 must indicate 'Phase (7)' so the phase command count is explicit"
        )
        assert "Workflow** (5)" in section, (
            "§2.5 must indicate 'Workflow (5)' so the workflow command count is explicit"
        )

    def test_claude_skill_count_drift_is_documented(self):
        """Claude ships more skill dirs than OpenCode; AGENTS.md explains the drift."""
        claude_skill_dirs = {
            p.name
            for p in CLAUDE_SKILLS.iterdir()
            if p.is_dir() and p.name != "references"
        }
        assert len(claude_skill_dirs) > len(CANONICAL_SKILL_NAMES), (
            f"Claude should ship more skill dirs than OpenCode (due to dual-emit); "
            f"got {len(claude_skill_dirs)} claude dirs vs "
            f"{len(CANONICAL_SKILL_NAMES)} opencode canonical"
        )

        agents_text = _read(CLAUDE_SKILLS_AGENTS)
        assert "Skill count on Claude" in agents_text, (
            "resources/claude/skills/AGENTS.md must include a 'Skill count on Claude' "
            "section that explains the dual-emit drift"
        )
        assert "dual-emit" in agents_text.lower(), (
            "resources/claude/skills/AGENTS.md must reference 'dual-emit' when "
            "explaining the count drift"
        )

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
