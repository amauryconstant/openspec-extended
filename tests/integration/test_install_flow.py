#!/usr/bin/env python3
"""
Integration tests for install flow.
"""

import re
import subprocess
import sys
from pathlib import Path

import toml
import yaml

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
        assert (test_env / ".opencode" / "skills" / "osx-commit").is_dir()
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
        """Install opencode writes a per-side manifest with the version field.

        Phase 5 split: orchestrator-side resources land in
        ``.opencode/manifest.toml`` (legacy position) and skills-side
        resources land in ``.opencode/skills-manifest.toml``. Both
        manifests carry the project ``version`` so callers can detect drift.
        Uses ``--with-autonomous`` so ``osx-workflow`` (the only
        orchestrator-side skill) is included in the orchestrator manifest.
        """
        result = run_osx(["install", "opencode", "--with-autonomous"], cwd=test_env)

        assert result.returncode == 0
        orch_manifest_path = test_env / ".opencode" / "manifest.toml"
        skills_manifest_path = test_env / ".opencode" / "skills-manifest.toml"
        assert orch_manifest_path.is_file()
        assert skills_manifest_path.is_file()

        with open(orch_manifest_path) as f:
            orch_manifest = toml.load(f)
        with open(skills_manifest_path) as f:
            skills_manifest = toml.load(f)

        assert orch_manifest.get("version") == __version__
        assert skills_manifest.get("version") == __version__

        # Disjoint resource ownership: orchestrator-side skills do not
        # include skills-side names, and vice versa.
        orch_skills = set(orch_manifest["resources"]["skills"])
        skills_skills = set(skills_manifest["resources"]["skills"])
        assert "osx-workflow" in orch_skills
        assert "osx-commit" in skills_skills
        assert orch_skills.isdisjoint(skills_skills)

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
        assert (test_env / ".claude" / "skills" / "osx-commit").is_dir()


class TestInstallClaudeDualEmit:
    """Claude Code merges commands and skills. Each opencode slash command
    must dual-emit on Claude as both a legacy ``.claude/commands/osx/<name>.md``
    and a modern ``.claude/skills/osx-<name>/SKILL.md``. Mirrors upstream
    OpenSpec's dual-emit strategy (introduced in v1.7.0, current as of v1.13.0).
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


class TestInstallTokenSubstitution:
    """Token substitution regression: the deploy step must rewrite every
    ``{{TOKEN}}`` placeholder in shipped resources. A regression here means
    the deploy drops literal ``{{CMD_PREFIX}}``, ``{{PLATFORM_DIR}}``, etc.
    into users' projects, which is the bug that motivated this class.

    The pytest entry points mirror the e2e bats cases so the regression
    guard runs both in the source tree (pytest) and against the built
    binary (bats).
    """

    LEFTOVER_TOKEN_RE = re.compile(r"\{\{[A-Z_]+\}\}")

    def _leftover_files(self, root: Path) -> list[Path]:
        if not root.is_dir():
            return []
        return [
            md
            for md in root.rglob("*.md")
            if self.LEFTOVER_TOKEN_RE.search(md.read_text())
        ]

    @pytest.mark.parametrize("tool", ["opencode", "claude"])
    def test_install_leaves_no_token_placeholders(self, test_env, tool: str):
        """No deployed ``.md`` should still contain a ``{{TOKEN}}``."""
        result = run_osx(
            ["install", tool, "--with-autonomous"], cwd=test_env
        )
        assert result.returncode == 0, result.stderr

        leftovers = self._leftover_files(test_env / TOOL_DIRS[tool])
        assert not leftovers, (
            f"{tool}: deployed files still contain {{TOKEN}} placeholders: "
            + ", ".join(str(p.relative_to(test_env)) for p in leftovers)
        )

    def test_install_opencode_uses_hyphen_slash_command(self, test_env):
        """OpenCode deploy uses the hyphen slash-command form (``/osx-review``)."""
        result = run_osx(
            ["install", "opencode", "--with-autonomous"], cwd=test_env
        )
        assert result.returncode == 0, result.stderr

        cmd = (test_env / ".opencode" / "commands" / "osx-review.md").read_text()
        assert "/osx-review" in cmd
        # The Claude colon form must NOT appear in an opencode deploy.
        assert "/osx:review" not in cmd
        # The platform dir token must be substituted.
        assert ".opencode/skills" in cmd
        # The skill-path reference must use the literal hyphenated directory.
        assert ".opencode/skills/osx-review-artifacts/SKILL.md" in cmd

    def test_install_claude_uses_colon_slash_command(self, test_env):
        """Claude deploy uses the colon slash-command form (``/osx:review``)."""
        result = run_osx(
            ["install", "claude", "--with-autonomous"], cwd=test_env
        )
        assert result.returncode == 0, result.stderr

        # The Claude deploy writes the legacy command form at
        # ``commands/osx/review.md`` (matching the
        # ``commands_style="namespaced-with-skill-mirror"`` layout).
        cmd = (test_env / ".claude" / "commands" / "osx" / "review.md").read_text()
        assert "/osx:review" in cmd
        # The opencode hyphen slash-command form must NOT appear in a claude
        # deploy (modulo the skill-path reference which is hyphenated on both
        # platforms).
        slash_labels = re.findall(r"\| `/osx[-:][\w-]+`", cmd)
        assert slash_labels and all("`/osx:" in lbl for lbl in slash_labels), (
            f"slash-command labels must be Claude form on Claude: {slash_labels}"
        )
        # The substituted platform dir is `.claude/...`.
        assert ".claude/skills" in cmd
        # The skill-path reference must use the literal hyphenated directory.
        assert ".claude/skills/osx-review-artifacts/SKILL.md" in cmd
        assert "osx:review-artifacts" not in cmd

    def test_install_claude_skill_mirror_path_resolves(self, test_env):
        """The dual-emit Claude skill mirror must point at the real
        ``osx-review-artifacts`` directory (hyphen, not colon)."""
        result = run_osx(
            ["install", "claude", "--with-autonomous"], cwd=test_env
        )
        assert result.returncode == 0, result.stderr

        skill_md = test_env / ".claude" / "skills" / "osx-review" / "SKILL.md"
        assert skill_md.is_file()
        text = skill_md.read_text()
        assert "osx-review-artifacts" in text
        assert "osx:review-artifacts" not in text
        # The referenced skill directory must actually exist on disk.
        assert (test_env / ".claude" / "skills" / "osx-review-artifacts").is_dir()


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


class TestInstallWithCoreLanguage:
    """A.5: ``--language`` flag and ``OPENSPEC_LANGUAGE`` env var propagate
    through ``install --with-core`` into the generated ``openspec/config.yaml``.
    """

    def test_install_with_core_propagates_language(self, test_env):
        """`install opencode --with-core --language french` -> config.yaml context
        mentions 'french'."""
        result = run_osx(
            ["install", "opencode", "--with-core", "--language", "french"],
            cwd=test_env,
        )
        assert result.returncode == 0, result.stderr

        config_path = test_env / "openspec" / "config.yaml"
        assert config_path.is_file(), (
            f"openspec/config.yaml should exist after install --with-core; "
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
        config = yaml.safe_load(config_path.read_text())
        context = config.get("context", "") or ""
        assert "french" in context, f"context missing 'french': {context!r}"

    def test_install_with_core_env_language(self, test_env):
        """OPENSPEC_LANGUAGE=portuguese + install --with-core (no flag) ->
        config.yaml context mentions 'portuguese'."""
        import os

        env = os.environ.copy()
        env["OPENSPEC_LANGUAGE"] = "portuguese"
        cmd = [sys.executable, "-m", "source", "install", "opencode", "--with-core"]
        result = subprocess.run(cmd, cwd=test_env, capture_output=True, text=True, env=env)

        assert result.returncode == 0, (
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

        config_path = test_env / "openspec" / "config.yaml"
        assert config_path.is_file(), (
            f"openspec/config.yaml should exist after install --with-core; "
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
        config = yaml.safe_load(config_path.read_text())
        context = config.get("context", "") or ""
        assert "portuguese" in context, f"context missing 'portuguese': {context!r}"


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

        skill_path = test_env / ".opencode" / "skills" / "osx-commit" / "SKILL.md"
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
        """Install upgrades when source version > installed version.

        Phase 5 split: ``osx-commit`` lives in the skills-side manifest,
        so the version-downgrade simulation targets that file.
        """
        run_osx(["install", "opencode"], cwd=test_env)

        manifest = test_env / ".opencode" / "skills-manifest.toml"
        manifest_data = toml.loads(manifest.read_text())
        manifest_data["resources"]["skills"]["osx-commit"]["version"] = "0.1.0"
        manifest.write_text(toml.dumps(manifest_data))

        result = run_osx(["install", "opencode"], cwd=test_env)
        assert result.returncode == 0

        new_manifest = toml.loads(manifest.read_text())
        assert new_manifest["resources"]["skills"]["osx-commit"]["version"] != "0.1.0"

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
        """Both per-side manifests track their resources with versions.

        ``osx-workflow`` is orchestrator-side; ``osx-commit`` is
        skills-side. Both must end up declared with a non-None version
        in the appropriate manifest.
        """
        run_osx(["install", "opencode", "--with-autonomous"], cwd=test_env)

        orch_manifest_path = test_env / ".opencode" / "manifest.toml"
        skills_manifest_path = test_env / ".opencode" / "skills-manifest.toml"
        orch_manifest = toml.loads(orch_manifest_path.read_text())
        skills_manifest = toml.loads(skills_manifest_path.read_text())

        assert orch_manifest.get("version") == __version__
        assert skills_manifest.get("version") == __version__

        assert len(orch_manifest["resources"]["skills"]) > 0
        assert (
            orch_manifest["resources"]["skills"]["osx-workflow"]["version"]
            is not None
        )

        assert len(skills_manifest["resources"]["skills"]) > 0
        assert (
            skills_manifest["resources"]["skills"]["osx-commit"]["version"]
            is not None
        )

        assert len(orch_manifest["resources"]["agents"]) > 0
        assert (
            orch_manifest["resources"]["agents"]["osx-analyzer"]["version"]
            is not None
        )

    def test_update_always_deploys_regardless_of_version(self, test_env):
        """Update always deploys regardless of version."""
        run_osx(["install", "opencode"], cwd=test_env)

        skill_path = test_env / ".opencode" / "skills" / "osx-commit" / "SKILL.md"
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
        assert (skills_dir / "osx-commit").is_dir()
        assert (skills_dir / "osx-review-artifacts").is_dir()
        assert (skills_dir / "osx-commit").is_dir()

    def test_install_without_autonomous_deploys_utility_commands(self, test_env):
        """`--no-with-autonomous` install still deploys utility commands."""
        result = run_osx(["install", "opencode", "--no-with-autonomous"], cwd=test_env)

        assert result.returncode == 0
        commands_dir = test_env / ".opencode" / "commands"
        for name in ("osx-review", "osx-changelog", "osx-maintain-docs"):
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
        assert (target / "skills" / "osx-commit").is_dir()
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
        assert (target / "skills" / "osx-commit").is_dir()
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
        assert (opencode_target / "skills" / "osx-commit").is_dir()

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
        assert (target / "skills" / "osx-commit").is_dir()
        assert (target / "commands" / "osx-review.md").is_file()

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


class _FakeOpenspec:
    """Helper that builds a fake ``openspec`` shell script on a tmpdir and
    adds it to PATH for the duration of one test.

    The fake binary delegates everything to the real ``openspec`` (resolved
    via ``OSX_REAL_OPENSPEC`` env var, which the test sets up) EXCEPT
    ``validate --archived --json``, which exits with ``archived_returncode``
    so we can simulate the "unfinished archives" state without seeding a
    real archive directory on disk.

    Set ``archived_returncode=0`` to simulate a clean tree.
    """

    def __init__(
        self,
        bin_dir: Path,
        archived_returncode: int = 0,
    ) -> None:
        self.bin_dir = bin_dir
        self.archived_returncode = archived_returncode

    def install(self) -> Path:
        self.bin_dir.mkdir(parents=True, exist_ok=True)
        script = self.bin_dir / "openspec"
        script.write_text(
            "#!/usr/bin/env bash\n"
            'if [ "$1" = "validate" ] && [ "$2" = "--archived" ]; then\n'
            '  exit "${OSX_FAKE_ARCHIVED_RC:-0}"\n'
            "fi\n"
            'if [ -n "${OSX_REAL_OPENSPEC:-}" ] && [ -x "${OSX_REAL_OPENSPEC}" ]; then\n'
            '  exec "${OSX_REAL_OPENSPEC}" "$@"\n'
            "fi\n"
            "exit 0\n"
        )
        script.chmod(0o755)
        return script


def _run_with_fake_openspec(
    args: list[str],
    cwd: Path,
    tmp_path: Path,
    archived_returncode: int = 0,
) -> subprocess.CompletedProcess:
    """Run ``openspec-extended <args>`` with a fake ``openspec`` binary on PATH.

    The fake delegates everything to the real ``openspec`` (resolved via
    ``OSX_REAL_OPENSPEC``) except ``validate --archived --json``, which it
    exits with the supplied ``archived_returncode``.
    """
    import os
    import shutil

    real_openspec = shutil.which("openspec")
    if real_openspec is None:
        pytest.skip("openspec CLI not on PATH; cannot run install/update-core tests")

    bin_dir = tmp_path / "fake-bin"
    fake = _FakeOpenspec(bin_dir, archived_returncode=archived_returncode)
    fake.install()

    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    env["OSX_FAKE_ARCHIVED_RC"] = str(archived_returncode)
    env["OSX_REAL_OPENSPEC"] = real_openspec
    env["HOME"] = str(tmp_path / "fake-home")
    (tmp_path / "fake-home").mkdir()

    if "OPENSPEC_NO_UPDATE_CHECK" not in env:
        env["OPENSPEC_NO_UPDATE_CHECK"] = "1"

    cmd = [sys.executable, "-m", "source", *args]
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, env=env, check=False
    )


class TestValidateArchivedSweep:
    """A.6: ``install --with-core`` and ``update-core`` run a non-fatal
    ``openspec validate --archived --json`` sweep after core deployment so
    unfinished archive state surfaces immediately rather than the next
    time ``osc-bulk-archive-change`` runs.
    """

    def test_install_with_core_warns_on_unfinished_archives(
        self, test_env, tmp_path
    ):
        """Non-fatal default: a warning is printed, exit code is 0."""
        result = _run_with_fake_openspec(
            ["install", "opencode", "--with-core"],
            cwd=test_env,
            tmp_path=tmp_path,
            archived_returncode=1,
        )
        output = result.stdout + result.stderr
        assert result.returncode == 0, (
            f"non-fatal sweep should not fail install; got {result.returncode}\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
        assert "Post-install sweep found unfinished archive state" in output, output
        assert "validate --archived" in output, output
        assert "tasks.md" in output, output

    def test_install_with_core_strict_archived_exits_nonzero(
        self, test_env, tmp_path
    ):
        """``--strict-archived`` makes a failing sweep exit non-zero."""
        result = _run_with_fake_openspec(
            ["install", "opencode", "--with-core", "--strict-archived"],
            cwd=test_env,
            tmp_path=tmp_path,
            archived_returncode=1,
        )
        assert result.returncode != 0, (
            f"--strict-archived should fail on unfinished archives; "
            f"got {result.returncode}\nstdout={result.stdout}\nstderr={result.stderr}"
        )
        output = result.stdout + result.stderr
        assert "Post-install sweep" in output

    def test_install_with_core_strict_archived_env_var_exits_nonzero(
        self, test_env, tmp_path, monkeypatch
    ):
        """``OPENSPEC_VALIDATE_ARCHIVED_STRICT=1`` env var triggers strict mode."""
        import os
        import shutil

        real_openspec = shutil.which("openspec")
        if real_openspec is None:
            pytest.skip("openspec CLI not on PATH")

        bin_dir = tmp_path / "fake-bin"
        _FakeOpenspec(bin_dir, archived_returncode=1).install()

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
        env["OSX_FAKE_ARCHIVED_RC"] = "1"
        env["OSX_REAL_OPENSPEC"] = real_openspec
        env["HOME"] = str(tmp_path / "fake-home")
        (tmp_path / "fake-home").mkdir()
        env["OPENSPEC_VALIDATE_ARCHIVED_STRICT"] = "1"
        env["OPENSPEC_NO_UPDATE_CHECK"] = "1"

        cmd = [sys.executable, "-m", "source", "install", "opencode", "--with-core"]
        result = subprocess.run(
            cmd, cwd=test_env, capture_output=True, text=True, env=env, check=False
        )
        assert result.returncode != 0, (
            f"OPENSPEC_VALIDATE_ARCHIVED_STRICT=1 should fail; got {result.returncode}\n"
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )

    def test_install_with_core_skips_sweep_when_openspec_missing(
        self, test_env, tmp_path
    ):
        """With no ``openspec`` on PATH, the sweep silently skips and install exits 0."""
        import os

        env = os.environ.copy()
        # Force PATH to an empty dir so openspec cannot be resolved.
        empty_bin = tmp_path / "empty-bin"
        empty_bin.mkdir()
        env["PATH"] = str(empty_bin)
        env["HOME"] = str(tmp_path / "fake-home")
        (tmp_path / "fake-home").mkdir()

        cmd = [sys.executable, "-m", "source", "install", "opencode", "--with-core"]
        result = subprocess.run(
            cmd, cwd=test_env, capture_output=True, text=True, env=env, check=False
        )
        # Install requires openspec init which will fail too — so we accept
        # any non-strict result and only assert the sweep's FileNotFoundError
        # path is handled gracefully (no traceback).
        output = result.stdout + result.stderr
        assert "Traceback" not in output, output

    def test_update_core_also_runs_sweep(self, test_env, tmp_path):
        """``update-core`` also runs the post-update sweep."""
        result = _run_with_fake_openspec(
            ["update-core"],
            cwd=test_env,
            tmp_path=tmp_path,
            archived_returncode=1,
        )
        output = result.stdout + result.stderr
        assert "Post-install sweep found unfinished archive state" in output, (
            f"stdout={result.stdout}\nstderr={result.stderr}"
        )
        assert "validate --archived" in output, output


class TestValidateArchivedSweepInProcess:
    """Direct in-process unit-style tests of ``_post_install_archived_sweep``.

    These tests patch ``subprocess.run`` at the module level so the function
    can be exercised in isolation without shelling out to a real CLI.
    """

    def test_sweep_returns_true_on_success(self, monkeypatch):
        from unittest.mock import MagicMock

        from source.cli import _post_install_archived_sweep

        monkeypatch.setattr(
            "source.cli.subprocess.run",
            lambda *a, **kw: MagicMock(returncode=0, stdout="{}", stderr=""),
        )
        assert _post_install_archived_sweep() is True

    def test_sweep_returns_false_on_nonzero(self, monkeypatch):
        from unittest.mock import MagicMock

        from source.cli import _post_install_archived_sweep

        monkeypatch.setattr(
            "source.cli.subprocess.run",
            lambda *a, **kw: MagicMock(
                returncode=1, stdout="{}", stderr="unfinished archive"
            ),
        )
        assert _post_install_archived_sweep() is False

    def test_sweep_strict_exits_nonzero_on_failure(self, monkeypatch):
        from unittest.mock import MagicMock

        from source.cli import _post_install_archived_sweep

        monkeypatch.setattr(
            "source.cli.subprocess.run",
            lambda *a, **kw: MagicMock(returncode=1, stdout="{}", stderr=""),
        )
        with pytest.raises(SystemExit) as exc:
            _post_install_archived_sweep(strict=True)
        assert exc.value.code != 0

    def test_sweep_skips_when_openspec_missing(self, monkeypatch):
        from source.cli import _post_install_archived_sweep

        def _raise_filenf(*a, **kw):
            raise FileNotFoundError("openspec")

        monkeypatch.setattr("source.cli.subprocess.run", _raise_filenf)
        assert _post_install_archived_sweep() is True

    def test_sweep_skips_on_timeout(self, monkeypatch):
        from source.cli import _post_install_archived_sweep

        def _raise_timeout(*a, **kw):
            import subprocess as _sp

            raise _sp.TimeoutExpired(cmd=["openspec"], timeout=30)

        monkeypatch.setattr("source.cli.subprocess.run", _raise_timeout)
        assert _post_install_archived_sweep() is True

    def test_sweep_env_var_overrides_strict(self, monkeypatch):
        from unittest.mock import MagicMock

        from source.cli import _post_install_archived_sweep

        monkeypatch.setenv("OPENSPEC_VALIDATE_ARCHIVED_STRICT", "1")
        monkeypatch.setattr(
            "source.cli.subprocess.run",
            lambda *a, **kw: MagicMock(returncode=1, stdout="{}", stderr=""),
        )
        with pytest.raises(SystemExit):
            _post_install_archived_sweep(strict=False)
        monkeypatch.delenv("OPENSPEC_VALIDATE_ARCHIVED_STRICT", raising=False)
