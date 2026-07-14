#!/usr/bin/env python3
"""
Integration tests for phase workflow.
"""

import json

import pytest
from typer.testing import CliRunner



@pytest.fixture
def test_env(tmp_path):
    """Create a test environment with git repo and change structure."""
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


def get_json_value(json_str, key):
    """Extract value from JSON string using key path like '.phase'."""
    try:
        data = json.loads(json_str)
        keys = key.lstrip(".").split(".")
        for k in keys:
            data = data[k]
        return data
    except (json.JSONDecodeError, KeyError, TypeError):
        return None


def invoke(args):
    """Invoke osx CLI with given args using CliRunner."""
    runner = CliRunner()
    from source.osx_cli import osx_app
    return runner.invoke(osx_app, args)


@pytest.mark.integration
class TestPhaseWorkflow:
    """Tests for phase workflow operations."""

    def test_advances_from_phase0_to_phase1(self, test_env, monkeypatch):
        """Advances from PHASE0 to PHASE1 with proper state updates."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE0","iteration":1,"phase_complete":true}',
        )

        monkeypatch.chdir(test_env)
        invoke(["phase", "advance", "test-change"])

        state_file = test_env / "openspec" / "changes" / "test-change" / "state.json"
        state = json.loads(state_file.read_text())
        assert state["phase"] == "PHASE1"
        assert state["iteration"] == 1
        assert state["phase_complete"] == False

    def test_advances_through_multiple_phases(self, test_env, monkeypatch):
        """Advances through multiple phases (0->1->2->3)."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE0","iteration":1,"phase_complete":true}',
        )

        monkeypatch.chdir(test_env)

        invoke(["phase", "advance", "test-change"])
        state = json.loads(
            (test_env / "openspec/changes/test-change/state.json").read_text()
        )
        assert state["phase"] == "PHASE1"

        invoke(["state", "complete", "test-change"])

        invoke(["phase", "advance", "test-change"])
        state = json.loads(
            (test_env / "openspec/changes/test-change/state.json").read_text()
        )
        assert state["phase"] == "PHASE2"

        invoke(["state", "complete", "test-change"])

        invoke(["phase", "advance", "test-change"])
        state = json.loads(
            (test_env / "openspec/changes/test-change/state.json").read_text()
        )
        assert state["phase"] == "PHASE3"

    def test_state_file_persists_between_phase_advances(self, test_env, monkeypatch):
        """State file persists correctly between phase advances."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE0","iteration":5,"phase_complete":true}',
        )

        monkeypatch.chdir(test_env)
        invoke(["phase", "advance", "test-change"])

        state_file = test_env / "openspec" / "changes" / "test-change" / "state.json"
        assert state_file.is_file()

        state = json.loads(state_file.read_text())
        assert state["phase"] == "PHASE1"
        assert state["iteration"] == 1

    def test_iterations_recorded_during_phase_transitions(self, test_env, monkeypatch):
        """Iterations are recorded during phase transitions."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE0","iteration":1,"phase_complete":true}',
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
                '{"action":"initial"}',
            ]
        )

        invoke(["phase", "advance", "test-change"])

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
                '{"action":"started"}',
            ]
        )

        invoke(["iterations", "get", "test-change"])

    def test_phase_names_correct_for_each_phase_number(self, test_env, monkeypatch):
        """Phase names are correct for each phase number."""
        setup_change(test_env, "test-change", '{"phase":"PHASE0","iteration":0}')

        monkeypatch.chdir(test_env)

        expected_next = {
            "PHASE0": "PHASE1",
            "PHASE1": "PHASE2",
            "PHASE2": "PHASE3",
            "PHASE3": "PHASE4",
            "PHASE4": "PHASE5",
            "PHASE5": "PHASE6",
            "PHASE6": "COMPLETE",
        }

        for current, expected in expected_next.items():
            if current != "PHASE0":
                invoke(["state", "set-phase", "test-change", current])

            result = invoke(["phase", "next", "test-change"])

    def test_advance_resets_iteration_to_1(self, test_env, monkeypatch):
        """Advance resets iteration to 1."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE1","iteration":5,"phase_complete":true}',
        )

        monkeypatch.chdir(test_env)
        invoke(["phase", "advance", "test-change"])

        state = json.loads(
            (test_env / "openspec/changes/test-change/state.json").read_text()
        )
        assert state["iteration"] == 1

    def test_advance_sets_phase_complete_to_false(self, test_env, monkeypatch):
        """Advance sets phase_complete to false."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE0","iteration":1,"phase_complete":true}',
        )

        monkeypatch.chdir(test_env)
        invoke(["phase", "advance", "test-change"])

        state = json.loads(
            (test_env / "openspec/changes/test-change/state.json").read_text()
        )
        assert state["phase_complete"] == False

    def test_complete_action_integrates_with_phase_workflow(
        self, test_env, monkeypatch
    ):
        """Complete action integrates with phase workflow."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE1","iteration":2,"phase_complete":false}',
        )

        monkeypatch.chdir(test_env)
        invoke(["state", "complete", "test-change"])

        result = invoke(["phase", "current", "test-change"])

    def test_advance_to_complete_from_phase6(self, test_env, monkeypatch):
        """Advance to COMPLETE from PHASE6."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE6","iteration":1,"phase_complete":true}',
        )

        monkeypatch.chdir(test_env)
        invoke(["phase", "advance", "test-change"])


@pytest.mark.integration
class TestPhaseTransition:
    """Tests for phase transition integration - bug regression tests."""

    def test_full_cycle_without_explicit_transitions(self, test_env, monkeypatch):
        """Full cycle without explicit transitions (bug regression test)."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE0","iteration":3,"phase_complete":true}',
        )

        monkeypatch.chdir(test_env)
        invoke(["phase", "advance", "test-change"])

        state = json.loads(
            (test_env / "openspec/changes/test-change/state.json").read_text()
        )
        assert state["phase"] == "PHASE1"
        assert state["iteration"] == 1
        assert state["phase_complete"] == False

    def test_explicit_transition_overrides_normal_advance(self, test_env, monkeypatch):
        """Explicit transition overrides normal advance."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE2","iteration":1,"phase_complete":true,"transition":{"target":"PHASE1","reason":"implementation_incorrect"}}',
        )

        state_file = test_env / "openspec" / "changes" / "test-change" / "state.json"
        state = json.loads(state_file.read_text())
        assert state["transition"]["target"] == "PHASE1"

        monkeypatch.chdir(test_env)
        invoke(["state", "clear-transition", "test-change"])

        invoke(["phase", "advance", "test-change"])
        state = json.loads(
            (test_env / "openspec/changes/test-change/state.json").read_text()
        )
        assert state["phase"] == "PHASE3"

    def test_transition_with_details_preserves_context(self, test_env, monkeypatch):
        """Transition with details preserves context."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE2","iteration":1,"phase_complete":true,"transition":{"target":"PHASE1","reason":"artifacts_modified","details":"Spec requirement 3.2 updated"}}',
        )

        state_file = test_env / "openspec" / "changes" / "test-change" / "state.json"
        state = json.loads(state_file.read_text())
        assert state["transition"]["reason"] == "artifacts_modified"
        assert state["transition"]["details"] == "Spec requirement 3.2 updated"

    def test_multiple_phase_advances_without_transitions(self, test_env, monkeypatch):
        """Multiple phase advances without transitions."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE0","iteration":1,"phase_complete":true}',
        )

        monkeypatch.chdir(test_env)
        invoke(["phase", "advance", "test-change"])

        invoke(["state", "complete", "test-change"])

        invoke(["phase", "advance", "test-change"])

        state = json.loads(
            (test_env / "openspec/changes/test-change/state.json").read_text()
        )
        assert state["phase"] == "PHASE2"
        assert state["phase_complete"] == False

    def test_backward_transition_from_phase2_to_phase1(self, test_env, monkeypatch):
        """Backward transition from PHASE2 to PHASE1."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE2","iteration":1,"phase_complete":true,"transition":{"target":"PHASE1","reason":"implementation_incorrect"}}',
        )

        state_file = test_env / "openspec" / "changes" / "test-change" / "state.json"
        state = json.loads(state_file.read_text())
        assert state["transition"]["target"] == "PHASE1"
        assert state["transition"]["reason"] == "implementation_incorrect"

        monkeypatch.chdir(test_env)
        invoke(["state", "clear-transition", "test-change"])
        invoke(["state", "set-phase", "test-change", "PHASE1"])

        state = json.loads(
            (test_env / "openspec/changes/test-change/state.json").read_text()
        )
        assert state["phase"] == "PHASE1"

    def test_artifacts_modified_triggers_reimplementation(self, test_env, monkeypatch):
        """Artifacts_modified triggers re-implementation."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE2","iteration":1,"phase_complete":true,"transition":{"target":"PHASE1","reason":"artifacts_modified","details":"ValidationPipeline spec updated"}}',
        )

        state_file = test_env / "openspec" / "changes" / "test-change" / "state.json"
        state = json.loads(state_file.read_text())
        assert state["transition"]["reason"] == "artifacts_modified"
        assert state["transition"]["details"] == "ValidationPipeline spec updated"
