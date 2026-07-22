import json
import os

import pytest

from source.lib import osx, state_io
from source.orchestrator import engine


pytestmark = pytest.mark.unit


def test_atomic_write_failure_preserves_original_state(tmp_path, monkeypatch):
    original = {"phase": "PHASE1", "iteration": 2}
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps(original))

    def fail_replace(source, destination):
        raise OSError("interrupted")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(OSError, match="interrupted"):
        state_io.write_state(tmp_path, {"phase": "PHASE2", "iteration": 1})

    assert json.loads(state_file.read_text()) == original


def test_engine_and_library_use_shared_state_io_module():
    assert engine.state_io is state_io
    assert osx.state_io is state_io


def _build_state(change_dir):
    state = engine.OrchestratorState()
    state.change_dir = change_dir
    return state


def test_engine_write_state_initializes_started_at_on_first_write(tmp_path):
    state = _build_state(tmp_path)

    engine.write_state(state, "PHASE1", iteration=1)

    data = json.loads((tmp_path / "state.json").read_text())
    assert "started_at" in data
    assert data["started_at"] == data["last_updated"]


def test_engine_write_state_preserves_started_at_across_writes(tmp_path):
    state = _build_state(tmp_path)

    engine.write_state(state, "PHASE1", iteration=1)
    first = json.loads((tmp_path / "state.json").read_text())
    started_at_1 = first["started_at"]
    last_updated_1 = first["last_updated"]
    assert started_at_1 == last_updated_1

    engine.write_state(state, "PHASE1", iteration=2)
    second = json.loads((tmp_path / "state.json").read_text())
    assert second["started_at"] == started_at_1
    assert second["last_updated"] != last_updated_1 or second["last_updated"] >= started_at_1


def test_get_next_phase_iteration_starts_at_one_when_no_state(tmp_path):
    state = _build_state(tmp_path)

    assert engine.get_next_phase_iteration(state, "PHASE1") == 1


def test_get_next_phase_iteration_returns_one_when_change_dir_is_none():
    state = engine.OrchestratorState()
    state.change_dir = None

    assert engine.get_next_phase_iteration(state, "PHASE1") == 1


def test_get_next_phase_iteration_resumes_from_persisted_count(tmp_path):
    state_data = {
        "phase": "PHASE1",
        "phase_name": "IMPLEMENTATION",
        "iteration": 4,
        "phase_complete": False,
        "total_invocations": 4,
        "phase_iterations": {"PHASE1": 4},
        "started_at": "2026-01-01T00:00:00Z",
        "last_updated": "2026-01-01T00:00:00Z",
    }
    (tmp_path / "state.json").write_text(json.dumps(state_data))
    state = _build_state(tmp_path)

    assert engine.get_next_phase_iteration(state, "PHASE1") == 5


def test_get_next_phase_iteration_uses_phase_specific_counter(tmp_path):
    state_data = {
        "phase": "PHASE2",
        "phase_iterations": {"PHASE1": 4, "PHASE2": 7},
        "iteration": 7,
    }
    (tmp_path / "state.json").write_text(json.dumps(state_data))
    state = _build_state(tmp_path)

    assert engine.get_next_phase_iteration(state, "PHASE1") == 5
    assert engine.get_next_phase_iteration(state, "PHASE2") == 8


def test_get_next_phase_iteration_treats_missing_phase_key_as_zero(tmp_path):
    state_data = {
        "phase": "PHASE3",
        "phase_iterations": {"PHASE2": 3},
        "iteration": 3,
    }
    (tmp_path / "state.json").write_text(json.dumps(state_data))
    state = _build_state(tmp_path)

    assert engine.get_next_phase_iteration(state, "PHASE3") == 1
