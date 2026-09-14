#!/usr/bin/env python3
"""Phase 1B byte-equality tests for cli.py deploy / purge consumers.

Before Phase 1B, ``deploy_commands``, ``deploy_skills``, ``deploy_agents``,
``purge_managed_resources``, and ``validate_deployment`` branched on the
literal ``tool`` string (``if tool == "opencode":`` / ``if tool !=
"claude":``). Phase 1B replaces those comparisons with adapter-driven
dispatch (``REGISTRY[tool].commands_style`` and ``has_agents_dir``).

These tests pin the same byte-output that the pre-1B literal-id branches
produced. They're the regression net: any divergence between the literal
behaviour and the registry-routed behaviour fails here before reaching a
user-facing test.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from source.cli import (
    deploy_agents,
    deploy_commands,
    deploy_skills,
    get_resources_dir,
    get_skills_resources_dir,
    purge_managed_resources,
    validate_deployment,
)
from source.tools import REGISTRY, ToolAdapter


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# deploy_skills
# ---------------------------------------------------------------------------


class TestDeploySkillsReproducesRegistryLayout:
    """``deploy_skills`` writes to ``<target>/skills/<name>`` for every
    adapter; per-adapter differences are token substitution only, not
    layout."""

    @pytest.fixture
    def oc_source(self) -> Path:
        return get_resources_dir() / "canonical" / "skills"

    @pytest.fixture
    def sk_source(self) -> Path:
        return get_skills_resources_dir() / "canonical" / "skills"

    @pytest.mark.parametrize("tool_id", ["opencode", "claude"])
    def test_writes_skill_under_target_skills(self, tmp_path, tool_id, oc_source):
        adapter = REGISTRY[tool_id]
        target = tmp_path / adapter.skills_dir
        target.mkdir(parents=True)
        deploy_skills(oc_source, target, "osx-workflow", tool=tool_id)

        skill_dir = target / "skills" / "osx-workflow"
        assert skill_dir.is_dir(), (
            f"{tool_id}: skill directory not written under target/skills/"
        )
        assert (skill_dir / "SKILL.md").is_file(), (
            f"{tool_id}: SKILL.md missing from deployed skill"
        )

    @pytest.mark.parametrize("tool_id", ["opencode", "claude"])
    def test_token_substitution_matches_adapter(
        self, tmp_path, tool_id
    ):
        """For every shipped adapter, ``{{PLATFORM_DIR}}`` and
        ``{{CMD_PREFIX}}`` (which appear in ``osx-review``'s body
        and references) must render to the adapter's ``skills_dir``
        and ``slash_prefix`` respectively.

        Uses the skills-side command source for ``osx-review``
        because its body explicitly references ``{{PLATFORM_DIR}}``.
        The orchestrator-side ``osx-workflow`` skill has tool-agnostic
        prose, so its tokens resolve to the same value without being
        visible in the body."""
        from source.cli import get_skills_resources_dir

        cmd_source = get_skills_resources_dir() / "canonical" / "commands"
        adapter = REGISTRY[tool_id]
        target = tmp_path / adapter.skills_dir
        target.mkdir(parents=True)
        deploy_commands(cmd_source, target, "osx-review", tool=tool_id)

        # Opencode: command file lives under commands/. Claude: dual-emit
        # to skills/<name>/SKILL.md as well — assert against whichever
        # form the adapter dispatches.
        if adapter.commands_style == "flat":
            rendered_path = target / "commands" / "osx-review.md"
        else:
            rendered_path = target / "skills" / "osx-review" / "SKILL.md"

        rendered = rendered_path.read_text()
        assert "{{PLATFORM_DIR}}" not in rendered, (
            f"{tool_id}: leftover {{{{PLATFORM_DIR}}}} after substitution"
        )
        assert adapter.skills_dir in rendered, (
            f"{tool_id}: skills_dir {adapter.skills_dir!r} not found in "
            f"rendered body (PLATFORM_DIR token mis-routed)"
        )
        assert adapter.slash_prefix in rendered, (
            f"{tool_id}: slash_prefix {adapter.slash_prefix!r} not in "
            f"rendered body (CMD_PREFIX token mis-routed)"
        )


# ---------------------------------------------------------------------------
# deploy_commands — single-emit flat vs dual-emit namespaced-with-skill-mirror
# ---------------------------------------------------------------------------


class TestDeployCommandsRoutesByCommandsStyle:
    """``deploy_commands`` branches on ``REGISTRY[tool].commands_style``:

    - ``flat`` (opencode): only the command file is written under
      ``<target>/commands/<name>.<ext>``.
    - ``namespaced-with-skill-mirror`` (claude): legacy command file
      plus a modern ``<target>/skills/<name>/SKILL.md`` skill mirror.
    """

    @pytest.fixture
    def source(self) -> Path:
        return get_skills_resources_dir() / "canonical" / "commands"

    def test_opencode_single_emits_flat(self, tmp_path, source):
        target = tmp_path / REGISTRY["opencode"].skills_dir
        target.mkdir(parents=True)
        deploy_commands(source, target, "osx-review", tool="opencode")

        cmd_file = target / "commands" / "osx-review.md"
        skill_mirror = target / "skills" / "osx-review" / "SKILL.md"

        assert cmd_file.is_file(), "opencode: command file missing"
        assert not skill_mirror.exists(), (
            "opencode: dual-emit skill mirror written (must not exist for "
            "commands_style='flat')"
        )

    def test_claude_dual_emits_legacy_and_modern(self, tmp_path, source):
        target = tmp_path / REGISTRY["claude"].skills_dir
        target.mkdir(parents=True)
        deploy_commands(source, target, "osx-review", tool="claude")

        # Phase 2A: claude's legacy form is nested under ``commands/osx/``
        # with the ``osx-`` prefix stripped (the deploy path is now driven
        # by ``adapter.commands_dir`` + ``adapter.cmd_filename_strip_prefix``).
        cmd_file = target / "commands" / "osx" / "review.md"
        skill_mirror = target / "skills" / "osx-review" / "SKILL.md"

        assert cmd_file.is_file(), "claude: legacy command file missing"
        assert skill_mirror.is_file(), (
            "claude: modern skill mirror missing "
            "(commands_style='namespaced-with-skill-mirror')"
        )

    def test_claude_skill_mirror_carries_claude_token_values(
        self, tmp_path, source
    ):
        """The dual-emit skill must render tokens for claude, not opencode.

        ``osx-review``'s source uses ``/{{CMD_PREFIX}}review`` for the
        slash-command prose; after substitution the rendered text must
        carry ``/osx:review`` (claude form) and not the literal ``osx-``
        prefix or any unresolved ``{{...}}`` placeholder."""
        target = tmp_path / REGISTRY["claude"].skills_dir
        target.mkdir(parents=True)
        deploy_commands(source, target, "osx-review", tool="claude")

        skill_md = (target / "skills" / "osx-review" / "SKILL.md").read_text()

        # No leftover tokens — the substitution table populated by
        # ``_adapter_tokens`` includes all 5 documented keys.
        for token in (
            "{{CMD_PREFIX}}",
            "{{TOOL_NAME}}",
            "{{DOCS_FILE}}",
            "{{PLATFORM_DIR}}",
            "{{ASK_TOOL}}",
        ):
            assert token not in skill_md, (
                f"claude: leftover {token} after substitution"
            )

        # The rendered prose for claude must carry the claude-specific
        # slash form ``/osx:review`` (the slash-command invocation).
        # Skill-directory references like ``/osx-review-artifacts`` are
        # path literals — they don't go through ``CMD_PREFIX``
        # substitution — and we explicitly do not assert about them.
        assert "/osx:review" in skill_md, (
            "claude: rendered slash-command prose missing /osx:review "
            "(CMD_PREFIX did not render to claude's slash form)"
        )
        # Make sure none of the slash-command lines carries the
        # opencode-specific dash prefix: scan every line that *starts
        # with* ``/osx`` and check it uses the colon.
        for line in skill_md.splitlines():
            stripped = line.lstrip()
            if stripped.startswith("/osx-"):
                # Skill-directory paths inside backticks are fine; only
                # plain (un-backticked) ``/osx-*`` is a problem.
                if "`" in stripped.split("/osx-", 1)[0] or stripped.count(
                    "`"
                ) % 2 == 0:
                    pytest.fail(
                        f"claude: opencode slash prefix /osx-* leaked: {line!r}"
                    )


# ---------------------------------------------------------------------------
# deploy_agents
# ---------------------------------------------------------------------------


class TestDeployAgentsRoutesByHasAgentsDir:
    """``deploy_agents`` writes to ``<target>/agents/<name>.md`` for
    every adapter. Per-adapter differences are token substitution only;
    the `has_agents_dir` flag governs whether the platform exposes the
    directory at all (validators later), not whether the deploy
    succeeds. Deploy-time bypass is not exposed today — Phase 1E will
    add the ``--agents`` policy knob."""

    @pytest.fixture
    def source(self) -> Path:
        return get_resources_dir() / "canonical" / "agents"

    @pytest.mark.parametrize("tool_id", ["opencode", "claude"])
    def test_writes_agent_md(self, tmp_path, tool_id, source):
        adapter = REGISTRY[tool_id]
        target = tmp_path / adapter.skills_dir
        target.mkdir(parents=True)
        deploy_agents(source, target, "osx-analyzer", tool=tool_id)

        agent_md = target / "agents" / "osx-analyzer.md"
        assert agent_md.is_file(), f"{tool_id}: agent file missing"


# ---------------------------------------------------------------------------
# purge_managed_resources — flat vs namespaced-with-skill-mirror
# ---------------------------------------------------------------------------


class TestPurgeReproducesRegistryLayout:
    """``purge_managed_resources`` branches on
    ``REGISTRY[tool].commands_style``. Pre-1B the opencode branch
    scanned ``commands/<name>.md`` flat files; the claude branch
    scanned ``commands/osx/<id>.md`` (and the modern skill mirror).
    Phase 1B routes identically."""

    def test_opencode_purges_flat_commands(self, tmp_path):
        target = tmp_path / REGISTRY["opencode"].skills_dir
        target.mkdir(parents=True)
        (target / "commands").mkdir()
        stale = target / "commands" / "osx-stale.md"
        stale.write_text("x")
        keep_path = target / "commands" / "osx-keep.md"
        keep_path.write_text("x")

        removed = purge_managed_resources(
            target,
            "opencode",
            keep_names={"osx-keep"},
            prefixes=("osx-",),
        )
        assert removed == 1
        assert not stale.exists()
        assert keep_path.exists()

    def test_claude_purges_nested_dual_emit(self, tmp_path):
        target = tmp_path / REGISTRY["claude"].skills_dir
        target.mkdir(parents=True)
        (target / "commands" / "osx").mkdir(parents=True)
        stale_legacy = target / "commands" / "osx" / "phase0.md"
        stale_legacy.write_text("x")

        # Modern skill mirror at <target>/skills/osx-phase0/SKILL.md
        skill_mirror = target / "skills" / "osx-phase0"
        skill_mirror.mkdir(parents=True)
        (skill_mirror / "SKILL.md").write_text("x")

        kept_modern = target / "skills" / "osx-phase0-keep"
        kept_modern.mkdir(parents=True)
        (kept_modern / "SKILL.md").write_text("x")

        removed = purge_managed_resources(
            target,
            "claude",
            keep_names={"osx-phase0-keep"},
            prefixes=("osx-",),
        )
        assert removed >= 1
        assert not stale_legacy.exists()
        assert not skill_mirror.exists()
        assert (kept_modern / "SKILL.md").exists()

    @pytest.mark.parametrize("tool_id", ["opencode", "claude"])
    def test_unknown_tool_raises_value_error(self, tmp_path, tool_id):
        """Phase 1B: validation reads ``REGISTRY`` (was ``TOOL_DIRS``)."""
        target = tmp_path / f"fake-{tool_id}"
        target.mkdir()
        with pytest.raises(ValueError, match="Unknown tool"):
            purge_managed_resources(
                target, "bogus", keep_names=set(), prefixes=("osx-",)
            )


# ---------------------------------------------------------------------------
# validate_deployment — skip-agents routing
# ---------------------------------------------------------------------------


class TestValidateDeploymentRoutesByHasAgentsDir:
    """``validate_deployment`` skips agents for tools whose adapter
    declares ``has_agents_dir=False``. Today that is only Claude;
    opencode's agents are validated against the deployed tree."""

    def _seed_target(self, root: Path, *, has_agents: bool) -> Path:
        # ``root/.opencode`` (or .claude) — pick the adapter matching
        # ``has_agents`` so we exercise the right branch.
        for adapter in REGISTRY.values():
            if adapter.has_agents_dir is has_agents:
                target = root / adapter.skills_dir
                target.mkdir(parents=True)
                return target
        raise RuntimeError("no adapter matching has_agents={has_agents}")

    def _seed_manifest_with_agents(self, manifest_path: Path) -> None:
        import toml

        manifest_path.write_text(
            toml.dumps(
                {
                    "version": "0.0.0",
                    "resources": {
                        "agents": {"osx-analyzer": {"version": "0.0.0"}},
                    },
                }
            )
        )

    def test_opencode_validates_agents_when_present(self, tmp_path, capsys):
        target = self._seed_target(tmp_path, has_agents=True)
        # Agent file present — no warning expected.
        (target / "agents").mkdir()
        (target / "agents" / "osx-analyzer.md").write_text("x")
        self._seed_manifest_with_agents(target / "manifest.toml")

        validate_deployment(target, {"resources": {"agents": {"osx-analyzer": {}}}})
        # ``validate_deployment`` only emits warnings on missing
        # resources; no warning expected when agent file exists.
        captured = capsys.readouterr()
        assert "osx-analyzer" not in captured.out

    def test_claude_skips_agent_validation(self, tmp_path, capsys):
        """Claude's adapter has ``has_agents_dir=False``; agent
        entries in a manifest should be silently skipped without
        warnings even though no agent file exists."""
        target = self._seed_target(tmp_path, has_agents=False)
        # No agents/ directory.
        validate_deployment(
            target,
            {"resources": {"agents": {"osx-analyzer": {}}}},
        )
        # No warning about osx-analyzer — the skip-agents branch
        # suppressed validation.
        captured = capsys.readouterr()
        assert "osx-analyzer" not in captured.out


# ---------------------------------------------------------------------------
# Phase 2 L3.2: shared-skills-root informational note
# ---------------------------------------------------------------------------


class TestValidateDeploymentSharedSkillsRootNote:
    """``validate_deployment`` emits an informational note when the active
    adapter's ``skills_dir`` is shared by multiple shipped registry
    entries. Today this branch never fires for opencode or claude (their
    ``skills_dir`` is unique to the adapter), so byte-equality holds for
    the shipped set. Hypothetical ``.agents``-using adapters (Codex, Zed,
    Antigravity, …) would trigger it."""

    @pytest.mark.parametrize("tool_id", ["opencode", "claude"])
    def test_no_shared_root_note_for_shipped_adapters(
        self, tmp_path, capsys, tool_id
    ):
        adapter = REGISTRY[tool_id]
        target = tmp_path / adapter.skills_dir
        target.mkdir(parents=True)

        result = validate_deployment(target, {"resources": {}})

        captured = capsys.readouterr()
        assert "shared skills root" not in captured.out, (
            f"{tool_id}: byte-equality broken — shared-skills-root note "
            f"printed but no shipped adapter should ever fire it"
        )
        assert result["notes"] == [], (
            f"{tool_id}: notes list should be empty for shipped adapters; "
            f"got {result['notes']!r}"
        )
        assert result["valid"] is True
        assert result["warnings"] == 0

    def test_shared_root_note_fires_for_hypothetical_agents_adapter(
        self, tmp_path, capsys
    ):
        """A synthetic ``.agents``-shaped adapter (Codex/Zed/Antigravity
        style) triggers the informational note when another shipped
        adapter also uses ``.agents``. The note does NOT set
        ``valid=False``."""
        from source.tools import ToolAdapter

        adapter_a = ToolAdapter(
            tool_id="codex",
            skills_dir=".agents",
            commands_dir="commands",
            commands_style="skills-only",
            commands_ext="md",
            slash_prefix="/",
            skill_prefix="$",
            runner_binary="codex",
            runner_kind="generic_print",
            has_agents_dir=False,
            agent_field_transform=None,
            inject_name_in_skill_mirror=False,
            cmd_filename_strip_prefix=None,
            docs_file="AGENTS.md",
            tool_name="Codex",
            detect_paths=(".agents",),
        )
        adapter_b = ToolAdapter(
            tool_id="zed",
            skills_dir=".agents",
            commands_dir="commands",
            commands_style="skills-only",
            commands_ext="md",
            slash_prefix="/",
            skill_prefix="$",
            runner_binary="zed",
            runner_kind="generic_print",
            has_agents_dir=False,
            agent_field_transform=None,
            inject_name_in_skill_mirror=False,
            cmd_filename_strip_prefix=None,
            docs_file="AGENTS.md",
            tool_name="Zed",
            detect_paths=(".agents",),
        )
        target = tmp_path / adapter_a.skills_dir
        target.mkdir(parents=True)

        with pytest.MonkeyPatch().context() as mp:
            mp.setitem(REGISTRY, "codex", adapter_a)
            mp.setitem(REGISTRY, "zed", adapter_b)
            result = validate_deployment(target, {"resources": {}})

        captured = capsys.readouterr()
        assert "shared skills root '.agents'" in captured.out
        assert "zed" in captured.out
        assert result["notes"] == [
            {
                "check": "shared-skills-root",
                "tool": "codex",
                "shared_with": ["zed"],
            }
        ]
        assert result["valid"] is True, (
            "shared-skills-root note is informational — must NOT set valid=False"
        )


# ---------------------------------------------------------------------------
# End-to-end smoke: deploy *every* shipped adapter, confirm byte-identical
# tree to the pre-1B shape (except no leftover {{TOKEN}} strings).
# ---------------------------------------------------------------------------


class TestEveryShippedAdapterDeploysCleanly:
    """End-to-end smoke: drive ``deploy_skills`` + ``deploy_commands`` +
    ``deploy_agents`` for every adapter in ``REGISTRY`` and confirm no
    ``{{TOKEN}}`` remains. This is the regression net for the entire
    Phase 1B refactor."""

    @pytest.mark.parametrize("tool_id", ["opencode", "claude"])
    def test_no_leftover_tokens_after_full_deploy(self, tmp_path, tool_id):
        from source.cli import deploy_type, _resolve_side_manifest
        from source.tools import REGISTRY

        adapter = REGISTRY[tool_id]
        target = tmp_path / adapter.skills_dir
        target.mkdir(parents=True)

        # Drive the full deploy path: orchestrator side first.
        oc_root = get_resources_dir() / "canonical"
        _, manifest = _resolve_side_manifest(oc_root)
        deploy_type(
            "skills",
            oc_root,
            target,
            target / "manifest.toml",
            manifest,
            force=True,
            tool=tool_id,
            with_autonomous=True,
        )

        for md in target.rglob("*.md"):
            assert "{{" not in md.read_text(), (
                f"{md.relative_to(target)}: leftover {{{{TOKEN}}}} after deploy"
            )


# ---------------------------------------------------------------------------
# Phase 3 L4.1–L4.3: skills-only deploy branch
# ---------------------------------------------------------------------------


class TestSkillsOnlyDeploy:
    """L4.1–L4.4: ``deploy_commands`` for a synthetic
    ``commands_style="skills-only"`` adapter (Codex/Kimi/Zed shape).

    The skills-only branch must:

    1. Skip the legacy ``commands/`` directory entirely (no slash-command
       file written there).
    2. Write the modern skill mirror at
       ``<target>/<skills_dir>/skills/<name>/SKILL.md``.
    3. Apply ``frontmatter_extras`` and the ``agent_field_transform``
       fallback (``L4.2``) so skills-only adapters that don't override
       ``agent_field_transform`` still get the opencode-only ``agent:``
       line stripped.
    4. Apply ``cross_ref_prefix`` rewriting (``L4.3``) so
       ``/opsx:<cmd>`` references in the body become the adapter's
       invocation form (``$openspec-<cmd>`` for Codex).
    5. Leave no ``{{TOKEN}}`` placeholder in the rendered body.

    Built around a synthesised ``codex`` adapter (cross_ref_prefix="$")
    and a synthesised ``kimi`` adapter (``cross_ref_prefix="/skill:"``)
    so the body rewrite is exercised for both non-canonical prefixes.
    """

    @pytest.fixture
    def source(self) -> Path:
        return get_skills_resources_dir() / "canonical" / "commands"

    @pytest.fixture
    def codex_adapter(self) -> ToolAdapter:
        return ToolAdapter(
            tool_id="codex",
            skills_dir=".agents",
            commands_dir="commands",
            commands_style="skills-only",
            commands_ext="md",
            slash_prefix="/",
            skill_prefix="$",
            runner_binary="codex",
            runner_kind="generic_print",
            has_agents_dir=False,
            agent_field_transform=None,
            inject_name_in_skill_mirror=False,
            frontmatter_extras={"source": "openspec-extended"},
            cmd_filename_strip_prefix=None,
            docs_file="AGENTS.md",
            tool_name="Codex",
            detect_paths=(".agents",),
            ask_tool="AskUserQuestion",
            install_hint=(
                "Run `openspec-extended install codex` after installing the codex CLI"
            ),
            cross_ref_prefix="$",
            runner_args=(),
        )

    @pytest.fixture
    def kimi_adapter(self) -> ToolAdapter:
        return ToolAdapter(
            tool_id="kimi",
            skills_dir=".kimi",
            commands_dir="commands",
            commands_style="skills-only",
            commands_ext="md",
            slash_prefix="/skill:",
            skill_prefix="/skill:",
            runner_binary="kimi",
            runner_kind="generic_print",
            has_agents_dir=False,
            agent_field_transform=None,
            inject_name_in_skill_mirror=True,
            frontmatter_extras={},
            cmd_filename_strip_prefix=None,
            docs_file="AGENTS.md",
            tool_name="Kimi",
            detect_paths=(".kimi",),
            ask_tool="AskUserQuestion",
            install_hint=(
                "Run `openspec-extended install kimi` after installing the Kimi CLI"
            ),
            cross_ref_prefix="/skill:",
            runner_args=(),
        )

    def test_no_legacy_command_file_written_under_commands(
        self, tmp_path, source, codex_adapter
    ):
        """L4.1: the skills-only branch must NOT touch ``<target>/commands/``.

        Codex resolves invocations from the skills tree; the legacy
        ``commands/<name>.md`` file would never be loaded, and writing
        it would just add noise to the deployed tree."""
        from source.tools import REGISTRY

        with pytest.MonkeyPatch().context() as mp:
            mp.setitem(REGISTRY, "codex", codex_adapter)
            target = tmp_path / codex_adapter.skills_dir
            target.mkdir(parents=True)
            deploy_commands(source, target, "osx-review", tool="codex")

        commands_dir = target / "commands"
        assert not commands_dir.exists() or not any(commands_dir.iterdir()), (
            "skills-only adapter: legacy commands/ subtree must NOT be written"
        )

    def test_writes_modern_skill_mirror_under_skills(
        self, tmp_path, source, codex_adapter
    ):
        """L4.1: skills-only adapter emits a ``skills/<name>/SKILL.md``
        modern skill mirror and nothing else."""
        from source.tools import REGISTRY

        with pytest.MonkeyPatch().context() as mp:
            mp.setitem(REGISTRY, "codex", codex_adapter)
            target = tmp_path / codex_adapter.skills_dir
            target.mkdir(parents=True)
            deploy_commands(source, target, "osx-review", tool="codex")

        skill_mirror = target / "skills" / "osx-review" / "SKILL.md"
        assert skill_mirror.is_file(), (
            f"skills-only adapter: {skill_mirror} not written"
        )

    def test_skill_mirror_carries_frontmatter_extras(
        self, tmp_path, source, codex_adapter
    ):
        """L4.2: ``frontmatter_extras`` (``source: openspec-extended``)
        ends up in the deployed frontmatter."""
        from source.tools import REGISTRY

        with pytest.MonkeyPatch().context() as mp:
            mp.setitem(REGISTRY, "codex", codex_adapter)
            target = tmp_path / codex_adapter.skills_dir
            target.mkdir(parents=True)
            deploy_commands(source, target, "osx-review", tool="codex")

        text = (target / "skills" / "osx-review" / "SKILL.md").read_text()
        assert "source: openspec-extended" in text, (
            "frontmatter_extras not injected into skill mirror"
        )

    def test_cross_ref_prefix_rewrites_opsx_references_to_dollar_form(
        self, tmp_path, codex_adapter
    ):
        """L4.3: ``/opsx:propose`` is rewritten to ``$openspec-propose``
        for the Codex adapter (cross_ref_prefix="$").

        Canonical source files don't currently contain ``/opsx:<cmd>``
        references (the post-rename form ``/osc-<verb>`` is the shipped
        surface); the rewrite is forward-compat infrastructure that
        kicks in if a future source file targets upstream core via the
        canonical slash form. Use a synthetic source file here so the
        test exercises the rewrite end-to-end through ``deploy_commands``.
        """
        from source.tools import REGISTRY

        synth_source = tmp_path / "synth-commands"
        synth_source.mkdir()
        (synth_source / "osx-review.md").write_text(
            "---\n"
            "name: osx-review\n"
            "description: synthetic\n"
            "license: MIT\n"
            "compatibility: Requires openspec CLI.\n"
            "---\n\n"
            "Run `/opsx:propose <name>` to start a change.\n"
        )

        with pytest.MonkeyPatch().context() as mp:
            mp.setitem(REGISTRY, "codex", codex_adapter)
            target = tmp_path / codex_adapter.skills_dir
            target.mkdir(parents=True)
            deploy_commands(synth_source, target, "osx-review", tool="codex")

        text = (target / "skills" / "osx-review" / "SKILL.md").read_text()
        assert "$openspec-propose" in text, (
            "codex: /opsx:propose should rewrite to $openspec-propose; "
            f"body was:\n{text}"
        )
        # Original colon form must NOT survive.
        assert "/opsx:propose" not in text, (
            f"codex: canonical /opsx:propose should be rewritten; body was:\n{text}"
        )

    def test_cross_ref_prefix_rewrites_opsx_references_to_skill_colon_form(
        self, tmp_path, kimi_adapter
    ):
        """L4.3: ``/opsx:propose`` is rewritten to ``/skill:openspec-propose``
        for the Kimi adapter (cross_ref_prefix="/skill:")."""
        from source.tools import REGISTRY

        synth_source = tmp_path / "synth-commands"
        synth_source.mkdir()
        (synth_source / "osx-review.md").write_text(
            "---\n"
            "name: osx-review\n"
            "description: synthetic\n"
            "license: MIT\n"
            "compatibility: Requires openspec CLI.\n"
            "---\n\n"
            "Run `/opsx:propose <name>` to start a change.\n"
        )

        with pytest.MonkeyPatch().context() as mp:
            mp.setitem(REGISTRY, "kimi", kimi_adapter)
            target = tmp_path / kimi_adapter.skills_dir
            target.mkdir(parents=True)
            deploy_commands(synth_source, target, "osx-review", tool="kimi")

        text = (target / "skills" / "osx-review" / "SKILL.md").read_text()
        assert "/skill:openspec-propose" in text, (
            "kimi: /opsx:propose should rewrite to /skill:openspec-propose; "
            f"body was:\n{text}"
        )
        # Original colon form must NOT survive.
        assert "/opsx:propose" not in text, (
            f"kimi: canonical /opsx:propose should be rewritten; body was:\n{text}"
        )

    def test_skill_mirror_has_no_leftover_token_placeholders(
        self, tmp_path, source, codex_adapter
    ):
        """L4.1: token substitution still runs in the skills-only branch.

        ``{{PLATFORM_DIR}}`` (the most common one) must render to the
        adapter's ``skills_dir`` (``/home/.agents`` here is irrelevant —
        we check the literal ``.agents`` is rendered)."""
        from source.tools import REGISTRY

        with pytest.MonkeyPatch().context() as mp:
            mp.setitem(REGISTRY, "codex", codex_adapter)
            target = tmp_path / codex_adapter.skills_dir
            target.mkdir(parents=True)
            deploy_commands(source, target, "osx-review", tool="codex")

        text = (target / "skills" / "osx-review" / "SKILL.md").read_text()
        assert "{{PLATFORM_DIR}}" not in text, (
            "skills-only deploy: {{PLATFORM_DIR}} leaked through substitution"
        )
        assert "{{" not in text, (
            f"skills-only deploy: leftover token placeholder in body:\n{text}"
        )

    def test_skill_mirror_strips_agent_field_when_transform_unset(
        self, tmp_path, source, codex_adapter
    ):
        """L4.2: ``_build_skill_mirror`` falls back to
        ``strip_agent_line`` for skills-only adapters that don't
        override ``agent_field_transform``. ``osx-review.md`` source
        has no ``agent:`` line (it's a non-phase command), so we drop a
        synthetic file with one to exercise the strip."""
        from source.cli import _build_skill_mirror
        from source.tools import REGISTRY

        synthetic_dir = tmp_path / "synth-commands"
        synthetic_dir.mkdir()
        synth_file = synthetic_dir / "osx-phase2.md"
        synth_file.write_text(
            "---\n"
            "name: osx-phase2\n"
            "description: synthetic\n"
            "agent: osx-reviewer\n"
            "---\n\n"
            "Body uses /opsx:apply when needed.\n"
        )

        with pytest.MonkeyPatch().context() as mp:
            mp.setitem(REGISTRY, "codex", codex_adapter)
            rendered = _build_skill_mirror(synth_file, "osx-phase2", codex_adapter)

        assert "agent: osx-reviewer" not in rendered, (
            f"skills-only adapter: agent: line should be stripped by "
            f"strip_agent_line fallback; got:\n{rendered}"
        )
        assert "name: osx-phase2" in rendered

    def test_skill_mirror_does_not_rewrite_when_cross_ref_prefix_is_slash(
        self, tmp_path, source
    ):
        """L4.3 + L4 verification: a Claude-shaped skills-only adapter
        (cross_ref_prefix="/") keeps the canonical ``/opsx:propose`` form.

        Not a real shipped adapter — just sanity-checks the no-op branch
        of :func:`_rewrite_skill_body_refs`."""
        from source.cli import _rewrite_skill_body_refs
        from source.tools import REGISTRY

        canonical_prefix_adapter = ToolAdapter(
            tool_id="canonical-prefix",
            skills_dir=".opencode",
            commands_dir="commands",
            commands_style="skills-only",
            commands_ext="md",
            slash_prefix="osx-",
            skill_prefix="/",
            runner_binary="opencode",
            runner_kind="generic_print",
            has_agents_dir=False,
            agent_field_transform=None,
            inject_name_in_skill_mirror=False,
            frontmatter_extras={},
            cmd_filename_strip_prefix=None,
            docs_file="AGENTS.md",
            tool_name="CanonicalPrefix",
            detect_paths=(".opencode",),
            ask_tool="AskUserQuestion",
            install_hint="Run `openspec-extended install canonical-prefix`",
            cross_ref_prefix="",
            runner_args=(),
        )

        body = "Run `/opsx:propose <name>` to start."
        with pytest.MonkeyPatch().context() as mp:
            mp.setitem(REGISTRY, "canonical-prefix", canonical_prefix_adapter)
            rewritten = _rewrite_skill_body_refs(body, canonical_prefix_adapter)

        assert rewritten == body, (
            "cross_ref_prefix='' (fallback to skill_prefix='/') must be a no-op; "
            f"expected {body!r}, got {rewritten!r}"
        )
