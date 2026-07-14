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
        "summary": {"totals": {"items": 1, "passed": 1 if valid else 0, "failed": 0 if valid else 1}},
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

    def test_default_concurrency_is_6(self):
        with patch("source.osx_cli.osx_lib.validate_all") as mock:
            mock.return_value = _make_validation_payload()
            runner.invoke(osx_app, ["validate", "all"])
        assert mock.call_args.kwargs.get("concurrency") == 6

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
            "diagnostics": [{"code": "no_openspec_root", "message": "no root", "fix": "init"}],
        }
        with patch("source.osx_cli.osx_lib.validate_change") as mock:
            mock.return_value = payload
            result = runner.invoke(osx_app, ["validate", "change", "c"])
        assert result.exit_code == 1
        parsed = json.loads(result.stdout)
        assert parsed["diagnostics"][0]["code"] == "no_openspec_root"