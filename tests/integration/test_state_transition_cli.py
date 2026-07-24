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


def _extract_bash_blocks(md_text: str) -> list[str]:
    """Pull every fenced ```bash ... ``` block from a markdown file."""
    blocks: list[str] = []
    in_block = False
    buf: list[str] = []
    for line in md_text.splitlines():
        if line.strip().startswith("```bash"):
            in_block = True
            buf = []
        elif in_block and line.strip().startswith("```"):
            blocks.append("\n".join(buf))
            in_block = False
        elif in_block:
            buf.append(line)
    return blocks


def _phase2_transition_blocks(platform: str) -> list[str]:
    """Return the bash blocks containing `osx state transition` from the phase2 command.

    Filters out the success-path `osx state complete` block and the
    `osx log append`/`osx iterations append` blocks; only Case A/B/C
    transition blocks remain.
    """
    if platform == "opencode":
        path = (
            Path(__file__).resolve().parent.parent.parent
            / "resources/opencode/commands/osx-phase2.md"
        )
    else:
        path = (
            Path(__file__).resolve().parent.parent.parent
            / "resources/claude/commands/osx/phase2.md"
        )
    text = path.read_text()
    return [
        b
        for b in _extract_bash_blocks(text)
        if "osx state transition " in b
    ]


@pytest.mark.integration
class TestPhase2TransitionExamplesAreRunnable:
    """Regression sentinel: the Case A/B/C bash blocks in osx-phase2.md must
    use the named-option form so they actually run against the current CLI."""

    @pytest.mark.parametrize(
        "platform,phase2_path",
        [
            (
                "opencode",
                Path(__file__).resolve().parent.parent.parent
                / "resources/opencode/commands/osx-phase2.md",
            ),
            (
                "claude",
                Path(__file__).resolve().parent.parent.parent
                / "resources/claude/commands/osx/phase2.md",
            ),
        ],
    )
    def test_phase2_md_uses_named_options(
        self, platform: str, phase2_path: Path
    ) -> None:
        text = phase2_path.read_text()
        assert "--target" in text, f"{platform}: phase2.md must use --target"
        assert "--reason" in text, f"{platform}: phase2.md must use --reason"

    @pytest.mark.parametrize("platform", ["opencode", "claude"])
    def test_every_transition_block_uses_named_options(self, platform: str) -> None:
        blocks = _phase2_transition_blocks(platform)
        assert len(blocks) >= 3, (
            f"{platform}: expected at least 3 Case A/B/C transition blocks, "
            f"found {len(blocks)}"
        )
        for i, block in enumerate(blocks, 1):
            assert "--target" in block, (
                f"{platform}: transition block #{i} missing --target — full block:\n{block}"
            )
            assert "--reason" in block, (
                f"{platform}: transition block #{i} missing --reason — full block:\n{block}"
            )

    @pytest.mark.parametrize("platform", ["opencode", "claude"])
    def test_every_transition_block_runs_against_cli(
        self, platform: str, change_dir: Path, tmp_path: Path
    ) -> None:
        import shlex

        blocks = _phase2_transition_blocks(platform)
        expected = [
            {
                "target": "PHASE1",
                "reason": "artifacts_modified",
                "details": "Brief description of what was fixed",
            },
            {
                "target": "PHASE1",
                "reason": "implementation_incorrect",
                "details": "Brief description of what needs fixing",
            },
            {
                "target": "PHASE2",
                "reason": "retry_requested",
                "details": "Brief description of alternative approach",
            },
        ]

        for case, block in zip(expected, blocks, strict=True):
            line = next(
                (
                    ln
                    for ln in block.splitlines()
                    if "osx state transition " in ln
                ),
                None,
            )
            assert line is not None, f"{platform}: no transition line in:\n{block}"

            tokens = shlex.split(line)
            assert "osx" in tokens, f"{platform}: tokens missing 'osx': {tokens}"
            sub_idx = tokens.index("osx")
            osx_args = [t.replace("$1", "test-change") for t in tokens[sub_idx + 1:]]

            assert "--target" in osx_args, (
                f"{platform}: example missing --target — {line!r}"
            )
            assert "--reason" in osx_args, (
                f"{platform}: example missing --reason — {line!r}"
            )

            change_dir.joinpath("state.json").write_text(
                json.dumps(
                    {
                        "phase": "PHASE2",
                        "iteration": 1,
                        "phase_complete": True,
                        "phase_iterations": {"PHASE2": 1},
                    }
                )
            )

            result = _run_osx(osx_args, cwd=tmp_path)
            assert result.returncode == 0, (
                f"{platform}: command failed (rc={result.returncode}): "
                f"{line!r}\nstdout: {result.stdout}\nstderr: {result.stderr}"
            )

            state = json.loads((change_dir / "state.json").read_text())
            assert state["transition"]["target"] == case["target"], (
                f"{platform}: expected target {case['target']!r}, got {state}"
            )
            assert state["transition"]["reason"] == case["reason"], (
                f"{platform}: expected reason {case['reason']!r}, got {state}"
            )
            assert state["transition"]["details"] == case["details"], (
                f"{platform}: expected details {case['details']!r}, got {state}"
            )
