#!/usr/bin/env python3
"""
Runner - Abstraction over AI-assistant CLI invocations.

The orchestrator dispatches phase steps to a runner. Two implementations:
- OpencodeRunner: uses `opencode run --command <cmd> --agent <agent> <change>`
- ClaudeRunner: uses `claude --print --dangerously-skip-permissions ... <cmd>`

The runner is selected automatically by `detect_runner(project_root)` based
on which tool directory (.opencode/ or .claude/) is present.
"""

import re
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Protocol

from source.lib.osx import OSXError


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

        return _run_with_logging(cmd, request, verbose=verbose, label=request.agent)


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

        return _run_with_logging(cmd, request, verbose=verbose, label=request.agent)


def _run_with_logging(
    cmd: list,
    request: RunRequest,
    *,
    verbose: bool,
    label: str,
) -> RunResult:
    """Spawn a subprocess, stream output, strip ANSI, return exit code.

    Mirrors the opencode invocation pattern in source/orchestrator/engine.py:498-546.
    """
    try:
        with tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix=".log"
        ) as agent_log:
            log_path = Path(agent_log.name)

        agent_log_file = open(log_path, "w", buffering=1)

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=request.cwd,
        )
        pid = process.pid

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
