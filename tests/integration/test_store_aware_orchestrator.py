#!/usr/bin/env python3
"""
Integration tests for store-aware orchestrator behavior.

Covers:
  - OrchestratorState.store field (default None, accepts override)
  - find_change_dir(change, store=...) consults the CLI (v1.5.0 shape)
  - parse_change_spec(spec) -> (store, change) for all forms
  - _extract_changes() handles every v1.5.0 list JSON shape
"""

import json
from unittest.mock import MagicMock

import pytest

from source.orchestrator.engine import (
    OrchestratorState,
    parse_change_spec,
    find_change_dir,
    _extract_changes,
)
from source.lib import osx


def make_run(stdout="", returncode=0, stderr="", exc=None):
    """Build a fake subprocess.run callable."""

    def _run(*args, **kwargs):
        if exc is not None:
            raise exc
        return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)

    return _run


@pytest.fixture
def store_change(tmp_path):
    """Create a fake change directory inside a fake planning_home."""
    planning = tmp_path / "planning"
    change_dir = planning / "openspec" / "changes" / "add-foo"
    change_dir.mkdir(parents=True)
    for f in ("proposal.md", "design.md", "tasks.md"):
        (change_dir / f).write_text("# stub")
    (change_dir / "specs").mkdir()
    (change_dir / "specs" / "spec.md").write_text("# spec")
    return planning, change_dir


@pytest.mark.integration
class TestStoreAwareEngine:
    def test_orchestrator_state_has_store_field(self):
        """OrchestratorState.store exists and defaults to None."""
        s = OrchestratorState(change_id="x")
        assert s.store is None
        s2 = OrchestratorState(change_id="x", store="s1")
        assert s2.store == "s1"

    def test_find_change_dir_with_store(self, store_change, monkeypatch):
        """find_change_dir(change, store=...) consults the CLI."""
        planning, change_dir = store_change
        payload = json.dumps(
            {
                "changeRoot": str(change_dir),
                "planningHome": {"kind": "repo", "root": str(planning)},
            }
        )
        monkeypatch.setattr(osx.subprocess, "run", make_run(stdout=payload))
        result = find_change_dir("add-foo", store="s1")
        assert result == change_dir

    def test_parse_change_spec(self):
        """parse_change_spec handles all forms."""
        assert parse_change_spec("foo") == (None, "foo")
        assert parse_change_spec("s1:foo") == ("s1", "foo")
        assert parse_change_spec("s1:ns:foo") == ("s1", "ns:foo")
        assert parse_change_spec("") == (None, "")
        assert parse_change_spec("s1:") == ("s1", "")

    def test_extract_changes(self):
        """_extract_changes handles the various v1.5.0 JSON shapes."""
        assert _extract_changes([{"name": "a"}]) == [{"name": "a"}]
        assert _extract_changes({"changes": [{"name": "a"}]}) == [{"name": "a"}]
        assert _extract_changes({"items": [{"name": "a"}]}) == [{"name": "a"}]
        assert _extract_changes({}) == []
        assert _extract_changes("garbage") == []
        assert _extract_changes(None) == []