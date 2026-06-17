#!/usr/bin/env python3
"""
OpenSpec-extended - Unified CLI for OpenSpec resources and autonomous workflow
"""

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
from source.orchestrator.engine import OrchestratorState, run_orchestrator

SCRIPT_VERSION = "1.0.1"
SCRIPT_NAME = "openspec-extended"

TOOL_DIRS = {"opencode": ".opencode", "claude": ".claude"}

console = Console()

app = typer.Typer(
    name=SCRIPT_NAME,
    help=f"{SCRIPT_NAME} - Installer and orchestrator for OpenSpec resources",
    add_completion=False,
)


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
    elif resource_type == "scripts":
        return target_dir / "scripts" / name
    elif resource_type == "lib":
        return target_dir / "scripts" / "lib" / name
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


def deploy_scripts(source_base: Path, target_dir: Path, name: str) -> None:
    target_scripts = target_dir / "scripts"
    target_scripts.mkdir(parents=True, exist_ok=True)
    source_name = "engine.py" if name == "osx-orchestrate" else name
    shutil.copy2(source_base / source_name, target_scripts / name)
    (target_scripts / name).chmod(0o755)


def deploy_lib(source_base: Path, target_dir: Path, name: str) -> None:
    target_lib = target_dir / "scripts" / "lib"
    target_lib.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_base / "osx.py", target_lib / name)
    (target_lib / name).chmod(0o755)


def get_source_type_dir(source_dir: Path, resource_type: str) -> Path:
    project_root = source_dir.parent.parent
    if resource_type == "scripts":
        return project_root / "source" / "orchestrator"
    elif resource_type == "lib":
        return project_root / "source" / "lib"
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
                "scripts": deploy_scripts,
                "lib": deploy_lib,
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
        elif resource_type == "scripts" and count == 1:
            type_label = "script"
        elif resource_type == "lib" and count == 1:
            type_label = "lib script"
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
    source_version = source_manifest.get("version", "unknown")

    target_dir = Path.cwd() / TOOL_DIRS[tool]
    target_manifest = target_dir / "manifest.toml"

    target_dir.mkdir(parents=True, exist_ok=True)

    total_count = 0
    total_skipped = 0

    for resource_type in ("skills", "commands", "agents", "scripts", "lib"):
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


def deploy_core(tool: str) -> None:
    target_dir = Path.cwd() / get_tool_dir(tool)
    target_manifest = target_dir / "manifest.toml"

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
        manifest_data["core"] = {"version": core_version, "installed": True}
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
            elif resource_type == "scripts":
                found = (target_dir / "scripts" / name).is_file()
            elif resource_type == "lib":
                found = (target_dir / "scripts" / "lib" / name).is_file()

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
) -> None:
    if tool not in TOOL_DIRS:
        log_error(f"Unknown tool: {tool}")
        console.print("  Available tools: opencode, claude")
        raise SystemExit(1)

    target_dir = Path.cwd() / TOOL_DIRS[tool]
    deploy_all_resources(tool, force=False)

    if (target_dir / "scripts" / "osx-orchestrate").is_file():
        update_gitignore()

    if with_core:
        deploy_core(tool)

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
) -> None:
    if tool not in TOOL_DIRS:
        log_error(f"Unknown tool: {tool}")
        console.print("  Available tools: opencode, claude")
        raise SystemExit(1)

    target_dir = Path.cwd() / TOOL_DIRS[tool]
    deploy_all_resources(tool, force=True)

    if (target_dir / "scripts" / "osx-orchestrate").is_file():
        update_gitignore()

    if with_core:
        deploy_core(tool)

    resources_dir = get_resources_dir()
    source_manifest = resources_dir / tool / "manifest.toml"
    if source_manifest.is_file():
        manifest_data = toml.loads(source_manifest.read_text())
        validate_deployment(target_dir, manifest_data)


@app.command("orchestrate", help="Run the 7-phase autonomous change workflow")
def orchestrate(
    ctx: typer.Context,
    change_name: Optional[str] = typer.Argument(None, help="OpenSpec change ID"),
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
    list_changes: bool = typer.Option(False, "--list", help="List available changes"),
) -> None:
    if not list_changes and not change_name:
        log_error("orchestrate: missing change ID (or pass --list)")
        raise typer.Exit(code=2)

    state = OrchestratorState()
    state.change_id = change_name or ""
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
    if log_file:
        state.log_file = Path(log_file)
        state.log_user_specified = True

    run_orchestrator(state)


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
