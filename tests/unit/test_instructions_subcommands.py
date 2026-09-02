#!/usr/bin/env python3
"""Tests for `osx instructions` subcommand and `fetch_instructions` library helper."""

import json
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from source.lib import osx as osx_lib
from source.lib.osx import OSXError, fetch_instructions
from source.osx_cli import osx_app

runner = CliRunner()


@pytest.fixture
def mock_json(monkeypatch):
    """Mock _run_openspec_json to capture argv and return canned payload."""
    captured: dict = {}

    def _fake(args, timeout=10):
        captured["args"] = list(args)
        captured["timeout"] = timeout
        return captured.get("payload", {})

    monkeypatch.setattr(osx_lib, "_run_openspec_json", _fake)
    return captured


@pytest.mark.unit
class TestFetchInstructions:
    """Library function: `fetch_instructions(operation, change_id, store=None)`."""

    def test_returns_envelope(self, mock_json) -> None:
        mock_json["payload"] = {
            "changeName": "add-auth",
            "context": "project context",
            "operationGuidance": ["advisory 1", "advisory 2"],
        }
        result = fetch_instructions("archive", "add-auth")
        assert result["changeName"] == "add-auth"
        assert result["operationGuidance"] == ["advisory 1", "advisory 2"]

    def test_propagates_store(self, mock_json) -> None:
        mock_json["payload"] = {"ok": True}
        fetch_instructions("proposal", "my-change", store="my-store")
        assert "--store" in mock_json["args"]
        assert "my-store" in mock_json["args"]

    def test_args_shape(self, mock_json) -> None:
        mock_json["payload"] = {}
        fetch_instructions("apply", "my-change")
        assert mock_json["args"] == ["instructions", "apply", "--change", "my-change"]
        assert mock_json["timeout"] == 30

    def test_raises_on_cli_error(self, mock_json, monkeypatch) -> None:
        def _raise(args, timeout=10):
            raise OSXError("cli_error", "openspec failed", args=args)

        monkeypatch.setattr(osx_lib, "_run_openspec_json", _raise)
        with pytest.raises(OSXError) as exc_info:
            fetch_instructions("archive", "missing-change")
        assert exc_info.value.code == "cli_error"

    def test_raises_on_cli_not_found(self, mock_json, monkeypatch) -> None:
        def _raise(args, timeout=10):
            raise OSXError("cli_not_found", "openspec CLI not found in PATH")

        monkeypatch.setattr(osx_lib, "_run_openspec_json", _raise)
        with pytest.raises(OSXError) as exc_info:
            fetch_instructions("proposal", "my-change")
        assert exc_info.value.code == "cli_not_found"


@pytest.mark.unit
class TestOsxInstructions:
    """CLI: `osx instructions <operation> --change <change_id>`."""

    def test_proposal_invokes_fetch_instructions(self) -> None:
        with patch(
            "source.osx_cli.osx_lib.fetch_instructions",
            return_value={"changeName": "x", "operationGuidance": []},
        ) as mock:
            result = runner.invoke(
                osx_app, ["instructions", "proposal", "--change", "x"]
            )
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert mock.called
        call_args = mock.call_args
        assert call_args[0][0] == "proposal"
        assert call_args[0][1] == "x"

    def test_archive_invokes_fetch_instructions(self) -> None:
        """The archive operation routes through the same library helper
        (no special-casing) — the value is structured error handling."""
        with patch(
            "source.osx_cli.osx_lib.fetch_instructions",
            return_value={"changeName": "x", "operationGuidance": ["a"]},
        ) as mock:
            result = runner.invoke(
                osx_app, ["instructions", "archive", "--change", "x"]
            )
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert mock.called
        call_args = mock.call_args
        assert call_args[0][0] == "archive"
        assert call_args[0][1] == "x"

    def test_apply_invokes_fetch_instructions(self) -> None:
        with patch(
            "source.osx_cli.osx_lib.fetch_instructions",
            return_value={"changeName": "x", "operationGuidance": []},
        ) as mock:
            result = runner.invoke(
                osx_app, ["instructions", "apply", "--change", "x"]
            )
        assert result.exit_code == 0
        assert mock.call_args[0][0] == "apply"

    def test_missing_change_exits_nonzero(self) -> None:
        """--change is required (was optional in the old passthrough, but
        the library function requires it and the new CLI surfaces the
        requirement at the Typer layer rather than letting upstream fail
        with a cryptic error)."""
        result = runner.invoke(osx_app, ["instructions", "proposal"])
        assert result.exit_code != 0

    def test_cli_error_surfaces_as_json_on_stderr(self) -> None:
        with patch(
            "source.osx_cli.osx_lib.fetch_instructions",
            side_effect=OSXError("cli_error", "openspec failed"),
        ):
            result = runner.invoke(
                osx_app, ["instructions", "archive", "--change", "x"]
            )
        assert result.exit_code == 1
        parsed = json.loads(result.stderr)
        assert parsed["error"] == "cli_error"

    def test_cli_not_found_surfaces_as_json_on_stderr(self) -> None:
        with patch(
            "source.osx_cli.osx_lib.fetch_instructions",
            side_effect=OSXError("cli_not_found", "openspec CLI not found"),
        ):
            result = runner.invoke(
                osx_app, ["instructions", "proposal", "--change", "x"]
            )
        assert result.exit_code == 1
        parsed = json.loads(result.stderr)
        assert parsed["error"] == "cli_not_found"

    def test_output_is_valid_json_envelope(self) -> None:
        with patch(
            "source.osx_cli.osx_lib.fetch_instructions",
            return_value={
                "changeName": "x",
                "context": "ctx",
                "operationGuidance": ["g1"],
            },
        ):
            result = runner.invoke(
                osx_app, ["instructions", "archive", "--change", "x"]
            )
        assert result.exit_code == 0
        payload = json.loads(result.stdout)
        assert payload["changeName"] == "x"
        assert payload["operationGuidance"] == ["g1"]
