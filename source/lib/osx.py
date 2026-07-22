#!/usr/bin/env python3
"""
osx - OpenSpec Extended change management library

Pure library. Every domain exposes a public function (e.g. `state_get`,
`phase_advance`, `baseline_record`) that:

- Returns a `dict` on success
- Raises `OSXError(code, message, **context)` on failure

There is no CLI surface here. The Typer app that exposes these
functions as `openspec-extended osx <domain> <action>` lives in
`source/osx_cli.py`.

In-process callers (the orchestrator, tests) should import the
library functions directly to avoid subprocess overhead and JSON
parsing.
"""

import json
import re
import select
import subprocess
import sys
import tempfile
from contextvars import ContextVar
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml

from source.lib import state_io

PHASES = ["PHASE0", "PHASE1", "PHASE2", "PHASE3", "PHASE4", "PHASE5", "PHASE6"]

PHASE_NAMES: dict[str, str] = {
    "PHASE0": "ARTIFACT REVIEW",
    "PHASE1": "IMPLEMENTATION",
    "PHASE2": "REVIEW",
    "PHASE3": "MAINTAIN DOCS",
    "PHASE4": "SYNC",
    "PHASE5": "SELF-REFLECTION",
    "PHASE6": "ARCHIVE",
}

PHASE_COMMANDS = {
    "PHASE0": "osx-phase0",
    "PHASE1": "osx-phase1",
    "PHASE2": "osx-phase2",
    "PHASE3": "osx-phase3",
    "PHASE4": "osx-phase4",
    "PHASE5": "osx-phase5",
    "PHASE6": "osx-phase6",
}

VALID_TRANSITION_REASONS = [
    "implementation_incorrect",
    "artifacts_modified",
    "retry_requested",
]

MIN_OPENSPEC_VERSION: tuple[int, int, int] = (1, 6, 0)


def get_core_version(timeout: int = 10) -> Optional[tuple[int, int, int]]:
    """Parse `openspec --version` stdout into a (major, minor, patch) tuple.

    Returns None if the binary is missing, errors, or the version cannot
    be parsed. Used by the orchestrator to enforce the minimum core version
    before relying on v1.6.0 workflows (notably ``openspec-update-change``).
    """
    try:
        result = subprocess.run(
            ["openspec", "--version"],
            capture_output=True,
            text=True,
            check=True,
            timeout=timeout,
        )
    except (
        FileNotFoundError,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
        OSError,
    ):
        return None
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", result.stdout or "")
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


LOG_TEXT_FIELD_MAX_LENGTH = 2000

_LOG_FINGERPRINTS = (
    "integer 10 readonly",
    "integer 1 readonly",
    "array readonly",
    "tied zsh_eval_context",
)

REQUIRED_SKILLS = [
    "osx-concepts",
    "osx-workflow",
    "osx-review-artifacts",
    "osx-modify-artifacts",
    "osx-review-test-compliance",
    "osx-maintain-ai-docs",
    "osx-commit",
]
# osx-generate-changelog is intentionally absent: it has its own /osx-changelog dispatch.

REQUIRED_CORE_SKILLS = [
    "osc-apply-change",
    "osc-verify-change",
    "osc-sync-specs",
    "osc-archive-change",
]

SKILLS_DIR = Path(".opencode/skills")
COMMANDS_DIR = Path(".opencode/commands")


def detect_platform(project_root: Path) -> str:
    """Detect whether the project uses opencode or claude.

    Mirrors `runner.detect_runner` precedence: opencode wins ties.
    Returns "opencode" if neither is present (default).
    """
    if (project_root / ".opencode").exists():
        return "opencode"
    if (project_root / ".claude").exists():
        return "claude"
    return "opencode"


def skills_dir(project_root: Path) -> Path:
    platform = detect_platform(project_root)
    if platform == "claude":
        return project_root / ".claude" / "skills"
    return project_root / ".opencode" / "skills"


def commands_dir(project_root: Path) -> Path:
    platform = detect_platform(project_root)
    if platform == "claude":
        return project_root / ".claude" / "commands" / "osx"
    return project_root / ".opencode" / "commands"


class OSXError(Exception):
    """Raised by library functions on error. Caught by the CLI wrappers."""

    def __init__(self, code: str, message: str, **context) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.context = context


def get_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


current_store: ContextVar[Optional[str]] = ContextVar("osx_current_store", default=None)

_PATHS_CACHE: dict[tuple[str, Optional[str]], dict] = {}


def _run_openspec_json(args: list, timeout: int = 10) -> dict:
    """Run `openspec <args...> --json` and return the parsed JSON dict.

    Raises:
      OSXError("cli_not_found")  — openspec binary not on PATH
      OSXError("cli_error")      — non-zero exit or timeout
      OSXError("invalid_json")   — stdout is not valid JSON
    """
    cmd = ["openspec", *args, "--json"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError as e:
        raise OSXError("cli_not_found", "openspec CLI not found in PATH") from e
    except subprocess.TimeoutExpired as e:
        raise OSXError("cli_error", "openspec CLI timed out", timeout=timeout) from e
    if result.returncode != 0:
        raise OSXError(
            "cli_error",
            result.stderr.strip() or "openspec failed",
            args=args,
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise OSXError(
            "invalid_json",
            "openspec returned non-JSON output",
            stdout=result.stdout[:200],
        ) from e


def resolve_change_paths(change: str, store: Optional[str] = None) -> dict:
    """Resolve where a change *would* live on disk.

    Always returns a dict. The `change_root` may not exist on disk —
    callers that need to assert existence should check `change_root.is_dir()`
    or use `_find_change_dir` instead.

    Returns:
      {
        "change_root":   Path,   # absolute (CLI) or repo-local
        "planning_home": Path,   # absolute (CLI) or Path("openspec")
        "archive_dir":   Path,   # <planning_home>/changes/archive
        "source":        "cli" | "fallback"
      }
    """
    effective_store = store if store is not None else current_store.get()
    cache_key = (change, effective_store)
    if cache_key in _PATHS_CACHE:
        return _PATHS_CACHE[cache_key]

    args = ["status", "--change", change]
    if effective_store:
        args.extend(["--store", effective_store])

    cli_result = None
    try:
        cli_result = _run_openspec_json(args)
    except OSXError:
        cli_result = None

    if isinstance(cli_result, dict):
        change_root_str = cli_result.get("changeRoot")
        planning_home_val = cli_result.get("planningHome")
        planning_home_str: Optional[str]
        if isinstance(planning_home_val, dict):
            planning_home_str = planning_home_val.get("root")
        else:
            planning_home_str = planning_home_val
        if change_root_str and planning_home_str:
            change_root = Path(change_root_str)
            planning_home = Path(planning_home_str) / "openspec"
            return {
                "change_root": change_root,
                "planning_home": planning_home,
                "archive_dir": planning_home / "changes" / "archive",
                "source": "cli",
            }

    result = {
        "change_root": Path(f"openspec/changes/{change}"),
        "planning_home": Path("openspec"),
        "archive_dir": Path("openspec/changes/archive"),
        "source": "fallback",
    }
    _PATHS_CACHE[cache_key] = result
    return result


def _find_change_dir(change: str, store: Optional[str] = None) -> Path:
    """Find the change directory. Checks the active path first, then the
    archive. Backward-compatible: existing callers that omit `store` get
    the same behavior as before (CLI consulted, then repo-local fallback).

    Raises OSXError("change_not_found") if neither the active path nor any
    archive entry matches.
    """
    paths = resolve_change_paths(change, store=store)
    primary = paths["change_root"]
    if primary.is_dir():
        return primary

    archive_dir = paths["archive_dir"]
    if archive_dir.is_dir():
        for d in sorted(archive_dir.iterdir()):
            if d.is_dir() and d.name.endswith(f"-{change}"):
                return d

    archive_dir_fallback = Path("openspec/changes/archive")
    if archive_dir_fallback.is_dir() and archive_dir_fallback != archive_dir:
        for d in sorted(archive_dir_fallback.iterdir()):
            if d.is_dir() and d.name.endswith(f"-{change}"):
                return d

    raise OSXError("change_not_found", "Change directory does not exist", change=change)


def _read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        raise OSXError("invalid_json", f"Invalid JSON in {path}", path=str(path)) from e


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, dir=path.parent, suffix=".json"
    ) as f:
        json.dump(data, f, indent=2)
        f.flush()
        Path(f.name).replace(path)


def _read_state(change_dir: Path) -> dict:
    state = state_io.read_state(change_dir)
    if state is not None:
        return state
    return _read_json(change_dir / "state.json")


def _write_state(change_dir: Path, state: dict) -> None:
    state_io.write_state(change_dir, state)


def _validate_log_text_field(field: str, value: str) -> None:
    """Reject shell-tainted free-text fields in the decision log.

    LLMs occasionally pass markdown backticks (e.g. `local`) inside a shell
    argument like `--summary "..."`. The user's shell interprets those
    backticks as command substitution, which can dump the entire shell
    environment (20KB+) into the decision log. This guard catches that and
    similar accidents before they reach the JSON file on disk.
    """
    if len(value) > LOG_TEXT_FIELD_MAX_LENGTH:
        raise OSXError(
            "input_too_long",
            f"{field} is {len(value)} chars; max is {LOG_TEXT_FIELD_MAX_LENGTH}. "
            "This usually means backticks in the argument were interpreted as "
            "command substitution by the shell. Remove backticks from the "
            f"--{field} value and try again.",
            field=field,
            length=len(value),
            max=LOG_TEXT_FIELD_MAX_LENGTH,
        )
    for fingerprint in _LOG_FINGERPRINTS:
        if fingerprint in value:
            raise OSXError(
                "input_tainted",
                f"{field} contains shell-output fingerprint {fingerprint!r}. "
                "This means backticks in the argument were interpreted as "
                "command substitution. Remove backticks from the "
                f"--{field} value and try again.",
                field=field,
                fingerprint=fingerprint,
            )


def _read_json_array(path: Path) -> list[Any]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, list):
            raise OSXError("invalid_format", f"{path.name} is not a valid JSON array")
        return data
    except json.JSONDecodeError as e:
        raise OSXError("invalid_json", f"Invalid JSON in {path}") from e


def append_to_json_array(path: Path, entry: dict) -> int:
    data = _read_json_array(path)
    data.append(entry)
    write_json(path, data)
    return len(data)


def _read_stdin_json() -> Optional[dict]:
    if sys.stdin.isatty():
        return None

    if hasattr(select, "select"):
        try:
            has_data, _, _ = select.select([sys.stdin], [], [], 0)
            if not has_data:
                return None
        except (ValueError, OSError):
            return None

    try:
        content = sys.stdin.read().strip()
        if not content:
            return None
        return json.loads(content)
    except json.JSONDecodeError as e:
        raise OSXError("invalid_json", "Input is not valid JSON") from e


def get_next_phase(current: str) -> str:
    phase_order = {
        "PHASE0": "PHASE1",
        "PHASE1": "PHASE2",
        "PHASE2": "PHASE3",
        "PHASE3": "PHASE4",
        "PHASE4": "PHASE5",
        "PHASE5": "PHASE6",
        "PHASE6": "COMPLETE",
        "COMPLETE": "COMPLETE",
    }
    return phase_order.get(current, "COMPLETE")


# ============================================================
# Library API: pure functions that return dicts and raise OSXError
# ============================================================


def baseline_record() -> dict:
    try:
        subprocess.check_output(
            ["git", "rev-parse", "--is-inside-work-tree"],
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise OSXError(
            "not_git_repo", "Current directory is not a git repository"
        ) from e

    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
        branch = (
            subprocess.check_output(
                ["git", "branch", "--show-current"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            or "unknown"
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        raise OSXError("git_error", "Failed to get git info") from e

    timestamp = get_timestamp()
    baseline_file = Path(".openspec-baseline.json")
    data = {
        "commit": commit,
        "branch": branch,
        "timestamp": timestamp,
    }
    write_json(baseline_file, data)
    return data


def baseline_get() -> dict:
    baseline_file = Path(".openspec-baseline.json")
    if not baseline_file.exists():
        raise OSXError("baseline_not_found", ".openspec-baseline.json does not exist")

    try:
        return json.loads(baseline_file.read_text())
    except json.JSONDecodeError as e:
        raise OSXError(
            "invalid_json", ".openspec-baseline.json contains invalid JSON"
        ) from e


def ctx_get(change: str, *, store: Optional[str] = None) -> dict:
    change_dir = _find_change_dir(change, store=store)

    def check_artifact(path: Path, artifact_type: str) -> dict:
        if artifact_type == "directory":
            if path.is_dir():
                count = len(list(path.glob("*.md")))
                return {"exists": True, "count": count}
            return {"exists": False, "count": 0}
        else:
            if path.is_file():
                return {"exists": True, "size": path.stat().st_size}
            return {"exists": False, "size": 0}

    def get_state() -> dict:
        state_file = change_dir / "state.json"
        if not state_file.exists():
            return {"phase": "UNKNOWN", "iteration": 0, "phase_complete": False}
        state = _read_state(change_dir)
        return {
            "phase": state.get("phase", "UNKNOWN"),
            "iteration": state.get("iteration", 0),
            "phase_complete": state.get("phase_complete", False),
        }

    def get_git() -> dict:
        result: dict[str, Any] = {
            "modified": [],
            "added": [],
            "untracked": [],
            "clean": True,
        }
        try:
            cmd = ["git", "status", "--porcelain", "--", str(change_dir)]
            output_lines = (
                subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True)
                .strip()
                .split("\n")
            )
            for line in output_lines:
                if not line:
                    continue
                status = line[:2]
                filepath = line[3:].strip()
                if status.startswith("M") or status[1] == "M":
                    result["modified"].append(filepath)
                    result["clean"] = False
                elif status.startswith("A") or status[1] == "A":
                    result["added"].append(filepath)
                    result["clean"] = False
                elif status.startswith("??"):
                    result["untracked"].append(filepath)
                    result["clean"] = False
                elif status.strip():
                    result["modified"].append(filepath)
                    result["clean"] = False
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass
        return result

    proposal = check_artifact(change_dir / "proposal.md", "file")
    specs = check_artifact(change_dir / "specs", "directory")
    design = check_artifact(change_dir / "design.md", "file")
    tasks = check_artifact(change_dir / "tasks.md", "file")

    decision_log = _read_json_array(change_dir / "decision-log.json")
    iterations = _read_json_array(change_dir / "iterations.json")

    project_root = change_dir.parent.parent.parent
    schema_info = resolve_schema(project_root=project_root, change_dir=change_dir)
    schema_artifacts = list_artifacts_for_schema(
        schema_info["name"], store=current_store.get()
    )

    return {
        "change": change,
        "state": get_state(),
        "git": get_git(),
        "artifacts": {
            "proposal": proposal,
            "specs": specs,
            "design": design,
            "tasks": tasks,
        },
        "schema": {
            "name": schema_info["name"],
            "source": schema_info["source"],
            "artifacts": schema_artifacts,
        },
        "history": {
            "decision_log_entries": len(decision_log),
            "iterations_recorded": len(iterations),
        },
    }


def git_get(change: str) -> dict:
    change_dir = _find_change_dir(change)
    result: dict[str, Any] = {
        "modified": [],
        "added": [],
        "untracked": [],
        "clean": True,
    }

    try:
        branch = (
            subprocess.check_output(
                ["git", "branch", "--show-current"],
                stderr=subprocess.DEVNULL,
                text=True,
            ).strip()
            or "unknown"
        )
        result["branch"] = branch

        cmd = ["git", "status", "--porcelain", "--", str(change_dir)]
        output_lines = (
            subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True)
            .strip()
            .split("\n")
        )

        for line in output_lines:
            if not line:
                continue
            status = line[:2]
            filepath = line[3:].strip()

            if status.startswith("M") or status[1] == "M":
                result["modified"].append(filepath)
                result["clean"] = False
            elif status.startswith("A") or status[1] == "A":
                result["added"].append(filepath)
                result["clean"] = False
            elif status.startswith("??"):
                result["untracked"].append(filepath)
                result["clean"] = False
            elif status.strip():
                result["modified"].append(filepath)
                result["clean"] = False

    except (subprocess.CalledProcessError, FileNotFoundError):
        result["branch"] = "unknown"

    return result


def phase_current(change: str, *, store: Optional[str] = None) -> dict:
    change_dir = _find_change_dir(change, store=store)
    state_file = change_dir / "state.json"

    if "archive" in str(change_dir) and not state_file.exists():
        raise OSXError("archived", "Change is archived, no active state")

    if not state_file.exists():
        timestamp = get_timestamp()
        state = {
            "phase": "PHASE0",
            "phase_name": PHASE_NAMES.get("PHASE0", "UNKNOWN"),
            "iteration": 1,
            "phase_complete": False,
            "phase_iterations": {},
            "started_at": timestamp,
            "last_updated": timestamp,
        }
        _write_state(change_dir, state)
    else:
        state = _read_state(change_dir)

    phase = state.get("phase", "UNKNOWN")
    iteration = state.get("iteration", 0)
    next_phase = get_next_phase(str(phase))
    return {"phase": phase, "next": next_phase, "iteration": iteration}


def phase_next(change: str, *, store: Optional[str] = None) -> dict:
    change_dir = _find_change_dir(change, store=store)
    state_file = change_dir / "state.json"

    if "archive" in str(change_dir) and not state_file.exists():
        raise OSXError("archived", "Change is archived, no active state")

    if not state_file.exists():
        timestamp = get_timestamp()
        state = {
            "phase": "PHASE0",
            "phase_name": PHASE_NAMES.get("PHASE0", "UNKNOWN"),
            "iteration": 1,
            "phase_complete": False,
            "phase_iterations": {},
            "started_at": timestamp,
            "last_updated": timestamp,
        }
        _write_state(change_dir, state)
    else:
        state = _read_state(change_dir)

    current = state.get("phase", "UNKNOWN")
    if not current:
        raise OSXError("invalid_state", "state.json missing phase field")
    next_phase = get_next_phase(str(current))
    return {"next": next_phase}


def phase_advance(change: str, *, store: Optional[str] = None) -> dict:
    change_dir = _find_change_dir(change, store=store)
    state_file = change_dir / "state.json"

    if "archive" in str(change_dir) and not state_file.exists():
        raise OSXError("archived", "Change is archived, no active state")

    if not state_file.exists():
        timestamp = get_timestamp()
        state = {
            "phase": "PHASE0",
            "phase_name": PHASE_NAMES.get("PHASE0", "UNKNOWN"),
            "iteration": 1,
            "phase_complete": False,
            "phase_iterations": {},
            "started_at": timestamp,
            "last_updated": timestamp,
        }
        _write_state(change_dir, state)
    else:
        state = _read_state(change_dir)

    current_phase = state.get("phase", "UNKNOWN")
    if not current_phase:
        raise OSXError("invalid_state", "state.json missing phase field")

    next_phase = get_next_phase(str(current_phase))
    timestamp = get_timestamp()

    state["phase"] = next_phase
    state["phase_name"] = PHASE_NAMES.get(next_phase, "UNKNOWN")
    state["iteration"] = 1
    state["phase_complete"] = False
    state["last_updated"] = timestamp
    _write_state(change_dir, state)

    next_next = get_next_phase(next_phase)
    return {
        "phase": next_phase,
        "previous": current_phase,
        "next": next_next,
        "iteration": 1,
    }


def state_get(change: str, *, store: Optional[str] = None) -> dict:
    change_dir = _find_change_dir(change, store=store)
    state_file = change_dir / "state.json"

    if not state_file.exists():
        raise OSXError(
            "state_not_found", "state.json does not exist", path=str(state_file)
        )

    state = _read_state(change_dir)
    return {
        "phase": state.get("phase", "UNKNOWN"),
        "iteration": state.get("iteration", 0),
        "phase_complete": state.get("phase_complete", False),
        "change": change,
    }


def state_complete(change: str, *, store: Optional[str] = None) -> dict:
    change_dir = _find_change_dir(change, store=store)
    state_file = change_dir / "state.json"

    if not state_file.exists():
        raise OSXError("state_not_found", "state.json does not exist")

    state = _read_state(change_dir)
    state["phase_complete"] = True
    state["last_updated"] = get_timestamp()
    _write_state(change_dir, state)

    return {"success": True, "phase_complete": True}


def state_transition(
    change: str,
    target: str,
    reason: str,
    details: Optional[str] = None,
    *,
    store: Optional[str] = None,
) -> dict:
    if target not in PHASES:
        raise OSXError(
            "invalid_target", f"Invalid target phase: {target}", valid=PHASES
        )

    if reason not in VALID_TRANSITION_REASONS:
        raise OSXError(
            "invalid_reason",
            f"Invalid reason: {reason}",
            valid=VALID_TRANSITION_REASONS,
        )

    change_dir = _find_change_dir(change, store=store)
    state_file = change_dir / "state.json"

    if not state_file.exists():
        raise OSXError("state_not_found", "state.json does not exist")

    state = _read_state(change_dir)
    state["phase_complete"] = True
    state["transition"] = {"target": target, "reason": reason}
    if details:
        state["transition"]["details"] = details
    state["last_updated"] = get_timestamp()
    _write_state(change_dir, state)

    result: dict = {
        "success": True,
        "transition": {"target": target, "reason": reason},
    }
    if details:
        result["transition"]["details"] = details
    return result


def state_clear_transition(change: str, *, store: Optional[str] = None) -> dict:
    change_dir = _find_change_dir(change, store=store)
    state_file = change_dir / "state.json"

    if not state_file.exists():
        raise OSXError("state_not_found", "state.json does not exist")

    state = _read_state(change_dir)
    state.pop("transition", None)
    state["last_updated"] = get_timestamp()
    _write_state(change_dir, state)

    return {"success": True, "transition_cleared": True}


def state_set_phase(
    change: str,
    phase: str,
    iteration: Optional[int] = None,
    *,
    store: Optional[str] = None,
) -> dict:
    if phase not in PHASES:
        raise OSXError("invalid_phase", f"Invalid phase: {phase}", valid=PHASES)

    change_dir = _find_change_dir(change, store=store)
    state_file = change_dir / "state.json"

    if not state_file.exists():
        raise OSXError("state_not_found", "state.json does not exist")

    state = _read_state(change_dir)
    previous = state.get("phase", "UNKNOWN")
    state["phase"] = phase
    state["phase_name"] = PHASE_NAMES[phase] if phase in PHASE_NAMES else "UNKNOWN"
    if iteration is not None:
        state["iteration"] = iteration
    state["last_updated"] = get_timestamp()
    _write_state(change_dir, state)

    return {"success": True, "phase": phase, "previous_phase": previous}


def iterations_get(change: str, *, store: Optional[str] = None) -> dict:
    change_dir = _find_change_dir(change, store=store)
    iterations_file = change_dir / "iterations.json"

    if not iterations_file.exists():
        return {"count": 0, "iterations": []}

    iterations = _read_json_array(iterations_file)
    iteration_nums = [i.get("iteration") for i in iterations if "iteration" in i]
    return {"count": len(iterations), "iterations": iteration_nums}


def iterations_append(
    change: str,
    iteration: Optional[int] = None,
    phase: Optional[str] = None,
    summary: Optional[str] = None,
    status: Optional[str] = None,
    notes: Optional[str] = None,
    commit_hash: Optional[str] = None,
    issues: Optional[str] = None,
    artifacts_modified: Optional[str] = None,
    decisions: Optional[str] = None,
    errors: Optional[str] = None,
    extra: Optional[str] = None,
    entry: Optional[dict] = None,
    store: Optional[str] = None,
) -> dict:
    change_dir = _find_change_dir(change, store=store)
    iterations_file = change_dir / "iterations.json"

    if entry is None:
        stdin_data = _read_stdin_json()
        if stdin_data is not None:
            entry = stdin_data
        else:
            if iteration is None or phase is None:
                raise OSXError(
                    "missing_field",
                    "iteration and phase required (via --iteration and --phase or stdin)",
                )

            entry = {"iteration": iteration, "phase": phase}
            if summary:
                entry["summary"] = summary
            if status:
                entry["status"] = status
            if notes:
                entry["notes"] = notes
            if commit_hash:
                entry["commit_hash"] = commit_hash
            if issues:
                try:
                    entry["issues"] = json.loads(issues)
                except json.JSONDecodeError as e:
                    raise OSXError("invalid_json", "issues must be valid JSON") from e
            if artifacts_modified:
                try:
                    entry["artifacts_modified"] = json.loads(artifacts_modified)
                except json.JSONDecodeError as e:
                    raise OSXError(
                        "invalid_json",
                        "artifacts_modified must be valid JSON",
                    ) from e
            if decisions:
                try:
                    entry["decisions"] = json.loads(decisions)
                except json.JSONDecodeError as e:
                    raise OSXError(
                        "invalid_json", "decisions must be valid JSON"
                    ) from e
            if errors:
                try:
                    entry["errors"] = json.loads(errors)
                except json.JSONDecodeError as e:
                    raise OSXError("invalid_json", "errors must be valid JSON") from e
            if extra:
                try:
                    extra_data = json.loads(extra)
                    if isinstance(extra_data, dict):
                        entry.update(extra_data)
                except json.JSONDecodeError as e:
                    raise OSXError(
                        "invalid_json", "extra must be valid JSON object"
                    ) from e

    if "iteration" not in entry:
        raise OSXError("missing_field", "iteration field is required")

    entry.setdefault("timestamp", get_timestamp())

    total = append_to_json_array(iterations_file, entry)
    return {
        "success": True,
        "iteration": entry["iteration"],
        "total_count": total,
    }


def log_get(change: str, *, store: Optional[str] = None) -> dict:
    change_dir = _find_change_dir(change, store=store)
    log_file = change_dir / "decision-log.json"

    if not log_file.exists():
        return {"count": 0, "entries": []}

    entries = _read_json_array(log_file)
    return {"count": len(entries), "entries": entries}


def log_append(
    change: str,
    phase: Optional[str] = None,
    iteration: Optional[int] = None,
    summary: Optional[str] = None,
    commit_hash: Optional[str] = None,
    next_steps: Optional[str] = None,
    issues: Optional[str] = None,
    artifacts_modified: Optional[str] = None,
    decisions: Optional[str] = None,
    errors: Optional[str] = None,
    extra: Optional[str] = None,
    entry: Optional[dict] = None,
    store: Optional[str] = None,
) -> dict:
    change_dir = _find_change_dir(change, store=store)
    log_file = change_dir / "decision-log.json"

    if entry is None:
        stdin_data = _read_stdin_json()
        if stdin_data is not None:
            entry = stdin_data
        else:
            if iteration is None or phase is None:
                raise OSXError(
                    "missing_field",
                    "phase and iteration required (via --phase and --iteration or stdin)",
                )

            entry = {"phase": phase, "iteration": iteration}
            if summary:
                entry["summary"] = summary
            if commit_hash:
                entry["commit_hash"] = commit_hash
            if next_steps:
                entry["next_steps"] = next_steps
            if issues:
                try:
                    entry["issues"] = json.loads(issues)
                except json.JSONDecodeError as e:
                    raise OSXError("invalid_json", "issues must be valid JSON") from e
            if artifacts_modified:
                try:
                    entry["artifacts_modified"] = json.loads(artifacts_modified)
                except json.JSONDecodeError as e:
                    raise OSXError(
                        "invalid_json",
                        "artifacts_modified must be valid JSON",
                    ) from e
            if decisions:
                try:
                    entry["decisions"] = json.loads(decisions)
                except json.JSONDecodeError as e:
                    raise OSXError(
                        "invalid_json", "decisions must be valid JSON"
                    ) from e
            if errors:
                try:
                    entry["errors"] = json.loads(errors)
                except json.JSONDecodeError as e:
                    raise OSXError("invalid_json", "errors must be valid JSON") from e
            if extra:
                try:
                    extra_data = json.loads(extra)
                    if isinstance(extra_data, dict):
                        entry.update(extra_data)
                except json.JSONDecodeError as e:
                    raise OSXError(
                        "invalid_json", "extra must be valid JSON object"
                    ) from e

    if "phase" not in entry:
        raise OSXError("missing_field", "phase field is required")
    if "iteration" not in entry:
        raise OSXError("missing_field", "iteration field is required")

    for field in ("summary", "next_steps"):
        value = entry.get(field)
        if isinstance(value, str):
            _validate_log_text_field(field, value)

    entries = _read_json_array(log_file)
    entry_num = len(entries) + 1
    timestamp = get_timestamp()

    entry["entry"] = entry_num
    entry["timestamp"] = timestamp

    append_to_json_array(log_file, entry)
    return {
        "success": True,
        "entry": entry_num,
        "phase": entry["phase"],
        "iteration": entry["iteration"],
        "timestamp": timestamp,
    }


def complete_check(change: str, *, store: Optional[str] = None) -> dict:
    change_dir = _find_change_dir(change, store=store)
    complete_file = change_dir / "complete.json"

    if not complete_file.exists():
        return {"exists": False}

    try:
        json.loads(complete_file.read_text())
        return {"exists": True}
    except json.JSONDecodeError:
        return {"exists": False, "error": "invalid_json"}


def complete_get(change: str, *, store: Optional[str] = None) -> dict:
    change_dir = _find_change_dir(change, store=store)
    complete_file = change_dir / "complete.json"

    if not complete_file.exists():
        raise OSXError("complete_not_found", "complete.json does not exist")

    try:
        data = json.loads(complete_file.read_text())
    except json.JSONDecodeError as e:
        raise OSXError("invalid_json", "complete.json contains invalid JSON") from e

    result: dict = {
        "status": data.get("status", "UNKNOWN"),
        "with_blocker": data.get("with_blocker", False),
    }
    if data.get("blocker_reason"):
        result["blocker_reason"] = data["blocker_reason"]
    return result


def complete_set(
    change: str,
    status: Optional[str] = None,
    blocker_reason: Optional[str] = None,
    *,
    store: Optional[str] = None,
) -> dict:
    change_dir = _find_change_dir(change, store=store)
    complete_file = change_dir / "complete.json"
    timestamp = get_timestamp()
    status_value = status or "COMPLETE"

    if status_value == "BLOCKED":
        if not blocker_reason:
            raise OSXError(
                "invalid_blocker",
                "BLOCKED status requires --blocker-reason",
            )
        data = {
            "status": status_value,
            "with_blocker": True,
            "blocker_reason": blocker_reason,
            "timestamp": timestamp,
        }
        write_json(complete_file, data)
        return {
            "status": status_value,
            "with_blocker": True,
            "blocker_reason": blocker_reason,
        }

    data = {
        "status": status_value,
        "with_blocker": False,
        "timestamp": timestamp,
    }
    write_json(complete_file, data)
    return {"status": status_value, "with_blocker": False}


def store_list() -> dict:
    """List registered OpenSpec stores."""
    return {"success": True, "data": _run_openspec_json(["store", "list"])}


def store_doctor(store_id: Optional[str] = None) -> dict:
    """Check health of a single registered store (or all when id is None)."""
    args = ["store", "doctor"]
    if store_id:
        args.append(store_id)
    return {"success": True, "data": _run_openspec_json(args)}


def store_register(path: str, store_id: Optional[str] = None) -> dict:
    """Register an OpenSpec store at the given filesystem path.

    Args:
      path: Filesystem path to the store repo.
      store_id: Optional explicit store id (upstream `--id` flag).

    Note: prior versions used `--name`; upstream uses `--id` (v1.5+ stores).
    """
    args = ["store", "register", path]
    if store_id:
        args.extend(["--id", store_id])
    return {"success": True, "data": _run_openspec_json(args)}


def store_unregister(store_id: str) -> dict:
    """Unregister an OpenSpec store."""
    return {
        "success": True,
        "data": _run_openspec_json(["store", "unregister", store_id]),
    }


def validate_json(target: str) -> dict:
    file_path = Path(target)

    if not file_path.exists():
        return {
            "valid": False,
            "errors": [{"check": "json", "message": f"File not found: {target}"}],
        }

    try:
        json.loads(file_path.read_text())
        return {"valid": True}
    except json.JSONDecodeError:
        return {
            "valid": False,
            "errors": [{"check": "json", "message": f"Invalid JSON in file: {target}"}],
        }


def validate_skills(project_root: Optional[Path] = None) -> dict:
    root = project_root if project_root is not None else Path.cwd()
    errors: list[dict] = []
    missing_skills: list[str] = []

    base = skills_dir(root)
    for skill in REQUIRED_SKILLS + REQUIRED_CORE_SKILLS:
        skill_path = base / skill / "SKILL.md"
        if not skill_path.exists():
            errors.append({"check": "skills", "message": f"Missing skill: {skill}"})
            missing_skills.append(skill)

    if errors:
        return {"valid": False, "errors": errors, "missing_skills": missing_skills}
    return {"valid": True}


def validate_commands(project_root: Optional[Path] = None) -> dict:
    root = project_root if project_root is not None else Path.cwd()
    errors: list[dict] = []

    base = commands_dir(root)
    for phase in PHASES:
        cmd_name = PHASE_COMMANDS.get(phase)
        if cmd_name:
            cmd_path = base / f"{cmd_name}.md"
            if not cmd_path.exists():
                errors.append(
                    {"check": "commands", "message": f"Missing command: {cmd_name}"}
                )

    if errors:
        return {"valid": False, "errors": errors}
    return {"valid": True}


def validate_change_dir(target: str, *, store: Optional[str] = None) -> dict:
    paths = resolve_change_paths(target, store=store)
    change_path = paths["change_root"]
    errors: list[dict] = []

    if not change_path.is_dir():
        return {
            "valid": False,
            "errors": [
                {
                    "check": "change-dir",
                    "message": f"Change directory not found: {change_path}",
                }
            ],
        }

    schema_info = resolve_schema(change_dir=change_path)
    schema_name = schema_info["name"]

    required_files = _required_artifact_files(schema_name)
    for file in required_files:
        if not (change_path / file).exists():
            errors.append(
                {"check": "change-dir", "message": f"Required file missing: {file}"}
            )

    if schema_name == "spec-driven":
        specs_dir = change_path / "specs"
        if not specs_dir.is_dir() or not list(specs_dir.rglob("*.md")):
            errors.append(
                {"check": "change-dir", "message": "No spec files found in specs/"}
            )

    if errors:
        return {"valid": False, "errors": errors}
    return {"valid": True}


def validate_archive(target: str, *, store: Optional[str] = None) -> dict:
    paths = resolve_change_paths(target, store=store)
    archive_dir = paths["archive_dir"]
    archives: list[Path] = []

    if archive_dir.is_dir():
        for d in archive_dir.iterdir():
            if d.is_dir() and d.name.endswith(f"-{target}"):
                archives.append(d)

    if len(archives) == 0:
        return {
            "valid": False,
            "errors": [{"check": "archive", "message": "Change not archived"}],
        }

    if len(archives) > 1:
        return {
            "valid": False,
            "errors": [
                {
                    "check": "archive",
                    "message": f"Multiple archives found for change: {len(archives)}",
                }
            ],
        }

    return {"valid": True, "archive": str(archives[0])}


def validate_iterations(target: str, *, store: Optional[str] = None) -> dict:
    try:
        change_dir = _find_change_dir(target, store=store)
    except OSXError:
        return {
            "valid": False,
            "errors": [
                {"check": "iterations", "message": "Change directory not found"}
            ],
        }

    iterations_file = change_dir / "iterations.json"

    if not iterations_file.exists():
        return {
            "valid": False,
            "errors": [{"check": "iterations", "message": "iterations.json not found"}],
        }

    try:
        json.loads(iterations_file.read_text())
    except json.JSONDecodeError:
        return {
            "valid": False,
            "errors": [
                {
                    "check": "iterations",
                    "message": "iterations.json contains invalid JSON",
                }
            ],
        }

    return {"valid": True}


def validate_completion(target: str, *, store: Optional[str] = None) -> dict:
    errors: list[dict] = []

    try:
        change_dir = _find_change_dir(target, store=store)
    except OSXError:
        return {
            "valid": False,
            "errors": [
                {"check": "completion", "message": "Change directory not found"}
            ],
        }

    state_file = change_dir / "state.json"
    if not state_file.exists():
        errors.append({"check": "completion", "message": "state.json not found"})
    else:
        try:
            json.loads(state_file.read_text())
        except json.JSONDecodeError:
            errors.append(
                {
                    "check": "completion",
                    "message": "state.json contains invalid JSON",
                }
            )

    complete_file = change_dir / "complete.json"
    if not complete_file.exists():
        errors.append({"check": "completion", "message": "complete.json not found"})
    else:
        try:
            json.loads(complete_file.read_text())
        except json.JSONDecodeError:
            errors.append(
                {
                    "check": "completion",
                    "message": "complete.json contains invalid JSON",
                }
            )

    iterations_file = change_dir / "iterations.json"
    if not iterations_file.exists():
        errors.append({"check": "completion", "message": "iterations.json not found"})
    else:
        try:
            json.loads(iterations_file.read_text())
        except json.JSONDecodeError:
            errors.append(
                {
                    "check": "completion",
                    "message": "iterations.json contains invalid JSON",
                }
            )

    log_file = change_dir / "decision-log.json"
    if not log_file.exists():
        errors.append({"check": "completion", "message": "decision-log.json not found"})

    archive_dir = resolve_change_paths(target, store=store)["archive_dir"]
    archives: list[Path] = []
    if archive_dir.is_dir():
        for d in archive_dir.iterdir():
            if d.is_dir() and d.name.endswith(f"-{target}"):
                archives.append(d)

    if len(archives) == 0:
        errors.append({"check": "completion", "message": "Archive validation failed"})

    if errors:
        return {"valid": False, "errors": errors}
    return {"valid": True}


def _translate_validate_payload(payload: dict) -> dict:
    """Translate upstream openspec validate JSON contract to our internal shape.

    Upstream shape (success):
      {"items": [{"id", "type", "valid", "issues": [{level, path, message, line?}], "durationMs"}],
       "summary": {"totals": {items, passed, failed}, "byType": {...}}, "version": "1.0", "root": {...}}

    Upstream shape (pre-validation error):
      {"status": [{"severity", "code", "message", "fix?"}]}

    Returns our internal shape:
      {"valid": bool, "errors": [...], "warnings": [...], "info": [...],
       "items": [{"id", "type", "valid", "issues": [...]}],
       "summary": {...},
       "root": {...},
       "diagnostics": [{"code", "message", "fix"}]}  # only present on pre-validation error
    """
    if "status" in payload and "items" not in payload:
        diagnostics = [
            {
                "code": d.get("code", "unknown"),
                "message": d.get("message", ""),
                "fix": d.get("fix"),
            }
            for d in payload.get("status", [])
        ]
        return {
            "valid": False,
            "errors": [
                {"check": d["code"], "message": d["message"]} for d in diagnostics
            ],
            "warnings": [],
            "info": [],
            "diagnostics": diagnostics,
        }

    items_out = []
    errors: list[dict] = []
    warnings: list[dict] = []
    info: list[dict] = []

    for item in payload.get("items", []):
        items_out.append(
            {
                "id": item.get("id"),
                "type": item.get("type"),
                "valid": item.get("valid", False),
                "issues": item.get("issues", []),
            }
        )
        for issue in item.get("issues", []):
            level = issue.get("level", "ERROR")
            entry = {
                "check": f"{item.get('type', 'item')}:{issue.get('path', 'file')}",
                "message": issue.get("message", ""),
                "target": item.get("id"),
                "line": issue.get("line"),
            }
            if level == "ERROR":
                errors.append(entry)
            elif level == "WARNING":
                warnings.append(entry)
            elif level == "INFO":
                info.append(entry)

    summary = payload.get("summary", {})
    failed = summary.get("totals", {}).get("failed")
    if failed is None:
        warnings.append(
            {
                "code": "unverifiable_envelope",
                "severity": "warning",
                "check": "unverifiable_envelope",
                "message": (
                    "Upstream validate envelope is missing summary.totals.failed; "
                    "result is unverifiable"
                ),
            }
        )
        return {
            "valid": None,
            "errors": errors,
            "warnings": warnings,
            "info": info,
            "items": items_out,
            "summary": summary,
            "root": payload.get("root", {}),
        }
    return {
        "valid": failed == 0,
        "errors": errors,
        "warnings": warnings,
        "info": info,
        "items": items_out,
        "summary": summary,
        "root": payload.get("root", {}),
    }


def validate_change(
    change_id: str, *, store: Optional[str] = None, strict: bool = False
) -> dict:
    """Validate a single OpenSpec change via `openspec validate <id> --json`.

    Args:
      change_id: OpenSpec change id (e.g., "add-auth-feature")
      store: Optional OpenSpec store id
      strict: If True, warnings are treated as failures (forwarded as --strict)

    Returns: see _translate_validate_payload.
    Raises: OSXError on subprocess failures (delegated to _run_openspec_json).
    """
    args = ["validate", change_id, "--no-interactive"]
    if strict:
        args.append("--strict")
    if store:
        args.extend(["--store", store])
    return _translate_validate_payload(_run_openspec_json(args))


def validate_spec(
    spec_id: str, *, store: Optional[str] = None, strict: bool = False
) -> dict:
    """Validate a single OpenSpec main spec via `openspec validate <id> --type spec --json`.

    Args:
      spec_id: Spec capability id (e.g., "authentication")
      store: Optional OpenSpec store id
      strict: If True, warnings are treated as failures

    Returns: see _translate_validate_payload.
    Raises: OSXError on subprocess failures.
    """
    args = ["validate", spec_id, "--type", "spec", "--no-interactive"]
    if strict:
        args.append("--strict")
    if store:
        args.extend(["--store", store])
    return _translate_validate_payload(_run_openspec_json(args))


def validate_all(
    *,
    store: Optional[str] = None,
    strict: bool = False,
    concurrency: int = 6,
) -> dict:
    """Validate all changes AND specs via `openspec validate --all --json`.

    Args:
      store: Optional OpenSpec store id
      strict: If True, warnings are treated as failures
      concurrency: Max parallel validations (default 6, per upstream default)

    Returns: see _translate_validate_payload.
    Raises: OSXError on subprocess failures.
    """
    args = [
        "validate",
        "--all",
        "--no-interactive",
        "--concurrency",
        str(concurrency),
    ]
    if strict:
        args.append("--strict")
    if store:
        args.extend(["--store", store])
    return _translate_validate_payload(_run_openspec_json(args, timeout=60))


def validate_changes_only(*, store: Optional[str] = None, strict: bool = False) -> dict:
    """Validate all active changes only via `openspec validate --changes --json`."""
    args = ["validate", "--changes", "--no-interactive"]
    if strict:
        args.append("--strict")
    if store:
        args.extend(["--store", store])
    return _translate_validate_payload(_run_openspec_json(args))


def validate_specs_only(*, store: Optional[str] = None, strict: bool = False) -> dict:
    """Validate all main specs only via `openspec validate --specs --json`."""
    args = ["validate", "--specs", "--no-interactive"]
    if strict:
        args.append("--strict")
    if store:
        args.extend(["--store", store])
    return _translate_validate_payload(_run_openspec_json(args))


def resolve_schema(
    *,
    project_root: Optional[Path] = None,
    explicit: Optional[str] = None,
    change_dir: Optional[Path] = None,
) -> dict:
    """Resolve the active workflow schema with 4-level precedence.

    Precedence:
      1. Explicit override (--schema CLI flag or programmatic)
      2. Per-change .openspec.yaml metadata
      3. Project openspec/config.yaml (or .yml)
      4. Default 'spec-driven'

    Returns: {"name": str, "source": "explicit"|"change-metadata"|"project-config"|"default"}

    Malformed YAML is logged but never raised — falls through to the next level.
    Missing files are not an error.
    """
    if project_root is None:
        project_root = Path.cwd()

    if explicit:
        return {"name": explicit, "source": "explicit"}

    if change_dir is not None:
        change_meta = change_dir / ".openspec.yaml"
        if change_meta.exists():
            try:
                data = yaml.safe_load(change_meta.read_text())
                if (
                    isinstance(data, dict)
                    and isinstance(data.get("schema"), str)
                    and data["schema"]
                ):
                    return {"name": data["schema"], "source": "change-metadata"}
            except (yaml.YAMLError, OSError) as error:
                print(
                    f"Warning: Could not load schema configuration {change_meta}: {error}",
                    file=sys.stderr,
                )

    for config_name in ("config.yaml", "config.yml"):
        config_path = project_root / "openspec" / config_name
        if config_path.exists():
            try:
                data = yaml.safe_load(config_path.read_text())
                if (
                    isinstance(data, dict)
                    and isinstance(data.get("schema"), str)
                    and data["schema"]
                ):
                    return {"name": data["schema"], "source": "project-config"}
            except (yaml.YAMLError, OSError) as error:
                print(
                    f"Warning: Could not load schema configuration {config_path}: {error}",
                    file=sys.stderr,
                )

    return {"name": "spec-driven", "source": "default"}


def list_artifacts_for_schema(
    schema_name: str, *, store: Optional[str] = None
) -> list[str]:
    """Return artifact IDs for a schema, resolved from upstream `openspec templates`.

    Falls back to spec-driven artifact list on subprocess failure.
    """
    try:
        args = ["templates", "--schema", schema_name]
        if store:
            args.extend(["--store", store])
        payload = _run_openspec_json(args)
        if isinstance(payload, dict):
            return list(payload.keys())
    except OSXError:
        pass
    return ["proposal", "specs", "design", "tasks"]


def required_core_skills(schema_name: str) -> list[str]:
    """Return the core (osc-*) skills required for a schema.

    Mapping derived from spec-driven's artifact graph. For non-spec-driven schemas,
    callers should fall back to whatever skills the schema's instructions reference.
    """
    if schema_name == "spec-driven":
        return [
            "osc-apply-change",
            "osc-verify-change",
            "osc-sync-specs",
            "osc-archive-change",
        ]
    return ["osc-archive-change"]


def schema_which(
    name: Optional[str] = None,
    *,
    all_schemas: bool = False,
    store: Optional[str] = None,
) -> dict:
    """Resolve which schema a project uses via `openspec schema which`.

    Returns the raw upstream payload (list of SchemaResolution objects if --all,
    single object otherwise).
    """
    args = ["schema", "which"]
    if name:
        args.append(name)
    if all_schemas:
        args.append("--all")
    if store:
        args.extend(["--store", store])
    return _run_openspec_json(args)


def schema_validate(
    name: Optional[str] = None,
    *,
    store: Optional[str] = None,
) -> dict:
    """Validate a schema via `openspec schema validate`.

    Returns {"valid": bool, "schemas": [...]} or single-schema result.
    """
    args = ["schema", "validate"]
    if name:
        args.append(name)
    if store:
        args.extend(["--store", store])
    return _run_openspec_json(args)


def schema_fork(
    source: str,
    name: Optional[str] = None,
    *,
    force: bool = False,
    store: Optional[str] = None,
) -> dict:
    """Fork a schema to project-local via `openspec schema fork`."""
    args = ["schema", "fork", source]
    if name:
        args.append(name)
    if force:
        args.append("--force")
    if store:
        args.extend(["--store", store])
    return _run_openspec_json(args)


def schema_init(
    name: str,
    *,
    description: Optional[str] = None,
    artifacts: Optional[list[str]] = None,
    set_default: bool = False,
    force: bool = False,
    store: Optional[str] = None,
) -> dict:
    """Initialize a new project-local schema via `openspec schema init`."""
    args = ["schema", "init", name]
    if description:
        args.extend(["--description", description])
    if artifacts:
        args.extend(["--artifacts", ",".join(artifacts)])
    if set_default:
        args.append("--default")
    if force:
        args.append("--force")
    if store:
        args.extend(["--store", store])
    return _run_openspec_json(args)


def schema_list(*, store: Optional[str] = None) -> list[dict]:
    """List all available schemas via `openspec schemas`.

    Returns the raw upstream list payload.
    """
    args = ["schemas"]
    if store:
        args.extend(["--store", store])
    payload = _run_openspec_json(args)
    if isinstance(payload, list):
        return payload
    return []


def _required_artifact_files(schema_name: str) -> list[str]:
    """Map schema artifact IDs to their required file paths."""
    if schema_name == "spec-driven":
        return ["proposal.md", "design.md", "tasks.md"]
    return []
