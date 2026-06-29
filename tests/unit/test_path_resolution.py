#!/usr/bin/env python3
"""
Unit tests for path resolution in source.lib.osx.

Locks down the v1.5.0 behavior of:
  - resolve_change_paths(change, store=None) -> dict
  - _find_change_dir(change, store=None) -> Path
  - _run_openspec_json(args) -> dict

Subprocess is mocked so tests do not depend on a real `openspec` binary.
The `_PATHS_CACHE` module-level dict is cleared between tests via an
autouse fixture to prevent cross-test pollution.
"""

import json
from unittest.mock import MagicMock

import pytest

from source.lib import osx


def make_run(stdout="", returncode=0, stderr="", exc=None):
    """Build a fake subprocess.run callable."""

    def _run(*args, **kwargs):
        if exc is not None:
            raise exc
        return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)

    return _run


@pytest.fixture(autouse=True)
def _clear_paths_cache():
    """Clear osx._PATHS_CACHE before and after each test."""
    osx._PATHS_CACHE.clear()
    yield
    osx._PATHS_CACHE.clear()


@pytest.mark.unit
class TestResolveChangePaths:
    def test_fallback_when_cli_missing(self, tmp_path, monkeypatch):
        """Without openspec on PATH, resolve_change_paths uses repo-local convention."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "openspec/changes/foo").mkdir(parents=True)
        monkeypatch.setattr(osx.subprocess, "run", make_run(exc=FileNotFoundError()))
        result = osx.resolve_change_paths("foo")
        assert result["change_root"].name == "foo"
        assert result["source"] == "fallback"
        assert result["archive_dir"].resolve() == (
            tmp_path / "openspec" / "changes" / "archive"
        )

    def test_uses_cli_change_root_when_available(self, tmp_path, monkeypatch):
        """With a CLI returning changeRoot + planningHome (object form), use them."""
        store_root = tmp_path / "store-root" / "openspec" / "changes" / "foo"
        store_root.mkdir(parents=True)
        planning_root = tmp_path / "store-root"
        payload = json.dumps(
            {
                "changeRoot": str(store_root),
                "planningHome": {
                    "kind": "repo",
                    "root": str(planning_root),
                    "changesDir": str(planning_root / "openspec" / "changes"),
                    "defaultSchema": "spec-driven",
                },
            }
        )
        monkeypatch.setattr(osx.subprocess, "run", make_run(stdout=payload))
        result = osx.resolve_change_paths("foo")
        assert result["change_root"] == store_root
        assert result["source"] == "cli"
        assert result["archive_dir"] == planning_root / "openspec" / "changes" / "archive"

    def test_explicit_store_kwarg_takes_precedence(self, tmp_path, monkeypatch):
        """store= kwarg overrides the contextvar."""
        store_root = tmp_path / "store-root" / "openspec" / "changes" / "foo"
        store_root.mkdir(parents=True)
        payload = json.dumps(
            {
                "changeRoot": str(store_root),
                "planningHome": {"kind": "repo", "root": str(tmp_path / "store-root")},
            }
        )
        monkeypatch.setattr(osx.subprocess, "run", make_run(stdout=payload))
        token = osx.current_store.set("wrong-store")
        try:
            result = osx.resolve_change_paths("foo", store="s1")
        finally:
            osx.current_store.reset(token)
        assert result["change_root"] == store_root

    def test_contextvar_used_when_kwarg_absent(self, tmp_path, monkeypatch):
        """When no store= kwarg, current_store.get() is used."""
        store_root = tmp_path / "store-root" / "openspec" / "changes" / "foo"
        store_root.mkdir(parents=True)
        payload = json.dumps(
            {
                "changeRoot": str(store_root),
                "planningHome": {"kind": "repo", "root": str(tmp_path / "store-root")},
            }
        )
        monkeypatch.setattr(osx.subprocess, "run", make_run(stdout=payload))
        token = osx.current_store.set("s1")
        try:
            result = osx.resolve_change_paths("foo")
        finally:
            osx.current_store.reset(token)
        assert result["change_root"] == store_root

    def test_subprocess_invocation_includes_store_flag(self, tmp_path, monkeypatch):
        """When a store is in effect, --store is added to the openspec args."""
        store_root = tmp_path / "store-root" / "openspec" / "changes" / "foo"
        store_root.mkdir(parents=True)
        payload = json.dumps(
            {
                "changeRoot": str(store_root),
                "planningHome": {"kind": "repo", "root": str(tmp_path / "store-root")},
            }
        )
        captured = {}

        def _run(*args, **kwargs):
            captured["cmd"] = list(args[0]) if args else kwargs.get("args", [])
            return MagicMock(returncode=0, stdout=payload, stderr="")

        monkeypatch.setattr(osx.subprocess, "run", _run)
        osx.resolve_change_paths("foo", store="my-store")
        assert "--store" in captured["cmd"]
        assert "my-store" in captured["cmd"]


@pytest.mark.unit
class TestFindChangeDir:
    """Backward-compatibility: _find_change_dir still works the way existing tests expect."""

    def test_primary_change_dir(self, tmp_path, monkeypatch):
        """Finds change in openspec/changes/<name>/ (fallback path)."""
        monkeypatch.chdir(tmp_path)
        (tmp_path / "openspec/changes/test-change").mkdir(parents=True)
        monkeypatch.setattr(osx.subprocess, "run", make_run(exc=FileNotFoundError()))
        result = osx._find_change_dir("test-change")
        assert result.name == "test-change"
        assert result.parent.name == "changes"

    def test_archived_change(self, tmp_path, monkeypatch):
        """Finds change in archive when not in active location."""
        monkeypatch.chdir(tmp_path)
        archive = tmp_path / "openspec" / "changes" / "archive" / "2024-01-15-test-change"
        archive.mkdir(parents=True)
        monkeypatch.setattr(osx.subprocess, "run", make_run(exc=FileNotFoundError()))
        result = osx._find_change_dir("test-change")
        assert result.resolve() == archive

    def test_not_found_raises(self, tmp_path, monkeypatch):
        """Raises OSXError when no change exists anywhere."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(osx.subprocess, "run", make_run(exc=FileNotFoundError()))
        with pytest.raises(osx.OSXError) as e:
            osx._find_change_dir("nonexistent")
        assert e.value.code == "change_not_found"


@pytest.mark.unit
class TestRunOpenspecJson:
    def test_parses_json(self, monkeypatch):
        """Returns parsed dict on success."""
        monkeypatch.setattr(osx.subprocess, "run", make_run(stdout='{"a": 1}'))
        assert osx._run_openspec_json(["list"]) == {"a": 1}

    def test_raises_cli_not_found(self, monkeypatch):
        monkeypatch.setattr(osx.subprocess, "run", make_run(exc=FileNotFoundError()))
        with pytest.raises(osx.OSXError) as e:
            osx._run_openspec_json(["list"])
        assert e.value.code == "cli_not_found"

    def test_raises_cli_error_on_nonzero(self, monkeypatch):
        monkeypatch.setattr(osx.subprocess, "run", make_run(returncode=1, stderr="bad"))
        with pytest.raises(osx.OSXError) as e:
            osx._run_openspec_json(["list"])
        assert e.value.code == "cli_error"
        assert "bad" in e.value.message

    def test_raises_invalid_json(self, monkeypatch):
        monkeypatch.setattr(osx.subprocess, "run", make_run(stdout="not-json"))
        with pytest.raises(osx.OSXError) as e:
            osx._run_openspec_json(["list"])
        assert e.value.code == "invalid_json"