#!/usr/bin/env python3
"""
OpenSpec Extended Autonomous Workflow Orchestrator - Core Engine

This module contains the orchestrator logic, migrated from osx-orchestrate.
It can be called directly via run_orchestrator() function.
"""

import json
import os
import re
import shutil
import signal
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from rich import print as rich_print

import toml

from source.lib import osx as osx_lib
from source.lib.osx import OSXError
from source.orchestrator.runner import detect_runner

PHASES = ["PHASE0", "PHASE1", "PHASE2", "PHASE3", "PHASE4", "PHASE5", "PHASE6"]

PHASE_NAMES = {
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

PHASE_AGENTS = {
    "PHASE0": "osx-analyzer",
    "PHASE1": "osx-builder",
    "PHASE2": "osx-analyzer",
    "PHASE3": "osx-maintainer",
    "PHASE4": "osx-maintainer",
    "PHASE5": "osx-analyzer",
    "PHASE6": "osx-maintainer",
}

DEFAULT_TIMEOUT = 1800
DEFAULT_MAX_PHASE_ITERATIONS = 10


def get_resources_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", "")) / "resources"
    return Path(__file__).parent.parent / "resources"


def get_version() -> str:
    manifest_path = get_resources_dir() / "opencode" / "manifest.toml"
    if manifest_path.exists():
        try:
            manifest = toml.loads(manifest_path.read_text())
            return (
                manifest.get("resources", {})
                .get("scripts", {})
                .get("osx-orchestrate", {})
                .get("version", "unknown")
            )
        except (toml.TomlDecodeError, KeyError, AttributeError):
            pass
    return "unknown"


@dataclass
class OrchestratorState:
    change_id: str = ""
    change_dir: Optional[Path] = None
    max_phase_iterations: int = DEFAULT_MAX_PHASE_ITERATIONS
    timeout: int = DEFAULT_TIMEOUT
    verbose: bool = False
    dry_run: bool = False
    force: bool = False
    clean: bool = False
    from_phase: str = ""
    no_color: bool = False
    log_file: Optional[Path] = None
    log_user_specified: bool = False
    total_invocations: int = 0
    start_time: int = 0
    interrupted: bool = False
    child_pid: Optional[int] = None
    model: str = ""
    list_changes: bool = False
    store: Optional[str] = None
    schema_override: Optional[str] = None
    schema_name: Optional[str] = None
    schema_source: Optional[str] = None


def get_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def find_change_dir(change: str, *, store: Optional[str] = None) -> Optional[Path]:
    try:
        return osx_lib._find_change_dir(
            change, store=store or osx_lib.current_store.get()
        )
    except osx_lib.OSXError:
        return None


def parse_change_spec(spec: str) -> tuple:
    """Parse '<store>:<change>' or '<change>' form. Returns (store_or_None, change).

    The first ':' is the separator. The change name itself may contain
    colons (rare but allowed); everything before the first colon is the
    store id (or None if no colon).
    """
    if not spec:
        return None, spec
    if ":" in spec:
        store, _, change = spec.partition(":")
        return store, change
    return None, spec


def log(state: OrchestratorState, msg: str) -> None:
    timestamp = get_timestamp()
    output = f"{timestamp} [INFO] {msg}"
    if state.no_color:
        print(output)
    else:
        rich_print(f"[blue]{output}[/blue]")


def log_success(state: OrchestratorState, msg: str) -> None:
    timestamp = get_timestamp()
    output = f"{timestamp} [OK] {msg}"
    if state.no_color:
        print(output)
    else:
        rich_print(f"[green]{output}[/green]")


def log_warning(state: OrchestratorState, msg: str) -> None:
    timestamp = get_timestamp()
    output = f"{timestamp} [WARN] {msg}"
    if state.no_color:
        print(output, file=sys.stderr)
    else:
        rich_print(f"[yellow]{output}[/yellow]", file=sys.stderr)


def log_error(state: OrchestratorState, msg: str) -> None:
    timestamp = get_timestamp()
    output = f"{timestamp} [ERROR] {msg}"
    if state.no_color:
        print(output, file=sys.stderr)
    else:
        rich_print(f"[red]{output}[/red]", file=sys.stderr)


def log_verbose(state: OrchestratorState, msg: str) -> None:
    timestamp = get_timestamp()
    output = f"{timestamp} [VERBOSE] {msg}"
    if state.verbose:
        if state.no_color:
            print(output)
        else:
            rich_print(f"[blue]{output}[/blue]")
    elif state.log_file and state.log_file.exists():
        with open(state.log_file, "a") as log_f:
            log_f.write(re.sub(r"\x1b\[[0-9;]*m", "", output) + "\n")


def print_validation_errors(state: OrchestratorState, data: dict) -> None:
    errors = data.get("errors", [])
    for err in errors:
        msg = err.get("message", "")
        if msg:
            log_error(state, msg)


def _project_root(state: OrchestratorState) -> Optional[Path]:
    """Project root derived from the active change directory.

    Mirrors the derivation used by ``validate_schema`` (``engine.py:284``).
    Returns ``None`` when no change directory is set, in which case the
    library functions fall back to ``Path.cwd()``.
    """
    return state.change_dir.parent.parent.parent if state.change_dir else None


def validate_skills(state: OrchestratorState) -> None:
    log(state, "Validating required skills...")

    data = osx_lib.validate_skills(project_root=_project_root(state))
    if not data.get("valid", False):
        log_error(state, "Required skills validation failed")
        print_validation_errors(state, data)
        log_error(state, "Run: openspec-extended install opencode")
        raise SystemExit(1)

    log_verbose(state, "All required skills found")


def validate_commands(state: OrchestratorState) -> None:
    log(state, "Validating required commands...")

    data = osx_lib.validate_commands(project_root=_project_root(state))
    if not data.get("valid", False):
        log_error(state, "Required commands validation failed")
        print_validation_errors(state, data)
        log_error(state, "Run: openspec-extended install opencode")
        raise SystemExit(1)

    log_verbose(state, "All required commands found")


def validate_git(state: OrchestratorState) -> None:
    log(state, "Validating git repository...")

    try:
        subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        log_error(state, "Not in a git repository")
        raise SystemExit(1)

    result = subprocess.run(["git", "diff", "--quiet"], capture_output=True)
    result_cached = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], capture_output=True
    )

    if result.returncode != 0 or result_cached.returncode != 0:
        log_warning(state, "Git working directory is dirty")
        log_warning(state, "Uncommitted changes detected")

        if not state.force and os.isatty(0):
            print("")
            print("Options:")
            print("  1. Commit or stash changes before proceeding")
            print("  2. Abort and clean up first")
            print("  3. Continue anyway (use --force to skip this prompt)")
            reply = input("Continue? [y/N] ")
            print("")
            if not reply.lower().startswith("y"):
                log_error(state, "Aborted due to dirty git state")
                raise SystemExit(1)
        else:
            log_warning(
                state, "Continuing with dirty git state (non-interactive or --force)"
            )

    log_verbose(state, "Git repository is ready")


def validate_change_dir(state: OrchestratorState) -> None:
    log(state, "Validating change directory...")

    data = osx_lib.validate_change_dir(state.change_id)
    if not data.get("valid", False):
        log_error(state, "Change directory validation failed")
        print_validation_errors(state, data)
        log_error(state, f"Change directory: {state.change_dir}")
        raise SystemExit(1)

    log_verbose(state, "Change directory validated")


def validate_schema(state: OrchestratorState) -> bool:
    """Resolve the schema at startup, log it, cache it in state.schema_name.

    Returns True if validation passes (always passes — we just log).
    If state.schema_override is set and conflicts with .openspec.yaml or
    openspec/config.yaml, log a warning but proceed.
    """
    log(state, "Resolving workflow schema...")

    change_dir = state.change_dir
    project_root = change_dir.parent.parent.parent if change_dir else Path.cwd()

    schema_info = osx_lib.resolve_schema(
        project_root=project_root,
        explicit=state.schema_override,
        change_dir=change_dir,
    )

    state.schema_name = schema_info["name"]
    state.schema_source = schema_info["source"]

    log(state, f"Schema: {schema_info['name']} (source: {schema_info['source']})")

    if state.schema_override and schema_info["source"] != "explicit":
        log_warning(
            state,
            f"--schema={state.schema_override} applied as override "
            f"(project declares: {schema_info['name']})",
        )

    log_verbose(state, "Schema resolution complete")
    return True


def validate_archive(state: OrchestratorState) -> tuple[bool, str]:
    data = osx_lib.validate_archive(state.change_id)
    if not data.get("valid", False):
        return False, ""
    return True, data.get("archive", "")


def record_baseline(state: OrchestratorState) -> None:
    log(state, "Recording baseline...")

    try:
        data = osx_lib.baseline_record()
    except osx_lib.OSXError as e:
        log_error(state, f"Failed to record baseline: {e.message}")
        raise SystemExit(1) from e

    commit = data.get("commit", "")
    if not commit:
        log_error(state, "Failed to record baseline")
        raise SystemExit(1)
    log_verbose(state, f"Baseline recorded: {commit}")


def read_state(state: OrchestratorState) -> Optional[dict]:
    if state.change_dir is None:
        return None

    state_file = state.change_dir / "state.json"
    if not state_file.exists():
        return None

    try:
        data = json.loads(state_file.read_text())
        phase = data.get("phase", "")
        iteration = data.get("iteration", None)

        if not phase or iteration is None:
            log_error(state, "State file missing required fields")
            return None

        if phase not in PHASES and phase != "COMPLETE":
            log_error(state, f"State file has invalid phase value: {phase}")
            return None

        return data
    except json.JSONDecodeError:
        log_error(state, "State file is corrupted, cannot resume")
        return None


def write_state(
    state: OrchestratorState,
    phase: str,
    iteration: int = 1,
    phase_complete: bool = False,
) -> None:
    if state.change_dir is None:
        return

    state_file = state.change_dir / "state.json"
    phase_iterations = {}

    if state_file.exists():
        try:
            existing = json.loads(state_file.read_text())
            phase_iterations = existing.get("phase_iterations", {})
        except json.JSONDecodeError:
            pass

    current_count = phase_iterations.get(phase, 0)
    new_count = current_count + 1
    phase_iterations[phase] = new_count

    timestamp = get_timestamp()
    state_data = {
        "phase": phase,
        "phase_name": PHASE_NAMES.get(phase, "UNKNOWN"),
        "iteration": iteration,
        "phase_complete": phase_complete,
        "total_invocations": state.total_invocations,
        "phase_iterations": phase_iterations,
        "started_at": timestamp,
        "last_updated": timestamp,
    }

    state_file.write_text(json.dumps(state_data, indent=2))
    log_verbose(
        state,
        f"State updated: {phase} (iteration {iteration}, complete: {phase_complete})",
    )


def get_current_phase(state: OrchestratorState) -> Optional[str]:
    data = read_state(state)
    if data:
        return data.get("phase")
    return None


def get_phase_iteration(state: OrchestratorState) -> int:
    data = read_state(state)
    if data:
        return data.get("iteration", 0)
    return 0


def check_phase_complete(state: OrchestratorState) -> bool:
    data = read_state(state)
    if data:
        return data.get("phase_complete", False) is True
    return False


def clear_phase_complete(state: OrchestratorState) -> None:
    if state.change_dir is None:
        return

    state_file = state.change_dir / "state.json"
    if not state_file.exists():
        return

    try:
        data = json.loads(state_file.read_text())
        data["phase_complete"] = False
        state_file.write_text(json.dumps(data, indent=2))
    except json.JSONDecodeError:
        pass


def check_transition(state: OrchestratorState) -> tuple[bool, str]:
    data = read_state(state)
    if data and "transition" in data:
        target = data["transition"].get("target", "")
        if target:
            return True, target
    return False, ""


def get_transition_reason(state: OrchestratorState) -> str:
    data = read_state(state)
    if data and "transition" in data:
        return data["transition"].get("reason", "unknown")
    return "unknown"


def get_transition_details(state: OrchestratorState) -> str:
    data = read_state(state)
    if data and "transition" in data:
        return data["transition"].get("details", "")
    return ""


def clear_transition(state: OrchestratorState) -> None:
    try:
        osx_lib.state_clear_transition(state.change_id)
    except osx_lib.OSXError as e:
        log_warning(state, f"Failed to clear transition: {e.message}")


def check_complete(state: OrchestratorState) -> bool:
    try:
        data = osx_lib.complete_check(state.change_id)
    except osx_lib.OSXError as e:
        log_warning(state, f"complete check failed: {e.message}")
        return False
    return data.get("exists", False) is True


def read_completion(state: OrchestratorState) -> Optional[str]:
    try:
        data = osx_lib.complete_get(state.change_id)
    except osx_lib.OSXError as e:
        log_warning(state, f"complete get failed: {e.message}")
        return None
    return data.get("status")


def advance_phase(current: str) -> str:
    order = {
        "PHASE0": "PHASE1",
        "PHASE1": "PHASE2",
        "PHASE2": "PHASE3",
        "PHASE3": "PHASE4",
        "PHASE4": "PHASE5",
        "PHASE5": "PHASE6",
        "PHASE6": "COMPLETE",
        "COMPLETE": "COMPLETE",
    }
    return order.get(current, "COMPLETE")


def run_agent(state: OrchestratorState, phase: str) -> bool:
    if state.dry_run:
        log(state, "[DRY RUN] Would run command for " + phase)
        return True

    log(state, f"Agent invocation #{state.total_invocations} for {phase}")

    cmd_name = PHASE_COMMANDS.get(phase, "")
    agent_name = PHASE_AGENTS.get(phase, "")
    title = f"OpenSpec: {state.change_id} - {PHASE_NAMES.get(phase, '')}"

    log_verbose(state, f"Using command: /{cmd_name}")
    log_verbose(state, f"Using agent: {agent_name}")
    log_verbose(state, f"Session title: {title}")

    try:
        project_root = (
            state.change_dir.parent.parent.parent if state.change_dir else Path.cwd()
        )
        runner = detect_runner(project_root)
    except OSXError as e:
        log_error(state, e.message)
        return False

    log_verbose(state, f"Using runner: {runner.name}")

    from source.orchestrator.runner import RunRequest

    request = RunRequest(
        command=cmd_name,
        agent=agent_name,
        change_id=state.change_id,
        title=title,
        model=state.model,
        cwd=Path.cwd(),
        timeout=state.timeout,
    )

    try:
        result = runner.run(request, verbose=state.verbose)
    except OSXError as e:
        log_error(state, e.message)
        return False

    state.child_pid = result.pid

    if state.log_file and result.log_path and result.log_path.exists():
        with open(state.log_file, "a") as log_f:
            log_f.write(f"> {agent_name}\n")
            with open(result.log_path) as agent_f:
                log_f.write(agent_f.read())
        result.log_path.unlink(missing_ok=True)

    if state.interrupted:
        log_warning(state, "Execution interrupted by user")
        raise SystemExit(130)

    if result.timed_out:
        log_error(
            state, f"Agent iteration timed out after {state.timeout // 60} minutes"
        )
        return False
    elif result.exit_code != 0:
        log_error(state, f"Agent execution failed with exit code {result.exit_code}")
        return False

    return True


def run_phase(state: OrchestratorState, phase: str) -> bool:
    log(state, PHASE_NAMES.get(phase, phase))
    iteration = 1

    while iteration <= state.max_phase_iterations or state.max_phase_iterations == -1:
        state.total_invocations += 1
        write_state(state, phase, iteration)

        if not run_agent(state, phase):
            return False

        if state.dry_run:
            return True

        if phase == "PHASE6":
            success, _ = validate_archive(state)
            if success:
                log_success(state, f"{phase} completed in {iteration} iteration(s)")
                return True
        elif check_phase_complete(state):
            log_success(state, f"{phase} completed in {iteration} iteration(s)")
            clear_phase_complete(state)
            return True

        iteration += 1

    log_warning(
        state, f"{phase} reached max phase iterations ({state.max_phase_iterations})"
    )
    return False


def show_progress(state: OrchestratorState) -> None:
    print("================================")
    print("Progress Summary")
    print("================================")
    print(f"Change ID: {state.change_id}")

    if state.change_dir:
        print(f"Change directory: {state.change_dir}")

    current_phase = get_current_phase(state)
    if current_phase:
        print(
            f"Current phase: {current_phase} - {PHASE_NAMES.get(current_phase, 'UNKNOWN')}"
        )
        iteration = get_phase_iteration(state)
        print(f"Phase iteration: {iteration}")
    else:
        print("Current phase: Not started")

    print("")
    print(f"Total invocations: {state.total_invocations}")

    elapsed = 0
    if state.start_time > 0:
        elapsed = int(datetime.now(timezone.utc).timestamp()) - state.start_time
    minutes = elapsed // 60
    seconds = elapsed % 60
    print(f"Elapsed time: {minutes}m {seconds}s")

    if state.log_file:
        print(f"Log file: {state.log_file}")

    if state.change_dir:
        state_file = state.change_dir / "state.json"
        if state_file.exists():
            print("")
            print("Iterations by phase:")
            try:
                data = json.loads(state_file.read_text())
                phase_iterations = data.get("phase_iterations", {})
                for p in PHASES:
                    count = phase_iterations.get(p, 0)
                    print(f"  {p} ({PHASE_NAMES[p]}): {count}")
            except json.JSONDecodeError:
                pass

    print("================================")


def archive_log_file(state: OrchestratorState) -> bool:
    if not state.log_file or not state.log_file.exists():
        log_verbose(state, "No log file to archive")
        return True

    if state.log_user_specified:
        log_verbose(state, "User-specified log path, not moving to archive")
        return True

    try:
        os.sync()
    except (AttributeError, OSError):
        pass

    success, archive_dir = validate_archive(state)
    if not success or not archive_dir:
        log_error(state, "Failed to get archive path")
        if state.log_file:
            log_error(state, f"Log file not archived: {state.log_file}")
        return False

    archive_path = Path(archive_dir)
    if not archive_path.is_dir():
        log_error(state, f"Archive directory does not exist: {archive_path}")
        if state.log_file:
            log_error(state, f"Log file not archived: {state.log_file}")
        return False

    archive_log = archive_path / "osx-orchestrate.log"

    try:
        shutil.move(str(state.log_file), str(archive_log))
    except Exception as e:
        log_error(state, f"Failed to move log file to archive: {e}")
        return False

    log_verbose(state, f"Log moved to archive: {archive_log}")

    try:
        subprocess.run(
            ["git", "add", str(archive_log)], capture_output=True, check=True
        )
    except subprocess.CalledProcessError:
        log_warning(state, "Failed to add log file to git")
        return True

    try:
        subprocess.run(
            ["git", "commit", "--amend", "--no-edit"], capture_output=True, check=True
        )
    except subprocess.CalledProcessError:
        log_error(state, "Failed to amend archive commit with log file")
        return False

    log_verbose(state, "Archive commit amended with log file")
    return True


def handle_interrupt(signum, frame, state: OrchestratorState) -> None:
    state.interrupted = True
    if state.child_pid:
        try:
            os.kill(state.child_pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass


def cleanup(state: OrchestratorState, exit_code: int) -> None:
    if state.child_pid:
        try:
            os.kill(state.child_pid, signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass

    if state.interrupted:
        log(state, "")
        log_warning(state, "Execution interrupted by user")
        log(state, "State files preserved for resumption:")
        if state.change_dir:
            for fname in [
                "state.json",
                "complete.json",
                "iterations.json",
                "decision-log.json",
            ]:
                fp = state.change_dir / fname
                if fp.exists():
                    log(state, f"  {fp}")
        log(state, "")
        log(state, "To resume: Run script again with same change-id")
        raise SystemExit(130)

    if exit_code != 0:
        log(state, "")
        log_error(state, f"Script exited with error (code {exit_code})")
        log(state, "State files preserved for investigation:")
        if state.change_dir:
            for fname in [
                "state.json",
                "complete.json",
                "iterations.json",
                "decision-log.json",
            ]:
                fp = state.change_dir / fname
                if fp.exists():
                    log(state, f"  {fp}")
        log(state, "")
        log(state, "To resume: Run script again with same change-id")
    else:
        if state.change_dir:
            for fname in ["state.json", "complete.json"]:
                fp = state.change_dir / fname
                if fp.exists():
                    try:
                        fp.unlink()
                    except OSError:
                        log_warning(state, f"Failed to remove {fname}")

        baseline = Path(".openspec-baseline.json")
        if baseline.exists():
            try:
                baseline.unlink()
            except OSError:
                log_warning(state, "Failed to remove .openspec-baseline.json")

        if state.log_file and not state.log_user_specified and state.log_file.exists():
            try:
                state.log_file.unlink()
            except OSError:
                log_warning(state, f"Failed to remove {state.log_file}")


def _extract_changes(payload) -> list:
    """Extract change list from various CLI JSON shapes."""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        if "changes" in payload and isinstance(payload["changes"], list):
            return payload["changes"]
        if "items" in payload and isinstance(payload["items"], list):
            return payload["items"]
    return []


def list_changes() -> None:
    print("Available OpenSpec changes:")
    print("")

    # Aggregate from registered stores
    try:
        stores_data = osx_lib.store_list().get("data", {})
        stores = []
        if isinstance(stores_data, dict):
            for key in ("stores", "items", "results"):
                if isinstance(stores_data.get(key), list):
                    stores = stores_data[key]
                    break
        elif isinstance(stores_data, list):
            stores = stores_data
        for s in stores:
            store_id = s.get("id", "?") if isinstance(s, dict) else str(s)
            try:
                payload = osx_lib._run_openspec_json(["list", "--store", store_id])
                for ch in _extract_changes(payload):
                    if isinstance(ch, dict):
                        print(f"  {store_id}:{ch.get('name', '')}")
            except osx_lib.OSXError:
                pass
    except osx_lib.OSXError:
        pass

    print("")
    print("From openspec/changes/ directory:")

    changes_dir = Path("openspec/changes")
    if changes_dir.is_dir():
        for d in sorted(changes_dir.iterdir()):
            if d.is_dir() and d.name != "archive":
                valid_marker = " ✓"
                required = ["tasks.md", "proposal.md", "design.md"]
                specs_dir = d / "specs"
                if (
                    not all((d / f).exists() for f in required)
                    or not specs_dir.is_dir()
                ):
                    valid_marker = " ✗"
                print(f"  {d.name}{valid_marker}")

    print("")
    print("Legend: ✓ = valid structure, ✗ = missing required files")


def run_orchestrator(state: Optional[OrchestratorState] = None) -> None:
    if state is None:
        state = OrchestratorState()

    signal.signal(signal.SIGINT, lambda s, f: handle_interrupt(s, f, state))
    signal.signal(signal.SIGTERM, lambda s, f: handle_interrupt(s, f, state))

    if state.list_changes:
        list_changes()
        raise SystemExit(0)

    if not state.change_id:
        log_error(state, "No change ID specified")
        raise SystemExit(1)

    # If change_id is in store:change form, split it (only when no --store was given)
    if ":" in state.change_id and not state.store:
        store_id, change = parse_change_spec(state.change_id)
        state.store = store_id
        state.change_id = change

    state.change_dir = find_change_dir(state.change_id, store=state.store)
    if not state.change_dir:
        log_error(state, f"Change not found: {state.change_id}")
        print("")
        print("Tried:")
        print(f"  - Direct path: openspec/changes/{state.change_id}")
        if state.store:
            print(f"  - Store: {state.store}")
        try:
            cmd = ["openspec", "list"]
            if state.store:
                cmd[1:1] = ["--store", state.store]
            subprocess.run(cmd, capture_output=True)
            print("  - CLI lookup: openspec list")
        except FileNotFoundError:
            pass
        print("")
        print("Run 'openspec-extended orchestrate --list' to see available changes")
        raise SystemExit(1)

    # All osx_lib calls below this point will see state.store via the contextvar
    token = osx_lib.current_store.set(state.store)
    try:
        if (
            "archive" in str(state.change_dir)
            and not (state.change_dir / "state.json").exists()
        ):
            log_success(
                state, f"Change '{state.change_id}' is already archived and complete"
            )
            log(state, f"Archive location: {state.change_dir}")
            raise SystemExit(0)

        if state.log_file:
            state.log_file = Path(state.log_file)
            state.log_user_specified = True
        else:
            state.log_file = Path(f".osx-orchestrate-{state.change_id}.log")
            state.log_user_specified = False

        state.start_time = int(datetime.now(timezone.utc).timestamp())

        log(state, "")
        log(state, "================================")
        log(state, "OpenSpec Autonomous Implementation")
        log(state, "================================")
        log(state, f"Version: {get_version()}")
        log(state, f"Change ID: {state.change_id}")
        log(state, f"Change directory: {state.change_dir}")
        if state.model:
            log(state, f"Model: {state.model}")
        log(state, f"Max phase iterations: {state.max_phase_iterations}")
        log(state, f"Timeout: {state.timeout} seconds")
        if state.log_file:
            log(state, f"Log file: {state.log_file}")
        log(state, "================================")
        log(state, "")

        if state.clean:
            log_verbose(state, "Cleaning up state files for fresh start...")
            if state.change_dir:
                for fname in ["state.json", "complete.json", "iterations.json"]:
                    fp = state.change_dir / fname
                    if fp.exists():
                        try:
                            fp.unlink()
                        except OSError:
                            pass
            baseline = Path(".openspec-baseline.json")
            if baseline.exists():
                try:
                    baseline.unlink()
                except OSError:
                    pass
            log_file_unset = Path(f".osx-orchestrate-{state.change_id}.log")
            if log_file_unset.exists():
                try:
                    log_file_unset.unlink()
                except OSError:
                    pass
            log_verbose(state, "State files cleaned, starting fresh")

            if not state.from_phase:
                try:
                    subprocess.run(
                        ["git", "rev-parse", "HEAD"], capture_output=True, check=True
                    )
                except (subprocess.CalledProcessError, FileNotFoundError):
                    log_error(state, "Required tool not found: git")
                    raise SystemExit(1)

                try:
                    subprocess.run(["jq", "--version"], capture_output=True)
                except FileNotFoundError:
                    log_error(state, "Required tool not found: jq")
                    raise SystemExit(1)

                try:
                    subprocess.run(["openspec", "--version"], capture_output=True)
                except FileNotFoundError:
                    log_error(state, "Required tool not found: openspec")
                    raise SystemExit(1)

                try:
                    subprocess.run(["opencode", "--version"], capture_output=True)
                except FileNotFoundError:
                    log_error(state, "Required tool not found: opencode")
                    raise SystemExit(1)

                validate_skills(state)
                validate_commands(state)
                validate_git(state)
                validate_change_dir(state)
                validate_schema(state)

                record_baseline(state)
            else:
                log(state, "Skipping pre-flight validation (--from-phase specified)")

        resume_phase = None
        data = read_state(state)
        if not state.from_phase and data:
            resume_phase = data.get("phase")
            if resume_phase:
                log(
                    state,
                    f"Resuming from phase: {resume_phase} - {PHASE_NAMES.get(resume_phase, 'UNKNOWN')}",
                )

                if not state.force and os.isatty(0):
                    print("")
                    reply = input("Continue? [Y/n] ")
                    print("")
                    if reply.lower().startswith("n"):
                        log_error(state, "Aborted by user")
                        raise SystemExit(1)
                else:
                    log(state, "Auto-continuing (non-interactive or --force)")

        current_phase = "PHASE0"
        started = False
        phase_determined = False

        if resume_phase:
            current_phase = resume_phase
            phase_determined = True

        try:
            while True:
                if not started and state.from_phase:
                    current_phase = state.from_phase
                    log(
                        state,
                        f"Starting from phase: {current_phase} - {PHASE_NAMES.get(current_phase, 'UNKNOWN')}",
                    )
                    started = True
                    phase_determined = True
                elif not phase_determined:
                    detected = get_current_phase(state)
                    if detected:
                        current_phase = detected
                        phase_determined = True
                    else:
                        current_phase = "PHASE0"
                        phase_determined = True

                if check_complete(state):
                    complete_file = (
                        state.change_dir / "complete.json" if state.change_dir else None
                    )
                    if complete_file and complete_file.exists():
                        try:
                            data = json.loads(complete_file.read_text())
                            if data.get("with_blocker", False):
                                blocker_reason = data.get("blocker_reason", "Unknown")
                                log(state, "")
                                log(state, "================================")
                                log_error(state, "CRITICAL BLOCKER DETECTED")
                                log(state, "================================")
                                log_warning(state, f"Blocker: {blocker_reason}")
                                log(state, "Review decision-log.json for details")
                                show_progress(state)

                                raise SystemExit(1)
                        except json.JSONDecodeError:
                            pass

                if current_phase in PHASES:
                    if not run_phase(state, current_phase):
                        log_error(state, f"{current_phase} failed")
                        raise SystemExit(1)

                    show_progress(state)

                    if current_phase == "PHASE6":
                        if (
                            state.log_file
                            and not state.log_user_specified
                            and state.log_file.exists()
                        ):
                            if not archive_log_file(state):
                                log_error(state, "Log file archiving failed")
                                log_error(
                                    state,
                                    "Archive validation will not proceed without log file",
                                )
                                raise SystemExit(1)

                        success, _ = validate_archive(state)
                        if success:
                            log(state, "")
                            log(state, "================================")
                            log_success(state, "Implementation completed successfully!")
                            log(state, "================================")
                            raise SystemExit(0)
                        else:
                            log(state, "")
                            log_error(state, "Archive validation failed")
                            log(state, "State files preserved for investigation")
                            raise SystemExit(1)

                    has_transition, transition_target = check_transition(state)
                    if has_transition and transition_target:
                        reason = get_transition_reason(state)
                        details = get_transition_details(state)

                        log(
                            state,
                            f"Explicit transition: {current_phase} -> {transition_target}",
                        )
                        log_verbose(state, f"Reason: {reason}")
                        if details:
                            log_verbose(state, f"Details: {details}")

                        clear_transition(state)
                        clear_phase_complete(state)
                        current_phase = transition_target
                    else:
                        next_phase = advance_phase(current_phase)
                        log(state, f"Phase transition: {current_phase} -> {next_phase}")
                        current_phase = next_phase

                elif current_phase == "COMPLETE":
                    log(state, "All phases complete, validating...")
                    break

                else:
                    log_error(state, f"Unknown phase: {current_phase}")
                    raise SystemExit(1)

        except SystemExit as e:
            cleanup(state, int(e.code) if e.code else 0)
            raise
    finally:
        osx_lib.current_store.reset(token)
