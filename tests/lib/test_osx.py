#!/usr/bin/env python3
"""
Unit tests for the osx library (source.lib.osx) and its CLI surface
(source.osx_cli).

The library is tested in-process by importing and calling functions
directly. The CLI is tested by invoking `osx_cli.osx_app` via
CliRunner.
"""

import json
import subprocess

import pytest
from typer.testing import CliRunner

from source.lib import osx
from source.osx_cli import osx_app

runner = CliRunner()


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


@pytest.mark.unit
class TestFindChangeDir:
    """Tests for the library _find_change_dir function (raises OSXError)."""

    def test_primary_location(self, change_dir, monkeypatch):
        """Test finding change in primary location."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        result = osx._find_change_dir("test-change")
        assert result.resolve() == change_dir.resolve()

    def test_archived_location(self, tmp_path, monkeypatch):
        """Test finding change in archived location."""
        archive_path = tmp_path / "openspec/changes/archive/2024-01-15-test-change"
        archive_path.mkdir(parents=True)
        monkeypatch.chdir(tmp_path)
        result = osx._find_change_dir("test-change")
        assert result.name == "2024-01-15-test-change"
        assert "archive" in str(result)

    def test_primary_takes_precedence(
        self, change_dir, archived_change_dir, monkeypatch
    ):
        """Test that primary location takes precedence over archived."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        result = osx._find_change_dir("test-change")
        assert result.resolve() == change_dir.resolve()

    def test_not_found(self, tmp_path, monkeypatch):
        """Test error when change not found."""
        monkeypatch.chdir(tmp_path)
        with pytest.raises(osx.OSXError) as exc_info:
            osx._find_change_dir("nonexistent")
        assert exc_info.value.code == "change_not_found"
        assert exc_info.value.context["change"] == "nonexistent"

    def test_multiple_archived_matches(self, tmp_path, monkeypatch):
        """Test that first archived match is returned when multiple exist."""
        monkeypatch.chdir(tmp_path)
        archive_dir = tmp_path / "openspec/changes/archive"
        archive_dir.mkdir(parents=True)
        archived1 = archive_dir / "2024-01-10-test-change"
        archived2 = archive_dir / "2024-01-15-test-change"
        archived1.mkdir()
        archived2.mkdir()
        result = osx._find_change_dir("test-change")
        assert result.name.endswith("-test-change")


@pytest.mark.unit
class TestLibraryIO:
    """Tests for library IO helpers (_read_json, _read_json_array, write_json)."""

    def test_read_json_existing(self, tmp_path):
        """Test reading existing JSON file."""
        json_file = tmp_path / "test.json"
        json_file.write_text('{"key": "value"}')
        result = osx._read_json(json_file)
        assert result == {"key": "value"}

    def test_read_json_not_found(self, tmp_path):
        """Test reading non-existent JSON file returns empty dict."""
        json_file = tmp_path / "nonexistent.json"
        result = osx._read_json(json_file)
        assert result == {}

    def test_read_json_invalid(self, tmp_path):
        """Test reading invalid JSON file raises OSXError."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text("not valid json")
        with pytest.raises(osx.OSXError) as exc_info:
            osx._read_json(json_file)
        assert exc_info.value.code == "invalid_json"

    def test_write_json(self, tmp_path):
        """Test writing JSON file."""
        json_file = tmp_path / "output.json"
        osx.write_json(json_file, {"key": "value"})
        assert json_file.exists()
        result = json.loads(json_file.read_text())
        assert result == {"key": "value"}

    def test_write_json_creates_parent_dirs(self, tmp_path):
        """Test that write_json creates parent directories."""
        json_file = tmp_path / "subdir/nested/output.json"
        osx.write_json(json_file, {"key": "value"})
        assert json_file.exists()

    def test_read_json_array_existing(self, tmp_path):
        """Test reading existing JSON array file."""
        json_file = tmp_path / "array.json"
        json_file.write_text('[{"id": 1}, {"id": 2}]')
        result = osx._read_json_array(json_file)
        assert result == [{"id": 1}, {"id": 2}]

    def test_read_json_array_not_found(self, tmp_path):
        """Test reading non-existent JSON array returns empty list."""
        json_file = tmp_path / "nonexistent.json"
        result = osx._read_json_array(json_file)
        assert result == []

    def test_read_json_array_invalid_format(self, tmp_path):
        """Test error when JSON file is not an array."""
        json_file = tmp_path / "not_array.json"
        json_file.write_text('{"key": "value"}')
        with pytest.raises(osx.OSXError) as exc_info:
            osx._read_json_array(json_file)
        assert exc_info.value.code == "invalid_format"

    def test_append_to_json_array(self, tmp_path):
        """Test appending entry to JSON array."""
        json_file = tmp_path / "array.json"
        json_file.write_text('[{"id": 1}]')
        count = osx.append_to_json_array(json_file, {"id": 2})
        assert count == 2
        result = json.loads(json_file.read_text())
        assert len(result) == 2
        assert result[1] == {"id": 2}

    def test_get_timestamp(self):
        """Test timestamp format."""
        ts = osx.get_timestamp()
        assert isinstance(ts, str)
        assert len(ts) == 20
        assert ts.endswith("Z")
        assert ts[4] == "-"
        assert ts[7] == "-"
        assert ts[10] == "T"


@pytest.mark.unit
class TestStateGet:
    """Tests for state get command."""

    def test_get_state(self, change_dir, monkeypatch):
        """Test getting state."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "state.json").write_text('{"phase": "PHASE1", "iteration": 2}')

        result = runner.invoke(osx_app, ["state", "get", "test-change"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        result_data = json.loads(result.output)
        assert result_data["phase"] == "PHASE1"
        assert result_data["iteration"] == 2
        assert result_data["phase_complete"] == False
        assert result_data["change"] == "test-change"

    def test_get_state_with_phase_complete(self, change_dir, monkeypatch):
        """Test getting state with phase_complete set."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "state.json").write_text(
            '{"phase": "PHASE2", "iteration": 3, "phase_complete": true}'
        )

        result = runner.invoke(osx_app, ["state", "get", "test-change"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        result_data = json.loads(result.output)
        assert result_data["phase_complete"] == True

    def test_get_state_defaults(self, change_dir, monkeypatch):
        """Test getting state with missing fields uses defaults."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "state.json").write_text("{}")

        result = runner.invoke(osx_app, ["state", "get", "test-change"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        result_data = json.loads(result.output)
        assert result_data["phase"] == "UNKNOWN"
        assert result_data["iteration"] == 0
        assert result_data["phase_complete"] == False

    def test_get_state_not_found(self, change_dir, monkeypatch):
        """Test error when state.json doesn't exist."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        result = runner.invoke(osx_app, ["state", "get", "test-change"])
        assert result.exit_code != 0


@pytest.mark.unit
class TestPhase:
    """Tests for phase command."""

    def test_phase_current(self, change_dir, monkeypatch):
        """Test getting current phase."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "state.json").write_text('{"phase": "PHASE2", "iteration": 3}')

        result = runner.invoke(osx_app, ["phase", "current", "test-change"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        result_data = json.loads(result.output)
        assert result_data["phase"] == "PHASE2"
        assert result_data["next"] == "PHASE3"
        assert result_data["iteration"] == 3

    def test_phase_next(self, change_dir, monkeypatch):
        """Test getting next phase."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "state.json").write_text('{"phase": "PHASE1"}')

        result = runner.invoke(osx_app, ["phase", "next", "test-change"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        result_data = json.loads(result.output)
        assert result_data["next"] == "PHASE2"

    def test_phase_advance(self, change_dir, monkeypatch):
        """Test advancing to next phase."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "state.json").write_text('{"phase": "PHASE0", "iteration": 1}')

        result = runner.invoke(osx_app, ["phase", "advance", "test-change"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        result_data = json.loads(result.output)
        assert result_data["phase"] == "PHASE1"
        assert result_data["previous"] == "PHASE0"
        assert result_data["iteration"] == 1

        state = json.loads((change_dir / "state.json").read_text())
        assert state["phase"] == "PHASE1"
        assert state["iteration"] == 1
        assert state["phase_complete"] == False


@pytest.mark.unit
class TestIterations:
    """Tests for iterations command."""

    def test_iterations_get_empty(self, change_dir, monkeypatch):
        """Test getting iterations when none exist."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        result = runner.invoke(osx_app, ["iterations", "get", "test-change"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        result_data = json.loads(result.output)
        assert result_data["count"] == 0
        assert result_data["iterations"] == []

    def test_iterations_append(self, change_dir, monkeypatch):
        """Test appending iteration."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        result = runner.invoke(
            osx_app,
            [
                "iterations",
                "append",
                "test-change",
                "--phase",
                "PHASE1",
                "--iteration",
                "1",
                "--summary",
                "Test",
            ],
        )
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        result_data = json.loads(result.output)
        assert result_data["success"] == True
        assert result_data["iteration"] == 1


@pytest.mark.unit
class TestLog:
    """Tests for log command."""

    def test_log_get_empty(self, change_dir, monkeypatch):
        """Test getting log when empty."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        result = runner.invoke(osx_app, ["log", "get", "test-change"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        result_data = json.loads(result.output)
        assert result_data["count"] == 0
        assert result_data["entries"] == []

    def test_log_append_rejects_oversized_summary(self, change_dir, monkeypatch):
        """Shell backtick expansion can dump the whole env into --summary.

        The lib must reject summaries that exceed LOG_TEXT_FIELD_MAX_LENGTH
        before they reach the JSON file, so the agent gets a clear error
        and the decision log stays small.
        """
        monkeypatch.chdir(change_dir.parent.parent.parent)
        oversized = "x" * (osx.LOG_TEXT_FIELD_MAX_LENGTH + 1)

        result = runner.invoke(
            osx_app,
            [
                "log",
                "append",
                "test-change",
                "--phase",
                "ARTIFACT_REVIEW",
                "--iteration",
                "1",
                "--summary",
                oversized,
            ],
        )
        assert result.exit_code == 1
        assert "input_too_long" in result.output
        assert not (change_dir / "decision-log.json").exists()

    def test_log_append_rejects_zsh_env_dump_fingerprint(
        self, change_dir, monkeypatch
    ):
        """`local` backtick-expanded in zsh produces 'integer 10 readonly ...'.

        Any string containing that fingerprint (or the other zsh dump
        markers) must be rejected with a clear `input_tainted` error
        rather than written to the decision log.
        """
        monkeypatch.chdir(change_dir.parent.parent.parent)
        tainted = "Reviewed all 4 artifacts. Use the `local` keyword.\n"
        tainted += "integer 10 readonly !=0\ninteger 10 readonly '#'=0\n"
        tainted += "BATS_TMPDIR=/tmp\n"

        result = runner.invoke(
            osx_app,
            [
                "log",
                "append",
                "test-change",
                "--phase",
                "ARTIFACT_REVIEW",
                "--iteration",
                "1",
                "--summary",
                tainted,
            ],
        )
        assert result.exit_code == 1
        assert "input_tainted" in result.output
        assert not (change_dir / "decision-log.json").exists()

    def test_log_append_rejects_oversized_next_steps(self, change_dir, monkeypatch):
        """--next-steps is also free-text and must be bounded."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        oversized = "y" * (osx.LOG_TEXT_FIELD_MAX_LENGTH + 1)

        result = runner.invoke(
            osx_app,
            [
                "log",
                "append",
                "test-change",
                "--phase",
                "ARTIFACT_REVIEW",
                "--iteration",
                "1",
                "--next-steps",
                oversized,
            ],
        )
        assert result.exit_code == 1
        assert "input_too_long" in result.output
        assert not (change_dir / "decision-log.json").exists()

    def test_log_append_accepts_normal_summary(self, change_dir, monkeypatch):
        """Normal-sized summaries (even with apostrophes) must succeed."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        result = runner.invoke(
            osx_app,
            [
                "log",
                "append",
                "test-change",
                "--phase",
                "ARTIFACT_REVIEW",
                "--iteration",
                "1",
                "--summary",
                "Reviewed all 4 artifacts. Found 0 critical, 1 warning.",
            ],
        )
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert (change_dir / "decision-log.json").exists()


@pytest.mark.unit
class TestComplete:
    """Tests for complete command."""

    def test_complete_check_exists(self, change_dir, monkeypatch):
        """Test checking when complete.json exists."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "complete.json").write_text('{"status": "COMPLETE"}')

        result = runner.invoke(osx_app, ["complete", "check", "test-change"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        result_data = json.loads(result.output)
        assert result_data["exists"] == True

    def test_complete_check_not_exists(self, change_dir, monkeypatch):
        """Test checking when complete.json doesn't exist."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        result = runner.invoke(osx_app, ["complete", "check", "test-change"])
        assert result.exit_code == 1

    def test_complete_set(self, change_dir, monkeypatch):
        """Test setting complete status."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        result = runner.invoke(
            osx_app, ["complete", "set", "test-change", "COMPLETE"]
        )
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        result_data = json.loads(result.output)
        assert result_data["status"] == "COMPLETE"
        assert result_data["with_blocker"] == False


@pytest.mark.unit
class TestCtx:
    """Tests for ctx command."""

    def test_ctx_get_basic(self, change_dir, monkeypatch):
        """Test getting basic context."""
        monkeypatch.chdir(change_dir.parent.parent.parent)
        (change_dir / "state.json").write_text(
            '{"phase": "PHASE1", "iteration": 2, "phase_complete": false}'
        )

        result = runner.invoke(osx_app, ["ctx", "get", "test-change"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        result_data = json.loads(result.output)
        assert result_data["change"] == "test-change"
        assert result_data["state"]["phase"] == "PHASE1"
        assert result_data["state"]["iteration"] == 2
        assert "artifacts" in result_data
        assert "history" in result_data


@pytest.mark.unit
class TestGit:
    """Tests for git command."""

    def test_git_get_clean(self, change_dir, monkeypatch):
        """Test getting git status when clean."""
        monkeypatch.chdir(change_dir.parent.parent.parent)

        result = runner.invoke(osx_app, ["git", "get", "test-change"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        result_data = json.loads(result.output)
        assert "modified" in result_data
        assert "added" in result_data
        assert "untracked" in result_data
        assert "clean" in result_data


@pytest.mark.unit
class TestValidate:
    """Tests for validate command."""

    def test_validate_json_valid(self, tmp_path, monkeypatch):
        """Test validating valid JSON file."""
        json_file = tmp_path / "valid.json"
        json_file.write_text('{"key": "value"}')
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(osx_app, ["validate", "json", "valid.json"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        result_data = json.loads(result.output)
        assert result_data["valid"] == True

    def test_validate_json_invalid(self, tmp_path, monkeypatch):
        """Test validating invalid JSON file."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text("not valid json")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(osx_app, ["validate", "json", "invalid.json"])
        assert result.exit_code == 1

    def test_validate_skills_present(self, tmp_path, monkeypatch):
        """Test validation passes when all skills exist."""
        monkeypatch.chdir(tmp_path)
        skills_dir = tmp_path / ".opencode/skills"
        skills_dir.mkdir(parents=True)

        for skill in osx.REQUIRED_SKILLS + osx.REQUIRED_CORE_SKILLS:
            skill_path = skills_dir / skill
            skill_path.mkdir()
            (skill_path / "SKILL.md").write_text(f"# {skill}")

        result = runner.invoke(osx_app, ["validate", "skills"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        result_data = json.loads(result.output)
        assert result_data["valid"] == True

    def test_validate_commands_present(self, tmp_path, monkeypatch):
        """Test validation passes when all commands exist."""
        monkeypatch.chdir(tmp_path)
        commands_dir = tmp_path / ".opencode/commands"
        commands_dir.mkdir(parents=True)

        for phase, cmd_name in osx.PHASE_COMMANDS.items():
            (commands_dir / f"{cmd_name}.md").write_text(f"# {cmd_name}")

        result = runner.invoke(osx_app, ["validate", "commands"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        result_data = json.loads(result.output)
        assert result_data["valid"] == True


@pytest.mark.unit
class TestBaseline:
    """Tests for baseline command."""

    def test_baseline_record_and_get(self, tmp_path, monkeypatch):
        """Test recording and getting baseline."""
        monkeypatch.chdir(tmp_path)
        subprocess.run(["git", "init", "-q"], check=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], check=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True)
        (tmp_path / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "README.md"], check=True)
        subprocess.run(["git", "commit", "-q", "-m", "Initial"], check=True)

        result = runner.invoke(osx_app, ["baseline", "record"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        result_data = json.loads(result.output)
        assert result_data["commit"] is not None
        assert result_data["branch"] is not None

        result2 = runner.invoke(osx_app, ["baseline", "get"])
        assert result2.exit_code == 0, (
            f"Output: {result2.output}, Exception: {result2.exception}"
        )
        result_data2 = json.loads(result2.output)
        assert result_data2["commit"] is not None
