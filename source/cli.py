#!/usr/bin/env python3
"""
OpenSpec-extended - Unified CLI for OpenSpec resources and autonomous workflow
"""

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import toml
import typer
from rich.console import Console

from source import __version__
from source.lib.osx import REQUIRED_CORE_SKILLS
from source.osx_cli import osx_app
from source.orchestrator.engine import OrchestratorState, run_orchestrator

SCRIPT_VERSION = "1.2.1"
SCRIPT_NAME = "openspec-extended"

TOOL_DIRS = {"opencode": ".opencode", "claude": ".claude"}

console = Console()

app = typer.Typer(
    name=SCRIPT_NAME,
    help=f"{SCRIPT_NAME} - Installer and orchestrator for OpenSpec resources",
    add_completion=False,
)
app.add_typer(osx_app, name="osx")


def get_resources_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", "")) / "resources"
    return Path(__file__).parent.parent / "resources"


def log_success(message: str) -> None:
    console.print(f"[green]✓[/green] {message}")


def log_info(message: str) -> None:
    console.print(f"[blue]→[/blue] {message}")


def log_error(message: str) -> None:
    typer.secho(f"✗ {message}", fg="red", err=True)


def log_warn(message: str) -> None:
    console.print(f"[yellow]![/yellow] {message}")


def get_tool_dir(tool: str) -> str:
    result = TOOL_DIRS.get(tool)
    if result is None:
        raise ValueError(f"Unknown tool: {tool}")
    return result


def parse_version(v: str) -> tuple[int, int, int]:
    match = re.match(r"^(\d+)\.(\d+)\.(\d+)$", v)
    if not match:
        return (0, 0, 0)
    return (int(match.group(1)), int(match.group(2)), int(match.group(3)))


def compare_versions(v1: str, v2: str) -> int:
    if not v1 or not v2:
        return 0
    p1 = parse_version(v1)
    p2 = parse_version(v2)
    for n1, n2 in zip(p1, p2):
        if n1 > n2:
            return 1
        elif n1 < n2:
            return -1
    return 0


def run_openspec(args: list[str], timeout: int = 30) -> int:
    """Run `openspec <args>` and forward stdout/stderr. Returns exit code.

    Raises SystemExit(1) if openspec is not installed or times out.
    """
    cmd = ["openspec", *args]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        log_error("openspec CLI not found. Install it first:")
        console.print("  npm install -g @fission-ai/openspec")
        raise SystemExit(1)
    except subprocess.TimeoutExpired:
        log_error(f"openspec command timed out after {timeout}s")
        raise SystemExit(1)

    if result.stdout:
        sys.stdout.write(result.stdout)
        sys.stdout.flush()
    if result.stderr:
        sys.stderr.write(result.stderr)
        sys.stderr.flush()
    return result.returncode


def get_installed_version(manifest: Path, resource_type: str, name: str) -> str:
    if not manifest.is_file():
        return ""
    try:
        data = toml.loads(manifest.read_text())
        return (
            data.get("resources", {})
            .get(resource_type, {})
            .get(name, {})
            .get("version", "")
        )
    except (toml.TomlDecodeError, KeyError):
        return ""


def should_deploy(
    name: str,
    source_version: str,
    target_path: Path,
    target_manifest: Path,
    resource_type: str,
    force: bool,
) -> str:
    if force:
        return "update"
    if not target_path.exists():
        return "install"
    installed = get_installed_version(target_manifest, resource_type, name)
    if not installed:
        return "install"
    cmp_result = compare_versions(source_version, installed)
    if cmp_result == 1:
        return "upgrade"
    return "skip"


def get_target_path(resource_type: str, target_dir: Path, name: str) -> Path:
    if resource_type == "skills":
        return target_dir / "skills" / name
    elif resource_type == "commands":
        cmd_path = target_dir / "commands" / f"{name}.md"
        if cmd_path.exists():
            return cmd_path
        commands_dir = target_dir / "commands"
        if commands_dir.is_dir():
            for subdir in commands_dir.iterdir():
                if subdir.is_dir():
                    base_name = (
                        name.replace("osx-", "", 1) if name.startswith("osx-") else name
                    )
                    alt_path = subdir / f"{base_name}.md"
                    if alt_path.exists():
                        return alt_path
        return cmd_path
    elif resource_type == "agents":
        return target_dir / "agents" / f"{name}.md"
    return target_dir / resource_type / name


def deploy_skills(source_base: Path, target_dir: Path, name: str) -> None:
    target_skills = target_dir / "skills"
    target_skills.mkdir(parents=True, exist_ok=True)
    target_path = target_skills / name
    if target_path.exists():
        shutil.rmtree(target_path)
    shutil.copytree(source_base / name, target_path)


def deploy_commands(source_base: Path, target_dir: Path, name: str) -> None:
    target_commands = target_dir / "commands"
    target_commands.mkdir(parents=True, exist_ok=True)
    source_path = source_base / f"{name}.md"
    if source_path.exists():
        shutil.copy2(source_path, target_commands / f"{name}.md")
    else:
        for subdir in source_base.iterdir():
            if subdir.is_dir():
                base_name = (
                    name.replace("osx-", "", 1) if name.startswith("osx-") else name
                )
                alt_source = subdir / f"{base_name}.md"
                if alt_source.exists():
                    subdir_name = subdir.name
                    (target_commands / subdir_name).mkdir(parents=True, exist_ok=True)
                    shutil.copy2(
                        alt_source, target_commands / subdir_name / f"{base_name}.md"
                    )
                    return
        raise FileNotFoundError(f"Command not found: {name}")


def deploy_agents(source_base: Path, target_dir: Path, name: str) -> None:
    target_agents = target_dir / "agents"
    target_agents.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_base / f"{name}.md", target_agents / f"{name}.md")


def get_source_type_dir(source_dir: Path, resource_type: str) -> Path:
    type_map = {
        "skills": "skills",
        "commands": "commands",
        "agents": "agents",
    }
    return source_dir / type_map.get(resource_type, resource_type)


def deploy_type(
    resource_type: str,
    source_dir: Path,
    target_dir: Path,
    target_manifest: Path,
    source_manifest: dict,
    force: bool,
    tool: str,
) -> tuple[int, int]:
    source_type_dir = get_source_type_dir(source_dir, resource_type)
    if not source_type_dir.is_dir():
        return (0, 0)

    resources = source_manifest.get("resources", {}).get(resource_type, {})
    if not resources:
        return (0, 0)

    count = 0
    skipped = 0

    for name, info in resources.items():
        source_version = info.get("version", "")
        if not source_version:
            continue

        target_path = get_target_path(resource_type, target_dir, name)
        decision = should_deploy(
            name, source_version, target_path, target_manifest, resource_type, force
        )

        if decision in ("install", "upgrade", "update"):
            deploy_func_map = {
                "skills": deploy_skills,
                "commands": deploy_commands,
                "agents": deploy_agents,
            }
            func = deploy_func_map.get(resource_type)
            if func:
                func(source_type_dir, target_dir, name)
            count += 1
        elif decision == "skip":
            skipped += 1

    if count > 0:
        type_label = resource_type
        if resource_type == "skills" and count == 1:
            type_label = "skill"
        elif resource_type == "commands" and count == 1:
            type_label = "command"
        elif resource_type == "agents" and count == 1:
            type_label = "agent"
        log_success(f"Deployed {count} {type_label} to {tool}")
        console.print(f"  Target: {target_dir}/{resource_type}/")

    if skipped > 0:
        console.print(f"  Skipped {skipped} current {resource_type}")

    return (count, skipped)


def deploy_all_resources(tool: str, force: bool) -> None:
    resources_dir = get_resources_dir()
    source_dir = resources_dir / tool
    source_manifest_path = source_dir / "manifest.toml"

    if not source_manifest_path.is_file():
        log_error(f"Manifest not found: {source_manifest_path}")
        raise SystemExit(1)

    source_manifest = toml.loads(source_manifest_path.read_text())
    source_version = __version__

    target_dir = Path.cwd() / TOOL_DIRS[tool]
    target_manifest = target_dir / "manifest.toml"

    target_dir.mkdir(parents=True, exist_ok=True)

    total_count = 0
    total_skipped = 0

    for resource_type in ("skills", "commands", "agents"):
        cnt, skp = deploy_type(
            resource_type,
            source_dir,
            target_dir,
            target_manifest,
            source_manifest,
            force,
            tool,
        )
        total_count += cnt
        total_skipped += skp

    manifest_data = source_manifest.copy()
    manifest_data["version"] = source_version
    target_manifest.write_text(toml.dumps(manifest_data))
    log_success(f"Manifest updated to v{source_version}")
    console.print(f"  Target: {target_dir}/manifest.toml")

    if total_count == 0 and total_skipped == 0:
        console.print("No resources to deploy")
    elif total_count == 0 and total_skipped > 0:
        console.print(f"All {total_skipped} resources are current")


def update_gitignore() -> None:
    gitignore = Path.cwd() / ".gitignore"
    marker_start = "# BEGIN OpenSpec autonomous workflow state"
    marker_end = "# END OpenSpec autonomous workflow state"

    if not gitignore.exists():
        gitignore.touch()

    content = gitignore.read_text()
    if marker_start in content:
        return

    entries = [
        "",
        marker_start,
        ".openspec-baseline.json",
        CORE_BASELINE_FILENAME,
        "openspec/changes/*/state.json",
        "openspec/changes/*/complete.json",
        "openspec/changes/*/iterations.json",
        "openspec/changes/*/decision-log.json",
        "openspec/changes/*/verification-report.md",
        "openspec/changes/*/reflections.md",
        "openspec/changes/*/test-compliance-report.md",
        "openspec/changes/*/suggestions.md",
        ".osx-orchestrate-*.log",
        marker_end,
    ]
    gitignore.write_text(content + "\n".join(entries) + "\n")
    log_success("Added OpenSpec state files to .gitignore")


def rename_core_resources(tool: str) -> None:
    target_dir = Path.cwd() / get_tool_dir(tool)
    log_info("Renaming core resources (opsx-* → osc-*, openspec-* → osc-*)...")

    renamed = 0
    commands_dir = target_dir / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)

    for cmd_dir in [commands_dir, target_dir / "command"]:
        if not cmd_dir.is_dir():
            continue

        for cmd_file in cmd_dir.glob("*.md"):
            basename = cmd_file.name
            if re.match(r"^opsx-(.+)\.md$", basename):
                new_name = re.sub(r"^opsx-(.+)\.md$", r"osc-\1.md", basename)
                cmd_file.rename(cmd_dir / new_name)
                renamed += 1
            elif cmd_dir == target_dir / "command" and re.match(
                r"^osc-(.+)\.md$", basename
            ):
                cmd_file.rename(commands_dir / basename)

        for subdir_name in ("osx", "opsx"):
            subdir = cmd_dir / subdir_name
            if subdir.is_dir():
                osc_dir = commands_dir / "osc"
                if not osc_dir.is_dir():
                    subdir.rename(osc_dir)
                else:
                    for f in subdir.glob("*.md"):
                        f.rename(osc_dir / f.name)
                    subdir.rmdir()
                renamed += 1

    old_command_dir = target_dir / "command"
    if old_command_dir.is_dir():
        try:
            old_command_dir.rmdir()
        except OSError:
            pass

    for cmd_file in commands_dir.rglob("*.md"):
        content = cmd_file.read_text()
        content = content.replace("/opsx-", "/osc-")
        content = content.replace("/opsx:", "/osc:")
        content = content.replace("OPSX: ", "OSC: ")
        cmd_file.write_text(content)

    skills_dir = target_dir / "skills"
    if skills_dir.is_dir():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and skill_dir.name.startswith("openspec-"):
                new_name = skill_dir.name.replace("openspec-", "osc-", 1)
                dest_dir = skills_dir / new_name
                if dest_dir.exists():
                    for f in skill_dir.glob("*"):
                        f.rename(dest_dir / f.name)
                    skill_dir.rmdir()
                else:
                    skill_dir.rename(dest_dir)
                renamed += 1

        for skill_file in skills_dir.rglob("*.md"):
            content = skill_file.read_text()
            content = re.sub(
                r"^name: openspec-", "name: osc-", content, flags=re.MULTILINE
            )
            content = content.replace("/opsx-", "/osc-")
            content = content.replace("/opsx:", "/osc:")
            content = content.replace("OPSX: ", "OSC: ")
            skill_file.write_text(content)

    if renamed > 0:
        log_success(f"Renamed {renamed} core resource(s)")


CORE_BASELINE_FILENAME = ".openspec-extended-baseline.json"


def _detect_existing_core_deployment(tool: str) -> bool:
    """Return True if a previous core deployment is detectable.

    Detection sources (any one is enough):
    - ``openspec list --json`` returns any resources.
    - ``<target_dir>/skills/osc-*.md`` exists (post-rename marker).
    - ``<target_dir>/manifest.toml`` declares ``[core].installed = true``.
    """
    target_dir = Path.cwd() / get_tool_dir(tool)

    # (a) upstream CLI introspection
    try:
        result = subprocess.run(
            ["openspec", "list", "--json"],
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
        payload = json.loads(result.stdout or "{}")
        for key in ("skills", "specs", "changes", "items"):
            if payload.get(key):
                return True
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
        ValueError,
    ):
        pass

    # (b) post-rename marker
    skills_dir = target_dir / "skills"
    if skills_dir.is_dir():
        for p in skills_dir.iterdir():
            if p.is_dir() and p.name.startswith("osc-"):
                return True

    # (c) manifest declaration
    manifest_path = target_dir / "manifest.toml"
    if manifest_path.is_file():
        try:
            manifest_data = toml.loads(manifest_path.read_text())
            if manifest_data.get("core", {}).get("installed"):
                return True
        except toml.TomlDecodeError:
            pass

    return False


def _capture_global_config() -> dict:
    """Snapshot the user's openspec global config.

    Best-effort: missing files / unreadable / non-JSON content returns
    an empty dict. The caller must persist whatever it can.
    """
    candidates = [
        Path.home() / ".config" / "openspec" / "config.json",
    ]
    for path in candidates:
        if path.is_file():
            try:
                return toml.loads(path.read_text())
            except toml.TomlDecodeError:
                try:
                    return json.loads(path.read_text())
                except (ValueError, OSError):
                    return {}
    return {}


def _write_core_baseline(tool: str, project_root: Path | None = None) -> Path | None:
    """Write ``.openspec-extended-baseline.json`` capturing the user's prior
    openspec core setup. Returns the path written, or None if nothing to save.
    """
    project_root = project_root or Path.cwd()
    from datetime import datetime, timezone

    snapshot = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "tool": tool,
        "global_config": _capture_global_config(),
        "project_root": str(project_root),
    }
    path = project_root / CORE_BASELINE_FILENAME
    try:
        path.write_text(json.dumps(snapshot, indent=2))
        return path
    except OSError:
        return None


def deploy_core(tool: str, force: bool = False) -> None:
    target_dir = Path.cwd() / get_tool_dir(tool)
    target_manifest = target_dir / "manifest.toml"

    # Non-destructive: refuse to overwrite an existing deployment without --force.
    if _detect_existing_core_deployment(tool) and not force:
        log_error(
            "An existing core deployment was detected. Re-run with --force to"
            " overwrite (a snapshot will be saved to .openspec-extended-baseline.json)."
        )
        console.print("  Hint: openspec-extended install <tool> --with-core --force")
        console.print("  Restore later with: openspec-extended restore-core")
        raise SystemExit(2)

    # With --force on an existing deploy, capture a baseline first.
    baseline_path: Path | None = None
    if force and _detect_existing_core_deployment(tool):
        baseline_path = _write_core_baseline(tool)
        if baseline_path:
            log_info(f"Saved pre-overwrite baseline to {baseline_path.name}")

    try:
        subprocess.run(
            ["openspec", "init", "--tools", tool, "--force"],
            check=True,
            capture_output=True,
        )
    except FileNotFoundError:
        log_error("openspec CLI not found. Install it first:")
        console.print("  npm install -g @fission-ai/openspec")
        raise SystemExit(1)
    except subprocess.CalledProcessError as e:
        log_error("openspec init failed")
        console.print(f"[red]{e.stderr}[/red]")
        raise SystemExit(1)

    rename_core_resources(tool)

    try:
        result = subprocess.run(
            ["openspec", "--version"], capture_output=True, text=True, check=True
        )
        core_version_match = re.search(r"(\d+\.\d+\.\d+)", result.stdout)
        core_version = core_version_match.group(1) if core_version_match else "unknown"
    except (subprocess.CalledProcessError, FileNotFoundError):
        core_version = "unknown"

    skills_dir = target_dir / "skills"
    manifest_updates = {}
    for skill_dir in skills_dir.iterdir():
        if skill_dir.is_dir() and skill_dir.name.startswith("osc-"):
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                match = re.search(
                    r'^version:\s*"([^"]+)"', skill_md.read_text(), re.MULTILINE
                )
                version = match.group(1) if match else core_version
                manifest_updates[skill_dir.name] = {"version": version}

    for skill in REQUIRED_CORE_SKILLS:
        if not (skills_dir / skill).is_dir():
            log_error(f"Core skill not installed: {skill}")
            raise SystemExit(1)

    log_success("Core resources installed (osc-*)")

    if manifest_updates and target_manifest.is_file():
        manifest_data = toml.loads(target_manifest.read_text())
        manifest_data.setdefault("resources", {}).setdefault("skills", {}).update(
            manifest_updates
        )
        manifest_data["core"] = {
            "version": core_version,
            "installed": True,
            "baseline": (CORE_BASELINE_FILENAME if baseline_path else None),
        }
        target_manifest.write_text(toml.dumps(manifest_data))
        log_info(f"Core v{core_version} tracked in manifest")


def validate_deployment(target_dir: Path, manifest: dict) -> None:
    warnings = 0
    if not target_dir.is_dir():
        return

    for resource_type, resources in manifest.get("resources", {}).items():
        for name in resources:
            found = False
            if resource_type == "skills":
                found = (target_dir / "skills" / name).is_dir()
            elif resource_type == "agents":
                found = (target_dir / "agents" / f"{name}.md").is_file()
            elif resource_type == "commands":
                cmd_path = target_dir / "commands" / f"{name}.md"
                if cmd_path.is_file():
                    found = True
                else:
                    base_name = (
                        name.replace("osx-", "", 1) if name.startswith("osx-") else name
                    )
                    for subdir in (target_dir / "commands").iterdir():
                        if subdir.is_dir() and (subdir / f"{base_name}.md").is_file():
                            found = True
                            break

            if not found:
                log_warn(f"Resource '{name}' in manifest but not deployed")
                warnings += 1

    if warnings > 0:
        console.print(f"  Validation: {warnings} warning(s)")


@app.command(
    "install",
    help="Deploy extended resources (skills, commands, agents, scripts) to tool directory",
)
def install(
    tool: str = typer.Argument(..., help="Target tool: opencode or claude"),
    with_core: bool = typer.Option(
        False, "--with-core", help="Also deploy core OpenSpec skills"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help=(
            "Required to overwrite an existing core deployment when "
            "--with-core is set. A snapshot of the prior state is saved "
            "automatically."
        ),
    ),
) -> None:
    if tool not in TOOL_DIRS:
        log_error(f"Unknown tool: {tool}")
        console.print("  Available tools: opencode, claude")
        raise SystemExit(1)

    target_dir = Path.cwd() / TOOL_DIRS[tool]
    deploy_all_resources(tool, force=False)

    update_gitignore()

    if with_core:
        deploy_core(tool, force=force)

    resources_dir = get_resources_dir()
    source_manifest = resources_dir / tool / "manifest.toml"
    if source_manifest.is_file():
        manifest_data = toml.loads(source_manifest.read_text())
        validate_deployment(target_dir, manifest_data)


@app.command(
    "update",
    help="Force reinstall all resources (same as install but always overwrites)",
)
def update(
    tool: str = typer.Argument(..., help="Target tool: opencode or claude"),
    with_core: bool = typer.Option(
        False, "--with-core", help="Also deploy core OpenSpec skills"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help=(
            "Required to overwrite an existing core deployment when "
            "--with-core is set. A snapshot of the prior state is saved "
            "automatically."
        ),
    ),
) -> None:
    if tool not in TOOL_DIRS:
        log_error(f"Unknown tool: {tool}")
        console.print("  Available tools: opencode, claude")
        raise SystemExit(1)

    target_dir = Path.cwd() / TOOL_DIRS[tool]
    deploy_all_resources(tool, force=True)

    update_gitignore()

    if with_core:
        deploy_core(tool, force=force)

    resources_dir = get_resources_dir()
    source_manifest = resources_dir / tool / "manifest.toml"
    if source_manifest.is_file():
        manifest_data = toml.loads(source_manifest.read_text())
        validate_deployment(target_dir, manifest_data)


@app.command("orchestrate", help="Run the 7-phase autonomous change workflow")
def orchestrate(
    ctx: typer.Context,
    change_name: Optional[str] = typer.Argument(
        None, help="OpenSpec change ID or 'store:change'"
    ),
    store: Optional[str] = typer.Option(
        None, "--store", help="OpenSpec store id (defaults to nearest openspec/ root)"
    ),
    timeout: int = typer.Option(
        1800, "--timeout", "-t", help="Timeout per iteration (seconds)"
    ),
    model: str = typer.Option("", "--model", "-m", help="AI model to use"),
    log_file: str = typer.Option(None, "--log-file", "-l", help="Log output file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    dry_run: bool = typer.Option(
        False, "--dry-run", "-d", help="Show what would be done"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Continue without prompts"),
    clean: bool = typer.Option(
        False, "--clean", "-c", help="Clean state for fresh start"
    ),
    no_color: bool = typer.Option(
        False, "--no-color", "-n", help="Disable colored output"
    ),
    max_phase_iterations: int = typer.Option(
        10, "--max-phase-iterations", help="Max retries per phase"
    ),
    from_phase: str = typer.Option(
        "", "--from-phase", help="Resume from specific phase"
    ),
    schema: Optional[str] = typer.Option(
        None, "--schema", help="Override schema resolution"
    ),
    list_changes: bool = typer.Option(False, "--list", help="List available changes"),
) -> None:
    if not list_changes and not change_name:
        log_error("orchestrate: missing change ID (or pass --list)")
        raise typer.Exit(code=2)

    parsed_store: Optional[str] = None
    parsed_change = change_name
    if change_name and ":" in change_name and not store:
        parsed_store, _, parsed_change = change_name.partition(":")

    state = OrchestratorState()
    state.change_id = parsed_change or change_name or ""
    state.store = store or parsed_store
    state.max_phase_iterations = max_phase_iterations
    state.timeout = timeout
    state.verbose = verbose
    state.dry_run = dry_run
    state.force = force
    state.clean = clean
    state.from_phase = from_phase
    state.no_color = no_color
    state.model = model
    state.list_changes = list_changes
    state.schema_override = schema
    if log_file:
        state.log_file = Path(log_file)
        state.log_user_specified = True

    run_orchestrator(state)


@app.command(
    "validate", help="Validate changes and specs (passthrough to openspec validate)"
)
def validate_cmd(
    item_name: Optional[str] = typer.Argument(None, help="Change or spec ID"),
    all: bool = typer.Option(False, "--all", help="Validate all changes and specs"),
    changes: bool = typer.Option(False, "--changes", help="Validate only changes"),
    specs: bool = typer.Option(False, "--specs", help="Validate only specs"),
    type_: Optional[str] = typer.Option(
        None, "--type", help="Disambiguate: change|spec"
    ),
    strict: bool = typer.Option(False, "--strict", help="Enable strict mode"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
    concurrency: Optional[int] = typer.Option(
        None, "--concurrency", help="Max concurrent validations"
    ),
    no_interactive: bool = typer.Option(
        True, "--no-interactive/--interactive", help="Disable prompts (default: true)"
    ),
    store: Optional[str] = typer.Option(None, "--store", help="OpenSpec store id"),
) -> None:
    args: list[str] = []
    if item_name:
        args.append(item_name)
    if all:
        args.append("--all")
    if changes:
        args.append("--changes")
    if specs:
        args.append("--specs")
    if type_:
        args.extend(["--type", type_])
    if strict:
        args.append("--strict")
    if json_output:
        args.append("--json")
    if concurrency is not None:
        args.extend(["--concurrency", str(concurrency)])
    if no_interactive:
        args.append("--no-interactive")
    if store:
        args.extend(["--store", store])

    code = run_openspec(["validate", *args])
    raise typer.Exit(code=code)


@app.command("list", help="List changes and specs (passthrough to openspec list)")
def list_cmd(
    specs: bool = typer.Option(False, "--specs", help="List only specs"),
    changes: bool = typer.Option(False, "--changes", help="List only changes"),
    sort: Optional[str] = typer.Option(None, "--sort", help="Sort field"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
    store: Optional[str] = typer.Option(None, "--store", help="OpenSpec store id"),
) -> None:
    args: list[str] = []
    if specs:
        args.append("--specs")
    if changes:
        args.append("--changes")
    if sort:
        args.extend(["--sort", sort])
    if json_output:
        args.append("--json")
    if store:
        args.extend(["--store", store])

    code = run_openspec(["list", *args])
    raise typer.Exit(code=code)


@app.command("show", help="Show change or spec (passthrough to openspec show)")
def show_cmd(
    item_name: Optional[str] = typer.Argument(None, help="Change or spec ID"),
    type_: Optional[str] = typer.Option(
        None, "--type", help="Disambiguate: change|spec"
    ),
    no_interactive: bool = typer.Option(
        True, "--no-interactive/--interactive", help="Disable prompts (default: true)"
    ),
    deltas_only: bool = typer.Option(False, "--deltas-only", help="Show only deltas"),
    requirements_only: bool = typer.Option(
        False, "--requirements-only", help="Show only requirements"
    ),
    requirements: bool = typer.Option(
        False, "--requirements", help="Include requirements"
    ),
    no_scenarios: bool = typer.Option(
        False, "--no-scenarios", help="Exclude scenarios"
    ),
    requirement: Optional[str] = typer.Option(
        None, "--requirement", "-r", help="Specific requirement id"
    ),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
    store: Optional[str] = typer.Option(None, "--store", help="OpenSpec store id"),
) -> None:
    args: list[str] = []
    if item_name:
        args.append(item_name)
    if type_:
        args.extend(["--type", type_])
    if no_interactive:
        args.append("--no-interactive")
    if deltas_only:
        args.append("--deltas-only")
    if requirements_only:
        args.append("--requirements-only")
    if requirements:
        args.append("--requirements")
    if no_scenarios:
        args.append("--no-scenarios")
    if requirement:
        args.extend(["--requirement", requirement])
    if json_output:
        args.append("--json")
    if store:
        args.extend(["--store", store])

    code = run_openspec(["show", *args])
    raise typer.Exit(code=code)


@app.command("status", help="Show project status (passthrough to openspec status)")
def status_cmd(
    change: Optional[str] = typer.Option(None, "--change", help="Specific change id"),
    schema: bool = typer.Option(False, "--schema", help="Show JSON schema"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
    store: Optional[str] = typer.Option(None, "--store", help="OpenSpec store id"),
) -> None:
    args: list[str] = []
    if change:
        args.extend(["--change", change])
    if schema:
        args.append("--schema")
    if json_output:
        args.append("--json")
    if store:
        args.extend(["--store", store])

    code = run_openspec(["status", *args])
    raise typer.Exit(code=code)


@app.command(
    "instructions",
    help="Show change instructions (passthrough to openspec instructions)",
)
def instructions_cmd(
    artifact: Optional[str] = typer.Argument(None, help="Artifact path or id"),
    change: Optional[str] = typer.Option(None, "--change", help="Specific change id"),
    schema: bool = typer.Option(False, "--schema", help="Show JSON schema"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
    store: Optional[str] = typer.Option(None, "--store", help="OpenSpec store id"),
) -> None:
    args: list[str] = []
    if artifact:
        args.append(artifact)
    if change:
        args.extend(["--change", change])
    if schema:
        args.append("--schema")
    if json_output:
        args.append("--json")
    if store:
        args.extend(["--store", store])

    code = run_openspec(["instructions", *args])
    raise typer.Exit(code=code)


@app.command("templates", help="List templates (passthrough to openspec templates)")
def templates_cmd(
    schema: Optional[str] = typer.Option(None, "--schema", help="Show JSON schema"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    args: list[str] = []
    if schema:
        args.extend(["--schema", schema])
    if json_output:
        args.append("--json")

    code = run_openspec(["templates", *args])
    raise typer.Exit(code=code)


@app.command("schemas", help="List JSON schemas (passthrough to openspec schemas)")
def schemas_cmd(
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    args: list[str] = []
    if json_output:
        args.append("--json")

    code = run_openspec(["schemas", *args])
    raise typer.Exit(code=code)


@app.command("schema", help="`openspec schema *` passthrough")
def schema_cmd(
    action: str = typer.Argument(..., help="which | list | validate | fork | init"),
    source: Optional[str] = typer.Argument(None, help="Source or target schema name"),
    name: Optional[str] = typer.Argument(None),
    all_schemas: bool = typer.Option(False, "--all"),
    description: Optional[str] = typer.Option(None, "--description"),
    artifacts: Optional[str] = typer.Option(None, "--artifacts"),
    set_default: bool = typer.Option(False, "--default"),
    force: bool = typer.Option(False, "--force"),
    json_output: bool = typer.Option(False, "--json"),
    store: Optional[str] = typer.Option(None, "--store"),
) -> None:
    if action == "init":
        target = name if name is not None else source
        if target is None:
            log_error("schema init requires <name>")
            raise typer.Exit(1)
        args = ["schema", "init", target]
    elif action == "fork":
        if source is None:
            log_error("schema fork requires <source>")
            raise typer.Exit(1)
        args = ["schema", "fork", source]
        if name:
            args.append(name)
    else:
        args = ["schema", action]
        target = source if name is None else name
        if target:
            args.append(target)

    if all_schemas and action == "which":
        args.append("--all")
    if description and action == "init":
        args.extend(["--description", description])
    if artifacts and action == "init":
        args.extend(["--artifacts", artifacts])
    if set_default and action == "init":
        args.append("--default")
    if force and action in ("fork", "init"):
        args.append("--force")
    if json_output:
        args.append("--json")
    if store:
        args.extend(["--store", store])

    raise typer.Exit(run_openspec(args))


@app.command(
    "init", help="Initialize OpenSpec in a project (passthrough to openspec init)"
)
def init_cmd(
    path: Optional[str] = typer.Argument(None, help="Project path"),
    tools: Optional[str] = typer.Option(
        None, "--tools", help="Comma-separated tools, 'all', or 'none'"
    ),
    force: bool = typer.Option(False, "--force", help="Auto-cleanup legacy files"),
    profile: Optional[str] = typer.Option(
        None, "--profile", help="Override global config profile (core|custom)"
    ),
) -> None:
    args: list[str] = []
    if path:
        args.append(path)
    if tools:
        args.extend(["--tools", tools])
    if force:
        args.append("--force")
    if profile:
        args.extend(["--profile", profile])

    code = run_openspec(["init", *args], timeout=60)
    raise typer.Exit(code=code)


@app.command(
    "update-core",
    help="Update OpenSpec instruction files (passthrough to openspec update)",
)
def update_core_cmd(
    path: Optional[str] = typer.Argument(None, help="Project path"),
    force: bool = typer.Option(False, "--force", help="Force update"),
) -> None:
    args: list[str] = []
    if path:
        args.append(path)
    if force:
        args.append("--force")

    code = run_openspec(["update", *args], timeout=60)
    raise typer.Exit(code=code)


@app.command(
    "feedback", help="Submit feedback about OpenSpec (passthrough to openspec feedback)"
)
def feedback_cmd(
    message: str = typer.Argument(..., help="Short feedback message"),
    body: Optional[str] = typer.Option(None, "--body", help="Detailed description"),
) -> None:
    args: list[str] = [message]
    if body:
        args.extend(["--body", body])

    code = run_openspec(["feedback", *args], timeout=60)
    raise typer.Exit(code=code)


@app.command("completion", help="Manage shell completions for the openspec CLI")
def completion_cmd(
    shell: Optional[str] = typer.Argument(None, help="Shell: bash|zsh|fish"),
    install: bool = typer.Option(False, "--install", help="Install completion"),
    uninstall: bool = typer.Option(False, "--uninstall", help="Uninstall completion"),
    verbose: bool = typer.Option(False, "--verbose", help="Verbose output"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
) -> None:
    args: list[str] = []
    if install:
        args.append("install")
    elif uninstall:
        args.append("uninstall")
    if shell:
        args.append(shell)
    if verbose:
        args.append("--verbose")
    if yes:
        args.append("--yes")

    code = run_openspec(["completion", *args])
    raise typer.Exit(code=code)


@app.command(
    "restore-core",
    help="Restore the openspec global config from the most recent .openspec-extended-baseline.json snapshot.",
)
def restore_core(
    path: Optional[Path] = typer.Option(
        None,
        "--from",
        help="Path to the baseline file. Defaults to ./.openspec-extended-baseline.json",
    ),
) -> None:
    """Restore the captured snapshot to ``~/.config/openspec/config.json``.

    Re-applies the snapshot's ``global_config`` block and writes it back.
    The baseline file is removed on success unless ``--keep-snapshot`` is passed.
    """
    baseline = path or (Path.cwd() / CORE_BASELINE_FILENAME)
    if not baseline.is_file():
        log_error(f"No baseline found at {baseline}")
        raise typer.Exit(code=1)

    try:
        snapshot = json.loads(baseline.read_text())
    except json.JSONDecodeError as e:
        log_error(f"Baseline is not valid JSON: {e}")
        raise typer.Exit(code=1)

    cfg = snapshot.get("global_config") or {}
    target = Path.home() / ".config" / "openspec" / "config.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        target.write_text(json.dumps(cfg, indent=2))
    except OSError as e:
        log_error(f"Failed to write {target}: {e}")
        raise typer.Exit(code=1)

    log_success(f"Restored {target} from {baseline}")
    try:
        baseline.unlink()
    except OSError:
        log_warn(f"Could not remove baseline {baseline}")


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    version: bool = typer.Option(False, "--version", "-V", help="Show version"),
) -> None:
    if version:
        console.print(f"{SCRIPT_NAME} {__version__}")
        raise SystemExit(0)
    if ctx.invoked_subcommand is None:
        console.print(f"Usage: {SCRIPT_NAME} [OPTIONS] COMMAND [ARGS]...")
        console.print("Try '--help' for more information.")
        raise SystemExit(1)


if __name__ == "__main__":
    app()
