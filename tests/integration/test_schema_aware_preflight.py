#!/usr/bin/env python3
"""Integration tests for schema-aware pre-flight in the orchestrator."""

from pathlib import Path

import pytest

from source.lib import osx as osx_lib


@pytest.mark.integration
class TestSchemaAwarePreflight:
    """Verify orchestrator's pre-flight resolves schema correctly."""

    def test_schema_resolves_from_project_config(self, tmp_path: Path) -> None:
        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yaml").write_text("schema: my-custom\n")

        result = osx_lib.resolve_schema(project_root=tmp_path)
        assert result["name"] == "my-custom"
        assert result["source"] == "project-config"

    def test_schema_resolves_from_change_metadata(self, tmp_path: Path) -> None:
        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yaml").write_text("schema: from-config\n")
        change = tmp_path / "openspec" / "changes" / "my-change"
        change.mkdir(parents=True)
        (change / ".openspec.yaml").write_text("schema: from-change\n")

        result = osx_lib.resolve_schema(project_root=tmp_path, change_dir=change)
        assert result["name"] == "from-change"
        assert result["source"] == "change-metadata"

    def test_explicit_override_wins(self, tmp_path: Path) -> None:
        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yaml").write_text("schema: from-config\n")

        result = osx_lib.resolve_schema(project_root=tmp_path, explicit="from-cli")
        assert result["name"] == "from-cli"
        assert result["source"] == "explicit"

    def test_default_when_no_config(self, tmp_path: Path) -> None:
        result = osx_lib.resolve_schema(project_root=tmp_path)
        assert result["name"] == "spec-driven"
        assert result["source"] == "default"

    def test_validate_schema_caches_resolved_name(self, tmp_path, monkeypatch) -> None:
        from source.orchestrator.engine import OrchestratorState, validate_schema

        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yaml").write_text("schema: cached\n")
        monkeypatch.chdir(tmp_path)

        state = OrchestratorState(change_id="x", no_color=True, verbose=False)
        validate_schema(state)

        assert state.schema_name == "cached"
        assert state.schema_source == "project-config"

    def test_required_core_skills_for_spec_driven(self) -> None:
        skills = osx_lib.required_core_skills("spec-driven")
        assert "osc-apply-change" in skills
        assert "osc-verify-change" in skills
        assert "osc-sync-specs" in skills
        assert "osc-archive-change" in skills

    def test_required_core_skills_for_unknown_schema(self) -> None:
        skills = osx_lib.required_core_skills("custom-schema")
        assert "osc-archive-change" in skills
