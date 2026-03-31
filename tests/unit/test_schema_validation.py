#!/usr/bin/env python3
"""
Schema validation tests for osx CLI tool.
Ensures consistent JSON output format across all osx subcommands.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).parent.parent.parent


@pytest.fixture
def test_env(tmp_path):
    """Create a test environment with git repo and osx tool."""
    env_dir = tmp_path / "test_env"
    env_dir.mkdir()

    subprocess.run(["git", "init", "-q"], cwd=env_dir, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=env_dir,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=env_dir,
        check=True,
    )

    readme = env_dir / "README.md"
    readme.write_text("# Test repo")
    subprocess.run(["git", "add", "README.md"], cwd=env_dir, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "Initial commit"], cwd=env_dir, check=True
    )

    (env_dir / "openspec" / "changes").mkdir(parents=True)

    return env_dir


def run_osx(env_dir, *args):
    """Run osx CLI tool via Python module and return result."""
    result = subprocess.run(
        [sys.executable, "-m", "source.lib.osx"] + list(args),
        cwd=env_dir,
        capture_output=True,
        text=True,
    )
    stderr_lines = [
        line
        for line in result.stderr.splitlines()
        if not line.startswith("<frozen runpy>")
    ]
    return result.returncode, result.stdout, "\n".join(stderr_lines)


def setup_change(env_dir, change_name="test-change"):
    """Create a minimal change directory."""
    change_path = env_dir / "openspec" / "changes" / change_name
    specs_dir = change_path / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    (change_path / "proposal.md").write_text("# Proposal")
    (change_path / "design.md").write_text("# Design")
    (change_path / "tasks.md").write_text("# Tasks")
    (specs_dir / "spec.md").write_text("# Spec")

    return change_path


def setup_change_with_state(env_dir, change_name, state_json):
    """Create a change with pre-existing state.json."""
    change_dir = setup_change(env_dir, change_name)
    (change_dir / "state.json").write_text(state_json)
    return change_dir


def setup_change_with_iterations(env_dir, change_name, iterations_json):
    """Create a change with pre-existing iterations.json."""
    change_dir = setup_change(env_dir, change_name)
    (change_dir / "iterations.json").write_text(iterations_json)
    return change_dir


def setup_change_with_decision_log(env_dir, change_name, log_json):
    """Create a change with pre-existing decision-log.json."""
    change_dir = setup_change(env_dir, change_name)
    (change_dir / "decision-log.json").write_text(log_json)
    return change_dir


def setup_change_with_complete(env_dir, change_name, complete_json):
    """Create a change with pre-existing complete.json."""
    change_dir = setup_change(env_dir, change_name)
    (change_dir / "complete.json").write_text(complete_json)
    return change_dir


def setup_baseline(
    env_dir, commit="abc123", branch="main", timestamp="2024-01-15T10:00:00Z"
):
    """Create a baseline file."""
    baseline = {
        "commit": commit,
        "branch": branch,
        "timestamp": timestamp,
    }
    (env_dir / ".openspec-baseline.json").write_text(json.dumps(baseline))


pytestmark = pytest.mark.unit


class TestErrorSchema:
    """Tests for error schema consistency across osx commands."""

    def test_osc_state_error_format(self, test_env):
        """osc-state error format has error and message fields."""
        code, stdout, stderr = run_osx(test_env, "state", "get", "nonexistent-change")
        assert code == 1
        result = json.loads(stderr)
        assert "error" in result
        assert "message" in result

    def test_osc_iterations_error_format(self, test_env):
        """osc-iterations error format has error and message fields."""
        code, stdout, stderr = run_osx(
            test_env, "iterations", "get", "nonexistent-change"
        )
        assert code == 1
        result = json.loads(stderr)
        assert "error" in result
        assert "message" in result

    def test_osc_log_error_format(self, test_env):
        """osc-log error format has error and message fields."""
        code, stdout, stderr = run_osx(test_env, "log", "get", "nonexistent-change")
        assert code == 1
        result = json.loads(stderr)
        assert "error" in result
        assert "message" in result

    def test_osc_git_returns_valid_without_git_repo(self, test_env):
        """osc-git returns valid output even without git repo."""
        change_dir = setup_change(test_env, "test-change")
        (test_env / ".git").rename(test_env / ".git_bak")

        code, stdout, stderr = run_osx(test_env, "git", "get", "test-change")
        assert code == 0
        result = json.loads(stdout)
        assert result["branch"] == "unknown"

        (test_env / ".git_bak").rename(test_env / ".git")

    def test_osc_ctx_error_format(self, test_env):
        """osc-ctx error format has error and message fields."""
        code, stdout, stderr = run_osx(test_env, "ctx", "get", "nonexistent")
        assert code == 1
        result = json.loads(stderr)
        assert "error" in result
        assert "message" in result

    def test_osc_validate_error_format(self, test_env):
        """osc-validate error format returns valid=false, not error/message."""
        code, stdout, stderr = run_osx(
            test_env, "validate", "change-dir", "nonexistent-change"
        )
        assert code == 1
        result = json.loads(stdout)
        assert result["valid"] is False

    def test_osc_phase_error_format(self, test_env):
        """osc-phase error format has error and message fields."""
        code, stdout, stderr = run_osx(
            test_env, "phase", "current", "nonexistent-change"
        )
        assert code == 1
        result = json.loads(stderr)
        assert "error" in result
        assert "message" in result

    def test_osc_baseline_error_format(self, test_env):
        """osc-baseline error format has error and message fields."""
        code, stdout, stderr = run_osx(test_env, "baseline", "get")
        assert code == 1
        result = json.loads(stderr)
        assert "error" in result
        assert "message" in result

    def test_osc_complete_error_format(self, test_env):
        """osc-complete error format has error and message fields."""
        code, stdout, stderr = run_osx(
            test_env, "complete", "get", "nonexistent-change"
        )
        assert code == 1
        result = json.loads(stderr)
        assert "error" in result
        assert "message" in result


class TestSuccessSchema:
    """Tests for success schema consistency across osx commands."""

    def test_osc_state_get_output(self, test_env):
        """osc-state get output has required fields."""
        setup_change_with_state(
            test_env,
            "test-change",
            '{"phase":"PHASE1","iteration":2,"phase_complete":false}',
        )
        code, stdout, stderr = run_osx(test_env, "state", "get", "test-change")
        assert code == 0
        result = json.loads(stdout)
        assert "phase" in result
        assert "iteration" in result
        assert "phase_complete" in result
        assert "change" in result

    def test_osc_iterations_get_output(self, test_env):
        """osc-iterations get output has required fields."""
        setup_change_with_iterations(test_env, "test-change", '[{"iteration":1}]')
        code, stdout, stderr = run_osx(test_env, "iterations", "get", "test-change")
        assert code == 0
        result = json.loads(stdout)
        assert "count" in result
        assert "iterations" in result

    def test_osc_log_get_output(self, test_env):
        """osc-log get output has required fields."""
        setup_change_with_decision_log(test_env, "test-change", '[{"entry":1}]')
        code, stdout, stderr = run_osx(test_env, "log", "get", "test-change")
        assert code == 0
        result = json.loads(stdout)
        assert "count" in result
        assert "entries" in result

    def test_osc_git_output(self, test_env):
        """osc-git output has required fields."""
        setup_change(test_env, "test-change")
        code, stdout, stderr = run_osx(test_env, "git", "get", "test-change")
        assert code == 0
        result = json.loads(stdout)
        assert "modified" in result
        assert "added" in result
        assert "untracked" in result
        assert "clean" in result
        assert "branch" in result

    def test_osc_ctx_output(self, test_env):
        """osc-ctx output has required fields."""
        setup_change(test_env, "test-change")
        code, stdout, stderr = run_osx(test_env, "ctx", "get", "test-change")
        assert code == 0
        result = json.loads(stdout)
        assert "change" in result
        assert "state" in result
        assert "git" in result
        assert "artifacts" in result
        assert "history" in result

    def test_osc_validate_valid_output(self, test_env):
        """osc-validate output has valid field."""
        setup_change(test_env, "test-change")
        code, stdout, stderr = run_osx(
            test_env, "validate", "change-dir", "test-change"
        )
        assert code == 0
        result = json.loads(stdout)
        assert "valid" in result

    def test_osc_validate_invalid_output(self, test_env):
        """osc-validate invalid output has errors array."""
        change_dir = test_env / "openspec" / "changes" / "test-change"
        change_dir.mkdir(parents=True, exist_ok=True)

        code, stdout, stderr = run_osx(
            test_env, "validate", "change-dir", "test-change"
        )
        assert code == 1
        result = json.loads(stdout)
        assert "valid" in result
        assert "errors" in result

    def test_osc_phase_current_output(self, test_env):
        """osc-phase current output has required fields."""
        setup_change_with_state(
            test_env, "test-change", '{"phase":"PHASE1","iteration":2}'
        )
        code, stdout, stderr = run_osx(test_env, "phase", "current", "test-change")
        assert code == 0
        result = json.loads(stdout)
        assert "phase" in result
        assert "next" in result
        assert "iteration" in result

    def test_osc_phase_advance_output(self, test_env):
        """osc-phase advance output has required fields."""
        setup_change_with_state(
            test_env, "test-change", '{"phase":"PHASE0","iteration":1}'
        )
        code, stdout, stderr = run_osx(test_env, "phase", "advance", "test-change")
        assert code == 0
        result = json.loads(stdout)
        assert "phase" in result
        assert "previous" in result
        assert "next" in result
        assert "iteration" in result

    def test_osc_baseline_get_output(self, test_env):
        """osc-baseline get output has required fields."""
        setup_baseline(test_env, "abc123", "main", "2024-01-15T10:00:00Z")
        code, stdout, stderr = run_osx(test_env, "baseline", "get")
        assert code == 0
        result = json.loads(stdout)
        assert "commit" in result
        assert "branch" in result
        assert "timestamp" in result

    def test_osc_baseline_record_output(self, test_env):
        """osc-baseline record output has required fields."""
        code, stdout, stderr = run_osx(test_env, "baseline", "record")
        assert code == 0
        result = json.loads(stdout)
        assert "commit" in result
        assert "branch" in result
        assert "timestamp" in result

    def test_osc_complete_get_output(self, test_env):
        """osc-complete get output has required fields."""
        setup_change_with_complete(
            test_env, "test-change", '{"status":"COMPLETE","with_blocker":false}'
        )
        code, stdout, stderr = run_osx(test_env, "complete", "get", "test-change")
        assert code == 0
        result = json.loads(stdout)
        assert "status" in result
        assert "with_blocker" in result

    def test_osc_complete_check_output(self, test_env):
        """osc-complete check output has exists field."""
        setup_change_with_complete(test_env, "test-change", '{"status":"COMPLETE"}')
        code, stdout, stderr = run_osx(test_env, "complete", "check", "test-change")
        assert code == 0
        result = json.loads(stdout)
        assert "exists" in result

    def test_osc_complete_set_output(self, test_env):
        """osc-complete set output has required fields."""
        setup_change(test_env, "test-change")
        code, stdout, stderr = run_osx(test_env, "complete", "set", "test-change")
        assert code == 0
        result = json.loads(stdout)
        assert "status" in result
        assert "with_blocker" in result
