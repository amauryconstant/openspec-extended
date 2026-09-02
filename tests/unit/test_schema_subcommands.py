#!/usr/bin/env python3
"""Tests for openspec schema * subprocess wrappers."""

import pytest

from source.lib import osx as osx_lib
from source.lib.osx import (
    OSXError,
    schema_fork,
    schema_fork_diff,
    schema_init,
    schema_list,
    schema_validate,
    schema_which,
)


@pytest.fixture
def mock_json(monkeypatch):
    """Mock _run_openspec_json to capture argv and return canned payload."""
    captured = {}

    def _fake(args, timeout=10):
        captured["args"] = list(args)
        captured["timeout"] = timeout
        return captured.get("payload", {})

    monkeypatch.setattr(osx_lib, "_run_openspec_json", _fake)
    return captured


@pytest.mark.unit
class TestSchemaWhich:
    def test_basic_invocation(self, mock_json) -> None:
        mock_json["payload"] = {"name": "spec-driven", "source": "package"}
        result = schema_which()
        assert "schema" in mock_json["args"]
        assert "which" in mock_json["args"]
        # Wrapper must NOT pass --json; the helper appends it. See test_no_double_json.
        assert "--json" not in mock_json["args"]
        assert result["name"] == "spec-driven"

    def test_with_name(self, mock_json) -> None:
        schema_which("my-schema")
        assert "my-schema" in mock_json["args"]

    def test_with_all_flag(self, mock_json) -> None:
        schema_which(all_schemas=True)
        assert "--all" in mock_json["args"]

    def test_with_store(self, mock_json) -> None:
        schema_which(store="store-id")
        assert "--store" in mock_json["args"]
        assert "store-id" in mock_json["args"]

    def test_default_has_no_name_or_all(self, mock_json) -> None:
        schema_which()
        assert "--all" not in mock_json["args"]
        # Wrapper must NOT append --json itself; helper owns the flag.
        assert "--json" not in mock_json["args"]


@pytest.mark.unit
class TestSchemaValidate:
    def test_basic_invocation(self, mock_json) -> None:
        mock_json["payload"] = {"valid": True}
        schema_validate()
        assert "validate" in mock_json["args"]
        assert "schema" in mock_json["args"]

    def test_with_name(self, mock_json) -> None:
        schema_validate("my-schema")
        assert "my-schema" in mock_json["args"]

    def test_with_store(self, mock_json) -> None:
        schema_validate(store="store-id")
        assert "store-id" in mock_json["args"]


@pytest.mark.unit
class TestSchemaFork:
    def test_basic_invocation(self, mock_json) -> None:
        schema_fork("spec-driven")
        assert "fork" in mock_json["args"]
        assert "spec-driven" in mock_json["args"]

    def test_with_destination(self, mock_json) -> None:
        schema_fork("spec-driven", "my-fork")
        assert "my-fork" in mock_json["args"]

    def test_with_force(self, mock_json) -> None:
        schema_fork("spec-driven", force=True)
        assert "--force" in mock_json["args"]

    def test_without_force(self, mock_json) -> None:
        schema_fork("spec-driven")
        assert "--force" not in mock_json["args"]

    def test_with_store(self, mock_json) -> None:
        schema_fork("spec-driven", store="store-id")
        assert "store-id" in mock_json["args"]


@pytest.mark.unit
class TestSchemaInit:
    def test_basic_invocation(self, mock_json) -> None:
        schema_init("my-schema")
        assert "init" in mock_json["args"]
        assert "my-schema" in mock_json["args"]
        assert "schema" in mock_json["args"]

    def test_with_description(self, mock_json) -> None:
        schema_init("my-schema", description="Test")
        assert "--description" in mock_json["args"]
        assert "Test" in mock_json["args"]

    def test_with_artifacts(self, mock_json) -> None:
        schema_init("my-schema", artifacts=["proposal", "specs"])
        assert "--artifacts" in mock_json["args"]
        assert "proposal,specs" in mock_json["args"]

    def test_with_set_default(self, mock_json) -> None:
        schema_init("my-schema", set_default=True)
        assert "--default" in mock_json["args"]

    def test_with_force(self, mock_json) -> None:
        schema_init("my-schema", force=True)
        assert "--force" in mock_json["args"]

    def test_without_force(self, mock_json) -> None:
        schema_init("my-schema")
        assert "--force" not in mock_json["args"]

    def test_with_store(self, mock_json) -> None:
        schema_init("my-schema", store="store-id")
        assert "store-id" in mock_json["args"]


@pytest.mark.unit
class TestSchemaList:
    def test_returns_list(self, mock_json) -> None:
        mock_json["payload"] = [{"name": "spec-driven"}, {"name": "other"}]
        result = schema_list()
        assert isinstance(result, list)
        assert len(result) == 2
        assert "schemas" in mock_json["args"]
        # Wrapper must NOT pass --json; the helper appends it. See test_no_double_json.
        assert "--json" not in mock_json["args"]

    def test_handles_non_list_payload(self, mock_json) -> None:
        mock_json["payload"] = {"not": "a list"}
        result = schema_list()
        assert result == []

    def test_with_store(self, mock_json) -> None:
        mock_json["payload"] = []
        schema_list(store="store-id")
        assert "store-id" in mock_json["args"]


@pytest.mark.unit
class TestSchemaSubcommandTranslation:
    """Each wrapper must return the raw upstream payload unchanged."""

    def test_which_returns_payload(self, mock_json) -> None:
        mock_json["payload"] = {"name": "x", "source": "y"}
        assert schema_which() == {"name": "x", "source": "y"}

    def test_validate_returns_payload(self, mock_json) -> None:
        mock_json["payload"] = {"valid": False, "errors": ["e"]}
        assert schema_validate() == {"valid": False, "errors": ["e"]}

    def test_fork_returns_payload(self, mock_json) -> None:
        mock_json["payload"] = {"schema": "forked", "destination": "/x"}
        assert schema_fork("spec-driven") == {"schema": "forked", "destination": "/x"}

    def test_init_returns_payload(self, mock_json) -> None:
        mock_json["payload"] = {"created": "my-schema"}
        assert schema_init("my-schema") == {"created": "my-schema"}


def _write_schema_yaml(path, data) -> None:
    """Write a schema.yaml with the given dict content."""
    import yaml

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False))


@pytest.mark.unit
class TestSchemaForkDiff:
    """`schema_fork_diff` (v1.9.0+ fidelity check)."""

    def test_perfect_fidelity(self, tmp_path, monkeypatch) -> None:
        identical = {
            "schema": "my-fork",
            "artifacts": ["proposal", "specs"],
            "context": "shared",
        }
        _write_schema_yaml(
            tmp_path / "openspec" / "schemas" / "spec-driven" / "schema.yaml",
            identical,
        )
        _write_schema_yaml(
            tmp_path / "openspec" / "schemas" / "my-fork" / "schema.yaml",
            identical,
        )

        monkeypatch.setattr(
            osx_lib, "schema_fork", lambda *a, **kw: {"ok": True}
        )

        result = schema_fork_diff(
            "spec-driven", "my-fork", project_root=tmp_path
        )
        assert result["valid"] is True
        assert result["fidelity"] == "perfect"
        assert result["differences"] == []
        assert result["fidelity_warning"] is None
        assert result["schema_path"].endswith("schemas/my-fork/schema.yaml")

    def test_drifted_fidelity(self, tmp_path, monkeypatch) -> None:
        _write_schema_yaml(
            tmp_path / "openspec" / "schemas" / "spec-driven" / "schema.yaml",
            {"schema": "spec-driven", "artifacts": ["proposal"]},
        )
        _write_schema_yaml(
            tmp_path / "openspec" / "schemas" / "my-fork" / "schema.yaml",
            {"schema": "my-fork", "artifacts": ["proposal", "specs"]},
        )

        monkeypatch.setattr(
            osx_lib, "schema_fork", lambda *a, **kw: {"ok": True}
        )

        result = schema_fork_diff(
            "spec-driven", "my-fork", project_root=tmp_path
        )
        assert result["valid"] is False
        assert result["fidelity"] == "drifted"
        assert result["differences"] != []
        assert result["fidelity_warning"] is not None

    def test_fork_failure_propagates(self, tmp_path, monkeypatch) -> None:
        def _raise(*a, **kw):
            raise OSXError("cli_error", "schema fork failed")

        monkeypatch.setattr(osx_lib, "schema_fork", _raise)

        with pytest.raises(OSXError) as exc_info:
            schema_fork_diff("spec-driven", "my-fork", project_root=tmp_path)
        assert exc_info.value.code == "cli_error"

    def test_missing_source_schema(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(
            osx_lib, "schema_fork", lambda *a, **kw: {"ok": True}
        )
        with pytest.raises(OSXError) as exc_info:
            schema_fork_diff("missing-src", "my-fork", project_root=tmp_path)
        assert exc_info.value.code == "schema_not_found"

    def test_force_propagates_to_fork(self, tmp_path, monkeypatch) -> None:
        captured: dict = {}

        def _fake(source, name=None, *, force=False, store=None):
            captured["force"] = force
            return {"ok": True}

        monkeypatch.setattr(osx_lib, "schema_fork", _fake)

        _write_schema_yaml(
            tmp_path / "openspec" / "schemas" / "spec-driven" / "schema.yaml",
            {"a": 1},
        )
        _write_schema_yaml(
            tmp_path / "openspec" / "schemas" / "my-fork" / "schema.yaml",
            {"a": 1},
        )

        schema_fork_diff(
            "spec-driven", "my-fork", force=True, project_root=tmp_path
        )
        assert captured["force"] is True
