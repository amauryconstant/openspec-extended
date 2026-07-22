#!/usr/bin/env python3
"""
Unit tests for osx-orchestrate state machine and signal handling.
"""

import json
from unittest.mock import patch

import pytest

from source.orchestrator.engine import (
    OrchestratorState,
    PHASE_NAMES,
    PHASE_COMMANDS,
    PHASE_AGENTS,
    find_change_dir,
    read_state,
    write_state,
    check_transition,
    get_transition_reason,
    get_transition_details,
    check_phase_complete,
    log_verbose,
    advance_phase,
    archive_log_file,
)


@pytest.fixture
def temp_change_dir(tmp_path):
    """Create temporary change directory structure."""
    change_dir = tmp_path / "openspec" / "changes" / "test-change"
    change_dir.mkdir(parents=True)
    (change_dir / "tasks.md").write_text("# Tasks")
    (change_dir / "proposal.md").write_text("# Proposal")
    (change_dir / "design.md").write_text("# Design")
    specs_dir = change_dir / "specs"
    specs_dir.mkdir()
    (specs_dir / "spec.md").write_text("# Spec")
    return change_dir


@pytest.fixture
def archived_change_dir(tmp_path):
    """Create archived change directory."""
    archive_dir = tmp_path / "openspec" / "changes" / "archive"
    archived = archive_dir / "2024-01-15-test-change"
    archived.mkdir(parents=True)
    return archived


@pytest.fixture
def state(temp_change_dir):
    """Create OrchestratorState for testing."""
    return OrchestratorState(
        change_dir=temp_change_dir,
        change_id="test-change",
        verbose=False,
        no_color=True,
    )


@pytest.mark.unit
class TestStateMachine:
    """Tests for state machine phase transitions."""

    def test_phase_transition_normal_advance(self, temp_change_dir, monkeypatch):
        """Normal advance when no explicit transition set."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)

        state_file = temp_change_dir / "state.json"
        state_file.write_text(
            json.dumps(
                {
                    "phase": "PHASE0",
                    "iteration": 1,
                    "phase_complete": True,
                    "phase_iterations": {"PHASE0": 1},
                }
            )
        )

        st = OrchestratorState(change_dir=temp_change_dir)
        has_transition, target = check_transition(st)

        assert has_transition is False
        assert target == ""

    def test_phase_transition_explicit(self, temp_change_dir, monkeypatch):
        """Explicit transition when set in state."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)

        state_file = temp_change_dir / "state.json"
        state_file.write_text(
            json.dumps(
                {
                    "phase": "PHASE2",
                    "iteration": 1,
                    "phase_complete": True,
                    "transition": {
                        "target": "PHASE1",
                        "reason": "implementation_incorrect",
                    },
                }
            )
        )

        st = OrchestratorState(change_dir=temp_change_dir)
        has_transition, target = check_transition(st)

        assert has_transition is True
        assert target == "PHASE1"

    def test_phase_transition_missing_state(self, temp_change_dir, monkeypatch):
        """Handles missing state.json gracefully."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)
        st = OrchestratorState(change_dir=temp_change_dir)

        has_transition, target = check_transition(st)

        assert has_transition is False
        assert target == ""

    def test_phase_iterations_tracking(self, temp_change_dir, monkeypatch):
        """Iteration counts per phase are tracked correctly."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)

        state_file = temp_change_dir / "state.json"
        state_file.write_text(
            json.dumps(
                {
                    "phase": "PHASE4",
                    "iteration": 1,
                    "phase_complete": False,
                    "phase_iterations": {
                        "PHASE0": 1,
                        "PHASE1": 2,
                        "PHASE2": 1,
                        "PHASE3": 1,
                        "PHASE4": 1,
                    },
                }
            )
        )

        st = OrchestratorState(change_dir=temp_change_dir)
        data = read_state(st)

        assert data["phase_iterations"]["PHASE0"] == 1
        assert data["phase_iterations"]["PHASE1"] == 2
        assert data["phase_iterations"]["PHASE2"] == 1

    def test_check_complete_detection(self, temp_change_dir, monkeypatch):
        """COMPLETE signal detection via complete.json."""
        from source.orchestrator.engine import check_complete

        monkeypatch.chdir(temp_change_dir.parent.parent.parent)
        st = OrchestratorState(change_dir=temp_change_dir, change_id="test-change")

        with patch("source.lib.osx.complete_check") as mock_check:
            mock_check.return_value = {"exists": True}
            result = check_complete(st)
            assert result is True


@pytest.mark.unit
class TestPhaseLookup:
    """Tests for phase name/command/agent lookups."""

    def test_get_phase_name(self):
        """Correct phase names returned."""
        assert PHASE_NAMES["PHASE0"] == "ARTIFACT REVIEW"
        assert PHASE_NAMES["PHASE1"] == "IMPLEMENTATION"
        assert PHASE_NAMES["PHASE2"] == "REVIEW"
        assert PHASE_NAMES["PHASE3"] == "MAINTAIN DOCS"
        assert PHASE_NAMES["PHASE4"] == "SYNC"
        assert PHASE_NAMES["PHASE5"] == "SELF-REFLECTION"
        assert PHASE_NAMES["PHASE6"] == "ARCHIVE"

    def test_get_phase_command(self):
        """Correct phase commands returned."""
        assert PHASE_COMMANDS["PHASE0"] == "osx-phase0"
        assert PHASE_COMMANDS["PHASE1"] == "osx-phase1"
        assert PHASE_COMMANDS["PHASE2"] == "osx-phase2"
        assert PHASE_COMMANDS["PHASE3"] == "osx-phase3"
        assert PHASE_COMMANDS["PHASE4"] == "osx-phase4"
        assert PHASE_COMMANDS["PHASE5"] == "osx-phase5"
        assert PHASE_COMMANDS["PHASE6"] == "osx-phase6"

    def test_get_phase_agent(self):
        """Correct phase agents returned.

        PHASE2 and PHASE5 dispatch to ``osx-reviewer`` (a write-capable
        low-temperature reviewer) because their bodies write
        ``verification-report.md`` / ``reflections.md`` and ``git commit``;
        the read-only ``osx-analyzer`` would deny those operations.
        """
        assert PHASE_AGENTS["PHASE0"] == "osx-analyzer"
        assert PHASE_AGENTS["PHASE1"] == "osx-builder"
        assert PHASE_AGENTS["PHASE2"] == "osx-reviewer"
        assert PHASE_AGENTS["PHASE3"] == "osx-maintainer"
        assert PHASE_AGENTS["PHASE4"] == "osx-maintainer"
        assert PHASE_AGENTS["PHASE5"] == "osx-reviewer"
        assert PHASE_AGENTS["PHASE6"] == "osx-maintainer"


@pytest.mark.unit
class TestChangeDirectory:
    """Tests for change directory resolution."""

    def test_find_change_dir_primary(self, temp_change_dir, monkeypatch):
        """Finds change in primary openspec/changes location."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)

        result = find_change_dir("test-change")

        assert result is not None
        assert result.name == "test-change"
        assert result.parent.name == "changes"

    def test_find_change_dir_archived(self, tmp_path, monkeypatch):
        """Finds change in archive directory."""
        archive_dir = tmp_path / "openspec/changes/archive"
        archive_dir.mkdir(parents=True)
        archived = archive_dir / "2024-01-15-test-change"
        archived.mkdir()

        monkeypatch.chdir(tmp_path)

        result = find_change_dir("test-change")

        assert result is not None
        assert "archive" in str(result)
        assert result.name.endswith("-test-change")

    def test_find_change_dir_not_found(self, tmp_path, monkeypatch):
        """Returns None if change not found."""
        monkeypatch.chdir(tmp_path)

        result = find_change_dir("nonexistent")

        assert result is None


@pytest.mark.unit
class TestLogging:
    """Tests for logging behavior."""

    def test_verbose_flag_controls_output(self, capsys, state):
        """Verbose flag enables VERBOSE output to terminal."""
        state.verbose = True

        log_verbose(state, "Test verbose message")

        captured = capsys.readouterr()
        assert "[VERBOSE]" in captured.out
        assert "Test verbose message" in captured.out

    def test_no_color_flag_strips_ansi(self, capsys, state):
        """no_color flag removes ANSI codes."""
        state.verbose = True
        state.no_color = True

        log_verbose(state, "Test message")

        captured = capsys.readouterr()
        assert "\x1b[" not in captured.out

    def test_log_file_receives_all_output(self, capsys, state):
        """Log file contains verbose messages even without -v flag."""
        log_file = state.change_dir / "test.log"
        log_file.touch()
        state.verbose = False
        state.no_color = True
        state.log_file = log_file

        log_verbose(state, "Verbose to log file")

        log_content = log_file.read_text()
        assert "Verbose to log file" in log_content


@pytest.mark.unit
class TestArchive:
    """Tests for log file archiving."""

    def test_archive_log_file_early_return(self, state):
        """Early return when no log file exists."""
        state.log_file = None

        result = archive_log_file(state)

        assert result is True

    def test_archive_log_file_user_specified(self, state):
        """User-specified log file is not archived."""
        log_file = state.change_dir / "user-specified.log"
        log_file.write_text("user log content")
        state.log_file = log_file
        state.log_user_specified = True

        result = archive_log_file(state)

        assert result is True
        assert log_file.exists()


@pytest.mark.unit
class TestAdvancePhase:
    """Tests for phase advancement logic."""

    def test_advance_phase_normal_sequence(self):
        """Phases advance in correct order."""
        assert advance_phase("PHASE0") == "PHASE1"
        assert advance_phase("PHASE1") == "PHASE2"
        assert advance_phase("PHASE2") == "PHASE3"
        assert advance_phase("PHASE3") == "PHASE4"
        assert advance_phase("PHASE4") == "PHASE5"
        assert advance_phase("PHASE5") == "PHASE6"
        assert advance_phase("PHASE6") == "COMPLETE"

    def test_advance_phase_complete_stays_complete(self):
        """COMPLETE remains COMPLETE."""
        assert advance_phase("COMPLETE") == "COMPLETE"


@pytest.mark.unit
class TestGetTransitionReason:
    """Tests for transition reason retrieval."""

    def test_get_transition_reason_valid(self, temp_change_dir, monkeypatch):
        """Returns reason when transition is set."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)

        state_file = temp_change_dir / "state.json"
        state_file.write_text(
            json.dumps(
                {
                    "phase": "PHASE2",
                    "iteration": 1,
                    "transition": {
                        "reason": "artifacts_modified",
                        "details": "Spec updated",
                    },
                }
            )
        )

        st = OrchestratorState(change_dir=temp_change_dir)
        reason = get_transition_reason(st)
        details = get_transition_details(st)

        assert reason == "artifacts_modified"
        assert details == "Spec updated"

    def test_get_transition_reason_missing(self, temp_change_dir, monkeypatch):
        """Returns 'unknown' when no transition set."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)

        state_file = temp_change_dir / "state.json"
        state_file.write_text(json.dumps({"phase": "PHASE0"}))

        st = OrchestratorState(change_dir=temp_change_dir)
        reason = get_transition_reason(st)

        assert reason == "unknown"


@pytest.mark.unit
class TestReadWriteState:
    """Tests for state file read/write operations."""

    def test_write_state_creates_file(self, temp_change_dir, monkeypatch):
        """write_state creates state.json file."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)
        st = OrchestratorState(change_dir=temp_change_dir, total_invocations=0)

        write_state(st, "PHASE0", 1)

        state_file = temp_change_dir / "state.json"
        assert state_file.exists()

        data = json.loads(state_file.read_text())
        assert data["phase"] == "PHASE0"
        assert data["iteration"] == 1

    def test_write_state_increments_phase_iterations(
        self, temp_change_dir, monkeypatch
    ):
        """write_state increments phase iteration count."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)
        st = OrchestratorState(change_dir=temp_change_dir, total_invocations=0)

        state_file = temp_change_dir / "state.json"
        state_file.write_text(
            json.dumps({"phase": "PHASE0", "phase_iterations": {"PHASE0": 1}})
        )

        write_state(st, "PHASE0", 2)

        data = json.loads(state_file.read_text())
        assert data["phase_iterations"]["PHASE0"] == 2

    def test_read_state_missing_file(self, temp_change_dir, monkeypatch):
        """read_state returns None when file missing."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)
        st = OrchestratorState(change_dir=temp_change_dir)

        result = read_state(st)

        assert result is None

    def test_read_state_invalid_json(self, temp_change_dir, monkeypatch):
        """read_state returns None for corrupted state."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)

        state_file = temp_change_dir / "state.json"
        state_file.write_text("not valid json")

        st = OrchestratorState(change_dir=temp_change_dir)
        result = read_state(st)

        assert result is None


@pytest.mark.unit
class TestCheckPhaseComplete:
    """Tests for phase completion detection."""

    def test_check_phase_complete_true(self, temp_change_dir, monkeypatch):
        """Returns True when phase_complete is true."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)

        state_file = temp_change_dir / "state.json"
        state_file.write_text(
            json.dumps({"phase": "PHASE0", "iteration": 1, "phase_complete": True})
        )

        st = OrchestratorState(change_dir=temp_change_dir)
        result = check_phase_complete(st)

        assert result is True

    def test_check_phase_complete_false(self, temp_change_dir, monkeypatch):
        """Returns False when phase_complete is false."""
        monkeypatch.chdir(temp_change_dir.parent.parent.parent)

        state_file = temp_change_dir / "state.json"
        state_file.write_text(json.dumps({"phase": "PHASE0", "phase_complete": False}))

        st = OrchestratorState(change_dir=temp_change_dir)
        result = check_phase_complete(st)

        assert result is False
