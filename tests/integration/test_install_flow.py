#!/usr/bin/env python3
"""
Integration tests for install flow.
"""

import subprocess
import sys
from pathlib import Path

import toml

import pytest

from source import __version__
from source.cli import TOOL_DIRS

pytestmark = pytest.mark.integration


@pytest.fixture
def test_env(tmp_path):
    """Create a clean test environment."""
    env_dir = tmp_path / "test_env"
    env_dir.mkdir()
    return env_dir


@pytest.fixture
def git_env(tmp_path):
    """Create a test environment with git repo."""
    env_dir = tmp_path / "git_env"
    env_dir.mkdir()

    subprocess.run(["git", "init", "-q"], cwd=env_dir, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"], cwd=env_dir, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=env_dir, check=True)

    readme = env_dir / "README.md"
    readme.write_text("# Test repo")
    subprocess.run(["git", "add", "README.md"], cwd=env_dir, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "Initial commit"], cwd=env_dir, check=True
    )

    return env_dir


def run_osx(args, cwd=None):
    """Run openspec-extended command via python -m source and return result."""
    cmd = [sys.executable, "-m", "source"] + args
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result


class TestInstallOpencode:
    """Tests for 'install opencode' command."""

    def test_install_opencode_creates_structure(self, test_env):
        """Install opencode creates .opencode structure."""
        result = run_osx(["install", "opencode", "--with-autonomous"], cwd=test_env)

        assert result.returncode == 0
        assert (test_env / ".opencode" / "skills").is_dir()
        assert (test_env / ".opencode" / "commands").is_dir()
        assert (test_env / ".opencode" / "agents").is_dir()
        assert not (test_env / ".opencode" / "scripts").exists()

    def test_install_opencode_copies_extension_skills(self, test_env):
        """Install opencode copies extension skills."""
        result = run_osx(["install", "opencode"], cwd=test_env)

        assert result.returncode == 0
        assert (test_env / ".opencode" / "skills" / "osx-concepts").is_dir()
        assert (test_env / ".opencode" / "skills" / "osx-modify-artifacts").is_dir()
        assert (test_env / ".opencode" / "skills" / "osx-review-artifacts").is_dir()

    def test_install_opencode_copies_agents(self, test_env):
        """Install opencode with --with-autonomous copies agents."""
        result = run_osx(["install", "opencode", "--with-autonomous"], cwd=test_env)

        assert result.returncode == 0
        assert (test_env / ".opencode" / "agents" / "osx-analyzer.md").is_file()
        assert (test_env / ".opencode" / "agents" / "osx-builder.md").is_file()
        assert (test_env / ".opencode" / "agents" / "osx-maintainer.md").is_file()

    def test_install_opencode_copies_commands(self, test_env):
        """Install opencode with --with-autonomous copies phase commands."""
        result = run_osx(["install", "opencode", "--with-autonomous"], cwd=test_env)

        assert result.returncode == 0
        assert (test_env / ".opencode" / "commands" / "osx-phase0.md").is_file()
        assert (test_env / ".opencode" / "commands" / "osx-phase1.md").is_file()
        assert (test_env / ".opencode" / "commands" / "osx-phase2.md").is_file()

    def test_install_opencode_does_not_create_scripts_dir(self, test_env):
        """Install opencode does not create a scripts/ directory.

        State I/O is done via the `openspec-extended osx` CLI subcommand,
        not a deployed Python script. Agents call the binary directly.
        """
        result = run_osx(["install", "opencode"], cwd=test_env)

        assert result.returncode == 0
        assert not (test_env / ".opencode" / "scripts").exists()

    def test_install_opencode_copies_manifest_with_version(self, test_env):
        """Install opencode copies manifest with version."""
        result = run_osx(["install", "opencode"], cwd=test_env)

        assert result.returncode == 0
        manifest_path = test_env / ".opencode" / "manifest.toml"
        assert manifest_path.is_file()

        with open(manifest_path) as f:
            manifest = toml.load(f)

        assert manifest.get("version") == __version__

    def test_install_opencode_shows_deployed_message(self, test_env):
        """Install opencode shows success message."""
        result = run_osx(["install", "opencode"], cwd=test_env)

        assert result.returncode == 0
        assert "Deployed" in result.stdout or "Deployed" in result.stderr


class TestInstallClaude:
    """Tests for 'install claude' command."""

    def test_install_claude_creates_structure(self, test_env):
        """Install claude creates .claude structure."""
        result = run_osx(["install", "claude"], cwd=test_env)

        assert result.returncode == 0
        assert (test_env / ".claude" / "skills").is_dir()
        assert (test_env / ".claude" / "commands").is_dir()

    def test_install_claude_copies_extension_skills(self, test_env):
        """Install claude copies extension skills."""
        result = run_osx(["install", "claude"], cwd=test_env)

        assert result.returncode == 0
        assert (test_env / ".claude" / "skills" / "osx-concepts").is_dir()


class TestInstallClaudeDualEmit:
    """Claude Code merges commands and skills. Each opencode slash command
    must dual-emit on Claude as both a legacy ``.claude/commands/osx/<name>.md``
    and a modern ``.claude/skills/osx-<name>/SKILL.md``. Mirrors upstream
    OpenSpec v1.7.0's own dual-emit strategy.
    """

    def test_install_claude_autonomous_emits_command_and_skill(self, test_env):
        """``install claude --with-autonomous`` writes BOTH the legacy command
        file and the modern skill form for every phase command."""
        result = run_osx(["install", "claude", "--with-autonomous"], cwd=test_env)
        assert result.returncode == 0, result.stderr

        for phase in range(7):
            cmd_name = f"osx-phase{phase}"
            base = f"phase{phase}"
            cmd_file = test_env / ".claude" / "commands" / "osx" / f"{base}.md"
            skill_md = test_env / ".claude" / "skills" / cmd_name / "SKILL.md"
            assert cmd_file.is_file(), f"missing command file for {cmd_name}"
            assert skill_md.is_file(), f"missing skill mirror for {cmd_name}"

    def test_install_claude_autonomous_skill_has_name_field(self, test_env):
        """The Claude skill mirror carries an explicit ``name: osx-<X>``
        frontmatter so Claude Code's slash-command resolver picks it up."""
        result = run_osx(["install", "claude", "--with-autonomous"], cwd=test_env)
        assert result.returncode == 0, result.stderr

        skill_md = test_env / ".claude" / "skills" / "osx-phase0" / "SKILL.md"
        assert skill_md.is_file()
        content = skill_md.read_text()
        assert "\nname: osx-phase0\n" in content, content

    def test_install_claude_autonomous_skill_drops_agent_field(self, test_env):
        """The opencode-only ``agent:`` directive is stripped from the
        Claude skill mirror (Claude has no equivalent dispatch model)."""
        result = run_osx(["install", "claude", "--with-autonomous"], cwd=test_env)
        assert result.returncode == 0, result.stderr

        for phase in range(7):
            skill_md = (
                test_env / ".claude" / "skills" / f"osx-phase{phase}" / "SKILL.md"
            )
            content = skill_md.read_text()
            assert "\nagent:" not in content, (
                f"phase{phase} skill leaked agent: field: {content[:200]}"
            )

    def test_install_claude_autonomous_skill_copies_referenced_refs(self, test_env):
        """Phase commands reference ``references/<file>.md`` paths in the
        shared skill-references pool. The Claude skill mirror copies those
        references into the per-skill ``references/`` directory so the
        skill is self-sufficient at deploy time."""
        result = run_osx(["install", "claude", "--with-autonomous"], cwd=test_env)
        assert result.returncode == 0, result.stderr

        refs_dir = test_env / ".claude" / "skills" / "osx-phase0" / "references"
        assert refs_dir.is_dir(), refs_dir
        assert (refs_dir / "phase-protocol-common.md").is_file()
        assert (refs_dir / "blocker-semantics.md").is_file()
        assert (refs_dir / "osx-decision-logging.md").is_file()
        assert (refs_dir / "shell-argument-safety.md").is_file()

    def test_install_opencode_autonomous_does_not_emit_skill_for_command(
        self, test_env
    ):
        """OpenCode is single-emit: phase commands stay as
        ``.opencode/commands/osx-phase0.md`` and do NOT produce a parallel
        skill. This is the asymmetry of the dual-emit rule."""
        result = run_osx(["install", "opencode", "--with-autonomous"], cwd=test_env)
        assert result.returncode == 0, result.stderr

        cmd_file = test_env / ".opencode" / "commands" / "osx-phase0.md"
        assert cmd_file.is_file()
        # The skill directory should not exist for this command-derived skill
        # on OpenCode. (osx-workflow as a real skill is separate.)
        assert not (test_env / ".opencode" / "skills" / "osx-phase0").is_dir()


class TestInstallWithCore:
    """Tests for 'install --with-core' command."""

    def test_install_with_core_includes_core_skills(self, test_env):
        """Install --with-core includes core skills."""
        result = run_osx(["install", "opencode", "--with-core"], cwd=test_env)

        assert result.returncode == 0
        skills_dir = test_env / ".opencode" / "skills"
        if skills_dir.is_dir():
            skills = list(skills_dir.iterdir())
            assert len(skills) > 6

    def test_install_with_core_includes_all_12_core_commands(self, test_env):
        """Install --with-core deploys all 12 canonical core commands (renamed
        to ``osc-*`` on disk). Guards against the v1.5.0+ regression where
        ``openspec init`` defaulted to ``profile=core`` and only emitted 6.
        """
        result = run_osx(["install", "opencode", "--with-core"], cwd=test_env)

        assert result.returncode == 0, result.stderr
        commands_dir = test_env / ".opencode" / "commands"
        deployed = {p.stem for p in commands_dir.glob("*.md")}
        missing = EXPECTED_CORE_COMMANDS_OPENCODE - deployed
        assert not missing, (
            f"missing core commands after install --with-core: {sorted(missing)}"
        )

    def test_install_with_core_includes_all_12_core_commands_claude(self, test_env):
        """Claude variant: --with-core deploys all 12 commands under
        ``.claude/commands/osc/`` (the Claude layout nests files under
        ``osc/`` with the prefix stripped)."""
        result = run_osx(["install", "claude", "--with-core"], cwd=test_env)

        assert result.returncode == 0, result.stderr
        osc_dir = test_env / ".claude" / "commands" / "osc"
        deployed = {p.stem for p in osc_dir.glob("*.md")} if osc_dir.is_dir() else set()
        missing = EXPECTED_CORE_COMMANDS_CLAUDE - deployed
        assert not missing, (
            f"missing core commands after install --with-core: {sorted(missing)}"
        )

    def test_update_with_core_reinstalls_all_12_core_commands(self, test_env):
        """``update --with-core --force`` regenerates the full 12-workflow set."""
        run_osx(["install", "opencode", "--with-core"], cwd=test_env)
        result = run_osx(["update", "opencode", "--with-core", "--force"], cwd=test_env)

        assert result.returncode == 0, result.stderr
        commands_dir = test_env / ".opencode" / "commands"
        deployed = {p.stem for p in commands_dir.glob("*.md")}
        missing = EXPECTED_CORE_COMMANDS_OPENCODE - deployed
        assert not missing, (
            f"missing core commands after update --with-core: {sorted(missing)}"
        )


# Canonical 12-workflow set delivered by `openspec init --profile custom`
# then renamed osc-* by `rename_core_resources`. Order is not significant.
EXPECTED_CORE_COMMANDS_OPENCODE = {
    "osc-apply",
    "osc-archive",
    "osc-bulk-archive",
    "osc-continue",
    "osc-explore",
    "osc-ff",
    "osc-new",
    "osc-onboard",
    "osc-propose",
    "osc-sync",
    "osc-update",
    "osc-verify",
}

EXPECTED_CORE_COMMANDS_CLAUDE = {
    "apply",
    "archive",
    "bulk-archive",
    "continue",
    "explore",
    "ff",
    "new",
    "onboard",
    "propose",
    "sync",
    "update",
    "verify",
}


class TestUpdateCommand:
    """Tests for 'update' command."""

    def test_update_overwrites_existing_skills(self, test_env):
        """Update overwrites existing skills."""
        run_osx(["install", "opencode"], cwd=test_env)

        skill_path = test_env / ".opencode" / "skills" / "osx-concepts" / "SKILL.md"
        original_len = len(skill_path.read_text())

        (skill_path).write_text((skill_path).read_text() + "\nmodified")

        result = run_osx(["update", "opencode"], cwd=test_env)
        assert result.returncode == 0

        new_len = len(skill_path.read_text())
        assert new_len == original_len

    def test_update_shows_deployed_message(self, test_env):
        """Update shows deployed message."""
        run_osx(["install", "opencode"], cwd=test_env)

        result = run_osx(["update", "opencode"], cwd=test_env)
        assert result.returncode == 0
        assert "Deployed" in result.stdout or "Deployed" in result.stderr


class TestInstallVsUpdate:
    """Tests for install vs update behavior."""

    def test_install_skips_existing_skills(self, test_env):
        """Install skips existing skills on second run."""
        run_osx(["install", "opencode"], cwd=test_env)

        result = run_osx(["install", "opencode"], cwd=test_env)
        assert result.returncode == 0
        assert "Skipped" in result.stdout or "0 skill" in result.stdout


class TestGitignore:
    """Tests for .gitignore handling."""

    def test_updates_gitignore_when_installing(self, test_env):
        """Updates .gitignore when openspec-extended resources are installed."""
        run_osx(["install", "opencode", "--with-autonomous"], cwd=test_env)

        gitignore = test_env / ".gitignore"
        assert gitignore.is_file()

        content = gitignore.read_text()
        assert "openspec/changes/*/state.json" in content

    def test_gitignore_has_markers(self, test_env):
        """Gitignore has BEGIN/END markers."""
        run_osx(["install", "opencode", "--with-autonomous"], cwd=test_env)

        content = (test_env / ".gitignore").read_text()
        assert "BEGIN OpenSpec autonomous" in content
        assert "END OpenSpec autonomous" in content

    def test_gitignore_preserves_existing_content(self, test_env):
        """Gitignore preserves existing content."""
        gitignore = test_env / ".gitignore"
        gitignore.write_text("# Existing content\n")

        run_osx(["install", "opencode", "--with-autonomous"], cwd=test_env)

        content = gitignore.read_text()
        assert "# Existing content" in content
        assert "openspec/changes" in content


class TestSkillsAndCommands:
    """Tests for skills and commands validation."""

    def test_skills_have_skill_md_file(self, test_env):
        """Skills have SKILL.md file."""
        run_osx(["install", "opencode"], cwd=test_env)

        skills_dir = test_env / ".opencode" / "skills"
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir():
                assert (skill_dir / "SKILL.md").is_file()

    def test_commands_have_md_files(self, test_env):
        """Commands have .md files."""
        run_osx(["install", "opencode"], cwd=test_env)

        commands_dir = test_env / ".opencode" / "commands"
        md_files = list(commands_dir.glob("*.md"))
        assert len(md_files) > 0


class TestErrorHandling:
    """Tests for error handling."""

    def test_install_to_invalid_tool_fails(self, test_env):
        """Install to invalid tool fails gracefully."""
        result = run_osx(["install", "nonexistent-tool"], cwd=test_env)
        assert result.returncode == 1


class TestVersionAwareUpgrade:
    """Tests for version-aware upgrade behavior."""

    def test_install_upgrades_when_source_version_greater(self, test_env):
        """Install upgrades when source version > installed version."""
        run_osx(["install", "opencode"], cwd=test_env)

        manifest = test_env / ".opencode" / "manifest.toml"
        manifest_data = toml.loads(manifest.read_text())
        manifest_data["resources"]["skills"]["osx-concepts"]["version"] = "0.1.0"
        manifest.write_text(toml.dumps(manifest_data))

        result = run_osx(["install", "opencode"], cwd=test_env)
        assert result.returncode == 0

        new_manifest = toml.loads(manifest.read_text())
        assert new_manifest["resources"]["skills"]["osx-concepts"]["version"] != "0.1.0"

    def test_install_skips_when_versions_match(self, test_env):
        """Install skips when source version == installed version."""
        run_osx(["install", "opencode"], cwd=test_env)

        result = run_osx(["install", "opencode"], cwd=test_env)
        assert result.returncode == 0
        assert (
            "Skipped" in result.stdout
            or "0 skill" in result.stdout
            or "are current" in result.stdout
        )

    def test_manifest_tracks_deployed_resources(self, test_env):
        """Manifest tracks deployed resources with versions."""
        run_osx(["install", "opencode", "--with-autonomous"], cwd=test_env)

        manifest = test_env / ".opencode" / "manifest.toml"
        manifest_data = toml.loads(manifest.read_text())

        assert manifest_data.get("version") == __version__

        assert len(manifest_data["resources"]["skills"]) > 0
        assert (
            manifest_data["resources"]["skills"]["osx-concepts"]["version"] is not None
        )

        assert len(manifest_data["resources"]["agents"]) > 0
        assert (
            manifest_data["resources"]["agents"]["osx-analyzer"]["version"] is not None
        )

    def test_update_always_deploys_regardless_of_version(self, test_env):
        """Update always deploys regardless of version."""
        run_osx(["install", "opencode"], cwd=test_env)

        skill_path = test_env / ".opencode" / "skills" / "osx-concepts" / "SKILL.md"
        (skill_path).write_text((skill_path).read_text() + "\nmodified")

        result = run_osx(["update", "opencode"], cwd=test_env)
        assert result.returncode == 0

        assert "modified" not in (skill_path).read_text()


class TestValidation:
    """Tests for validation without false positives."""

    def test_validation_no_warnings(self, test_env):
        """Validation shows no warnings for any manifest resource."""
        result = run_osx(["install", "opencode"], cwd=test_env)
        assert result.returncode == 0

        output = result.stdout + result.stderr
        assert "in manifest but not deployed" not in output


class TestInstallAutonomousFlag:
    """Tests for the --with-autonomous / --no-with-autonomous flag.

    The flag gates the 7-phase autonomous workflow resources (phase commands,
    agents, and the osx-workflow skill) on top of the utility default.
    """

    def test_install_without_autonomous_skips_phase_commands(self, test_env):
        """`--no-with-autonomous` install does not deploy osx-phase0..6 commands."""
        result = run_osx(["install", "opencode", "--no-with-autonomous"], cwd=test_env)

        assert result.returncode == 0
        commands_dir = test_env / ".opencode" / "commands"
        for n in range(7):
            assert not (commands_dir / f"osx-phase{n}.md").is_file(), (
                f"osx-phase{n}.md should not exist under utility-only install"
            )

    def test_install_without_autonomous_skips_agents(self, test_env):
        """`--no-with-autonomous` install leaves no osx-* agents on disk."""
        result = run_osx(["install", "opencode", "--no-with-autonomous"], cwd=test_env)

        assert result.returncode == 0
        agents_dir = test_env / ".opencode" / "agents"
        if agents_dir.is_dir():
            deployed = {p.stem for p in agents_dir.glob("*.md")}
            assert not deployed, (
                f"Agents directory should be empty under utility-only install; "
                f"found {deployed}"
            )

    def test_install_without_autonomous_skips_workflow_skill(self, test_env):
        """`--no-with-autonomous` install does not deploy the osx-workflow skill."""
        result = run_osx(["install", "opencode", "--no-with-autonomous"], cwd=test_env)

        assert result.returncode == 0
        skills_dir = test_env / ".opencode" / "skills"
        assert not (skills_dir / "osx-workflow").is_dir(), (
            "osx-workflow skill should not exist under utility-only install"
        )

    def test_install_without_autonomous_deploys_utility_skills(self, test_env):
        """`--no-with-autonomous` install still deploys utility skills."""
        result = run_osx(["install", "opencode", "--no-with-autonomous"], cwd=test_env)

        assert result.returncode == 0
        skills_dir = test_env / ".opencode" / "skills"
        assert (skills_dir / "osx-concepts").is_dir()
        assert (skills_dir / "osx-modify-artifacts").is_dir()
        assert (skills_dir / "osx-review-artifacts").is_dir()
        assert (skills_dir / "osx-commit").is_dir()

    def test_install_without_autonomous_deploys_utility_commands(self, test_env):
        """`--no-with-autonomous` install still deploys utility commands."""
        result = run_osx(["install", "opencode", "--no-with-autonomous"], cwd=test_env)

        assert result.returncode == 0
        commands_dir = test_env / ".opencode" / "commands"
        for name in ("osx-modify", "osx-review", "osx-changelog", "osx-maintain-docs"):
            assert (commands_dir / f"{name}.md").is_file(), (
                f"{name}.md should exist under utility-only install"
            )

    def test_install_with_autonomous_deploys_phase_commands(self, test_env):
        """`--with-autonomous` (or default) install deploys osx-phase0..6 commands."""
        result = run_osx(["install", "opencode", "--with-autonomous"], cwd=test_env)

        assert result.returncode == 0
        commands_dir = test_env / ".opencode" / "commands"
        for n in range(7):
            assert (commands_dir / f"osx-phase{n}.md").is_file(), (
                f"osx-phase{n}.md should exist with --with-autonomous"
            )

    def test_install_with_autonomous_deploys_agents(self, test_env):
        """`--with-autonomous` install deploys osx-analyzer, builder, maintainer, reviewer."""
        result = run_osx(["install", "opencode", "--with-autonomous"], cwd=test_env)

        assert result.returncode == 0
        agents_dir = test_env / ".opencode" / "agents"
        for name in ("osx-analyzer", "osx-builder", "osx-maintainer", "osx-reviewer"):
            assert (agents_dir / f"{name}.md").is_file(), (
                f"{name}.md should exist with --with-autonomous"
            )

    def test_install_without_autonomous_skips_gitignore_markers(self, test_env):
        """`--no-with-autonomous` install does not add orchestrator gitignore markers."""
        result = run_osx(["install", "opencode", "--no-with-autonomous"], cwd=test_env)

        assert result.returncode == 0
        gitignore = test_env / ".gitignore"
        if gitignore.is_file():
            content = gitignore.read_text()
            assert "BEGIN OpenSpec autonomous" not in content, (
                "Utility-only install should not add autonomous-state gitignore entries"
            )

    def test_install_with_autonomous_adds_gitignore_markers(self, test_env):
        """`--with-autonomous` install adds the orchestrator gitignore markers."""
        result = run_osx(["install", "opencode", "--with-autonomous"], cwd=test_env)

        assert result.returncode == 0
        gitignore = test_env / ".gitignore"
        assert gitignore.is_file()
        content = gitignore.read_text()
        assert "BEGIN OpenSpec autonomous" in content

    def test_update_without_autonomous_does_not_refresh_phase_commands(self, test_env):
        """`update --with-autonomous` after a utility-only install adds the autonomous
        resources. ``update --no-with-autonomous`` leaves them absent.
        """
        run_osx(["install", "opencode", "--no-with-autonomous"], cwd=test_env)

        result = run_osx(["update", "opencode", "--no-with-autonomous"], cwd=test_env)
        assert result.returncode == 0

        commands_dir = test_env / ".opencode" / "commands"
        for n in range(7):
            assert not (commands_dir / f"osx-phase{n}.md").is_file(), (
                f"osx-phase{n}.md should remain absent after no-autonomous update"
            )


class TestUpdateRemovesStale:
    """``update`` reconciles the deployed tree against the current manifest.

    Locks in that resources which are no longer present in the source
    manifest are removed on the next ``update``. Custom (non-``osx-``/non-
    ``osc-``) resources are preserved across updates.
    """

    def _seed_obsolete(self, test_env: Path, tool: str) -> None:
        """Plant stale ``osx-*`` resources of every type."""
        target = test_env / TOOL_DIRS[tool]

        # Stale skill
        skill = target / "skills" / "osx-obsolete-skill"
        skill.mkdir(parents=True, exist_ok=True)
        (skill / "SKILL.md").write_text("---\nname: osx-obsolete-skill\n---\nold")

        # Stale agent
        agent = target / "agents" / "osx-obsolete-agent.md"
        agent.parent.mkdir(parents=True, exist_ok=True)
        agent.write_text("# obsolete agent")

        # Stale command (per-platform layout)
        commands = target / "commands"
        commands.mkdir(parents=True, exist_ok=True)
        if tool == "opencode":
            (commands / "osx-obsolete-cmd.md").write_text("# obsolete")
        else:
            (commands / "osx" / "obsolete-cmd.md").parent.mkdir(
                parents=True, exist_ok=True
            )
            (commands / "osx" / "obsolete-cmd.md").write_text("# obsolete")

        # Custom resource that must survive every update
        (target / "skills" / "my-custom-skill").mkdir(parents=True, exist_ok=True)
        (target / "skills" / "my-custom-skill" / "SKILL.md").write_text(
            "---\nname: my-custom-skill\n---\ncustom"
        )

    def test_update_opencode_removes_obsolete_osx_resources(self, test_env):
        run_osx(["install", "opencode", "--with-autonomous"], cwd=test_env)
        self._seed_obsolete(test_env, "opencode")

        result = run_osx(["update", "opencode", "--with-autonomous"], cwd=test_env)
        assert result.returncode == 0

        target = test_env / ".opencode"
        assert not (target / "skills" / "osx-obsolete-skill").exists()
        assert not (target / "agents" / "osx-obsolete-agent.md").exists()
        assert not (target / "commands" / "osx-obsolete-cmd.md").exists()

        # Custom resources preserved
        assert (target / "skills" / "my-custom-skill").is_dir()

        # Current resources untouched
        assert (target / "skills" / "osx-concepts").is_dir()
        assert (target / "agents" / "osx-analyzer.md").is_file()
        assert (target / "commands" / "osx-phase0.md").is_file()

    def test_update_claude_removes_obsolete_osx_resources(self, test_env):
        run_osx(["install", "claude", "--with-autonomous"], cwd=test_env)
        self._seed_obsolete(test_env, "claude")

        result = run_osx(["update", "claude", "--with-autonomous"], cwd=test_env)
        assert result.returncode == 0

        target = test_env / ".claude"
        assert not (target / "skills" / "osx-obsolete-skill").exists()
        assert not (target / "commands" / "osx" / "obsolete-cmd.md").exists()

        # Current resources untouched
        assert (target / "skills" / "osx-concepts").is_dir()
        assert (target / "commands" / "osx" / "phase0.md").is_file()

    def test_install_does_not_remove_obsolete_resources(self, test_env):
        """``install`` is non-destructive; only ``update`` reconciles the tree."""
        run_osx(["install", "opencode", "--with-autonomous"], cwd=test_env)
        self._seed_obsolete(test_env, "opencode")

        # Install runs should NOT purge leftovers left by an older release.
        result = run_osx(["install", "opencode", "--with-autonomous"], cwd=test_env)
        assert result.returncode == 0

        target = test_env / ".opencode"
        assert (target / "skills" / "osx-obsolete-skill").is_dir()
        assert (target / "agents" / "osx-obsolete-agent.md").is_file()
        assert (target / "commands" / "osx-obsolete-cmd.md").is_file()

    def test_update_does_not_touch_other_tool(self, test_env):
        """Cleanup only affects the requested tool directory."""
        run_osx(["install", "opencode", "--with-autonomous"], cwd=test_env)
        run_osx(["install", "claude", "--with-autonomous"], cwd=test_env)
        self._seed_obsolete(test_env, "claude")

        result = run_osx(["update", "opencode", "--with-autonomous"], cwd=test_env)
        assert result.returncode == 0

        # Claude tree should still contain the obsolete resources
        claude_target = test_env / ".claude"
        assert (claude_target / "skills" / "osx-obsolete-skill").is_dir()
        assert (claude_target / "commands" / "osx" / "obsolete-cmd.md").is_file()

        # OpenCode tree (which had no obsolete resources) remains valid
        opencode_target = test_env / ".opencode"
        assert (opencode_target / "skills" / "osx-concepts").is_dir()

    def test_update_preserves_non_managed_skills(self, test_env):
        """Resources outside the managed prefix must never be deleted."""
        run_osx(["install", "opencode"], cwd=test_env)

        target = test_env / ".opencode"
        for skill in ("my-review", "team-onboarding", "my-osx-helper"):
            (target / "skills" / skill).mkdir(parents=True, exist_ok=True)
            (target / "skills" / skill / "SKILL.md").write_text(skill)
        (target / "agents" / "my-agent.md").parent.mkdir(parents=True, exist_ok=True)
        (target / "agents" / "my-agent.md").write_text("# agent")
        (target / "commands" / "my-command.md").write_text("# cmd")
        (target / "commands" / "oscillator.md").write_text("# cmd")

        result = run_osx(["update", "opencode"], cwd=test_env)
        assert result.returncode == 0

        for skill in ("my-review", "team-onboarding", "my-osx-helper"):
            assert (target / "skills" / skill).is_dir(), skill
        assert (target / "agents" / "my-agent.md").is_file()
        assert (target / "commands" / "my-command.md").is_file()
        assert (target / "commands" / "oscillator.md").is_file()


class TestUpdateAutonomousToggleCleanup:
    """Switching between autonomous and utility-only via ``update`` must
    reconcile the deployed tree so that previously-deployed autonomous
    resources are removed when ``--no-with-autonomous`` is set.
    """

    def test_update_drops_autonomous_resources_when_toggled_off(self, test_env):
        run_osx(["install", "opencode", "--with-autonomous"], cwd=test_env)

        # Sanity check: autonomous resources present after first install.
        target = test_env / ".opencode"
        assert (target / "commands" / "osx-phase0.md").is_file()
        assert (target / "agents" / "osx-analyzer.md").is_file()
        assert (target / "skills" / "osx-workflow").is_dir()

        result = run_osx(["update", "opencode", "--no-with-autonomous"], cwd=test_env)
        assert result.returncode == 0

        # Autonomous resources are gone
        for n in range(7):
            assert not (target / "commands" / f"osx-phase{n}.md").exists()
        agents_dir = target / "agents"
        if agents_dir.is_dir():
            assert not any(agents_dir.glob("*.md")), (
                "Autonomous agents should be removed under no-with-autonomous"
            )
        assert not (target / "skills" / "osx-workflow").exists()

        # Utility resources remain
        assert (target / "skills" / "osx-concepts").is_dir()
        assert (target / "commands" / "osx-modify.md").is_file()

    def test_update_adds_autonomous_resources_when_toggled_on(self, test_env):
        run_osx(["install", "opencode", "--no-with-autonomous"], cwd=test_env)

        target = test_env / ".opencode"
        assert not (target / "skills" / "osx-workflow").exists()

        result = run_osx(["update", "opencode", "--with-autonomous"], cwd=test_env)
        assert result.returncode == 0

        assert (target / "skills" / "osx-workflow").is_dir()
        for n in range(7):
            assert (target / "commands" / f"osx-phase{n}.md").is_file()
        assert (target / "agents" / "osx-analyzer.md").is_file()
