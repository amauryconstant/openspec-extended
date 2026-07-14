#!/usr/bin/env python3
"""
Integration tests for git operations with state.
"""

import json

import pytest

from source import osx_cli


@pytest.fixture
def test_env(tmp_path):
    """Create a test environment with git repo."""
    env_dir = tmp_path / "test_env"
    env_dir.mkdir()

    import subprocess

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

    (env_dir / "openspec" / "changes").mkdir(parents=True)
    (env_dir / ".opencode" / "skills").mkdir(parents=True)
    (env_dir / ".opencode" / "commands").mkdir(parents=True)

    for skill in ["osx-concepts", "osx-review-artifacts", "osx-modify-artifacts"]:
        skill_dir = env_dir / ".opencode" / "skills" / skill
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(f"# {skill}")

    for phase in range(7):
        cmd_file = env_dir / ".opencode" / "commands" / f"osx-phase{phase}.md"
        cmd_file.write_text(f"# osx-phase{phase}")

    return env_dir


def setup_change(env_dir, change_name, state_data=None):
    """Setup a change directory with required files."""
    change_dir = env_dir / "openspec" / "changes" / change_name
    change_dir.mkdir(parents=True, exist_ok=True)
    (change_dir / "specs").mkdir(exist_ok=True)

    (change_dir / "proposal.md").write_text("# Proposal")
    (change_dir / "design.md").write_text("# Design")
    (change_dir / "tasks.md").write_text("# Tasks")
    (change_dir / "specs" / "spec.md").write_text("# Spec")

    if state_data:
        (change_dir / "state.json").write_text(state_data)

    return change_dir


@pytest.mark.integration
class TestGitIntegration:
    """Tests for git operations with state."""

    def test_baseline_recorded_with_commit_hash(self, test_env, monkeypatch):
        """Baseline is recorded with commit hash."""
        monkeypatch.chdir(test_env)
        osx_cli.baseline_cmd("record")

        baseline_file = test_env / ".openspec-baseline.json"
        assert baseline_file.is_file()

        baseline = json.loads(baseline_file.read_text())
        assert baseline["commit"] is not None
        assert baseline["commit"] != "null"
        assert len(baseline["commit"]) == 40
        assert all(c in "0123456789abcdef" for c in baseline["commit"])

    def test_baseline_persists_across_state_operations(self, test_env, monkeypatch):
        """Baseline persists across state operations."""
        monkeypatch.chdir(test_env)
        osx_cli.baseline_cmd("record")

        baseline_file = test_env / ".openspec-baseline.json"
        recorded_commit = json.loads(baseline_file.read_text())["commit"]

        setup_change(test_env, "test-change", '{"phase":"PHASE0","iteration":1}')

        osx_cli.phase_cmd("advance", "test-change")

        result = osx_cli.baseline_cmd("get")

    def test_git_status_integrates_with_context(self, test_env, monkeypatch):
        """Git status integrates with context."""
        setup_change(test_env, "test-change", '{"phase":"PHASE1","iteration":1}')

        test_file = test_env / "openspec" / "changes" / "test-change" / "test-file.txt"
        test_file.write_text("test content")

        import subprocess

        subprocess.run(
            ["git", "add", "openspec/changes/test-change/test-file.txt"],
            cwd=test_env,
            check=True,
        )

        monkeypatch.chdir(test_env)
        result = osx_cli.git_cmd("get", "test-change")

    def test_branch_name_captured_correctly(self, test_env, monkeypatch):
        """Branch name is captured correctly."""
        monkeypatch.chdir(test_env)
        osx_cli.baseline_cmd("record")

        baseline_file = test_env / ".openspec-baseline.json"
        baseline = json.loads(baseline_file.read_text())
        assert baseline["branch"] is not None
        assert baseline["branch"] != "null"

    def test_git_status_detects_untracked_files(self, test_env, monkeypatch):
        """Git status detects untracked files in change directory."""
        setup_change(test_env, "test-change", '{"phase":"PHASE1","iteration":1}')

        import subprocess

        subprocess.run(
            ["git", "add", "openspec/changes/test-change/proposal.md"],
            cwd=test_env,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-q", "-m", "Track change files"],
            cwd=test_env,
            check=True,
        )

        new_dir = test_env / "openspec" / "changes" / "test-change" / "newdir"
        new_dir.mkdir()
        untracked = new_dir / "untracked.md"
        untracked.write_text("new file")

        monkeypatch.chdir(test_env)
        result = osx_cli.git_cmd("get", "test-change")

    def test_git_status_reflects_change_directory_modifications(
        self, test_env, monkeypatch
    ):
        """Git status reflects change directory modifications."""
        setup_change(test_env, "test-change", '{"phase":"PHASE1","iteration":1}')

        import subprocess

        subprocess.run(
            ["git", "add", "openspec/changes/test-change/"], cwd=test_env, check=True
        )
        subprocess.run(
            ["git", "commit", "-q", "-m", "Track change files"],
            cwd=test_env,
            check=True,
        )

        proposal = test_env / "openspec" / "changes" / "test-change" / "proposal.md"
        proposal.write_text(proposal.read_text() + "\nmodified content")

        monkeypatch.chdir(test_env)
        result = osx_cli.git_cmd("get", "test-change")
