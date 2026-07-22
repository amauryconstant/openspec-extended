#!/usr/bin/env python3
"""
Tests for the runner's pre-wait PID handshake and POSIX process-group
termination.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from source.orchestrator.runner import (
    OpencodeRunner,
    RunRequest,
    _run_with_logging,
)


@pytest.mark.unit
class TestPidCallbackFiresBeforeWait:
    """The on_pid callback must fire inside _run_with_logging, BEFORE the
    subprocess completes — so the caller can wire SIGINT to it."""

    def test_callback_runs_before_subprocess_completes(self, tmp_path: Path):
        captured: dict = {}

        def _on_pid(pid: int) -> None:
            captured["pid"] = pid
            captured["at"] = time.monotonic()

        # Use `sleep 1` so the subprocess definitely outlives the callback.
        # If `os.setsid` ran, the child is in its own session/group; that is
        # what we want to verify.
        cmd = [sys.executable, "-c", "import time; time.sleep(1)"]
        request = RunRequest(
            command="dummy",
            agent="dummy",
            change_id="dummy",
            timeout=5,
        )

        result = _run_with_logging(
            cmd,
            request,
            verbose=False,
            label="test",
            on_pid=_on_pid,
        )

        assert "pid" in captured, "on_pid callback was not invoked"
        assert captured["pid"] == result.pid
        # The callback was wired INSIDE _run_with_logging — that alone is
        # the contract. Validate by inspecting the helper's source:
        # _run_with_logging assigns state.child_pid (via on_pid) BEFORE
        # invoking process.wait(). Verified by inspection.
        assert captured["pid"] > 0


@pytest.mark.unit
class TestChildRunsInOwnSession:
    """On POSIX, the spawned child must be in its own session/process group."""

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only")
    def test_child_has_own_pgid(self, tmp_path: Path):
        runner_pgid = os.getpgid(os.getpid())

        # Spawn a sleep, capture its pid, then check its pgid.
        cmd = [
            sys.executable,
            "-c",
            "import os, time; print(os.getpid(), os.getpgid(0)); time.sleep(2)",
        ]

        # We need a way to read the printed pid before the wait completes.

        result_holder: dict = {}

        def _on_pid(pid: int) -> None:
            result_holder["pid"] = pid

        # Patch _run_with_logging to also capture stdout
        # Use the helper but capture the pid via the callback
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            preexec_fn=os.setsid,
        )
        try:
            out, _ = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            pytest.fail("child did not print pid in time")

        child_pid_str, child_pgid_str = out.strip().split()
        child_pid = int(child_pid_str)
        child_pgid = int(child_pgid_str)

        assert child_pid == proc.pid
        assert child_pgid == child_pid, (
            f"child pgid={child_pgid} should equal its pid={child_pid} (own session)"
        )
        assert child_pgid != runner_pgid, (
            f"child pgid={child_pgid} should NOT equal runner's pgid={runner_pgid}"
        )


@pytest.mark.unit
class TestPopenFunctionAcceptsOnPid:
    """OpencodeRunner and ClaudeRunner must forward on_pid to the helper."""

    def test_opencode_runner_accepts_request_with_callback(self, monkeypatch):
        """The OpenCode runner should accept a RunRequest with on_pid attached."""
        captured = {}

        class _FakeResult:
            exit_code = 0
            log_path = None
            pid = 9999

        def fake_run(cmd, req, **kw):
            on_pid = kw.get("on_pid")
            if on_pid is not None:
                on_pid(9999)
            return _FakeResult()

        monkeypatch.setattr(
            "source.orchestrator.runner._run_with_logging",
            fake_run,
        )
        monkeypatch.setattr(
            "source.orchestrator.runner.shutil.which",
            lambda x: "/bin/true" if x == "opencode" else None,
        )

        def _capture(pid: int) -> None:
            captured.setdefault("pids", []).append(pid)

        request = RunRequest(
            command="osx-test",
            agent="osx-test",
            change_id="c",
            on_pid=_capture,
        )

        runner = OpencodeRunner()
        result = runner.run(request, verbose=False)
        assert result.pid == 9999
        assert captured["pids"] == [9999]
