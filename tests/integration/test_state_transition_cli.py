#!/usr/bin/env python3
"""
Tests for the osx state CLI surface — locked-in contract for `state transition`.

The `state transition` action previously took positional args (change, phase,
target, reason, details) but the implementation bound the args wrong: it ignored
the second positional. This file pins the new behavior: transition takes named
options `--target`, `--reason`, `--details`, requires `--target` AND `--reason`.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def change_dir(tmp_path: Path) -> Path:
    """Create a minimal openspec/changes/<name> with state.json ready for transition."""
    change = tmp_path / "openspec" / "changes" / "test-change"
    change.mkdir(parents=True)
    (change / "state.json").write_text(
        json.dumps(
            {
                "phase": "PHASE2",
                "iteration": 1,
                "phase_complete": True,
                "phase_iterations": {"PHASE2": 1},
            }
        )
    )
    return change


def _run_osx(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    """Invoke `python -m source osx …` against the test cwd."""
    return subprocess.run(
        [sys.executable, "-m", "source", "osx", *args],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        check=False,
    )


@pytest.mark.integration
class TestStateTransitionNamedOptions:
    def test_transition_with_target_and_reason_writes_state(
        self, change_dir: Path, tmp_path: Path
    ) -> None:
        result = _run_osx(
            [
                "state",
                "transition",
                "test-change",
                "--target",
                "PHASE1",
                "--reason",
                "artifacts_modified",
            ],
            cwd=tmp_path,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads((change_dir / "state.json").read_text())
        assert data["transition"]["target"] == "PHASE1"
        assert data["transition"]["reason"] == "artifacts_modified"
        assert "details" not in data["transition"]

    def test_transition_with_details_passes_through(
        self, change_dir: Path, tmp_path: Path
    ) -> None:
        result = _run_osx(
            [
                "state",
                "transition",
                "test-change",
                "--target",
                "PHASE1",
                "--reason",
                "artifacts_modified",
                "--details",
                "Spec requirement 3.2 updated",
            ],
            cwd=tmp_path,
        )
        assert result.returncode == 0, f"stderr: {result.stderr}"
        data = json.loads((change_dir / "state.json").read_text())
        assert data["transition"]["details"] == "Spec requirement 3.2 updated"

    def test_transition_without_target_fails(self, change_dir: Path, tmp_path: Path) -> None:
        result = _run_osx(
            [
                "state",
                "transition",
                "test-change",
                "--reason",
                "artifacts_modified",
            ],
            cwd=tmp_path,
        )
        assert result.returncode == 1
        payload = json.loads(result.stderr)
        assert payload["error"] == "missing_field"
        assert "target" in payload

    def test_transition_without_reason_fails(self, change_dir: Path, tmp_path: Path) -> None:
        result = _run_osx(
            [
                "state",
                "transition",
                "test-change",
                "--target",
                "PHASE1",
            ],
            cwd=tmp_path,
        )
        assert result.returncode == 1
        payload = json.loads(result.stderr)
        assert payload["error"] == "missing_field"
        assert "reason" in payload

    def test_positional_target_no_longer_accepted(
        self, change_dir: Path, tmp_path: Path
    ) -> None:
        """
        The old (broken) form `state transition <change> PHASE1 artifacts_modified "details"`
        must NOT silently mis-bind. After the hard-break the command fails
        (either Typer exit 2 for unexpected positional, or our missing_field
        exit 1). State file must NOT be mutated.
        """
        result = _run_osx(
            [
                "state",
                "transition",
                "test-change",
                "PHASE1",
                "artifacts_modified",
                "details text",
            ],
            cwd=tmp_path,
        )
        assert result.returncode != 0, "old positional form must not succeed"
        data = json.loads((change_dir / "state.json").read_text())
        assert "transition" not in data, "state must NOT be mutated by rejected invocation"
