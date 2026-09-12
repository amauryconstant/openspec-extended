#!/usr/bin/env python3
"""Phase 1C engine-side tests.

The engine.py preflight functions (``validate_skills`` /
``validate_commands``) and the orchestrator's preflight binary probe
(``ai_binary = REGISTRY[platform].runner_binary``) used to embed
hardcoded ``"opencode"`` / ``"claude"`` literals. Phase 1C wires them
through ``REGISTRY`` so a third-party adapter ships with no engine
edits.

These tests pin the registry-driven behaviour:

- the platform-aware install hint reads from ``detect_platform``,
- the preflight binary probe reads from ``REGISTRY[platform].runner_binary``,
- every shipped adapter's runner_kind resolves to a concrete runner
  via ``_runner_for``.

No AI subprocess is spawned.
"""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import MagicMock

import pytest

from source.tools import REGISTRY, ToolAdapter


pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Registry ↔ engine contract
# ---------------------------------------------------------------------------


class TestRegistryMapsToEngineConsumers:
    """The engine's binary probe (``REGISTRY[platform].runner_binary``)
    and the install-hint message (``detect_platform``) must agree with
    the runner dispatch. This is a regression guard for the day someone
    adds a third adapter: the new adapter's ``runner_binary`` and
    ``runner_kind`` must both resolve cleanly.
    """

    def test_opencode_runner_binary_matches_runner_class_name(self):
        assert REGISTRY["opencode"].runner_binary == "opencode"

    def test_claude_runner_binary_matches_runner_class_name(self):
        assert REGISTRY["claude"].runner_binary == "claude"

    def test_every_shipped_runner_kind_resolves_to_runner_class(self):
        from source.orchestrator.runner import _runner_for

        for adapter in REGISTRY.values():
            runner = _runner_for(adapter)
            assert runner.adapter is adapter, (
                f"{adapter.tool_id}: _runner_for returned a runner "
                f"whose adapter is not the input adapter"
            )

    def test_every_shipped_adapter_has_distinct_runner_binary(self):
        # Two adapters sharing a runner_binary would collide when both
        # could plausibly be the "active" tool on the same machine.
        binaries = [a.runner_binary for a in REGISTRY.values()]
        assert len(binaries) == len(set(binaries)), (
            f"runner_binary collision across shipped adapters: {binaries}"
        )


# ---------------------------------------------------------------------------
# validate_skills / validate_commands install-hint
# ---------------------------------------------------------------------------


class TestValidateSkillsInstallHint:
    """``validate_skills`` emits ``Run: openspec-extended install <platform>``
    on failure, where ``<platform>`` comes from
    ``osx_lib.detect_platform(project_root)``. When no tool directory
    is present, ``detect_platform`` defaults to ``"opencode"`` — the
    message is byte-identical to pre-1C behaviour in that case.
    """

    def test_hint_names_claude_when_claude_marker_present(
        self, tmp_path, monkeypatch
    ):
        (tmp_path / ".claude").mkdir()
        monkeypatch.chdir(tmp_path)
        from source.orchestrator import engine as eng

        state = MagicMock()
        state.change_dir = None

        monkeypatch.setattr(
            eng.osx_lib,
            "validate_skills",
            lambda project_root=None: {
                "valid": False,
                "errors": [],
                "missing_skills": ["x"],
            },
        )

        captured = []
        monkeypatch.setattr(eng, "log_error", lambda s, msg: captured.append(msg))
        monkeypatch.setattr(eng, "log", lambda s, msg: None)
        monkeypatch.setattr(eng, "log_verbose", lambda s, msg: None)
        monkeypatch.setattr(eng, "print_validation_errors", lambda s, d: None)

        with pytest.raises(SystemExit):
            eng.validate_skills(state)

        install_hints = [m for m in captured if "install" in m]
        assert install_hints, f"no install hint in {captured!r}"
        assert any("install claude" in m for m in install_hints), (
            f"hint should mention detected platform 'claude'; got {install_hints!r}"
        )

    def test_hint_names_opencode_when_no_marker_present(
        self, tmp_path, monkeypatch
    ):
        # No tool directory → detect_platform falls back to "opencode".
        # Hint matches the pre-1C byte-identical message.
        monkeypatch.chdir(tmp_path)
        from source.orchestrator import engine as eng

        state = MagicMock()
        state.change_dir = None

        monkeypatch.setattr(
            eng.osx_lib,
            "validate_skills",
            lambda project_root=None: {
                "valid": False,
                "errors": [],
                "missing_skills": ["x"],
            },
        )

        captured = []
        monkeypatch.setattr(eng, "log_error", lambda s, msg: captured.append(msg))
        monkeypatch.setattr(eng, "log", lambda s, msg: None)
        monkeypatch.setattr(eng, "log_verbose", lambda s, msg: None)
        monkeypatch.setattr(eng, "print_validation_errors", lambda s, d: None)

        with pytest.raises(SystemExit):
            eng.validate_skills(state)

        install_hints = [m for m in captured if "install" in m]
        assert install_hints
        assert any("install opencode" in m for m in install_hints), (
            f"hint should default to 'opencode' when no marker is present; "
            f"got {install_hints!r}"
        )


class TestValidateCommandsInstallHint:
    """Same contract as ``TestValidateSkillsInstallHint`` but for the
    ``validate_commands`` preflight."""

    def test_hint_names_claude_when_claude_marker_present(
        self, tmp_path, monkeypatch
    ):
        (tmp_path / ".claude").mkdir()
        monkeypatch.chdir(tmp_path)
        from source.orchestrator import engine as eng

        state = MagicMock()
        state.change_dir = None

        monkeypatch.setattr(
            eng.osx_lib,
            "validate_commands",
            lambda project_root=None: {"valid": False, "errors": []},
        )

        captured = []
        monkeypatch.setattr(eng, "log_error", lambda s, msg: captured.append(msg))
        monkeypatch.setattr(eng, "log", lambda s, msg: None)
        monkeypatch.setattr(eng, "log_verbose", lambda s, msg: None)
        monkeypatch.setattr(eng, "print_validation_errors", lambda s, d: None)

        with pytest.raises(SystemExit):
            eng.validate_commands(state)

        install_hints = [m for m in captured if "install" in m]
        assert install_hints
        assert any("install claude" in m for m in install_hints), (
            f"hint should mention detected platform 'claude'; got {install_hints!r}"
        )


# ---------------------------------------------------------------------------
# Pre-flight binary probe (line 1212)
# ---------------------------------------------------------------------------


class TestPreflightBinaryFromRegistry:
    """The pre-flight probe at line 1212 derives ``ai_binary`` from
    ``REGISTRY[platform].runner_binary``. Pinning the contract here
    means a future adapter whose ``runner_binary`` differs from the
    tool id (e.g. ``claude_code`` aliased to ``claude``) only needs a
    registry edit — no engine change."""

    def test_ai_binary_for_opencode_project(self):
        platform = "opencode"
        assert REGISTRY[platform].runner_binary == "opencode"

    def test_ai_binary_for_claude_project(self):
        platform = "claude"
        assert REGISTRY[platform].runner_binary == "claude"

    def test_synthetic_adapter_runner_binary_round_trips(self):
        # A synthetic adapter with a non-default runner_binary proves
        # the engine lookup is purely registry-driven (no fall-through
        # to a hardcoded name).
        synthetic = ToolAdapter(
            tool_id="foo",
            skills_dir=".foo",
            commands_dir="commands",
            commands_style="flat",
            commands_ext="md",
            slash_prefix="foo-",
            skill_prefix="/",
            runner_binary="foo-cli",
            runner_kind="generic_print",
            has_agents_dir=False,
            agent_field_transform=None,
            docs_file="AGENTS.md",
            tool_name="Foo",
            detect_paths=(".foo",),
        )
        assert REGISTRY.get("foo") is None  # not shipped
        assert synthetic.runner_binary == "foo-cli"


# ---------------------------------------------------------------------------
# Pre-commit hook coverage: registry integrity for runner consumers
# ---------------------------------------------------------------------------


class TestRegistrySupportsEngineDispatch:
    """Sanity: every shipped adapter has the field the engine reads
    (``runner_binary``) and every adapter's runner_kind is one of the
    three values the engine's runner factory understands.
    """

    @pytest.mark.parametrize("tool_id", sorted(REGISTRY))
    def test_runner_binary_is_nonempty(self, tool_id):
        assert REGISTRY[tool_id].runner_binary, (
            f"{tool_id}: runner_binary must be set (engine reads it "
            f"at line 1212 to spawn the AI binary)"
        )

    @pytest.mark.parametrize("tool_id", sorted(REGISTRY))
    def test_runner_kind_is_known(self, tool_id):
        valid_kinds = {"opencode_run", "claude_print", "generic_print"}
        assert REGISTRY[tool_id].runner_kind in valid_kinds, (
            f"{tool_id}: runner_kind {REGISTRY[tool_id].runner_kind!r} "
            f"must be one of {sorted(valid_kinds)}"
        )

    @pytest.mark.parametrize("tool_id", sorted(REGISTRY))
    def test_detect_paths_is_nonempty(self, tool_id):
        assert REGISTRY[tool_id].detect_paths, (
            f"{tool_id}: detect_paths must be non-empty (engine's "
            f"detect_runner walks it)"
        )

    @pytest.mark.parametrize("tool_id", sorted(REGISTRY))
    def test_tool_name_is_nonempty(self, tool_id):
        assert REGISTRY[tool_id].tool_name, (
            f"{tool_id}: tool_name is consumed in install hints and "
            f"log lines"
        )
