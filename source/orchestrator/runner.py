#!/usr/bin/env python3
"""
Runner - Abstraction over AI-assistant CLI invocations.

The orchestrator dispatches phase steps to a runner. Two implementations:
- OpencodeRunner: uses `opencode run --command <cmd> --agent <agent> <change>`
- ClaudeRunner: uses `claude --print --dangerously-skip-permissions ... <cmd>`

The runner is selected automatically by `detect_runner(project_root)` based
on which tool directory (.opencode/ or .claude/) is present.
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Protocol

from source.lib.osx import OSXError

OnPidCallback = Callable[[int], None]


@dataclass
class RunRequest:
    """A single AI invocation request."""

    command: str
    agent: str
    change_id: str
    title: str = ""
    model: str = ""
    cwd: Optional[Path] = None
    timeout: int = 1800
    on_pid: Optional[OnPidCallback] = None
    env: dict[str, str] | None = None


@dataclass
class RunResult:
    """Outcome of a runner dispatch."""

    exit_code: int
    log_path: Optional[Path] = None
    timed_out: bool = False
    error: Optional[str] = None
    pid: Optional[int] = None


class Runner(Protocol):
    """Protocol that all AI runner implementations satisfy."""

    name: str

    def run(self, request: RunRequest, *, verbose: bool = False) -> RunResult:
        """Dispatch the request to the underlying AI CLI.

        Returns a RunResult. Never raises on non-zero exit; instead returns
        the exit code in the result. Only raises OSXError for unrecoverable
        setup failures (binary missing, etc.).
        """
        ...


def detect_runner(project_root: Path) -> Runner:
    """Detect which AI runner to use based on the project root's tool directory.

    Detection order:
      1. .opencode/ → OpencodeRunner
      2. .claude/ → ClaudeRunner
      3. Otherwise → raise OSXError("no_runner_detected", ...)

    The `project_root` defaults to the current working directory if None.
    """
    root = project_root or Path.cwd()
    if (root / ".opencode").is_dir():
        return OpencodeRunner()
    if (root / ".claude").is_dir():
        return ClaudeRunner()
    raise OSXError(
        "no_runner_detected",
        f"No AI runner detected at {root}. Install .opencode/ or .claude/ first.",
        hint="Run `openspec-extended install opencode` or `openspec-extended install claude`",
    )


class OpencodeRunner:
    """Runner that dispatches to `opencode run`."""

    name = "opencode"

    def run(self, request: RunRequest, *, verbose: bool = False) -> RunResult:
        binary = shutil.which("opencode")
        if binary is None:
            raise OSXError("runner_not_found", "opencode binary not found in PATH")

        cmd = [
            "opencode",
            "run",
            "--command",
            request.command,
            "--agent",
            request.agent,
            request.change_id,
            f"--title={request.title or f'OpenSpec: {request.change_id}'}",
        ]
        if request.model:
            cmd.append(f"--model={request.model}")

        return _run_with_logging(
            cmd,
            request,
            verbose=verbose,
            label=request.agent,
            on_pid=request.on_pid,
        )


class ClaudeRunner:
    """Runner that dispatches to `claude --print` with the slash command.

    Claude Code's CLI invocation pattern:
      claude --print --dangerously-skip-permissions --model <model> "<prompt>"

    We pass the slash command + change id as the prompt so the slash
    command is interpreted by Claude Code.
    """

    name = "claude"

    def run(self, request: RunRequest, *, verbose: bool = False) -> RunResult:
        binary = shutil.which("claude")
        if binary is None:
            raise OSXError("runner_not_found", "claude binary not found in PATH")

        prompt = f"/{request.command} {request.change_id}"
        cmd = ["claude", "--print", "--dangerously-skip-permissions", prompt]
        if request.model:
            cmd.extend(["--model", request.model])

        return _run_with_logging(
            cmd,
            request,
            verbose=verbose,
            label=request.agent,
            on_pid=request.on_pid,
        )


def _run_with_logging(
    cmd: list,
    request: RunRequest,
    *,
    verbose: bool,
    label: str,
    on_pid: Optional[OnPidCallback] = None,
) -> RunResult:
    """Spawn a subprocess, stream output, strip ANSI, return exit code.

    Mirrors the opencode invocation pattern in source/orchestrator/engine.py:498-546.

    If ``on_pid`` is provided, it is invoked with ``process.pid`` *immediately*
    after ``Popen`` returns — before ``process.wait()`` — so the caller's
    state has a live PID for cancellation. The callback fires synchronously
    inside this function; it must not block.

    On POSIX, the child is spawned in its own session via ``os.setsid`` so the
    engine can terminate the whole process group with ``killpg`` if the child
    becomes unresponsive. On Windows, falls back to ``CREATE_NEW_PROCESS_GROUP``
    (``creationflags``); see TODO(Windows follow-up).
    """
    try:
        with tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix=".log"
        ) as agent_log:
            log_path = Path(agent_log.name)

        agent_log_file = open(log_path, "w", buffering=1)

        popen_kwargs: dict = dict(
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=request.cwd,
            env=os.environ | (request.env or {}),
        )
        # Use a new session / process group so we can signal the whole tree
        # if the AI runner spawns child processes of its own.
        if sys.platform != "win32":
            popen_kwargs["preexec_fn"] = os.setsid
        else:
            # TODO(Windows follow-up): add creationflags=CREATE_NEW_PROCESS_GROUP
            # and use signal.CTRL_BREAK_EVENT when terminating.
            popen_kwargs["creationflags"] = getattr(
                subprocess, "CREATE_NEW_PROCESS_GROUP", 0
            )

        process = subprocess.Popen(cmd, **popen_kwargs)
        pid = process.pid
        # Hand the PID to the caller BEFORE waiting — so cancellation
        # handlers (SIGINT in engine.handle_interrupt) can kill the live child.
        if on_pid is not None:
            try:
                on_pid(pid)
            except Exception as error:
                print(
                    f"Warning: PID callback failed for process {pid}: {error}",
                    file=sys.stderr,
                )

        def _stream() -> None:
            stdout = process.stdout
            if stdout is None:
                return
            with agent_log_file:
                for line in stdout:
                    agent_log_file.write(re.sub(r"\x1b\[[0-9;]*m", "", line))
                    if verbose:
                        sys.stdout.write(line)
                        sys.stdout.flush()

        reader = threading.Thread(target=_stream, daemon=True)
        reader.start()
        try:
            exit_code = process.wait(timeout=request.timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            reader.join(timeout=2)
            log_path.unlink(missing_ok=True)
            return RunResult(
                exit_code=124,
                log_path=None,
                timed_out=True,
                error=f"Timed out after {request.timeout}s",
                pid=pid,
            )

        reader.join()
        return RunResult(exit_code=exit_code, log_path=log_path, pid=pid)

    except FileNotFoundError as e:
        raise OSXError(
            "runner_not_found",
            f"{cmd[0]} binary not found in PATH",
        ) from e
    except Exception as e:
        return RunResult(exit_code=1, error=str(e))
