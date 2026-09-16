#!/usr/bin/env python3
"""
Integration tests for phase workflow.
"""

import json
from pathlib import Path

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

    for skill in ["osx-concepts", "osx-review-artifacts"]:
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


@pytest.mark.integration
class TestPhase0RoutesPending:
    """Regression sentinel for C3 (PHASE0 routes without completing).

    PHASE0 is read-only and can only route the user to other commands
    (``/opsx:update``). The engine must halt cleanly so the
    user has time to run the routed commands. Without ``routes_pending`` the
    engine would loop PHASE0 until the iteration cap exhausts.
    """

    def _state_file(self, test_env) -> Path:
        return test_env / "openspec" / "changes" / "test-change" / "state.json"

    def _read_state(self, test_env) -> dict:
        return json.loads(self._state_file(test_env).read_text())

    def test_set_routes_writes_routes_pending(self, test_env, monkeypatch):
        """`osx state set-routes --routes …` writes routes_pending to state.json."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE0","iteration":1,"phase_complete":false}',
        )
        monkeypatch.chdir(test_env)
        result = invoke(
            [
                "state",
                "set-routes",
                "test-change",
                "--routes",
                "/opsx:update",
            ]
        )
        assert result.exit_code == 0, result.stdout
        payload = json.loads(result.stdout.strip())
        assert payload["routes_pending"] == ["/opsx:update"]
        assert self._read_state(test_env)["routes_pending"] == ["/opsx:update"]

    def test_set_routes_replaces_previous_routes(self, test_env, monkeypatch):
        """A second `set-routes` call overwrites the previous list."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE0","iteration":1,"phase_complete":false,"routes_pending":["/opsx:update"]}',
        )
        monkeypatch.chdir(test_env)
        invoke(
            [
                "state",
                "set-routes",
                "test-change",
                "--routes",
                "/opsx:continue",
            ]
        )
        assert self._read_state(test_env)["routes_pending"] == ["/opsx:continue"]

    def test_clear_routes_removes_field(self, test_env, monkeypatch):
        """`osx state clear-routes` strips routes_pending from state.json."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE0","iteration":1,"phase_complete":false,"routes_pending":["/opsx:update"]}',
        )
        monkeypatch.chdir(test_env)
        result = invoke(["state", "clear-routes", "test-change"])
        assert result.exit_code == 0, result.stdout
        assert "routes_pending" not in self._read_state(test_env)

    def test_set_routes_without_flag_clears(self, test_env, monkeypatch):
        """`osx state set-routes --routes ""` clears the list (explicit empty)."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE0","iteration":1,"phase_complete":false,"routes_pending":["/opsx:update"]}',
        )
        monkeypatch.chdir(test_env)
        invoke(["state", "set-routes", "test-change", "--routes", ""])
        assert self._read_state(test_env)["routes_pending"] == []

    def test_state_complete_clears_routes(self, test_env, monkeypatch):
        """Phase completion clears routes_pending (engine contract)."""
        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE0","iteration":1,"phase_complete":false,"routes_pending":["/opsx:update"]}',
        )
        monkeypatch.chdir(test_env)
        invoke(["state", "complete", "test-change"])
        state = self._read_state(test_env)
        assert state["phase_complete"] is True
        assert "routes_pending" not in state

    def test_engine_check_routes_pending_helper(self, test_env, monkeypatch):
        """Engine helper reads the list from state.json."""
        from source.orchestrator import engine as eng

        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE0","iteration":1,"phase_complete":false,"routes_pending":["/opsx:update","/opsx:continue"]}',
        )
        orch_state = eng.OrchestratorState(
            change_id="test-change",
            change_dir=test_env / "openspec" / "changes" / "test-change",
        )
        assert eng.check_routes_pending(orch_state) == [
            "/opsx:update",
            "/opsx:continue",
        ]

    def test_engine_check_routes_pending_empty_when_missing(self, test_env):
        """Engine helper returns [] when no state.json routes_pending is set."""
        from source.orchestrator import engine as eng

        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE0","iteration":1,"phase_complete":false}',
        )
        orch_state = eng.OrchestratorState(
            change_id="test-change",
            change_dir=test_env / "openspec" / "changes" / "test-change",
        )
        assert eng.check_routes_pending(orch_state) == []

    def test_engine_check_routes_pending_handles_corrupt_field(self, test_env):
        """Engine helper tolerates a non-list routes_pending field."""
        from source.orchestrator import engine as eng

        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE0","iteration":1,"phase_complete":false,"routes_pending":"not-a-list"}',
        )
        orch_state = eng.OrchestratorState(
            change_id="test-change",
            change_dir=test_env / "openspec" / "changes" / "test-change",
        )
        assert eng.check_routes_pending(orch_state) == []


@pytest.mark.integration
class TestEnginePhase0RouteHalt:
    """Engine-level tests for the soft-halt behavior in `run_phase`."""

    def test_run_phase_returns_false_when_routes_pending(self, test_env, monkeypatch):
        """PHASE0 with routes_pending non-empty + phase_complete=False → False (halt)."""
        from source.orchestrator import engine as eng

        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE0","iteration":1,"phase_complete":false,"routes_pending":["/opsx:update"]}',
        )
        monkeypatch.setattr(eng, "run_agent", lambda s, p: True)
        orch_state = eng.OrchestratorState(
            change_id="test-change",
            change_dir=test_env / "openspec" / "changes" / "test-change",
            max_phase_iterations=3,
        )
        assert eng.run_phase(orch_state, "PHASE0") is False

    def test_run_phase_proceeds_when_routes_pending_cleared(
        self, test_env, monkeypatch
    ):
        """PHASE0 with routes_pending cleared + phase_complete=True → True (advance)."""
        from source.orchestrator import engine as eng

        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE0","iteration":1,"phase_complete":false,"routes_pending":[]}',
        )
        monkeypatch.chdir(test_env)

        def _run_agent_sets_complete(state, phase):
            invoke(["state", "complete", "test-change"])
            return True

        monkeypatch.setattr(eng, "run_agent", _run_agent_sets_complete)
        orch_state = eng.OrchestratorState(
            change_id="test-change",
            change_dir=test_env / "openspec" / "changes" / "test-change",
            max_phase_iterations=3,
        )
        assert eng.run_phase(orch_state, "PHASE0") is True
        state = json.loads(
            (
                test_env / "openspec" / "changes" / "test-change" / "state.json"
            ).read_text()
        )
        assert state["phase_complete"] is False
        assert "routes_pending" not in state

    def test_write_state_preserves_routes_pending(self, test_env, monkeypatch):
        """The engine's write_state preserves routes_pending across iterations."""
        from source.orchestrator import engine as eng

        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE0","iteration":1,"phase_complete":false,"routes_pending":["/opsx:update","/opsx:continue"]}',
        )
        orch_state = eng.OrchestratorState(
            change_id="test-change",
            change_dir=test_env / "openspec" / "changes" / "test-change",
        )
        eng.write_state(orch_state, "PHASE0", iteration=2, phase_complete=False)
        state = json.loads(
            (
                test_env / "openspec" / "changes" / "test-change" / "state.json"
            ).read_text()
        )
        assert state["routes_pending"] == ["/opsx:update", "/opsx:continue"]


@pytest.mark.integration
class TestPhase0SeverityThreshold:
    """Severity-threshold contract for PHASE0 routing (Suggestion-only advances).

    The `osx-phase0` command and `osx-review-artifacts` skill apply a
    severity threshold: only Critical and Warning findings trigger a
    `routes_pending` route; Suggestion-only findings are advisory and the
    phase advances without routing. The engine treats an empty/absent
    ``routes_pending`` + ``phase_complete: true`` as "phase done, proceed
    to PHASE1". These tests pin the threshold contract end-to-end.
    """

    def _state_file(self, test_env) -> Path:
        return test_env / "openspec" / "changes" / "test-change" / "state.json"

    def _read_state(self, test_env) -> dict:
        return json.loads(self._state_file(test_env).read_text())

    def test_phase0_suggestion_only_no_routes_pending_advances(
        self, test_env, monkeypatch
    ):
        """PHASE0 with only Suggestion findings sets phase_complete; no routes_pending.

        Mirrors the agent's behavior when only Suggestion findings are
        classified: call ``osx state complete`` and do not call
        ``osx state set-routes``. The engine returns True (advance).
        """
        from source.orchestrator import engine as eng

        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE0","iteration":1,"phase_complete":false,'
            '"issues_found":{"critical":0,"warning":0,"suggestion":2}}',
        )
        monkeypatch.chdir(test_env)

        def _run_agent_marks_complete_only(state, phase):
            invoke(["state", "complete", "test-change"])
            return True

        monkeypatch.setattr(eng, "run_agent", _run_agent_marks_complete_only)
        orch_state = eng.OrchestratorState(
            change_id="test-change",
            change_dir=test_env / "openspec" / "changes" / "test-change",
            max_phase_iterations=3,
        )
        assert eng.run_phase(orch_state, "PHASE0") is True
        state = self._read_state(test_env)
        assert state["phase_complete"] is False
        assert "routes_pending" not in state

    def test_phase0_mixed_finding_sets_routes_pending(self, test_env, monkeypatch):
        """PHASE0 with Warning + Suggestion still routes (regression guard).

        Mixed finding sets contain at least one Critical/Warning and must
        still trigger the existing routing halt. Suggestion-only is the
        new exception; the mixed case is unchanged.
        """
        from source.orchestrator import engine as eng

        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE0","iteration":1,"phase_complete":false,'
            '"issues_found":{"critical":0,"warning":1,"suggestion":2},'
            '"routes_pending":["/osc-update-change"]}',
        )
        monkeypatch.setattr(eng, "run_agent", lambda s, p: True)
        orch_state = eng.OrchestratorState(
            change_id="test-change",
            change_dir=test_env / "openspec" / "changes" / "test-change",
            max_phase_iterations=3,
        )
        assert eng.run_phase(orch_state, "PHASE0") is False
        state = self._read_state(test_env)
        assert state["routes_pending"] == ["/osc-update-change"]

    def test_phase0_critical_only_sets_routes_pending(self, test_env, monkeypatch):
        """PHASE0 with Critical findings still routes (existing contract)."""
        from source.orchestrator import engine as eng

        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE0","iteration":1,"phase_complete":false,'
            '"issues_found":{"critical":1,"warning":0,"suggestion":0},'
            '"routes_pending":["/osc-update-change"]}',
        )
        monkeypatch.setattr(eng, "run_agent", lambda s, p: True)
        orch_state = eng.OrchestratorState(
            change_id="test-change",
            change_dir=test_env / "openspec" / "changes" / "test-change",
            max_phase_iterations=3,
        )
        assert eng.run_phase(orch_state, "PHASE0") is False
        state = self._read_state(test_env)
        assert state["routes_pending"] == ["/osc-update-change"]


@pytest.mark.integration
class TestPhase6ArchiveCleanup:
    """C4 fix: cleanup() re-resolves the path so transients are removed from the archive.

    The bug: after PHASE6, the change directory moved to
    ``openspec/changes/archive/YYYY-MM-DD-<change>/`` but the engine's
    ``cleanup()`` still references the pre-archive path. Transients
    (``state.json``, ``complete.json``, the per-change log) are silently
    never removed. The next ``orchestrate`` invocation finds the stale
    ``state.json`` in the archive and either aborts preflight or attempts
    to re-run a phantom phase.

    The fix: ``cleanup()`` re-resolves the change path via
    ``find_change_dir`` (with a direct archive-walk fallback) before
    touching any files.
    """

    def test_cleanup_removes_transients_from_archive(self, test_env, monkeypatch):
        """End-to-end: setup post-archive state, run cleanup, verify transients gone."""
        import shutil
        import subprocess

        from source.orchestrator import engine as eng

        active = test_env / "openspec" / "changes" / "test-change"
        if active.exists():
            shutil.rmtree(active)

        archive = (
            test_env / "openspec" / "changes" / "archive" / "2024-01-15-test-change"
        )
        archive.mkdir(parents=True)
        (archive / "proposal.md").write_text("# Proposal")
        (archive / "tasks.md").write_text("# Tasks")
        (archive / "decision-log.json").write_text("[]")
        (archive / "iterations.json").write_text("[]")
        (archive / "state.json").write_text(
            json.dumps({"phase": "PHASE6", "phase_complete": True})
        )
        (archive / "complete.json").write_text(json.dumps({"status": "COMPLETE"}))
        log_file = archive / ".osx-orchestrate-test-change.log"
        log_file.write_text("orchestrator log")
        baseline = test_env / ".openspec-baseline.json"
        baseline.write_text("{}")

        subprocess.run(["git", "add", "-A"], cwd=test_env, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "Archive test-change"],
            cwd=test_env,
            check=True,
        )

        monkeypatch.chdir(test_env)

        st = eng.OrchestratorState(
            change_dir=active,
            change_id="test-change",
        )
        st.log_file = log_file
        st.log_user_specified = False

        eng.cleanup(st, 0)

        assert not (archive / "state.json").exists()
        assert not (archive / "complete.json").exists()
        assert not log_file.exists()
        assert not baseline.exists()

        assert (archive / "iterations.json").exists()
        assert (archive / "decision-log.json").exists()
        assert (archive / "proposal.md").exists()
        assert (archive / "tasks.md").exists()

    def test_validate_archive_passes_for_well_formed_archive(
        self, test_env, monkeypatch
    ):
        """validate_archive (called by the engine) accepts a properly archived change."""
        from source.lib import osx as osx_lib

        archive = (
            test_env / "openspec" / "changes" / "archive" / "2024-01-15-test-change"
        )
        archive.mkdir(parents=True)
        (archive / "decision-log.json").write_text("[]")
        (archive / "iterations.json").write_text("[]")
        (archive / "proposal.md").write_text("# Proposal")

        import subprocess

        subprocess.run(["git", "add", "-A"], cwd=test_env, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "Archive test-change"],
            cwd=test_env,
            check=True,
        )

        monkeypatch.chdir(test_env)
        osx_lib._PATHS_CACHE.clear()

        result = osx_lib.validate_archive("test-change")

        assert result["valid"] is True
        assert result["archive"].endswith("2024-01-15-test-change")

    def test_validate_archive_rejects_archive_missing_decision_log(
        self, test_env, monkeypatch
    ):
        """validate_archive rejects an archive directory that lacks decision-log.json."""
        from source.lib import osx as osx_lib

        archive = (
            test_env / "openspec" / "changes" / "archive" / "2024-01-15-test-change"
        )
        archive.mkdir(parents=True)
        (archive / "iterations.json").write_text("[]")
        (archive / "proposal.md").write_text("# Proposal")

        import subprocess

        subprocess.run(["git", "add", "-A"], cwd=test_env, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "Archive test-change"],
            cwd=test_env,
            check=True,
        )

        monkeypatch.chdir(test_env)
        osx_lib._PATHS_CACHE.clear()

        result = osx_lib.validate_archive("test-change")

        assert result["valid"] is False
        assert any(e["check"] == "decision-log" for e in result["errors"])

    def test_orchestrator_early_exit_fires_after_cleanup(self, test_env, monkeypatch):
        """After cleanup removes transients, the engine's early-exit check fires.

        Reproduces the C4 bug scenario: a previously-archived change that
        had stale transients. After cleanup, the next ``orchestrate`` call
        should detect the change is already archived and complete.
        """
        import shutil
        import subprocess

        active = test_env / "openspec" / "changes" / "test-change"
        if active.exists():
            shutil.rmtree(active)

        archive = (
            test_env / "openspec" / "changes" / "archive" / "2024-01-15-test-change"
        )
        archive.mkdir(parents=True)
        (archive / "decision-log.json").write_text("[]")
        (archive / "iterations.json").write_text("[]")
        (archive / "proposal.md").write_text("# Proposal")
        (archive / "tasks.md").write_text("# Tasks")
        (archive / "state.json").write_text(
            json.dumps({"phase": "PHASE6", "phase_complete": True})
        )
        (archive / "complete.json").write_text(json.dumps({"status": "COMPLETE"}))

        subprocess.run(["git", "add", "-A"], cwd=test_env, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "Archive test-change"],
            cwd=test_env,
            check=True,
        )

        monkeypatch.chdir(test_env)

        from source.orchestrator import engine as eng

        resolved = eng.find_change_dir("test-change")
        assert resolved is not None
        assert "archive" in str(resolved)

        assert (resolved / "state.json").exists()
        assert (resolved / "complete.json").exists()

        st = eng.OrchestratorState(change_dir=active, change_id="test-change")
        st.log_file = None
        st.log_user_specified = False
        eng.cleanup(st, 0)

        assert not (resolved / "state.json").exists()
        assert not (resolved / "complete.json").exists()

        assert "archive" in str(resolved) and not (resolved / "state.json").exists()


@pytest.mark.integration
class TestCleanErrorReporting:
    """M20: --clean logs warnings instead of silently swallowing OSError
    when transient file removal fails."""

    def test_clean_logs_warning_when_state_json_unremovable(
        self, test_env, monkeypatch
    ):
        """A read-only parent directory causes --clean to log a clear warning
        instead of failing silently."""
        from source.orchestrator import engine as eng

        change = test_env / "openspec" / "changes" / "test-change"
        change.mkdir(parents=True, exist_ok=True)
        state_file = change / "state.json"
        state_file.write_text('{"phase":"PHASE1"}')

        import getpass
        import os as _os
        import stat

        if getpass.getuser() == "root" or _os.geteuid() == 0:
            pytest.skip("cannot simulate permission failure as root")

        original_mode = change.stat().st_mode
        try:
            # Make the parent directory read-only so unlink fails
            change.chmod(stat.S_IRUSR | stat.S_IXUSR)
            monkeypatch.chdir(test_env)

            captured: dict = {"warnings": []}

            def capture_warn(state_or_msg, msg=None):
                if msg is None and isinstance(state_or_msg, str):
                    captured["warnings"].append(state_or_msg)
                else:
                    captured["warnings"].append(msg)

            monkeypatch.setattr(eng, "log_warning", capture_warn)
            monkeypatch.setattr(eng, "log_verbose", lambda *a, **kw: None)
            monkeypatch.setattr(
                eng, "run_agent", lambda s, p: (_ for _ in ()).throw(SystemExit(0))
            )

            st = eng.OrchestratorState(
                change_id="test-change",
                change_dir=change,
                clean=True,
                force=True,
            )

            from contextlib import suppress

            with suppress(SystemExit):
                eng.run_orchestrator(st)

            assert any(
                "Failed to remove" in w and "state.json" in w
                for w in captured["warnings"]
            ), f"expected warning; got {captured['warnings']}"
        finally:
            change.chmod(original_mode)


@pytest.mark.integration
class TestBlockerFileRecheck:
    """M22: a phase that writes ``complete.json`` BLOCKED without setting
    ``phase_complete`` must not be re-invoked in the next iteration."""

    def test_check_blocker_returns_reason_when_present(self, tmp_path):
        """The check_blocker helper returns the blocker_reason from complete.json."""
        from source.orchestrator import engine as eng

        change = tmp_path / "openspec" / "changes" / "test-change"
        change.mkdir(parents=True)
        (change / "complete.json").write_text(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "with_blocker": True,
                    "blocker_reason": "tests failing in CI",
                }
            )
        )

        st = eng.OrchestratorState(change_id="test-change", change_dir=change)
        reason = eng.check_blocker(st)
        assert reason == "tests failing in CI"

    def test_check_blocker_returns_none_when_not_blocked(self, tmp_path):
        """complete.json without with_blocker returns None."""
        from source.orchestrator import engine as eng

        change = tmp_path / "openspec" / "changes" / "test-change"
        change.mkdir(parents=True)
        (change / "complete.json").write_text(json.dumps({"status": "COMPLETE"}))

        st = eng.OrchestratorState(change_id="test-change", change_dir=change)
        assert eng.check_blocker(st) is None

    def test_check_blocker_returns_none_when_file_missing(self, tmp_path):
        """No complete.json returns None (graceful)."""
        from source.orchestrator import engine as eng

        change = tmp_path / "openspec" / "changes" / "test-change"
        change.mkdir(parents=True)

        st = eng.OrchestratorState(change_id="test-change", change_dir=change)
        assert eng.check_blocker(st) is None

    def test_run_phase_halts_when_blocker_detected(self, tmp_path, monkeypatch):
        """After run_agent returns, if complete.json BLOCKED appears,
        run_phase returns False without re-invoking the agent."""
        from source.orchestrator import engine as eng

        change = tmp_path / "openspec" / "changes" / "test-change"
        change.mkdir(parents=True)
        (change / "tasks.md").write_text("# Tasks")
        (change / "proposal.md").write_text("# Proposal")
        (change / "design.md").write_text("# Design")
        (change / "specs").mkdir()
        (change / "specs" / "spec.md").write_text("# Spec")
        (change / "state.json").write_text(
            json.dumps({"phase": "PHASE1", "iteration": 1, "phase_complete": False})
        )

        monkeypatch.chdir(tmp_path)

        agent_call_count = {"n": 0}

        def fake_run_agent(state, phase):  # noqa: ARG001
            agent_call_count["n"] += 1
            # Simulate the agent writing complete.json BLOCKED
            (state.change_dir / "complete.json").write_text(
                json.dumps(
                    {
                        "status": "BLOCKED",
                        "with_blocker": True,
                        "blocker_reason": "stuck",
                    }
                )
            )
            return True

        monkeypatch.setattr(eng, "run_agent", fake_run_agent)
        monkeypatch.setattr(eng, "write_state", lambda *a, **kw: None)
        monkeypatch.setattr(eng, "get_next_phase_iteration", lambda state, phase: 1)
        monkeypatch.setattr(eng, "check_phase_complete", lambda state: False)
        monkeypatch.setattr(eng, "check_routes_pending", lambda state: [])

        st = eng.OrchestratorState(change_id="test-change", change_dir=change)
        result = eng.run_phase(st, "PHASE1")

        assert result is False
        assert agent_call_count["n"] == 1, "agent must not be re-invoked after blocker"


@pytest.mark.integration
class TestPhase2DiffLogField:
    """A.2: PHASE2 must record the ``openspec show --diff --json`` envelope
    in the decision-log entry's ``cli_diff`` field. The osx-phase2 command's
    MANDATORY CHECKPOINT step 3 mandates this; the test mocks the agent
    subprocess to emit the log entry and asserts the field round-trips."""

    def test_phase2_emits_diff_log_field(self, test_env, monkeypatch):
        """A mocked PHASE2 agent emits a decision-log entry whose ``--extra``
        JSON carries a non-empty ``cli_diff`` object. ``osx log get`` then
        returns the entry with the field intact."""
        from source.orchestrator import engine as eng

        setup_change(
            test_env,
            "test-change",
            '{"phase":"PHASE2","iteration":1,"phase_complete":false}',
        )
        monkeypatch.chdir(test_env)

        # Diff envelope: shape mirrors the openspec show --diff --json
        # payload (per-requirement diff blocks for MODIFIED deltas).
        diff_envelope = {
            "changeName": "test-change",
            "deltas": [
                {
                    "delta": "MODIFIED",
                    "capability": "auth",
                    "requirement": "R1",
                    "diff": (
                        "--- a/openspec/specs/auth.md\n"
                        "+++ b/openspec/specs/auth.md\n"
                        "@@ -1,3 +1,3 @@\n"
                        "-The system SHALL authenticate users.\n"
                        "+The system SHALL authenticate users via OAuth2."
                    ),
                    "warning": None,
                },
                {
                    "delta": "ADDED",
                    "capability": "auth",
                    "requirement": "R2",
                },
            ],
        }

        extra_json = json.dumps(
            {
                "verification_result": "passed",
                "issues_found": {"critical": 0, "warning": 0, "suggestion": 0},
                "verification_report_path": "openspec/changes/test-change/verification-report.md",
                "artifacts_modified": False,
                "cli_diff": diff_envelope,
            }
        )

        def fake_run_agent(state, phase):
            invoke(
                [
                    "log",
                    "append",
                    "test-change",
                    "--phase",
                    "REVIEW",
                    "--iteration",
                    "1",
                    "--summary",
                    "PHASE2 verification passed; embedded openspec show --diff appendix",
                    "--extra",
                    extra_json,
                ]
            )
            invoke(["state", "complete", "test-change"])
            return True

        monkeypatch.setattr(eng, "run_agent", fake_run_agent)
        monkeypatch.setattr(eng, "write_state", lambda *a, **kw: None)
        monkeypatch.setattr(eng, "get_next_phase_iteration", lambda state, phase: 1)
        monkeypatch.setattr(eng, "check_routes_pending", lambda state: [])

        st = eng.OrchestratorState(change_id="test-change", change_dir=test_env / "openspec/changes/test-change")
        assert eng.run_phase(st, "PHASE2") is True

        # Round-trip: `osx log get` must surface the cli_diff field.
        get_result = invoke(["log", "get", "test-change"])
        assert get_result.exit_code == 0, get_result.stdout
        payload = json.loads(get_result.stdout)
        assert isinstance(payload, dict), f"log get payload should be a dict; got {payload!r}"
        entries = payload.get("entries")
        assert isinstance(entries, list) and entries, (
            f"decision log must have at least one entry; got payload={payload!r}"
        )
        latest = entries[-1]
        assert "cli_diff" in latest, (
            f"PHASE2 decision-log entry missing cli_diff field; got keys: {list(latest.keys())}"
        )
        assert isinstance(latest["cli_diff"], dict), (
            f"cli_diff should round-trip as a dict; got {type(latest['cli_diff']).__name__}"
        )
        assert latest["cli_diff"] == diff_envelope, (
            "cli_diff payload must round-trip exactly; "
            f"got {latest['cli_diff']!r}"
        )
        # Spot-check the MODIFIED delta's diff block survived intact.
        deltas = latest["cli_diff"]["deltas"]
        assert deltas[0]["delta"] == "MODIFIED"
        assert "diff" in deltas[0]
        assert "OAuth2" in deltas[0]["diff"]


@pytest.mark.integration
class TestRetireCapabilitiesRouting:
    """A.3: PHASE0 pre-flight detects ``retire_capabilities: true`` in
    ``.openspec.yaml`` and stamps ``state.retire_capabilities = True``.

    The wrapper functions in the orchestrator engine (not the full
    ``run_orchestrator`` loop, which would require a live AI subprocess)
    are exercised directly so the routing signal is verified without a
    real agent invocation.
    """

    def _setup_retirement_change(self, test_env, monkeypatch):
        """Create a change with retire_capabilities: true in .openspec.yaml
        and a minimal ``## REMOVED Requirements`` block to simulate a
        retirement-ready change."""
        change_dir = setup_change(
            test_env,
            "retire-cap",
            '{"phase":"PHASE0","iteration":1,"phase_complete":false}',
        )
        (change_dir / ".openspec.yaml").write_text(
            "schema: spec-driven\nretire_capabilities: true\n"
        )
        specs_dir = change_dir / "specs"
        specs_dir.mkdir(exist_ok=True)
        (specs_dir / "legacy.md").write_text(
            "# Legacy capability\n\n## REMOVED Requirements\n\n"
            "### R: legacy-thing\n\nThe system SHALL not retain legacy-thing.\n"
        )
        monkeypatch.chdir(test_env)
        return change_dir

    def test_validate_change_dir_stamps_retire_capabilities(
        self, test_env, monkeypatch
    ):
        """``validate_change_dir`` wrapper reads .openspec.yaml and sets
        ``state.retire_capabilities = True``."""
        from source.lib import osx as osx_lib
        from source.orchestrator import engine as eng

        change_dir = self._setup_retirement_change(test_env, monkeypatch)

        # Mock the underlying library call so we don't need a real
        # ``openspec`` CLI on PATH.
        def _fake_validate(change_id, *, store=None):
            return {"valid": True, "planning_complete": True}

        monkeypatch.setattr(osx_lib, "validate_change_dir", _fake_validate)

        st = eng.OrchestratorState(
            change_id="retire-cap", change_dir=change_dir
        )
        assert st.retire_capabilities is False
        eng.validate_change_dir(st)
        assert st.retire_capabilities is True

    def test_validate_change_dir_emits_verbose_log(
        self, test_env, monkeypatch, capsys
    ):
        """The verbose log line is emitted when retire_capabilities is true."""
        from source.lib import osx as osx_lib
        from source.orchestrator import engine as eng

        change_dir = self._setup_retirement_change(test_env, monkeypatch)

        def _fake_validate(change_id, *, store=None):
            return {"valid": True, "planning_complete": True}

        monkeypatch.setattr(osx_lib, "validate_change_dir", _fake_validate)

        st = eng.OrchestratorState(
            change_id="retire-cap",
            change_dir=change_dir,
            verbose=True,
        )
        eng.validate_change_dir(st)
        captured = capsys.readouterr()
        assert "Retire capabilities: true (from .openspec.yaml)" in captured.out

    def test_validate_change_dir_no_marker_keeps_default(
        self, test_env, monkeypatch
    ):
        """A change without ``retire_capabilities: true`` leaves the field
        at its default (False)."""
        from source.lib import osx as osx_lib
        from source.orchestrator import engine as eng

        change_dir = setup_change(
            test_env,
            "plain-change",
            '{"phase":"PHASE0","iteration":1,"phase_complete":false}',
        )
        (change_dir / ".openspec.yaml").write_text("schema: spec-driven\n")
        monkeypatch.chdir(test_env)

        def _fake_validate(change_id, *, store=None):
            return {"valid": True, "planning_complete": True}

        monkeypatch.setattr(osx_lib, "validate_change_dir", _fake_validate)

        st = eng.OrchestratorState(
            change_id="plain-change", change_dir=change_dir
        )
        eng.validate_change_dir(st)
        assert st.retire_capabilities is False

    def test_validate_archive_stamps_retire_capabilities_from_archive_dir(
        self, test_env, monkeypatch
    ):
        """``validate_archive`` wrapper also reads the metadata — but from
        the archive directory once the change has moved."""
        from source.lib import osx as osx_lib
        from source.orchestrator import engine as eng

        # Build a pre-archive change with retire_capabilities: true.
        change_dir = self._setup_retirement_change(test_env, monkeypatch)

        # Build a parallel archive directory with the same metadata.
        archive = (
            test_env / "openspec" / "changes" / "archive"
            / "2024-09-01-retire-cap"
        )
        archive.mkdir(parents=True)
        (archive / "decision-log.json").write_text("[]")
        (archive / "iterations.json").write_text("[]")
        (archive / "proposal.md").write_text("# Proposal")
        (archive / ".openspec.yaml").write_text(
            "schema: spec-driven\nretire_capabilities: true\n"
        )

        import subprocess

        subprocess.run(["git", "add", "-A"], cwd=test_env, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "Archive retire-cap"],
            cwd=test_env,
            check=True,
        )
        osx_lib._PATHS_CACHE.clear()

        def _fake_validate(change_id, *, store=None):
            return {
                "valid": True,
                "archive": str(archive),
            }

        monkeypatch.setattr(osx_lib, "validate_archive", _fake_validate)
        monkeypatch.chdir(test_env)

        st = eng.OrchestratorState(
            change_id="retire-cap", change_dir=change_dir
        )
        assert st.retire_capabilities is False
        success, archive_dir = eng.validate_archive(st)
        assert success is True
        assert "retire-cap" in archive_dir
        assert st.retire_capabilities is True


@pytest.mark.integration
class TestOperationGuidanceInjection:
    """A.4: ``operations.{apply|archive}.guidance`` from
    ``openspec/config.yaml`` reaches the dispatched AI prompt for PHASE1
    and PHASE6 (and only those phases) via ``RunRequest.extra_prompt``.

    Tests target ``build_run_request`` directly so the dispatch shape can
    be asserted without spawning an AI subprocess. The runner-level
    coverage (OpenCode ``--file`` flag, Claude prompt prepend) lives in
    ``tests/unit/test_runner_abstraction.py::TestRunRequestExtraPrompt``.
    """

    def _setup_with_guidance(self, test_env, monkeypatch, guidance_yaml: str) -> Path:
        """Lay down ``openspec/config.yaml`` and ``.opencode/`` so the
        project_root derivation works."""
        openspec = test_env / "openspec"
        openspec.mkdir(exist_ok=True)
        (openspec / "config.yaml").write_text(guidance_yaml)
        change = openspec / "changes" / "op-test"
        change.mkdir(parents=True, exist_ok=True)
        monkeypatch.chdir(test_env)
        return change

    def test_phase1_injects_apply_guidance(self, test_env, monkeypatch):
        """PHASE1 spawns receive the apply guidance joined by newlines."""
        from source.orchestrator import engine as eng

        change = self._setup_with_guidance(
            test_env,
            monkeypatch,
            (
                "operations:\n"
                "  apply:\n"
                "    guidance:\n"
                "      - 'Always run unit tests.'\n"
                "      - 'Prefer composition over inheritance.'\n"
            ),
        )
        st = eng.OrchestratorState(change_id="op-test", change_dir=change)

        request = eng.build_run_request(st, "PHASE1")

        assert request.command == "osx-phase1"
        assert request.agent == "osx-builder"
        assert request.extra_prompt == (
            "Always run unit tests.\nPrefer composition over inheritance."
        )

    def test_phase6_injects_archive_guidance(self, test_env, monkeypatch):
        """PHASE6 spawns receive the archive guidance joined by newlines."""
        from source.orchestrator import engine as eng

        change = self._setup_with_guidance(
            test_env,
            monkeypatch,
            "operations:\n  archive:\n    guidance:\n      - 'Move CHANGELOG.md entry above the v-next header.'\n",
        )
        st = eng.OrchestratorState(change_id="op-test", change_dir=change)

        request = eng.build_run_request(st, "PHASE6")

        assert request.command == "osx-phase6"
        assert request.agent == "osx-maintainer"
        assert request.extra_prompt == (
            "Move CHANGELOG.md entry above the v-next header."
        )

    def test_other_phases_get_empty_extra_prompt(self, test_env, monkeypatch):
        """PHASE0/PHASE2/PHASE3/PHASE4/PHASE5 ignore the guidance — even
        when both operations define it. Only apply (PHASE1) and archive
        (PHASE6) are surfaced."""
        from source.orchestrator import engine as eng

        change = self._setup_with_guidance(
            test_env,
            monkeypatch,
            (
                "operations:\n"
                "  apply:\n"
                "    guidance:\n"
                "      - 'A1'\n"
                "      - 'A2'\n"
                "  archive:\n"
                "    guidance:\n"
                "      - 'Z1'\n"
            ),
        )
        st = eng.OrchestratorState(change_id="op-test", change_dir=change)

        for phase in ("PHASE0", "PHASE2", "PHASE3", "PHASE4", "PHASE5"):
            request = eng.build_run_request(st, phase)
            assert request.extra_prompt == "", (
                f"{phase} must not surface operation guidance; "
                f"got {request.extra_prompt!r}"
            )

    def test_missing_config_yields_empty_extra_prompt(
        self, test_env, monkeypatch
    ):
        """No ``openspec/config.yaml`` means no guidance."""
        from source.orchestrator import engine as eng

        # Project root has no openspec/config.yaml.
        openspec = test_env / "openspec"
        openspec.mkdir(exist_ok=True)
        change = openspec / "changes" / "op-test"
        change.mkdir(parents=True, exist_ok=True)
        monkeypatch.chdir(test_env)

        st = eng.OrchestratorState(change_id="op-test", change_dir=change)
        for phase in ("PHASE1", "PHASE6"):
            request = eng.build_run_request(st, phase)
            assert request.extra_prompt == ""

    def test_apply_only_guidance_does_not_leak_into_archive(
        self, test_env, monkeypatch
    ):
        """Archive spawns stay empty when only ``operations.apply`` has
        guidance."""
        from source.orchestrator import engine as eng

        change = self._setup_with_guidance(
            test_env,
            monkeypatch,
            "operations:\n  apply:\n    guidance:\n      - 'A only'\n",
        )
        st = eng.OrchestratorState(change_id="op-test", change_dir=change)

        assert eng.build_run_request(st, "PHASE1").extra_prompt == "A only"
        assert eng.build_run_request(st, "PHASE6").extra_prompt == ""
