#!/usr/bin/env python3
"""Tests for `osx schema *` subcommands and the schema-aware pre-flight."""

import pytest
from typer.testing import CliRunner

from source.lib import osx as osx_lib
from source.osx_cli import osx_app
from source.orchestrator.engine import OrchestratorState, validate_schema

runner = CliRunner()


@pytest.mark.unit
class TestOsxSchemaSubapp:
    """Tests for `osx schema *` Typer subcommands."""

    def test_schema_which_invokes_library(self, monkeypatch) -> None:
        captured = {}

        def fake(name=None, *, all_schemas=False, store=None):
            captured["fn"] = "schema_which"
            captured["name"] = name
            captured["all_schemas"] = all_schemas
            captured["store"] = store
            return {"name": "spec-driven", "source": "package"}

        monkeypatch.setattr(osx_lib, "schema_which", fake)

        result = runner.invoke(osx_app, ["schema", "which"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["fn"] == "schema_which"
        assert captured["name"] is None
        assert captured["all_schemas"] is False

    def test_schema_which_with_name_and_all(self, monkeypatch) -> None:
        captured = {}

        def fake(name=None, *, all_schemas=False, store=None):
            captured["name"] = name
            captured["all_schemas"] = all_schemas
            return [{"name": "spec-driven", "source": "package"}]

        monkeypatch.setattr(osx_lib, "schema_which", fake)

        result = runner.invoke(osx_app, ["schema", "which", "my-schema", "--all"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["name"] == "my-schema"
        assert captured["all_schemas"] is True

    def test_schema_list_invokes_library(self, monkeypatch) -> None:
        captured = {}

        def fake(*, store=None):
            captured["fn"] = "schema_list"
            captured["store"] = store
            return [{"name": "spec-driven"}]

        monkeypatch.setattr(osx_lib, "schema_list", fake)

        result = runner.invoke(osx_app, ["schema", "list"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["fn"] == "schema_list"

    def test_schema_validate_invokes_library(self, monkeypatch) -> None:
        captured = {}

        def fake(name=None, *, store=None):
            captured["fn"] = "schema_validate"
            captured["name"] = name
            return {"valid": True, "schemas": []}

        monkeypatch.setattr(osx_lib, "schema_validate", fake)

        result = runner.invoke(osx_app, ["schema", "validate", "my-schema"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["fn"] == "schema_validate"
        assert captured["name"] == "my-schema"

    def test_schema_fork_invokes_library(self, monkeypatch) -> None:
        captured = {}

        def fake(source, name=None, *, force=False, store=None):
            captured["fn"] = "schema_fork"
            captured["source"] = source
            captured["name"] = name
            captured["force"] = force
            return {"ok": True}

        monkeypatch.setattr(osx_lib, "schema_fork", fake)

        result = runner.invoke(
            osx_app, ["schema", "fork", "spec-driven", "my-fork", "--force"]
        )
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["source"] == "spec-driven"
        assert captured["name"] == "my-fork"
        assert captured["force"] is True

    def test_schema_init_invokes_library(self, monkeypatch) -> None:
        captured = {}

        def fake(
            name, *, description=None, artifacts=None, set_default=False, force=False, store=None
        ):
            captured["fn"] = "schema_init"
            captured["name"] = name
            captured["description"] = description
            captured["artifacts"] = artifacts
            captured["set_default"] = set_default
            captured["force"] = force
            return {"ok": True}

        monkeypatch.setattr(osx_lib, "schema_init", fake)

        result = runner.invoke(
            osx_app,
            [
                "schema",
                "init",
                "my-schema",
                "--description",
                "My schema",
                "--artifacts",
                "proposal,specs,design",
                "--default",
                "--force",
            ],
        )
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["name"] == "my-schema"
        assert captured["description"] == "My schema"
        assert captured["artifacts"] == ["proposal", "specs", "design"]
        assert captured["set_default"] is True
        assert captured["force"] is True

    def test_schema_init_artifacts_handles_empty(self, monkeypatch) -> None:
        captured = {}

        def fake(
            name, *, description=None, artifacts=None, set_default=False, force=False, store=None
        ):
            captured["artifacts"] = artifacts
            return {"ok": True}

        monkeypatch.setattr(osx_lib, "schema_init", fake)

        result = runner.invoke(osx_app, ["schema", "init", "my-schema"])
        assert result.exit_code == 0, (
            f"Output: {result.output}, Exception: {result.exception}"
        )
        assert captured["artifacts"] is None

    def test_schema_help_shows_subcommands(self) -> None:
        result = runner.invoke(osx_app, ["schema", "--help"])
        assert result.exit_code == 0
        for sub in ["which", "list", "validate", "fork", "init"]:
            assert sub in result.output, f"Missing subcommand: {sub}"


@pytest.mark.unit
class TestValidateSchemaPreflight:
    """Tests for validate_schema() pre-flight function."""

    def _state(self, **kwargs) -> OrchestratorState:
        defaults = {"change_id": "test-change", "no_color": True, "verbose": False}
        defaults.update(kwargs)
        return OrchestratorState(**defaults)

    def test_resolves_default_when_no_config(self, tmp_path, monkeypatch) -> None:
        monkeypatch.chdir(tmp_path)
        state = self._state()
        result = validate_schema(state)
        assert result is True
        assert state.schema_name == "spec-driven"
        assert state.schema_source == "default"

    def test_resolves_from_project_config(self, tmp_path, monkeypatch) -> None:
        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yaml").write_text("schema: my-custom\n")
        monkeypatch.chdir(tmp_path)
        state = self._state()
        result = validate_schema(state)
        assert result is True
        assert state.schema_name == "my-custom"
        assert state.schema_source == "project-config"

    def test_resolves_from_change_metadata(self, tmp_path, monkeypatch) -> None:
        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yaml").write_text("schema: from-config\n")
        change = tmp_path / "openspec" / "changes" / "my-change"
        change.mkdir(parents=True)
        (change / ".openspec.yaml").write_text("schema: from-change\n")
        monkeypatch.chdir(tmp_path)

        state = self._state(change_dir=change)
        result = validate_schema(state)
        assert result is True
        assert state.schema_name == "from-change"
        assert state.schema_source == "change-metadata"

    def test_explicit_override_wins(self, tmp_path, monkeypatch) -> None:
        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yaml").write_text("schema: from-config\n")
        monkeypatch.chdir(tmp_path)

        state = self._state(schema_override="from-cli")
        result = validate_schema(state)
        assert result is True
        assert state.schema_name == "from-cli"
        assert state.schema_source == "explicit"
