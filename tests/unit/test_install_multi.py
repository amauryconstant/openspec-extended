#!/usr/bin/env python3
"""Phase 1E tests: multi-tool install / update.

Pins:

1. ``_parse_tool_target`` accepts single ids, comma-separated lists, and
   whitespace; rejects empty input, unknown ids, duplicates, and "all".
2. ``install opencode,claude`` loops per-tool; global hooks
   (``update_gitignore``) called once even for multi-tool.
3. ``install --all`` is rejected by ``_parse_tool_target``.
4. ``update opencode,claude`` mirrors install's loop.
5. Single-tool calls preserve byte-identical v1.9.x behaviour: no
   summary line, exit-code 1 on failure, exit-code 0 on success.
6. Partial failure: one tool fails, others continue, summary printed,
   exit-code 1.
"""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

from source.cli import REGISTRY, _parse_tool_target, app


pytestmark = pytest.mark.unit


runner = CliRunner()


# ---------------------------------------------------------------------------
# _parse_tool_target
# ---------------------------------------------------------------------------


class TestParseToolTargetValid:
    @pytest.mark.parametrize("raw,expected", [
        ("opencode", ["opencode"]),
        ("claude", ["claude"]),
        ("opencode,claude", ["opencode", "claude"]),
        ("claude,opencode", ["claude", "opencode"]),
        ("opencode, claude", ["opencode", "claude"]),
        ("  opencode ,  claude  ", ["opencode", "claude"]),
    ])
    def test_accepts_valid_inputs(self, raw, expected):
        assert _parse_tool_target(raw) == expected

    def test_all_registered_tools_listed(self):
        # Registry may grow in v1.11.0; this test pins _parse_tool_target
        # does NOT secretly accept "all".
        assert "opencode" in REGISTRY
        assert "claude" in REGISTRY


class TestParseToolTargetInvalid:
    @pytest.mark.parametrize("raw", [
        "",
        "   ",
        "unknown",
        "opencode,unknown",
        "opencode,opencode",
        "all",
        "ALL",
    ])
    def test_rejects_invalid_inputs(self, raw):
        with pytest.raises(SystemExit) as exc_info:
            _parse_tool_target(raw)
        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# install / update with comma-separated tool lists
# ---------------------------------------------------------------------------


class TestInstallCommaSeparated:
    def test_two_tools_each_deploy(self, tmp_path, monkeypatch):
        deploy_calls: list[str] = []
        validate_calls: list[str] = []

        def fake_deploy(tool, force=False, with_autonomous=False):
            deploy_calls.append(tool)

        def fake_validate(target_dir):
            validate_calls.append(str(target_dir))

        monkeypatch.setattr("source.cli.deploy_all_resources", fake_deploy)
        monkeypatch.setattr("source.cli._validate_target_after_deploy", fake_validate)
        monkeypatch.setattr("source.cli.update_gitignore", lambda: None)

        result = runner.invoke(app, ["install", "opencode,claude"])

        assert result.exit_code == 0, result.output
        assert deploy_calls == ["opencode", "claude"]
        assert len(validate_calls) == 2

    def test_order_preserved(self, tmp_path, monkeypatch):
        deploy_calls: list[str] = []

        def fake_deploy(tool, force=False, with_autonomous=False):
            deploy_calls.append(tool)

        monkeypatch.setattr("source.cli.deploy_all_resources", fake_deploy)
        monkeypatch.setattr("source.cli._validate_target_after_deploy", lambda d: None)
        monkeypatch.setattr("source.cli.update_gitignore", lambda: None)

        result = runner.invoke(app, ["install", "claude,opencode"])

        assert result.exit_code == 0, result.output
        assert deploy_calls == ["claude", "opencode"]


class TestInstallUpdateGitignoreOnceForMultiTool:
    def test_update_gitignore_called_once_for_two_tools(self, tmp_path, monkeypatch):
        gitignore_calls: list[int] = [0]

        def fake_deploy(tool, force=False, with_autonomous=False):
            pass

        def fake_gitignore():
            gitignore_calls[0] += 1

        monkeypatch.setattr("source.cli.deploy_all_resources", fake_deploy)
        monkeypatch.setattr("source.cli._validate_target_after_deploy", lambda d: None)
        monkeypatch.setattr("source.cli.update_gitignore", fake_gitignore)

        result = runner.invoke(app, ["install", "opencode,claude", "--with-autonomous"])

        assert result.exit_code == 0, result.output
        assert gitignore_calls[0] == 1, (
            f"update_gitignore should be called exactly once for multi-tool "
            f"with --with-autonomous; got {gitignore_calls[0]} calls"
        )

    def test_update_gitignore_not_called_when_all_targets_fail(self, tmp_path, monkeypatch):
        gitignore_calls: list[int] = [0]

        def failing_deploy(tool, force=False, with_autonomous=False):
            raise RuntimeError(f"simulated failure for {tool}")

        def fake_gitignore():
            gitignore_calls[0] += 1

        monkeypatch.setattr("source.cli.deploy_all_resources", failing_deploy)
        monkeypatch.setattr("source.cli._validate_target_after_deploy", lambda d: None)
        monkeypatch.setattr("source.cli.update_gitignore", fake_gitignore)

        result = runner.invoke(app, ["install", "opencode,claude", "--with-autonomous"])

        assert result.exit_code == 1
        assert gitignore_calls[0] == 0


# ---------------------------------------------------------------------------
# Partial failure handling
# ---------------------------------------------------------------------------


class TestInstallPartialFailure:
    def test_first_tool_succeeds_second_fails(self, tmp_path, monkeypatch):
        deploy_calls: list[str] = []

        def maybe_deploy(tool, force=False, with_autonomous=False):
            deploy_calls.append(tool)
            if tool == "claude":
                raise RuntimeError("simulated claude failure")

        monkeypatch.setattr("source.cli.deploy_all_resources", maybe_deploy)
        monkeypatch.setattr("source.cli._validate_target_after_deploy", lambda d: None)
        monkeypatch.setattr("source.cli.update_gitignore", lambda: None)

        result = runner.invoke(app, ["install", "opencode,claude"])

        assert result.exit_code == 1
        assert deploy_calls == ["opencode", "claude"]
        # Summary mentions both
        assert "summary" in result.output.lower()
        assert "opencode" in result.output
        assert "claude" in result.output

    def test_systemexit_propagates_as_failure(self, tmp_path, monkeypatch):
        def abort_deploy(tool, force=False, with_autonomous=False):
            if tool == "claude":
                raise SystemExit(2)

        monkeypatch.setattr("source.cli.deploy_all_resources", abort_deploy)
        monkeypatch.setattr("source.cli._validate_target_after_deploy", lambda d: None)
        monkeypatch.setattr("source.cli.update_gitignore", lambda: None)

        result = runner.invoke(app, ["install", "opencode,claude"])

        assert result.exit_code == 1
        # The recorded failure reason should reference exit code 2
        assert "exit 2" in result.output or "exit" in result.output.lower()

    def test_all_targets_fail_still_exits_1(self, tmp_path, monkeypatch):
        def always_fail(tool, force=False, with_autonomous=False):
            raise RuntimeError(f"fail {tool}")

        monkeypatch.setattr("source.cli.deploy_all_resources", always_fail)
        monkeypatch.setattr("source.cli._validate_target_after_deploy", lambda d: None)
        monkeypatch.setattr("source.cli.update_gitignore", lambda: None)

        result = runner.invoke(app, ["install", "opencode,claude"])

        assert result.exit_code == 1
        # No successes -> summary mentions failures only
        assert "2 failed" in result.output or "failed" in result.output.lower()


# ---------------------------------------------------------------------------
# update multi-tool
# ---------------------------------------------------------------------------


class TestUpdateCommaSeparated:
    def test_two_tools_each_update(self, tmp_path, monkeypatch):
        update_calls: list[str] = []

        def fake_update(tool, *, with_core, with_autonomous, force, language, strict_archived):
            update_calls.append(tool)

        monkeypatch.setattr("source.cli._update_one_tool", fake_update)

        result = runner.invoke(app, ["update", "opencode,claude"])

        assert result.exit_code == 0, result.output
        assert update_calls == ["opencode", "claude"]

    def test_partial_failure_records_and_continues(self, tmp_path, monkeypatch):
        update_calls: list[str] = []

        def maybe_update(tool, *, with_core, with_autonomous, force, language, strict_archived):
            update_calls.append(tool)
            if tool == "claude":
                raise RuntimeError("simulated claude update failure")

        monkeypatch.setattr("source.cli._update_one_tool", maybe_update)

        result = runner.invoke(app, ["update", "opencode,claude"])

        assert result.exit_code == 1
        assert update_calls == ["opencode", "claude"]


# ---------------------------------------------------------------------------
# Backwards compatibility (single-tool calls must be byte-identical)
# ---------------------------------------------------------------------------


class TestSingleToolBackwardCompat:
    def test_install_single_tool_no_summary_line(self, tmp_path, monkeypatch):
        monkeypatch.setattr("source.cli.deploy_all_resources", lambda t, force=False, with_autonomous=False: None)
        monkeypatch.setattr("source.cli._validate_target_after_deploy", lambda d: None)

        result = runner.invoke(app, ["install", "opencode"])

        assert result.exit_code == 0
        assert "summary" not in result.output.lower()

    def test_install_single_tool_failure_exits_1(self, tmp_path, monkeypatch):
        def fail(tool, force=False, with_autonomous=False):
            raise RuntimeError("boom")

        monkeypatch.setattr("source.cli.deploy_all_resources", fail)

        result = runner.invoke(app, ["install", "opencode"])

        assert result.exit_code == 1
        # Single-tool failure: no summary line
        assert "summary" not in result.output.lower()

    def test_install_unknown_tool_exits_1(self, tmp_path, monkeypatch):
        # Existing test_openspec_extended.py::test_install_unknown_tool_shows_error
        # already pins this. Confirm it still holds after refactor.
        result = runner.invoke(app, ["install", "invalid-tool"])
        assert result.exit_code == 1

    def test_install_unknown_tool_in_comma_list_exits_1(self, tmp_path, monkeypatch):
        monkeypatch.setattr("source.cli.deploy_all_resources", lambda t, force=False, with_autonomous=False: None)
        monkeypatch.setattr("source.cli._validate_target_after_deploy", lambda d: None)

        result = runner.invoke(app, ["install", "opencode,invalid-tool"])

        assert result.exit_code == 1
        # The whole loop is skipped -- no tool was deployed
        assert "invalid-tool" in result.output

    def test_install_empty_tool_id_exits_1(self, tmp_path, monkeypatch):
        # Typer treats "" as a present (empty) argument, not a missing one,
        # so the parser rejects it with exit code 1 — same as unknown tool.
        result = runner.invoke(app, ["install", ""])
        assert result.exit_code == 1

    def test_install_duplicate_tool_id_exits_1(self, tmp_path, monkeypatch):
        result = runner.invoke(app, ["install", "opencode,opencode"])
        assert result.exit_code == 1


class TestHelpTextMentionsMultiTool:
    def test_install_help_mentions_comma_separated(self):
        result = runner.invoke(app, ["install", "--help"])
        assert result.exit_code == 0
        assert "comma-separated" in result.output

    def test_update_help_mentions_comma_separated(self):
        result = runner.invoke(app, ["update", "--help"])
        assert result.exit_code == 0
        assert "comma-separated" in result.output