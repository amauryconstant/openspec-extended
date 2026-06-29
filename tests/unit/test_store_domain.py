#!/usr/bin/env python3
"""
Unit tests for store_* functions in source.lib.osx.

Covers the v1.5.0 CLI shapes for:
  - store_list()   -> {success, data}
  - store_doctor([id]) -> {success, data}
  - store_register(path, name=None) -> {success, data}
  - store_unregister(id) -> {success, data}

Subprocess is mocked; tests do not need a real `openspec` binary.
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


@pytest.mark.unit
class TestStoreDomain:
    def test_store_list_parses(self, monkeypatch):
        """store_list() returns success+data from the CLI JSON."""
        payload = json.dumps(
            {"stores": [{"id": "s1", "path": "/x", "name": "S1"}], "status": []}
        )
        monkeypatch.setattr(osx.subprocess, "run", make_run(stdout=payload))
        result = osx.store_list()
        assert result["success"] is True
        assert "stores" in result["data"]

    def test_store_list_cli_missing_raises(self, monkeypatch):
        monkeypatch.setattr(osx.subprocess, "run", make_run(exc=FileNotFoundError()))
        with pytest.raises(osx.OSXError) as e:
            osx.store_list()
        assert e.value.code == "cli_not_found"

    def test_store_doctor_with_id(self, monkeypatch):
        """store_doctor(id) passes the id as a CLI arg."""
        captured = {}

        def _run(*args, **kwargs):
            captured["cmd"] = list(args[0]) if args else kwargs.get("args", [])
            return MagicMock(returncode=0, stdout='{"id": "s1", "ok": true}', stderr="")

        monkeypatch.setattr(osx.subprocess, "run", _run)
        osx.store_doctor("my-store")
        assert "my-store" in captured["cmd"]
        assert "doctor" in captured["cmd"]

    def test_store_doctor_without_id(self, monkeypatch):
        """store_doctor() with no id checks all stores."""
        captured = {}

        def _run(*args, **kwargs):
            captured["cmd"] = list(args[0]) if args else kwargs.get("args", [])
            return MagicMock(returncode=0, stdout='{"stores": []}', stderr="")

        monkeypatch.setattr(osx.subprocess, "run", _run)
        osx.store_doctor()
        assert "doctor" in captured["cmd"]
        # No store id should be appended (cmd is ["openspec","store","doctor","--json"])
        assert captured["cmd"] == ["openspec", "store", "doctor", "--json"]

    def test_store_register_passes_name(self, monkeypatch):
        """store_register includes --name when given."""
        captured = {}

        def _run(*args, **kwargs):
            captured["cmd"] = list(args[0]) if args else kwargs.get("args", [])
            return MagicMock(returncode=0, stdout='{"id": "s1"}', stderr="")

        monkeypatch.setattr(osx.subprocess, "run", _run)
        osx.store_register("/path/to/repo", name="My Store")
        assert "/path/to/repo" in captured["cmd"]
        assert "register" in captured["cmd"]
        assert "--name" in captured["cmd"]
        assert "My Store" in captured["cmd"]

    def test_store_register_without_name(self, monkeypatch):
        """store_register without name does not add --name."""
        captured = {}

        def _run(*args, **kwargs):
            captured["cmd"] = list(args[0]) if args else kwargs.get("args", [])
            return MagicMock(returncode=0, stdout='{"id": "s1"}', stderr="")

        monkeypatch.setattr(osx.subprocess, "run", _run)
        osx.store_register("/path/to/repo")
        assert "/path/to/repo" in captured["cmd"]
        assert "--name" not in captured["cmd"]

    def test_store_unregister(self, monkeypatch):
        """store_unregister passes the id as a CLI arg."""
        captured = {}

        def _run(*args, **kwargs):
            captured["cmd"] = list(args[0]) if args else kwargs.get("args", [])
            return MagicMock(returncode=0, stdout='{"id": "s1"}', stderr="")

        monkeypatch.setattr(osx.subprocess, "run", _run)
        osx.store_unregister("my-store")
        assert "my-store" in captured["cmd"]
        assert "unregister" in captured["cmd"]