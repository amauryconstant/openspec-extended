#!/usr/bin/env python3
"""Tests for resolve_schema() 4-level precedence chain."""

from pathlib import Path
from unittest.mock import patch

import pytest

from source.lib import osx as osx_lib
from source.lib.osx import (
    list_artifacts_for_schema,
    resolve_schema,
    required_core_skills,
)


@pytest.mark.unit
class TestResolveSchema:
    def test_explicit_override_wins(self, tmp_path: Path) -> None:
        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yaml").write_text("schema: from-config\n")
        result = resolve_schema(project_root=tmp_path, explicit="from-cli")
        assert result == {"name": "from-cli", "source": "explicit"}

    def test_change_metadata_overrides_project_config(self, tmp_path: Path) -> None:
        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yaml").write_text("schema: from-config\n")
        change = tmp_path / "openspec" / "changes" / "my-change"
        change.mkdir(parents=True)
        (change / ".openspec.yaml").write_text("schema: from-change\n")
        result = resolve_schema(project_root=tmp_path, change_dir=change)
        assert result == {"name": "from-change", "source": "change-metadata"}

    def test_project_config_used_when_no_change_metadata(self, tmp_path: Path) -> None:
        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yaml").write_text("schema: my-custom\n")
        result = resolve_schema(project_root=tmp_path)
        assert result == {"name": "my-custom", "source": "project-config"}

    def test_yaml_yml_fallback(self, tmp_path: Path) -> None:
        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yml").write_text("schema: from-yml\n")
        result = resolve_schema(project_root=tmp_path)
        assert result == {"name": "from-yml", "source": "project-config"}

    def test_yaml_prefers_yaml_over_yml(self, tmp_path: Path) -> None:
        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yaml").write_text("schema: from-yaml\n")
        (tmp_path / "openspec" / "config.yml").write_text("schema: from-yml\n")
        result = resolve_schema(project_root=tmp_path)
        assert result == {"name": "from-yaml", "source": "project-config"}

    def test_default_when_no_config(self, tmp_path: Path) -> None:
        result = resolve_schema(project_root=tmp_path)
        assert result == {"name": "spec-driven", "source": "default"}

    def test_malformed_yaml_falls_through(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / "openspec").mkdir()
        config_path = tmp_path / "openspec" / "config.yaml"
        config_path.write_text("schema: : invalid\n")
        result = resolve_schema(project_root=tmp_path)
        captured = capsys.readouterr()
        assert result == {"name": "spec-driven", "source": "default"}
        assert "Warning: Could not load schema configuration" in captured.err
        assert str(config_path) in captured.err

    def test_empty_schema_field_falls_through(self, tmp_path: Path) -> None:
        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yaml").write_text("schema: ''\n")
        result = resolve_schema(project_root=tmp_path)
        assert result == {"name": "spec-driven", "source": "default"}

    def test_non_string_schema_falls_through(self, tmp_path: Path) -> None:
        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yaml").write_text("schema: 42\n")
        result = resolve_schema(project_root=tmp_path)
        assert result == {"name": "spec-driven", "source": "default"}

    def test_change_dir_without_metadata_falls_through_to_config(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yaml").write_text("schema: from-config\n")
        change = tmp_path / "openspec" / "changes" / "my-change"
        change.mkdir(parents=True)
        result = resolve_schema(project_root=tmp_path, change_dir=change)
        assert result == {"name": "from-config", "source": "project-config"}

    def test_change_metadata_malformed_falls_through(self, tmp_path: Path) -> None:
        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yaml").write_text("schema: from-config\n")
        change = tmp_path / "openspec" / "changes" / "my-change"
        change.mkdir(parents=True)
        (change / ".openspec.yaml").write_text("schema: : invalid\n")
        result = resolve_schema(project_root=tmp_path, change_dir=change)
        assert result == {"name": "from-config", "source": "project-config"}


@pytest.mark.unit
class TestRequiredCoreSkills:
    def test_spec_driven_returns_full_set(self) -> None:
        skills = required_core_skills("spec-driven")
        assert "osc-apply-change" in skills
        assert "osc-verify-change" in skills
        assert "osc-sync-specs" in skills
        assert "osc-archive-change" in skills

    def test_unknown_schema_returns_archive_only(self) -> None:
        skills = required_core_skills("custom-schema")
        assert skills == ["osc-archive-change"]

    def test_empty_string_returns_archive_only(self) -> None:
        skills = required_core_skills("")
        assert skills == ["osc-archive-change"]


@pytest.mark.unit
class TestListArtifactsForSchema:
    def test_returns_dict_keys_on_success(self) -> None:
        fake_payload = {"proposal": {}, "specs": {}, "design": {}}
        with patch.object(
            osx_lib, "_run_openspec_json", return_value=fake_payload
        ) as mock:
            result = list_artifacts_for_schema("spec-driven")
        assert set(result) == {"proposal", "specs", "design"}
        assert "templates" in mock.call_args[0][0]
        assert "--schema" in mock.call_args[0][0]
        assert "spec-driven" in mock.call_args[0][0]

    def test_passes_store(self) -> None:
        with patch.object(osx_lib, "_run_openspec_json", return_value={}) as mock:
            list_artifacts_for_schema("spec-driven", store="store-1")
        args = mock.call_args[0][0]
        assert "--store" in args
        assert "store-1" in args

    def test_falls_back_on_osxerror(self) -> None:
        with patch.object(
            osx_lib, "_run_openspec_json", side_effect=osx_lib.OSXError("cli", "x")
        ):
            result = list_artifacts_for_schema("anything")
        assert result == ["proposal", "specs", "design", "tasks"]

    def test_falls_back_on_non_dict_payload(self) -> None:
        with patch.object(osx_lib, "_run_openspec_json", return_value=["not", "dict"]):
            result = list_artifacts_for_schema("anything")
        assert result == ["proposal", "specs", "design", "tasks"]