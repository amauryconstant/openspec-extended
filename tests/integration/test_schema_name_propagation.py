#!/usr/bin/env python3
"""Integration tests for ``state.schema_name`` propagation through phases.

Roadmap Tier 4 audit item: the orchestrator resolves the workflow schema
exactly once, in ``source/orchestrator/engine.py:274-305`` (``validate_schema``),
and stores the result on ``state.schema_name`` / ``state.schema_source``.
No test had previously exercised the full path from pre-flight through a
simulated phase advance to confirm the schema name survives.

These tests fill that gap. They drive ``OrchestratorState`` directly and
use ``osx_lib.state_set_phase`` to write ``state.json`` so we can observe
the full read/write loop without spawning AI subprocesses.
"""

from pathlib import Path

import pytest

from source.lib import osx as osx_lib


@pytest.mark.integration
class TestSchemaNamePropagation:
    """Pin that ``state.schema_name`` survives from pre-flight to PHASE6."""

    def test_schema_name_set_after_preflight(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from source.orchestrator.engine import OrchestratorState, validate_schema

        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yaml").write_text("schema: live-test\n")
        monkeypatch.chdir(tmp_path)

        state = OrchestratorState(change_id="x", no_color=True, verbose=False)
        validate_schema(state)

        assert state.schema_name == "live-test"
        assert state.schema_source == "project-config"

    def test_schema_name_survives_simulated_phase_advance(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A phase advance must not clear ``state.schema_name``.

        ``state_set_phase`` writes ``state.json`` under
        ``openspec/changes/<id>/`` but never mutates the in-memory
        ``OrchestratorState``. The orchestrator loop
        (``source/orchestrator/engine.py:1009-1102``) does not re-invoke
        ``validate_schema`` after the first call, so the schema name
        established at pre-flight is the one in force for the whole run.
        """
        from source.orchestrator.engine import OrchestratorState, validate_schema

        (tmp_path / "openspec" / "config.yaml").parent.mkdir(parents=True)
        (tmp_path / "openspec" / "config.yaml").write_text("schema: persists\n")
        change_dir = tmp_path / "openspec" / "changes" / "propagation-test"
        change_dir.mkdir(parents=True)
        (change_dir / "proposal.md").write_text("# propagation-test\n")

        monkeypatch.chdir(tmp_path)
        state = OrchestratorState(
            change_id="propagation-test",
            change_dir=change_dir,
            no_color=True,
            verbose=False,
        )
        validate_schema(state)
        assert state.schema_name == "persists"

        (change_dir / "state.json").write_text(
            '{"phase": "PHASE0", "iteration": 0, "phase_complete": false}'
        )

        osx_lib.state_set_phase("propagation-test", "PHASE1", iteration=1)
        assert state.schema_name == "persists"
        assert state.schema_source == "project-config"

        osx_lib.state_set_phase("propagation-test", "PHASE6", iteration=1)
        assert state.schema_name == "persists"

    def test_explicit_override_wins_over_project_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``state.schema_override`` (from ``--schema``) wins over the
        project config and the resolved name is reported as ``explicit``."""
        from source.orchestrator.engine import OrchestratorState, validate_schema

        (tmp_path / "openspec").mkdir()
        (tmp_path / "openspec" / "config.yaml").write_text("schema: from-config\n")
        monkeypatch.chdir(tmp_path)

        state = OrchestratorState(
            change_id="override-test",
            schema_override="from-cli",
            no_color=True,
            verbose=False,
        )
        validate_schema(state)

        assert state.schema_name == "from-cli"
        assert state.schema_source == "explicit"

    def test_default_when_no_config(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """With no config and no override, schema falls back to ``spec-driven``."""
        from source.orchestrator.engine import OrchestratorState, validate_schema

        monkeypatch.chdir(tmp_path)
        state = OrchestratorState(
            change_id="default-test", no_color=True, verbose=False
        )
        validate_schema(state)

        assert state.schema_name == "spec-driven"
        assert state.schema_source == "default"