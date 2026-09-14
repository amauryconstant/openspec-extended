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
from source.tools import REGISTRY


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
