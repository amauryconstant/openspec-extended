#!/usr/bin/env python3
"""
Unit tests for openspec-extended CLI and deployment logic.
"""

import json

import toml
from pathlib import Path

import pytest
from typer.testing import CliRunner

from source.cli import (
    app,
    compare_versions,
    should_deploy,
    get_tool_dir,
    parse_version,
    get_installed_version,
    get_target_path,
    get_resources_dir,
)

runner = CliRunner()


@pytest.fixture
def temp_dir(tmp_path):
    """Create a temporary directory for testing."""
    return tmp_path


@pytest.fixture
def mock_resources_dir(temp_dir):
    """Create a mock resources directory with manifest."""
    resources = temp_dir / "resources"
    opencode = resources / "opencode"
    opencode.mkdir(parents=True)

    manifest = {
        "version": "1.0.0",
        "resources": {
            "skills": {"osx-test-skill": {"version": "1.0.0"}},
            "commands": {"osx-test": {"version": "1.0.0"}},
            "agents": {"osx-test-agent": {"version": "1.0.0"}},
            "scripts": {"test-script": {"version": "1.0.0"}},
        },
    }

    (opencode / "manifest.json").write_text(json.dumps(manifest))

    skills_dir = opencode / "skills" / "osx-test-skill"
    skills_dir.mkdir(parents=True)
    (skills_dir / "test.md").write_text("# Test skill")

    commands_dir = opencode / "commands"
    commands_dir.mkdir()
    (commands_dir / "osx-test.md").write_text("# Test command")

    agents_dir = opencode / "agents"
    agents_dir.mkdir()
    (agents_dir / "osx-test-agent.md").write_text("# Test agent")

    scripts_dir = opencode / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "test-script").write_text("#!/bin/bash\necho test")
    (scripts_dir / "test-script").chmod(0o755)

    lib_dir = scripts_dir / "lib"
    lib_dir.mkdir()
    (lib_dir / "test-lib").write_text("#!/bin/bash\necho test")
    (lib_dir / "test-lib").chmod(0o755)

    return resources


@pytest.mark.unit
class TestCLIParsing:
    """Tests for CLI argument parsing."""

    def test_install_command_requires_target(self):
        """install without tool shows error and exits 2 (Typer exit code)."""
        result = runner.invoke(app, ["install"])
        assert result.exit_code == 2
        assert "Missing argument" in result.output

    def test_update_command_requires_target(self):
        """update without tool shows error and exits 2 (Typer exit code)."""
        result = runner.invoke(app, ["update"])
        assert result.exit_code == 2
        assert "Missing argument" in result.output

    def test_run_command_requires_change_id(self):
        """run without change_id shows error and exits 2 (Typer exit code)."""
        result = runner.invoke(app, ["run"])
        assert result.exit_code == 2
        assert "Missing argument" in result.output

    def test_install_unknown_tool_shows_error(self):
        """install with invalid tool exits 1."""
        result = runner.invoke(app, ["install", "invalid-tool"])
        assert result.exit_code == 1

    def test_help_shows_commands(self):
        """--help displays install, update, and run commands."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "install" in result.output
        assert "update" in result.output
        assert "run" in result.output


@pytest.mark.unit
class TestVersionComparison:
    """Tests for compare_versions function."""

    def test_compare_versions_greater(self):
        """0.4.0 > 0.3.1 returns 1."""
        assert compare_versions("0.4.0", "0.3.1") == 1

    def test_compare_versions_less(self):
        """0.3.1 < 0.4.0 returns -1."""
        assert compare_versions("0.3.1", "0.4.0") == -1

    def test_compare_versions_equal(self):
        """Equal versions return 0."""
        assert compare_versions("1.2.3", "1.2.3") == 0
        assert compare_versions("0.4.0", "0.4.0") == 0

    def test_compare_versions_handles_empty(self):
        """Empty string is handled gracefully."""
        assert compare_versions("", "1.0.0") == 0
        assert compare_versions("1.0.0", "") == 0
        assert compare_versions("", "") == 0

    def test_compare_versions_non_semver(self):
        """Non-semver defaults to 0.0.0."""
        assert compare_versions("invalid", "1.0.0") == -1
        assert compare_versions("1.0.0", "invalid") == 1
        assert compare_versions("invalid", "not-a-version") == 0

    def test_compare_versions_major(self):
        """Major version comparison works."""
        assert compare_versions("2.0.0", "1.9.9") == 1
        assert compare_versions("1.9.9", "2.0.0") == -1

    def test_compare_versions_minor(self):
        """Minor version comparison works."""
        assert compare_versions("1.5.0", "1.4.9") == 1
        assert compare_versions("1.4.9", "1.5.0") == -1

    def test_compare_versions_patch(self):
        """Patch version comparison works."""
        assert compare_versions("1.0.5", "1.0.4") == 1
        assert compare_versions("1.0.4", "1.0.5") == -1


@pytest.mark.unit
class TestDeploymentLogic:
    """Tests for deployment decision logic."""

    def test_should_deploy_when_not_installed(self, temp_dir):
        """No existing install returns 'install'."""
        target_path = temp_dir / "skills" / "osx-test"
        target_manifest = temp_dir / "manifest.json"
        result = should_deploy(
            "osx-test", "1.0.0", target_path, target_manifest, "skills", False
        )
        assert result == "install"

    def test_should_deploy_when_newer_version(self, temp_dir):
        """Version comparison triggers upgrade."""
        target_path = temp_dir / "skills" / "osx-test"
        target_path.mkdir(parents=True)
        target_manifest = temp_dir / "manifest.toml"
        target_manifest.write_text(
            toml.dumps({"resources": {"skills": {"osx-test": {"version": "0.9.0"}}}})
        )
        result = should_deploy(
            "osx-test", "1.0.0", target_path, target_manifest, "skills", False
        )
        assert result == "upgrade"

    def test_should_skip_when_older_version(self, temp_dir):
        """Skip downgrade when installed version is newer."""
        target_path = temp_dir / "skills" / "osx-test"
        target_path.mkdir(parents=True)
        target_manifest = temp_dir / "manifest.toml"
        target_manifest.write_text(
            toml.dumps({"resources": {"skills": {"osx-test": {"version": "2.0.0"}}}})
        )
        result = should_deploy(
            "osx-test", "1.0.0", target_path, target_manifest, "skills", False
        )
        assert result == "skip"

    def test_should_deploy_when_force(self, temp_dir):
        """Force flag triggers update even if installed."""
        target_path = temp_dir / "skills" / "osx-test"
        target_path.mkdir(parents=True)
        target_manifest = temp_dir / "manifest.json"
        target_manifest.write_text(
            json.dumps({"resources": {"skills": {"osx-test": {"version": "1.0.0"}}}})
        )
        result = should_deploy(
            "osx-test", "1.0.0", target_path, target_manifest, "skills", True
        )
        assert result == "update"

    def test_get_resources_dir_returns_project_resources(self):
        """get_resources_dir returns the correct resources path."""
        resources = get_resources_dir()
        assert resources.name == "resources"
        assert resources.parent.name == "OpenSpec-extended"


@pytest.mark.unit
class TestPathResolution:
    """Tests for tool directory mapping."""

    def test_get_tool_dir_opencode(self):
        """opencode tool maps to .opencode."""
        assert get_tool_dir("opencode") == ".opencode"

    def test_get_tool_dir_claude(self):
        """claude tool maps to .claude."""
        assert get_tool_dir("claude") == ".claude"

    def test_get_tool_dir_invalid(self):
        """Invalid tool raises ValueError."""
        with pytest.raises(ValueError, match="Unknown tool"):
            get_tool_dir("invalid")


@pytest.mark.unit
class TestParseVersion:
    """Tests for parse_version function."""

    def test_parse_version_valid(self):
        """Valid semver is parsed correctly."""
        assert parse_version("1.2.3") == (1, 2, 3)
        assert parse_version("0.4.0") == (0, 4, 0)
        assert parse_version("10.20.30") == (10, 20, 30)

    def test_parse_version_invalid(self):
        """Invalid semver returns (0, 0, 0)."""
        assert parse_version("invalid") == (0, 0, 0)
        assert parse_version("1.2") == (0, 0, 0)
        assert parse_version("v1.0.0") == (0, 0, 0)


@pytest.mark.unit
class TestGetInstalledVersion:
    """Tests for get_installed_version function."""

    def test_returns_empty_when_no_manifest(self, temp_dir):
        """No manifest file returns empty string."""
        manifest = temp_dir / "manifest.toml"
        result = get_installed_version(manifest, "skills", "test")
        assert result == ""

    def test_returns_empty_when_no_resource(self, temp_dir):
        """Manifest without resource returns empty string."""
        manifest = temp_dir / "manifest.toml"
        manifest.write_text(toml.dumps({"resources": {}}))
        result = get_installed_version(manifest, "skills", "test")
        assert result == ""

    def test_returns_version_when_found(self, temp_dir):
        """Resource with version returns that version."""
        manifest = temp_dir / "manifest.toml"
        manifest.write_text(
            toml.dumps({"resources": {"skills": {"test": {"version": "1.2.3"}}}})
        )
        result = get_installed_version(manifest, "skills", "test")
        assert result == "1.2.3"

    def test_returns_empty_for_invalid_toml(self, temp_dir):
        """Invalid TOML returns empty string."""
        manifest = temp_dir / "manifest.toml"
        manifest.write_text("not valid toml [")
        result = get_installed_version(manifest, "skills", "test")
        assert result == ""


@pytest.mark.unit
class TestGetTargetPath:
    """Tests for get_target_path function."""

    def test_skills_target_path(self, temp_dir):
        """Skills deploy to skills/<name>."""
        target_dir = temp_dir / ".opencode"
        result = get_target_path("skills", target_dir, "osx-test")
        assert result == target_dir / "skills" / "osx-test"

    def test_commands_target_path(self, temp_dir):
        """Commands deploy to commands/<name>.md."""
        target_dir = temp_dir / ".opencode"
        commands_dir = target_dir / "commands"
        commands_dir.mkdir(parents=True)
        result = get_target_path("commands", target_dir, "osx-test")
        assert result == target_dir / "commands" / "osx-test.md"

    def test_agents_target_path(self, temp_dir):
        """Agents deploy to agents/<name>.md."""
        target_dir = temp_dir / ".opencode"
        result = get_target_path("agents", target_dir, "osx-test")
        assert result == target_dir / "agents" / "osx-test.md"

    def test_scripts_target_path(self, temp_dir):
        """Scripts deploy to scripts/<name>."""
        target_dir = temp_dir / ".opencode"
        result = get_target_path("scripts", target_dir, "test-script")
        assert result == target_dir / "scripts" / "test-script"

    def test_lib_target_path(self, temp_dir):
        """Lib scripts deploy to scripts/lib/<name>."""
        target_dir = temp_dir / ".opencode"
        result = get_target_path("lib", target_dir, "test-lib")
        assert result == target_dir / "scripts" / "lib" / "test-lib"
