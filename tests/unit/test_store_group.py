#!/usr/bin/env python3
"""
Tests the `openspec-extended store <sub>` Typer sub-app — mirrors the upstream
`openspec store` group (v1.5.0+). Coexists with `openspec-extended osx store`
(JSON-only programmatic facade); see `tests/unit/test_store_domain.py`.
"""

import pytest
from typer.testing import CliRunner

from source.cli import app

pytestmark = pytest.mark.mechanism

runner = CliRunner()


class TestStoreGroupRegistration:
    """Tests that the `store` sub-app exposes all six upstream subcommands."""

    def test_all_subcommands_registered(self) -> None:
        result = runner.invoke(app, ["store", "--help"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        for sub in ["setup", "register", "unregister", "remove", "list", "doctor"]:
            assert sub in result.output, f"Missing subcommand: {sub}"


class TestStoreSetupForwarding:
    """Verifies `store setup` forwards its flags to upstream."""

    @staticmethod
    def _capture(monkeypatch):
        from source import cli as cli_module

        captured = {}

        def fake_run_openspec(args, timeout=30):
            captured["args"] = list(args)
            return 0

        monkeypatch.setattr(cli_module, "run_openspec", fake_run_openspec)
        return captured

    def test_setup_default_omits_init_git_flag(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["store", "setup", "alpha", "--path", "/tmp/x"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"] == ["store", "setup", "alpha", "--path", "/tmp/x"]
        assert "--init-git" not in captured["args"]
        assert "--no-init-git" not in captured["args"]

    def test_setup_no_init_git_forwards_flag(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["store", "setup", "--no-init-git"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert "--no-init-git" in captured["args"]


class TestStoreRegisterForwarding:
    """Verifies `store register` forwards its flags to upstream."""

    @staticmethod
    def _capture(monkeypatch):
        from source import cli as cli_module

        captured = {}

        def fake_run_openspec(args, timeout=30):
            captured["args"] = list(args)
            return 0

        monkeypatch.setattr(cli_module, "run_openspec", fake_run_openspec)
        return captured

    def test_register_with_path_and_id(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(
            app, ["store", "register", "/tmp/repo", "--id", "alpha", "--yes"]
        )
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"][:3] == ["store", "register", "/tmp/repo"]
        assert "--id" in captured["args"]
        assert "alpha" in captured["args"]
        assert "--yes" in captured["args"]

    def test_register_without_id_omits_flag(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["store", "register", "/tmp/repo"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert "--id" not in captured["args"]


class TestStoreUnregisterRemoveForwarding:
    """Verifies `store unregister` and `store remove` forward to upstream."""

    @staticmethod
    def _capture(monkeypatch):
        from source import cli as cli_module

        captured = {}

        def fake_run_openspec(args, timeout=30):
            captured["args"] = list(args)
            return 0

        monkeypatch.setattr(cli_module, "run_openspec", fake_run_openspec)
        return captured

    def test_unregister_forwards_id_and_json(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["store", "unregister", "alpha", "--json"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"][:3] == ["store", "unregister", "alpha"]
        assert "--json" in captured["args"]

    def test_remove_forwards_yes(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["store", "remove", "alpha", "--yes"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert "--yes" in captured["args"]

    def test_unregister_requires_id(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["store", "unregister"])
        assert result.exit_code != 0
        assert captured == {}, "Should not invoke openspec when store id is missing"


class TestStoreListDoctorForwarding:
    """Verifies `store list` and `store doctor` forward to upstream."""

    @staticmethod
    def _capture(monkeypatch):
        from source import cli as cli_module

        captured = {}

        def fake_run_openspec(args, timeout=30):
            captured["args"] = list(args)
            return 0

        monkeypatch.setattr(cli_module, "run_openspec", fake_run_openspec)
        return captured

    def test_list_forwards_json(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["store", "list", "--json"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"][:2] == ["store", "list"]
        assert "--json" in captured["args"]

    def test_doctor_with_id(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["store", "doctor", "alpha"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert "alpha" in captured["args"]

    def test_doctor_all_when_no_id(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["store", "doctor"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"] == ["store", "doctor"]