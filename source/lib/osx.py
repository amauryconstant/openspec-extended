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


def osx_error(code: str, message: str, **context) -> None:
    result = {"error": code, "message": message}
    result.update(context)
    print(json.dumps(result), file=sys.stderr)
    raise typer.Exit(1)


def osx_output(data: dict) -> None:
    print(json.dumps(data))


def get_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def find_change_dir(change: str) -> Path:
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


def read_json(path: Path) -> Any:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        osx_error("invalid_json", f"Invalid JSON in {path}", path=str(path))


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", delete=False, dir=path.parent, suffix=".json"
    ) as f:
        json.dump(data, f, indent=2)
        f.flush()
        Path(f.name).replace(path)


def read_json_array(path: Path) -> list[Any]:
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


@app.command(name="baseline")
def baseline_cmd(
    action: str = typer.Argument(..., help="Action: record, get"),
) -> None:
    if action == "record":
        try:
            subprocess.check_output(
                ["git", "rev-parse", "--is-inside-work-tree"],
                stderr=subprocess.DEVNULL,
                text=True,
            )
        except (subprocess.CalledProcessError, FileNotFoundError):
            osx_error("not_git_repo", "Current directory is not a git repository")

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
        except (subprocess.CalledProcessError, FileNotFoundError):
            osx_error("git_error", "Failed to get git info")

        timestamp = get_timestamp()

        baseline_file = Path(".openspec-baseline.json")
        data = {
            "commit": commit,
            "branch": branch,
            "timestamp": timestamp,
        }
        write_json(baseline_file, data)
        osx_output(data)

    elif action == "get":
        baseline_file = Path(".openspec-baseline.json")

        if not baseline_file.exists():
            osx_error("baseline_not_found", ".openspec-baseline.json does not exist")

        try:
            data = json.loads(baseline_file.read_text())
        except json.JSONDecodeError:
            osx_error("invalid_json", ".openspec-baseline.json contains invalid JSON")

        osx_output(data)

    else:
        osx_error("invalid_action", f"Unknown action: {action}", valid="record, get")


@app.command(name="ctx")
def ctx_cmd(
    action: str = typer.Argument(..., help="Action: get"),
    change: str = typer.Argument(..., help="Change name"),
) -> None:
    if action != "get":
        osx_error("invalid_action", f"Unknown action: {action}", valid="get")

    change_dir = find_change_dir(change)

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

    def get_state():
        state_file = change_dir / "state.json"
        if not state_file.exists():
            return {"phase": "UNKNOWN", "iteration": 0, "phase_complete": False}
        state = read_json(state_file)
        return {
            "phase": state.get("phase", "UNKNOWN"),
            "iteration": state.get("iteration", 0),
            "phase_complete": state.get("phase_complete", False),
        }

    def get_git():
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

    decision_log = read_json_array(change_dir / "decision-log.json")
    iterations = read_json_array(change_dir / "iterations.json")

    osx_output(
        {
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
    )


@app.command(name="git")
def git_cmd(
    action: str = typer.Argument(..., help="Action: get"),
    change: str = typer.Argument(..., help="Change name"),
) -> None:
    if action != "get":
        osx_error("invalid_action", f"Unknown action: {action}", valid="get")

    change_dir = find_change_dir(change)

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

    osx_output(result)


@app.command(name="phase")
def phase_cmd(
    action: str = typer.Argument(..., help="Action: current, next, advance"),
    change: str = typer.Argument(..., help="Change name"),
) -> None:
    change_dir = find_change_dir(change)
    state_file = change_dir / "state.json"

    if "archive" in str(change_dir) and not state_file.exists():
        osx_error("archived", "Change is archived, no active state")

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
        state = read_json(state_file)

    if action == "current":
        phase = state.get("phase", "UNKNOWN")
        iteration = state.get("iteration", 0)
        next_phase = get_next_phase(str(phase))
        osx_output({"phase": phase, "next": next_phase, "iteration": iteration})
    elif action == "next":
        current = state.get("phase", "UNKNOWN")
        if not current:
            osx_error("invalid_state", "state.json missing phase field")
        next_phase = get_next_phase(str(current))
        osx_output({"next": next_phase})
    elif action == "advance":
        current_phase = state.get("phase", "UNKNOWN")
        if not current_phase:
            osx_error("invalid_state", "state.json missing phase field")

        next_phase = get_next_phase(str(current_phase))
        timestamp = get_timestamp()

        state["phase"] = next_phase
        state["phase_name"] = PHASE_NAMES.get(next_phase, "UNKNOWN")
        state["iteration"] = 1
        state["phase_complete"] = False
        state["last_updated"] = timestamp
        write_json(state_file, state)

        next_next = get_next_phase(next_phase)
        osx_output(
            {
                "phase": next_phase,
                "previous": current_phase,
                "next": next_next,
                "iteration": 1,
            }
        )
    else:
        osx_error(
            "invalid_action",
            f"Unknown action: {action}",
            valid="current, next, advance",
        )


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
    change_dir = find_change_dir(change)
    state_file = change_dir / "state.json"

    if action == "get":
        if not state_file.exists():
            osx_error(
                "state_not_found", "state.json does not exist", path=str(state_file)
            )

        state = read_json(state_file)
        osx_output(
            {
                "phase": state.get("phase", "UNKNOWN"),
                "iteration": state.get("iteration", 0),
                "phase_complete": state.get("phase_complete", False),
                "change": change,
            }
        )

    elif action == "complete":
        if not state_file.exists():
            osx_error("state_not_found", "state.json does not exist")

        state = read_json(state_file)
        state["phase_complete"] = True
        state["last_updated"] = get_timestamp()
        write_json(state_file, state)

        osx_output({"success": True, "phase_complete": True})

    elif action == "transition":
        if target is None or reason is None:
            osx_error("missing_field", "target and reason required for transition")

        if target not in PHASES:
            osx_error("invalid_target", f"Invalid target phase: {target}", valid=PHASES)

        if reason not in VALID_TRANSITION_REASONS:
            osx_error(
                "invalid_reason",
                f"Invalid reason: {reason}",
                valid=VALID_TRANSITION_REASONS,
            )

        if not state_file.exists():
            osx_error("state_not_found", "state.json does not exist")

        state = read_json(state_file)
        state["phase_complete"] = True
        state["transition"] = {"target": target, "reason": reason}
        if details:
            state["transition"]["details"] = details
        state["last_updated"] = get_timestamp()
        write_json(state_file, state)

        result = {
            "success": True,
            "transition": {"target": target, "reason": reason},
        }
        if details:
            result["transition"]["details"] = details
        osx_output(result)

    elif action == "clear-transition":
        if not state_file.exists():
            osx_error("state_not_found", "state.json does not exist")

        state = read_json(state_file)
        state.pop("transition", None)
        state["last_updated"] = get_timestamp()
        write_json(state_file, state)

        osx_output({"success": True, "transition_cleared": True})

    elif action == "set-phase":
        if phase is None:
            osx_error("missing_field", "phase required for set-phase")

        if phase not in PHASES:
            osx_error("invalid_phase", f"Invalid phase: {phase}", valid=PHASES)

        if not state_file.exists():
            osx_error("state_not_found", "state.json does not exist")

        state = read_json(state_file)
        previous = state.get("phase", "UNKNOWN")
        state["phase"] = phase
        state["phase_name"] = PHASE_NAMES[phase] if phase in PHASE_NAMES else "UNKNOWN"
        if iteration is not None:
            state["iteration"] = iteration
        state["last_updated"] = get_timestamp()
        write_json(state_file, state)

        osx_output({"success": True, "phase": phase, "previous_phase": previous})

    else:
        osx_error(
            "invalid_action",
            f"Unknown action: {action}",
            valid="get, complete, transition, clear-transition, set-phase",
        )


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
    change_dir = find_change_dir(change)
    iterations_file = change_dir / "iterations.json"

    if action == "get":
        if not iterations_file.exists():
            osx_output({"count": 0, "iterations": []})
            return

        iterations = read_json_array(iterations_file)
        iteration_nums = [i.get("iteration") for i in iterations if "iteration" in i]
        osx_output({"count": len(iterations), "iterations": iteration_nums})

    elif action == "append":
        stdin_data = read_stdin_json()
        if stdin_data is not None:
            entry = stdin_data
        else:
            if iteration is None or phase is None:
                osx_error(
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
                except json.JSONDecodeError:
                    osx_error("invalid_json", "issues must be valid JSON")
            if artifacts_modified:
                try:
                    entry["artifacts_modified"] = json.loads(artifacts_modified)
                except json.JSONDecodeError:
                    osx_error("invalid_json", "artifacts_modified must be valid JSON")
            if decisions:
                try:
                    entry["decisions"] = json.loads(decisions)
                except json.JSONDecodeError:
                    osx_error("invalid_json", "decisions must be valid JSON")
            if errors:
                try:
                    entry["errors"] = json.loads(errors)
                except json.JSONDecodeError:
                    osx_error("invalid_json", "errors must be valid JSON")
            if extra:
                try:
                    extra_data = json.loads(extra)
                    if isinstance(extra_data, dict):
                        entry.update(extra_data)
                except json.JSONDecodeError:
                    osx_error("invalid_json", "extra must be valid JSON object")

        if "iteration" not in entry:
            osx_error("missing_field", "iteration field is required")

        entry.setdefault("timestamp", get_timestamp())

        total = append_to_json_array(iterations_file, entry)
        osx_output(
            {
                "success": True,
                "iteration": entry["iteration"],
                "total_count": total,
            }
        )

    else:
        osx_error("invalid_action", f"Unknown action: {action}", valid="get, append")


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
    change_dir = find_change_dir(change)
    log_file = change_dir / "decision-log.json"

    if action == "get":
        if not log_file.exists():
            osx_output({"count": 0, "entries": []})
            return

        entries = read_json_array(log_file)
        osx_output({"count": len(entries), "entries": entries})

    elif action == "append":
        stdin_data = read_stdin_json()
        if stdin_data is not None:
            entry = stdin_data
        else:
            if iteration is None or phase is None:
                osx_error(
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
                except json.JSONDecodeError:
                    osx_error("invalid_json", "issues must be valid JSON")
            if artifacts_modified:
                try:
                    entry["artifacts_modified"] = json.loads(artifacts_modified)
                except json.JSONDecodeError:
                    osx_error("invalid_json", "artifacts_modified must be valid JSON")
            if decisions:
                try:
                    entry["decisions"] = json.loads(decisions)
                except json.JSONDecodeError:
                    osx_error("invalid_json", "decisions must be valid JSON")
            if errors:
                try:
                    entry["errors"] = json.loads(errors)
                except json.JSONDecodeError:
                    osx_error("invalid_json", "errors must be valid JSON")
            if extra:
                try:
                    extra_data = json.loads(extra)
                    if isinstance(extra_data, dict):
                        entry.update(extra_data)
                except json.JSONDecodeError:
                    osx_error("invalid_json", "extra must be valid JSON object")

        if "phase" not in entry:
            osx_error("missing_field", "phase field is required")
        if "iteration" not in entry:
            osx_error("missing_field", "iteration field is required")

        entries = read_json_array(log_file)
        entry_num = len(entries) + 1
        timestamp = get_timestamp()

        entry["entry"] = entry_num
        entry["timestamp"] = timestamp

        append_to_json_array(log_file, entry)
        osx_output(
            {
                "success": True,
                "entry": entry_num,
                "phase": entry["phase"],
                "iteration": entry["iteration"],
                "timestamp": timestamp,
            }
        )

    else:
        osx_error("invalid_action", f"Unknown action: {action}", valid="get, append")


@app.command(name="complete")
def complete_cmd(
    action: str = typer.Argument(..., help="Action: check, get, set"),
    change: str = typer.Argument(..., help="Change name"),
    status: Optional[str] = typer.Argument(None, help="Status (COMPLETE or BLOCKED)"),
    blocker_reason: Optional[str] = typer.Option(
        None, "--blocker-reason", help="Blocker reason"
    ),
) -> None:
    change_dir = find_change_dir(change)
    complete_file = change_dir / "complete.json"

    if action == "check":
        if not complete_file.exists():
            osx_output({"exists": False})
            raise typer.Exit(1)

        try:
            json.loads(complete_file.read_text())
            osx_output({"exists": True})
        except json.JSONDecodeError:
            osx_output({"exists": False, "error": "invalid_json"})
            raise typer.Exit(1)

    elif action == "get":
        if not complete_file.exists():
            osx_error("complete_not_found", "complete.json does not exist")

        try:
            data = json.loads(complete_file.read_text())
        except json.JSONDecodeError:
            osx_error("invalid_json", "complete.json contains invalid JSON")

        result = {
            "status": data.get("status", "UNKNOWN"),
            "with_blocker": data.get("with_blocker", False),
        }
        if data.get("blocker_reason"):
            result["blocker_reason"] = data["blocker_reason"]

        osx_output(result)

    elif action == "set":
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
            osx_output(
                {
                    "status": status_value,
                    "with_blocker": True,
                    "blocker_reason": blocker_reason,
                }
            )
        else:
            data = {
                "status": status_value,
                "with_blocker": False,
                "timestamp": timestamp,
            }
            write_json(complete_file, data)
            osx_output({"status": status_value, "with_blocker": False})

    else:
        osx_error(
            "invalid_action", f"Unknown action: {action}", valid="check, get, set"
        )


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
            raise SystemExit(1)

        file_path = Path(target)

        if not file_path.exists():
            osx_output(
                {
                    "valid": False,
                    "errors": [
                        {"check": "json", "message": f"File not found: {target}"}
                    ],
                }
            )
            raise typer.Exit(1)

        try:
            json.loads(file_path.read_text())
            osx_output({"valid": True})
        except json.JSONDecodeError:
            osx_output(
                {
                    "valid": False,
                    "errors": [
                        {"check": "json", "message": f"Invalid JSON in file: {target}"}
                    ],
                }
            )
            raise typer.Exit(1)

    elif action == "skills":
        errors = []
        missing_skills = []

        for skill in REQUIRED_SKILLS + REQUIRED_CORE_SKILLS:
            skill_path = SKILLS_DIR / skill / "SKILL.md"
            if not skill_path.exists():
                errors.append({"check": "skills", "message": f"Missing skill: {skill}"})
                missing_skills.append(skill)

        if errors:
            osx_output(
                {"valid": False, "errors": errors, "missing_skills": missing_skills}
            )
            raise typer.Exit(1)

        osx_output({"valid": True})

    elif action == "commands":
        errors = []

        for phase in PHASES:
            cmd_name = PHASE_COMMANDS.get(phase)
            if cmd_name:
                cmd_path = COMMANDS_DIR / f"{cmd_name}.md"
                if not cmd_path.exists():
                    errors.append(
                        {"check": "commands", "message": f"Missing command: {cmd_name}"}
                    )

        if errors:
            osx_output({"valid": False, "errors": errors})
            raise typer.Exit(1)

        osx_output({"valid": True})

    elif action == "change-dir":
        if target is None:
            osx_error("missing_field", "change name required for change-dir validation")

        change_path = Path(f"openspec/changes/{target}")
        errors = []

        if not change_path.is_dir():
            osx_output(
                {
                    "valid": False,
                    "errors": [
                        {
                            "check": "change-dir",
                            "message": f"Change directory not found: {change_path}",
                        }
                    ],
                }
            )
            raise typer.Exit(1)

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
            osx_output({"valid": False, "errors": errors})
            raise typer.Exit(1)

        osx_output({"valid": True})

    elif action == "archive":
        if target is None:
            osx_error("missing_field", "change name required for archive validation")

        archive_dir = Path("openspec/changes/archive")
        archives = []

        if archive_dir.is_dir():
            for d in archive_dir.iterdir():
                if d.is_dir() and d.name.endswith(f"-{target}"):
                    archives.append(d)

        if len(archives) == 0:
            osx_output(
                {
                    "valid": False,
                    "errors": [{"check": "archive", "message": "Change not archived"}],
                }
            )
            raise typer.Exit(1)

        if len(archives) > 1:
            osx_output(
                {
                    "valid": False,
                    "errors": [
                        {
                            "check": "archive",
                            "message": f"Multiple archives found for change: {len(archives)}",
                        }
                    ],
                }
            )
            raise typer.Exit(1)

        osx_output({"valid": True, "archive": str(archives[0])})

    elif action == "iterations":
        if target is None:
            osx_error("missing_field", "change name required for iterations validation")
            raise SystemExit(1)

        try:
            change_dir = find_change_dir(target)
        except SystemExit:
            osx_output(
                {
                    "valid": False,
                    "errors": [
                        {"check": "iterations", "message": "Change directory not found"}
                    ],
                }
            )
            raise typer.Exit(1)

        iterations_file = change_dir / "iterations.json"

        if not iterations_file.exists():
            osx_output(
                {
                    "valid": False,
                    "errors": [
                        {"check": "iterations", "message": "iterations.json not found"}
                    ],
                }
            )
            raise typer.Exit(1)

        try:
            json.loads(iterations_file.read_text())
        except json.JSONDecodeError:
            osx_output(
                {
                    "valid": False,
                    "errors": [
                        {
                            "check": "iterations",
                            "message": "iterations.json contains invalid JSON",
                        }
                    ],
                }
            )
            raise typer.Exit(1)

        osx_output({"valid": True})

    elif action == "completion":
        if target is None:
            osx_error("missing_field", "change name required for completion validation")
            raise SystemExit(1)

        errors = []

        try:
            change_dir = find_change_dir(target)
        except SystemExit:
            osx_output(
                {
                    "valid": False,
                    "errors": [
                        {"check": "completion", "message": "Change directory not found"}
                    ],
                }
            )
            raise typer.Exit(1)

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
            errors.append(
                {"check": "completion", "message": "iterations.json not found"}
            )
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
            errors.append(
                {"check": "completion", "message": "decision-log.json not found"}
            )

        archive_dir = Path("openspec/changes/archive")
        archives = []
        if archive_dir.is_dir():
            for d in archive_dir.iterdir():
                if d.is_dir() and d.name.endswith(f"-{target}"):
                    archives.append(d)

        if len(archives) == 0:
            errors.append(
                {"check": "completion", "message": "Archive validation failed"}
            )

        if errors:
            osx_output({"valid": False, "errors": errors})
            raise typer.Exit(1)

        osx_output({"valid": True})

    else:
        osx_error(
            "invalid_action",
            f"Unknown action: {action}",
            valid="json, skills, commands, change-dir, archive, iterations, completion",
        )


@app.command(name="instructions")
def instructions_cmd(
    artifact: str = typer.Argument(..., help="Artifact type (e.g., specs, apply)"),
    change: Optional[str] = typer.Option(None, "--change", help="Change name"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
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
    except FileNotFoundError:
        osx_error("cli_not_found", "openspec CLI not found in PATH")


if __name__ == "__main__":
    app()
