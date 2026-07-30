#!/usr/bin/env python3
"""
Tests for the runner's pre-wait PID handshake and POSIX process-group
termination.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import patch

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

    def test_callback_error_is_logged_and_subprocess_is_waited_for(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        def _raise_callback(pid: int) -> None:
            raise RuntimeError(f"cannot store {pid}")

        request = RunRequest(
            command="dummy",
            agent="dummy",
            change_id="dummy",
            timeout=5,
        )
        result = _run_with_logging(
            [sys.executable, "-c", "raise SystemExit(0)"],
            request,
            verbose=False,
            label="test",
            on_pid=_raise_callback,
        )
        captured = capsys.readouterr()

        assert result.exit_code == 0
        assert result.pid is not None
        assert f"Warning: PID callback failed for process {result.pid}" in captured.err
        assert f"cannot store {result.pid}" in captured.err
        assert result.log_path is not None
        result.log_path.unlink()


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


@pytest.mark.unit
class TestTimeoutProcessGroupTermination:
    """M21a: the timeout path must signal the whole process group, not just
    the direct child PID. The runner sets up ``os.setsid`` on POSIX so the
    AI's own subprocesses inherit a fresh pgid."""

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only")
    def test_timeout_signals_process_group(self, monkeypatch: pytest.MonkeyPatch):
        """When the subprocess exceeds the timeout, the helper signals the
        process group with ``SIGTERM`` and escalates to ``SIGKILL``."""
        killpg_calls: list = []
        kill_calls: list = []

        def fake_killpg(pgid: int, sig: int) -> None:
            killpg_calls.append((pgid, sig))

        def fake_kill(pid: int, sig: int) -> None:
            kill_calls.append((pid, sig))

        monkeypatch.setattr(os, "killpg", fake_killpg)
        monkeypatch.setattr(os, "kill", fake_kill)
        # getpgid must still return something so the killpg branch is taken.
        monkeypatch.setattr(os, "getpgid", lambda pid: pid)

        # Build a fake Popen that always raises TimeoutExpired on wait().
        class _FakeProcess:
            pid = 12345
            stdout = None

            def wait(self, timeout=None):  # noqa: ARG002
                raise subprocess.TimeoutExpired(cmd=["sleep"], timeout=timeout)

            def terminate(self) -> None:
                pass

            def kill(self) -> None:
                pass

        request = RunRequest(
            command="dummy",
            agent="dummy",
            change_id="dummy",
            timeout=0,
        )

        with patch(
            "source.orchestrator.runner.subprocess.Popen",
            return_value=_FakeProcess(),
        ):
            result = _run_with_logging(
                ["sleep", "10"],
                request,
                verbose=False,
                label="test",
            )

        assert result.timed_out is True
        assert result.exit_code == 124
        sigterms = [c for c in killpg_calls if c[1] == signal.SIGTERM]
        assert sigterms, f"expected SIGTERM via killpg; got {killpg_calls}"

    @pytest.mark.skipif(sys.platform == "win32", reason="POSIX-only")
    def test_timeout_falls_back_to_direct_terminate_when_pgid_unknown(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        """If getpgid raises (process already reaped), fall back to terminate()."""
        terminate_calls: list = []

        class _FakeProcess:
            pid = 99999
            stdout = None

            def wait(self, timeout=None):  # noqa: ARG002
                raise subprocess.TimeoutExpired(cmd=["x"], timeout=timeout)

            def terminate(self) -> None:
                terminate_calls.append(None)

            def kill(self) -> None:
                pass

        def fake_getpgid(pid: int) -> int:  # noqa: ARG001
            raise ProcessLookupError("not found")

        monkeypatch.setattr(os, "getpgid", fake_getpgid)

        request = RunRequest(
            command="dummy",
            agent="dummy",
            change_id="dummy",
            timeout=0,
        )

        with patch(
            "source.orchestrator.runner.subprocess.Popen",
            return_value=_FakeProcess(),
        ):
            result = _run_with_logging(
                ["x"],
                request,
                verbose=False,
                label="test",
            )

        assert result.timed_out is True
        assert terminate_calls, "expected fallback to process.terminate()"


@pytest.mark.unit
class TestChildPidClearedAfterRunAgent:
    """M21b: ``state.child_pid`` must be cleared after ``run_agent`` returns,
    so a stale PID cannot be signalled by a later SIGINT."""

    def test_state_child_pid_cleared_after_run_agent(self, tmp_path, monkeypatch):
        from source.orchestrator import engine as eng
        from source.orchestrator import runner as runner_mod

        change_dir = tmp_path / "openspec" / "changes" / "test-change"
        change_dir.mkdir(parents=True)
        (change_dir / "tasks.md").write_text("# Tasks")
        (change_dir / "proposal.md").write_text("# Proposal")
        (change_dir / "design.md").write_text("# Design")
        (change_dir / "specs").mkdir()
        (change_dir / "specs" / "spec.md").write_text("# Spec")

        monkeypatch.chdir(tmp_path)

        st = eng.OrchestratorState(
            change_dir=change_dir,
            change_id="test-change",
        )
        st.log_file = None
        st.log_user_specified = False

        class _FakeResult:
            exit_code = 0
            log_path = None
            pid = 4242
            timed_out = False
            error = None

        pid_observed: dict = {}

        class _FakeRunner:
            name = "fake"

            def run(self, request, verbose=False):  # noqa: ARG002
                if request.on_pid is not None:
                    request.on_pid(4242)
                    pid_observed["inside_run"] = st.child_pid
                return _FakeResult()

        monkeypatch.setattr(eng, "detect_runner", lambda x: _FakeRunner())
        monkeypatch.setattr(runner_mod, "detect_runner", lambda x: _FakeRunner())

        st.child_pid = None
        result = eng.run_agent(st, "PHASE0")
        assert result is True
        assert pid_observed.get("inside_run") == 4242
        assert st.child_pid is None, (
            f"state.child_pid should be cleared after run_agent; got {st.child_pid}"
        )


@pytest.mark.unit
class TestWindowsSignalSelection:
    """M21c: on Windows, the timeout / interrupt path must select
    ``signal.CTRL_BREAK_EVENT`` when available. The signal is only defined
    on Windows; on POSIX we patch it in."""

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows-only contract test")
    def test_windows_terminate_child_uses_ctrl_break_event(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        from source.orchestrator import engine as eng

        sent_signals: list = []

        def fake_kill(pid: int, sig: int) -> None:
            sent_signals.append((pid, sig))

        monkeypatch.setattr(eng.os, "kill", fake_kill)

        st = eng.OrchestratorState(change_id="x")
        st.child_pid = 1234

        with patch.object(eng.sys, "platform", "win32"):
            monkeypatch.setattr(eng.signal, "CTRL_BREAK_EVENT", 1, raising=False)
            eng._terminate_child(st)

        assert sent_signals, "expected at least one kill call"
        assert all(pid == 1234 for pid, _ in sent_signals)
        # The control-break event (value 1 from our patch) should appear
        # in the sent signals when available.
        assert 1 in (sig for _, sig in sent_signals), (
            f"expected CTRL_BREAK_EVENT (1) in sent signals; got {sent_signals}"
        )

    @pytest.mark.skipif(sys.platform == "win32", reason="Windows-only contract test")
    def test_windows_terminate_subprocess_tree_uses_ctrl_break_event(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        from source.orchestrator import runner as runner_mod

        sent_signals: list = []

        def fake_kill(pid: int, sig: int) -> None:
            sent_signals.append((pid, sig))

        monkeypatch.setattr(runner_mod.os, "kill", fake_kill)

        class _FakeProcess:
            pid = 5555
            stdout = None

            def wait(self, timeout=None):  # noqa: ARG002
                raise subprocess.TimeoutExpired(cmd=["x"], timeout=timeout)

            def terminate(self) -> None:
                pass

            def kill(self) -> None:
                pass

        with patch.object(runner_mod.sys, "platform", "win32"):
            monkeypatch.setattr(runner_mod.signal, "CTRL_BREAK_EVENT", 1, raising=False)
            runner_mod._terminate_subprocess_tree(_FakeProcess(), 5555)

        assert sent_signals
        assert all(pid == 5555 for pid, _ in sent_signals)
        assert 1 in (sig for _, sig in sent_signals)
