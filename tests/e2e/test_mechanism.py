#!/usr/bin/env python3
"""
E2E mechanism tests - no AI calls, safe to run anytime.
Tests CLI options and error handling.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.mechanism


PROJECT_ROOT = Path(__file__).parent.parent.parent
OPENCODE_SOURCE = PROJECT_ROOT / "orchestrator" / "resources" / "canonical"
SKILLS_OPENCODE_SOURCE = PROJECT_ROOT / "skills" / "resources" / "canonical"
RESOURCES_OPENCODE = PROJECT_ROOT / "orchestrator" / "resources" / "canonical"


@pytest.fixture
def e2e_repo(tmp_path):
    """Create temporary E2E repo with opencode installed."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "e2e@test.com"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "E2E Test"],
        cwd=tmp_path,
        check=True,
    )

    readme = tmp_path / "README.md"
    readme.write_text("# E2E Test Repo\n")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "Initial commit"], cwd=tmp_path, check=True
    )

    opencode_target = tmp_path / ".opencode"
    if OPENCODE_SOURCE.exists():
        shutil.copytree(OPENCODE_SOURCE, opencode_target)
    else:
        manifest = RESOURCES_OPENCODE / "manifest.toml"
        scripts_dir = opencode_target / "scripts"
        scripts_dir.mkdir(parents=True)
        (opencode_target / "manifest.toml").write_text(manifest.read_text())

    # Phase 5 split: copy the skills-side source tree alongside the
    # orchestrator-side tree so the deployed target has BOTH manifests
    # (``manifest.toml`` = orchestrator side, ``skills-manifest.toml``
    # = skills side). Validate_skills reads both to cross-check
    # REQUIRED_SKILLS. The skills-side manifest must be renamed so it
    # does not overwrite the orchestrator-side one.
    if SKILLS_OPENCODE_SOURCE.exists():
        for entry in SKILLS_OPENCODE_SOURCE.iterdir():
            dest_name = (
                "skills-manifest.toml" if entry.name == "manifest.toml" else entry.name
            )
            dest = opencode_target / dest_name
            if entry.is_dir():
                shutil.copytree(entry, dest, dirs_exist_ok=True)
            else:
                shutil.copy2(entry, dest)

    # The orchestrator's preflight (validate_skills) cross-checks every
    # REQUIRED_CORE_SKILLS entry against the deployed manifests. Core
    # skills aren't shipped by openspec-extended itself, so append stub
    # entries for each of the 12 osc-* skills to the orchestrator-side
    # manifest (the side that owns the workflow surface).
    import toml

    deployed_manifest_path = opencode_target / "manifest.toml"
    deployed = toml.loads(deployed_manifest_path.read_text())
    skills_section = deployed.setdefault("resources", {}).setdefault("skills", {})
    for osc in (
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
    ):
        skills_section.setdefault(osc, {"version": "0.0.0"})
    deployed_manifest_path.write_text(toml.dumps(deployed))

    # Regardless of source, ensure stub skills + phase commands exist so the
    # orchestrator's preflight (Fix 5: always runs) can pass validate_skills
    # and validate_commands. REQUIRED_CORE_SKILLS expanded to all 12 in
    # dual-emit refactor; osx-changelog and osx-maintain-docs are slash
    # commands (not skills), so they aren't stubbed here.
    skills_dir = opencode_target / "skills"
    for skill in (
        "osx-workflow",
        "osx-review-artifacts",
        "osx-review-test-compliance",
        "osx-commit",
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
    ):
        skill_path = skills_dir / skill / "SKILL.md"
        if not skill_path.exists():
            (skills_dir / skill).mkdir(parents=True, exist_ok=True)
            skill_path.write_text("# stub")

    commands_dir = opencode_target / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    for phase in range(7):
        cmd_file = commands_dir / f"osx-phase{phase}.md"
        if not cmd_file.exists():
            cmd_file.write_text("# stub")

    # Stub the OpenSpec upstream slash commands so the engine's auto-fix
    # pre-check (which verifies the slash command file exists before
    # dispatching) passes. The canonical `orchestrator/resources/canonical/`
    # source tree does NOT ship the `osc-*` slash commands — those come
    # from upstream OpenSpec core (npm package `openspec`). In a real
    # project they land via `openspec init`; in the e2e fixture we stub
    # them so the preflight / auto-fix dispatch can find a file at the
    # expected path. Tests that need to exercise the missing-file
    # behavior delete the stub.
    for osc_cmd in (
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
    ):
        cmd_file = commands_dir / f"{osc_cmd}.md"
        if not cmd_file.exists():
            cmd_file.write_text("# stub")

    changes_dir = tmp_path / "openspec" / "changes"
    changes_dir.mkdir(parents=True, exist_ok=True)

    yield tmp_path


def run_osx_orchestrate(cwd, *args):
    """Run osx-orchestrate via python -m source and return (exit_code, stdout, stderr)."""
    cmd = [sys.executable, "-m", "source", "orchestrate"] + list(args)
    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def setup_minimal_change(cwd, change_name):
    """Create a minimal change structure."""
    change_dir = cwd / "openspec" / "changes" / change_name
    specs_dir = change_dir / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)

    (change_dir / "proposal.md").write_text(
        """# Test Proposal

Minimal test change for E2E testing.

## Summary
Test change for validating osx-orchestrate.
"""
    )
    (change_dir / "design.md").write_text(
        """# Test Design

Minimal design document.
"""
    )
    (change_dir / "tasks.md").write_text(
        """# Tasks

- [ ] Complete test task
"""
    )
    (specs_dir / "spec.md").write_text(
        """# Specification

**SHALL** complete successfully.
"""
    )


class TestVersion:
    """Tests for --version option."""

    def test_version_not_available_on_orchestrate(self, e2e_repo):
        """orchestrate command doesn't have --version (it's a Typer limitation)."""
        exit_code, stdout, stderr = run_osx_orchestrate(e2e_repo, "--version")
        combined = stdout + stderr
        assert exit_code == 2, f"Expected exit 2, got {exit_code}. Output: {combined}"
        assert "No such option: --version" in combined


class TestHelp:
    """Tests for --help option."""

    def test_help_shows_usage_with_all_options(self, e2e_repo):
        """--help shows usage with all options."""
        exit_code, stdout, stderr = run_osx_orchestrate(e2e_repo, "--help")
        combined = stdout + stderr
        assert exit_code == 0, f"Expected exit 0, got {exit_code}. Output: {combined}"
        assert "Usage:" in combined, f"Expected 'Usage:' in output: {combined}"
        assert "--max-phase-iterations" in combined, (
            f"Expected '--max-phase-iterations' in output: {combined}"
        )
        assert "--timeout" in combined, f"Expected '--timeout' in output: {combined}"
        assert "--model" in combined, f"Expected '--model' in output: {combined}"
        assert "--verbose" in combined, f"Expected '--verbose' in output: {combined}"
        assert "--dry-run" in combined, f"Expected '--dry-run' in output: {combined}"
        assert "--force" in combined, f"Expected '--force' in output: {combined}"
        assert "--clean" in combined, f"Expected '--clean' in output: {combined}"
        assert "--from-phase" in combined, (
            f"Expected '--from-phase' in output: {combined}"
        )
        assert "--to-phase" in combined, f"Expected '--to-phase' in output: {combined}"
        assert "--list" in combined, f"Expected '--list' in output: {combined}"
        assert "--schema" in combined, f"Expected '--schema' in output: {combined}"


class TestList:
    """Tests for --list option."""

    def test_list_shows_available_changes(self, e2e_repo):
        """--list shows available changes when used with a change name (Typer requires argument order)."""
        setup_minimal_change(e2e_repo, "test-change")
        setup_minimal_change(e2e_repo, "another-change")

        exit_code, stdout, stderr = run_osx_orchestrate(
            e2e_repo, "test-change", "--list"
        )
        combined = stdout + stderr
        assert exit_code == 0, f"Expected exit 0, got {exit_code}. Output: {combined}"
        assert "test-change" in combined or "another-change" in combined, (
            f"Expected at least one change name in output: {combined}"
        )


class TestDryRun:
    """Tests for --dry-run option."""

    def test_dry_run_shows_phases_without_execution(self, e2e_repo):
        """--dry-run shows phases without execution."""
        setup_minimal_change(e2e_repo, "dry-test")

        exit_code, stdout, stderr = run_osx_orchestrate(
            e2e_repo, "dry-test", "--dry-run", "--max-phase-iterations=1"
        )
        combined = stdout + stderr
        assert "[DRY RUN]" in combined, f"Expected '[DRY RUN]' in output: {combined}"


class TestErrorHandling:
    """Tests for error handling."""

    def test_invalid_change_id_exits_with_error(self, e2e_repo):
        """Invalid change ID exits with error."""
        exit_code, stdout, stderr = run_osx_orchestrate(e2e_repo, "nonexistent-change")
        assert exit_code == 1, (
            f"Expected exit 1, got {exit_code}. Output: {stdout + stderr}"
        )
        combined = stdout + stderr
        assert "not found" in combined or "Error" in combined or "Change" in combined, (
            f"Expected error message in output: {combined}"
        )

    def test_invalid_option_exits_with_error(self, e2e_repo):
        """Invalid option exits with error (Typer exits with code 2 for invalid options)."""
        exit_code, stdout, stderr = run_osx_orchestrate(e2e_repo, "--invalid-option")
        assert exit_code == 2, (
            f"Expected exit 2, got {exit_code}. Output: {stdout + stderr}"
        )
        combined = stdout + stderr
        assert "No such option" in combined or "invalid" in combined, (
            f"Expected error message in output: {combined}"
        )


# ============================================================================
# PHASE0 self-healing contract — Layer 2 mechanism coverage
# ============================================================================
#
# These tests pin the contract that catches the `library-state-status`
# regression (the engine halted on `/osc-update-change` instead of
# self-fixing). They run on every commit (mechanism marker = always-collected)
# without spawning any AI subprocess.
# ============================================================================


def _engine_state_path(e2e_repo, change_name):
    return e2e_repo / "openspec" / "changes" / change_name / "state.json"


def _write_engine_state(e2e_repo, change_name, payload: dict) -> None:
    state_path = _engine_state_path(e2e_repo, change_name)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(payload))


@pytest.fixture
def change_with_state(e2e_repo):
    """Seed a change directory whose ``state.json`` already exists.

    Lets the engine's ``run_phase`` read pre-populated state (e.g.
    ``routes_pending``) without first having to run a real agent
    subprocess. Returns the change name; tests customize the state via
    ``_write_engine_state``.
    """
    change_name = "phase0-autofix-test"
    change_dir = e2e_repo / "openspec" / "changes" / change_name
    change_dir.mkdir(parents=True, exist_ok=True)
    (change_dir / "proposal.md").write_text("# stub\n")
    (change_dir / "design.md").write_text("# stub\n")
    (change_dir / "tasks.md").write_text("# stub\n")
    specs_dir = change_dir / "specs"
    specs_dir.mkdir(parents=True, exist_ok=True)
    (specs_dir / "spec.md").write_text("# stub\n")
    yield e2e_repo, change_name


class TestSlashCommandNameResolution:
    """Every route in ``AUTO_FIXABLE_ROUTES`` resolves to a deployed slash command.

    The `library-state-status` regression shipped because the deployed
    slash command was ``osc-update.md`` while the route name was
    ``osc-update-change``. These tests pin the contract by deriving the
    expected filename from the engine's own ``AUTO_FIXABLE_ROUTES``
    table — adding a route without a matching deployed file fails
    immediately.
    """

    def test_autofixable_route_slash_command_exists(self, e2e_repo):
        from source.orchestrator.engine import AUTO_FIXABLE_ROUTES

        commands_dir = e2e_repo / ".opencode" / "commands"
        missing = [
            route
            for route in AUTO_FIXABLE_ROUTES
            if not (commands_dir / f"{route}.md").exists()
        ]
        assert not missing, (
            f"routes in engine.AUTO_FIXABLE_ROUTES have no deployed slash "
            f"command file at .opencode/commands/<route>.md: {missing}. "
            f"The engine's _run_auto_fix will fail pre-check at runtime "
            f"with no clear path to resolution. Re-run "
            f"`openspec-extended install opencode` to deploy the canonical "
            f"slash commands."
        )

    def test_osc_update_change_command_file_present(self, e2e_repo):
        """The exact regression sentinel for the `library-state-status` bug.

        Before the fix, the engine emitted ``/osc-update-change`` to
        ``state.json``'s ``routes_pending`` and opencode returned
        "command not found" because the deployed file was
        ``osc-update.md``. Pinning the exact filename closes that door.
        """
        path = e2e_repo / ".opencode" / "commands" / "osc-update-change.md"
        assert path.exists(), (
            f"Required slash command missing: {path}. The engine emits "
            f"`/osc-update-change` from PHASE0's auto-fixable routing and "
            f"would fail pre-check at runtime if this file is absent."
        )

    def test_no_legacy_osc_update_file(self, e2e_repo):
        """Catches the *specific* misnaming that caused the airk regression.

        If a project deploys ``osc-update.md`` alongside (or instead of)
        ``osc-update-change.md``, the engine's pre-check passes but
        ``opencode run --command osc-update-change`` still fails. This
        test pins the canonical filename contract.
        """
        legacy_path = e2e_repo / ".opencode" / "commands" / "osc-update.md"
        assert not legacy_path.exists(), (
            f"Legacy slash command name detected: {legacy_path}. The "
            f"engine routes PHASE0's auto-fix to `/osc-update-change` "
            f"(with the `-change` suffix), not `/osc-update`. Rename "
            f"the deployed file from `osc-update.md` to "
            f"`osc-update-change.md` (and update its body references) "
            f"so the engine's pre-check resolves correctly."
        )

    def test_no_legacy_osc_continue_or_apply_files(self, e2e_repo):
        """Symmetric regression sentinel for the other renamed routes.

        The airk repo's misnaming wasn't unique to ``osc-update`` —
        every ``osc-<verb>`` was renamed to ``osc-<verb>-change``. This
        test pins the suffix contract for the routes referenced in the
        orchestrator's docs.
        """
        commands_dir = e2e_repo / ".opencode" / "commands"
        legacy_names = (
            "osc-apply",
            "osc-continue",
            "osc-new",
            "osc-archive",
            "osc-bulk-archive",
            "osc-verify",
            "osc-ff",
            "osc-sync",
        )
        present = [n for n in legacy_names if (commands_dir / f"{n}.md").exists()]
        assert not present, (
            f"Legacy slash command names detected (without `-change` "
            f"suffix): {present}. The orchestrator's skills/agents/docs "
            f"reference the `-change` suffixed forms. Rename the deployed "
            f"files so the engine's pre-check resolves correctly."
        )


class TestPhase0AutoFixVsHaltContract:
    """Engine-level contract for auto-fixable vs halt-and-surface routes.

    Pins the behavior change that fixed the `library-state-status`
    regression: ``run_phase`` no longer halts on auto-fixable routes
    (``/osc-update-change``), but still halts on routes that require
    user judgment (``/osc-continue-change``, ``/osc-new-change``,
    ``/osc-archive-change``, ``/osc-explore``).
    """

    def test_engine_does_not_halt_on_autofixable_route(
        self, change_with_state, monkeypatch
    ):
        """`/osc-update-change` alone in routes_pending → engine auto-fixes + advances.

        Regression sentinel: if this fails, the engine has reverted to
        the halt-on-every-route behavior that blocked
        `library-state-status`.
        """
        from source.orchestrator import engine as eng

        e2e_repo, change = change_with_state
        monkeypatch.chdir(e2e_repo)
        _write_engine_state(
            e2e_repo,
            change,
            {
                "phase": "PHASE0",
                "iteration": 1,
                "phase_complete": False,
                "phase_iterations": {"PHASE0": 0},
                "routes_pending": ["/osc-update-change"],
            },
        )

        agent_calls = {"n": 0}
        autofix_calls: list[str] = []

        def _run_agent_then_complete(state, phase):
            agent_calls["n"] += 1
            if agent_calls["n"] == 1:
                _write_engine_state(
                    e2e_repo,
                    change,
                    {
                        "phase": "PHASE0",
                        "iteration": 1,
                        "phase_complete": False,
                        "phase_iterations": {"PHASE0": 1},
                        "routes_pending": ["/osc-update-change"],
                    },
                )
            else:
                _write_engine_state(
                    e2e_repo,
                    change,
                    {
                        "phase": "PHASE0",
                        "iteration": 2,
                        "phase_complete": True,
                        "phase_iterations": {"PHASE0": 2},
                    },
                )
            return True

        def _autofix(state, route):
            autofix_calls.append(route)
            _write_engine_state(
                e2e_repo,
                change,
                {
                    "phase": "PHASE0",
                    "iteration": 2,
                    "phase_complete": False,
                    "phase_iterations": {"PHASE0": 1},
                },
            )
            return True

        original_run_agent = eng.run_agent
        original_run_auto_fix = eng._run_auto_fix
        eng.run_agent = _run_agent_then_complete  # type: ignore[assignment]
        eng._run_auto_fix = _autofix  # type: ignore[assignment]
        try:
            orch_state = eng.OrchestratorState(
                change_id=change,
                change_dir=e2e_repo / "openspec" / "changes" / change,
                max_phase_iterations=5,
            )
            result = eng.run_phase(orch_state, "PHASE0")
        finally:
            eng.run_agent = original_run_agent  # type: ignore[assignment]
            eng._run_auto_fix = original_run_auto_fix  # type: ignore[assignment]

        assert result is True, (
            "PHASE0 halted on /osc-update-change — the engine should "
            "have auto-dispatched the fix and re-entered PHASE0 to "
            "verify. This is the regression that blocked "
            "`library-state-status` in production."
        )
        assert autofix_calls == ["/osc-update-change"], (
            f"_run_auto_fix was invoked with {autofix_calls}; expected "
            f"['/osc-update-change']"
        )

    def test_engine_halts_on_non_autofixable_route(
        self, change_with_state, monkeypatch
    ):
        """`/osc-continue-change` alone in routes_pending → engine halts.

        Symmetric sentinel: if this fails, the engine has auto-fixed a
        route that requires user judgment (creating missing artifacts,
        intent-level changes, archive decisions). The auto-fix dispatch
        must NOT swallow these.
        """
        from source.orchestrator import engine as eng

        e2e_repo, change = change_with_state
        monkeypatch.chdir(e2e_repo)
        _write_engine_state(
            e2e_repo,
            change,
            {
                "phase": "PHASE0",
                "iteration": 1,
                "phase_complete": False,
                "phase_iterations": {"PHASE0": 0},
                "routes_pending": ["/osc-continue-change"],
            },
        )

        original_run_agent = eng.run_agent
        original_run_auto_fix = eng._run_auto_fix

        def _run_agent(state, phase):
            return True

        autofix_called = {"hit": False}

        def _autofix_should_not_be_called(state, route):
            autofix_called["hit"] = True
            return True

        eng.run_agent = _run_agent  # type: ignore[assignment]
        eng._run_auto_fix = _autofix_should_not_be_called  # type: ignore[assignment]
        try:
            orch_state = eng.OrchestratorState(
                change_id=change,
                change_dir=e2e_repo / "openspec" / "changes" / change,
                max_phase_iterations=3,
            )
            result = eng.run_phase(orch_state, "PHASE0")
        finally:
            eng.run_agent = original_run_agent  # type: ignore[assignment]
            eng._run_auto_fix = original_run_auto_fix  # type: ignore[assignment]

        assert result is False, (
            "PHASE0 advanced on /osc-continue-change — the engine "
            "should have halted for the user. Missing-artifact routes "
            "require user judgment and must not be auto-fixed."
        )
        assert autofix_called["hit"] is False, (
            "_run_auto_fix was invoked for a non-auto-fixable route "
            "(/osc-continue-change); the auto-fix dispatch must only "
            "trigger for routes in engine.AUTO_FIXABLE_ROUTES."
        )

    def test_engine_halts_on_mixed_routes(
        self, change_with_state, monkeypatch
    ):
        """Mixed routes (auto-fix + user-judgment) → halt, no auto-fix.

        A mixed set is unsafe to auto-fix: the engine can't decide
        whether to silently handle the auto-fixable part or surface the
        whole set. Halting preserves the user's visibility into both
        routes.
        """
        from source.orchestrator import engine as eng

        e2e_repo, change = change_with_state
        monkeypatch.chdir(e2e_repo)
        _write_engine_state(
            e2e_repo,
            change,
            {
                "phase": "PHASE0",
                "iteration": 1,
                "phase_complete": False,
                "phase_iterations": {"PHASE0": 0},
                "routes_pending": ["/osc-update-change", "/osc-new-change"],
            },
        )

        original_run_agent = eng.run_agent
        original_run_auto_fix = eng._run_auto_fix

        autofix_called = {"hit": False}

        def _autofix(state, route):
            autofix_called["hit"] = True
            return True

        def _run_agent(state, phase):
            return True

        eng.run_agent = _run_agent  # type: ignore[assignment]
        eng._run_auto_fix = _autofix  # type: ignore[assignment]
        try:
            orch_state = eng.OrchestratorState(
                change_id=change,
                change_dir=e2e_repo / "openspec" / "changes" / change,
                max_phase_iterations=3,
            )
            result = eng.run_phase(orch_state, "PHASE0")
        finally:
            eng.run_agent = original_run_agent  # type: ignore[assignment]
            eng._run_auto_fix = original_run_auto_fix  # type: ignore[assignment]

        assert result is False, (
            "PHASE0 advanced on a mixed routes_pending set; engine "
            "should have halted. Mixed auto-fixable + user-judgment "
            "routes must surface together, not partially auto-fixed."
        )
        assert autofix_called["hit"] is False, (
            "_run_auto_fix was invoked on a mixed routes_pending set; "
            "auto-fix dispatch must only trigger when every pending "
            "route is in engine.AUTO_FIXABLE_ROUTES."
        )

class TestAutoFixAgentDispatchContract:
    """The ``osx-editor`` agent and the engine's auto-fix dispatch.

    Pins the existence and shape of the dedicated auto-fix agent, plus
    the engine's pre-check that surfaces slash-command-resolution
    failures with a clear, named-file diagnostic (instead of letting
    opencode emit a generic "command not found").
    """

    def test_osx_editor_agent_registered(self):
        from source.orchestrator.engine import AUTO_FIX_AGENTS, AUTO_FIXABLE_ROUTES

        # Engine contract: every auto-fixable route has a registered agent.
        for route in AUTO_FIXABLE_ROUTES:
            assert route in AUTO_FIX_AGENTS, (
                f"route {route!r} is in AUTO_FIXABLE_ROUTES but has no "
                f"agent registered in AUTO_FIX_AGENTS — engine dispatch "
                f"would log an error and halt."
            )
            assert AUTO_FIX_AGENTS[route], (
                f"agent registered for route {route!r} is empty"
            )

    def test_osx_editor_agent_file_present(self):
        """The agent file ships with the canonical resources."""
        from source.orchestrator.engine import AUTO_FIX_AGENTS
        from source.orchestrator.engine import _is_auto_fixable_route

        for route, agent_name in AUTO_FIX_AGENTS.items():
            if not _is_auto_fixable_route(route):
                continue
            path = (
                Path(__file__).parent.parent.parent
                / "orchestrator"
                / "resources"
                / "canonical"
                / "agents"
                / f"{agent_name}.md"
            )
            assert path.exists(), (
                f"auto-fix agent file missing: {path}. The engine's "
                f"RunRequest will reference this agent; the opencode "
                f"runner will fail to dispatch without it."
            )

    def test_run_auto_fix_pre_check_fails_cleanly_on_missing_slash_command(
        self, change_with_state, monkeypatch
    ):
        """Missing slash command file → engine returns False, no spawn.

        Regression sentinel for the `library-state-status` failure
        mode: opencode emitted "command not found" because the deployed
        slash command was misnamed. The engine's pre-check surfaces
        this with a clear diagnostic instead of letting the runner
        fail opaquely.
        """
        from source.orchestrator import engine as eng

        e2e_repo, change = change_with_state
        monkeypatch.chdir(e2e_repo)
        # Delete the stub slash command the e2e_repo fixture deployed.
        cmd = e2e_repo / ".opencode" / "commands" / "osc-update-change.md"
        if cmd.exists():
            cmd.unlink()

        _write_engine_state(
            e2e_repo,
            change,
            {
                "phase": "PHASE0",
                "iteration": 1,
                "phase_complete": False,
                "phase_iterations": {"PHASE0": 0},
                "routes_pending": ["/osc-update-change"],
            },
        )

        # Patch out detect_runner so we don't depend on the binary.
        # The pre-check should fail BEFORE this is reached.
        original_detect = eng.detect_runner
        detect_called = {"hit": False}

        def _fail_if_called(*_a, **_kw):
            detect_called["hit"] = True
            raise AssertionError(
                "detect_runner should not be reached when pre-check fails"
            )

        eng.detect_runner = _fail_if_called  # type: ignore[assignment]
        try:
            orch_state = eng.OrchestratorState(
                change_id=change,
                change_dir=e2e_repo / "openspec" / "changes" / change,
                max_phase_iterations=3,
            )
            # Call the REAL _run_auto_fix — not a monkeypatched one.
            # The test asserts the pre-check returns False before
            # reaching detect_runner / the subprocess spawn.
            result = eng._run_auto_fix(orch_state, "/osc-update-change")
        finally:
            eng.detect_runner = original_detect  # type: ignore[assignment]

        assert result is False, (
            "_run_auto_fix returned True when the slash command file "
            "was missing; the pre-check should return False and log "
            "an error naming the missing file."
        )
        assert detect_called["hit"] is False, (
            "_run_auto_fix reached detect_runner with a missing slash "
            "command file; the pre-check should short-circuit before "
            "the runner probe."
        )


class TestToPhaseFlag:
    """The --to-phase flag stops the orchestrator after a given phase.

    PHASE0-only e2e tests (self-heal-workflow.bats) rely on this flag to
    skip PHASE1-PHASE6 and keep the regression sentinel under ~5 min.
    """

    def test_to_phase_help_describes_purpose(self, e2e_repo):
        """`--help` for orchestrate mentions --to-phase with its purpose."""
        exit_code, stdout, stderr = run_osx_orchestrate(e2e_repo, "--help")
        combined = stdout + stderr
        assert exit_code == 0
        assert "--to-phase" in combined
        # Purpose hint should be present so users discover the flag.
        assert "PHASE0" in combined or "phase" in combined.lower()

    def test_to_phase_unknown_value_rejected(self, e2e_repo):
        """--to-phase=BOGUS exits non-zero with an error naming valid values."""
        setup_minimal_change(e2e_repo, "test-change")
        exit_code, stdout, stderr = run_osx_orchestrate(
            e2e_repo, "test-change", "--to-phase=BOGUS", "--force"
        )
        combined = stdout + stderr
        assert exit_code != 0, (
            f"--to-phase=BOGUS should be rejected; got exit 0. Output: {combined}"
        )
        assert "Unknown" in combined or "PHASE0" in combined, (
            f"Expected error message naming valid phases; got: {combined}"
        )
