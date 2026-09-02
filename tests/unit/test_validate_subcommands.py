#!/usr/bin/env python3
"""
Unit tests for the new osx validate subcommands.

Tests via Typer's CliRunner, mocking the underlying library functions.
"""

import json
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from source.osx_cli import osx_app

runner = CliRunner()


def _make_validation_payload(valid=True):
    """Sample payload from _translate_validate_payload."""
    return {
        "valid": valid,
        "errors": [] if valid else [{"check": "spec:requirements", "message": "fail"}],
        "warnings": [],
        "info": [],
        "items": [{"id": "x", "type": "change", "valid": valid, "issues": []}],
        "summary": {
            "totals": {
                "items": 1,
                "passed": 1 if valid else 0,
                "failed": 0 if valid else 1,
            }
        },
        "root": {},
    }


@pytest.mark.unit
class TestOsxValidateChange:
    def test_calls_validate_change_with_id(self):
        with patch("source.osx_cli.osx_lib.validate_change") as mock:
            mock.return_value = _make_validation_payload(valid=True)
            result = runner.invoke(osx_app, ["validate", "change", "my-change"])
        assert mock.called
        call_args = mock.call_args
        assert call_args[0][0] == "my-change"
        assert result.exit_code == 0

    def test_exits_nonzero_on_validation_failure(self):
        with patch("source.osx_cli.osx_lib.validate_change") as mock:
            mock.return_value = _make_validation_payload(valid=False)
            result = runner.invoke(osx_app, ["validate", "change", "bad-change"])
        assert result.exit_code == 1
        payload = json.loads(result.stdout)
        assert payload["valid"] is False

    def test_missing_target_errors(self):
        result = runner.invoke(osx_app, ["validate", "change"])
        assert result.exit_code == 1
        assert "missing_field" in result.stderr or "change id required" in result.stderr

    def test_passes_strict_flag(self):
        with patch("source.osx_cli.osx_lib.validate_change") as mock:
            mock.return_value = _make_validation_payload()
            runner.invoke(osx_app, ["validate", "change", "c", "--strict"])
        assert mock.call_args.kwargs.get("strict") is True


@pytest.mark.unit
class TestOsxValidateSpec:
    def test_calls_validate_spec_with_id(self):
        with patch("source.osx_cli.osx_lib.validate_spec") as mock:
            mock.return_value = _make_validation_payload(valid=True)
            result = runner.invoke(osx_app, ["validate", "spec", "auth"])
        assert mock.called
        assert mock.call_args[0][0] == "auth"
        assert result.exit_code == 0

    def test_missing_target_errors(self):
        result = runner.invoke(osx_app, ["validate", "spec"])
        assert result.exit_code == 1

    def test_passes_strict_flag(self):
        with patch("source.osx_cli.osx_lib.validate_spec") as mock:
            mock.return_value = _make_validation_payload()
            runner.invoke(osx_app, ["validate", "spec", "auth", "--strict"])
        assert mock.call_args.kwargs.get("strict") is True


@pytest.mark.unit
class TestOsxValidateAll:
    def test_calls_validate_all(self):
        with patch("source.osx_cli.osx_lib.validate_all") as mock:
            mock.return_value = _make_validation_payload(valid=True)
            result = runner.invoke(osx_app, ["validate", "all"])
        assert mock.called
        assert result.exit_code == 0

    def test_default_concurrency_is_none(self):
        """Without --concurrency or env var, osx_cli passes None and lets
        ``validate_all`` resolve OPENSPEC_CONCURRENCY (or fall back to 6)."""
        with patch("source.osx_cli.osx_lib.validate_all") as mock:
            mock.return_value = _make_validation_payload()
            runner.invoke(osx_app, ["validate", "all"])
        assert mock.call_args.kwargs.get("concurrency") is None

    def test_default_concurrency_env_falls_back_in_library(self, monkeypatch):
        """Without an explicit flag, the library resolves env-driven concurrency."""
        monkeypatch.setenv("OPENSPEC_CONCURRENCY", "12")
        with patch(
            "source.osx_cli.osx_lib.validate_all", side_effect=_make_validation_payload()
        ) as mock:
            runner.invoke(osx_app, ["validate", "all"])
        assert mock.call_args.kwargs.get("concurrency") is None
        # The library call itself received None; the env var is read inside validate_all.

    def test_custom_concurrency(self):
        with patch("source.osx_cli.osx_lib.validate_all") as mock:
            mock.return_value = _make_validation_payload()
            runner.invoke(osx_app, ["validate", "all", "--concurrency", "12"])
        assert mock.call_args.kwargs.get("concurrency") == 12

    def test_passes_strict_flag(self):
        with patch("source.osx_cli.osx_lib.validate_all") as mock:
            mock.return_value = _make_validation_payload()
            runner.invoke(osx_app, ["validate", "all", "--strict"])
        assert mock.call_args.kwargs.get("strict") is True


@pytest.mark.unit
class TestOsxValidateChangesOnly:
    def test_calls_validate_changes_only(self):
        with patch("source.osx_cli.osx_lib.validate_changes_only") as mock:
            mock.return_value = _make_validation_payload()
            result = runner.invoke(osx_app, ["validate", "changes"])
        assert mock.called
        assert result.exit_code == 0

    def test_passes_strict_flag(self):
        with patch("source.osx_cli.osx_lib.validate_changes_only") as mock:
            mock.return_value = _make_validation_payload()
            runner.invoke(osx_app, ["validate", "changes", "--strict"])
        assert mock.call_args.kwargs.get("strict") is True


@pytest.mark.unit
class TestOsxValidateSpecsOnly:
    def test_calls_validate_specs_only(self):
        with patch("source.osx_cli.osx_lib.validate_specs_only") as mock:
            mock.return_value = _make_validation_payload()
            result = runner.invoke(osx_app, ["validate", "specs"])
        assert mock.called
        assert result.exit_code == 0

    def test_passes_strict_flag(self):
        with patch("source.osx_cli.osx_lib.validate_specs_only") as mock:
            mock.return_value = _make_validation_payload()
            runner.invoke(osx_app, ["validate", "specs", "--strict"])
        assert mock.call_args.kwargs.get("strict") is True


@pytest.mark.unit
class TestOsxValidateArchived:
    """`osx validate archived [--change <id>]` (v1.9.0+ scope)."""

    def test_archived_default_scope(self):
        with patch("source.osx_cli.osx_lib.validate_archived") as mock:
            mock.return_value = _make_validation_payload(valid=True)
            result = runner.invoke(osx_app, ["validate", "archived"])
        assert mock.called
        # First positional arg is the change_id (None when not provided)
        assert mock.call_args[0][0] is None
        assert result.exit_code == 0

    def test_archived_specific_change_positional(self):
        with patch("source.osx_cli.osx_lib.validate_archived") as mock:
            mock.return_value = _make_validation_payload(valid=True)
            result = runner.invoke(
                osx_app, ["validate", "archived", "my-change"]
            )
        assert mock.called
        assert mock.call_args[0][0] == "my-change"
        assert result.exit_code == 0

    def test_archived_specific_change_flag(self):
        with patch("source.osx_cli.osx_lib.validate_archived") as mock:
            mock.return_value = _make_validation_payload(valid=True)
            result = runner.invoke(
                osx_app, ["validate", "archived", "--change", "my-change"]
            )
        assert mock.called
        assert mock.call_args[0][0] == "my-change"
        assert result.exit_code == 0

    def test_archived_strict_flag_propagates(self):
        with patch("source.osx_cli.osx_lib.validate_archived") as mock:
            mock.return_value = _make_validation_payload(valid=True)
            runner.invoke(osx_app, ["validate", "archived", "--strict"])
        assert mock.call_args.kwargs.get("strict") is True

    def test_archived_exits_nonzero_on_failure(self):
        with patch("source.osx_cli.osx_lib.validate_archived") as mock:
            mock.return_value = _make_validation_payload(valid=False)
            result = runner.invoke(osx_app, ["validate", "archived"])
        assert result.exit_code == 1
        payload = json.loads(result.stdout)
        assert payload["valid"] is False


@pytest.mark.unit
class TestOsxValidateErrorFormat:
    def test_invalid_action_lists_all_actions(self):
        result = runner.invoke(osx_app, ["validate", "bogus"])
        assert result.exit_code == 1
        assert "change" in result.stderr
        assert "spec" in result.stderr
        assert "all" in result.stderr

    def test_prevalidation_error_shape(self):
        payload = {
            "valid": False,
            "errors": [{"check": "no_openspec_root", "message": "no root"}],
            "warnings": [],
            "info": [],
            "diagnostics": [
                {"code": "no_openspec_root", "message": "no root", "fix": "init"}
            ],
        }
        with patch("source.osx_cli.osx_lib.validate_change") as mock:
            mock.return_value = payload
            result = runner.invoke(osx_app, ["validate", "change", "c"])
        assert result.exit_code == 1
        parsed = json.loads(result.stdout)
        assert parsed["diagnostics"][0]["code"] == "no_openspec_root"


@pytest.mark.unit
class TestOsxStoreEnvFallback:
    """M18: the osx CLI callback consults ``OSX_STORE`` env var as a fallback
    when ``--store`` is not passed. This is how the AI subprocess picks up
    the store from the orchestrator's RunRequest without explicit flags."""

    def test_env_var_sets_current_store(self, monkeypatch):
        from source.lib import osx as osx_lib

        captured: dict = {}

        def fake_get():
            captured["store"] = osx_lib.current_store.get()
            return osx_lib.current_store.get()

        monkeypatch.setenv("OSX_STORE", "team-store")
        monkeypatch.setattr(
            osx_lib, "current_store", osx_lib.ContextVar("test", default=None)
        )

        from typer.testing import CliRunner
        from source.osx_cli import osx_app

        r = CliRunner()
        with patch("source.osx_cli.osx_lib.baseline_get", side_effect=fake_get):
            result = r.invoke(osx_app, ["baseline", "get"])
        assert captured["store"] == "team-store"
        assert result.exit_code == 0

    def test_explicit_flag_overrides_env_var(self, monkeypatch):
        from source.lib import osx as osx_lib

        monkeypatch.setenv("OSX_STORE", "env-store")

        from typer.testing import CliRunner
        from source.osx_cli import osx_app

        r = CliRunner()

        captured: dict = {}

        def fake_get():
            captured["store"] = osx_lib.current_store.get()
            return osx_lib.current_store.get()

        with patch("source.osx_cli.osx_lib.baseline_get", side_effect=fake_get):
            result = r.invoke(
                osx_app,
                ["--store", "flag-store", "baseline", "get"],
            )
        assert captured["store"] == "flag-store"
        assert result.exit_code == 0
