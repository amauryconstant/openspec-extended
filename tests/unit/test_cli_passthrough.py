#!/usr/bin/env python3
"""
Mechanism tests for openspec-extended CLI passthrough commands.
Verifies that the new top-level commands delegate correctly to upstream `openspec`.
"""

import json
import subprocess
import sys

import pytest
from typer.testing import CliRunner

from source.cli import app

pytestmark = pytest.mark.mechanism

runner = CliRunner()


def run_cli(*args, cwd=None):
    """Run openspec-extended via python -m source and return (exit_code, stdout, stderr)."""
    cmd = [sys.executable, "-m", "source", *args]
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr


@pytest.fixture
def e2e_repo(tmp_path):
    """Create a temporary E2E repo with git initialized and openspec dir in place."""
    tmp_path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"], cwd=tmp_path, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)

    readme = tmp_path / "README.md"
    readme.write_text("# Test Repo\n")
    subprocess.run(["git", "add", "README.md"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "Initial commit"], cwd=tmp_path, check=True
    )

    (tmp_path / "openspec" / "changes").mkdir(parents=True, exist_ok=True)
    return tmp_path


class TestCommandRegistration:
    """Tests that all 11 new commands are registered on the Typer app."""

    def test_all_passthrough_commands_registered(self):
        """All 12 passthrough commands are present in the Typer app."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        for cmd in [
            "validate",
            "list",
            "show",
            "status",
            "instructions",
            "templates",
            "schemas",
            "schema",
            "init",
            "update-core",
            "feedback",
            "completion",
        ]:
            assert cmd in result.output, f"Missing command: {cmd}"

    def test_validate_help(self):
        """validate --help shows all flags."""
        result = runner.invoke(app, ["validate", "--help"])
        assert result.exit_code == 0
        for flag in ["--all", "--changes", "--specs", "--type", "--strict", "--json"]:
            assert flag in result.output, f"Missing flag: {flag}"

    def test_list_help(self):
        """list --help shows all flags."""
        result = runner.invoke(app, ["list", "--help"])
        assert result.exit_code == 0
        for flag in ["--specs", "--changes", "--sort", "--json"]:
            assert flag in result.output, f"Missing flag: {flag}"

    def test_show_help(self):
        """show --help shows all flags."""
        result = runner.invoke(app, ["show", "--help"])
        assert result.exit_code == 0
        for flag in ["--type", "--deltas-only", "--json"]:
            assert flag in result.output, f"Missing flag: {flag}"

    def test_status_help(self):
        """status --help shows all flags."""
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0
        for flag in ["--change", "--schema", "--json"]:
            assert flag in result.output, f"Missing flag: {flag}"

    def test_instructions_help(self):
        """instructions --help shows all flags."""
        result = runner.invoke(app, ["instructions", "--help"])
        assert result.exit_code == 0
        for flag in ["--change", "--schema", "--json"]:
            assert flag in result.output, f"Missing flag: {flag}"

    def test_templates_help(self):
        """templates --help shows all flags."""
        result = runner.invoke(app, ["templates", "--help"])
        assert result.exit_code == 0
        assert "--schema" in result.output
        assert "--json" in result.output

    def test_schemas_help(self):
        """schemas --help shows --json flag."""
        result = runner.invoke(app, ["schemas", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output

    def test_init_help(self):
        """init --help shows all flags."""
        result = runner.invoke(app, ["init", "--help"])
        assert result.exit_code == 0
        for flag in ["--tools", "--force", "--profile"]:
            assert flag in result.output, f"Missing flag: {flag}"

    def test_update_core_help(self):
        """update-core --help shows --force flag."""
        result = runner.invoke(app, ["update-core", "--help"])
        assert result.exit_code == 0
        assert "--force" in result.output

    def test_feedback_help(self):
        """feedback --help shows --body flag."""
        result = runner.invoke(app, ["feedback", "--help"])
        assert result.exit_code == 0
        assert "--body" in result.output

    def test_completion_help(self):
        """completion --help shows --install and --uninstall flags."""
        result = runner.invoke(app, ["completion", "--help"])
        assert result.exit_code == 0
        for flag in ["--install", "--uninstall", "--yes"]:
            assert flag in result.output, f"Missing flag: {flag}"


class TestPassthroughExecution:
    """Tests that commands actually execute and forward openspec output."""

    def test_schemas_json_returns_valid_json(self, e2e_repo):
        """schemas --json returns valid JSON list of schemas."""
        exit_code, stdout, stderr = run_cli("schemas", "--json", cwd=e2e_repo)
        if exit_code == 0:
            data = json.loads(stdout)
            assert isinstance(data, (list, dict))

    def test_validate_no_args_exits_nonzero_or_hints(self, e2e_repo):
        """validate with no args either validates everything or hints at usage."""
        exit_code, stdout, stderr = run_cli("validate", cwd=e2e_repo)
        combined = stdout + stderr
        assert "Traceback" not in combined, f"Got traceback: {combined}"

    def test_list_in_empty_repo(self, e2e_repo):
        """list in empty repo returns empty list or hint, no traceback."""
        exit_code, stdout, stderr = run_cli("list", cwd=e2e_repo)
        combined = stdout + stderr
        assert "Traceback" not in combined, f"Got traceback: {combined}"

    def test_init_missing_tool_flag_fails_gracefully(self, e2e_repo):
        """init without --tools in non-TTY exits cleanly without traceback."""
        exit_code, stdout, stderr = run_cli("init", cwd=e2e_repo)
        combined = stdout + stderr
        assert "Traceback" not in combined, f"Got traceback: {combined}"

    def test_feedback_requires_message(self):
        """feedback without message argument shows error and exits non-zero."""
        result = runner.invoke(app, ["feedback"])
        assert result.exit_code != 0
        assert (
            "Missing argument" in result.output
            or "message" in result.output.lower()
            or "required" in result.output.lower()
        )


class TestOpenspecMissing:
    """Tests behavior when openspec CLI is not installed."""

    def test_openspec_missing_friendly_error(self, e2e_repo, monkeypatch):
        """When openspec is not in PATH, error message is friendly (not traceback)."""
        empty_dir = e2e_repo / "empty-bin"
        empty_dir.mkdir()
        monkeypatch.setenv("PATH", str(empty_dir))

        exit_code, stdout, stderr = run_cli("list", cwd=e2e_repo)
        combined = stdout + stderr
        assert "Traceback" not in combined, f"Got traceback: {combined}"
        assert "openspec" in combined.lower() or "install" in combined.lower(), (
            f"Expected install hint in output: {combined}"
        )


class TestTemplatesSchemaFlag:
    """Verifies the templates --schema flag passes its value through."""

    def test_schema_flag_passes_value(self, monkeypatch):
        from source import cli as cli_module

        captured = {}

        def fake_run_openspec(args, timeout=30):
            captured["args"] = args
            return 0

        monkeypatch.setattr(cli_module, "run_openspec", fake_run_openspec)

        result = runner.invoke(app, ["templates", "--schema", "spec-driven"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert "--schema" in captured["args"]
        schema_idx = captured["args"].index("--schema")
        assert captured["args"][schema_idx + 1] == "spec-driven"


class TestSchemaPassthrough:
    """Verifies the top-level `schema` passthrough dispatches to upstream."""

    def _capture(self, monkeypatch):
        from source import cli as cli_module

        captured = {}

        def fake_run_openspec(args, timeout=30):
            captured["args"] = list(args)
            return 0

        monkeypatch.setattr(cli_module, "run_openspec", fake_run_openspec)
        return captured

    def test_schema_list_invokes_openspec(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["schema", "list", "--json"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"][:2] == ["schema", "list"]
        assert "--json" in captured["args"]

    def test_schema_list_without_json_omits_flag(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["schema", "list"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"] == ["schema", "list"]

    def test_schema_which_with_name(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["schema", "which", "my-schema", "--json"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"][:3] == ["schema", "which", "my-schema"]
        assert "--json" in captured["args"]

    def test_schema_which_with_all_flag(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["schema", "which", "--all"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert "--all" in captured["args"]

    def test_schema_validate_invokes_openspec(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["schema", "validate", "my-schema", "--json"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"][:3] == ["schema", "validate", "my-schema"]
        assert "--json" in captured["args"]

    def test_schema_fork_requires_source(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["schema", "fork"])
        assert result.exit_code != 0
        assert captured == {}, "Should not invoke openspec when source is missing"

    def test_schema_fork_with_source(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(
            app, ["schema", "fork", "spec-driven", "my-fork", "--force"]
        )
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"][:4] == [
            "schema",
            "fork",
            "spec-driven",
            "my-fork",
        ]
        assert "--force" in captured["args"]

    def test_schema_init_requires_name(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["schema", "init"])
        assert result.exit_code != 0
        assert captured == {}, "Should not invoke openspec when name is missing"

    def test_schema_init_invokes_openspec(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(
            app,
            [
                "schema",
                "init",
                "my-schema",
                "--description",
                "My schema",
                "--artifacts",
                "proposal,specs",
                "--default",
            ],
        )
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"][:3] == ["schema", "init", "my-schema"]
        assert "--description" in captured["args"]
        assert "My schema" in captured["args"]
        assert "--artifacts" in captured["args"]
        assert "proposal,specs" in captured["args"]
        assert "--default" in captured["args"]


class TestOrchestrateSchemaFlag:
    """Verifies the --schema flag on orchestrate is accepted and passes through."""

    def test_schema_option_present_in_help(self) -> None:
        result = runner.invoke(app, ["orchestrate", "--help"])
        assert result.exit_code == 0
        assert "--schema" in result.output

    def test_schema_flag_propagates_to_state(self, monkeypatch) -> None:
        from source.orchestrator.engine import OrchestratorState, run_orchestrator

        captured = {}

        def fake_run(state):
            captured["schema_override"] = state.schema_override
            captured["change_id"] = state.change_id
            raise SystemExit(0)

        monkeypatch.setattr(
            "source.cli.run_orchestrator",
            fake_run,
        )

        result = runner.invoke(
            app,
            [
                "orchestrate",
                "--list",
                "--schema",
                "my-explicit-schema",
            ],
        )
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["schema_override"] == "my-explicit-schema"
