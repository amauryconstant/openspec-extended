#!/usr/bin/env python3
"""Tests for resolve_schema() 4-level precedence chain."""

from pathlib import Path
from unittest.mock import patch

import pytest

from source.lib import osx as osx_lib
from source.lib.osx import (
    list_artifacts_for_schema,
    read_change_metadata,
    required_core_skills,
    resolve_schema,
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
class TestSchemaAndMetadataAgreement:
    """A.3: ``resolve_schema`` and ``read_change_metadata`` read the same
    ``.openspec.yaml`` file but for different keys. They must agree on
    schema precedence: whatever schema name ``resolve_schema`` returns from
    the change-metadata layer must also appear under ``schema:`` in the
    metadata dict.
    """

    def test_resolve_schema_and_read_metadata_agree(self, tmp_path: Path) -> None:
        change = tmp_path / "openspec" / "changes" / "retire-capability"
        change.mkdir(parents=True)
        (change / ".openspec.yaml").write_text(
            "schema: workspace-planning\nretire_capabilities: true\n"
        )

        schema_info = resolve_schema(
            project_root=tmp_path, change_dir=change
        )
        assert schema_info["name"] == "workspace-planning"
        assert schema_info["source"] == "change-metadata"

        meta = read_change_metadata(change)
        assert meta["schema"] == "workspace-planning"
        assert meta["retire_capabilities"] is True
        # Both agree the same schema wins — and that retire_capabilities
        # surfaces as a sibling key without disturbing schema precedence.
        assert meta["schema"] == schema_info["name"]

    def test_resolve_schema_default_when_only_retire_set(self, tmp_path: Path) -> None:
        """``.openspec.yaml`` with only `retire_capabilities` (no schema key)
        does not influence schema resolution — falls back to spec-driven,
        but ``read_change_metadata`` still surfaces the retire flag."""
        change = tmp_path / "openspec" / "changes" / "no-schema"
        change.mkdir(parents=True)
        (change / ".openspec.yaml").write_text("retire_capabilities: true\n")

        schema_info = resolve_schema(
            project_root=tmp_path, change_dir=change
        )
        assert schema_info == {"name": "spec-driven", "source": "default"}

        meta = read_change_metadata(change)
        assert meta == {"retire_capabilities": True}
        assert "schema" not in meta


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
class TestFetchOperationGuidance:
    """A.4: ``fetch_operation_guidance`` reads
    ``operations.{operation}.guidance`` from ``openspec/config.yaml`` so the
    orchestrator can inject project-level advisory guidance into PHASE1
    (apply) and PHASE6 (archive) prompts without a subprocess round-trip.
    """

    def test_apply_guidance(self, tmp_path: Path) -> None:
        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yaml").write_text(
            "operations:\n  apply:\n    guidance:\n      - 'always use snake_case'\n"
        )
        from source.lib.osx import fetch_operation_guidance

        assert fetch_operation_guidance("apply", project_root=tmp_path) == [
            "always use snake_case"
        ]

    def test_archive_guidance(self, tmp_path: Path) -> None:
        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yaml").write_text(
            "operations:\n  archive:\n    guidance:\n      - 'preserve CHANGELOG ordering'\n"
        )
        from source.lib.osx import fetch_operation_guidance

        assert fetch_operation_guidance("archive", project_root=tmp_path) == [
            "preserve CHANGELOG ordering"
        ]

    def test_other_operation_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yaml").write_text(
            "operations:\n  deploy:\n    guidance:\n      - 'ignore me'\n"
        )
        from source.lib.osx import fetch_operation_guidance

        # Even when "deploy" has guidance, fetching "apply" returns [] —
        # only the canonical {apply, archive} operations are supported.
        assert fetch_operation_guidance("apply", project_root=tmp_path) == []
        assert fetch_operation_guidance("archive", project_root=tmp_path) == []

    def test_only_archive_returns_empty_for_apply(self, tmp_path: Path) -> None:
        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yaml").write_text(
            "operations:\n  archive:\n    guidance:\n      - 'archive-only'\n"
        )
        from source.lib.osx import fetch_operation_guidance

        # Operations are addressed individually; asking for apply when only
        # archive has guidance returns [].
        assert fetch_operation_guidance("apply", project_root=tmp_path) == []
        assert fetch_operation_guidance("archive", project_root=tmp_path) == [
            "archive-only"
        ]

    def test_missing_config_returns_empty(self, tmp_path: Path) -> None:
        from source.lib.osx import fetch_operation_guidance

        # No openspec/config.yaml under tmp_path; both operations return [].
        assert fetch_operation_guidance("apply", project_root=tmp_path) == []
        assert fetch_operation_guidance("archive", project_root=tmp_path) == []

    def test_malformed_yaml_returns_empty(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / "openspec").mkdir()
        config_path = tmp_path / "openspec" / "config.yaml"
        config_path.write_text("operations: : invalid\n")
        from source.lib.osx import fetch_operation_guidance

        result = fetch_operation_guidance("apply", project_root=tmp_path)
        assert result == []
        # Malformed YAML is tolerated (logged, not raised) — same tolerance
        # as ``resolve_schema``.
        captured = capsys.readouterr()
        assert "Could not load operations guidance" in captured.err
        assert str(config_path) in captured.err

    def test_invalid_operation_returns_empty(self, tmp_path: Path) -> None:
        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yaml").write_text(
            "operations:\n  apply:\n    guidance:\n      - 'snake_case'\n"
        )
        from source.lib.osx import fetch_operation_guidance

        # Anything outside the canonical set returns [] — even if a
        # matching guidance block exists.
        assert fetch_operation_guidance("invalid", project_root=tmp_path) == []
        assert fetch_operation_guidance("", project_root=tmp_path) == []
        assert fetch_operation_guidance("APPLY", project_root=tmp_path) == []

    def test_yml_fallback(self, tmp_path: Path) -> None:
        """``config.yml`` is consulted when ``config.yaml`` is absent."""
        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yml").write_text(
            "operations:\n  apply:\n    guidance:\n      - 'yml-path works'\n"
        )
        from source.lib.osx import fetch_operation_guidance

        assert fetch_operation_guidance("apply", project_root=tmp_path) == [
            "yml-path works"
        ]

    def test_non_list_guidance_returns_empty(self, tmp_path: Path) -> None:
        """A guidance block that isn't a list is silently ignored."""
        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yaml").write_text(
            "operations:\n  apply:\n    guidance: 'single-string-not-list'\n"
        )
        from source.lib.osx import fetch_operation_guidance

        assert fetch_operation_guidance("apply", project_root=tmp_path) == []


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
