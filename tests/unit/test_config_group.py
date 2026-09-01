#!/usr/bin/env python3
"""
Tests the `openspec-extended config <sub>` Typer sub-app — mirrors the upstream
`openspec config` group. Use `openspec-extended osx schema` for programmatic
schema discovery instead.
"""

import pytest
from typer.testing import CliRunner

from source.cli import app

pytestmark = pytest.mark.mechanism

runner = CliRunner()


class TestConfigGroupRegistration:
    """Tests that the `config` sub-app exposes all eight upstream subcommands."""

    def test_all_subcommands_registered(self) -> None:
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        for sub in ["path", "list", "get", "set", "unset", "reset", "edit", "profile"]:
            assert sub in result.output, f"Missing subcommand: {sub}"


class TestConfigSimpleCommands:
    """Verifies simple `config` subcommands forward to upstream."""

    @staticmethod
    def _capture(monkeypatch):
        from source import cli as cli_module

        captured = {}

        def fake_run_openspec(args, timeout=30):
            captured["args"] = list(args)
            return 0

        monkeypatch.setattr(cli_module, "run_openspec", fake_run_openspec)
        return captured

    def test_path_invokes_openspec(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["config", "path"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"] == ["config", "path"]

    def test_list_forwards_json(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["config", "list", "--json"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"][:2] == ["config", "list"]
        assert "--json" in captured["args"]

    def test_reset_invokes_openspec(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["config", "reset"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"] == ["config", "reset"]

    def test_edit_invokes_openspec(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["config", "edit"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"] == ["config", "edit"]


class TestConfigGetUnsetForwarding:
    """Verifies `config get` and `config unset` forward the key to upstream."""

    @staticmethod
    def _capture(monkeypatch):
        from source import cli as cli_module

        captured = {}

        def fake_run_openspec(args, timeout=30):
            captured["args"] = list(args)
            return 0

        monkeypatch.setattr(cli_module, "run_openspec", fake_run_openspec)
        return captured

    def test_get_forwards_key(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["config", "get", "profile"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"] == ["config", "get", "profile"]

    def test_unset_forwards_key(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["config", "unset", "profile"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"] == ["config", "unset", "profile"]

    def test_get_requires_key(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["config", "get"])
        assert result.exit_code != 0
        assert captured == {}, "Should not invoke openspec when key is missing"


class TestConfigSetForwarding:
    """Verifies `config set` forwards key, value, and flags to upstream."""

    @staticmethod
    def _capture(monkeypatch):
        from source import cli as cli_module

        captured = {}

        def fake_run_openspec(args, timeout=30):
            captured["args"] = list(args)
            return 0

        monkeypatch.setattr(cli_module, "run_openspec", fake_run_openspec)
        return captured

    def test_set_minimal(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["config", "set", "profile", "custom"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"] == ["config", "set", "profile", "custom"]
        assert "--string" not in captured["args"]
        assert "--allow-unknown" not in captured["args"]

    def test_set_with_string_flag(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(
            app, ["config", "set", "defaultSchema", "spec-driven", "--string"]
        )
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"][:4] == ["config", "set", "defaultSchema", "spec-driven"]
        assert "--string" in captured["args"]

    def test_set_with_allow_unknown(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(
            app, ["config", "set", "experimental.flag", "true", "--allow-unknown"]
        )
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"][:4] == ["config", "set", "experimental.flag", "true"]
        assert "--allow-unknown" in captured["args"]


class TestConfigProfileForwarding:
    """Verifies `config profile` forwards optional preset to upstream."""

    @staticmethod
    def _capture(monkeypatch):
        from source import cli as cli_module

        captured = {}

        def fake_run_openspec(args, timeout=30):
            captured["args"] = list(args)
            return 0

        monkeypatch.setattr(cli_module, "run_openspec", fake_run_openspec)
        return captured

    def test_profile_no_preset(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["config", "profile"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"] == ["config", "profile"]

    def test_profile_with_preset(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["config", "profile", "custom"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"] == ["config", "profile", "custom"]
