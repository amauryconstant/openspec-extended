#!/usr/bin/env python3
"""
Integration tests for full change lifecycle.
"""

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from source.lib import osx


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


def setup_archive(env_dir, change_name, timestamp="2024-01-15"):
    """Setup archive directory with timestamped change."""
    archive_dir = env_dir / "openspec" / "changes" / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    archived = archive_dir / f"{timestamp}-{change_name}"
    archived.mkdir(parents=True, exist_ok=True)
    (archived / "specs").mkdir(exist_ok=True)

    (archived / "proposal.md").write_text("# Proposal")
    (archived / "design.md").write_text("# Design")
    (archived / "tasks.md").write_text("# Tasks")
    (archived / "specs" / "spec.md").write_text("# Spec")

    return archived


def invoke(args):
    """Invoke osx CLI with given args using CliRunner."""
    runner = CliRunner()
    return runner.invoke(osx.app, args)


@pytest.mark.integration
class TestChangeLifecycle:
    """Tests for full change lifecycle."""

    def test_create_change_advance_phases_complete(self, test_env, monkeypatch):
        """Create change -> advance phases -> complete."""
        setup_change(
            test_env,
            "lifecycle-test",
            '{"phase":"PHASE0","iteration":0,"phase_complete":false}',
        )

        monkeypatch.chdir(test_env)

        invoke(["phase", "current", "lifecycle-test"])

        invoke(["state", "complete", "lifecycle-test"])

        invoke(["phase", "advance", "lifecycle-test"])
        state = json.loads(
            (test_env / "openspec/changes/lifecycle-test/state.json").read_text()
        )
        assert state["phase"] == "PHASE1"

        invoke(["state", "complete", "lifecycle-test"])
        invoke(["phase", "advance", "lifecycle-test"])
        state = json.loads(
            (test_env / "openspec/changes/lifecycle-test/state.json").read_text()
        )
        assert state["phase"] == "PHASE2"

        invoke(["state", "complete", "lifecycle-test"])
        invoke(["phase", "advance", "lifecycle-test"])
        state = json.loads(
            (test_env / "openspec/changes/lifecycle-test/state.json").read_text()
        )
        assert state["phase"] == "PHASE3"

        invoke(["state", "complete", "lifecycle-test"])
        invoke(["phase", "advance", "lifecycle-test"])
        state = json.loads(
            (test_env / "openspec/changes/lifecycle-test/state.json").read_text()
        )
        assert state["phase"] == "PHASE4"

        invoke(["state", "complete", "lifecycle-test"])
        invoke(["phase", "advance", "lifecycle-test"])
        state = json.loads(
            (test_env / "openspec/changes/lifecycle-test/state.json").read_text()
        )
        assert state["phase"] == "PHASE5"

        invoke(["state", "complete", "lifecycle-test"])
        invoke(["phase", "advance", "lifecycle-test"])
        state = json.loads(
            (test_env / "openspec/changes/lifecycle-test/state.json").read_text()
        )
        assert state["phase"] == "PHASE6"

        invoke(["state", "complete", "lifecycle-test"])
        invoke(["phase", "advance", "lifecycle-test"])
        state = json.loads(
            (test_env / "openspec/changes/lifecycle-test/state.json").read_text()
        )
        assert state["phase"] == "COMPLETE"

        invoke(["complete", "set", "lifecycle-test", "COMPLETE"])

    def test_context_aggregation_across_full_lifecycle(self, test_env, monkeypatch):
        """Context aggregation across full lifecycle."""
        setup_change(
            test_env,
            "lifecycle-test",
            '{"phase":"PHASE1","iteration":2,"phase_complete":false}',
        )

        monkeypatch.chdir(test_env)

        invoke(
            [
                "iterations",
                "append",
                "lifecycle-test",
                "--phase",
                "PHASE0",
                "--iteration",
                "1",
                "--extra",
                '{"notes":"review"}',
            ]
        )

        invoke(
            [
                "iterations",
                "append",
                "lifecycle-test",
                "--phase",
                "PHASE1",
                "--iteration",
                "1",
                "--extra",
                '{"notes":"implement"}',
            ]
        )

        invoke(["ctx", "get", "lifecycle-test"])

    def test_archive_workflow_creates_archive_directory(self, test_env, monkeypatch):
        """Archive workflow creates archive directory."""
        setup_change(
            test_env,
            "lifecycle-test",
            '{"phase":"PHASE6","iteration":1,"phase_complete":true}',
        )

        monkeypatch.chdir(test_env)
        invoke(["complete", "set", "lifecycle-test", "COMPLETE"])

        setup_archive(test_env, "lifecycle-test", "2024-01-15")

        archive_dir = test_env / "openspec" / "changes" / "archive"
        assert archive_dir.is_dir()

        archived = archive_dir / "2024-01-15-lifecycle-test"
        assert archived.is_dir()

    def test_multiple_changes_can_coexist_independently(self, test_env, monkeypatch):
        """Multiple changes can coexist independently."""
        setup_change(test_env, "change-alpha")
        setup_change(test_env, "change-beta")

        setup_change(test_env, "change-alpha", '{"phase":"PHASE1","iteration":1}')
        setup_change(test_env, "change-beta", '{"phase":"PHASE3","iteration":2}')

        monkeypatch.chdir(test_env)

        invoke(["phase", "current", "change-alpha"])

        invoke(["phase", "current", "change-beta"])

        invoke(["phase", "advance", "change-alpha"])

        invoke(["phase", "current", "change-beta"])
