#!/usr/bin/env python3
# ruff: noqa: EXE001 - shebang is intentional (PyInstaller entry may invoke it directly)
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
import os
import re
import select
import subprocess
import sys
import tempfile
from contextvars import ContextVar
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import toml
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

MIN_OPENSPEC_VERSION: tuple[int, int, int] = (1, 13, 0)


def get_core_version(timeout: int = 10) -> tuple[int, int, int] | None:
    """Parse `openspec --version` stdout into a (major, minor, patch) tuple.

    Returns None if the binary is missing, errors, or the version cannot
    be parsed. Used by the orchestrator to enforce the minimum core version
    before relying on the v1.13.0 contract surface:

    - store resolution and ``--store <id>`` (v1.5.0+)
    - ``requires`` array on each artifact in ``openspec status --json``
      (v1.7.0+)
    - ``openspec instructions archive`` read-only surface (v1.7.0+)
    - ``skip_specs: true`` change metadata (v1.7.0+)
    - ``defaultStore`` machine-level fallback (v1.7.0+)
    - ``isPlanningComplete`` field separating planning from implementation
      (v1.8.0+). ``validate_change_dir`` consults this field directly;
      pass ``OPENSPEC_EXTENDED_NO_PLANNING_CORE=1`` to force the local
      file-existence fallback (offline CI without ``openspec`` on PATH).
    - ``openspec validate --archived`` (v1.9.0+)
    - ``openspec init --language <lang>`` (v1.10.0+)
    - ``openspec status --all`` single-process sweep (v1.11.0+)
    - ``openspec show --diff`` requirement-level diff (v1.11.0+)
    - ``retire_capabilities: true`` change metadata (v1.8.0+)
    - ``openspec validate --report findings`` opt-in bulk-scope
      informational findings (v1.12.0+)
    - ``missingPrerequisites`` array in ``openspec instructions apply --json``
      naming the full build-order chain (not just the first hop)
      (v1.13.0+). ``fetch_apply_prerequisites`` reads it.
    - ``openspec list --specs`` and ``openspec show <id> --type spec
      --json --no-scenarios`` filtered spec read (v1.13.0+).
      ``list_specs`` / ``show_spec`` consume them.
    - ``retire_capabilities`` no longer refuses specs with wrapped scenario
      bullets or ``+``-marker bullets (v1.13.0+); ``osx-phase6``'s
      precondition check is relaxed accordingly.
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
    "osx-review-artifacts",
    "osx-review-test-compliance",
    "osx-commit",
]
# `osx-changelog` and `osx-maintain-docs` are intentionally absent from
# REQUIRED_SKILLS: they are slash commands (with self-contained bodies), not
# skills. They do not appear under `skills/<name>/SKILL.md` on either platform,
# so the pre-flight skill gate is the wrong surface. The slash-command body is
# validated separately by `validate_commands` if needed. See `osx-concepts`
# §2.5 for the full taxonomy.
#
# `osx-workflow` is also absent: it is gated by `--with-autonomous` install and
# added to the required set only when the autonomous workflow is enabled.

REQUIRED_CORE_SKILLS = [
    "osc-propose",
    "osc-explore",
    "osc-new-change",
    "osc-continue-change",
    "osc-apply-change",
    "osc-update-change",
    "osc-ff-change",
    "osc-verify-change",
    "osc-sync-specs",
    "osc-archive-change",
    "osc-bulk-archive-change",
    "osc-onboard",
]

AUTONOMOUS_RESOURCE_NAMES = frozenset(
    {
        "osx-analyzer",
        "osx-builder",
        "osx-maintainer",
        "osx-reviewer",
        "osx-phase0",
        "osx-phase1",
        "osx-phase2",
        "osx-phase3",
        "osx-phase4",
        "osx-phase5",
        "osx-phase6",
        "osx-workflow",
    }
)

# Phase 1D: ``detect_platform`` / ``skills_dir`` / ``commands_dir`` /
# ``_load_manifest`` / ``_command_resolved_for_phase`` /
# ``validate_commands`` are registry-driven. ``REGISTRY`` is imported
# at module top-level so consumers (``engine.py``, ``runner.py``,
# ``cli.py``) read the same source of truth; ``source.tools`` is a leaf
# module with only stdlib imports, so there's no cycle.
from source.tools import REGISTRY


def detect_platform(project_root: Path) -> str:
    """Return the active tool id for ``project_root``.

    Walks ``REGISTRY`` in registration order and returns the
    ``tool_id`` of the first adapter whose ``detect_paths`` includes
    an existing directory. Defaults to the first registered tool
    (``"opencode"`` today; pinned by
    ``tests/unit/test_platform_detection.py::TestDetectPlatformDefaultsToFirstRegistered``)
    when no marker is present — matches pre-1D behavior byte-for-byte.

    Opencode wins ties by being registered first (locked by
    ``tests/unit/test_tool_registry.py``).
    """
    for adapter in REGISTRY.values():
        if any((project_root / p).is_dir() for p in adapter.detect_paths):
            return adapter.tool_id
    return next(iter(REGISTRY))


def skills_dir(project_root: Path) -> Path:
    """Path to the deployed skills root for the active tool.

    Resolves through ``detect_platform`` so every adapter's
    ``skills_dir`` is honored. Today: ``.opencode/skills`` or
    ``.claude/skills``; future adapters add their own.
    """
    adapter = REGISTRY[detect_platform(project_root)]
    return project_root / adapter.skills_dir / "skills"


def commands_dir(project_root: Path) -> Path:
    """Path to the deployed commands root for the active tool.

    Resolves through the adapter's ``commands_dir`` field — flat
    (``commands``) for opencode, nested (``commands/osx``) for claude.
    ``Path / "commands/osx"`` correctly produces the nested form
    because ``pathlib.PurePath.__truediv__`` treats strings with
    embedded ``/`` as nested relative path components.
    """
    adapter = REGISTRY[detect_platform(project_root)]
    return project_root / adapter.skills_dir / adapter.commands_dir


class OSXError(Exception):
    """Raised by library functions on error. Caught by the CLI wrappers."""

    def __init__(self, code: str, message: str, **context) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.context = context


def get_timestamp() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


current_store: ContextVar[str | None] = ContextVar("osx_current_store", default=None)

_PATHS_CACHE: dict[tuple[str, str | None], dict] = {}


def _run_openspec_json(args: list, timeout: int = 10) -> dict:
    """Run `openspec <args...> --json` and return the parsed JSON dict.

    Raises:
      OSXError("cli_not_found")  — openspec binary not on PATH
      OSXError("cli_error")      — non-zero exit or timeout
      OSXError("invalid_json")   — stdout is not valid JSON
    """
    cmd = ["openspec", *args, "--json"]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout, check=False
        )
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


def _fetch_planning_status(change_id: str, *, store: str | None = None) -> dict | None:
    """Call ``openspec status --change <id> [--store <id>] --json`` and return
    the parsed envelope, or ``None`` when the CLI is missing or the call fails.

    Used by ``validate_change_dir`` to consult core's ``isPlanningComplete``
    signal (v1.8.0+) before falling back to a local file-existence check.
    """
    effective_store = store if store is not None else current_store.get()
    args = ["status", "--change", change_id]
    if effective_store:
        args.extend(["--store", effective_store])
    try:
        result = _run_openspec_json(args)
    except OSXError:
        return None
    return result if isinstance(result, dict) else None


def resolve_change_paths(change: str, store: str | None = None) -> dict:
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
        planning_home_str: str | None
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


def _find_change_dir(change: str, store: str | None = None) -> Path:
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


def _read_stdin_json() -> dict | None:
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


def ctx_get(change: str, *, store: str | None = None) -> dict:
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


def phase_current(change: str, *, store: str | None = None) -> dict:
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


def phase_next(change: str, *, store: str | None = None) -> dict:
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


def phase_advance(change: str, *, store: str | None = None) -> dict:
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


def state_get(change: str, *, store: str | None = None) -> dict:
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


def state_complete(change: str, *, store: str | None = None) -> dict:
    change_dir = _find_change_dir(change, store=store)
    state_file = change_dir / "state.json"

    if not state_file.exists():
        raise OSXError("state_not_found", "state.json does not exist")

    state = _read_state(change_dir)
    state["phase_complete"] = True
    state.pop("routes_pending", None)
    state["last_updated"] = get_timestamp()
    _write_state(change_dir, state)

    return {"success": True, "phase_complete": True}


def state_transition(
    change: str,
    target: str,
    reason: str,
    details: str | None = None,
    *,
    store: str | None = None,
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


def state_clear_transition(change: str, *, store: str | None = None) -> dict:
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
    iteration: int | None = None,
    *,
    store: str | None = None,
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
    state["phase_name"] = PHASE_NAMES.get(phase, "UNKNOWN")
    if iteration is not None:
        state["iteration"] = iteration
    state["last_updated"] = get_timestamp()
    _write_state(change_dir, state)

    return {"success": True, "phase": phase, "previous_phase": previous}


def state_set_routes(
    change: str,
    routes: list[str],
    *,
    store: str | None = None,
) -> dict:
    """Record pending routes from a read-only phase (e.g. PHASE0).

    Routes are slash-command names the user should run externally to fix
    issues the phase found (e.g. ``/osx-modify``, ``/opsx:update``,
    ``/opsx:continue``). The engine halts cleanly when ``routes_pending``
    is non-empty after a phase, so the user actually has time to run them.
    """
    change_dir = _find_change_dir(change, store=store)
    state_file = change_dir / "state.json"

    if not state_file.exists():
        raise OSXError("state_not_found", "state.json does not exist")

    routes = [r for r in routes if r]
    state = _read_state(change_dir)
    state["routes_pending"] = routes
    state["last_updated"] = get_timestamp()
    _write_state(change_dir, state)

    return {"success": True, "routes_pending": routes}


def state_clear_routes(change: str, *, store: str | None = None) -> dict:
    """Drop any ``routes_pending`` from state.json."""
    change_dir = _find_change_dir(change, store=store)
    state_file = change_dir / "state.json"

    if not state_file.exists():
        raise OSXError("state_not_found", "state.json does not exist")

    state = _read_state(change_dir)
    had = bool(state.get("routes_pending"))
    state.pop("routes_pending", None)
    state["last_updated"] = get_timestamp()
    _write_state(change_dir, state)

    return {"success": True, "had_routes": had}


def iterations_get(change: str, *, store: str | None = None) -> dict:
    change_dir = _find_change_dir(change, store=store)
    iterations_file = change_dir / "iterations.json"

    if not iterations_file.exists():
        return {"count": 0, "iterations": []}

    iterations = _read_json_array(iterations_file)
    iteration_nums = [i.get("iteration") for i in iterations if "iteration" in i]
    return {"count": len(iterations), "iterations": iteration_nums}


def iterations_append(
    change: str,
    iteration: int | None = None,
    phase: str | None = None,
    summary: str | None = None,
    status: str | None = None,
    notes: str | None = None,
    commit_hash: str | None = None,
    issues: str | None = None,
    artifacts_modified: str | None = None,
    decisions: str | None = None,
    errors: str | None = None,
    extra: str | None = None,
    entry: dict | None = None,
    store: str | None = None,
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


def log_get(change: str, *, store: str | None = None) -> dict:
    change_dir = _find_change_dir(change, store=store)
    log_file = change_dir / "decision-log.json"

    if not log_file.exists():
        return {"count": 0, "entries": []}

    entries = _read_json_array(log_file)
    return {"count": len(entries), "entries": entries}


def log_append(
    change: str,
    phase: str | None = None,
    iteration: int | None = None,
    summary: str | None = None,
    commit_hash: str | None = None,
    next_steps: str | None = None,
    issues: str | None = None,
    artifacts_modified: str | None = None,
    decisions: str | None = None,
    errors: str | None = None,
    extra: str | None = None,
    entry: dict | None = None,
    store: str | None = None,
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


def complete_check(change: str, *, store: str | None = None) -> dict:
    change_dir = _find_change_dir(change, store=store)
    complete_file = change_dir / "complete.json"

    if not complete_file.exists():
        return {"exists": False}

    try:
        json.loads(complete_file.read_text())
        return {"exists": True}
    except json.JSONDecodeError:
        return {"exists": False, "error": "invalid_json"}


def complete_get(change: str, *, store: str | None = None) -> dict:
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
    status: str | None = None,
    blocker_reason: str | None = None,
    *,
    store: str | None = None,
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


def store_doctor(store_id: str | None = None) -> dict:
    """Check health of a single registered store (or all when id is None)."""
    args = ["store", "doctor"]
    if store_id:
        args.append(store_id)
    return {"success": True, "data": _run_openspec_json(args)}


def store_register(path: str, store_id: str | None = None) -> dict:
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


def _load_manifest(project_root: Path) -> dict | None:
    """Load the deployed per-side manifests for the active tool.

    Phase 5 split the on-disk manifests into a per-side layout:
    ``<skills_dir>/manifest.toml`` (orchestrator side) and
    ``<skills_dir>/skills-manifest.toml`` (skills side). The shape is
    identical for every shipped adapter — only ``skills_dir`` changes —
    so the candidate paths are derived from the active adapter rather
    than enumerated per platform. Phase 1D collapsed the
    opencode/claude conditional ladder into a single
    registry-driven resolution.

    Returns ``None`` if no manifest is found or all are unparseable —
    callers should treat missing manifest as "no cross-check available"
    rather than as a hard failure. The defensive ``KeyError`` branch
    below is unreachable in practice (``detect_platform`` always
    returns a registered id) but kept so a future caller passing an
    unknown id fails gracefully.
    """
    try:
        adapter = REGISTRY[detect_platform(project_root)]
    except KeyError:
        return None
    candidates = (
        project_root / adapter.skills_dir / "manifest.toml",
        project_root / adapter.skills_dir / "skills-manifest.toml",
    )
    merged: dict = {"resources": {}}
    seen = False
    for path in candidates:
        if not path.is_file():
            continue
        try:
            data = toml.loads(path.read_text())
        except (OSError, toml.TomlDecodeError):
            continue
        seen = True
        for kind, entries in data.get("resources", {}).items():
            if not isinstance(entries, dict):
                continue
            merged["resources"].setdefault(kind, {}).update(entries)
    return merged if seen else None


def validate_skills(project_root: Path | None = None) -> dict:
    root = project_root if project_root is not None else Path.cwd()
    errors: list[dict] = []
    missing_skills: list[str] = []

    base = skills_dir(root)
    for skill in REQUIRED_SKILLS + REQUIRED_CORE_SKILLS:
        skill_path = base / skill / "SKILL.md"
        if not skill_path.exists():
            errors.append({"check": "skills", "message": f"Missing skill: {skill}"})
            missing_skills.append(skill)

    # M23: cross-check the manifest. Each required skill should be declared
    # in [resources.skills.<name>] in the deployed manifest.toml.
    manifest = _load_manifest(root)
    if manifest is not None:
        declared = manifest.get("resources", {}).get("skills", {})
        for skill in REQUIRED_SKILLS + REQUIRED_CORE_SKILLS:
            if skill not in declared:
                errors.append(
                    {
                        "check": "skills-manifest",
                        "message": f"Skill '{skill}' not declared in manifest",
                    }
                )

    if errors:
        platform = detect_platform(root)
        if missing_skills:
            errors.append(
                {
                    "check": "autonomous-install-hint",
                    "message": _install_hint(platform),
                }
            )
        return {"valid": False, "errors": errors, "missing_skills": missing_skills}
    return {"valid": True}


def _install_hint(platform: str) -> str:
    return f"Re-run: openspec-extended install {platform} --with-autonomous"


def _command_resolved_for_phase(
    root: Path, platform: str, cmd_name: str
) -> Path | None:
    """Return the on-disk path of a slash command, accepting either the
    legacy ``<target>/<commands_dir>/<name>.md`` form or the modern
    ``<target>/skills/<name>/SKILL.md`` form.

    The dual-emit fallthrough is driven by ``adapter.commands_style``:
    ``"namespaced-with-skill-mirror"`` adapters (Claude today) exercise
    both forms — the modern skill file is the back-compat surface that
    mirrors upstream OpenSpec's dual-emit strategy introduced in v1.7.0,
    current as of v1.13.0. Flat adapters (opencode today) only the
    legacy command file.

    The ``osx-`` prefix-strip on the deployed filename is also
    adapter-driven: ``flat`` adapters keep the prefix in the filename,
    namespaced adapters strip it (since the namespacing directory
    ``osx/`` already conveys the prefix in the on-disk path).

    Returns ``None`` if neither form resolves.
    """
    adapter = REGISTRY[platform]
    base = commands_dir(root)
    if adapter.commands_style != "flat" and cmd_name.startswith("osx-"):
        deployed_name = cmd_name.replace("osx-", "", 1)
    else:
        deployed_name = cmd_name

    cmd_path = base / f"{deployed_name}.md"
    if cmd_path.exists():
        return cmd_path

    if adapter.commands_style == "namespaced-with-skill-mirror":
        skill_path = root / adapter.skills_dir / "skills" / cmd_name / "SKILL.md"
        if skill_path.exists():
            return skill_path

    return None


def validate_commands(project_root: Path | None = None) -> dict:
    root = project_root if project_root is not None else Path.cwd()
    errors: list[dict] = []

    platform = detect_platform(root)
    install_hint = _install_hint(platform)
    adapter = REGISTRY[platform]
    missing_phase_commands: list[str] = []
    for phase in PHASES:
        cmd_name = PHASE_COMMANDS.get(phase)
        if not cmd_name:
            continue
        if adapter.commands_style != "flat" and cmd_name.startswith("osx-"):
            deployed_name = cmd_name.replace("osx-", "", 1)
        else:
            deployed_name = cmd_name
        resolved = _command_resolved_for_phase(root, platform, cmd_name)
        if resolved is None:
            missing_phase_commands.append(deployed_name)
            errors.append(
                {
                    "check": "commands",
                    "message": f"Missing command: {deployed_name}",
                }
            )

    # M23: cross-check the manifest. Each phase command should be declared
    # in [resources.commands.<name>] in the deployed manifest.toml, and
    # each PHASE_AGENTS[phase] should exist as an agent file. The
    # agent-file check is driven by ``adapter.has_agents_dir`` —
    # ``opencode`` exposes an on-disk agent dispatch model, ``claude``
    # (and most future adapters) do not: the user brings their own
    # session. Phase 1D collapsed the opencode-only conditional ladder
    # into a registry-driven check.
    manifest = _load_manifest(root)
    if manifest is not None:
        declared_commands = manifest.get("resources", {}).get("commands", {})
        for phase, cmd_name in PHASE_COMMANDS.items():
            if cmd_name and cmd_name not in declared_commands:
                errors.append(
                    {
                        "check": "commands-manifest",
                        "message": f"Command '{cmd_name}' (for {phase}) not declared in manifest",
                    }
                )

        if adapter.has_agents_dir:
            from source.orchestrator.engine import PHASE_AGENTS

            agents_dir = root / adapter.skills_dir / "agents"
            for phase, agent_name in PHASE_AGENTS.items():
                if not agent_name:
                    continue
                if not (agents_dir / f"{agent_name}.md").is_file():
                    errors.append(
                        {
                            "check": "agents",
                            "message": (
                                f"PHASE_AGENTS['{phase}'] = '{agent_name}' "
                                f"but agents/{agent_name}.md not found"
                            ),
                        }
                    )

    if errors:
        if missing_phase_commands:
            errors.append(
                {
                    "check": "autonomous-install-hint",
                    "message": install_hint,
                }
            )
        return {"valid": False, "errors": errors}
    return {"valid": True}


def validate_change_dir(target: str, *, store: str | None = None) -> dict:
    """Validate that ``target`` points at a usable change directory.

    Resolution precedence:

    1. **Core signal** (``isPlanningComplete`` from
       ``openspec status --change <id> --json``) — consulted first when
       available (core v1.8.0+). When the field is ``true``, the change is
       considered planned; we then locally verify ``tasks.md`` exists and is
       non-empty so we don't accept an empty change. When ``false``, every
       artifact whose ``status != "done"`` (from the ``artifacts`` array) is
       reported as a missing planning artifact.
    2. **Local heuristic** — when the core call fails (CLI missing, non-zero
       exit, malformed JSON) or the response lacks ``isPlanningComplete``
       (defensive path for very old cores; the orchestrator's
       ``MIN_OPENSPEC_VERSION`` gate normally rules this out), the original
       local file-existence check runs verbatim.
    3. **CI escape hatch** — ``OPENSPEC_EXTENDED_NO_PLANNING_CORE=1`` skips
       the core call entirely so offline CI without ``openspec`` on ``PATH``
       never spawns the binary.

    Return shape (backward-compatible):

    - ``{"valid": True, "planning_complete": True, "missing_artifacts": []}``
    - ``{"valid": False, "errors": [...], "planning_complete": False | None,
       "missing_artifacts": [str]}``

    Existing ``valid``/``errors`` keys are preserved on every path; the two
    new keys are additive.
    """
    paths = resolve_change_paths(target, store=store)
    change_path = paths["change_root"]

    if not change_path.is_dir():
        return {
            "valid": False,
            "errors": [
                {
                    "check": "change-dir",
                    "message": f"Change directory not found: {change_path}",
                }
            ],
            "planning_complete": None,
            "missing_artifacts": [],
        }

    if os.environ.get("OPENSPEC_EXTENDED_NO_PLANNING_CORE", "").strip() == "1":
        return _validate_change_dir_local(change_path)

    planning = _fetch_planning_status(target, store=store)

    if isinstance(planning, dict) and "isPlanningComplete" in planning:
        return _validate_with_planning_core(change_path, planning)

    print(
        f"Warning: openspec status --change {target} unavailable; "
        f"falling back to local check",
        file=sys.stderr,
    )

    return _validate_change_dir_local(change_path)


def _validate_with_planning_core(change_path: Path, planning: dict) -> dict:
    """Validate a change dir using core's ``isPlanningComplete`` signal."""
    errors: list[dict] = []
    missing: list[str] = []

    if planning.get("isPlanningComplete") is True:
        tasks_path = change_path / "tasks.md"
        if not tasks_path.is_file() or tasks_path.stat().st_size == 0:
            errors.append(
                {
                    "check": "change-dir",
                    "message": "Required file missing: tasks.md",
                }
            )
            missing.append("tasks.md")
        return {
            "valid": not errors,
            "errors": errors,
            "planning_complete": True,
            "missing_artifacts": missing,
        }

    raw_artifacts = planning.get("artifacts")
    if isinstance(raw_artifacts, list):
        for artifact in raw_artifacts:
            if not isinstance(artifact, dict):
                continue
            if artifact.get("status") == "done":
                continue
            artifact_id = artifact.get("id") or "<unknown>"
            missing.append(str(artifact_id))
            errors.append(
                {
                    "check": "change-dir",
                    "message": f"Missing planning artifact: {artifact_id}",
                }
            )

    return {
        "valid": not errors,
        "errors": errors,
        "planning_complete": False,
        "missing_artifacts": missing,
    }


def _validate_change_dir_local(change_path: Path) -> dict:
    """Original file-existence validation, preserved verbatim as the fallback."""
    errors: list[dict] = []
    missing: list[str] = []

    schema_info = resolve_schema(change_dir=change_path)
    schema_name = schema_info["name"]

    required_files = _required_artifact_files(schema_name)
    for file in required_files:
        if not (change_path / file).exists():
            missing.append(file)
            errors.append(
                {"check": "change-dir", "message": f"Required file missing: {file}"}
            )

    if schema_name == "spec-driven":
        specs_dir = change_path / "specs"
        if not specs_dir.is_dir() or not list(specs_dir.rglob("*.md")):
            errors.append(
                {"check": "change-dir", "message": "No spec files found in specs/"}
            )

    return {
        "valid": not errors,
        "errors": errors,
        "planning_complete": None,
        "missing_artifacts": missing,
    }


def validate_archive(target: str, *, store: str | None = None) -> dict:
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

    archive = archives[0]
    errors: list[dict] = []

    if not (archive / "decision-log.json").is_file():
        errors.append(
            {
                "check": "decision-log",
                "message": f"Archive missing decision-log.json: {archive}",
            }
        )

    if not (archive / "iterations.json").is_file():
        errors.append(
            {
                "check": "iterations",
                "message": f"Archive missing iterations.json: {archive}",
            }
        )

    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%H", "--", "."],
            cwd=str(archive),
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        errors.append(
            {
                "check": "commit",
                "message": f"Archive commit check failed: {e}",
            }
        )
    else:
        if result.returncode != 0 or not result.stdout.strip():
            stderr = (result.stderr or "").strip()
            errors.append(
                {
                    "check": "commit",
                    "message": (
                        f"Archive directory has no commit: {archive}"
                        + (f" ({stderr})" if stderr else "")
                    ),
                }
            )

    if errors:
        return {"valid": False, "archive": str(archive), "errors": errors}

    return {"valid": True, "archive": str(archive)}


def validate_iterations(target: str, *, store: str | None = None) -> dict:
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


def validate_completion(target: str, *, store: str | None = None) -> dict:
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
    change_id: str, *, store: str | None = None, strict: bool = False
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
    spec_id: str, *, store: str | None = None, strict: bool = False
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


def _resolve_concurrency(explicit: int | None) -> int:
    """Resolve the --concurrency value with environment-variable fallback.

    Precedence:
      1. Explicit value (CLI flag or programmatic)
      2. ``OPENSPEC_CONCURRENCY`` env var (must parse as int and be > 0)
      3. Default ``6`` (matches upstream ``openspec validate --all`` default)

    Invalid env values (non-int, <=0, empty) fall back to 6 silently.
    """
    if explicit is not None:
        return explicit
    raw = os.environ.get("OPENSPEC_CONCURRENCY")
    if not raw:
        return 6
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return 6
    if value <= 0:
        return 6
    return value


def validate_all(
    *,
    store: str | None = None,
    strict: bool = False,
    concurrency: int | None = None,
) -> dict:
    """Validate all changes AND specs via `openspec validate --all --json`.

    Args:
      store: Optional OpenSpec store id
      strict: If True, warnings are treated as failures
      concurrency: Max parallel validations. Resolution precedence:
        1. Explicit value (this argument)
        2. ``OPENSPEC_CONCURRENCY`` env var (must parse as int and be > 0)
        3. Default ``6`` (matches upstream ``openspec validate --all`` default).
        Invalid env values (non-int, <=0, empty) fall back to 6 silently.

    Returns: see _translate_validate_payload.
    Raises: OSXError on subprocess failures.
    """
    resolved = _resolve_concurrency(concurrency)
    args = [
        "validate",
        "--all",
        "--no-interactive",
        "--concurrency",
        str(resolved),
    ]
    if strict:
        args.append("--strict")
    if store:
        args.extend(["--store", store])
    return _translate_validate_payload(_run_openspec_json(args, timeout=60))


def validate_changes_only(*, store: str | None = None, strict: bool = False) -> dict:
    """Validate all active changes only via `openspec validate --changes --json`."""
    args = ["validate", "--changes", "--no-interactive"]
    if strict:
        args.append("--strict")
    if store:
        args.extend(["--store", store])
    return _translate_validate_payload(_run_openspec_json(args))


def validate_archived(
    change_id: str | None = None,
    *,
    store: str | None = None,
    strict: bool = False,
) -> dict:
    """Validate archived changes via `openspec validate --archived --json` (v1.9.0+).

    Brings the ``--archived`` scope to parity with the other ``osx validate``
    actions (``change``, ``spec``, ``all``, ``changes``, ``specs``): same
    normalized envelope (via ``_translate_validate_payload``), same
    structured error handling, same exit semantics.

    Args:
      change_id: optional — scope to a single archived change. When given,
        the change id is passed as a positional alongside ``--archived``,
        matching the existing top-level ``openspec-extended validate
        <id> --archived`` passthrough (``source/cli.py:1570``).
      store: optional store id.
      strict: treat warnings as failures.

    Returns: see ``_translate_validate_payload``.

    Raises: OSXError on subprocess failures (delegated to
      ``_run_openspec_json``).
    """
    if change_id:
        args = ["validate", change_id, "--archived", "--no-interactive"]
    else:
        args = ["validate", "--archived", "--no-interactive"]
    if strict:
        args.append("--strict")
    if store:
        args.extend(["--store", store])
    return _translate_validate_payload(_run_openspec_json(args, timeout=60))


def validate_specs_only(*, store: str | None = None, strict: bool = False) -> dict:
    """Validate all main specs only via `openspec validate --specs --json`."""
    args = ["validate", "--specs", "--no-interactive"]
    if strict:
        args.append("--strict")
    if store:
        args.extend(["--store", store])
    return _translate_validate_payload(_run_openspec_json(args))


def read_change_metadata(change_dir: Path | None) -> dict:
    """Read ``.openspec.yaml`` from ``change_dir`` and return its metadata.

    Returns a dict with optional keys:
      - schema: str                # workflow schema name (same key resolve_schema reads)
      - skip_specs: bool           # zero-delta change marker
      - retire_capabilities: bool  # allow archive to delete the spec when
                                   # REMOVED entries empty it (v1.8.0+)

    Returns ``{}`` if the file is missing or malformed. Never raises — same
    tolerance as ``resolve_schema``.

    Booleans are accepted both as native YAML booleans (``true``/``false``,
    which ``yaml.safe_load`` parses to ``True``/``False``) and as quoted
    strings (``"true"``/``"false"``) for human-authored files. Non-bool values
    for boolean fields fall back to ``False``.
    """
    if change_dir is None:
        return {}
    change_meta = change_dir / ".openspec.yaml"
    if not change_meta.exists():
        return {}

    try:
        data = yaml.safe_load(change_meta.read_text())
    except (yaml.YAMLError, OSError) as error:
        print(
            f"Warning: Could not load change metadata {change_meta}: {error}",
            file=sys.stderr,
        )
        return {}

    if not isinstance(data, dict):
        return {}

    result: dict = {}

    schema = data.get("schema")
    if isinstance(schema, str) and schema:
        result["schema"] = schema

    for key in ("skip_specs", "retire_capabilities"):
        value = data.get(key)
        if isinstance(value, bool):
            result[key] = value
        elif isinstance(value, str) and value.lower() in ("true", "false"):
            result[key] = value.lower() == "true"
        # Non-bool values are silently ignored — the marker is opt-in.

    return result


def resolve_schema(
    *,
    project_root: Path | None = None,
    explicit: str | None = None,
    change_dir: Path | None = None,
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


def fetch_instructions(
    operation: str,
    change_id: str,
    *,
    store: str | None = None,
) -> dict:
    """Run `openspec instructions <operation> --change <id> --json` and return the envelope.

    The read-only mirror surface introduced in OpenSpec v1.7.0. Works for
    any of the supported operations (`proposal`, `apply`, `archive` and any
    future additions). Used by ``osx instructions`` to provide structured
    error handling and JSON output consistent with the rest of the osx
    library — in-process callers (orchestrator, tests) should prefer
    ``fetch_operation_guidance`` when they only need the operationGuidance
    string list, since that helper reads the config file directly.

    Args:
      operation: OpenSpec instructions operation (e.g. ``"proposal"``,
        ``"apply"``, ``"archive"``).
      change_id: OpenSpec change id.
      store: optional store id.

    Returns: parsed JSON dict.

    Raises: OSXError on subprocess failures (delegated to
      ``_run_openspec_json``).
    """
    effective_store = store if store is not None else current_store.get()
    args = ["instructions", operation, "--change", change_id]
    if effective_store:
        args.extend(["--store", effective_store])
    return _run_openspec_json(args, timeout=30)


def fetch_apply_prerequisites(
    change_id: str,
    *,
    store: str | None = None,
) -> list[str] | None:
    """Read ``missingPrerequisites`` from ``openspec instructions apply --json``.

    OpenSpec v1.13.0 added the ``missingPrerequisites`` array to the
    ``openspec instructions apply --change <id> --json`` envelope. The
    array names the **full build-order chain** for an apply whose
    ``applyRequires`` set is not yet satisfied — not just the first hop.
    A change with no delta specs at all (and no ``skip_specs: true``)
    is also reported here as a warning, naming both remedies ("write the
    specs" or "declare ``skip_specs: true``").

    PHASE1 consumers should prefer this field over regex-parsing the text
    response remedies (which reference ``openspec instructions <artifact>
    --change <name>`` rather than the ``openspec-continue-change`` skill
    that the ``core`` profile never installs). The orchestrator's PHASE1
    logs the chain in the decision log via ``osx log append --extra
    '{"missing_prerequisites": [...]}'``; logging is informational,
    not blocking.

    Args:
      change_id: OpenSpec change id.
      store: optional store id.

    Returns:
      - ``[]`` when the field is present and empty (apply is ready).
      - ``list[str]`` of artifact ids when the field is present and
        non-empty (apply is blocked; the list is the full chain).
      - ``None`` when the CLI call fails, the response is non-JSON, the
        response is not a dict, or the field is absent (older cores
        pre-v1.13.0). Callers that need to distinguish "older core"
        from "apply-ready on a newer core" should check the field
        explicitly via ``fetch_instructions``.
    """
    try:
        payload = fetch_instructions("apply", change_id, store=store)
    except OSXError:
        return None
    if not isinstance(payload, dict):
        return None
    value = payload.get("missingPrerequisites")
    if value is None:
        return None
    if not isinstance(value, list):
        return None
    return [item for item in value if isinstance(item, str)]


def list_specs(*, store: str | None = None) -> list[dict] | None:
    """Run ``openspec list --specs [--store <id>] --json`` and return the array.

    OpenSpec v1.13.0 introduced the ``--specs`` flag on ``openspec list``
    as a first-class spec-inventory command (parallel to ``openspec list``
    for changes). The payload is ``{"specs": [...], "root": {...}}``
    (mirroring the v1.11.0 ``status --all`` shape). Generated guidance
    reads the inventory then drills into each spec with
    ``openspec show <id> --type spec --json --no-scenarios`` so the read
    stays small enough to enumerate on every capability.

    PHASE0 spec-aware review (``osx-review-artifacts`` Step 2) uses this
    helper to build a ``{spec_id -> {path, purpose}}`` map; Step 4's
    "Capability-already-exists" check consumes the map to flag drift
    before approving an ``ADDED Requirements`` block.

    Args:
      store: optional store id.

    Returns:
      - ``list[dict]`` of spec entries (may be empty).
      - ``None`` when the CLI call fails, the response is non-JSON, the
        response is not a dict, or the command is not recognized (cores
        pre-v1.13.0). Callers should treat ``None`` as "feature
        unavailable" and degrade gracefully.
    """
    effective_store = store if store is not None else current_store.get()
    args = ["list", "--specs"]
    if effective_store:
        args.extend(["--store", effective_store])
    try:
        payload = _run_openspec_json(args, timeout=30)
    except OSXError:
        return None
    if not isinstance(payload, dict):
        return None
    specs = payload.get("specs")
    if specs is None:
        # Some shells may emit a bare list; tolerate both shapes.
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        return None
    if not isinstance(specs, list):
        return None
    return [item for item in specs if isinstance(item, dict)]


def show_spec(
    spec_id: str,
    *,
    store: str | None = None,
) -> dict | None:
    """Run ``openspec show <id> --type spec --json --no-scenarios`` and return the envelope.

    The filtered read used by generated guidance in v1.13.0+. The
    ``--no-scenarios`` flag keeps the bulk read small enough to
    enumerate on every capability; agents still read relevant specs in
    full (with scenarios) before deciding what is already covered or
    what should change. See ``orchestrator/core/source/CHANGELOG.md``
    PR #1700.

    Args:
      spec_id: OpenSpec capability path (e.g. ``"auth/oauth-flow"``).
      store: optional store id.

    Returns:
      Parsed JSON dict, or ``None`` on CLI failure / non-JSON output /
      unrecognized command (cores pre-v1.13.0). Callers should treat
      ``None`` as "feature unavailable" and degrade gracefully.
    """
    effective_store = store if store is not None else current_store.get()
    args = ["show", spec_id, "--type", "spec", "--json", "--no-scenarios"]
    if effective_store:
        args.extend(["--store", effective_store])
    try:
        payload = _run_openspec_json(args, timeout=30)
    except OSXError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


# Operations whose advisory guidance the orchestrator injects into the AI
# prompt. Core (OpenSpec v1.7.0+) surfaces these via ``openspec instructions
# apply|archive --json`` (``operationGuidance`` field); the orchestrator reads
# the same file directly so it can prepend the strings to the spawn prompt
# without a subprocess round-trip. See A.4 in the implementation plan.
_GUIDANCE_OPERATIONS = frozenset({"apply", "archive"})


def fetch_operation_guidance(
    operation: str,
    project_root: Path | None = None,
    store: str | None = None,
) -> list[str]:
    """Read ``operations.{operation}.guidance`` from ``openspec/config.yaml``.

    The orchestrator (PHASE1/PHASE6) calls this to source project-level
    advisory guidance for the matching AI spawn. Core's JSON envelope
    exposes the same data via ``openspec instructions apply|archive
    --json`` (the ``operationGuidance`` field, since v1.7.0); reading the
    file directly avoids the subprocess round-trip and the store-aware
    resolution the CLI does internally.

    Args:
      operation: ``"apply"`` or ``"archive"`` — the only operations core
        supports guidance for. Any other value returns ``[]``.
      project_root: project root containing the ``openspec/`` directory.
        Falls back to ``Path.cwd()`` when ``None`` (mirrors
        ``resolve_schema``).
      store: unused for direct-file reads; kept for signature symmetry
        with ``resolve_schema`` so a future store-aware variant can
        extend without breaking callers.

    Returns:
      A list of advisory guidance strings. Empty when the file is
      missing or malformed, when the operation has no guidance entry,
      or when the operation is outside ``{apply, archive}``. Never raises.
    """
    if operation not in _GUIDANCE_OPERATIONS:
        return []

    if project_root is None:
        project_root = Path.cwd()

    data: dict | None = None
    for config_name in ("config.yaml", "config.yml"):
        config_path = project_root / "openspec" / config_name
        if not config_path.exists():
            continue
        try:
            loaded = yaml.safe_load(config_path.read_text())
        except (yaml.YAMLError, OSError) as error:
            print(
                f"Warning: Could not load operations guidance from {config_path}: {error}",
                file=sys.stderr,
            )
            return []
        if isinstance(loaded, dict):
            data = loaded
            break

    if not isinstance(data, dict):
        return []

    operations = data.get("operations")
    if not isinstance(operations, dict):
        return []

    op_entry = operations.get(operation)
    if not isinstance(op_entry, dict):
        return []

    guidance = op_entry.get("guidance")
    if not isinstance(guidance, list):
        return []

    return [item for item in guidance if isinstance(item, str)]


def list_artifacts_for_schema(
    schema_name: str, *, store: str | None = None
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
    name: str | None = None,
    *,
    all_schemas: bool = False,
    store: str | None = None,
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
    name: str | None = None,
    *,
    store: str | None = None,
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
    name: str | None = None,
    *,
    force: bool = False,
    store: str | None = None,
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


def schema_fork_diff(
    source: str,
    target: str,
    *,
    force: bool = False,
    project_root: Path | None = None,
) -> dict:
    """Fork a schema and assert YAML fidelity against the source.

    Performs ``openspec schema fork <source> <target> [--force]`` and then
    parses both the source and target ``schema.yaml`` to confirm semantic
    equivalence after the fork. The v1.9.0+ core guarantees YAML fidelity
    (comments, key order, scalar style preserved via the YAML Document API);
    this helper makes the guarantee programmatically verifiable — useful as
    a CI gate before customizing a forked schema.

    Args:
      source: source schema name (e.g. ``"spec-driven"``).
      target: target schema name (the fork).
      force: pass ``--force`` to upstream fork.
      project_root: project root used to locate schema files. Defaults to
        ``Path.cwd()``.

    Returns:
      {
        "valid": bool,                 # fork succeeded AND fidelity is perfect
        "schema_path": str,            # absolute path to the forked schema.yaml
        "fidelity": "perfect"|"drifted"|"unverified",
        "differences": [str],          # human-readable drift lines (empty when perfect)
        "fidelity_warning": str | None # present when fidelity is "drifted" or "unverified"
      }

    Raises:
      OSXError on subprocess failures or when either schema file is
      missing or unparseable after the fork.
    """
    if project_root is None:
        project_root = Path.cwd()

    schema_fork(source, target, force=force)

    source_path = project_root / "openspec" / "schemas" / source / "schema.yaml"
    target_path = project_root / "openspec" / "schemas" / target / "schema.yaml"

    if not source_path.is_file():
        raise OSXError(
            "schema_not_found",
            f"Source schema.yaml not found: {source_path}",
            path=str(source_path),
        )
    if not target_path.is_file():
        raise OSXError(
            "schema_not_found",
            f"Target schema.yaml not found: {target_path}",
            path=str(target_path),
        )

    try:
        source_data = yaml.safe_load(source_path.read_text())
        target_data = yaml.safe_load(target_path.read_text())
    except yaml.YAMLError as e:
        raise OSXError(
            "invalid_yaml",
            f"Failed to parse schema YAML: {e}",
            path=str(target_path),
        ) from e

    differences = _yaml_diff(source_data, target_data)
    perfect = not differences
    fidelity = "perfect" if perfect else "drifted"
    fidelity_warning = (
        "Schema drifted from source after fork — YAML Document API fidelity "
        "guarantee may have regressed. Review differences before customizing."
        if not perfect
        else None
    )

    return {
        "valid": perfect,
        "schema_path": str(target_path),
        "fidelity": fidelity,
        "differences": differences,
        "fidelity_warning": fidelity_warning,
    }


def _yaml_diff(source: Any, target: Any, path: str = "") -> list[str]:
    """Return human-readable drift lines between two parsed YAML trees.

    Compares keys, scalar values, and list lengths recursively. The
    MVP check uses ``yaml.safe_load`` (semantic equality, not byte
    fidelity); the v1.9.0+ Document API guarantee is stronger than this
    comparison, so any non-empty result here is a real signal of drift.
    """
    diffs: list[str] = []

    if isinstance(source, dict) and isinstance(target, dict):
        source_keys = cast(set[str], set(source.keys()))
        target_keys = cast(set[str], set(target.keys()))
        for missing in sorted(source_keys - target_keys):
            diffs.append(f"{path or '.'}: missing key {missing!r}")
        for extra in sorted(target_keys - source_keys):
            diffs.append(f"{path or '.'}: extra key {extra!r}")
        for key in sorted(source_keys & target_keys):
            diffs.extend(
                _yaml_diff(
                    source[key], target[key], f"{path}.{key}" if path else str(key)
                )
            )
    elif isinstance(source, list) and isinstance(target, list):
        if len(source) != len(target):
            diffs.append(
                f"{path or '.'}: list length differs (source={len(source)}, target={len(target)})"
            )
        for i, (s_item, t_item) in enumerate(zip(source, target)):
            diffs.extend(_yaml_diff(s_item, t_item, f"{path}[{i}]"))
    else:
        if source != target:
            diffs.append(
                f"{path or '.'}: value differs (source={source!r}, target={target!r})"
            )
    return diffs


def schema_init(
    name: str,
    *,
    description: str | None = None,
    artifacts: list[str] | None = None,
    set_default: bool = False,
    force: bool = False,
    store: str | None = None,
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


def schema_list(*, store: str | None = None) -> list[dict]:
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
