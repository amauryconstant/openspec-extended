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
import time
from datetime import UTC
from pathlib import Path

import toml
import typer
from rich.console import Console

from source import __version__
from source.lib.osx import (
    CORE_BASELINE_FILENAME,
    ORCHESTRATION_RESOURCE_NAMES,
    REQUIRED_CORE_SKILLS,
)
from source.orchestrator.engine import OrchestratorState, run_orchestrator
from source.osx_cli import osx_app
from source.tools import (
    PLATFORM_TOKENS,
    REGISTRY,
    TOOL_DIRS,
    ToolAdapter,
    _adapter_tokens,
    strip_agent_line,
)

SCRIPT_NAME = "openspec-extended"

# Adapter registry: ``source.tools.REGISTRY`` is the single source of
# truth for tool-specific behaviour. ``TOOL_DIRS`` and ``PLATFORM_TOKENS``
# are derived views re-exported here so existing
# (``from source.cli import TOOL_DIRS, PLATFORM_TOKENS``) keep working.
# The substitution mechanism itself — ``{{TOKEN}}`` placeholders in
# resource files rendered at deploy time — is unchanged;
# ``_substitute_tokens`` consumes ``PLATFORM_TOKENS`` from this module.
#
# Source files under ``orchestrator/resources/canonical/`` (the
# orchestrator side; the skills side lives under
# ``skills/resources/canonical/`` per Phase 4) carry ``{{TOKEN}}``
# placeholders; the deploy step substitutes them with the values for the
# active tool. The canonical source ships the same tokens literally —
# the Python side is the single source of truth for substitution. Per-
# adapter rendering happens at deploy time via ``deploy_*``; there is no
# on-disk per-tool mirror and no separate token-substitution step.
# New tokens MUST be added to both platforms; the substitution is silent
# for unknown tokens so future additions don't crash.

_LEFTOVER_TOKEN_RE = re.compile(r"\{\{([A-Z_]+)\}\}")

# Canonical slash form in source: ``/osx-<id>`` (matches opencode native).
# The Claude adapter rewrites this to ``/osx:<id>`` at deploy time.
# The negative lookbehind / lookahead avoids matching path components
# (e.g. ``.opencode/skills/osx-modify/SKILL.md`` is left untouched).
_SLASH_OSX_RE = re.compile(r"(?<![\w/])/osx-([a-z0-9-]+)(?!/)")

# Cross-reference to upstream OpenSpec core skills in the colon-form
# slash command: ``/opsx:<verb>``. Rewritten to the adapter's
# ``cross_ref_prefix`` form (e.g. Codex's ``$openspec-propose``) for
# skills-only adapters. Shipped adapters (``cross_ref_prefix=""`` →
# falls back to ``skill_prefix="/"``) skip the rewrite so the canonical
# upstream spelling survives. Same lookbehind/lookahead guard as
# ``_SLASH_OSX_RE`` keeps path components (``.opencode/skills/...``)
# untouched.
_SLASH_OPSX_RE = re.compile(r"(?<![\w/])/opsx:([a-z][a-z-]+)(?!/)")


def _rewrite_skill_body_refs(body: str, adapter: ToolAdapter) -> str:
    """Rewrite ``/opsx:<cmd>`` cross-references in a SKILL.md body
    to the adapter's ``cross_ref_prefix`` form.

    For shipped adapters (opencode, claude), ``cross_ref_prefix``
    defaults to ``""`` and falls back to ``skill_prefix`` (``"/"``),
    so the canonical ``/opsx:<cmd>`` form is preserved.

    For skills-only adapters with a different cross-ref prefix
    (Codex's ``$``, Kimi's ``/skill:``), the references are
    rewritten to ``<cross_ref_prefix>openspec-<cmd>`` — the upstream
    core skill name (``openspec-propose``, ``openspec-apply``, …),
    not the extended ``osx-<cmd>`` name.

    Unknown ``/opsx:<cmd>`` references are left verbatim (matches
    upstream ``transformToSkillReferences`` semantics in
    ``core/source/src/utils/command-references.ts``); the regex
    only matches ``[a-z][a-z-]+`` so false positives in markdown
    prose stay rare.
    """
    cross_ref_prefix = adapter.cross_ref_prefix or adapter.skill_prefix
    if cross_ref_prefix == "/":
        return body
    return _SLASH_OPSX_RE.sub(f"{cross_ref_prefix}openspec-\\1", body)


def _substitute_tokens(text: str, tool: str) -> str:
    """Replace every ``{{TOKEN}}`` in ``text`` with the value for ``tool``.

    Unknown tokens (or unknown tools) are left verbatim — that way a future
    token added to the source but not yet to ``PLATFORM_TOKENS`` surfaces as a
    literal in the deployed file rather than silently disappearing. The
    substituter is the single source of truth for token values; deploy-time
    rendering in ``deploy_*`` is the only mechanism that produces per-
    adapter output.

    After token substitution, the canonical slash form ``/osx-<id>`` is
    rewritten to the Claude slash form ``/osx:<id>`` for tools whose
    ``slash_prefix`` is colon-terminated. Filenames containing ``/osx-<id>/``
    are left untouched.
    """
    mapping = PLATFORM_TOKENS.get(tool, {})
    if not mapping:
        # Fall back to a live REGISTRY read so monkeypatched / synthesised
        # adapters (e.g. the skills-only test fixtures that land after
        # module import) still see their token values. For shipped
        # adapters PLATFORM_TOKENS already covers them so the fallback
        # never fires in production.
        adapter = REGISTRY.get(tool)
        if adapter is not None:
            mapping = _adapter_tokens(adapter)

    def repl(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in mapping:
            return mapping[key]
        return match.group(0)

    text = _LEFTOVER_TOKEN_RE.sub(repl, text)

    slash_prefix = mapping.get("CMD_PREFIX", "")
    if slash_prefix.endswith(":"):
        text = _SLASH_OSX_RE.sub(r"/osx:\1", text)

    return text


console = Console()

app = typer.Typer(
    name=SCRIPT_NAME,
    help=f"{SCRIPT_NAME} - Installer and orchestrator for OpenSpec resources",
    add_completion=False,
)
app.add_typer(osx_app, name="osx")


def get_resources_dir() -> Path:
    """Return the orchestrator-side resources directory.

    The project ships two parallel resource trees (Phase 4 split) —
    ``orchestrator/resources/`` (workflow side, this function) and
    ``skills/resources/`` (see :func:`get_skills_resources_dir`).
    Each side owns its own manifest and writes its own target-side
    manifest at deploy time (Phase 5).

    In the source tree, ``source/`` lives at ``orchestrator/source/``,
    so ``Path(__file__).parent.parent`` resolves to ``orchestrator/``
    and adding ``"resources"`` lands at ``orchestrator/resources/``.

    In the frozen bundle, PyInstaller's ``openspec.spec`` collects each
    side's files under the legacy ``resources/`` prefix for the
    orchestrator side and under ``skills/resources/`` for the skills
    side.
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
    adapter = REGISTRY.get(tool)
    if adapter is None:
        raise ValueError(f"Unknown tool: {tool!r}; available: {sorted(REGISTRY)}")
    return adapter.skills_dir


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
    tool: str,
    shared_refs: list[str] | None = None,
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
        # Single canonical shared-references pool — lives once on the
        # orchestrator side at
        # `orchestrator/resources/canonical/skills/references/`, regardless
        # of the consuming skill's side (orchestrator or skills) and
        # regardless of the target tool (opencode, claude, …). The
        # per-tool `<tool>/skills/references/` directory does not exist
        # on disk and is not generated — see
        # `orchestrator/resources/AGENTS.md` and
        # `tests/unit/test_resource_contract.py::TestSharedReferencesPackaging`.
        orchestrator_resources = get_resources_dir()
        shared_refs_dir = orchestrator_resources / "canonical" / "skills" / "references"
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


def _build_skill_mirror(source_path: Path, name: str, adapter: ToolAdapter) -> str:
    """Read an opencode command file and render it as a per-adapter SKILL.md body.

    Drives four adapter-controlled behaviours:

    - ``agent_field_transform`` strips opencode-only ``agent:`` lines
      for tools whose slash resolver doesn't read opencode's dispatch
      model (Claude, Cursor, Codex, Kimi). When the adapter is
      ``commands_style="skills-only"`` and ``agent_field_transform`` is
      ``None``, falls back to :func:`strip_agent_line` — skills-only
      tools never read opencode's ``agent:`` directive, so dropping it
      is the right default. Shipped adapters that set
      ``agent_field_transform`` explicitly still win.
    - ``inject_name_in_skill_mirror`` adds ``name: <name>`` for tools
      whose slash resolver reads it from frontmatter (Claude). Only
      consulted when ``"name"`` is not present in ``frontmatter_extras``;
      an extras-supplied name wins.
    - ``frontmatter_extras`` injects arbitrary ``key: value`` pairs
      into the closing-fence frontmatter, in iteration order.
    - inline fallback handles the rare unclosed-frontmatter case.

    Returns the rendered string; callers write it to disk.
    """
    extras = adapter.frontmatter_extras
    name_via_extras = "name" in extras
    want_inject_name = adapter.inject_name_in_skill_mirror and not name_via_extras
    transform = adapter.agent_field_transform
    if transform is None and adapter.commands_style == "skills-only":
        transform = strip_agent_line
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
                if want_inject_name:
                    out_lines.append(f"name: {name}\n")
                for extra_key, extra_value in extras.items():
                    out_lines.append(f"{extra_key}: {extra_value}\n")
                seen_close = True
                in_fm = False
            out_lines.append(line)
            continue
        if in_fm and transform is not None:
            line = transform(line)
            if line == "":
                continue
        out_lines.append(line)
    if not seen_close and (want_inject_name or extras):
        # File had no closing frontmatter fence; still inject a fresh
        # header with the name/extras so downstream readers get one.
        head = ["---\n"]
        if want_inject_name:
            head.append(f"name: {name}\n")
        for extra_key, extra_value in extras.items():
            head.append(f"{extra_key}: {extra_value}\n")
        head.append("---\n")
        return "".join(head) + raw
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


def _deploy_skill_mirror(
    source_path: Path,
    source_base: Path,
    target_dir: Path,
    name: str,
    tool: str,
    adapter: ToolAdapter,
) -> Path:
    """Render ``source_path`` as a modern ``<target>/skills/<name>/SKILL.md``
    skill mirror and copy any ``references/<file>.md`` files referenced
    from the body so the skill is self-sufficient at deploy time.

    Shared between two ``commands_style`` branches:

    - ``namespaced-with-skill-mirror`` (Claude): the legacy command file
      was already written by ``deploy_commands``; this helper dual-emits
      the skill mirror so the slash command resolves against the modern
      skills surface too (mirrors upstream OpenSpec's dual-emit
      strategy introduced in v1.7.0, current as of v1.13.0).
    - ``skills-only`` (Codex, Kimi, Zed, ForgeCode): the legacy command
      file is *not* written (the target doesn't load it). The skill
      mirror is the only command surface.

    Drives three adapter-controlled behaviours:

    - :func:`_build_skill_mirror` for frontmatter rewriting (``agent:``
      strip via ``agent_field_transform`` — defaults to
      ``strip_agent_line`` for skills-only adapters that don't override
      it — plus ``name:`` injection and ``frontmatter_extras``).
    - :func:`_substitute_tokens_in_file` for ``{{TOKEN}}`` substitution
      driven by ``PLATFORM_TOKENS``.
    - :func:`_rewrite_skill_body_refs` for body cross-reference
      rewriting (``/opsx:<cmd>`` → ``<cross_ref_prefix>openspec-<cmd>``
      for skills-only adapters with a non-canonical cross-ref prefix).
      Shipped adapters (``cross_ref_prefix=""`` → falls back to
      ``skill_prefix="/"``) hit the no-op branch.

    Returns the path of the written ``SKILL.md``. References are copied
    as a side effect; their on-disk token substitution is independent of
    the skill mirror's body rewrite.
    """
    skill_dir = target_dir / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(_build_skill_mirror(source_path, name, adapter))
    _substitute_tokens_in_file(skill_md, tool)

    # Apply the cross-ref prefix rewrite (L4.3) AFTER token substitution
    # so any ``{{CROSS_REF_PREFIX}}`` substitution has already run on
    # tokens; the rewrite targets literal ``/opsx:<cmd>`` references
    # only and is a no-op for shipped adapters.
    body = skill_md.read_text()
    body = _rewrite_skill_body_refs(body, adapter)
    skill_md.write_text(body)

    # Copy any references/ files referenced from the body so the skill
    # is self-sufficient at deploy time. Source refs live once under
    # the source skills/references/ pool. Read the *rewritten* body
    # because the cross-ref rewrite can never affect reference paths —
    # refs are slash-form commands, never ``/opsx:<cmd>`` — but reading
    # after the rewrite keeps the helper consistent.
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
    return skill_md


def deploy_commands(source_base: Path, target_dir: Path, name: str, tool: str) -> None:
    adapter = REGISTRY[tool]

    # Adapter-driven source resolution: search ``source_base/<name>.md``,
    # then fall back to ``source_base/<subdir>/<base_name>.md``. Works
    # for both flat and namespaced command trees today; skills-only
    # adapters need the same resolution because the source command file
    # is the input to the skill mirror (see L4.1).
    source_path = source_base / f"{name}.md"
    if not source_path.exists():
        for subdir in source_base.iterdir():
            if subdir.is_dir():
                base_name = (
                    name.replace("osx-", "", 1) if name.startswith("osx-") else name
                )
                alt_source = subdir / f"{base_name}.md"
                if alt_source.exists():
                    source_path = alt_source
                    break
        else:
            raise FileNotFoundError(f"Command not found: {name}")

    if adapter.commands_style == "skills-only":
        # Skills-only adapters (Codex, Kimi, Zed, ForgeCode) don't
        # load slash-command files — the slash command surface is the
        # modern skills tree (``<target>/<skills_dir>/skills/<name>/SKILL.md``).
        # Skip the ``commands/`` directory entirely (no legacy file
        # written) and dual-emit the skill mirror only.
        skill_md = _deploy_skill_mirror(
            source_path, source_base, target_dir, name, tool, adapter
        )
        relative = skill_md.relative_to(target_dir)
        log_info(
            f"deployed skill mirror for {tool!r} "
            f"(commands_style=skills-only): {relative}"
        )
        return

    # Adapter-driven legacy form: commands_dir (subdir layout) +
    # cmd_filename_strip_prefix (prefix strip). For opencode this is
    # ``target/commands/<name>.md`` (flat, prefix preserved); for Claude
    # it's ``target/commands/osx/<base>.md`` (nested, prefix stripped).
    cmd_subdir_parts = adapter.commands_dir.split("/")
    target_commands = target_dir.joinpath(*cmd_subdir_parts)
    target_commands.mkdir(parents=True, exist_ok=True)

    deployed_name = name
    if adapter.cmd_filename_strip_prefix and name.startswith(
        adapter.cmd_filename_strip_prefix
    ):
        deployed_name = name[len(adapter.cmd_filename_strip_prefix) :]
    target_cmd_path = target_commands / f"{deployed_name}.md"
    shutil.copy2(source_path, target_cmd_path)
    _substitute_tokens_in_file(target_cmd_path, tool)

    if adapter.commands_style != "namespaced-with-skill-mirror":
        # Single-emit layouts (opencode today; future flat adapters) write
        # the command file only — the file format and the per-tool
        # extension come from the adapter.
        return

    # namespaced-with-skill-mirror: dual-emit. Also write the command as a
    # skill at ``<target>/skills/<name>/SKILL.md`` so the slash command
    # resolves against the modern skills surface as well — mirrors
    # upstream OpenSpec's dual-emit strategy (introduced in v1.7.0,
    # current as of v1.11.0). The legacy .claude/commands/ file written
    # above remains in place for back-compat.
    _deploy_skill_mirror(source_path, source_base, target_dir, name, tool, adapter)


def deploy_agents(source_base: Path, target_dir: Path, name: str, tool: str) -> None:
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
    with_orchestration: bool,
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

        if name in ORCHESTRATION_RESOURCE_NAMES and not with_orchestration:
            gated += 1
            continue

        # Phase 5 split: each side's manifest declares only its own
        # resources, and on disk each resource lives on exactly one
        # side. The deploy_type caller passes a per-side source manifest
        # so this defensive skip rarely fires — but it remains for
        # safety against manifest entries that drift from the on-disk
        # layout. Skills are directories; commands and agents are files.
        if resource_type == "skills":
            source_path = source_type_dir / name
        else:
            source_path = source_type_dir / f"{name}.md"
        if not source_path.exists():
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
            f"  Skipped {gated} orchestration {resource_type} (use --with-orchestration)"
        )

    return (count, skipped)


def _filter_orchestration(manifest: dict) -> dict:
    """Return ``manifest`` with orchestration resources removed from each kind.

    Used to keep the on-disk target manifest consistent with ``--with-orchestration``
    without forcing the deploy loop to skip everything per-side. Preserves
    top-level keys (e.g. ``version``) so callers don't lose them.
    """
    filtered: dict = {
        key: value for key, value in manifest.items() if key != "resources"
    }
    filtered["resources"] = {}
    for resource_type, entries in manifest.get("resources", {}).items():
        if not isinstance(entries, dict):
            continue
        filtered["resources"][resource_type] = {
            name: info
            for name, info in entries.items()
            if name not in ORCHESTRATION_RESOURCE_NAMES
        }
    return filtered


def _preserve_core_tracking(side_manifest: dict, target_manifest: Path) -> dict:
    """Carry forward ``[core]`` and any ``osc-*`` skill entries from the
    previously written ``target_manifest`` into ``side_manifest``.

    ``deploy_all_resources`` rewrites the orchestrator-side manifest on
    every install. When a previous ``--with-core`` install wrote the
    ``[core]`` block and ``[resources.skills.osc-*]`` entries, a
    subsequent ``--with-orchestration`` (or default) install would
    silently clobber them — leaving on-disk ``osc-*`` skills untracked
    and the validator's cross-check failing.

    Returns ``side_manifest`` (mutated in-place is fine; we return it for
    call-site clarity). When the file is missing or unparseable, returns
    the input untouched.
    """
    if not target_manifest.is_file():
        return side_manifest
    try:
        existing = toml.loads(target_manifest.read_text())
    except (OSError, toml.TomlDecodeError):
        return side_manifest
    if not isinstance(existing, dict):
        return side_manifest

    if "core" in existing and isinstance(existing["core"], dict):
        side_manifest["core"] = existing["core"]

    existing_skills = (
        existing.get("resources", {}).get("skills", {})
        if isinstance(existing.get("resources"), dict)
        else {}
    )
    if isinstance(existing_skills, dict):
        osc_entries = {
            name: info
            for name, info in existing_skills.items()
            if name.startswith("osc-") and isinstance(info, dict)
        }
        if osc_entries:
            side_resources = side_manifest.setdefault("resources", {})
            if not isinstance(side_resources, dict):
                side_resources = {}
                side_manifest["resources"] = side_resources
            side_skills = side_resources.setdefault("skills", {})
            if not isinstance(side_skills, dict):
                side_skills = {}
                side_resources["skills"] = side_skills
            side_skills.update(osc_entries)
    return side_manifest


def _resolve_side_manifest(source_dir: Path) -> tuple[Path | None, dict]:
    """Read the source-side manifest at ``source_dir/manifest.toml``.

    Returns ``(path, data)`` where ``path`` is ``None`` if no manifest exists.
    The caller decides what to do when ``path`` is ``None`` (e.g. the skills
    side is optional in some configurations).
    """
    manifest_path = source_dir / "manifest.toml"
    if not manifest_path.is_file():
        return None, {}
    return manifest_path, toml.loads(manifest_path.read_text())


def deploy_all_resources(tool: str, force: bool, with_orchestration: bool) -> None:
    """Deploy every resource across the orchestrator and skills trees.

    Phase 5 split the on-disk manifests: each side writes its own manifest
    at the target. Orchestrator-side resources land at ``<target>/manifest.toml``
    (legacy position); skills-side resources land at ``<target>/skills-manifest.toml``.

    Phase 2A: the canonical on-disk source is ``canonical/`` (a single,
    tool-neutral tree); the ``ToolAdapter`` drives per-tool rendering
    (commands_dir layout, cmd_filename_strip_prefix,
    inject_name_in_skill_mirror, frontmatter_extras,
    agent_field_transform, token substitution). The per-tool source
    trees were deleted in lockstep — there is no ``<tool>/`` source
    to read from anymore.
    """
    source_version = __version__
    target_dir = Path.cwd() / TOOL_DIRS[tool]
    target_dir.mkdir(parents=True, exist_ok=True)

    orchestrator_source_dir = get_resources_dir() / "canonical"
    _, orchestrator_manifest = _resolve_side_manifest(orchestrator_source_dir)
    if not orchestrator_manifest:
        log_error(f"Manifest not found: {orchestrator_source_dir / 'manifest.toml'}")
        raise SystemExit(1)

    skills_source_dir = get_skills_resources_dir() / "canonical"
    _, skills_manifest = _resolve_side_manifest(skills_source_dir)

    total_count = 0
    total_skipped = 0

    sides = (
        ("orchestrator", orchestrator_source_dir, orchestrator_manifest),
        ("skills", skills_source_dir, skills_manifest),
    )

    for side_label, source_dir, source_manifest in sides:
        if not source_manifest:
            continue
        target_manifest = (
            target_dir / "manifest.toml"
            if side_label == "orchestrator"
            else target_dir / "skills-manifest.toml"
        )
        for resource_type in ("skills", "commands", "agents"):
            cnt, skp = deploy_type(
                resource_type,
                source_dir,
                target_dir,
                target_manifest,
                source_manifest,
                force,
                tool,
                with_orchestration,
            )
            total_count += cnt
            total_skipped += skp

        side_manifest = dict(source_manifest)
        side_manifest["version"] = source_version
        if not with_orchestration:
            side_manifest = _filter_orchestration(side_manifest)
        if side_label == "orchestrator":
            side_manifest = _preserve_core_tracking(side_manifest, target_manifest)
        target_manifest.write_text(toml.dumps(side_manifest))
        log_success(f"{side_label.title()} manifest updated to v{source_version}")
        console.print(f"  Target: {target_manifest}")

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
    if tool not in REGISTRY:
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
        adapter = REGISTRY[tool]
        if adapter.commands_style == "flat":
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
        elif adapter.commands_style == "namespaced-with-skill-mirror":
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
        elif adapter.commands_style == "skills-only":
            # skills-only adapters (Codex, Kimi, Zed, ForgeCode) don't
            # load command files — no commands/ subdir to walk. Skills DO
            # land under <target>/<skills_dir>/skills/ (the same path the
            # universal skills block at the top of this function already
            # walks). Re-walk here so the per-style contract is explicit:
            # only directories are removed (skill names should always be
            # directories); non-directory entries (files / symlinks) are
            # skipped — symlinks could be left by a user pointing at a
            # sibling tree and we don't want to follow them.
            skills_only_dir = target_dir / "skills"
            if skills_only_dir.is_dir():
                for entry in skills_only_dir.iterdir():
                    if not entry.is_dir():
                        continue
                    if starts_with_managed(entry.name) is None:
                        continue
                    if should_keep(entry.name):
                        continue
                    if safe_remove(entry):
                        removed += 1
        elif adapter.commands_style == "namespaced":
            # namespaced: declared in the type system for future use;
            # no shipped adapter exercises it. No commands/ subdir to
            # walk; skills are reconciled by the universal skills block
            # at the top of this function.
            pass
        else:
            raise NotImplementedError(
                f"purge_managed_resources: commands_style={adapter.commands_style!r}"
            )

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


def _backup_existing(target: Path, incoming_bytes: bytes | None = None) -> Path | None:
    """Snapshot ``target`` to ``<target>.user-backup-<ts>`` if it exists.

    Used by the core renamer to preserve user-authored content before
    POSIX ``rename`` would silently overwrite it. Returns the backup path
    if a backup was made, otherwise ``None``.

    When ``incoming_bytes`` is supplied and matches ``target``'s bytes
    exactly, no backup is created: the caller is about to overwrite the
    file with content byte-for-byte identical to what is already on disk,
    so there is nothing to preserve (this is the common case when the
    wrapper re-renders its own previous output). The byte-equality
    short-circuit applies to files only; directory targets are always
    copied.
    """
    if not target.exists():
        return None
    if (
        incoming_bytes is not None
        and target.is_file()
        and target.read_bytes() == incoming_bytes
    ):
        return None
    ts = int(time.time())
    backup = target.with_name(f"{target.name}.user-backup-{ts}")
    counter = 1
    while backup.exists():
        backup = target.with_name(f"{target.name}.user-backup-{ts}-{counter}")
        counter += 1
    if target.is_dir():
        shutil.copytree(target, backup)
    else:
        shutil.copy2(target, backup)
    return backup


_FRONTMATTER_FENCE = re.compile(r"^---\s*$", re.MULTILINE)
_FENCE_OPEN = re.compile(r"(?m)^[ \t]*(```|~~~)")


def _rewrite_renamed_references(content: str) -> str:
    """Rewrite ``/opsx-*``, ``/opsx:`` and ``OPSX:`` tokens to ``osc-*``.

    - ``OPSX:`` is rewritten inside the YAML frontmatter only (line-
      anchored) — that is the only legitimate ``OPSX:`` token upstream
      emits, and the line anchor avoids clobbering user prose that
      happens to mention the string.
    - ``/opsx-*`` and ``/opsx:`` are rewritten **everywhere** in the
      body — inline prose, list items, table cells, AND inside fenced
      code blocks. The v1.10.5 narrowing (``^/opsx-`` line-start only)
      let upstream-generated inline references slip through into
      deployed skill bodies; that was the user-facing regression this
      function reverses.

      Why rewrite inside fences too: upstream places assistant-output
      templates inside ```` ``` ```` blocks (e.g. ``osc-onboard/SKILL.md``
      line 158), and those templates include ``/opsx-*`` slash-command
      references that the wrapper's filename rename has invalidated
      (the file is now ``osc-explore.md`` → ``/osc-explore``). Leaving
      the fences intact propagates the upstream vocabulary into the
      installed tree, which is exactly the inconsistency the user wants
      to eliminate. The rewrite is also intentionally applied to
      ``commands/*.md`` files (where fenced samples can carry the same
      stale references), so a single canonical rule covers all surfaces.

    Character classes are tight: ``[a-z][a-z0-9-]+`` (hyphen form) and
    ``[a-z][a-z-]+`` (colon form) match the upstream canonical slash-
    command vocabulary exactly (``apply``, ``archive``, ``bulk-archive``,
    ``continue``, ``explore``, ``ff``, ``new``, ``onboard``, ``propose``,
    ``sync``, ``update``, ``verify``) and nothing else in practice. Real
    user code samples that mention ``/opsx-*`` slash commands are
    vanishingly rare; if one exists, rewriting it matches the user's
    installed convention anyway. Rewriting an already-rewritten file is
    a no-op (``/osc-*`` is not matched by ``/opsx-*``), so the function
    is idempotent.
    """
    front_match = _FRONTMATTER_FENCE.search(content)
    if front_match is None:
        head_end = 0
        front_end = -1
    else:
        head_end = front_match.start()
        second = _FRONTMATTER_FENCE.search(content, front_match.end())
        front_end = second.end() if second is not None else -1

    head = content[:head_end]
    if front_end > 0:
        front = content[head_end:front_end]
        tail = content[front_end:]
        front = re.sub(r"^OPSX:\s", "OSC: ", front, flags=re.MULTILINE)
    else:
        front = ""
        tail = content[head_end:]

    tail = re.sub(r"/opsx-([a-z][a-z0-9-]+)", r"/osc-\1", tail)
    tail = re.sub(r"/opsx:([a-z][a-z-]+)", r"/osc:\1", tail)

    return head + front + tail


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
                dest = cmd_dir / new_name
                if dest.exists() and dest != cmd_file:
                    backup = _backup_existing(dest, incoming_bytes=cmd_file.read_bytes())
                    if backup is not None:
                        log_warn(f"Preserved user file at {backup}")
                cmd_file.rename(dest)
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
                        dest = osc_dir / f.name
                        if dest.exists() and dest != f:
                            backup = _backup_existing(dest, incoming_bytes=f.read_bytes())
                            if backup is not None:
                                log_warn(f"Preserved user file at {backup}")
                        f.rename(dest)
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
        content = _rewrite_renamed_references(content)
        cmd_file.write_text(content)

    skills_dir = target_dir / "skills"
    if skills_dir.is_dir():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and skill_dir.name.startswith("openspec-"):
                new_name = skill_dir.name.replace("openspec-", "osc-", 1)
                dest_dir = skills_dir / new_name
                if dest_dir.exists():
                    for f in skill_dir.glob("*"):
                        dest = dest_dir / f.name
                        if dest.exists() and dest != f:
                            incoming_bytes = (
                                f.read_bytes() if f.is_file() else None
                            )
                            backup = _backup_existing(dest, incoming_bytes=incoming_bytes)
                            if backup is not None:
                                log_warn(f"Preserved user file at {backup}")
                        f.rename(dest)
                    skill_dir.rmdir()
                else:
                    skill_dir.rename(dest_dir)
                renamed += 1

        for skill_file in skills_dir.rglob("*.md"):
            content = skill_file.read_text()
            content = re.sub(
                r"^name: openspec-", "name: osc-", content, flags=re.MULTILINE
            )
            content = _rewrite_renamed_references(content)
            skill_file.write_text(content)

    if renamed > 0:
        log_success(f"Renamed {renamed} core resource(s)")


def _detect_existing_core_deployment(tool: str) -> bool:
    """Return True if a previous core deployment is detectable.

    Detection sources (any one is enough):

    - ``<target_dir>/skills/<name>`` matches one of the canonical core
      names from ``REQUIRED_CORE_SKILLS`` (post-rename marker). Tightened
      from a prefix match: a user-authored ``osc-internal/`` skill no
      longer triggers the gate.
    - ``<target_dir>/manifest.toml`` declares ``[core].installed = true``.

    The earlier global ``openspec list --json`` branch was removed:
    ``openspec list`` returns the user's project state (changes + specs),
    not per-tool state, so once any core install exists, every
    subsequent cross-tool install would refuse without ``--force``.
    Per-tool scoping is restored by relying on the on-disk marker and the
    manifest declaration only.
    """
    target_dir = Path.cwd() / get_tool_dir(tool)

    skills_dir = target_dir / "skills"
    if skills_dir.is_dir():
        canonical = set(REQUIRED_CORE_SKILLS)
        for entry in skills_dir.iterdir():
            if entry.is_dir() and entry.name in canonical:
                return True

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
        console.print(f"  Hint: openspec-extended install {tool} --with-core --force")
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

    identical_backups = _purge_identical_backups(target_dir)
    if identical_backups:
        log_info(f"Purged {identical_backups} identical user backup(s)")

    nested_removed = _purge_nested_core_orphans(target_dir)
    if nested_removed:
        log_info(f"Purged {nested_removed} nested core orphan(s)")

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


def validate_deployment(target_dir: Path, manifest: dict, *, label: str = "") -> dict:
    warnings = 0
    notes: list[dict] = []
    if not target_dir.is_dir():
        return {"valid": True, "warnings": 0, "notes": []}

    # Tools that don't expose an ``agents/`` directory (e.g. Claude Code,
    # which uses an agent-per-conversation model rather than on-disk agent
    # definitions) skip agent validation. Per-side manifests still list
    # agents (for OpenCode parity); the deploy loop above skips them per
    # the source-existence check.
    target_adapter = next(
        (a for a in REGISTRY.values() if str(target_dir).endswith(a.skills_dir)),
        None,
    )
    skip_agents = target_adapter is not None and not target_adapter.has_agents_dir

    # Informational note (Phase 2 L3.2): when the active adapter's
    # ``skills_dir`` is shared by multiple shipped registry entries
    # (currently only hypothetical ``.agents``-using adapters like
    # Codex/Zed/Antigravity), flag it so the user knows a sibling tool
    # install can reuse the existing skill tree. For the two shipped
    # adapters (opencode, claude) this branch never fires today — their
    # ``skills_dir`` is unique to the adapter — so byte-equality for the
    # shipped set is preserved.
    if target_adapter is not None:
        shared_root_owners = [
            tid
            for tid, other in REGISTRY.items()
            if tid != target_adapter.tool_id
            and other.skills_dir == target_adapter.skills_dir
        ]
        if shared_root_owners:
            note = {
                "check": "shared-skills-root",
                "tool": target_adapter.tool_id,
                "shared_with": shared_root_owners,
            }
            notes.append(note)
            console.print(
                f"  [blue]→[/blue] shared skills root "
                f"'{target_adapter.skills_dir}' is also used by: "
                f"{', '.join(shared_root_owners)}"
            )

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
                    # v1.7.0, current as of v1.13.0).
                    if not found:
                        skill_path = target_dir / "skills" / name / "SKILL.md"
                        if skill_path.is_file():
                            found = True

            if not found:
                suffix = f" ({label})" if label else ""
                log_warn(f"Resource '{name}' in manifest{suffix} but not deployed")
                warnings += 1

    if warnings > 0:
        scope = f" ({label})" if label else ""
        console.print(f"  Validation{scope}: {warnings} warning(s)")

    return {"valid": warnings == 0, "warnings": warnings, "notes": notes}


def _validate_target_after_deploy(target_dir: Path) -> None:
    """Validate every per-side manifest that exists on disk after a deploy.

    Phase 5 split the on-disk manifests; we may have only the orchestrator
    side (``manifest.toml``) deployed (utility-only install), only the
    skills side (``skills-manifest.toml``), or both. Run the per-side
    validation pass for whichever manifests are present.
    """
    if not target_dir.is_dir():
        return
    manifest_files = (
        ("orchestrator", target_dir / "manifest.toml"),
        ("skills", target_dir / "skills-manifest.toml"),
    )
    for label, path in manifest_files:
        if not path.is_file():
            continue
        try:
            data = toml.loads(path.read_text())
        except toml.TomlDecodeError:
            log_warn(f"Skipping invalid manifest: {path}")
            continue
        validate_deployment(target_dir, data, label=label)


def _parse_tool_target(raw: str) -> list[str]:
    """Parse a multi-tool target argument into a list of registered tool ids.

    Accepts comma-separated ids (``"opencode,claude"``) or a single id
    (``"opencode"``). Whitespace around ids is stripped. Rejects empty
    input, unknown ids, and duplicates — every failure logs an error
    and raises ``SystemExit(1)`` (preserving the v1.9.x exit code).

    Note: ``--all`` is intentionally NOT supported. The upstream
    ``openspec init --tools all`` flag configures all 35 upstream tools,
    which is the wrong semantics here — this CLI deploys the extended
    ``osx-*`` layer to specific targets, and projects rarely need
    more than 2-3 CLIs. Users wanting multiple tools list them
    explicitly: ``install opencode,claude``.
    """
    raw = (raw or "").strip()
    if not raw:
        log_error("tool argument cannot be empty")
        raise SystemExit(1)
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        log_error("tool argument must contain at least one tool id")
        raise SystemExit(1)
    unknown = [p for p in parts if p not in REGISTRY]
    if unknown:
        log_error(f"Unknown tool(s): {', '.join(unknown)}")
        log_info(f"Available tools: {', '.join(sorted(REGISTRY))}")
        raise SystemExit(1)
    if len(set(parts)) != len(parts):
        log_error(f"Duplicate tool ids in: {raw!r}")
        raise SystemExit(1)
    return parts


def _install_one_tool(
    tool: str,
    *,
    with_core: bool,
    with_orchestration: bool,
    force: bool,
    language: str | None,
    strict_archived: bool,
) -> None:
    """Per-tool install body. Raises whatever ``deploy_all_resources`` or
    ``deploy_core`` raise; the caller in ``install`` catches and records."""
    deploy_all_resources(tool, force=False, with_orchestration=with_orchestration)

    if with_core:
        effective_language = _resolve_language(language)
        deploy_core(
            tool,
            force=force,
            language=effective_language,
            strict_archived=strict_archived,
        )


def _summarise(
    label: str,
    successes: list[str],
    failures: list[tuple[str, int, str]],
) -> None:
    """Print a per-tool summary; raise SystemExit on any failure.

    Single-tool calls (1 target total) get NO summary line, and the exit
    code is whatever the underlying failure raised (``SystemExit(code)``
    for refusal paths like ``deploy_core``, ``1`` for unexpected
    exceptions) — preserves byte-identical v1.9.x behaviour of letting
    the per-tool error reach the caller.

    Multi-tool calls collapse all failures to ``SystemExit(1)`` because
    a single composite code must summarise many heterogeneous tool
    outcomes (the partial-failure contract pinned by
    ``tests/unit/test_install_multi.py``).
    """
    total = len(successes) + len(failures)
    if total <= 1:
        if failures:
            _, exit_code, _ = failures[0]
            raise SystemExit(exit_code if exit_code != 0 else 1)
        return
    console.print()
    if failures:
        log_error(
            f"{label} summary: {len(successes)} succeeded, {len(failures)} failed"
        )
        for tid, _, err in failures:
            console.print(f"  [red]x[/red] {tid}: {err}")
        for tid in successes:
            console.print(f"  [green]v[/green] {tid}")
        raise SystemExit(1)
    log_success(f"{label} summary: {len(successes)} succeeded")
    for tid in successes:
        console.print(f"  [green]v[/green] {tid}")


def _update_one_tool(
    tool: str,
    *,
    with_core: bool,
    with_orchestration: bool,
    force: bool,
    language: str | None,
    strict_archived: bool,
) -> None:
    """Per-tool update body: purge stale, redeploy, optionally core, reconcile."""
    target_dir = Path.cwd() / REGISTRY[tool].skills_dir
    target_dir.mkdir(parents=True, exist_ok=True)

    # 1. Purge stale extended ``osx-*`` resources before the forced redeploy
    #    so the resulting tree exactly matches the current source manifest.
    osx_keep = _expected_extension_names(tool, with_orchestration)
    removed = purge_managed_resources(
        target_dir, tool, keep_names=osx_keep, prefixes=("osx-",)
    )
    if removed:
        log_info(f"Purged {removed} stale osx-* resource(s)")

    deploy_all_resources(tool, force=True, with_orchestration=with_orchestration)

    if with_orchestration:
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
        #    that is no longer generated upstream is removed here. The
        #    nested-orphan sweep and identical-backup purge now live in
        #    ``deploy_core`` itself so both ``install --with-core`` and
        #    ``update --with-core`` paths benefit.
        core_keep = _core_keep_set(target_dir)
        removed = purge_managed_resources(
            target_dir,
            tool,
            keep_names=core_keep,
            prefixes=("osc-",),
        )
        if removed:
            log_info(f"Purged {removed} stale osc-* resource(s)")

    _validate_target_after_deploy(target_dir)


@app.command(
    "install",
    help="Deploy extended resources (skills, commands, agents, scripts) to one or more tool directories.",
)
def install(
    tool: str = typer.Argument(
        ...,
        help=(
            "Target tool id, or comma-separated list (e.g. 'opencode,claude'). "
            "Registered: " + ", ".join(sorted(REGISTRY)) + "."
        ),
    ),
    with_core: bool = typer.Option(
        False, "-c", "--with-core", help="Also deploy core OpenSpec skills"
    ),
    with_orchestration: bool = typer.Option(
        False,
        "-o",
        "--with-orchestration/--no-with-orchestration",
        help=(
            "Also deploy the 7-phase orchestration workflow resources "
            "(phase commands, agents, workflow skill). Defaults to off; "
            "pass --with-orchestration (or -o) to enable the orchestrator."
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
    targets = _parse_tool_target(tool)
    successes: list[str] = []
    failures: list[tuple[str, int, str]] = []

    for target in targets:
        try:
            _install_one_tool(
                target,
                with_core=with_core,
                with_orchestration=with_orchestration,
                force=force,
                language=language,
                strict_archived=strict_archived,
            )
            successes.append(target)
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 1
            failures.append((target, code, f"exit {code}"))
            log_error(f"install {target} failed (exit {code})")
        except Exception as e:  # noqa: BLE001 — per-tool isolation
            failures.append((target, 1, str(e)))
            log_error(f"install {target} failed: {e}")

    # Global post-deploy hooks (idempotent — see update_gitignore)
    if with_orchestration and successes:
        update_gitignore()

    # Per-tool validation (only for tools that succeeded; failed tools
    # didn't deploy anything to validate).
    for target in successes:
        target_dir = Path.cwd() / REGISTRY[target].skills_dir
        _validate_target_after_deploy(target_dir)

    _summarise("install", successes, failures)


def _expected_extension_names(tool: str, with_orchestration: bool) -> set[str]:
    """Return the set of extended ``osx-*`` resource names that the current
    source manifest will deploy for ``tool``.

    The set mirrors ``deploy_all_resources`` filtering: autonomous names are
    included only when ``with_orchestration`` is set. Reads both the orchestrator
    and skills side manifests (Phase 5 split) from the single canonical
    source tree and returns their union.
    """
    expected: set[str] = set()
    for source_dir in (
        get_resources_dir() / "canonical",
        get_skills_resources_dir() / "canonical",
    ):
        manifest_path = source_dir / "manifest.toml"
        if not manifest_path.is_file():
            continue
        data = toml.loads(manifest_path.read_text())
        for entries in data.get("resources", {}).values():
            if not isinstance(entries, dict):
                continue
            for name in entries:
                if not with_orchestration and name in ORCHESTRATION_RESOURCE_NAMES:
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


_CORE_ORPHAN_PREFIXES = ("openspec-", "opsx-")

_BACKUP_SUFFIX = ".user-backup-"


def _purge_identical_backups(target_dir: Path) -> int:
    """Remove ``*.user-backup-*`` files whose bytes match the
    corresponding non-backup sibling in the same directory.

    Walks ``target_dir/skills/`` (recursively, since a ``SKILL.md`` can
    sit next to ``SKILL.md.user-backup-*``) and ``target_dir/commands/``
    (only top-level ``*.md`` for the OpenCode adapter — command files
    are flat there). User-authored backups (mismatched bytes) survive
    untouched; backups that match the wrapper's current output byte-for-
    byte are deleted as redundant.

    Returns the number of backups removed. Idempotent: a no-op when no
    backups exist or all backups are user-authored.
    """
    removed = 0

    skills_dir = target_dir / "skills"
    if skills_dir.is_dir():
        for backup in skills_dir.rglob(f"*{_BACKUP_SUFFIX}*"):
            if not backup.is_file():
                continue
            original = backup.with_name(backup.name.split(_BACKUP_SUFFIX, 1)[0])
            if not original.is_file():
                continue
            if backup.read_bytes() == original.read_bytes():
                backup.unlink()
                removed += 1

    commands_dir = target_dir / "commands"
    if commands_dir.is_dir():
        for backup in commands_dir.glob(f"*{_BACKUP_SUFFIX}*"):
            if not backup.is_file():
                continue
            original = backup.with_name(backup.name.split(_BACKUP_SUFFIX, 1)[0])
            if not original.is_file():
                continue
            if backup.read_bytes() == original.read_bytes():
                backup.unlink()
                removed += 1

    return removed


def _purge_nested_core_orphans(target_dir: Path) -> int:
    """Remove ``openspec-*`` / ``opsx-*`` dirs nested inside ``osc-*`` dirs.

    Runs from ``deploy_core`` (covers both ``install --with-core`` and
    ``update --with-core`` paths) immediately after
    ``rename_core_resources``.

    When ``openspec init`` runs against a tree that already contains a
    renamed ``osc-X/`` skill, the upstream CLI may emit
    ``osc-X/openspec-X/SKILL.md`` instead of overwriting at the flat
    level. The renamer's merge branch (``dest_dir.exists()``) handles the
    flat-level collision but does not recurse, so the nested ``openspec-X/``
    dir survives every subsequent install.

    This pass scans every ``osc-*`` skill dir and command subdir, then
    removes any descendant whose name starts with ``openspec-`` or
    ``opsx-``. User-authored nested dirs with other names are left alone.

    Returns the number of orphan entries removed (dirs + files).
    """
    removed = 0

    skills_dir = target_dir / "skills"
    if skills_dir.is_dir():
        for entry in skills_dir.iterdir():
            if not (entry.is_dir() and entry.name.startswith("osc-")):
                continue
            for orphan in entry.rglob("*"):
                if not orphan.name.startswith(_CORE_ORPHAN_PREFIXES):
                    continue
                if orphan.is_dir() and not any(orphan.iterdir()):
                    orphan.rmdir()
                    removed += 1
                    log_info(f"Removed empty nested core orphan: {orphan}")
                elif orphan.is_dir():
                    shutil.rmtree(orphan)
                    removed += 1
                    log_info(f"Removed nested core orphan dir: {orphan}")
                elif orphan.is_file() or orphan.is_symlink():
                    orphan.unlink()
                    removed += 1
                    log_info(f"Removed nested core orphan file: {orphan}")

    commands_dir = target_dir / "commands"
    if commands_dir.is_dir():
        osc_subdir = commands_dir / "osc"
        if osc_subdir.is_dir():
            for orphan in osc_subdir.rglob("*"):
                if not orphan.name.startswith(_CORE_ORPHAN_PREFIXES):
                    continue
                if orphan.is_dir() and not any(orphan.iterdir()):
                    orphan.rmdir()
                    removed += 1
                elif orphan.is_dir():
                    shutil.rmtree(orphan)
                    removed += 1
                    log_info(f"Removed nested core orphan dir: {orphan}")
                elif orphan.is_file() or orphan.is_symlink():
                    orphan.unlink()
                    removed += 1

    return removed


@app.command(
    "update",
    help="Force reinstall all resources (same as install but always overwrites)",
)
def update(
    tool: str = typer.Argument(
        ...,
        help=(
            "Target tool id, or comma-separated list (e.g. 'opencode,claude'). "
            "Registered: " + ", ".join(sorted(REGISTRY)) + "."
        ),
    ),
    with_core: bool = typer.Option(
        False, "-c", "--with-core", help="Also deploy core OpenSpec skills"
    ),
    with_orchestration: bool = typer.Option(
        False,
        "-o",
        "--with-orchestration/--no-with-orchestration",
        help=(
            "Refresh the 7-phase orchestration workflow resources "
            "(phase commands, agents, workflow skill). Defaults to off; "
            "pass --with-orchestration (or -o) to refresh them."
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
    targets = _parse_tool_target(tool)
    successes: list[str] = []
    failures: list[tuple[str, int, str]] = []

    for target in targets:
        try:
            _update_one_tool(
                target,
                with_core=with_core,
                with_orchestration=with_orchestration,
                force=force,
                language=language,
                strict_archived=strict_archived,
            )
            successes.append(target)
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 1
            failures.append((target, code, f"exit {code}"))
            log_error(f"update {target} failed (exit {code})")
        except Exception as e:  # noqa: BLE001 — per-tool isolation
            failures.append((target, 1, str(e)))
            log_error(f"update {target} failed: {e}")

    _summarise("update", successes, failures)


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
