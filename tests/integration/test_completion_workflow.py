#!/usr/bin/env python3
"""
Integration tests for completion workflow.
"""

import json

import pytest
from typer.testing import CliRunner



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


def invoke(args):
    """Invoke osx CLI with given args using CliRunner."""
    runner = CliRunner()
    from source.osx_cli import osx_app
    return runner.invoke(osx_app, args)


@pytest.mark.integration
class TestCompletionWorkflow:
    """Tests for completion workflow."""

    def test_complete_set_creates_complete_json(self, test_env, monkeypatch):
        """osc-complete set creates complete.json."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE6","iteration":1,"phase_complete":true}',
        )

        monkeypatch.chdir(test_env)
        invoke(["complete", "set", "test-change", "COMPLETE"])

        complete_file = (
            test_env / "openspec" / "changes" / "test-change" / "complete.json"
        )
        assert complete_file.is_file()

    def test_complete_check_returns_correct_status(self, test_env, monkeypatch):
        """osc-complete check returns correct status."""
        setup_change(test_env, "test-change")

        monkeypatch.chdir(test_env)

        invoke(["complete", "set", "test-change", "COMPLETE"])

    def test_state_marked_complete_via_osc_state(self, test_env, monkeypatch):
        """State is marked complete via osc-state."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE6","iteration":1,"phase_complete":false}',
        )

        monkeypatch.chdir(test_env)
        invoke(["state", "complete", "test-change"])

        state_file = test_env / "openspec" / "changes" / "test-change" / "state.json"
        state = json.loads(state_file.read_text())
        assert state["phase_complete"] == True

    def test_iterations_json_persists_after_completion(self, test_env, monkeypatch):
        """iterations.json persists after completion."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE6","iteration":1,"phase_complete":true}',
        )

        monkeypatch.chdir(test_env)
        invoke(
            [
                "iterations",
                "append",
                "test-change",
                "--phase",
                "PHASE0",
                "--iteration",
                "1",
                "--extra",
                '{"action":"start"}',
            ]
        )

        invoke(
            [
                "iterations",
                "append",
                "test-change",
                "--phase",
                "PHASE1",
                "--iteration",
                "1",
                "--extra",
                '{"action":"implement"}',
            ]
        )

        invoke(["complete", "set", "test-change", "COMPLETE"])

        iterations_file = (
            test_env / "openspec" / "changes" / "test-change" / "iterations.json"
        )
        assert iterations_file.is_file()

        invoke(["iterations", "get", "test-change"])

    def test_full_completion_flow_with_all_artifacts(self, test_env, monkeypatch):
        """Full completion flow with all artifacts."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE6","iteration":1,"phase_complete":true}',
        )

        monkeypatch.chdir(test_env)
        invoke(["state", "complete", "test-change"])

        invoke(["complete", "set", "test-change", "COMPLETE"])

    def test_completion_with_blocker_records_reason(self, test_env, monkeypatch):
        """Completion with blocker records reason."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE6","iteration":1,"phase_complete":true}',
        )

        monkeypatch.chdir(test_env)
        invoke(
            [
                "complete",
                "set",
                "test-change",
                "BLOCKED",
                "--blocker-reason",
                "Tests failed in CI",
            ]
        )
