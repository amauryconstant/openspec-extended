#!/usr/bin/env python3
# ruff: noqa: EXE001 - shebang is intentional (module may also be invoked directly)
"""
OpenSpec-extended - Unified CLI for OpenSpec resources and autonomous workflow
"""

import json
import os
import re
import shutil
import subprocess
import sys
from datetime import UTC
from pathlib import Path

import toml
import typer
from rich.console import Console

from source import __version__
from source.lib.osx import AUTONOMOUS_RESOURCE_NAMES, REQUIRED_CORE_SKILLS
from source.orchestrator.engine import OrchestratorState, run_orchestrator
from source.osx_cli import osx_app

SCRIPT_NAME = "openspec-extended"

TOOL_DIRS = {"opencode": ".opencode", "claude": ".claude"}

# Per-platform token values for resource rendering. Source files under
# ``orchestrator/resources/opencode/`` (the orchestrator side; the
# skills side lives under ``skills/resources/opencode/`` per Phase 4) carry
# ``{{TOKEN}}`` placeholders; the deploy step substitutes them with the
# values for the active ``tool``. The OpenCode source ships the same tokens
# literally — the Python side is the single source of truth for
# substitution. The bash ``sync-mirrors`` script is a pure mirror (no
# token substitution). New tokens MUST be added to both platforms; the
# substitution is silent for unknown tokens so future additions don't crash.
PLATFORM_TOKENS: dict[str, dict[str, str]] = {
    "opencode": {
        "ASK_TOOL": "AskUserQuestion",
        "DOCS_FILE": "AGENTS.md",
        "CMD_PREFIX": "osx-",
        "TOOL_NAME": "OpenCode",
        "PLATFORM_DIR": ".opencode",
    },
    "claude": {
        "ASK_TOOL": "Ask",
        "DOCS_FILE": "CLAUDE.md",
        "CMD_PREFIX": "osx:",
        "TOOL_NAME": "Claude Code",
        "PLATFORM_DIR": ".claude",
    },
}

_LEFTOVER_TOKEN_RE = re.compile(r"\{\{([A-Z_]+)\}\}")


def _substitute_tokens(text: str, tool: str) -> str:
    """Replace every ``{{TOKEN}}`` in ``text`` with the value for ``tool``.

    Unknown tokens (or unknown tools) are left verbatim — that way a future
    token added to the source but not yet to ``PLATFORM_TOKENS`` surfaces as a
    literal in the deployed file rather than silently disappearing. The
    substituter is the single source of truth for token values; the bash
    ``sync-mirrors`` script no longer substitutes tokens.
    """
    mapping = PLATFORM_TOKENS.get(tool, {})

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in mapping:
            return mapping[key]
        return match.group(0)

    return _LEFTOVER_TOKEN_RE.sub(repl, text)


console = Console()

app = typer.Typer(
    name=SCRIPT_NAME,
    help=f"{SCRIPT_NAME} - Installer and orchestrator for OpenSpec resources",
    add_completion=False,
)
app.add_typer(osx_app, name="osx")


def get_resources_dir() -> Path:
    """Return the orchestrator-side resources directory.

    Phase 4 split the single ``resources/`` root into two parallel trees
    — ``orchestrator/resources/`` (this function) and
    ``skills/resources/`` (see :func:`get_skills_resources_dir`). The
    frozen binary ships both trees; in the source tree, this resolver
    points at the orchestrator side (the side that owns the workflow
    resources, phase commands, and agents).

    In the source tree, ``source/`` lives at ``orchestrator/source/``,
    so ``Path(__file__).parent.parent`` resolves to ``orchestrator/``
    and adding ``"resources"`` lands at ``orchestrator/resources/``.

    In the frozen bundle, PyInstaller's ``openspec.spec`` collects each
    side's files under the legacy ``resources/`` prefix for the
    orchestrator side and under ``skills/resources/`` for the skills
    side. The deploy function consults both trees once Phase 5 splits
    the manifests.
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", "")) / "resources"
    return Path(__file__).parent.parent / "resources"


def get_skills_resources_dir() -> Path:
    """Return the skills-side resources directory.

    Companion to :func:`get_resources_dir`. In the source tree this
    resolves to ``skills/resources/`` (a sibling of ``orchestrator/``).
    In the frozen bundle the matching files are placed under
    ``MEIPASS/skills/resources/`` by the PyInstaller spec.
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", "")) / "skills" / "resources"
    return Path(__file__).parent.parent.parent / "skills" / "resources"


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


def _resolve_language(arg: str | None) -> str | None:
    """Resolve --language value with env-var fallback.

    Precedence: explicit flag > OPENSPEC_LANGUAGE env > unset.
    Empty string treated as unset.
    """
    if arg:
        return arg
    return os.environ.get("OPENSPEC_LANGUAGE") or None


def run_openspec(
    args: list[str], timeout: int = 30, extra_env: dict[str, str] | None = None
) -> int:
    """Run `openspec <args>` and forward stdout/stderr. Returns exit code.

    Raises SystemExit(1) if openspec is not installed or times out.
    When ``extra_env`` is provided, the named variables are merged into the
    subprocess environment (overriding the parent values when keys collide).
    """
    cmd = ["openspec", *args]
    env = None
    if extra_env:
        import os

        env = os.environ.copy()
        env.update(extra_env)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
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


def deploy_skills(
    source_base: Path,
    target_dir: Path,
    name: str,
    shared_refs: list[str] | None = None,
    tool: str = "opencode",
) -> None:
    target_skills = target_dir / "skills"
    target_skills.mkdir(parents=True, exist_ok=True)
    target_path = target_skills / name
    if target_path.exists():
        shutil.rmtree(target_path)
    shutil.copytree(source_base / name, target_path)
    _substitute_tokens_in_tree(target_path, tool)

    if shared_refs:
        target_refs = target_path / "references"
        target_refs.mkdir(parents=True, exist_ok=True)
        # Phase 4 split: the shared references pool lives on the
        # orchestrator side (`orchestrator/resources/<tool>/skills/references/`)
        # even when the consuming skill lives on the skills side.
        # Resolve via the resource path's parent to find the orchestrator
        # pool, regardless of which side the skill itself lives on.
        orchestrator_resources = get_resources_dir()
        shared_refs_dir = orchestrator_resources / tool / "skills" / "references"
        for ref_name in shared_refs:
            src = shared_refs_dir / ref_name
            dst = target_refs / ref_name
            if src.is_file():
                shutil.copy2(src, dst)
                _substitute_tokens_in_file(dst, tool)
            else:
                log_warn(f"Shared reference not found: {src}")


def _substitute_tokens_in_file(path: Path, tool: str) -> None:
    """Rewrite ``path`` in place with ``{{TOKEN}}`` values for ``tool``.

    Non-``.md`` files are skipped silently — only text files carry tokens.
    """
    if path.suffix != ".md":
        return
    path.write_text(_substitute_tokens(path.read_text(), tool))


def _substitute_tokens_in_tree(root: Path, tool: str) -> None:
    """Walk ``root`` and substitute tokens in every ``.md`` file (in place)."""
    for md_file in root.rglob("*.md"):
        _substitute_tokens_in_file(md_file, tool)


def _build_claude_skill_from_command(source_path: Path, name: str) -> str:
    """Read an opencode command file and render it as a Claude SKILL.md body.

    Strips opencode-only ``agent:`` frontmatter (Claude has no equivalent
    dispatch model), injects ``name: <name>`` so the skill carries a slash
    command identifier, and preserves everything else verbatim. Returns the
    rendered string; callers write it to disk.
    """
    raw = source_path.read_text()
    in_fm = False
    seen_close = False
    out_lines: list[str] = []
    for line in raw.splitlines(keepends=True):
        stripped = line.strip()
        if stripped == "---":
            if not in_fm:
                in_fm = True
                out_lines.append(line)
                continue
            if not seen_close:
                out_lines.append(f"name: {name}\n")
                seen_close = True
                in_fm = False
            out_lines.append(line)
            continue
        if in_fm and line.lstrip().startswith("agent:"):
            continue
        out_lines.append(line)
    if not seen_close:
        # File had no closing frontmatter fence; still inject name on a fresh header.
        return f"---\nname: {name}\n---\n{raw}"
    return "".join(out_lines)


def _referenced_skill_refs(body: str) -> list[str]:
    """Extract ``references/<file>.md`` paths referenced in a command body.

    Phase commands point at the shared ``skills/references/`` pool via prose
    like ``See ``references/phase-protocol-common.md#mandatory-start`.`` The
    Claude skill mirror needs to copy those reference files into its own
    ``references/`` subdir so the skill is self-sufficient at deploy time.
    """
    seen: set[str] = set()
    for match in re.finditer(r"`?references/([A-Za-z0-9_\-]+\.md)", body):
        seen.add(match.group(1))
    return sorted(seen)


def deploy_commands(
    source_base: Path, target_dir: Path, name: str, tool: str = "opencode"
) -> None:
    target_commands = target_dir / "commands"
    target_commands.mkdir(parents=True, exist_ok=True)
    source_path = source_base / f"{name}.md"
    if source_path.exists():
        target_cmd_path = target_commands / f"{name}.md"
        shutil.copy2(source_path, target_cmd_path)
        _substitute_tokens_in_file(target_cmd_path, tool)
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
                    target_cmd_path = target_commands / subdir_name / f"{base_name}.md"
                    shutil.copy2(alt_source, target_cmd_path)
                    _substitute_tokens_in_file(target_cmd_path, tool)
                    source_path = alt_source
                    break
        else:
            raise FileNotFoundError(f"Command not found: {name}")

    if tool != "claude":
        # OpenCode: single-emit command file only (its native shape).
        return

    # Claude: dual-emit. Also write the command as a skill at
    # ``<target>/skills/<name>/SKILL.md`` so the slash command resolves
    # against the modern skills surface as well — mirrors upstream
    # OpenSpec's dual-emit strategy (introduced in v1.7.0, current as
    # of v1.11.0). The legacy .claude/commands/ file written above
    # remains in place for back-compat.
    skill_dir = target_dir / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(_build_claude_skill_from_command(source_path, name))
    _substitute_tokens_in_file(skill_md, tool)

    # Copy any references/ files referenced from the body so the skill
    # is self-sufficient at deploy time. Source refs live once under
    # the source skills/references/ pool.
    body = skill_md.read_text()
    ref_names = _referenced_skill_refs(body)
    if ref_names:
        source_refs_dir = source_base.parent / "skills" / "references"
        target_refs_dir = skill_dir / "references"
        target_refs_dir.mkdir(parents=True, exist_ok=True)
        for ref_name in ref_names:
            src = source_refs_dir / ref_name
            if src.is_file():
                dst = target_refs_dir / ref_name
                shutil.copy2(src, dst)
                _substitute_tokens_in_file(dst, tool)


def deploy_agents(
    source_base: Path, target_dir: Path, name: str, tool: str = "opencode"
) -> None:
    target_agents = target_dir / "agents"
    target_agents.mkdir(parents=True, exist_ok=True)
    target_agent_path = target_agents / f"{name}.md"
    shutil.copy2(source_base / f"{name}.md", target_agent_path)
    _substitute_tokens_in_file(target_agent_path, tool)


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
    with_autonomous: bool,
) -> tuple[int, int]:
    source_type_dir = get_source_type_dir(source_dir, resource_type)
    if not source_type_dir.is_dir():
        return (0, 0)

    resources = source_manifest.get("resources", {}).get(resource_type, {})
    if not resources:
        return (0, 0)

    count = 0
    skipped = 0
    gated = 0

    for name, info in resources.items():
        source_version = info.get("version", "")
        if not source_version:
            continue

        if name in AUTONOMOUS_RESOURCE_NAMES and not with_autonomous:
            gated += 1
            continue

        # Phase 4 split: the unified manifest declares resources from
        # both sides, but on disk each resource lives on exactly one
        # side. Skip names whose source path is missing on the current
        # side — the other side's deploy loop will pick them up.
        # Skills are directories; commands and agents are files. Claude
        # commands may also live under a nested ``osx/`` subdir.
        if resource_type == "skills":
            source_path = source_type_dir / name
        else:
            source_path = source_type_dir / f"{name}.md"
        if source_path.exists():
            pass
        elif (source_type_dir / "osx" / f"{name.replace('osx-', '', 1)}.md").exists():
            # Claude: source lives at <tree>/osx/<base>.md
            pass
        else:
            continue

        target_path = get_target_path(resource_type, target_dir, name)
        decision = should_deploy(
            name, source_version, target_path, target_manifest, resource_type, force
        )

        if decision in ("install", "upgrade", "update"):
            if resource_type == "skills":
                deploy_skills(
                    source_type_dir,
                    target_dir,
                    name,
                    shared_refs=info.get("references", []),
                    tool=tool,
                )
                count += 1
            elif resource_type == "commands":
                deploy_commands(source_type_dir, target_dir, name, tool=tool)
                count += 1
            elif resource_type == "agents":
                deploy_agents(source_type_dir, target_dir, name, tool=tool)
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

    if gated > 0:
        console.print(
            f"  Skipped {gated} autonomous {resource_type} (use --with-autonomous)"
        )

    return (count, skipped)


def deploy_all_resources(tool: str, force: bool, with_autonomous: bool) -> None:
    """Deploy every resource across the orchestrator and skills trees.

    Phase 4 split the resources into two parallel trees; this function
    iterates over both and merges the manifest on disk. Phase 5 will
    split the manifests on disk into two files (one per side); the
    iteration logic stays the same.
    """
    orchestrator_resources_dir = get_resources_dir()
    orchestrator_source_dir = orchestrator_resources_dir / tool
    orchestrator_manifest_path = orchestrator_source_dir / "manifest.toml"

    if not orchestrator_manifest_path.is_file():
        log_error(f"Manifest not found: {orchestrator_manifest_path}")
        raise SystemExit(1)

    orchestrator_manifest = toml.loads(orchestrator_manifest_path.read_text())
    source_version = __version__

    skills_resources_dir = get_skills_resources_dir()
    skills_source_dir = skills_resources_dir / tool
    skills_manifest_path = skills_source_dir / "manifest.toml"
    skills_manifest: dict = {}
    if skills_manifest_path.is_file():
        skills_manifest = toml.loads(skills_manifest_path.read_text())

    target_dir = Path.cwd() / TOOL_DIRS[tool]
    target_manifest = target_dir / "manifest.toml"

    target_dir.mkdir(parents=True, exist_ok=True)

    total_count = 0
    total_skipped = 0

    for source_dir, source_manifest in (
        (orchestrator_source_dir, orchestrator_manifest),
        (skills_source_dir, skills_manifest),
    ):
        if not source_manifest:
            continue
        for resource_type in ("skills", "commands", "agents"):
            cnt, skp = deploy_type(
                resource_type,
                source_dir,
                target_dir,
                target_manifest,
                source_manifest,
                force,
                tool,
                with_autonomous,
            )
            total_count += cnt
            total_skipped += skp

    # Merge both manifests into the target manifest. Phase 5 will split
    # the on-disk manifests so this merge becomes a no-op (each side
    # writes its own target-side manifest entry).
    merged_manifest = {
        "resources": {},
        "version": source_version,
    }
    for src in (orchestrator_manifest, skills_manifest):
        for kind, entries in src.get("resources", {}).items():
            if not isinstance(entries, dict):
                continue
            merged_manifest["resources"].setdefault(kind, {}).update(entries)
    if not with_autonomous:
        filtered: dict = {}
        for resource_type, entries in merged_manifest["resources"].items():
            if not isinstance(entries, dict):
                continue
            filtered[resource_type] = {
                name: info
                for name, info in entries.items()
                if name not in AUTONOMOUS_RESOURCE_NAMES
            }
        merged_manifest["resources"] = filtered
    target_manifest.write_text(toml.dumps(merged_manifest))
    log_success(f"Manifest updated to v{source_version}")
    console.print(f"  Target: {target_dir}/manifest.toml")

    if total_count == 0 and total_skipped == 0:
        console.print("No resources to deploy")
    elif total_count == 0 and total_skipped > 0:
        console.print(f"All {total_skipped} resources are current")


def purge_managed_resources(
    target_dir: Path,
    tool: str,
    keep_names: set[str],
    prefixes: tuple[str, ...],
) -> int:
    """Remove stale ``osx-*``/``osc-*`` resources from a deployed tool tree.

    Scans only the direct managed destinations (skills, commands, agents) and
    removes entries whose name starts with one of ``prefixes`` and is **not**
    in ``keep_names``. Returns the number of entries removed.

    Scope is intentionally narrow:

    - **Skills**: ``<target>/skills/<dir>`` whose directory name starts with a
      managed prefix. The directory and its entire contents are removed.
    - **Agents**: ``<target>/agents/<name>.md`` whose stem starts with a
      managed prefix. Only files (or symlinks) are removed; subdirectories
      are left untouched.
    - **Commands**: layout-aware.
        - OpenCode: ``<target>/commands/<name>.md`` flat files, plus any
          leftover ``openspec-*.md`` files from pre-rename layouts.
        - Claude: ``<target>/commands/osx/<name>.md`` and
          ``<target>/commands/osc/<name>.md`` nested layouts. Any orphan
          flat ``osx-*.md``/``osc-*.md`` files at the top of ``commands/``
          are also removed for legacy compatibility.

    Symlinks are unlinked (never followed) so that a symlinked tree cannot
    cause unintended removal outside the managed namespace. Directories whose
    entry was not removed but is now empty are left in place.
    """
    if tool not in TOOL_DIRS:
        raise ValueError(f"Unknown tool: {tool}")

    removed = 0
    if not target_dir.is_dir():
        return 0

    def starts_with_managed(name: str) -> str | None:
        for prefix in prefixes:
            if name.startswith(prefix):
                return prefix
        return None

    def should_keep(name: str) -> bool:
        return name in keep_names

    def safe_remove(path: Path) -> bool:
        try:
            if path.is_symlink() or path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
            else:
                return False
            return True
        except OSError:
            log_warn(f"Could not remove {path}")
            return False

    # Skills: directories under <target>/skills/ matching a managed prefix.
    skills_dir = target_dir / "skills"
    if skills_dir.is_dir():
        for entry in skills_dir.iterdir():
            if starts_with_managed(entry.name) is None:
                continue
            if should_keep(entry.name):
                continue
            if safe_remove(entry):
                removed += 1

    # Agents: files under <target>/agents/ whose stem matches a managed prefix.
    agents_dir = target_dir / "agents"
    if agents_dir.is_dir():
        for entry in agents_dir.iterdir():
            if not (entry.is_file() or entry.is_symlink()):
                continue
            stem = entry.stem
            if starts_with_managed(stem) is None:
                continue
            if should_keep(stem):
                continue
            if safe_remove(entry):
                removed += 1

    # Commands: layout-aware cleanup.
    commands_dir = target_dir / "commands"
    if commands_dir.is_dir():
        if tool == "opencode":
            # Flat layout: commands/<name>.md
            for entry in commands_dir.iterdir():
                if not (entry.is_file() or entry.is_symlink()):
                    continue
                stem = entry.stem
                # Catch osx-*, osc-*, and legacy openspec-* flat files
                # from pre-rename OpenSpec layouts.
                if starts_with_managed(stem) is None and not stem.startswith(
                    "openspec-"
                ):
                    continue
                if should_keep(stem):
                    continue
                if safe_remove(entry):
                    removed += 1
        else:
            # Claude: nested under commands/osx/ and commands/osc/. The
            # disk filenames strip the osx-/osc- prefix, so we reapply it
            # when matching against keep_names.
            for subdir_name, implicit_prefix in (("osx", "osx-"), ("osc", "osc-")):
                subdir = commands_dir / subdir_name
                if not subdir.is_dir():
                    continue
                if not any(prefix.startswith(implicit_prefix) for prefix in prefixes):
                    continue
                for entry in subdir.iterdir():
                    if not (entry.is_file() or entry.is_symlink()):
                        continue
                    stem = entry.stem
                    # Filenames on disk are like "phase0.md" but the manifest
                    # names them "osx-phase0". Always treat anything in this
                    # subdir as belonging to the implicit prefix.
                    canonical = f"{implicit_prefix}{stem}"
                    if should_keep(stem) or should_keep(canonical):
                        continue
                    if safe_remove(entry):
                        removed += 1

            # Any legacy flat osx-*.md / osc-*.md / openspec-*.md files at
            # the top of commands/ are also removed for safety.
            for entry in commands_dir.iterdir():
                if not (entry.is_file() or entry.is_symlink()):
                    continue
                stem = entry.stem
                if starts_with_managed(stem) is None and not stem.startswith(
                    "openspec-"
                ):
                    continue
                if should_keep(stem):
                    continue
                if safe_remove(entry):
                    removed += 1

    return removed


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
        "!openspec/changes/archive/**/state.json",
        "openspec/changes/*/complete.json",
        "!openspec/changes/archive/**/complete.json",
        "openspec/changes/*/iterations.json",
        "!openspec/changes/archive/**/iterations.json",
        "openspec/changes/*/decision-log.json",
        "!openspec/changes/archive/**/decision-log.json",
        "openspec/changes/*/verification-report.md",
        "!openspec/changes/archive/**/verification-report.md",
        "openspec/changes/*/reflections.md",
        "!openspec/changes/archive/**/reflections.md",
        "openspec/changes/*/test-compliance-report.md",
        "!openspec/changes/archive/**/test-compliance-report.md",
        "openspec/changes/*/suggestions.md",
        "!openspec/changes/archive/**/suggestions.md",
        ".osx-orchestrate-*.log",
        "!openspec/changes/archive/**/.osx-orchestrate-*.log",
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
        # `openspec list --json` returns a top-level `items` array; `skills`,
        # `specs`, and `changes` are nested under each item. Iterating over
        # the latter at the top level yields dead branches.
        if payload.get("items"):
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


# Canonical 12-workflow custom profile written to ~/.config/openspec/config.json
# before `openspec init` is invoked. Mirrors the profile written by
# .mise/tasks/sync-core (write_custom_profile) so install/update --with-core
# produces the same artifact set regardless of the user's prior global config.
CANONICAL_CORE_WORKFLOWS = [
    "propose",
    "explore",
    "new",
    "continue",
    "apply",
    "update",
    "ff",
    "sync",
    "archive",
    "bulk-archive",
    "verify",
    "onboard",
]


def _write_canonical_core_config() -> Path:
    """Seed ``~/.config/openspec/config.json`` with the canonical 12-workflow
    custom profile. Returns the path written.
    """
    config_dir = Path.home() / ".config" / "openspec"
    config_dir.mkdir(parents=True, exist_ok=True)
    target = config_dir / "config.json"
    canonical = {
        "profile": "custom",
        "delivery": "both",
        "workflows": CANONICAL_CORE_WORKFLOWS,
    }
    target.write_text(json.dumps(canonical, indent=2) + "\n")
    return target


def _write_core_baseline(tool: str, project_root: Path | None = None) -> Path | None:
    """Write ``.openspec-extended-baseline.json`` capturing the user's prior
    openspec core setup. Returns the path written, or None if nothing to save.
    """
    project_root = project_root or Path.cwd()
    from datetime import datetime

    snapshot = {
        "captured_at": datetime.now(UTC).isoformat(),
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


def _ensure_baseline_for_global_config(project_root: Path) -> Path | None:
    """Snapshot the global openspec config when it exists but no prior core
    deployment is detectable. Returns the path written, or None if the prior
    global config was empty/missing (nothing meaningful to restore).
    """
    from datetime import datetime

    prior = _capture_global_config()
    if not prior:
        return None
    snapshot = {
        "captured_at": datetime.now(UTC).isoformat(),
        "tool": "(global-config)",
        "global_config": prior,
        "project_root": str(project_root),
    }
    path = project_root / CORE_BASELINE_FILENAME
    try:
        path.write_text(json.dumps(snapshot, indent=2))
        return path
    except OSError:
        return None


def deploy_core(
    tool: str,
    force: bool = False,
    language: str | None = None,
    strict_archived: bool = False,
) -> None:
    target_dir = Path.cwd() / get_tool_dir(tool)
    target_manifest = target_dir / "manifest.toml"
    project_root = Path.cwd()

    # Non-destructive: refuse to overwrite an existing deployment without --force.
    if _detect_existing_core_deployment(tool) and not force:
        log_error(
            "An existing core deployment was detected. Re-run with --force to"
            " overwrite (a snapshot will be saved to .openspec-extended-baseline.json)."
        )
        console.print("  Hint: openspec-extended install <tool> --with-core --force")
        console.print("  Restore later with: openspec-extended restore-core")
        raise SystemExit(2)

    # Snapshot whatever we are about to overwrite. Two cases:
    #   1. A prior core deployment exists AND --force: capture the prior
    #      deployment via _write_core_baseline (records tool + global_config).
    #   2. No prior deployment, but ~/.config/openspec/config.json already
    #      exists (e.g. user ran plain `openspec init` previously): capture
    #      that global config so restore-core can put it back.
    baseline_path: Path | None = None
    if force and _detect_existing_core_deployment(tool):
        baseline_path = _write_core_baseline(tool)
    else:
        baseline_path = _ensure_baseline_for_global_config(project_root)

    # Seed the canonical 12-workflow custom profile so `openspec init` installs
    # the full set regardless of the user's prior global config. Mirrors
    # .mise/tasks/sync-core (write_custom_profile + generate_ai_files).
    config_path = _write_canonical_core_config()
    if baseline_path:
        log_info(f"Saved pre-overwrite baseline to {baseline_path.name}")
    log_info(f"Wrote canonical 12-workflow profile to {config_path}")

    try:
        init_args = [
            "openspec",
            "init",
            "--tools",
            tool,
            "--profile",
            "custom",
            "--force",
        ]
        if language:
            init_args.extend(["--language", language])
        subprocess.run(
            init_args,
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
    _post_install_archived_sweep(strict=strict_archived)

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

    # Claude doesn't ship the agents/ directory — skip agent validation.
    # The merged manifest still lists agents (for OpenCode parity); the
    # deploy loop above skips them per the source-existence check.
    target_tool = None
    for tool_name, tool_dir in TOOL_DIRS.items():
        if str(target_dir).endswith(tool_dir):
            target_tool = tool_name
            break
    skip_agents = target_tool == "claude"

    for resource_type, resources in manifest.get("resources", {}).items():
        if skip_agents and resource_type == "agents":
            continue
        for name in resources:
            found = False
            if resource_type == "skills":
                found = (target_dir / "skills" / name).is_dir()
            elif resource_type == "agents":
                found = (target_dir / "agents" / f"{name}.md").is_file()
            elif resource_type == "commands":
                commands_dir = target_dir / "commands"
                if not commands_dir.is_dir():
                    # No commands directory at all — nothing to validate
                    pass
                else:
                    cmd_path = commands_dir / f"{name}.md"
                    if cmd_path.is_file():
                        found = True
                    else:
                        base_name = (
                            name.replace("osx-", "", 1)
                            if name.startswith("osx-")
                            else name
                        )
                        for subdir in commands_dir.iterdir():
                            if (
                                subdir.is_dir()
                                and (subdir / f"{base_name}.md").is_file()
                            ):
                                found = True
                                break
                    # Modern Claude form: slash command emitted as a skill
                    # (dual-emit mirrors upstream OpenSpec — introduced in
                    # v1.7.0, current as of v1.11.0).
                    if not found:
                        skill_path = target_dir / "skills" / name / "SKILL.md"
                        if skill_path.is_file():
                            found = True

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
    with_autonomous: bool = typer.Option(
        False,
        "--with-autonomous/--no-with-autonomous",
        help=(
            "Also deploy the 7-phase autonomous workflow resources "
            "(phase commands, agents, workflow skill). Defaults to off; "
            "pass --with-autonomous to enable the orchestrator."
        ),
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
    language: str | None = typer.Option(
        None,
        "--language",
        help="Language used for artifacts in new projects (v1.10.0+). Precedence: --language > OPENSPEC_LANGUAGE > unset.",
    ),
    strict_archived: bool = typer.Option(
        False,
        "--strict-archived",
        help="Fail on warnings from the post-install `openspec validate --archived` sweep.",
    ),
) -> None:
    if tool not in TOOL_DIRS:
        log_error(f"Unknown tool: {tool}")
        console.print("  Available tools: opencode, claude")
        raise SystemExit(1)

    target_dir = Path.cwd() / TOOL_DIRS[tool]
    deploy_all_resources(tool, force=False, with_autonomous=with_autonomous)

    if with_autonomous:
        update_gitignore()

    if with_core:
        effective_language = _resolve_language(language)
        deploy_core(
            tool,
            force=force,
            language=effective_language,
            strict_archived=strict_archived,
        )

    target_manifest_path = target_dir / "manifest.toml"
    if target_manifest_path.is_file():
        manifest_data = toml.loads(target_manifest_path.read_text())
        validate_deployment(target_dir, manifest_data)


def _expected_extension_names(tool: str, with_autonomous: bool) -> set[str]:
    """Return the set of extended ``osx-*`` resource names that the current
    source manifest will deploy for ``tool``.

    The set mirrors ``deploy_all_resources`` filtering: autonomous names are
    included only when ``with_autonomous`` is set.
    """
    resources_dir = get_resources_dir() / tool
    manifest_path = resources_dir / "manifest.toml"
    if not manifest_path.is_file():
        return set()
    data = toml.loads(manifest_path.read_text())
    expected: set[str] = set()
    for entries in data.get("resources", {}).values():
        if not isinstance(entries, dict):
            continue
        for name in entries:
            if not with_autonomous and name in AUTONOMOUS_RESOURCE_NAMES:
                continue
            expected.add(name)
    return expected


def _post_install_archived_sweep(strict: bool = False, timeout: int = 30) -> bool:
    """Run ``openspec validate --archived --json`` after install/update.

    Non-fatal by default: on failure, log a yellow warning and return False.
    With ``strict=True`` (or ``OPENSPEC_VALIDATE_ARCHIVED_STRICT=1``), exit non-zero.

    Returns True on success or when openspec is missing (skipped).
    """
    if os.environ.get("OPENSPEC_VALIDATE_ARCHIVED_STRICT") == "1":
        strict = True
    try:
        result = subprocess.run(
            ["openspec", "validate", "--archived", "--json"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError:
        log_info("openspec not installed; skipping post-install archived sweep")
        return True
    except subprocess.TimeoutExpired:
        log_warn("openspec validate --archived timed out; skipping")
        return True
    if result.returncode == 0:
        log_success("Post-install sweep: archives valid")
        return True
    log_warn("Post-install sweep found unfinished archive state")
    stderr = (result.stderr or "").strip()
    stdout = (result.stdout or "").strip()[:500]
    if stderr:
        log_warn(f"stderr: {stderr}")
    if stdout:
        log_warn(f"stdout (truncated): {stdout}")
    log_warn(
        "Remediation: run `openspec validate --archived --strict` to see issues, "
        "then tick remaining tasks.md checkboxes or use `--no-validate` when archiving."
    )
    if strict:
        log_error(
            "Strict mode: exiting non-zero (set OPENSPEC_VALIDATE_ARCHIVED_STRICT=0 to disable)"
        )
        raise SystemExit(result.returncode or 1)
    return False


def _core_keep_set(target_dir: Path) -> set[str]:
    """Build the keep-set for the ``osc-*`` cleanup pass from the resources
    currently present on disk in the deployed core tree.

    Layout-aware:

    - Skills: ``<target>/skills/<dir>`` whose name starts with ``osc-``.
    - Commands (Claude): ``<target>/commands/osc/<id>.md`` → ``osc-<id>``.
    - Commands (OpenCode): ``<target>/commands/osc-<id>.md`` flat files.
    """
    keep: set[str] = set()

    skills_dir = target_dir / "skills"
    if skills_dir.is_dir():
        for entry in skills_dir.iterdir():
            if entry.is_dir() and entry.name.startswith("osc-"):
                keep.add(entry.name)

    commands_dir = target_dir / "commands"
    if commands_dir.is_dir():
        # Claude layout: commands/osc/<id>.md
        osc_dir = commands_dir / "osc"
        if osc_dir.is_dir():
            for entry in osc_dir.iterdir():
                if entry.is_file() and entry.suffix == ".md":
                    keep.add(f"osc-{entry.stem}")
        # OpenCode layout: commands/osc-<id>.md (flat)
        for entry in commands_dir.iterdir():
            if (
                (entry.is_file() or entry.is_symlink())
                and entry.suffix == ".md"
                and entry.stem.startswith("osc-")
            ):
                keep.add(entry.stem)

    return keep


@app.command(
    "update",
    help="Force reinstall all resources (same as install but always overwrites)",
)
def update(
    tool: str = typer.Argument(..., help="Target tool: opencode or claude"),
    with_core: bool = typer.Option(
        False, "--with-core", help="Also deploy core OpenSpec skills"
    ),
    with_autonomous: bool = typer.Option(
        False,
        "--with-autonomous/--no-with-autonomous",
        help=(
            "Refresh the 7-phase autonomous workflow resources. "
            "Defaults to off; pass --with-autonomous to refresh them."
        ),
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
    language: str | None = typer.Option(
        None,
        "--language",
        help="Language used for artifacts in new projects (v1.10.0+). Precedence: --language > OPENSPEC_LANGUAGE > unset.",
    ),
    strict_archived: bool = typer.Option(
        False,
        "--strict-archived",
        help="Fail on warnings from the post-update `openspec validate --archived` sweep.",
    ),
) -> None:
    if tool not in TOOL_DIRS:
        log_error(f"Unknown tool: {tool}")
        console.print("  Available tools: opencode, claude")
        raise SystemExit(1)

    target_dir = Path.cwd() / TOOL_DIRS[tool]
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Purge stale extended ``osx-*`` resources before the forced redeploy
    #    so the resulting tree exactly matches the current source manifest.
    osx_keep = _expected_extension_names(tool, with_autonomous)
    removed = purge_managed_resources(
        target_dir, tool, keep_names=osx_keep, prefixes=("osx-",)
    )
    if removed:
        log_info(f"Purged {removed} stale osx-* resource(s)")

    deploy_all_resources(tool, force=True, with_autonomous=with_autonomous)

    if with_autonomous:
        update_gitignore()

    if with_core:
        effective_language = _resolve_language(language)
        deploy_core(
            tool,
            force=force,
            language=effective_language,
            strict_archived=strict_archived,
        )

        # 2. After core deployment succeeds, reconcile ``osc-*`` resources
        #    against what was just generated. Anything previously deployed
        #    that is no longer generated upstream is removed here.
        core_keep = _core_keep_set(target_dir)
        removed = purge_managed_resources(
            target_dir,
            tool,
            keep_names=core_keep,
            prefixes=("osc-",),
        )
        if removed:
            log_info(f"Purged {removed} stale osc-* resource(s)")

    target_manifest_path = target_dir / "manifest.toml"
    if target_manifest_path.is_file():
        manifest_data = toml.loads(target_manifest_path.read_text())
        validate_deployment(target_dir, manifest_data)


@app.command("orchestrate", help="Run the 7-phase autonomous change workflow")
def orchestrate(
    ctx: typer.Context,
    change_name: str | None = typer.Argument(
        None, help="OpenSpec change ID or 'store:change'"
    ),
    store: str | None = typer.Option(
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
    schema: str | None = typer.Option(
        None, "--schema", help="Override schema resolution"
    ),
    list_changes: bool = typer.Option(False, "--list", help="List available changes"),
) -> None:
    if not list_changes and not change_name:
        log_error("orchestrate: missing change ID (or pass --list)")
        raise typer.Exit(code=2)

    os.environ["OSX_AUTONOMOUS"] = "1"

    parsed_store: str | None = None
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
    "view",
    help="Display an interactive dashboard (passthrough to openspec view; v1.8.0+). Requires a TTY.",
)
def view_cmd(
    store: str | None = typer.Option(None, "--store", help="OpenSpec store id"),
    json_output: bool = typer.Option(
        False, "--json", help="JSON output (when supported)"
    ),
) -> None:
    args: list[str] = []
    if store:
        args.extend(["--store", store])
    if json_output:
        args.append("--json")

    code = run_openspec(["view", *args])
    raise typer.Exit(code=code)


@app.command(
    "archive", help="Archive a completed change (passthrough to openspec archive)"
)
def archive_cmd(
    change_name: str | None = typer.Argument(
        None, help="Change id (omit for interactive picker)"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompts"),
    skip_specs: bool = typer.Option(
        False,
        "--skip-specs",
        help="Skip spec update operations (useful for infrastructure, tooling, or doc-only changes)",
    ),
    no_validate: bool = typer.Option(
        False,
        "--no-validate",
        help="Skip validation (not recommended, requires confirmation upstream)",
    ),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
    no_interactive: bool = typer.Option(
        False, "--no-interactive", help="Disable interactive prompts"
    ),
    store: str | None = typer.Option(None, "--store", help="OpenSpec store id"),
) -> None:
    args: list[str] = []
    if change_name:
        args.append(change_name)
    if yes:
        args.append("--yes")
    if skip_specs:
        args.append("--skip-specs")
    if no_validate:
        args.append("--no-validate")
    if json_output:
        args.append("--json")
    if no_interactive:
        args.append("--no-interactive")
    if store:
        args.extend(["--store", store])

    code = run_openspec(["archive", *args])
    raise typer.Exit(code=code)


@app.command(
    "context",
    help="Print the working context for the resolved OpenSpec root (passthrough to openspec context; v1.5.0+)",
)
def context_cmd(
    store: str | None = typer.Option(None, "--store", help="OpenSpec store id"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
    code_workspace: str | None = typer.Option(
        None,
        "--code-workspace",
        help="Also write a VS Code workspace file for the set",
    ),
    force: bool = typer.Option(
        False,
        "--force",
        help="Overwrite an existing --code-workspace file",
    ),
) -> None:
    args: list[str] = []
    if store:
        args.extend(["--store", store])
    if json_output:
        args.append("--json")
    if code_workspace:
        args.extend(["--code-workspace", code_workspace])
    if force:
        args.append("--force")

    code = run_openspec(["context", *args])
    raise typer.Exit(code=code)


@app.command(
    "doctor",
    help="Report relationship health for the resolved OpenSpec root (passthrough to openspec doctor; v1.5.0+)",
)
def doctor_cmd(
    store: str | None = typer.Option(None, "--store", help="OpenSpec store id"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
) -> None:
    args: list[str] = []
    if store:
        args.extend(["--store", store])
    if json_output:
        args.append("--json")

    code = run_openspec(["doctor", *args])
    raise typer.Exit(code=code)


@app.command(
    "validate", help="Validate changes and specs (passthrough to openspec validate)"
)
def validate_cmd(
    item_name: str | None = typer.Argument(None, help="Change or spec ID"),
    all: bool = typer.Option(False, "--all", help="Validate all changes and specs"),
    changes: bool = typer.Option(False, "--changes", help="Validate only changes"),
    specs: bool = typer.Option(False, "--specs", help="Validate only specs"),
    type_: str | None = typer.Option(None, "--type", help="Disambiguate: change|spec"),
    strict: bool = typer.Option(False, "--strict", help="Enable strict mode"),
    archived: bool = typer.Option(
        False,
        "--archived",
        help="Validate that every archived change has all tasks.md checkboxes ticked (v1.9.0+)",
    ),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
    concurrency: int | None = typer.Option(
        None,
        "--concurrency",
        help="Max concurrent validations. Falls back to OPENSPEC_CONCURRENCY env (must be a positive int), else omitted (upstream default 6)",
    ),
    no_interactive: bool = typer.Option(
        True, "--no-interactive/--interactive", help="Disable prompts (default: true)"
    ),
    store: str | None = typer.Option(None, "--store", help="OpenSpec store id"),
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
    if archived:
        args.append("--archived")
    if json_output:
        args.append("--json")
    effective_concurrency = concurrency
    if effective_concurrency is None:
        env_raw = os.environ.get("OPENSPEC_CONCURRENCY")
        if env_raw:
            try:
                parsed = int(env_raw)
            except (TypeError, ValueError):
                parsed = None
            if parsed is not None and parsed > 0:
                effective_concurrency = parsed
    if effective_concurrency is not None:
        args.extend(["--concurrency", str(effective_concurrency)])
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
    sort: str | None = typer.Option(None, "--sort", help="Sort field"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
    store: str | None = typer.Option(None, "--store", help="OpenSpec store id"),
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
    item_name: str | None = typer.Argument(None, help="Change or spec ID"),
    type_: str | None = typer.Option(None, "--type", help="Disambiguate: change|spec"),
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
    requirement: str | None = typer.Option(
        None, "--requirement", "-r", help="Specific requirement id"
    ),
    diff: bool = typer.Option(
        False,
        "--diff",
        help="Render requirement-level diffs against the main spec (v1.11.0+)",
    ),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
    store: str | None = typer.Option(None, "--store", help="OpenSpec store id"),
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
    if diff:
        args.append("--diff")
    if json_output:
        args.append("--json")
    if store:
        args.extend(["--store", store])

    code = run_openspec(["show", *args])
    raise typer.Exit(code=code)


@app.command("status", help="Show project status (passthrough to openspec status)")
def status_cmd(
    change: str | None = typer.Option(None, "--change", help="Specific change id"),
    schema: bool = typer.Option(False, "--schema", help="Show JSON schema"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
    store: str | None = typer.Option(None, "--store", help="OpenSpec store id"),
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
    artifact: str | None = typer.Argument(None, help="Artifact path or id"),
    change: str | None = typer.Option(None, "--change", help="Specific change id"),
    schema: bool = typer.Option(False, "--schema", help="Show JSON schema"),
    json_output: bool = typer.Option(False, "--json", help="JSON output"),
    store: str | None = typer.Option(None, "--store", help="OpenSpec store id"),
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
    schema: str | None = typer.Option(None, "--schema", help="Show JSON schema"),
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
    source: str | None = typer.Argument(None, help="Source or target schema name"),
    name: str | None = typer.Argument(None),
    all_schemas: bool = typer.Option(False, "--all"),
    description: str | None = typer.Option(None, "--description"),
    artifacts: str | None = typer.Option(None, "--artifacts"),
    set_default: bool = typer.Option(False, "--default"),
    force: bool = typer.Option(False, "--force"),
    json_output: bool = typer.Option(False, "--json"),
    store: str | None = typer.Option(None, "--store"),
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
    path: str | None = typer.Argument(None, help="Project path"),
    tools: str | None = typer.Option(
        None, "--tools", help="Comma-separated tools, 'all', or 'none'"
    ),
    force: bool = typer.Option(False, "--force", help="Auto-cleanup legacy files"),
    profile: str | None = typer.Option(
        None, "--profile", help="Override global config profile (core|custom)"
    ),
    language: str | None = typer.Option(
        None,
        "--language",
        help="Language used for artifacts in new projects (v1.10.0+). Precedence: --language > OPENSPEC_LANGUAGE > unset.",
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
    effective_language = _resolve_language(language)
    if effective_language:
        args.extend(["--language", effective_language])

    code = run_openspec(["init", *args], timeout=60)
    raise typer.Exit(code=code)


@app.command(
    "update-core",
    help="Update OpenSpec instruction files (passthrough to openspec update)",
)
def update_core_cmd(
    path: str | None = typer.Argument(None, help="Project path"),
    force: bool = typer.Option(False, "--force", help="Force update"),
    strict_archived: bool = typer.Option(
        False,
        "--strict-archived",
        help="Fail on warnings from the post-update `openspec validate --archived` sweep. "
        "Alternatively set OPENSPEC_VALIDATE_ARCHIVED_STRICT=1.",
    ),
) -> None:
    args: list[str] = []
    if path:
        args.append(path)
    if force:
        args.append("--force")

    # Skip the v1.11.0 interactive "upgrade CLI?" offer when invoked from
    # openspec-extended so that automated contexts (CI, install --with-core)
    # don't hang on a prompt. The user can always run `openspec update`
    # directly to upgrade.
    code = run_openspec(
        ["update", *args], timeout=60, extra_env={"OPENSPEC_NO_UPDATE_CHECK": "1"}
    )
    _post_install_archived_sweep(strict=strict_archived)
    raise typer.Exit(code=code)


@app.command(
    "feedback", help="Submit feedback about OpenSpec (passthrough to openspec feedback)"
)
def feedback_cmd(
    message: str = typer.Argument(..., help="Short feedback message"),
    body: str | None = typer.Option(None, "--body", help="Detailed description"),
) -> None:
    args: list[str] = [message]
    if body:
        args.extend(["--body", body])

    code = run_openspec(["feedback", *args], timeout=60)
    raise typer.Exit(code=code)


@app.command("completion", help="Manage shell completions for the openspec CLI")
def completion_cmd(
    shell: str | None = typer.Argument(None, help="Shell: bash|zsh|fish"),
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


# ---------------------------------------------------------------------------
# Subcommand groups: 'new', 'store', 'config'
#
# Each group mirrors an upstream OpenSpec subcommand group as a thin Typer
# sub-app. Coexists with `openspec-extended osx <group>` (the programmatic
# JSON-only facade) where applicable — see `source/osx_cli.py`.
# ---------------------------------------------------------------------------


new_app = typer.Typer(help="Create new items (passthrough to openspec new)")


@new_app.command(
    "change",
    help="Create a new change directory (v1.7.0+; passthrough to openspec new change)",
)
def new_change_cmd(
    name: str = typer.Argument(..., help="Change name"),
    description: str | None = typer.Option(
        None, "--description", help="Description to add to README.md"
    ),
    goal: str | None = typer.Option(
        None, "--goal", help="Optional goal metadata to store with the change"
    ),
    schema: str | None = typer.Option(
        None, "--schema", help="Workflow schema name (default: spec-driven)"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    store: str | None = typer.Option(None, "--store", help="OpenSpec store id"),
) -> None:
    args: list[str] = ["new", "change", name]
    if description:
        args.extend(["--description", description])
    if goal:
        args.extend(["--goal", goal])
    if schema:
        args.extend(["--schema", schema])
    if json_output:
        args.append("--json")
    if store:
        args.extend(["--store", store])

    code = run_openspec(args)
    raise typer.Exit(code=code)


app.add_typer(new_app, name="new")


store_app = typer.Typer(
    help=(
        "Create and manage stores — standalone OpenSpec repos registered on this machine "
        "(passthrough to openspec store; v1.5.0+). "
        "For a JSON-only programmatic surface, see `openspec-extended osx store`."
    )
)


@store_app.command("setup", help="Create and register a local store (v1.5.0+)")
def store_setup_cmd(
    store_id: str | None = typer.Argument(None, help="Store id"),
    path: str | None = typer.Option(
        None, "--path", help="Folder where the store should live (e.g. ~/openspec/<id>)"
    ),
    init_git: bool = typer.Option(
        True,
        "--init-git/--no-init-git",
        help="Initialize a Git repository with an initial commit (default: on)",
    ),
    remote: str | None = typer.Option(
        None, "--remote", help="Canonical clone source recorded in store.yaml"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    args: list[str] = ["store", "setup"]
    if store_id:
        args.append(store_id)
    if path:
        args.extend(["--path", path])
    if not init_git:
        args.append("--no-init-git")
    if remote:
        args.extend(["--remote", remote])
    if json_output:
        args.append("--json")

    code = run_openspec(args)
    raise typer.Exit(code=code)


@store_app.command("register", help="Register an existing local store (v1.5.0+)")
def store_register_cmd(
    path_arg: str | None = typer.Argument(
        None, help="Filesystem path to the store repo"
    ),
    store_id: str | None = typer.Option(
        None, "--id", help="Store id; defaults to metadata or folder name"
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        help="Confirm creating store identity metadata for a healthy OpenSpec root",
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    args: list[str] = ["store", "register"]
    if path_arg:
        args.append(path_arg)
    if store_id:
        args.extend(["--id", store_id])
    if yes:
        args.append("--yes")
    if json_output:
        args.append("--json")

    code = run_openspec(args)
    raise typer.Exit(code=code)


@store_app.command(
    "unregister",
    help="Forget a local store registration without deleting files (v1.5.0+)",
)
def store_unregister_cmd(
    store_id: str = typer.Argument(..., help="Store id"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    args: list[str] = ["store", "unregister", store_id]
    if json_output:
        args.append("--json")

    code = run_openspec(args)
    raise typer.Exit(code=code)


@store_app.command(
    "remove",
    help="Forget a local store registration and delete its local folder (v1.5.0+)",
)
def store_remove_cmd(
    store_id: str = typer.Argument(..., help="Store id"),
    yes: bool = typer.Option(
        False, "--yes", help="Confirm local store folder deletion"
    ),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    args: list[str] = ["store", "remove", store_id]
    if yes:
        args.append("--yes")
    if json_output:
        args.append("--json")

    code = run_openspec(args)
    raise typer.Exit(code=code)


@store_app.command("list", help="List locally registered stores (v1.5.0+)")
def store_list_cmd(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    args: list[str] = ["store", "list"]
    if json_output:
        args.append("--json")

    code = run_openspec(args)
    raise typer.Exit(code=code)


@store_app.command(
    "doctor", help="Check local store registration and metadata (v1.5.0+)"
)
def store_doctor_cmd(
    store_id: str | None = typer.Argument(None, help="Store id (omit to check all)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    args: list[str] = ["store", "doctor"]
    if store_id:
        args.append(store_id)
    if json_output:
        args.append("--json")

    code = run_openspec(args)
    raise typer.Exit(code=code)


app.add_typer(store_app, name="store")


config_app = typer.Typer(
    help="View and modify global OpenSpec configuration (passthrough to openspec config)"
)


@config_app.command("path", help="Show config file location")
def config_path_cmd() -> None:
    raise typer.Exit(run_openspec(["config", "path"]))


@config_app.command("list", help="Show all current settings")
def config_list_cmd(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    args: list[str] = ["config", "list"]
    if json_output:
        args.append("--json")
    raise typer.Exit(run_openspec(args))


@config_app.command("get", help="Get a specific value (raw, scriptable)")
def config_get_cmd(
    key: str = typer.Argument(..., help="Config key (dotted path)"),
) -> None:
    raise typer.Exit(run_openspec(["config", "get", key]))


@config_app.command("set", help="Set a value (auto-coerce types)")
def config_set_cmd(
    key: str = typer.Argument(..., help="Config key (dotted path)"),
    value: str = typer.Argument(..., help="Config value"),
    string: bool = typer.Option(
        False, "--string", help="Force value to be stored as string"
    ),
    allow_unknown: bool = typer.Option(
        False,
        "--allow-unknown",
        help="Allow setting unknown keys (still enforces prototype-safety)",
    ),
) -> None:
    args: list[str] = ["config", "set", key, value]
    if string:
        args.append("--string")
    if allow_unknown:
        args.append("--allow-unknown")
    raise typer.Exit(run_openspec(args))


@config_app.command("unset", help="Remove a setting")
def config_unset_cmd(
    key: str = typer.Argument(..., help="Config key (dotted path)"),
) -> None:
    raise typer.Exit(run_openspec(["config", "unset", key]))


@config_app.command("reset", help="Reset config to defaults")
def config_reset_cmd() -> None:
    raise typer.Exit(run_openspec(["config", "reset"]))


@config_app.command("edit", help="Open config in your editor")
def config_edit_cmd() -> None:
    raise typer.Exit(run_openspec(["config", "edit"]))


@config_app.command("profile", help="Set or show the active workflow profile")
def config_profile_cmd(
    preset: str | None = typer.Argument(
        None, help="Profile preset: core | custom | <name>"
    ),
) -> None:
    args: list[str] = ["config", "profile"]
    if preset:
        args.append(preset)
    raise typer.Exit(run_openspec(args))


app.add_typer(config_app, name="config")


@app.command(
    "restore-core",
    help="Restore the openspec global config from the most recent .openspec-extended-baseline.json snapshot.",
)
def restore_core(
    path: str | None = typer.Option(
        None,
        "--from",
        help="Path to the baseline file. Defaults to ./.openspec-extended-baseline.json",
    ),
) -> None:
    """Restore the captured snapshot to ``~/.config/openspec/config.json``.

    Re-applies the snapshot's ``global_config`` block and writes it back.
    The baseline file is removed on success unless ``--keep-snapshot`` is passed.
    """
    baseline = Path(path) if path else (Path.cwd() / CORE_BASELINE_FILENAME)
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
