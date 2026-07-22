#!/usr/bin/env python3
"""
Unit tests for the ``complete`` domain in ``source.lib.osx``.

Locks in Phase-1 correctness contracts:

- ``complete_set(change, "BLOCKED")`` without ``blocker_reason`` MUST raise
  ``OSXError(code="invalid_blocker")`` instead of silently writing a
  ``with_blocker=False`` record.
- ``complete_set(change, "BLOCKED", blocker_reason=...)`` MUST persist
  ``with_blocker=True`` together with the reason.
"""

import json
from unittest.mock import MagicMock

import pytest

from source.lib import osx
from source.lib.osx import OSXError


def make_run(exc=None):
    """Build a fake subprocess.run that fails as if openspec is missing."""

    def _run(*args, **kwargs):
        if exc is not None:
            raise exc
        return MagicMock(returncode=0, stdout="{}", stderr="")

    return _run


@pytest.fixture
def change_dir(tmp_path, monkeypatch):
    """Create a change directory under tmp_path and chdir to its root."""
    change = "blocked-test"
    change_root = tmp_path / "openspec" / "changes" / change
    change_root.mkdir(parents=True)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(osx.subprocess, "run", make_run(exc=FileNotFoundError()))
    return change


@pytest.fixture(autouse=True)
def _clear_paths_cache():
    osx._PATHS_CACHE.clear()
    yield
    osx._PATHS_CACHE.clear()


@pytest.mark.unit
class TestCompleteSetBlocked:
    def test_blocked_without_reason_raises_invalid_blocker(self, change_dir, tmp_path):
        """BLOCKED without blocker_reason must raise OSXError(invalid_blocker)."""
        with pytest.raises(OSXError) as exc_info:
            osx.complete_set(change_dir, "BLOCKED")
        assert exc_info.value.code == "invalid_blocker"
        assert "blocker-reason" in exc_info.value.message

    def test_blocked_without_reason_does_not_write_file(self, change_dir, tmp_path):
        """A failed BLOCKED write must not leave a complete.json behind."""
        complete_file = tmp_path / "openspec" / "changes" / change_dir / "complete.json"
        with pytest.raises(OSXError):
            osx.complete_set(change_dir, "BLOCKED")
        assert not complete_file.exists()

    def test_blocked_with_reason_persists_with_blocker(self, change_dir, tmp_path):
        """BLOCKED with a reason writes with_blocker=True and the reason."""
        result = osx.complete_set(
            change_dir, "BLOCKED", blocker_reason="flaky upstream API"
        )
        assert result == {
            "status": "BLOCKED",
            "with_blocker": True,
            "blocker_reason": "flaky upstream API",
        }
        complete_file = tmp_path / "openspec" / "changes" / change_dir / "complete.json"
        payload = json.loads(complete_file.read_text())
        assert payload["status"] == "BLOCKED"
        assert payload["with_blocker"] is True
        assert payload["blocker_reason"] == "flaky upstream API"

    def test_blocked_with_empty_string_reason_still_raises(self, change_dir):
        """An empty string is treated as 'no reason' and must raise."""
        with pytest.raises(OSXError) as exc_info:
            osx.complete_set(change_dir, "BLOCKED", blocker_reason="")
        assert exc_info.value.code == "invalid_blocker"

    def test_complete_default_still_succeeds(self, change_dir):
        """Status=None defaults to COMPLETE and is unaffected by the new check."""
        result = osx.complete_set(change_dir)
        assert result == {"status": "COMPLETE", "with_blocker": False}
