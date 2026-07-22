#!/usr/bin/env python3
"""
E2E mechanism tests - no AI calls, safe to run anytime.
Tests CLI options and error handling.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.mechanism


PROJECT_ROOT = Path(__file__).parent.parent.parent
OPENCODE_SOURCE = PROJECT_ROOT / ".opencode"
RESOURCES_OPENCODE = PROJECT_ROOT / "resources" / "opencode"


@pytest.fixture
def e2e_repo(tmp_path):
    """Create temporary E2E repo with opencode installed."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "e2e@test.com"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "E2E Test"],
        cwd=tmp_path,
        check=True,
    )

    readme = tmp_path / "README.md"
    readme.write_text("# E2E Test Repo\n")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "Initial commit"], cwd=tmp_path, check=True
    )

    opencode_target = tmp_path / ".opencode"
    if OPENCODE_SOURCE.exists():
        shutil.copytree(OPENCODE_SOURCE, opencode_target)
    else:
        manifest = RESOURCES_OPENCODE / "manifest.toml"
        scripts_dir = opencode_target / "scripts"
        scripts_dir.mkdir(parents=True)
        (opencode_target / "manifest.toml").write_text(manifest.read_text())

    # Regardless of source, ensure stub skills + phase commands exist so the
    # orchestrator's preflight (Fix 5: always runs) can pass validate_skills
    # and validate_commands.
    skills_dir = opencode_target / "skills"
    for skill in (
        "osx-concepts",
        "osx-workflow",
        "osx-review-artifacts",
        "osx-modify-artifacts",
        "osx-review-test-compliance",
        "osx-maintain-ai-docs",
        "osc-apply-change",
        "osc-verify-change",
        "osc-sync-specs",
        "osc-archive-change",
    ):
        skill_path = skills_dir / skill / "SKILL.md"
        if not skill_path.exists():
            (skills_dir / skill).mkdir(parents=True, exist_ok=True)
            skill_path.write_text("# stub")

    commands_dir = opencode_target / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    for phase in range(7):
        cmd_file = commands_dir / f"osx-phase{phase}.md"
        if not cmd_file.exists():
            cmd_file.write_text("# stub")

    changes_dir = tmp_path / "openspec" / "changes"
    changes_dir.mkdir(parents=True, exist_ok=True)

    yield tmp_path


def run_osx_orchestrate(cwd, *args):
    """Run osx-orchestrate via python -m source and return (exit_code, stdout, stderr)."""
    cmd = [sys.executable, "-m", "source", "orchestrate"] + list(args)
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def setup_minimal_change(cwd, change_name):
    """Create a minimal change structure."""
    change_dir = cwd / "openspec" / "changes" / change_name
    specs_dir = change_dir / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    (change_dir / "proposal.md").write_text(
        """# Test Proposal

Minimal test change for E2E testing.

## Summary
Test change for validating osx-orchestrate.
"""
    )
    (change_dir / "design.md").write_text(
        """# Test Design

Minimal design document.
"""
    )
    (change_dir / "tasks.md").write_text(
        """# Tasks

- [ ] Complete test task
"""
    )
    (specs_dir / "spec.md").write_text(
        """# Specification

**SHALL** complete successfully.
"""
    )


class TestVersion:
    """Tests for --version option."""

    def test_version_not_available_on_orchestrate(self, e2e_repo):
        """orchestrate command doesn't have --version (it's a Typer limitation)."""
        exit_code, stdout, stderr = run_osx_orchestrate(e2e_repo, "--version")
        combined = stdout + stderr
        assert exit_code == 2, f"Expected exit 2, got {exit_code}. Output: {combined}"
        assert "No such option: --version" in combined


class TestHelp:
    """Tests for --help option."""

    def test_help_shows_usage_with_all_options(self, e2e_repo):
        """--help shows usage with all options."""
        exit_code, stdout, stderr = run_osx_orchestrate(e2e_repo, "--help")
        combined = stdout + stderr
        assert exit_code == 0, f"Expected exit 0, got {exit_code}. Output: {combined}"
        assert "Usage:" in combined, f"Expected 'Usage:' in output: {combined}"
        assert "--max-phase-iterations" in combined, (
            f"Expected '--max-phase-iterations' in output: {combined}"
        )
        assert "--timeout" in combined, f"Expected '--timeout' in output: {combined}"
        assert "--model" in combined, f"Expected '--model' in output: {combined}"
        assert "--verbose" in combined, f"Expected '--verbose' in output: {combined}"
        assert "--dry-run" in combined, f"Expected '--dry-run' in output: {combined}"
        assert "--force" in combined, f"Expected '--force' in output: {combined}"
        assert "--clean" in combined, f"Expected '--clean' in output: {combined}"
        assert "--from-phase" in combined, (
            f"Expected '--from-phase' in output: {combined}"
        )
        assert "--list" in combined, f"Expected '--list' in output: {combined}"
        assert "--schema" in combined, f"Expected '--schema' in output: {combined}"


class TestList:
    """Tests for --list option."""

    def test_list_shows_available_changes(self, e2e_repo):
        """--list shows available changes when used with a change name (Typer requires argument order)."""
        setup_minimal_change(e2e_repo, "test-change")
        setup_minimal_change(e2e_repo, "another-change")

        exit_code, stdout, stderr = run_osx_orchestrate(
            e2e_repo, "test-change", "--list"
        )
        combined = stdout + stderr
        assert exit_code == 0, f"Expected exit 0, got {exit_code}. Output: {combined}"
        assert "test-change" in combined or "another-change" in combined, (
            f"Expected at least one change name in output: {combined}"
        )


class TestDryRun:
    """Tests for --dry-run option."""

    def test_dry_run_shows_phases_without_execution(self, e2e_repo):
        """--dry-run shows phases without execution."""
        setup_minimal_change(e2e_repo, "dry-test")

        exit_code, stdout, stderr = run_osx_orchestrate(
            e2e_repo, "dry-test", "--dry-run", "--max-phase-iterations=1"
        )
        combined = stdout + stderr
        assert "[DRY RUN]" in combined, f"Expected '[DRY RUN]' in output: {combined}"


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_change_id_exits_with_error(self, e2e_repo):
        """Invalid change ID exits with error."""
        exit_code, stdout, stderr = run_osx_orchestrate(e2e_repo, "nonexistent-change")
        assert exit_code == 1, (
            f"Expected exit 1, got {exit_code}. Output: {stdout + stderr}"
        )
        combined = stdout + stderr
        assert "not found" in combined or "Error" in combined or "Change" in combined, (
            f"Expected error message in output: {combined}"
        )

    def test_invalid_option_exits_with_error(self, e2e_repo):
        """Invalid option exits with error (Typer exits with code 2 for invalid options)."""
        exit_code, stdout, stderr = run_osx_orchestrate(e2e_repo, "--invalid-option")
        assert exit_code == 2, (
            f"Expected exit 2, got {exit_code}. Output: {stdout + stderr}"
        )
        combined = stdout + stderr
        assert "No such option" in combined or "invalid" in combined, (
            f"Expected error message in output: {combined}"
        )
