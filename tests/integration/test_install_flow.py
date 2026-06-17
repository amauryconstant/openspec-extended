#!/usr/bin/env python3
"""
Integration tests for install flow.
"""

import json
import subprocess
import sys

import toml
from pathlib import Path

import pytest

from source.cli import app

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
        result = run_osx(["install", "opencode"], cwd=test_env)

        assert result.returncode == 0
        assert (test_env / ".opencode" / "skills").is_dir()
        assert (test_env / ".opencode" / "commands").is_dir()
        assert (test_env / ".opencode" / "scripts").is_dir()
        assert (test_env / ".opencode" / "agents").is_dir()

    def test_install_opencode_copies_extension_skills(self, test_env):
        """Install opencode copies extension skills."""
        result = run_osx(["install", "opencode"], cwd=test_env)

        assert result.returncode == 0
        assert (test_env / ".opencode" / "skills" / "osx-concepts").is_dir()
        assert (test_env / ".opencode" / "skills" / "osx-modify-artifacts").is_dir()
        assert (test_env / ".opencode" / "skills" / "osx-review-artifacts").is_dir()

    def test_install_opencode_copies_agents(self, test_env):
        """Install opencode copies agents."""
        result = run_osx(["install", "opencode"], cwd=test_env)

        assert result.returncode == 0
        assert (test_env / ".opencode" / "agents" / "osx-analyzer.md").is_file()
        assert (test_env / ".opencode" / "agents" / "osx-builder.md").is_file()
        assert (test_env / ".opencode" / "agents" / "osx-maintainer.md").is_file()

    def test_install_opencode_copies_commands(self, test_env):
        """Install opencode copies commands."""
        result = run_osx(["install", "opencode"], cwd=test_env)

        assert result.returncode == 0
        assert (test_env / ".opencode" / "commands" / "osx-phase0.md").is_file()
        assert (test_env / ".opencode" / "commands" / "osx-phase1.md").is_file()
        assert (test_env / ".opencode" / "commands" / "osx-phase2.md").is_file()

    def test_install_opencode_copies_scripts_and_executable(self, test_env):
        """Install opencode copies scripts and makes executable."""
        result = run_osx(["install", "opencode"], cwd=test_env)

        assert result.returncode == 0
        script_path = test_env / ".opencode" / "scripts" / "osx-orchestrate"
        assert script_path.is_file()
        assert (script_path.stat().st_mode & 0o111) != 0

    def test_install_opencode_copies_lib_scripts(self, test_env):
        """Install opencode copies lib scripts."""
        result = run_osx(["install", "opencode"], cwd=test_env)

        assert result.returncode == 0
        assert (test_env / ".opencode" / "scripts" / "lib").is_dir()
        assert (test_env / ".opencode" / "scripts" / "lib" / "osx").is_file()

    def test_install_opencode_copies_manifest_with_version(self, test_env):
        """Install opencode copies manifest with version."""
        result = run_osx(["install", "opencode"], cwd=test_env)

        assert result.returncode == 0
        manifest_path = test_env / ".opencode" / "manifest.toml"
        assert manifest_path.is_file()

        with open(manifest_path) as f:
            manifest = toml.load(f)

        assert manifest.get("version") is not None
        assert manifest.get("version") != ""

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

    def test_install_with_core_includes_core_commands(self, test_env):
        """Install --with-core includes core commands."""
        result = run_osx(["install", "opencode", "--with-core"], cwd=test_env)

        assert result.returncode == 0
        commands_dir = test_env / ".opencode" / "commands"
        if commands_dir.is_dir():
            cmd_files = list(commands_dir.glob("*.md"))
            assert len(cmd_files) > 7 or (commands_dir / "osx").is_dir()


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

    def test_updates_gitignore_when_orchestrate_present(self, test_env):
        """Updates .gitignore when osx-orchestrate present."""
        run_osx(["install", "opencode"], cwd=test_env)

        gitignore = test_env / ".gitignore"
        assert gitignore.is_file()

        content = gitignore.read_text()
        assert "openspec/changes/*/state.json" in content

    def test_gitignore_has_markers(self, test_env):
        """Gitignore has BEGIN/END markers."""
        run_osx(["install", "opencode"], cwd=test_env)

        content = (test_env / ".gitignore").read_text()
        assert "BEGIN OpenSpec autonomous" in content
        assert "END OpenSpec autonomous" in content

    def test_gitignore_preserves_existing_content(self, test_env):
        """Gitignore preserves existing content."""
        gitignore = test_env / ".gitignore"
        gitignore.write_text("# Existing content\n")

        run_osx(["install", "opencode"], cwd=test_env)

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
        run_osx(["install", "opencode"], cwd=test_env)

        manifest = test_env / ".opencode" / "manifest.toml"
        manifest_data = toml.loads(manifest.read_text())

        assert manifest_data.get("version") is not None
        assert manifest_data.get("version") != "null"

        assert len(manifest_data["resources"]["skills"]) > 0
        assert (
            manifest_data["resources"]["skills"]["osx-concepts"]["version"] is not None
        )

        assert len(manifest_data["resources"]["agents"]) > 0
        assert (
            manifest_data["resources"]["scripts"]["osx-orchestrate"]["version"]
            is not None
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

    def test_validation_no_warnings_for_deployed_scripts_and_lib(self, test_env):
        """Validation shows no warnings for deployed scripts and lib."""
        result = run_osx(["install", "opencode"], cwd=test_env)
        assert result.returncode == 0

        output = result.stdout + result.stderr
        assert "Resource 'osx' in manifest but not deployed" not in output
        assert "Resource 'osx-orchestrate' in manifest but not deployed" not in output
