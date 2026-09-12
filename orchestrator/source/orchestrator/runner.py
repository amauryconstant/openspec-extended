#!/usr/bin/env python3
# ruff: noqa: EXE001 - shebang is intentional
"""
Runner - Abstraction over AI-assistant CLI invocations.

The orchestrator dispatches phase steps to a runner. Three implementations:
- OpencodeRunner: uses `opencode run --command <cmd> --agent <agent> <change>`
- ClaudeRunner: uses `claude --print --dangerously-skip-permissions ... <cmd>`
- GenericPrintRunner: `<tool> --print --dangerously-skip-permissions "<prompt>"`
  (lands in v1.11.0 for Cursor / Qwen / Kiro; skeleton in v1.10.0)

The runner is selected automatically by `detect_runner(project_root)` which
walks ``REGISTRY`` (orchestrator/source/tools.py) in registration order and
returns the runner for the first adapter whose ``detect_paths`` includes an
existing directory at ``project_root``. ``opencode`` wins ties by being
registered first.
"""

import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, TYPE_CHECKING

from source.lib.osx import OSXError

if TYPE_CHECKING:
    from source.tools import ToolAdapter

OnPidCallback = Callable[[int], None]


@dataclass
class RunRequest:
    """A single AI invocation request."""

    command: str
    agent: str
    change_id: str
    title: str = ""
    model: str = ""
    cwd: Path | None = None
    timeout: int = 1800
    on_pid: OnPidCallback | None = None
    env: dict[str, str] | None = None
    store: str | None = None
    schema_name: str | None = None
    extra_prompt: str = ""
    """Prepended to the AI prompt when non-empty. Used to inject project-level
    operation guidance (A.4) on PHASE1 and PHASE6 spawns only; ignored for
    other phases. See ``OpencodeRunner.run`` / ``ClaudeRunner.run`` for the
    per-platform mechanism."""


@dataclass
class RunResult:
    """Outcome of a runner dispatch."""

    exit_code: int
    log_path: Path | None = None
    timed_out: bool = False
    error: str | None = None
    pid: int | None = None


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


def detect_runner(project_root: Path | None = None) -> Runner:
    """Detect which AI runner to use based on the project root's tool directory.

    Walks ``REGISTRY`` in registration order and returns the runner for
    the first adapter whose ``detect_paths`` includes an existing
    directory at ``project_root``. ``opencode`` wins ties by being
    registered first (locked by
    ``tests/unit/test_tool_registry.py::test_detect_paths_are_unique_across_shipped_tools``
    and confirmed by ``test_opencode_takes_precedence`` in this module).

    Raises ``OSXError("no_runner_detected", ...)`` when no adapter's
    ``detect_paths`` match.
    """
    from source.tools import REGISTRY

    root = project_root or Path.cwd()
    for adapter in REGISTRY.values():
        if any((root / p).is_dir() for p in adapter.detect_paths):
            return _runner_for(adapter)
    raise OSXError(
        "no_runner_detected",
        f"No AI runner detected at {root}.",
        hint=(
            "Run `openspec-extended install <tool>` for one of: "
            + ", ".join(sorted(REGISTRY))
        ),
    )


def _runner_for(adapter: "ToolAdapter") -> Runner:
    """Construct the runner class appropriate for ``adapter.runner_kind``.

    Dispatches to the three runner classes:

    - ``opencode_run`` → ``OpencodeRunner``
    - ``claude_print`` → ``ClaudeRunner``
    - ``generic_print`` → ``GenericPrintRunner`` (lands in v1.11.0)

    Raises ``OSXError("unknown_runner_kind", ...)`` for an adapter whose
    ``runner_kind`` is not one of the three supported values. Adding a
    new ``runner_kind`` literal to ``source/tools.py:RunnerKind``
    without extending this factory is a TypeError-catchable programming
    error; the explicit error message surfaces it during tests.
    """
    if adapter.runner_kind == "opencode_run":
        return OpencodeRunner(adapter=adapter)
    if adapter.runner_kind == "claude_print":
        return ClaudeRunner(adapter=adapter)
    if adapter.runner_kind == "generic_print":
        return GenericPrintRunner(adapter=adapter)
    raise OSXError(
        "unknown_runner_kind",
        f"Tool adapter {adapter.tool_id!r} declares unsupported "
        f"runner_kind {adapter.runner_kind!r}",
    )


class OpencodeRunner:
    """Runner that dispatches to `opencode run`."""

    name = "opencode"
    _FALLBACK_BINARY = "opencode"

    def __init__(self, adapter: "ToolAdapter | None" = None) -> None:
        self.adapter = adapter

    def _binary(self) -> str:
        """Resolve the binary name from the adapter (preferred) or fall
        back to the literal ``"opencode"`` for legacy call paths that
        construct ``OpencodeRunner()`` without an adapter."""
        if self.adapter is not None:
            return self.adapter.runner_binary
        return self._FALLBACK_BINARY

    def run(self, request: RunRequest, *, verbose: bool = False) -> RunResult:
        binary = shutil.which(self._binary())
        if binary is None:
            raise OSXError(
                "runner_not_found", f"{self._binary()} binary not found in PATH"
            )

        cmd = [
            self._binary(),
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

        # A.4: when project-level operation guidance is provided, attach it
        # to the message via ``--file``. ``opencode run`` has no ``--prompt``
        # flag (``--prompt`` belongs to the TUI's ``--continue``/``--session``
        # flow, not the ``run`` subcommand) and the positional message args
        # are forwarded as ``$1``/``$2``/... args to the slash command —
        # prepending to the positional would break the command templates.
        # Writing the guidance to a temp file and attaching via ``--file``
        # is the documented mechanism that keeps ``$1`` clean.
        guidance_path: Path | None = None
        if request.extra_prompt:
            guidance_fd, guidance_name = tempfile.mkstemp(
                prefix="osx-operation-guidance-", suffix=".md"
            )
            guidance_path = Path(guidance_name)
            try:
                with os.fdopen(guidance_fd, "w") as guidance_file:
                    guidance_file.write(request.extra_prompt)
            except OSError:
                guidance_path.unlink(missing_ok=True)
                guidance_path = None
            if guidance_path is not None:
                cmd.extend(["--file", str(guidance_path)])

        try:
            return _run_with_logging(
                cmd,
                request,
                verbose=verbose,
                label=request.agent,
                on_pid=request.on_pid,
            )
        finally:
            if guidance_path is not None:
                guidance_path.unlink(missing_ok=True)


class ClaudeRunner:
    """Runner that dispatches to `claude --print` with the slash command.

    Claude Code's CLI invocation pattern:
      claude --print --dangerously-skip-permissions --model <model> "<prompt>"

    We pass the slash command + change id as the prompt so the slash
    command is interpreted by Claude Code.
    """

    name = "claude"
    _FALLBACK_BINARY = "claude"

    def __init__(self, adapter: "ToolAdapter | None" = None) -> None:
        self.adapter = adapter

    def _binary(self) -> str:
        """Resolve the binary name from the adapter (preferred) or fall
        back to the literal ``"claude"`` for legacy call paths that
        construct ``ClaudeRunner()`` without an adapter."""
        if self.adapter is not None:
            return self.adapter.runner_binary
        return self._FALLBACK_BINARY

    def run(self, request: RunRequest, *, verbose: bool = False) -> RunResult:
        binary = shutil.which(self._binary())
        if binary is None:
            raise OSXError(
                "runner_not_found", f"{self._binary()} binary not found in PATH"
            )

        prompt = f"/{request.command} {request.change_id}"
        if request.extra_prompt:
            prompt = f"{request.extra_prompt}\n\n{prompt}"
        cmd = [self._binary(), "--print", "--dangerously-skip-permissions", prompt]
        if request.model:
            cmd.extend(["--model", request.model])

        return _run_with_logging(
            cmd,
            request,
            verbose=verbose,
            label=request.agent,
            on_pid=request.on_pid,
        )


def _terminate_subprocess_tree(process: subprocess.Popen, pid: int) -> None:
    """Terminate ``process`` and any descendants it spawned.

    Mirrors ``engine._terminate_child`` semantics:

    - POSIX: child runs in its own session (``os.setsid`` above). Signal the
      whole group with ``SIGTERM`` first, escalate to ``SIGKILL`` after a
      short grace period.
    - Windows: child runs with ``CREATE_NEW_PROCESS_GROUP``; send
      ``CTRL_BREAK_EVENT`` to the direct PID (process-group signal semantics
      differ). Falls back to ``TerminateProcess`` (SIGTERM) if the break
      event is unavailable.

    Errors (process already dead, permission denied) are swallowed — the
    caller cannot act on them and the subprocess is about to be reaped.
    """
    if sys.platform != "win32":
        try:
            pgid = os.getpgid(pid)
            os.killpg(pgid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                process.terminate()
            except OSError:
                pass
        try:
            process.wait(timeout=2)
            return
        except subprocess.TimeoutExpired:
            pass
        try:
            pgid = os.getpgid(pid)
            os.killpg(pgid, signal.SIGKILL)
        except (ProcessLookupError, PermissionError, OSError):
            try:
                process.kill()
            except OSError:
                pass
    else:
        ctrl_break = getattr(signal, "CTRL_BREAK_EVENT", None)
        try:
            if ctrl_break is not None:
                os.kill(pid, ctrl_break)
            else:
                process.terminate()
        except (ProcessLookupError, PermissionError, OSError):
            try:
                process.terminate()
            except OSError:
                pass


def _run_with_logging(
    cmd: list,
    request: RunRequest,
    *,
    verbose: bool,
    label: str,
    on_pid: OnPidCallback | None = None,
) -> RunResult:
    """Spawn a subprocess, stream output, strip ANSI, return exit code.

    Mirrors the opencode invocation pattern in source/orchestrator/engine.py:498-546.

    If ``on_pid`` is provided, it is invoked with ``process.pid`` *immediately*
    after ``Popen`` returns — before ``process.wait()`` — so the caller's
    state has a live PID for cancellation. The callback fires synchronously
    inside this function; it must not block.

    On POSIX, the child is spawned in its own session via ``os.setsid`` so the
    engine can terminate the whole process group with ``killpg`` if the child
    becomes unresponsive. On Windows, ``CREATE_NEW_PROCESS_GROUP`` is set so
    ``CTRL_BREAK_EVENT`` can be sent on cancellation. See
    ``_terminate_subprocess_tree`` for the termination policy.
    """
    try:
        with tempfile.NamedTemporaryFile(
            mode="w+", delete=False, suffix=".log"
        ) as agent_log:
            log_path = Path(agent_log.name)

        popen_kwargs: dict = {
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
            "text": True,
            "bufsize": 1,
            "cwd": request.cwd,
            "env": os.environ | (request.env or {}),
        }
        if request.store:
            popen_kwargs["env"] = {
                **popen_kwargs["env"],
                "OSX_STORE": request.store,
            }
        if request.schema_name:
            popen_kwargs["env"] = {
                **popen_kwargs["env"],
                "OSX_SCHEMA": request.schema_name,
            }
        # Use a new session / process group so we can signal the whole tree
        # if the AI runner spawns child processes of its own.
        if sys.platform != "win32":
            popen_kwargs["preexec_fn"] = os.setsid
        else:
            # CREATE_NEW_PROCESS_GROUP is required for CTRL_BREAK_EVENT to be
            # delivered on Windows; see _terminate_subprocess_tree.
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
            except Exception as error:  # noqa: BLE001 - user callback may raise anything
                print(
                    f"Warning: PID callback failed for process {pid}: {error}",
                    file=sys.stderr,
                )

        def _stream() -> None:
            stdout = process.stdout
            if stdout is None:
                return
            with open(log_path, "w", buffering=1) as agent_log_file:
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
            _terminate_subprocess_tree(process, pid)
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
    except Exception as e:  # noqa: BLE001 - process spawn can fail in many ways; converted to RunResult
        return RunResult(exit_code=1, error=str(e))
