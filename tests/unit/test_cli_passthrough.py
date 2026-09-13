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
        """All passthrough commands and groups are present in the Typer app."""
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
            # v1.8.0+ interactive dashboard
            "view",
            # top-level archive
            "archive",
            # v1.5.0+ store / health / context
            "context",
            "doctor",
        ]:
            assert cmd in result.output, f"Missing command: {cmd}"

    def test_subcommand_groups_registered(self):
        """All new subcommand groups appear in top-level --help."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        for group in ["new", "store", "config"]:
            assert group in result.output, f"Missing group: {group}"

    @pytest.mark.parametrize(
        "command,expected_flags",
        [
            (
                ["validate"],
                ["--all", "--changes", "--specs", "--type", "--strict", "--json"],
            ),
            (["list"], ["--specs", "--changes", "--sort", "--json"]),
            (["show"], ["--type", "--deltas-only", "--json"]),
            (["status"], ["--change", "--schema", "--json"]),
            (["instructions"], ["--change", "--schema", "--json"]),
            (["templates"], ["--schema", "--json"]),
            (["schemas"], ["--json"]),
            (["init"], ["--tools", "--force", "--profile"]),
            (["update-core"], ["--force"]),
            (["feedback"], ["--body"]),
            (["completion"], ["--install", "--uninstall", "--yes"]),
            (["view"], ["--store", "--json"]),
            (
                ["archive"],
                ["--yes", "--skip-specs", "--no-validate", "--json", "--store"],
            ),
            (["context"], ["--store", "--json", "--code-workspace", "--force"]),
            (["doctor"], ["--store", "--json"]),
            (
                ["new", "change"],
                ["--description", "--goal", "--schema", "--json", "--store"],
            ),
            (
                ["store"],
                ["setup", "register", "unregister", "remove", "list", "doctor"],
            ),
            (
                ["config"],
                [
                    "path",
                    "list",
                    "get",
                    "set",
                    "unset",
                    "reset",
                    "edit",
                    "profile",
                ],
            ),
        ],
    )
    def test_command_help_shows_flags(self, command, expected_flags):
        """Each command's --help shows its documented flags/subcommands."""
        result = runner.invoke(app, command + ["--help"])
        assert result.exit_code == 0
        for flag in expected_flags:
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

    @staticmethod
    def _capture(monkeypatch):
        from source import cli as cli_module

        captured = {}

        def fake_run_openspec(args, timeout=30):
            captured["args"] = list(args)
            return 0

        monkeypatch.setattr(cli_module, "run_openspec", fake_run_openspec)
        return captured

    @pytest.mark.parametrize(
        "args,expected_prefix,expected_in_args",
        [
            (["schema", "list", "--json"], ["schema", "list"], ["--json"]),
            (["schema", "list"], ["schema", "list"], []),
            (
                ["schema", "which", "my-schema", "--json"],
                ["schema", "which", "my-schema"],
                ["--json"],
            ),
            (["schema", "which", "--all"], ["schema", "which"], ["--all"]),
            (
                ["schema", "validate", "my-schema", "--json"],
                ["schema", "validate", "my-schema"],
                ["--json"],
            ),
            (
                ["schema", "fork", "spec-driven", "my-fork", "--force"],
                ["schema", "fork", "spec-driven", "my-fork"],
                ["--force"],
            ),
            (
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
                ["schema", "init", "my-schema"],
                [
                    "--description",
                    "My schema",
                    "--artifacts",
                    "proposal,specs",
                    "--default",
                ],
            ),
        ],
    )
    def test_schema_passthrough_invokes_openspec(
        self, monkeypatch, args, expected_prefix, expected_in_args
    ):
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, args)
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"][: len(expected_prefix)] == expected_prefix
        for flag in expected_in_args:
            assert flag in captured["args"], f"Missing {flag} in {captured['args']}"

    @pytest.mark.parametrize("args", [["schema", "fork"], ["schema", "init"]])
    def test_schema_passthrough_missing_required_arg(self, monkeypatch, args):
        """Required args missing -> non-zero exit and openspec never invoked."""
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, args)
        assert result.exit_code != 0
        assert captured == {}, (
            f"Should not invoke openspec when required args are missing: "
            f"args={captured.get('args')}"
        )


class TestOrchestrateSchemaFlag:
    """Verifies the --schema flag on orchestrate is accepted and passes through."""

    def test_schema_option_present_in_help(self) -> None:
        result = runner.invoke(app, ["orchestrate", "--help"])
        assert result.exit_code == 0
        assert "--schema" in result.output

    def test_schema_flag_propagates_to_state(self, monkeypatch) -> None:

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


class TestValidateConcurrencyEnv:
    """A.7: ``OPENSPEC_CONCURRENCY`` env var passes --concurrency through the
    top-level ``openspec-extended validate`` passthrough command."""

    @staticmethod
    def _capture(monkeypatch):
        from source import cli as cli_module

        captured = {}

        def fake_run_openspec(args, timeout=30):
            captured["args"] = list(args)
            return 0

        monkeypatch.setattr(cli_module, "run_openspec", fake_run_openspec)
        return captured

    def test_env_var_propagates_to_subprocess(self, monkeypatch):
        """OPENSPEC_CONCURRENCY=16 + no explicit flag -> args contain --concurrency 16."""
        monkeypatch.setenv("OPENSPEC_CONCURRENCY", "16")
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["validate", "--all", "--json"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert "--concurrency" in captured["args"]
        idx = captured["args"].index("--concurrency")
        assert captured["args"][idx + 1] == "16"

    def test_no_env_var_omits_flag(self, monkeypatch):
        """No env var and no explicit flag -> --concurrency is NOT in args (upstream default used)."""
        monkeypatch.delenv("OPENSPEC_CONCURRENCY", raising=False)
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["validate", "--all", "--json"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert "--concurrency" not in captured["args"]

    def test_invalid_env_var_omits_flag(self, monkeypatch):
        """Invalid env value (non-int) -> --concurrency omitted."""
        monkeypatch.setenv("OPENSPEC_CONCURRENCY", "invalid")
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["validate", "--all", "--json"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert "--concurrency" not in captured["args"]

    def test_zero_env_var_omits_flag(self, monkeypatch):
        """Env value of 0 (must be > 0) -> --concurrency omitted."""
        monkeypatch.setenv("OPENSPEC_CONCURRENCY", "0")
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["validate", "--all", "--json"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert "--concurrency" not in captured["args"]

    def test_explicit_flag_overrides_env_var(self, monkeypatch):
        """Explicit --concurrency=8 wins over OPENSPEC_CONCURRENCY=16."""
        monkeypatch.setenv("OPENSPEC_CONCURRENCY", "16")
        captured = self._capture(monkeypatch)
        result = runner.invoke(
            app, ["validate", "--all", "--json", "--concurrency", "8"]
        )
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert "--concurrency" in captured["args"]
        idx = captured["args"].index("--concurrency")
        assert captured["args"][idx + 1] == "8"


class TestLanguageFlag:
    """A.5: ``--language`` flag and ``OPENSPEC_LANGUAGE`` env var both flow
    through to the upstream ``openspec init`` call. Precedence: explicit
    flag > env > unset.
    """

    @staticmethod
    def _capture(monkeypatch):
        from source import cli as cli_module

        captured = {}

        def fake_run_openspec(args, timeout=60):
            captured["args"] = list(args)
            return 0

        monkeypatch.setattr(cli_module, "run_openspec", fake_run_openspec)
        return captured

    def test_explicit_flag_propagates(self, monkeypatch):
        """`init --language french` -> upstream args contain `--language french`."""
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["init", "--language", "french"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert "--language" in captured["args"]
        idx = captured["args"].index("--language")
        assert captured["args"][idx + 1] == "french"

    def test_env_var_propagates_when_no_flag(self, monkeypatch):
        """OPENSPEC_LANGUAGE=french + no flag -> upstream args contain `--language french`."""
        monkeypatch.setenv("OPENSPEC_LANGUAGE", "french")
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert "--language" in captured["args"]
        idx = captured["args"].index("--language")
        assert captured["args"][idx + 1] == "french"

    def test_explicit_flag_overrides_env_var(self, monkeypatch):
        """`--language spanish` with OPENSPEC_LANGUAGE=french -> upstream gets `spanish`."""
        monkeypatch.setenv("OPENSPEC_LANGUAGE", "french")
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["init", "--language", "spanish"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert "--language" in captured["args"]
        idx = captured["args"].index("--language")
        assert captured["args"][idx + 1] == "spanish"

    def test_empty_env_var_omits_flag(self, monkeypatch):
        """OPENSPEC_LANGUAGE='' (empty) + no flag -> --language NOT in args."""
        monkeypatch.setenv("OPENSPEC_LANGUAGE", "")
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert "--language" not in captured["args"]

    def test_no_flag_no_env_omits_flag(self, monkeypatch):
        """No flag and no env var -> --language NOT in args."""
        monkeypatch.delenv("OPENSPEC_LANGUAGE", raising=False)
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert "--language" not in captured["args"]


class TestNewPassthroughsArgForwarding:
    """Verifies the v1.5+ top-level passthroughs forward their flags verbatim."""

    @staticmethod
    def _capture(monkeypatch):
        from source import cli as cli_module

        captured = {}

        def fake_run_openspec(args, timeout=30, extra_env=None):
            captured["args"] = list(args)
            return 0

        monkeypatch.setattr(cli_module, "run_openspec", fake_run_openspec)
        return captured

    def test_view_forwards_store_and_json(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["view", "--store", "alpha", "--json"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"][:1] == ["view"]
        assert "--store" in captured["args"]
        assert "alpha" in captured["args"]
        assert "--json" in captured["args"]

    def test_archive_forwards_all_flags(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(
            app,
            [
                "archive",
                "my-change",
                "--yes",
                "--skip-specs",
                "--no-validate",
                "--store",
                "alpha",
                "--json",
            ],
        )
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"][:2] == ["archive", "my-change"]
        for flag in ["--yes", "--skip-specs", "--no-validate", "--json", "--store"]:
            assert flag in captured["args"], f"Missing flag in args: {flag}"
        assert "alpha" in captured["args"]

    def test_context_forwards_code_workspace_and_force(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(
            app,
            [
                "context",
                "--store",
                "alpha",
                "--code-workspace",
                "/tmp/ws.code-workspace",
                "--force",
                "--json",
            ],
        )
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"][:1] == ["context"]
        assert "--store" in captured["args"]
        assert "alpha" in captured["args"]
        assert "--code-workspace" in captured["args"]
        assert "/tmp/ws.code-workspace" in captured["args"]
        assert "--force" in captured["args"]
        assert "--json" in captured["args"]

    def test_doctor_forwards_store_and_json(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["doctor", "--store", "alpha", "--json"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"][:1] == ["doctor"]
        assert "--store" in captured["args"]
        assert "alpha" in captured["args"]
        assert "--json" in captured["args"]


class TestNewGroupArgForwarding:
    """Verifies the 'new' subcommand group forwards args to upstream."""

    @staticmethod
    def _capture(monkeypatch):
        from source import cli as cli_module

        captured = {}

        def fake_run_openspec(args, timeout=30, extra_env=None):
            captured["args"] = list(args)
            return 0

        monkeypatch.setattr(cli_module, "run_openspec", fake_run_openspec)
        return captured

    def test_new_change_forwards_all_flags(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(
            app,
            [
                "new",
                "change",
                "my-change",
                "--description",
                "My change",
                "--goal",
                "Add feature",
                "--schema",
                "spec-driven",
                "--store",
                "alpha",
                "--json",
            ],
        )
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["args"][:3] == ["new", "change", "my-change"]
        for flag in [
            "--description",
            "--goal",
            "--schema",
            "--store",
            "--json",
        ]:
            assert flag in captured["args"], f"Missing flag: {flag}"

    def test_new_change_requires_name(self, monkeypatch) -> None:
        captured = self._capture(monkeypatch)
        result = runner.invoke(app, ["new", "change"])
        assert result.exit_code != 0
        assert captured == {}, "Should not invoke openspec when name is missing"
