#!/usr/bin/env python3
"""
osx - OpenSpec Extended change management tool

Usage:
    openspec-extended osx <domain> <action> [args]

Domains:
    baseline    Baseline tracking (commit/branch)
    ctx         Aggregate context for a change
    git         Git status for change directory
    phase       Phase advancement management
    state       Phase and iteration state management
    iterations  Iteration history tracking
    log         Decision log management
    complete    Completion status tracking
    validate    Validation utilities
    instructions Get artifact instructions (proxies to openspec CLI)

Output: JSON to stdout, errors to stderr

Library API:
    Every domain exposes a public library function (e.g. `state_get`,
    `phase_advance`, `baseline_record`) that returns a dict and raises
    `OSXError` on failure. The Typer commands above are thin wrappers
    that catch `OSXError`, call `osx_error` to print, and exit.

    In-process callers (the orchestrator) should import the library
    functions directly to avoid subprocess overhead and JSON parsing.
"""

import json
import select
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import typer

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

REQUIRED_SKILLS = [
    "osx-concepts",
    "osx-review-artifacts",
    "osx-modify-artifacts",
    "osx-review-test-compliance",
    "osx-maintain-ai-docs",
]

REQUIRED_CORE_SKILLS = [
    "osc-apply-change",
    "osc-verify-change",
    "osc-sync-specs",
    "osc-archive-change",
]

SKILLS_DIR = Path(".opencode/skills")
COMMANDS_DIR = Path(".opencode/commands")

app = typer.Typer(help="OpenSpec Extended change management tool")


class OSXError(Exception):
    """Raised by library functions on error. Caught by Typer wrappers."""

    def __init__(self, code: str, message: str, **context) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.context = context


def osx_error(code: str, message: str, **context) -> None:
    """Print an error JSON to stderr and raise typer.Exit(1).

    Used by the Typer command wrappers and by low-level utilities
    that need the CLI behavior (print + exit). Library functions
    should raise `OSXError` instead.
    """
    result = {"error": code, "message": message}
    result.update(context)
    print(json.dumps(result), file=sys.stderr)
    raise typer.Exit(1)


def osx_output(data: dict) -> None:
    print(json.dumps(data))


def get_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def find_change_dir(change: str) -> Path:
    """Find a change directory (primary or archived).

    CLI behavior: raises typer.Exit(1) on not found.
    Library callers should use `_find_change_dir` instead.
    """
    primary = Path(f"openspec/changes/{change}")
    if primary.is_dir():
        return primary

    archive_dir = Path("openspec/changes/archive")
    if not archive_dir.is_dir():
        osx_error("change_not_found", "Change directory does not exist", change=change)

    for d in sorted(archive_dir.iterdir()):
        if d.is_dir() and d.name.endswith(f"-{change}"):
            return d

    osx_error("change_not_found", "Change directory does not exist", change=change)
    raise AssertionError("unreachable")


def _find_change_dir(change: str) -> Path:
    """Library version of find_change_dir: raises OSXError on not found."""
    primary = Path(f"openspec/changes/{change}")
    if primary.is_dir():
        return primary

    archive_dir = Path("openspec/changes/archive")
    if not archive_dir.is_dir():
        raise OSXError(
            "change_not_found", "Change directory does not exist", change=change
        )

    for d in sorted(archive_dir.iterdir()):
        if d.is_dir() and d.name.endswith(f"-{change}"):
            return d

    raise OSXError("change_not_found", "Change directory does not exist", change=change)


def read_json(path: Path) -> Any:
    """Read a JSON file, returning {} if missing.

    CLI behavior: raises typer.Exit(1) on invalid JSON.
    Library callers should use `_read_json` instead.
    """
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        osx_error("invalid_json", f"Invalid JSON in {path}", path=str(path))


def _read_json(path: Path) -> Any:
    """Library version of read_json: raises OSXError on invalid JSON."""
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


def read_json_array(path: Path) -> list[Any]:
    """Read a JSON array file, returning [] if missing.

    CLI behavior: raises typer.Exit(1) on error.
    Library callers should use `_read_json_array` instead.
    """
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        if not isinstance(data, list):
            osx_error("invalid_format", f"{path.name} is not a valid JSON array")
            return []
        return data
    except json.JSONDecodeError:
        osx_error("invalid_json", f"Invalid JSON in {path}")
        return []


def _read_json_array(path: Path) -> list[Any]:
    """Library version of read_json_array: raises OSXError on error."""
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
    data = read_json_array(path)
    data.append(entry)
    write_json(path, data)
    return len(data)


def read_stdin_json() -> Optional[dict]:
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
    except json.JSONDecodeError:
        osx_error("invalid_json", "Input is not valid JSON")


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


def ctx_get(change: str) -> dict:
    change_dir = _find_change_dir(change)

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
        state = _read_json(state_file)
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


def phase_current(change: str) -> dict:
    change_dir = _find_change_dir(change)
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
        write_json(state_file, state)
    else:
        state = _read_json(state_file)

    phase = state.get("phase", "UNKNOWN")
    iteration = state.get("iteration", 0)
    next_phase = get_next_phase(str(phase))
    return {"phase": phase, "next": next_phase, "iteration": iteration}


def phase_next(change: str) -> dict:
    change_dir = _find_change_dir(change)
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
        write_json(state_file, state)
    else:
        state = _read_json(state_file)

    current = state.get("phase", "UNKNOWN")
    if not current:
        raise OSXError("invalid_state", "state.json missing phase field")
    next_phase = get_next_phase(str(current))
    return {"next": next_phase}


def phase_advance(change: str) -> dict:
    change_dir = _find_change_dir(change)
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
        write_json(state_file, state)
    else:
        state = _read_json(state_file)

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
    write_json(state_file, state)

    next_next = get_next_phase(next_phase)
    return {
        "phase": next_phase,
        "previous": current_phase,
        "next": next_next,
        "iteration": 1,
    }


def state_get(change: str) -> dict:
    change_dir = _find_change_dir(change)
    state_file = change_dir / "state.json"

    if not state_file.exists():
        raise OSXError(
            "state_not_found", "state.json does not exist", path=str(state_file)
        )

    state = _read_json(state_file)
    return {
        "phase": state.get("phase", "UNKNOWN"),
        "iteration": state.get("iteration", 0),
        "phase_complete": state.get("phase_complete", False),
        "change": change,
    }


def state_complete(change: str) -> dict:
    change_dir = _find_change_dir(change)
    state_file = change_dir / "state.json"

    if not state_file.exists():
        raise OSXError("state_not_found", "state.json does not exist")

    state = _read_json(state_file)
    state["phase_complete"] = True
    state["last_updated"] = get_timestamp()
    write_json(state_file, state)

    return {"success": True, "phase_complete": True}


def state_transition(
    change: str, target: str, reason: str, details: Optional[str] = None
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

    change_dir = _find_change_dir(change)
    state_file = change_dir / "state.json"

    if not state_file.exists():
        raise OSXError("state_not_found", "state.json does not exist")

    state = _read_json(state_file)
    state["phase_complete"] = True
    state["transition"] = {"target": target, "reason": reason}
    if details:
        state["transition"]["details"] = details
    state["last_updated"] = get_timestamp()
    write_json(state_file, state)

    result: dict = {
        "success": True,
        "transition": {"target": target, "reason": reason},
    }
    if details:
        result["transition"]["details"] = details
    return result


def state_clear_transition(change: str) -> dict:
    change_dir = _find_change_dir(change)
    state_file = change_dir / "state.json"

    if not state_file.exists():
        raise OSXError("state_not_found", "state.json does not exist")

    state = _read_json(state_file)
    state.pop("transition", None)
    state["last_updated"] = get_timestamp()
    write_json(state_file, state)

    return {"success": True, "transition_cleared": True}


def state_set_phase(change: str, phase: str, iteration: Optional[int] = None) -> dict:
    if phase not in PHASES:
        raise OSXError("invalid_phase", f"Invalid phase: {phase}", valid=PHASES)

    change_dir = _find_change_dir(change)
    state_file = change_dir / "state.json"

    if not state_file.exists():
        raise OSXError("state_not_found", "state.json does not exist")

    state = _read_json(state_file)
    previous = state.get("phase", "UNKNOWN")
    state["phase"] = phase
    state["phase_name"] = PHASE_NAMES[phase] if phase in PHASE_NAMES else "UNKNOWN"
    if iteration is not None:
        state["iteration"] = iteration
    state["last_updated"] = get_timestamp()
    write_json(state_file, state)

    return {"success": True, "phase": phase, "previous_phase": previous}


def iterations_get(change: str) -> dict:
    change_dir = _find_change_dir(change)
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
) -> dict:
    change_dir = _find_change_dir(change)
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

    total = _append_to_json_array(iterations_file, entry)
    return {
        "success": True,
        "iteration": entry["iteration"],
        "total_count": total,
    }


def log_get(change: str) -> dict:
    change_dir = _find_change_dir(change)
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
) -> dict:
    change_dir = _find_change_dir(change)
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

    entries = _read_json_array(log_file)
    entry_num = len(entries) + 1
    timestamp = get_timestamp()

    entry["entry"] = entry_num
    entry["timestamp"] = timestamp

    _append_to_json_array(log_file, entry)
    return {
        "success": True,
        "entry": entry_num,
        "phase": entry["phase"],
        "iteration": entry["iteration"],
        "timestamp": timestamp,
    }


def complete_check(change: str) -> dict:
    change_dir = _find_change_dir(change)
    complete_file = change_dir / "complete.json"

    if not complete_file.exists():
        return {"exists": False}

    try:
        json.loads(complete_file.read_text())
        return {"exists": True}
    except json.JSONDecodeError:
        return {"exists": False, "error": "invalid_json"}


def complete_get(change: str) -> dict:
    change_dir = _find_change_dir(change)
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
    change: str, status: Optional[str] = None, blocker_reason: Optional[str] = None
) -> dict:
    change_dir = _find_change_dir(change)
    complete_file = change_dir / "complete.json"
    timestamp = get_timestamp()
    status_value = status or "COMPLETE"

    if status_value == "BLOCKED" and blocker_reason:
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


def validate_skills() -> dict:
    errors: list[dict] = []
    missing_skills: list[str] = []

    for skill in REQUIRED_SKILLS + REQUIRED_CORE_SKILLS:
        skill_path = SKILLS_DIR / skill / "SKILL.md"
        if not skill_path.exists():
            errors.append({"check": "skills", "message": f"Missing skill: {skill}"})
            missing_skills.append(skill)

    if errors:
        return {"valid": False, "errors": errors, "missing_skills": missing_skills}
    return {"valid": True}


def validate_commands() -> dict:
    errors: list[dict] = []

    for phase in PHASES:
        cmd_name = PHASE_COMMANDS.get(phase)
        if cmd_name:
            cmd_path = COMMANDS_DIR / f"{cmd_name}.md"
            if not cmd_path.exists():
                errors.append(
                    {"check": "commands", "message": f"Missing command: {cmd_name}"}
                )

    if errors:
        return {"valid": False, "errors": errors}
    return {"valid": True}


def validate_change_dir(target: str) -> dict:
    change_path = Path(f"openspec/changes/{target}")
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

    required_files = ["tasks.md", "proposal.md", "design.md"]
    for file in required_files:
        if not (change_path / file).exists():
            errors.append(
                {"check": "change-dir", "message": f"Missing required file: {file}"}
            )

    specs_dir = change_path / "specs"
    if not specs_dir.is_dir() or not list(specs_dir.rglob("*.md")):
        errors.append(
            {"check": "change-dir", "message": "No spec files found in specs/"}
        )

    if errors:
        return {"valid": False, "errors": errors}
    return {"valid": True}


def validate_archive(target: str) -> dict:
    archive_dir = Path("openspec/changes/archive")
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


def validate_iterations(target: str) -> dict:
    try:
        change_dir = _find_change_dir(target)
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


def validate_completion(target: str) -> dict:
    errors: list[dict] = []

    try:
        change_dir = _find_change_dir(target)
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

    archive_dir = Path("openspec/changes/archive")
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


# ============================================================
# Internal helpers used by the library functions
# ============================================================


def _read_stdin_json() -> Optional[dict]:
    """Library version of read_stdin_json: raises OSXError on error."""
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


def _append_to_json_array(path: Path, entry: dict) -> int:
    data = _read_json_array(path)
    data.append(entry)
    write_json(path, data)
    return len(data)


def instructions(
    artifact: str, change: Optional[str] = None, json_output: bool = False
) -> None:
    cmd_args = ["openspec", "instructions", artifact]
    if change:
        cmd_args.extend(["--change", change])
    if json_output:
        cmd_args.append("--json")

    try:
        result = subprocess.run(cmd_args, capture_output=True, text=True)
        print(result.stdout, end="")
        if result.returncode != 0:
            print(result.stderr, file=sys.stderr, end="")
            raise typer.Exit(result.returncode)
    except FileNotFoundError as e:
        raise OSXError("cli_not_found", "openspec CLI not found in PATH") from e


# ============================================================
# Typer command wrappers: thin layer that calls library functions
# and prints their result. Used for `python -m source.lib.osx ...`
# and `typer.testing.CliRunner.invoke(osx.app, ...)`.
# ============================================================


def _print_or_exit(data: dict) -> None:
    """Print the dict and exit 1 if it indicates failure."""
    osx_output(data)
    if data.get("valid") is False:
        raise typer.Exit(1)
    if data.get("error"):
        raise typer.Exit(1)


def _call_library(fn, *args, **kwargs):
    """Call a library function, catching OSXError and re-raising as osx_error."""
    try:
        return fn(*args, **kwargs)
    except OSXError as e:
        osx_error(e.code, e.message, **e.context)


@app.command(name="baseline")
def baseline_cmd(
    action: str = typer.Argument(..., help="Action: record, get"),
) -> None:
    if action == "record":
        data = _call_library(baseline_record)
    elif action == "get":
        data = _call_library(baseline_get)
    else:
        osx_error("invalid_action", f"Unknown action: {action}", valid="record, get")
        return
    osx_output(data)


@app.command(name="ctx")
def ctx_cmd(
    action: str = typer.Argument(..., help="Action: get"),
    change: str = typer.Argument(..., help="Change name"),
) -> None:
    if action != "get":
        osx_error("invalid_action", f"Unknown action: {action}", valid="get")
        return
    data = _call_library(ctx_get, change)
    osx_output(data)


@app.command(name="git")
def git_cmd(
    action: str = typer.Argument(..., help="Action: get"),
    change: str = typer.Argument(..., help="Change name"),
) -> None:
    if action != "get":
        osx_error("invalid_action", f"Unknown action: {action}", valid="get")
        return
    data = _call_library(git_get, change)
    osx_output(data)


@app.command(name="phase")
def phase_cmd(
    action: str = typer.Argument(..., help="Action: current, next, advance"),
    change: str = typer.Argument(..., help="Change name"),
) -> None:
    if action == "current":
        data = _call_library(phase_current, change)
    elif action == "next":
        data = _call_library(phase_next, change)
    elif action == "advance":
        data = _call_library(phase_advance, change)
    else:
        osx_error(
            "invalid_action",
            f"Unknown action: {action}",
            valid="current, next, advance",
        )
        return
    osx_output(data)


@app.command(name="state")
def state_cmd(
    action: str = typer.Argument(
        ..., help="Action: get, complete, transition, clear-transition, set-phase"
    ),
    change: str = typer.Argument(..., help="Change name"),
    phase: Optional[str] = typer.Argument(None, help="Phase (for set-phase)"),
    target: Optional[str] = typer.Argument(None, help="Target phase (for transition)"),
    reason: Optional[str] = typer.Argument(
        None, help="Transition reason (for transition)"
    ),
    details: Optional[str] = typer.Argument(
        None, help="Transition details (for transition)"
    ),
    iteration: Optional[int] = typer.Option(
        None, "--iteration", help="Iteration number"
    ),
) -> None:
    if action == "get":
        data = _call_library(state_get, change)
    elif action == "complete":
        data = _call_library(state_complete, change)
    elif action == "transition":
        data = _call_library(state_transition, change, target, reason, details)
    elif action == "clear-transition":
        data = _call_library(state_clear_transition, change)
    elif action == "set-phase":
        data = _call_library(state_set_phase, change, phase, iteration)
    else:
        osx_error(
            "invalid_action",
            f"Unknown action: {action}",
            valid="get, complete, transition, clear-transition, set-phase",
        )
        return
    osx_output(data)


@app.command(name="iterations")
def iterations_cmd(
    action: str = typer.Argument(..., help="Action: get, append"),
    change: str = typer.Argument(..., help="Change name"),
    phase: Optional[str] = typer.Option(None, "--phase", help="Phase"),
    iteration: Optional[int] = typer.Option(
        None, "--iteration", help="Iteration number"
    ),
    summary: Optional[str] = typer.Option(None, "--summary", help="Summary text"),
    status: Optional[str] = typer.Option(None, "--status", help="Status"),
    notes: Optional[str] = typer.Option(None, "--notes", help="Notes"),
    commit_hash: Optional[str] = typer.Option(
        None, "--commit-hash", help="Git commit hash"
    ),
    issues: Optional[str] = typer.Option(None, "--issues", help="Issues (JSON)"),
    artifacts_modified: Optional[str] = typer.Option(
        None, "--artifacts-modified", help="Artifacts modified (JSON)"
    ),
    decisions: Optional[str] = typer.Option(
        None, "--decisions", help="Decisions (JSON)"
    ),
    errors: Optional[str] = typer.Option(None, "--errors", help="Errors (JSON)"),
    extra: Optional[str] = typer.Option(
        None, "--extra", help="Additional fields (JSON object)"
    ),
) -> None:
    if action == "get":
        data = _call_library(iterations_get, change)
    elif action == "append":
        data = _call_library(
            iterations_append,
            change,
            iteration=iteration,
            phase=phase,
            summary=summary,
            status=status,
            notes=notes,
            commit_hash=commit_hash,
            issues=issues,
            artifacts_modified=artifacts_modified,
            decisions=decisions,
            errors=errors,
            extra=extra,
        )
    else:
        osx_error("invalid_action", f"Unknown action: {action}", valid="get, append")
        return
    osx_output(data)


@app.command(name="log")
def log_cmd(
    action: str = typer.Argument(..., help="Action: get, append"),
    change: str = typer.Argument(..., help="Change name"),
    phase: Optional[str] = typer.Option(None, "--phase", help="Phase"),
    iteration: Optional[int] = typer.Option(
        None, "--iteration", help="Iteration number"
    ),
    summary: Optional[str] = typer.Option(None, "--summary", help="Summary text"),
    commit_hash: Optional[str] = typer.Option(
        None, "--commit-hash", help="Git commit hash"
    ),
    next_steps: Optional[str] = typer.Option(None, "--next-steps", help="Next steps"),
    issues: Optional[str] = typer.Option(None, "--issues", help="Issues (JSON)"),
    artifacts_modified: Optional[str] = typer.Option(
        None, "--artifacts-modified", help="Artifacts modified (JSON)"
    ),
    decisions: Optional[str] = typer.Option(
        None, "--decisions", help="Decisions (JSON)"
    ),
    errors: Optional[str] = typer.Option(None, "--errors", help="Errors (JSON)"),
    extra: Optional[str] = typer.Option(
        None, "--extra", help="Additional fields (JSON object)"
    ),
) -> None:
    if action == "get":
        data = _call_library(log_get, change)
    elif action == "append":
        data = _call_library(
            log_append,
            change,
            phase=phase,
            iteration=iteration,
            summary=summary,
            commit_hash=commit_hash,
            next_steps=next_steps,
            issues=issues,
            artifacts_modified=artifacts_modified,
            decisions=decisions,
            errors=errors,
            extra=extra,
        )
    else:
        osx_error("invalid_action", f"Unknown action: {action}", valid="get, append")
        return
    osx_output(data)


@app.command(name="complete")
def complete_cmd(
    action: str = typer.Argument(..., help="Action: check, get, set"),
    change: str = typer.Argument(..., help="Change name"),
    status: Optional[str] = typer.Argument(None, help="Status (COMPLETE or BLOCKED)"),
    blocker_reason: Optional[str] = typer.Option(
        None, "--blocker-reason", help="Blocker reason"
    ),
) -> None:
    if action == "check":
        data = _call_library(complete_check, change)
        osx_output(data)
        if not data.get("exists", False):
            raise typer.Exit(1)
    elif action == "get":
        data = _call_library(complete_get, change)
        osx_output(data)
    elif action == "set":
        data = _call_library(complete_set, change, status, blocker_reason)
        osx_output(data)
    else:
        osx_error(
            "invalid_action", f"Unknown action: {action}", valid="check, get, set"
        )
        return


@app.command(name="validate")
def validate_cmd(
    action: str = typer.Argument(
        ...,
        help="Action: json, skills, commands, change-dir, archive, iterations, completion",
    ),
    target: Optional[str] = typer.Argument(
        None, help="Target (file path or change name depending on action)"
    ),
) -> None:
    if action == "json":
        if target is None:
            osx_error("missing_field", "file path required for json validation")
            return
        data = validate_json(target)
    elif action == "skills":
        data = validate_skills()
    elif action == "commands":
        data = validate_commands()
    elif action == "change-dir":
        if target is None:
            osx_error("missing_field", "change name required for change-dir validation")
            return
        data = validate_change_dir(target)
    elif action == "archive":
        if target is None:
            osx_error("missing_field", "change name required for archive validation")
            return
        data = validate_archive(target)
    elif action == "iterations":
        if target is None:
            osx_error("missing_field", "change name required for iterations validation")
            return
        data = validate_iterations(target)
    elif action == "completion":
        if target is None:
            osx_error("missing_field", "change name required for completion validation")
            return
        data = validate_completion(target)
    else:
        osx_error(
            "invalid_action",
            f"Unknown action: {action}",
            valid="json, skills, commands, change-dir, archive, iterations, completion",
        )
        return

    osx_output(data)
    if data.get("valid") is False:
        raise typer.Exit(1)


@app.command(name="instructions")
def instructions_cmd(
    artifact: str = typer.Argument(..., help="Artifact type (e.g., specs, apply)"),
    change: Optional[str] = typer.Option(None, "--change", help="Change name"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    try:
        instructions(artifact, change, json_output)
    except OSXError as e:
        osx_error(e.code, e.message, **e.context)


if __name__ == "__main__":
    app()
