#!/usr/bin/env python3
"""
Phase 1D unit tests for registry-driven ``lib/osx.py`` helpers.

Phases 1A–1C landed the ``REGISTRY`` adapter abstraction and rewired
``cli.py``, ``runner.py``, and ``engine.py`` to read from it. Phase 1D
generalizes the remaining consumers in ``source/lib/osx.py``:

- ``detect_platform(project_root)``
- ``skills_dir(project_root)``
- ``commands_dir(project_root)``
- ``_load_manifest(project_root)``
- ``_command_resolved_for_phase(root, platform, cmd_name)``
- ``validate_commands(project_root)`` (agent-file check)

These tests pin the byte-identical behavior for the two shipped
adapters (opencode, claude) and verify the dispatch is purely
adapter-driven via a synthetic cursor-shaped adapter.

No filesystem side effects outside ``tmp_path``. No subprocess calls
to the built binary — exercise Python modules directly.
"""

from __future__ import annotations

import toml
import pytest

from source.lib import osx
from source.tools import REGISTRY, ToolAdapter


pytestmark = pytest.mark.unit


@pytest.fixture
def cursor_adapter(monkeypatch):
    """Register a cursor-shaped synthetic adapter for the test, restore after.

    Mirrors the canonical Cursor adapter from upstream OpenSpec
    (``runner_kind="generic_print"``, ``commands_style="flat"``,
    ``has_agents_dir=False``). The fixture is module-scoped per test
    invocation so the registry mutation is reverted at teardown."""
    synthetic = ToolAdapter(
        tool_id="cursor",
        skills_dir=".cursor",
        commands_dir="commands",
        commands_style="flat",
        commands_ext="md",
        slash_prefix="osx-",
        skill_prefix="/",
        cross_ref_prefix="",
        ask_tool="AskUserQuestion",
        install_hint=(
            "Run `openspec-extended install cursor` after installing the Cursor CLI"
        ),
        runner_binary="cursor",
        runner_kind="generic_print",
        runner_args=(),
        has_agents_dir=False,
        agent_field_transform=None,
        inject_name_in_skill_mirror=False,
        cmd_filename_strip_prefix=None,
        frontmatter_extras={},
        docs_file="AGENTS.md",
        tool_name="Cursor",
        detect_paths=(".cursor",),
    )
    monkeypatch.setitem(REGISTRY, "cursor", synthetic)
    yield synthetic


# ---------------------------------------------------------------------------
# _load_manifest: registry-driven path resolution
# ---------------------------------------------------------------------------


class TestLoadManifestDerivesFromAdapter:
    """``_load_manifest`` reads from ``REGISTRY[detect_platform].skills_dir``.

    Phase 1D collapsed the ``if platform == "opencode" / elif "claude"``
    ladder into a single registry-driven path computation. The two
    shipped adapters must produce the legacy path layout; a synthetic
    cursor adapter must produce the cursor layout.
    """

    def test_loads_manifest_at_skills_dir_for_each_shipped_adapter(
        self, tmp_path: pytest.TempPathFactory
    ):
        for adapter in REGISTRY.values():
            manifest_dir = tmp_path / adapter.skills_dir
            manifest_dir.mkdir()
            (manifest_dir / "manifest.toml").write_text(
                '[resources.skills]\n[resources.skills.osx-x]\nversion = "0.1.0"\n'
            )

            manifest = osx._load_manifest(tmp_path)
            assert manifest is not None, (
                f"{adapter.tool_id}: _load_manifest returned None despite "
                f"a manifest at <tmp>/{adapter.skills_dir}/manifest.toml"
            )
            assert "osx-x" in manifest["resources"]["skills"], (
                f"{adapter.tool_id}: 'osx-x' skill missing from merged manifest"
            )

    def test_loads_skills_manifest_when_orchestrator_missing(self, tmp_path):
        adapter = REGISTRY["opencode"]
        manifest_dir = tmp_path / adapter.skills_dir
        manifest_dir.mkdir()
        (manifest_dir / "skills-manifest.toml").write_text(
            '[resources.skills]\n[resources.skills.osx-y]\nversion = "0.2.0"\n'
        )

        manifest = osx._load_manifest(tmp_path)
        assert manifest is not None
        assert "osx-y" in manifest["resources"]["skills"]

    def test_merges_both_manifests_into_single_resources_view(self, tmp_path):
        adapter = REGISTRY["opencode"]
        manifest_dir = tmp_path / adapter.skills_dir
        manifest_dir.mkdir()
        (manifest_dir / "manifest.toml").write_text(
            '[resources.skills]\n[resources.skills.osx-a]\nversion = "0.1.0"\n'
        )
        (manifest_dir / "skills-manifest.toml").write_text(
            '[resources.skills]\n[resources.skills.osx-b]\nversion = "0.1.0"\n'
        )

        manifest = osx._load_manifest(tmp_path)
        assert manifest is not None
        skills = manifest["resources"]["skills"]
        assert "osx-a" in skills
        assert "osx-b" in skills

    def test_returns_none_for_unknown_platform(self, tmp_path, monkeypatch):
        """Defensive: if ``detect_platform`` somehow returns an
        unregistered id, ``_load_manifest`` returns ``None`` rather
        than raising ``KeyError``. In practice ``detect_platform``
        always returns a registered id, so this is the back-stop."""
        monkeypatch.setattr(osx, "detect_platform", lambda _: "not-a-real-tool")
        assert osx._load_manifest(tmp_path) is None

    def test_returns_none_when_no_manifests_present(self, tmp_path):
        """No manifest files under any adapter's skills_dir."""
        assert osx._load_manifest(tmp_path) is None


# ---------------------------------------------------------------------------
# _command_resolved_for_phase: commands_style-driven resolution
# ---------------------------------------------------------------------------


class TestCommandResolvedForPhase:
    """``_command_resolved_for_phase`` accepts both the legacy
    ``<target>/<commands_dir>/<name>.md`` form and the modern
    ``<target>/skills/<name>/SKILL.md`` form when the adapter's
    ``commands_style`` is ``"namespaced-with-skill-mirror"`` (Claude
    today). Flat adapters (opencode today) only resolve the legacy
    command file.
    """

    def test_opencode_layout_resolves_flat_command_file(self, tmp_path):
        adapter = REGISTRY["opencode"]
        (tmp_path / adapter.skills_dir).mkdir(parents=True)
        cmd_path = tmp_path / adapter.skills_dir / "commands" / "osx-phase0.md"
        cmd_path.parent.mkdir(parents=True, exist_ok=True)
        cmd_path.write_text("# osx-phase0")

        resolved = osx._command_resolved_for_phase(tmp_path, "opencode", "osx-phase0")
        assert resolved == cmd_path

    def test_claude_layout_resolves_namespaced_legacy_file(self, tmp_path):
        adapter = REGISTRY["claude"]
        (tmp_path / adapter.skills_dir).mkdir(parents=True)
        # Claude's commands_dir is "commands/osx" → on-disk path is
        # .claude/commands/osx/phase0.md (prefix stripped)
        cmd_path = tmp_path / adapter.skills_dir / "commands" / "osx" / "phase0.md"
        cmd_path.parent.mkdir(parents=True, exist_ok=True)
        cmd_path.write_text("# osx-phase0")

        resolved = osx._command_resolved_for_phase(tmp_path, "claude", "osx-phase0")
        assert resolved == cmd_path

    def test_claude_layout_resolves_modern_skill_mirror(self, tmp_path):
        """Modern Claude skill form (no legacy command file)."""
        adapter = REGISTRY["claude"]
        (tmp_path / adapter.skills_dir).mkdir(parents=True)
        skill_path = (
            tmp_path / adapter.skills_dir / "skills" / "osx-phase0" / "SKILL.md"
        )
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text("---\nname: osx-phase0\n---\n# body")

        resolved = osx._command_resolved_for_phase(tmp_path, "claude", "osx-phase0")
        assert resolved == skill_path

    def test_flat_layout_skips_skill_mirror_check(self, tmp_path):
        """Opencode is ``flat`` — even if a stray skills/<id>/SKILL.md
        exists, the resolver returns the command file (commands-style
        drives the dispatch, not filesystem coincidences)."""
        adapter = REGISTRY["opencode"]
        (tmp_path / adapter.skills_dir).mkdir(parents=True)
        cmd_path = tmp_path / adapter.skills_dir / "commands" / "osx-phase0.md"
        cmd_path.parent.mkdir(parents=True, exist_ok=True)
        cmd_path.write_text("# osx-phase0")
        skill_path = (
            tmp_path / adapter.skills_dir / "skills" / "osx-phase0" / "SKILL.md"
        )
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        skill_path.write_text("stray")

        resolved = osx._command_resolved_for_phase(tmp_path, "opencode", "osx-phase0")
        assert resolved == cmd_path

    def test_returns_none_when_neither_form_present(self, tmp_path):
        adapter = REGISTRY["opencode"]
        (tmp_path / adapter.skills_dir).mkdir(parents=True)
        assert (
            osx._command_resolved_for_phase(tmp_path, "opencode", "osx-phase0")
            is None
        )

    def test_opencode_prefix_preserved_in_deployed_filename(self, tmp_path):
        """Flat adapters keep the ``osx-`` prefix in the on-disk
        filename; only namespaced adapters strip it."""
        adapter = REGISTRY["opencode"]
        (tmp_path / adapter.skills_dir).mkdir(parents=True)
        # The deployed filename on opencode keeps the prefix:
        # .opencode/commands/osx-phase0.md
        kept_path = tmp_path / adapter.skills_dir / "commands" / "osx-phase0.md"
        kept_path.parent.mkdir(parents=True, exist_ok=True)
        kept_path.write_text("# body")
        # The stripped filename would be: .opencode/commands/phase0.md
        # (which we deliberately do NOT create)

        resolved = osx._command_resolved_for_phase(tmp_path, "opencode", "osx-phase0")
        assert resolved == kept_path


# ---------------------------------------------------------------------------
# validate_commands: agent-file check driven by has_agents_dir
# ---------------------------------------------------------------------------


class TestValidateCommandsAgentCheck:
    """The agents-dir check at the end of ``validate_commands`` is
    driven by ``adapter.has_agents_dir``. ``opencode`` exposes an
    on-disk agent dispatch model; ``claude`` does not (and neither
    do most future adapters). Phase 1D collapses the
    ``if platform == "opencode"`` ladder into a registry-driven check.
    """

    def _populate_minimal_change(self, tmp_path, platform):
        """Drop the minimum resources ``validate_commands`` needs."""
        adapter = REGISTRY[platform]
        # Skills root must exist (otherwise validate_skills fails first;
        # here we only call validate_commands, which doesn't need skills).
        # Manifest under <skills_dir>/manifest.toml
        manifest_dir = tmp_path / adapter.skills_dir
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_lines = ["[resources.commands]"]
        for phase in osx.PHASES:
            cmd_name = osx.PHASE_COMMANDS.get(phase)
            if cmd_name:
                manifest_lines.append(f'[resources.commands.{cmd_name}]')
                manifest_lines.append('version = "0.1.0"')
        (manifest_dir / "manifest.toml").write_text("\n".join(manifest_lines) + "\n")

    def test_opencode_project_reports_missing_agent(self, tmp_path):
        """opencode adapter has has_agents_dir=True; missing agent
        file is reported as a validation error."""
        self._populate_minimal_change(tmp_path, "opencode")
        # Skills dir must exist for validate_skills gate (we don't
        # call it here, but the manifest is enough for validate_commands).
        (tmp_path / ".opencode" / "skills").mkdir(parents=True, exist_ok=True)

        result = osx.validate_commands(tmp_path)
        assert result["valid"] is False, result
        agent_errors = [
            e for e in result["errors"] if e.get("check") == "agents"
        ]
        assert agent_errors, (
            "opencode project should report missing-agent errors; "
            f"got {result['errors']!r}"
        )
        # Phase0's agent is osx-analyzer — its missing file is the
        # canonical first error.
        assert any("osx-analyzer" in e["message"] for e in agent_errors), (
            f"expected osx-analyzer in agent errors; got {agent_errors!r}"
        )

    def test_claude_project_skips_agent_check(self, tmp_path):
        """claude adapter has has_agents_dir=False; no agent errors
        are reported even when no agents/<name>.md files exist."""
        self._populate_minimal_change(tmp_path, "claude")
        (tmp_path / ".claude" / "skills").mkdir(parents=True, exist_ok=True)

        result = osx.validate_commands(tmp_path)
        agent_errors = [
            e for e in result["errors"] if e.get("check") == "agents"
        ]
        assert not agent_errors, (
            "claude project must not report agent-check errors "
            f"(has_agents_dir=False); got {agent_errors!r}"
        )

    def test_synthetic_cursor_adapter_skips_agent_check(self, tmp_path):
        """A synthetic cursor-shaped adapter with has_agents_dir=False
        also skips the agent check."""
        adapter = ToolAdapter(
            tool_id="cursor",
            skills_dir=".cursor",
            commands_dir="commands",
            commands_style="flat",
            commands_ext="md",
            slash_prefix="osx-",
            skill_prefix="/",
            runner_binary="cursor",
            runner_kind="generic_print",
            has_agents_dir=False,
            agent_field_transform=None,
            inject_name_in_skill_mirror=False,
            cmd_filename_strip_prefix=None,
            docs_file="AGENTS.md",
            tool_name="Cursor",
            detect_paths=(".cursor",),
        )
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setitem(REGISTRY, "cursor", adapter)
        try:
            self._populate_minimal_change(tmp_path, "cursor")
            (tmp_path / ".cursor" / "skills").mkdir(parents=True, exist_ok=True)

            result = osx.validate_commands(tmp_path)
            agent_errors = [
                e for e in result["errors"] if e.get("check") == "agents"
            ]
            assert not agent_errors, (
                f"cursor adapter must not report agent-check errors; "
                f"got {agent_errors!r}"
            )
        finally:
            monkeypatch.undo()


# ---------------------------------------------------------------------------
# _install_hint: platform-agnostic template
# ---------------------------------------------------------------------------


class TestInstallHint:
    """``_install_hint`` reads ``REGISTRY[platform].install_hint`` for
    the requested platform. Both shipped adapters declare a hint that
    follows the same template — names the install command and the
    tool's display name — so the byte-equivalent test below locks the
    shape.

    L1.3 moved the hint off a hand-rolled ``f"Re-run: openspec-extended
    install {platform} --with-orchestration"`` template and onto the
    adapter's ``install_hint`` field. Unknown platforms still hit a
    KeyError at REGISTRY lookup — the helper is no longer tolerant
    of an unregistered id, which the engine's callers already guard
    via ``detect_platform``.
    """

    @pytest.mark.parametrize("tool_id", ["opencode", "claude", "cursor"])
    def test_hint_names_each_shipped_platform(self, tool_id, cursor_adapter):
        hint = osx._install_hint(tool_id)
        expected = REGISTRY[tool_id].install_hint
        assert hint == expected, (
            f"{tool_id}: hint {hint!r} did not match adapter.install_hint {expected!r}"
        )

    def test_hint_for_unknown_platform_raises(self):
        """An unknown platform id raises ``KeyError`` (REGISTRY lookup
        fails). Callers upstream always go through ``detect_platform``
        which guarantees a registered id, so the helper stays strict."""
        with pytest.raises(KeyError):
            osx._install_hint("not-a-real-tool")


# ---------------------------------------------------------------------------
# Synthetic adapter exercises the whole stack end-to-end
# ---------------------------------------------------------------------------


class TestSyntheticCursorAdapterDrivesAllLibHelpers:
    """Drop a synthetic cursor-shaped adapter into ``REGISTRY`` and
    verify every Phase-1D lib helper drives off it. The synthetic
    adapter is cursor-shaped (flat commands, no agents) and the test
    is the proof that no helper hardcodes ``"opencode"`` or
    ``"claude"`` internally — adding a new adapter is a one-line
    registry edit, not a lib/osx.py edit.
    """

    @pytest.fixture
    def cursor_marker(self, tmp_path):
        (tmp_path / ".cursor").mkdir()
        return tmp_path

    @pytest.fixture
    def monkeypatch_cursor(self):
        """Register a cursor-shaped adapter for the test, restore after."""
        synthetic = ToolAdapter(
            tool_id="cursor",
            skills_dir=".cursor",
            commands_dir="commands",
            commands_style="flat",
            commands_ext="md",
            slash_prefix="osx-",
            skill_prefix="/",
            runner_binary="cursor",
            runner_kind="generic_print",
            has_agents_dir=False,
            agent_field_transform=None,
            inject_name_in_skill_mirror=False,
            cmd_filename_strip_prefix=None,
            docs_file="AGENTS.md",
            tool_name="Cursor",
            detect_paths=(".cursor",),
        )
        monkeypatch = pytest.MonkeyPatch()
        monkeypatch.setitem(REGISTRY, "cursor", synthetic)
        yield synthetic
        monkeypatch.undo()

    def test_detect_platform_returns_cursor(self, cursor_marker, monkeypatch_cursor):
        assert osx.detect_platform(cursor_marker) == "cursor"

    def test_skills_dir_returns_cursor_skills(self, cursor_marker, monkeypatch_cursor):
        assert osx.skills_dir(cursor_marker) == cursor_marker / ".cursor" / "skills"

    def test_commands_dir_returns_cursor_commands(self, cursor_marker, monkeypatch_cursor):
        assert osx.commands_dir(cursor_marker) == cursor_marker / ".cursor" / "commands"

    def test_load_manifest_finds_cursor_layout(self, cursor_marker, monkeypatch_cursor):
        manifest_dir = cursor_marker / ".cursor"
        (manifest_dir / "manifest.toml").write_text(
            '[resources.skills]\n[resources.skills.osx-cursor-skill]\nversion = "0.1.0"\n'
        )
        manifest = osx._load_manifest(cursor_marker)
        assert manifest is not None
        assert "osx-cursor-skill" in manifest["resources"]["skills"]

    def test_command_resolved_uses_cursor_flat_layout(
        self, cursor_marker, monkeypatch_cursor
    ):
        cmd_path = cursor_marker / ".cursor" / "commands" / "osx-phase0.md"
        cmd_path.parent.mkdir(parents=True, exist_ok=True)
        cmd_path.write_text("# body")
        resolved = osx._command_resolved_for_phase(
            cursor_marker, "cursor", "osx-phase0"
        )
        assert resolved == cmd_path

    def test_install_hint_names_cursor(self, cursor_marker, monkeypatch_cursor):
        hint = osx._install_hint("cursor")
        assert hint == monkeypatch_cursor.install_hint
