#!/usr/bin/env python3
"""
Unit tests for the osc (OpenSpec Change management) tool.

Tests all 5 domains: state, iterations, log, complete, validate
"""

import json
import sys
import io
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest

# Load the osc module from the file path (no .py extension)
_OSC_PATH = Path(__file__).parent.parent.parent / "resources/opencode/scripts/lib/osc"


def _load_osc_module():
    """Load the osc module from its file path."""
    osc_module = ModuleType("osc")
    osc_module.__file__ = str(_OSC_PATH)

    # Read and execute the module code
    with open(_OSC_PATH, "r") as f:
        code = f.read()

    exec(compile(code, _OSC_PATH, "exec"), osc_module.__dict__)
    return osc_module


osc = _load_osc_module()


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def change_dir(tmp_path):
    """Create a test change directory with required structure."""
    change_path = tmp_path / "openspec/changes/test-change"
    change_path.mkdir(parents=True)
    return change_path


@pytest.fixture
def archived_change_dir(tmp_path):
    """Create an archived test change directory."""
    archive_path = tmp_path / "openspec/changes/archive/2024-01-15-test-change"
    archive_path.mkdir(parents=True)
    return archive_path


@pytest.fixture
def change_dir_with_specs(tmp_path):
    """Create a test change directory with complete structure."""
    change_path = tmp_path / "openspec/changes/test-change"
    change_path.mkdir(parents=True)
    (change_path / "tasks.md").write_text("# Tasks")
    (change_path / "proposal.md").write_text("# Proposal")
    (change_path / "design.md").write_text("# Design")
    specs_dir = change_path / "specs"
    specs_dir.mkdir()
    (specs_dir / "spec.md").write_text("# Spec")
    return change_path


# =============================================================================
# Test Utility Functions
# =============================================================================


class TestFindChangeDir:
    """Tests for find_change_dir function."""

    def test_primary_location(self, change_dir, monkeypatch):
        """Test finding change in primary location."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        result = osc.find_change_dir("test-change")
        # Compare resolved paths since find_change_dir returns relative path
        assert result.resolve() == change_dir.resolve()

    def test_archived_location(self, tmp_path, monkeypatch):
        """Test finding change in archived location."""
        # Create the archived directory directly
        archive_path = tmp_path / "openspec/changes/archive/2024-01-15-test-change"
        archive_path.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        result = osc.find_change_dir("test-change")
        # Verify it found the archived location
        assert result.name == "2024-01-15-test-change"
        assert "archive" in str(result)

    def test_primary_takes_precedence(
        self, change_dir, archived_change_dir, monkeypatch
    ):
        """Test that primary location takes precedence over archived."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        result = osc.find_change_dir("test-change")
        # Compare resolved paths
        assert result.resolve() == change_dir.resolve()

    def test_not_found(self, tmp_path, monkeypatch, capsys):
        """Test error when change not found."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(SystemExit) as exc_info:
            osc.find_change_dir("nonexistent")
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        result = json.loads(captured.err)
        assert result["error"] == "change_not_found"
        assert "nonexistent" in result["change"]

    def test_multiple_archived_matches(self, tmp_path, monkeypatch):
        """Test that first archived match is returned when multiple exist."""
        monkeypatch.chdir(tmp_path)
        archive_dir = tmp_path / "openspec/changes/archive"
        archive_dir.mkdir(parents=True)
        # Create two archived versions
        archived1 = archive_dir / "2024-01-10-test-change"
        archived2 = archive_dir / "2024-01-15-test-change"
        archived1.mkdir()
        archived2.mkdir()
        result = osc.find_change_dir("test-change")
        # Should return first (sorted alphabetically)
        assert result.name.endswith("-test-change")


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_output(self, capsys):
        """Test JSON output to stdout."""
        osc.output({"test": "value", "number": 42})
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result == {"test": "value", "number": 42}

    def test_error(self, capsys):
        """Test error output to stderr."""
        with pytest.raises(SystemExit) as exc_info:
            osc.error("test_error", "Test message", extra="data")
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        result = json.loads(captured.err)
        assert result["error"] == "test_error"
        assert result["message"] == "Test message"
        assert result["extra"] == "data"

    def test_read_json_existing(self, tmp_path):
        """Test reading existing JSON file."""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key": "value"}')
        result = osc.read_json(json_file)
        assert result == {"key": "value"}

    def test_read_json_not_found(self, tmp_path):
        """Test reading non-existent JSON file returns empty dict."""
        json_file = tmp_path / "nonexistent.json"
        result = osc.read_json(json_file)
        assert result == {}

    def test_read_json_invalid(self, tmp_path, capsys):
        """Test reading invalid JSON file."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text("not valid json")
        with pytest.raises(SystemExit):
            osc.read_json(json_file)
        captured = capsys.readouterr()
        result = json.loads(captured.err)
        assert result["error"] == "invalid_json"

    def test_write_json(self, tmp_path):
        """Test writing JSON file."""
        json_file = tmp_path / "output.json"
        osc.write_json(json_file, {"key": "value"})
        assert json_file.exists()
        result = json.loads(json_file.read_text())
        assert result == {"key": "value"}

    def test_write_json_creates_parent_dirs(self, tmp_path):
        """Test that write_json creates parent directories."""
        json_file = tmp_path / "subdir/nested/output.json"
        osc.write_json(json_file, {"key": "value"})
        assert json_file.exists()

    def test_read_json_array_existing(self, tmp_path):
        """Test reading existing JSON array file."""
        json_file = tmp_path / "array.json"
        json_file.write_text('[{"id": 1}, {"id": 2}]')
        result = osc.read_json_array(json_file)
        assert result == [{"id": 1}, {"id": 2}]

    def test_read_json_array_not_found(self, tmp_path):
        """Test reading non-existent JSON array returns empty list."""
        json_file = tmp_path / "nonexistent.json"
        result = osc.read_json_array(json_file)
        assert result == []

    def test_read_json_array_invalid_format(self, tmp_path, capsys):
        """Test error when JSON file is not an array."""
        json_file = tmp_path / "not_array.json"
        json_file.write_text('{"key": "value"}')
        with pytest.raises(SystemExit):
            osc.read_json_array(json_file)
        captured = capsys.readouterr()
        result = json.loads(captured.err)
        assert result["error"] == "invalid_format"

    def test_append_to_json_array(self, tmp_path):
        """Test appending entry to JSON array."""
        json_file = tmp_path / "array.json"
        json_file.write_text('[{"id": 1}]')
        count = osc.append_to_json_array(json_file, {"id": 2})
        assert count == 2
        result = json.loads(json_file.read_text())
        assert len(result) == 2
        assert result[1] == {"id": 2}

    def test_get_timestamp(self):
        """Test timestamp format."""
        ts = osc.get_timestamp()
        assert isinstance(ts, str)
        # Check ISO format: YYYY-MM-DDTHH:MM:SSZ
        assert len(ts) == 20
        assert ts.endswith("Z")
        assert ts[4] == "-"
        assert ts[7] == "-"
        assert ts[10] == "T"


# =============================================================================
# Test State Domain
# =============================================================================


class TestStateGet:
    """Tests for state get command."""

    def test_get_state(self, change_dir, monkeypatch, capsys):
        """Test getting state."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "state.json").write_text('{"phase": "PHASE1", "iteration": 2}')

        class Args:
            change = "test-change"

        osc.cmd_state_get(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["phase"] == "PHASE1"
        assert result["iteration"] == 2
        assert result["phase_complete"] == False
        assert result["change"] == "test-change"

    def test_get_state_with_phase_complete(self, change_dir, monkeypatch, capsys):
        """Test getting state with phase_complete set."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "state.json").write_text(
            '{"phase": "PHASE2", "iteration": 3, "phase_complete": true}'
        )

        class Args:
            change = "test-change"

        osc.cmd_state_get(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["phase_complete"] == True

    def test_get_state_defaults(self, change_dir, monkeypatch, capsys):
        """Test getting state with missing fields uses defaults."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "state.json").write_text("{}")

        class Args:
            change = "test-change"

        osc.cmd_state_get(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["phase"] == "UNKNOWN"
        assert result["iteration"] == 0
        assert result["phase_complete"] == False

    def test_get_state_not_found(self, change_dir, monkeypatch, capsys):
        """Test error when state.json doesn't exist."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        class Args:
            change = "test-change"

        with pytest.raises(SystemExit):
            osc.cmd_state_get(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.err)
        assert result["error"] == "state_not_found"


class TestStateSetPhase:
    """Tests for state set-phase command."""

    def test_set_phase(self, change_dir, monkeypatch, capsys):
        """Test setting phase."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "state.json").write_text('{"phase": "PHASE0", "iteration": 1}')

        class Args:
            change = "test-change"
            phase = "PHASE1"

        osc.cmd_state_set_phase(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["success"] == True
        assert result["phase"] == "PHASE1"
        assert result["previous_phase"] == "PHASE0"

        # Verify file was updated
        state = json.loads((change_dir / "state.json").read_text())
        assert state["phase"] == "PHASE1"
        assert state["phase_name"] == "IMPLEMENTATION"

    def test_set_phase_invalid(self, change_dir, monkeypatch, capsys):
        """Test error when setting invalid phase."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "state.json").write_text('{"phase": "PHASE0"}')

        class Args:
            change = "test-change"
            phase = "INVALID_PHASE"

        with pytest.raises(SystemExit):
            osc.cmd_state_set_phase(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.err)
        assert result["error"] == "invalid_phase"

    def test_set_phase_state_not_found(self, change_dir, monkeypatch, capsys):
        """Test error when state.json doesn't exist."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        class Args:
            change = "test-change"
            phase = "PHASE1"

        with pytest.raises(SystemExit):
            osc.cmd_state_set_phase(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.err)
        assert result["error"] == "state_not_found"


class TestStateComplete:
    """Tests for state complete command."""

    def test_complete(self, change_dir, monkeypatch, capsys):
        """Test marking phase complete."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "state.json").write_text('{"phase": "PHASE1", "iteration": 1}')

        class Args:
            change = "test-change"

        osc.cmd_state_complete(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["success"] == True
        assert result["phase_complete"] == True

        # Verify file was updated
        state = json.loads((change_dir / "state.json").read_text())
        assert state["phase_complete"] == True

    def test_complete_state_not_found(self, change_dir, monkeypatch, capsys):
        """Test error when state.json doesn't exist."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        class Args:
            change = "test-change"

        with pytest.raises(SystemExit):
            osc.cmd_state_complete(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.err)
        assert result["error"] == "state_not_found"


class TestStateTransition:
    """Tests for state transition command."""

    def test_transition(self, change_dir, monkeypatch, capsys):
        """Test setting transition."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "state.json").write_text('{"phase": "PHASE2"}')

        class Args:
            change = "test-change"
            target = "PHASE1"
            reason = "artifacts_modified"
            details = None

        osc.cmd_state_transition(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["success"] == True
        assert result["transition"]["target"] == "PHASE1"
        assert result["transition"]["reason"] == "artifacts_modified"

        # Verify file was updated
        state = json.loads((change_dir / "state.json").read_text())
        assert state["transition"]["target"] == "PHASE1"
        assert state["phase_complete"] == True

    def test_transition_with_details(self, change_dir, monkeypatch, capsys):
        """Test setting transition with details."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "state.json").write_text('{"phase": "PHASE2"}')

        class Args:
            change = "test-change"
            target = "PHASE1"
            reason = "implementation_incorrect"
            details = "Need to fix the auth module"

        osc.cmd_state_transition(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["transition"]["details"] == "Need to fix the auth module"

    def test_transition_invalid_target(self, change_dir, monkeypatch, capsys):
        """Test error with invalid target phase."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "state.json").write_text('{"phase": "PHASE2"}')

        class Args:
            change = "test-change"
            target = "INVALID"
            reason = "artifacts_modified"
            details = None

        with pytest.raises(SystemExit):
            osc.cmd_state_transition(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.err)
        assert result["error"] == "invalid_target"

    def test_transition_invalid_reason(self, change_dir, monkeypatch, capsys):
        """Test error with invalid reason."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "state.json").write_text('{"phase": "PHASE2"}')

        class Args:
            change = "test-change"
            target = "PHASE1"
            reason = "invalid_reason"
            details = None

        with pytest.raises(SystemExit):
            osc.cmd_state_transition(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.err)
        assert result["error"] == "invalid_reason"


class TestStateClearTransition:
    """Tests for state clear-transition command."""

    def test_clear_transition(self, change_dir, monkeypatch, capsys):
        """Test clearing transition."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "state.json").write_text(
            '{"phase": "PHASE2", "transition": {"target": "PHASE1"}}'
        )

        class Args:
            change = "test-change"

        osc.cmd_state_clear_transition(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["success"] == True
        assert result["transition_cleared"] == True

        # Verify file was updated
        state = json.loads((change_dir / "state.json").read_text())
        assert "transition" not in state

    def test_clear_transition_no_existing(self, change_dir, monkeypatch, capsys):
        """Test clearing transition when none exists (no error)."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "state.json").write_text('{"phase": "PHASE2"}')

        class Args:
            change = "test-change"

        osc.cmd_state_clear_transition(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["success"] == True


# =============================================================================
# Test Iterations Domain
# =============================================================================


class TestIterationsGet:
    """Tests for iterations get command."""

    def test_get_empty(self, change_dir, monkeypatch, capsys):
        """Test getting iterations when none exist."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        class Args:
            change = "test-change"

        osc.cmd_iterations_get(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["count"] == 0
        assert result["iterations"] == []

    def test_get_with_data(self, change_dir, monkeypatch, capsys):
        """Test getting iterations with data."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "iterations.json").write_text(
            '[{"iteration": 1, "phase": "PHASE0"}, {"iteration": 2, "phase": "PHASE1"}]'
        )

        class Args:
            change = "test-change"

        osc.cmd_iterations_get(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["count"] == 2
        assert result["iterations"] == [1, 2]

    def test_get_archived(self, tmp_path, monkeypatch, capsys):
        """Test getting iterations from archived location."""
        # Create archived change directory
        archive_path = tmp_path / "openspec/changes/archive/2024-01-15-test-change"
        archive_path.mkdir(parents=True)
        (archive_path / "iterations.json").write_text(
            '[{"iteration": 5, "phase": "PHASE6"}]'
        )
        monkeypatch.chdir(tmp_path)

        class Args:
            change = "test-change"

        osc.cmd_iterations_get(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["count"] == 1
        assert result["iterations"] == [5]


class TestIterationsAppend:
    """Tests for iterations append command."""

    def test_append_cli_args(self, change_dir, monkeypatch, capsys):
        """Test appending iteration via CLI args."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        class Args:
            change = "test-change"
            phase = "PHASE1"
            iteration = 1
            summary = "Test iteration"
            status = None
            issues = None
            artifacts_modified = None
            decisions = None
            errors = None

        osc.cmd_iterations_append(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["success"] == True
        assert result["iteration"] == 1
        assert result["total_count"] == 1

        # Verify file was created
        iterations = json.loads((change_dir / "iterations.json").read_text())
        assert len(iterations) == 1
        assert iterations[0]["phase"] == "PHASE1"
        assert iterations[0]["summary"] == "Test iteration"
        assert "timestamp" in iterations[0]

    def test_append_with_json_options(self, change_dir, monkeypatch, capsys):
        """Test appending iteration with JSON options."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        class Args:
            change = "test-change"
            phase = "PHASE1"
            iteration = 1
            summary = None
            status = "completed"
            issues = '[{"type": "warning"}]'
            artifacts_modified = None
            decisions = None
            errors = None

        osc.cmd_iterations_append(Args())
        iterations = json.loads((change_dir / "iterations.json").read_text())
        assert iterations[0]["status"] == "completed"
        assert iterations[0]["issues"] == [{"type": "warning"}]

    def test_append_stdin(self, change_dir, monkeypatch, capsys):
        """Test appending iteration via stdin."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        stdin_data = '{"iteration": 3, "phase": "PHASE2", "summary": "From stdin"}'

        class Args:
            change = "test-change"
            phase = None
            iteration = None
            summary = None
            status = None
            issues = None
            artifacts_modified = None
            decisions = None
            errors = None

        # Mock stdin properly
        mock_stdin = io.StringIO(stdin_data)
        with patch("sys.stdin", mock_stdin):
            with patch.object(sys.stdin, "isatty", return_value=False):
                # Also need to mock select.select for Unix systems
                import select

                with patch.object(
                    select, "select", return_value=([mock_stdin], [], [])
                ):
                    osc.cmd_iterations_append(Args())

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["success"] == True
        assert result["iteration"] == 3

    def test_append_missing_required(self, change_dir, monkeypatch, capsys):
        """Test error when required fields are missing."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        class Args:
            change = "test-change"
            phase = None
            iteration = None
            summary = None
            status = None
            issues = None
            artifacts_modified = None
            decisions = None
            errors = None

        with pytest.raises(SystemExit):
            osc.cmd_iterations_append(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.err)
        assert result["error"] == "missing_field"

    def test_append_invalid_json_option(self, change_dir, monkeypatch, capsys):
        """Test error when JSON option has invalid JSON."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        class Args:
            change = "test-change"
            phase = "PHASE1"
            iteration = 1
            summary = None
            status = None
            issues = "not valid json"
            artifacts_modified = None
            decisions = None
            errors = None

        with pytest.raises(SystemExit):
            osc.cmd_iterations_append(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.err)
        assert result["error"] == "invalid_json"


# =============================================================================
# Test Log Domain
# =============================================================================


class TestLogGet:
    """Tests for log get command."""

    def test_get_empty(self, change_dir, monkeypatch, capsys):
        """Test getting log when empty."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        class Args:
            change = "test-change"

        osc.cmd_log_get(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["count"] == 0
        assert result["entries"] == []

    def test_get_with_data(self, change_dir, monkeypatch, capsys):
        """Test getting log with data."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "decision-log.json").write_text(
            '[{"entry": 1, "phase": "PHASE0", "iteration": 1, "summary": "First"}]'
        )

        class Args:
            change = "test-change"

        osc.cmd_log_get(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["count"] == 1
        assert len(result["entries"]) == 1


class TestLogAppend:
    """Tests for log append command."""

    def test_append_cli_args(self, change_dir, monkeypatch, capsys):
        """Test appending log entry via CLI args."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        class Args:
            change = "test-change"
            phase = "PHASE1"
            iteration = 2
            summary = "Test log entry"
            issues = None
            artifacts_modified = None
            next_steps = None
            decisions = None
            errors = None

        osc.cmd_log_append(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["success"] == True
        assert result["entry"] == 1
        assert result["phase"] == "PHASE1"
        assert result["iteration"] == 2

        # Verify file was created
        log = json.loads((change_dir / "decision-log.json").read_text())
        assert len(log) == 1
        assert log[0]["entry"] == 1
        assert log[0]["summary"] == "Test log entry"

    def test_append_stdin(self, change_dir, monkeypatch, capsys):
        """Test appending log entry via stdin."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        stdin_data = '{"phase": "PHASE2", "iteration": 3, "summary": "From stdin"}'

        class Args:
            change = "test-change"
            phase = None
            iteration = None
            summary = None
            issues = None
            artifacts_modified = None
            next_steps = None
            decisions = None
            errors = None

        # Mock stdin properly
        mock_stdin = io.StringIO(stdin_data)
        with patch("sys.stdin", mock_stdin):
            with patch.object(sys.stdin, "isatty", return_value=False):
                # Also need to mock select.select for Unix systems
                import select

                with patch.object(
                    select, "select", return_value=([mock_stdin], [], [])
                ):
                    osc.cmd_log_append(Args())

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["success"] == True

    def test_append_increments_entry_number(self, change_dir, monkeypatch, capsys):
        """Test that entry numbers increment correctly."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "decision-log.json").write_text(
            '[{"entry": 1, "phase": "PHASE0", "iteration": 1}]'
        )

        class Args:
            change = "test-change"
            phase = "PHASE1"
            iteration = 2
            summary = None
            issues = None
            artifacts_modified = None
            next_steps = None
            decisions = None
            errors = None

        osc.cmd_log_append(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["entry"] == 2

    def test_append_missing_required(self, change_dir, monkeypatch, capsys):
        """Test error when required fields are missing."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        class Args:
            change = "test-change"
            phase = None
            iteration = None
            summary = None
            issues = None
            artifacts_modified = None
            next_steps = None
            decisions = None
            errors = None

        with pytest.raises(SystemExit):
            osc.cmd_log_append(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.err)
        assert result["error"] == "missing_field"


# =============================================================================
# Test Complete Domain
# =============================================================================


class TestCompleteCheck:
    """Tests for complete check command."""

    def test_check_exists(self, change_dir, monkeypatch, capsys):
        """Test checking when complete.json exists."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "complete.json").write_text('{"status": "COMPLETE"}')

        class Args:
            change = "test-change"

        osc.cmd_complete_check(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["exists"] == True

    def test_check_not_exists(self, change_dir, monkeypatch, capsys):
        """Test checking when complete.json doesn't exist."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        class Args:
            change = "test-change"

        with pytest.raises(SystemExit) as exc_info:
            osc.cmd_complete_check(Args())
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["exists"] == False

    def test_check_invalid_json(self, change_dir, monkeypatch, capsys):
        """Test checking when complete.json has invalid JSON."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "complete.json").write_text("not valid json")

        class Args:
            change = "test-change"

        with pytest.raises(SystemExit):
            osc.cmd_complete_check(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["exists"] == False
        assert result.get("error") == "invalid_json"


class TestCompleteGet:
    """Tests for complete get command."""

    def test_get_complete(self, change_dir, monkeypatch, capsys):
        """Test getting complete status."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "complete.json").write_text(
            '{"status": "COMPLETE", "with_blocker": false}'
        )

        class Args:
            change = "test-change"

        osc.cmd_complete_get(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["status"] == "COMPLETE"
        assert result["with_blocker"] == False

    def test_get_blocked(self, change_dir, monkeypatch, capsys):
        """Test getting blocked status."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "complete.json").write_text(
            '{"status": "BLOCKED", "with_blocker": true, "blocker_reason": "Need approval"}'
        )

        class Args:
            change = "test-change"

        osc.cmd_complete_get(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["status"] == "BLOCKED"
        assert result["with_blocker"] == True
        assert result["blocker_reason"] == "Need approval"

    def test_get_not_found(self, change_dir, monkeypatch, capsys):
        """Test error when complete.json doesn't exist."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        class Args:
            change = "test-change"

        with pytest.raises(SystemExit):
            osc.cmd_complete_get(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.err)
        assert result["error"] == "complete_not_found"


class TestCompleteSet:
    """Tests for complete set command."""

    def test_set_complete(self, change_dir, monkeypatch, capsys):
        """Test setting complete status."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        class Args:
            change = "test-change"
            status = "COMPLETE"
            blocker_reason = None

        osc.cmd_complete_set(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["status"] == "COMPLETE"
        assert result["with_blocker"] == False

        # Verify file was created
        complete = json.loads((change_dir / "complete.json").read_text())
        assert complete["status"] == "COMPLETE"
        assert complete["with_blocker"] == False

    def test_set_blocked(self, change_dir, monkeypatch, capsys):
        """Test setting blocked status with reason."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        class Args:
            change = "test-change"
            status = "BLOCKED"
            blocker_reason = "Waiting for review"

        osc.cmd_complete_set(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["status"] == "BLOCKED"
        assert result["with_blocker"] == True
        assert result["blocker_reason"] == "Waiting for review"

        # Verify file was created
        complete = json.loads((change_dir / "complete.json").read_text())
        assert complete["blocker_reason"] == "Waiting for review"

    def test_set_default_status(self, change_dir, monkeypatch, capsys):
        """Test that default status is COMPLETE."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        class Args:
            change = "test-change"
            status = "COMPLETE"
            blocker_reason = None

        osc.cmd_complete_set(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["status"] == "COMPLETE"


# =============================================================================
# Test Validate Domain
# =============================================================================


class TestValidateJson:
    """Tests for validate json command."""

    def test_validate_json_valid(self, tmp_path, monkeypatch, capsys):
        """Test validating valid JSON file."""
        monkeypatch.chdir(tmp_path)
        json_file = tmp_path / "valid.json"
        json_file.write_text('{"key": "value"}')

        class Args:
            file = "valid.json"

        osc.cmd_validate_json(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["valid"] == True

    def test_validate_json_invalid(self, tmp_path, monkeypatch, capsys):
        """Test validating invalid JSON file."""
        monkeypatch.chdir(tmp_path)
        json_file = tmp_path / "invalid.json"
        json_file.write_text("not valid json")

        class Args:
            file = "invalid.json"

        with pytest.raises(SystemExit):
            osc.cmd_validate_json(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["valid"] == False
        assert len(result["errors"]) == 1

    def test_validate_json_not_found(self, tmp_path, monkeypatch, capsys):
        """Test validating non-existent JSON file."""
        monkeypatch.chdir(tmp_path)

        class Args:
            file = "nonexistent.json"

        with pytest.raises(SystemExit):
            osc.cmd_validate_json(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["valid"] == False
        assert "not found" in result["errors"][0]["message"].lower()


class TestValidateSkills:
    """Tests for validate skills command."""

    def test_validate_skills_missing(self, tmp_path, monkeypatch, capsys):
        """Test validation fails when skills are missing."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".opencode/skills").mkdir(parents=True)

        class Args:
            pass

        with pytest.raises(SystemExit):
            osc.cmd_validate_skills(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["valid"] == False
        assert len(result["errors"]) > 0

    def test_validate_skills_present(self, tmp_path, monkeypatch, capsys):
        """Test validation passes when all skills exist."""
        monkeypatch.chdir(tmp_path)
        skills_dir = tmp_path / ".opencode/skills"
        skills_dir.mkdir(parents=True)

        # Create all required skills
        for skill in osc.REQUIRED_SKILLS:
            skill_path = skills_dir / skill
            skill_path.mkdir()
            (skill_path / "SKILL.md").write_text(f"# {skill}")

        class Args:
            pass

        osc.cmd_validate_skills(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["valid"] == True


class TestValidateCommands:
    """Tests for validate commands command."""

    def test_validate_commands_missing(self, tmp_path, monkeypatch, capsys):
        """Test validation fails when commands are missing."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / ".opencode/commands").mkdir(parents=True)

        class Args:
            pass

        with pytest.raises(SystemExit):
            osc.cmd_validate_commands(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["valid"] == False

    def test_validate_commands_present(self, tmp_path, monkeypatch, capsys):
        """Test validation passes when all commands exist."""
        monkeypatch.chdir(tmp_path)
        commands_dir = tmp_path / ".opencode/commands"
        commands_dir.mkdir(parents=True)

        # Create all required commands
        for phase, cmd_name in osc.PHASE_COMMANDS.items():
            (commands_dir / f"{cmd_name}.md").write_text(f"# {cmd_name}")

        class Args:
            pass

        osc.cmd_validate_commands(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["valid"] == True


class TestValidateChangeDir:
    """Tests for validate change-dir command."""

    def test_validate_change_dir_valid(
        self, change_dir_with_specs, monkeypatch, capsys
    ):
        """Test validation passes for valid change directory."""
        monkeypatch.chdir(change_dir_with_specs.parent.parent.parent)

        class Args:
            change = "test-change"

        osc.cmd_validate_change_dir(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["valid"] == True

    def test_validate_change_dir_not_found(self, tmp_path, monkeypatch, capsys):
        """Test validation fails when change directory doesn't exist."""
        monkeypatch.chdir(tmp_path)

        class Args:
            change = "nonexistent"

        with pytest.raises(SystemExit):
            osc.cmd_validate_change_dir(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["valid"] == False

    def test_validate_change_dir_missing_files(self, change_dir, monkeypatch, capsys):
        """Test validation fails when required files are missing."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        class Args:
            change = "test-change"

        with pytest.raises(SystemExit):
            osc.cmd_validate_change_dir(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["valid"] == False
        # Should have errors for tasks.md, proposal.md, design.md, specs/
        assert len(result["errors"]) >= 3


class TestValidateArchive:
    """Tests for validate archive command."""

    def test_validate_archive_found(self, tmp_path, monkeypatch, capsys):
        """Test validation passes when archive is found."""
        # Create archived change directory
        archive_path = tmp_path / "openspec/changes/archive/2024-01-15-test-change"
        archive_path.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        class Args:
            change = "test-change"

        osc.cmd_validate_archive(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["valid"] == True
        assert "archive" in result

    def test_validate_archive_not_found(self, tmp_path, monkeypatch, capsys):
        """Test validation fails when archive not found."""
        monkeypatch.chdir(tmp_path)

        class Args:
            change = "test-change"

        with pytest.raises(SystemExit):
            osc.cmd_validate_archive(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["valid"] == False

    def test_validate_archive_multiple(self, tmp_path, monkeypatch, capsys):
        """Test validation fails when multiple archives found."""
        monkeypatch.chdir(tmp_path)
        archive_dir = tmp_path / "openspec/changes/archive"
        archive_dir.mkdir(parents=True)
        (archive_dir / "2024-01-10-test-change").mkdir()
        (archive_dir / "2024-01-15-test-change").mkdir()

        class Args:
            change = "test-change"

        with pytest.raises(SystemExit):
            osc.cmd_validate_archive(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["valid"] == False
        assert "Multiple archives" in result["errors"][0]["message"]


class TestValidateIterations:
    """Tests for validate iterations command."""

    def test_validate_iterations_valid(self, change_dir, monkeypatch, capsys):
        """Test validation passes for valid iterations.json."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "iterations.json").write_text('[{"iteration": 1}]')

        class Args:
            change = "test-change"

        osc.cmd_validate_iterations(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["valid"] == True

    def test_validate_iterations_not_found(self, change_dir, monkeypatch, capsys):
        """Test validation fails when iterations.json not found."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        class Args:
            change = "test-change"

        with pytest.raises(SystemExit):
            osc.cmd_validate_iterations(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["valid"] == False

    def test_validate_iterations_invalid_json(self, change_dir, monkeypatch, capsys):
        """Test validation fails when iterations.json is invalid."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "iterations.json").write_text("not valid json")

        class Args:
            change = "test-change"

        with pytest.raises(SystemExit):
            osc.cmd_validate_iterations(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["valid"] == False


class TestValidateCompletion:
    """Tests for validate completion command."""

    def test_validate_completion_valid(self, tmp_path, monkeypatch, capsys):
        """Test validation passes for complete archived change."""
        # Create archived change directory with all required files
        archive_path = tmp_path / "openspec/changes/archive/2024-01-15-test-change"
        archive_path.mkdir(parents=True)
        (archive_path / "state.json").write_text('{"phase": "PHASE6"}')
        (archive_path / "complete.json").write_text('{"status": "COMPLETE"}')
        (archive_path / "iterations.json").write_text("[]")
        (archive_path / "decision-log.json").write_text("[]")
        monkeypatch.chdir(tmp_path)

        class Args:
            change = "test-change"

        osc.cmd_validate_completion(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["valid"] == True

    def test_validate_completion_missing_files(self, tmp_path, monkeypatch, capsys):
        """Test validation fails when required files are missing."""
        # Create archived change directory without required files
        archive_path = tmp_path / "openspec/changes/archive/2024-01-15-test-change"
        archive_path.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)

        class Args:
            change = "test-change"

        with pytest.raises(SystemExit):
            osc.cmd_validate_completion(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["valid"] == False
        # Should have errors for state.json, complete.json, iterations.json, decision-log.json
        assert len(result["errors"]) >= 3

    def test_validate_completion_not_archived(self, change_dir, monkeypatch, capsys):
        """Test validation fails when change not archived."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "state.json").write_text('{"phase": "PHASE5"}')
        (change_dir / "complete.json").write_text('{"status": "COMPLETE"}')
        (change_dir / "iterations.json").write_text("[]")
        (change_dir / "decision-log.json").write_text("[]")

        class Args:
            change = "test-change"

        with pytest.raises(SystemExit):
            osc.cmd_validate_completion(Args())
        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["valid"] == False


# =============================================================================
# Test Argument Parser
# =============================================================================


class TestArgumentParser:
    """Tests for argument parsing."""

    def test_parser_version(self, capsys):
        """Test --version flag."""
        parser = osc.create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--version"])
        captured = capsys.readouterr()
        assert "osc" in captured.out
        assert osc.get_version() in captured.out

    def test_parser_no_args(self, capsys):
        """Test no args shows help when main() is called."""
        parser = osc.create_parser()
        args = parser.parse_args([])
        # parse_args doesn't exit, but args won't have func attribute
        assert not hasattr(args, "func")

    def test_parser_state_get(self):
        """Test parsing state get command."""
        parser = osc.create_parser()
        args = parser.parse_args(["state", "get", "test-change"])
        assert args.domain == "state"
        assert args.action == "get"
        assert args.change == "test-change"
        assert hasattr(args, "func")

    def test_parser_iterations_append(self):
        """Test parsing iterations append command with options."""
        parser = osc.create_parser()
        args = parser.parse_args(
            [
                "iterations",
                "append",
                "test-change",
                "--phase",
                "PHASE1",
                "--iteration",
                "2",
                "--summary",
                "Test summary",
            ]
        )
        assert args.domain == "iterations"
        assert args.action == "append"
        assert args.phase == "PHASE1"
        assert args.iteration == 2
        assert args.summary == "Test summary"

    def test_parser_complete_set(self):
        """Test parsing complete set command."""
        parser = osc.create_parser()
        args = parser.parse_args(
            [
                "complete",
                "set",
                "test-change",
                "BLOCKED",
                "--blocker-reason",
                "Waiting for approval",
            ]
        )
        assert args.status == "BLOCKED"
        assert args.blocker_reason == "Waiting for approval"


# =============================================================================
# Test Main Function
# =============================================================================


class TestMain:
    """Tests for main function."""

    def test_main_calls_func(self, change_dir, monkeypatch, capsys):
        """Test that main calls the correct function."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "state.json").write_text('{"phase": "PHASE1"}')

        with patch("sys.argv", ["osc", "state", "get", "test-change"]):
            osc.main()

        captured = capsys.readouterr()
        result = json.loads(captured.out)
        assert result["phase"] == "PHASE1"

    def test_main_no_func_exits(self, capsys):
        """Test that main exits when no func is set."""
        with patch("sys.argv", ["osc"]):
            with pytest.raises(SystemExit):
                osc.main()


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_state_transition_all_reasons(self, change_dir, monkeypatch, capsys):
        """Test all valid transition reasons."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        reasons = ["implementation_incorrect", "artifacts_modified", "retry_requested"]

        for reason in reasons:
            (change_dir / "state.json").write_text('{"phase": "PHASE2"}')

            # Create a simple namespace object for args
            from types import SimpleNamespace

            args = SimpleNamespace(
                change="test-change", target="PHASE1", reason=reason, details=None
            )

            osc.cmd_state_transition(args)
            captured = capsys.readouterr()
            result = json.loads(captured.out)
            assert result["transition"]["reason"] == reason

    def test_write_json_preserves_existing_data(self, tmp_path):
        """Test that write_json overwrites completely (atomic write)."""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"old": "data"}')
        osc.write_json(json_file, {"new": "data"})
        result = json.loads(json_file.read_text())
        assert result == {"new": "data"}
        assert "old" not in result

    def test_archived_change_dir_with_date_prefix(self, tmp_path, monkeypatch):
        """Test finding archived change with various date prefixes."""
        monkeypatch.chdir(tmp_path)
        archive_dir = tmp_path / "openspec/changes/archive"
        archive_dir.mkdir(parents=True)
        archived = archive_dir / "2024-12-31-my-change"
        archived.mkdir()

        result = osc.find_change_dir("my-change")
        # Compare resolved paths
        assert result.resolve() == archived.resolve()

    def test_phases_constant(self):
        """Test that PHASES constant is correct."""
        assert osc.PHASES == [
            "PHASE0",
            "PHASE1",
            "PHASE2",
            "PHASE3",
            "PHASE4",
            "PHASE5",
            "PHASE6",
        ]

    def test_phase_names_constant(self):
        """Test that PHASE_NAMES constant is correct."""
        assert osc.PHASE_NAMES["PHASE0"] == "ARTIFACT REVIEW"
        assert osc.PHASE_NAMES["PHASE1"] == "IMPLEMENTATION"
        assert osc.PHASE_NAMES["PHASE6"] == "ARCHIVE"

    def test_valid_transition_reasons_constant(self):
        """Test that VALID_TRANSITION_REASONS constant is correct."""
        assert "artifacts_modified" in osc.VALID_TRANSITION_REASONS
        assert "implementation_incorrect" in osc.VALID_TRANSITION_REASONS
        assert "retry_requested" in osc.VALID_TRANSITION_REASONS
