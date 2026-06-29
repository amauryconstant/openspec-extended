#!/usr/bin/env python3
"""
osx_cli - Typer CLI surface for the osx change-management library

Exposes the library functions in `source.lib.osx` as
`openspec-extended osx <domain> <action> [args]`. Each command is a
thin wrapper that catches `OSXError`, prints a JSON error to stderr,
and exits non-zero. Successful commands print a JSON dict to stdout.

This module exists separately from `source.lib.osx` so the library
can be imported in-process (orchestrator, tests) without pulling in
the Typer/CLI surface.
"""

import json
import subprocess
import sys
from typing import Optional

import typer

from source.lib import osx as osx_lib

osx_app = typer.Typer(help="OpenSpec Extended change management tool")


@osx_app.callback()
def _osx_app_callback(
    ctx: typer.Context,
    store: Optional[str] = typer.Option(
        None,
        "--store",
        "-s",
        help="OpenSpec store id (defaults to nearest openspec/ root)",
    ),
) -> None:
    if store is not None:
        token = osx_lib.current_store.set(store)
        ctx.obj = {"store_token": token, "store": store}
        ctx.call_on_close(lambda: osx_lib.current_store.reset(token))
    else:
        ctx.obj = {}


def osx_error(code: str, message: str, **context) -> None:
    """Print an error JSON to stderr and exit non-zero."""
    result = {"error": code, "message": message}
    result.update(context)
    print(json.dumps(result), file=sys.stderr)
    raise typer.Exit(1)


def osx_output(data: dict) -> None:
    print(json.dumps(data))


def _call_library(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except osx_lib.OSXError as e:
        osx_error(e.code, e.message, **e.context)


@osx_app.command(name="baseline")
def baseline_cmd(
    action: str = typer.Argument(..., help="Action: record, get"),
) -> None:
    if action == "record":
        data = _call_library(osx_lib.baseline_record)
    elif action == "get" or action == "show":
        data = _call_library(osx_lib.baseline_get)
    else:
        osx_error("invalid_action", f"Unknown action: {action}", valid="record, get")
        return
    osx_output(data)


@osx_app.command(name="ctx")
def ctx_cmd(
    action: str = typer.Argument(..., help="Action: get"),
    change: str = typer.Argument(..., help="Change name"),
) -> None:
    if action == "get" or action == "show":
        data = _call_library(osx_lib.ctx_get, change)
    else:
        osx_error("invalid_action", f"Unknown action: {action}", valid="get")
        return
    osx_output(data)


@osx_app.command(name="git")
def git_cmd(
    action: str = typer.Argument(..., help="Action: get"),
    change: str = typer.Argument(..., help="Change name"),
) -> None:
    if action == "get" or action == "show":
        data = _call_library(osx_lib.git_get, change)
    else:
        osx_error("invalid_action", f"Unknown action: {action}", valid="get")
        return
    osx_output(data)


@osx_app.command(name="phase")
def phase_cmd(
    action: str = typer.Argument(..., help="Action: current, next, advance"),
    change: str = typer.Argument(..., help="Change name"),
) -> None:
    if action == "current":
        data = _call_library(osx_lib.phase_current, change)
    elif action == "next":
        data = _call_library(osx_lib.phase_next, change)
    elif action == "advance":
        data = _call_library(osx_lib.phase_advance, change)
    else:
        osx_error(
            "invalid_action",
            f"Unknown action: {action}",
            valid="current, next, advance",
        )
        return
    osx_output(data)


@osx_app.command(name="state")
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
    if action == "get" or action == "show":
        data = _call_library(osx_lib.state_get, change)
    elif action == "complete":
        data = _call_library(osx_lib.state_complete, change)
    elif action == "transition":
        data = _call_library(osx_lib.state_transition, change, target, reason, details)
    elif action == "clear-transition" or action == "clear":
        data = _call_library(osx_lib.state_clear_transition, change)
    elif action == "set-phase" or action == "set":
        data = _call_library(osx_lib.state_set_phase, change, phase, iteration)
    else:
        osx_error(
            "invalid_action",
            f"Unknown action: {action}",
            valid="get, complete, transition, clear-transition, set-phase",
        )
        return
    osx_output(data)


@osx_app.command(name="iterations")
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
    if action == "get" or action == "show" or action == "list":
        data = _call_library(osx_lib.iterations_get, change)
    elif action == "append":
        data = _call_library(
            osx_lib.iterations_append,
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


@osx_app.command(name="log")
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
    if action == "get" or action == "show" or action == "list":
        data = _call_library(osx_lib.log_get, change)
    elif action == "append":
        data = _call_library(
            osx_lib.log_append,
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


@osx_app.command(name="complete")
def complete_cmd(
    action: str = typer.Argument(..., help="Action: check, get, set"),
    change: str = typer.Argument(..., help="Change name"),
    status: Optional[str] = typer.Argument(None, help="Status (COMPLETE or BLOCKED)"),
    blocker_reason: Optional[str] = typer.Option(
        None, "--blocker-reason", help="Blocker reason"
    ),
) -> None:
    if action == "check":
        data = _call_library(osx_lib.complete_check, change)
        osx_output(data)
        if not data.get("exists", False):
            raise typer.Exit(1)
    elif action == "get":
        data = _call_library(osx_lib.complete_get, change)
        osx_output(data)
    elif action == "set":
        data = _call_library(osx_lib.complete_set, change, status, blocker_reason)
        osx_output(data)
    else:
        osx_error(
            "invalid_action", f"Unknown action: {action}", valid="check, get, set"
        )
        return


@osx_app.command(name="validate")
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
        data = osx_lib.validate_json(target)
    elif action == "skills":
        data = osx_lib.validate_skills()
    elif action == "commands":
        data = osx_lib.validate_commands()
    elif action == "change-dir":
        if target is None:
            osx_error("missing_field", "change name required for change-dir validation")
            return
        data = osx_lib.validate_change_dir(target)
    elif action == "archive":
        if target is None:
            osx_error("missing_field", "change name required for archive validation")
            return
        data = osx_lib.validate_archive(target)
    elif action == "iterations":
        if target is None:
            osx_error("missing_field", "change name required for iterations validation")
            return
        data = osx_lib.validate_iterations(target)
    elif action == "completion":
        if target is None:
            osx_error("missing_field", "change name required for completion validation")
            return
        data = osx_lib.validate_completion(target)
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


@osx_app.command(name="instructions")
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


store_app = typer.Typer(help="OpenSpec store management")
osx_app.add_typer(store_app, name="store")


@store_app.command("list")
def store_list_cmd() -> None:
    """List registered OpenSpec stores."""
    data = _call_library(osx_lib.store_list)
    osx_output(data)


@store_app.command("doctor")
def store_doctor_cmd(
    store: Optional[str] = typer.Argument(None, help="Store id (omit to check all)"),
) -> None:
    """Check health of a registered store (or all when id is omitted)."""
    data = _call_library(osx_lib.store_doctor, store)
    osx_output(data)


@store_app.command("register")
def store_register_cmd(
    path: str = typer.Argument(..., help="Filesystem path to the store repo"),
    name: Optional[str] = typer.Option(None, "--name", help="Display name"),
) -> None:
    """Register a new OpenSpec store."""
    data = _call_library(osx_lib.store_register, path, name)
    osx_output(data)


@store_app.command("unregister")
def store_unregister_cmd(store: str = typer.Argument(..., help="Store id")) -> None:
    """Unregister an OpenSpec store."""
    data = _call_library(osx_lib.store_unregister, store)
    osx_output(data)
