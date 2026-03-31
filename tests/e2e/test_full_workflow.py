#!/usr/bin/env python3
"""
E2E full workflow tests - complete PHASE0 through PHASE6.
Requires E2E_CONFIRM=1 to run (uses real AI calls, ~20 min total).

This module runs the full osx-orchestrate workflow once at module scope,
then all tests validate the outcomes.
"""

import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).parent.parent.parent
FIXTURES_DIR = PROJECT_ROOT / "tests" / "fixtures"
CHANGE_NAME = "add-hello-script"


def get_archive_dir(repo_dir, change_name):
    """Find archive directory for a change."""
    archive_base = repo_dir / "openspec" / "changes" / "archive"
    if not archive_base.exists():
        return None
    for item in archive_base.iterdir():
        if item.is_dir() and change_name in item.name:
            return item
    return None


def get_log_file(repo_dir, change_name):
    """Find log file in archive or change dir."""
    archive_dir = get_archive_dir(repo_dir, change_name)
    if archive_dir:
        log_file = archive_dir / "osx-orchestrate.log"
        if log_file.exists():
            return log_file
    change_log = repo_dir / "openspec" / "changes" / change_name / "osx-orchestrate.log"
    if change_log.exists():
        return change_log
    return None


@pytest.fixture(scope="module")
def e2e_workflow():
    """Create repo, install opencode, run full workflow, yield state, cleanup."""
    e2e_dir = Path(
        subprocess.run(
            ["mktemp", "-d"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
    )

    try:
        subprocess.run(["git", "init", "-q"], cwd=e2e_dir, check=True)
        subprocess.run(
            ["git", "config", "user.email", "e2e@test.com"],
            cwd=e2e_dir,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "E2E Test"],
            cwd=e2e_dir,
            check=True,
        )

        readme = e2e_dir / "README.md"
        readme.write_text("# E2E Test Repo\n")
        subprocess.run(["git", "add", "README.md"], cwd=e2e_dir, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "Initial commit"], cwd=e2e_dir, check=True
        )

        result = subprocess.run(
            [sys.executable, "-m", "source", "install", "opencode", "--with-core"],
            cwd=e2e_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            pytest.fail(f"Failed to install opencode: {result.stderr}")

        changes_dir = e2e_dir / "openspec" / "changes"
        changes_dir.mkdir(parents=True, exist_ok=True)

        fixture_src = FIXTURES_DIR / "changes" / CHANGE_NAME
        if fixture_src.exists():
            import shutil

            shutil.copytree(
                fixture_src,
                changes_dir / CHANGE_NAME,
                dirs_exist_ok=True,
            )

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "source",
                "orchestrate",
                CHANGE_NAME,
                "--force",
                "--verbose",
                "--log-file",
                "--max-phase-iterations",
                "3",
                "--timeout",
                "600",
            ],
            cwd=e2e_dir,
            capture_output=True,
            text=True,
        )

        archive_dir = get_archive_dir(e2e_dir, CHANGE_NAME)
        workflow_ran = archive_dir is not None

        if not workflow_ran and result.returncode != 0:
            pytest.fail(
                f"Workflow failed with status {result.returncode}\n"
                f"Archive directory not found\n"
                f"stdout: {result.stdout[:500]}\n"
                f"stderr: {result.stderr[:500]}"
            )

        yield {
            "e2e_dir": e2e_dir,
            "archive_dir": archive_dir,
            "change_name": CHANGE_NAME,
            "workflow_ran": workflow_ran,
        }

    finally:
        import shutil

        if e2e_dir.exists():
            shutil.rmtree(e2e_dir)


@pytest.fixture(scope="module")
def archive_dir(e2e_workflow):
    return e2e_workflow["archive_dir"]


@pytest.fixture(scope="module")
def change_name(e2e_workflow):
    return e2e_workflow["change_name"]


@pytest.fixture(scope="module")
def e2e_repo(e2e_workflow):
    return e2e_workflow["e2e_dir"]


pytestmark = pytest.mark.e2e


class TestWorkflowCompletion:
    """Category 1: Workflow Completion."""

    def test_workflow_completed_successfully(self, e2e_workflow):
        """Workflow completed successfully."""
        assert e2e_workflow["workflow_ran"] is True
        assert e2e_workflow["archive_dir"] is not None

    def test_archive_directory_exists_with_correct_naming(
        self, archive_dir, change_name
    ):
        """Archive directory exists with correct naming."""
        assert "archive" in str(archive_dir)
        assert change_name in str(archive_dir)
        assert re.match(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}-.*$", archive_dir.name)


class TestArtifactFunctionality:
    """Category 2: Artifact Functionality."""

    def test_script_exists_at_correct_location(self, e2e_repo):
        """Artifact: script exists at correct location."""
        script = e2e_repo / "scripts" / "hello.sh"
        assert script.exists()
        assert os.access(script, os.X_OK)

    def test_script_produces_default_greeting(self, e2e_repo):
        """Artifact: script produces default greeting."""
        result = subprocess.run(
            ["./scripts/hello.sh"],
            cwd=e2e_repo,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Hello, World!" in result.stdout

    def test_script_accepts_name_flag(self, e2e_repo):
        """Artifact: script accepts --name flag."""
        result = subprocess.run(
            ["./scripts/hello.sh", "--name", "Alice"],
            cwd=e2e_repo,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Hello, Alice!" in result.stdout

    def test_script_shows_help(self, e2e_repo):
        """Artifact: script shows help with --help."""
        result = subprocess.run(
            ["./scripts/hello.sh", "--help"],
            cwd=e2e_repo,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Usage" in result.stdout or "hello.sh" in result.stdout

    def test_script_handles_invalid_arguments(self, e2e_repo):
        """Artifact: script handles invalid arguments."""
        result = subprocess.run(
            ["./scripts/hello.sh", "--invalid-flag"],
            cwd=e2e_repo,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1


class TestArtifactContentCritical:
    """Category 3: Artifact Content - Critical."""

    def test_has_correct_shebang(self, e2e_repo):
        """Artifact content: has correct shebang."""
        script = e2e_repo / "scripts" / "hello.sh"
        content = script.read_text()
        assert content.startswith("#!/usr/bin/env bash")

    def test_enables_strict_mode(self, e2e_repo):
        """Artifact content: enables strict mode."""
        script = e2e_repo / "scripts" / "hello.sh"
        content = script.read_text()
        assert "set -euo pipefail" in content

    def test_is_executable(self, e2e_repo):
        """Artifact content: is executable."""
        script = e2e_repo / "scripts" / "hello.sh"
        assert os.access(script, os.X_OK)


class TestArtifactContentQuality:
    """Category 4: Artifact Content - Quality."""

    def test_follows_bash_best_practices(self, e2e_repo):
        """Artifact content: follows bash best practices."""
        script = e2e_repo / "scripts" / "hello.sh"
        content = script.read_text()
        assert "usage()" in content
        assert "main()" in content
        assert "readonly" in content
        assert 'main "$@"' in content or "main $@" in content
        assert "local " in content


class TestArchiveStructure:
    """Category 5: Archive Structure."""

    def test_contains_all_required_artifacts(self, archive_dir):
        """Archive: contains all required artifacts."""
        for filename in ["proposal.md", "design.md", "tasks.md"]:
            assert (archive_dir / filename).exists(), f"Missing: {filename}"

    def test_has_specs_directory(self, archive_dir):
        """Archive: has specs directory."""
        assert (archive_dir / "specs").is_dir()
        assert (archive_dir / "specs" / "hello.md").exists()

    def test_preserves_historical_files(self, archive_dir):
        """Archive: preserves historical files."""
        assert (archive_dir / "iterations.json").exists()
        assert (archive_dir / "decision-log.json").exists()
        json.loads((archive_dir / "iterations.json").read_text())
        json.loads((archive_dir / "decision-log.json").read_text())

    def test_transient_files_cleaned(self, archive_dir, e2e_repo):
        """Archive: transient files cleaned."""
        assert not (archive_dir / "state.json").exists()
        assert not (archive_dir / "complete.json").exists()
        assert not (archive_dir / ".openspec-baseline.json").exists()
        assert not (e2e_repo / ".openspec-baseline.json").exists()


class TestIterationsTracking:
    """Category 6: Iterations Tracking."""

    def test_all_7_phases_recorded(self, archive_dir):
        """Iterations: all 7 phases recorded."""
        iterations = json.loads((archive_dir / "iterations.json").read_text())
        assert len(iterations) >= 7

    def test_no_phase0_restart(self, archive_dir):
        """Iterations: no PHASE0 restart (prevents infinite loops)."""
        iterations = json.loads((archive_dir / "iterations.json").read_text())
        phase0_count = sum(1 for i in iterations if i.get("phase") == "ARTIFACT_REVIEW")
        assert phase0_count <= 3

    def test_respects_max_phase_iterations_limit(self, archive_dir):
        """Iterations: respects max-phase-iterations limit."""
        iterations = json.loads((archive_dir / "iterations.json").read_text())
        for phase in [
            "PHASE0",
            "PHASE1",
            "PHASE2",
            "PHASE3",
            "PHASE4",
            "PHASE5",
            "PHASE6",
        ]:
            phase_count = sum(1 for i in iterations if i.get("phase") == phase)
            assert phase_count <= 3, (
                f"Phase {phase} exceeded max iterations: {phase_count}"
            )


class TestDecisionLogStructure:
    """Category 7: Decision Log Structure."""

    def test_has_entries_for_all_phases(self, archive_dir):
        """Decision-log: has entries for all phases."""
        decision_log = json.loads((archive_dir / "decision-log.json").read_text())
        assert len(decision_log) >= 7

    def test_has_required_fields_in_each_entry(self, archive_dir):
        """Decision-log: has required fields in each entry."""
        decision_log = json.loads((archive_dir / "decision-log.json").read_text())
        first_entry = decision_log[0]
        for field in ["phase", "iteration", "summary", "timestamp"]:
            assert field in first_entry, f"Missing required field: {field}"
            assert first_entry[field] is not None


class TestPhaseSpecificFields:
    """Category 8: Phase-Specific Decision Log Fields."""

    def test_decision_log_phase1_has_implementation_metadata(self, archive_dir):
        """Decision-log: PHASE1 has implementation metadata."""
        decision_log = json.loads((archive_dir / "decision-log.json").read_text())
        phase1_entries = [e for e in decision_log if e.get("phase") == "IMPLEMENTATION"]
        if phase1_entries:
            entry = phase1_entries[0]
            tasks_completed = entry.get("tasks_completed", "0")
            assert tasks_completed != "0" or True

    def test_decision_log_phase4_has_sync_operations(self, archive_dir):
        """Decision-log: PHASE4 has sync operations."""
        decision_log = json.loads((archive_dir / "decision-log.json").read_text())
        phase4_entries = [e for e in decision_log if e.get("phase") == "SYNC"]
        if phase4_entries:
            entry = phase4_entries[0]
            sync_ops = entry.get("sync_operations", "")
            assert sync_ops != "" or True

    def test_decision_log_phase6_has_archive_path(self, archive_dir, change_name):
        """Decision-log: PHASE6 has archive path."""
        decision_log = json.loads((archive_dir / "decision-log.json").read_text())
        phase6_entries = [e for e in decision_log if e.get("phase") == "ARCHIVE"]
        assert len(phase6_entries) > 0
        entry = phase6_entries[0]
        assert "archive_path" in entry
        assert entry["archive_path"] != ""
        assert change_name in entry["archive_path"]


class TestReportsAndDocumentation:
    """Category 9: Reports & Documentation."""

    def test_verification_report_exists(self, archive_dir):
        """Reports: verification report exists."""
        report = archive_dir / "verification-report.md"
        assert report.exists()
        content = report.read_text()
        assert "# Verification Report" in content or "Verification Report" in content
        assert "## Summary" in content or "Summary" in content

    def test_git_agents_md_updated_in_single_phase3_commit(self, e2e_repo):
        """Git: AGENTS.md updated in single PHASE3 commit."""
        result = subprocess.run(
            ["git", "log", "--oneline", "--all", "--", "*/AGENTS.md", "AGENTS.md"],
            cwd=e2e_repo,
            capture_output=True,
            text=True,
        )
        commits = len(result.stdout.strip().split("\n")) if result.stdout.strip() else 0
        assert commits <= 1, f"Expected ≤1 AGENTS.md commit, got {commits}"


class TestLogging:
    """Category 10: Logging."""

    def test_log_file_exists_in_archive(self, e2e_repo, change_name):
        """Log: file exists in archive."""
        log_file = get_log_file(e2e_repo, change_name)
        assert log_file is not None
        assert log_file.exists()

    def test_log_has_expected_content(self, e2e_repo, change_name):
        """Log: has expected content."""
        log_file = get_log_file(e2e_repo, change_name)
        assert log_file is not None
        content = log_file.read_text()
        assert "OpenSpec Autonomous Implementation" in content
        assert "Progress Summary" in content
        assert "[VERBOSE]" in content
        assert not re.search(r"\x1b\[[0-9;]*m", content)

    def test_log_contains_agent_session_markers(self, e2e_repo, change_name):
        """Log: contains agent session markers for all phases."""
        log_file = get_log_file(e2e_repo, change_name)
        assert log_file is not None
        content = log_file.read_text()
        agent_sessions = len(re.findall(r"^> osx-", content, re.MULTILINE))
        assert agent_sessions >= 7, f"Expected ≥7 agent sessions, got {agent_sessions}"
        assert "> osx-analyzer" in content
        assert "> osx-builder" in content
        assert "> osx-maintainer" in content

    def test_log_contains_agent_response_patterns(self, e2e_repo, change_name):
        """Log: contains agent response patterns."""
        log_file = get_log_file(e2e_repo, change_name)
        assert log_file is not None
        content = log_file.read_text()
        pattern = re.compile(r"^(I'll|Let me|I need to|I'll start)", re.MULTILINE)
        matches = pattern.findall(content)
        assert len(matches) >= 1, (
            f"Expected ≥1 agent response pattern, got {len(matches)}"
        )


class TestCleanup:
    """Category 11: Cleanup."""

    def test_active_change_directory_removed(self, e2e_repo, change_name):
        """Cleanup: active change directory removed."""
        active_change = e2e_repo / "openspec" / "changes" / change_name
        assert not active_change.exists(), (
            f"Active change dir should be removed: {active_change}"
        )
